import os
from io import BytesIO
from collections import defaultdict
from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)


def number_to_words(n):
    """Convert a number to words (Indian English)."""
    if n == 0:
        return 'Zero'

    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digits(num):
        if num < 20:
            return ones[num]
        return tens[num // 10] + ('' if num % 10 == 0 else ' ' + ones[num % 10])

    def three_digits(num):
        if num >= 100:
            return ones[num // 100] + ' Hundred' + ('' if num % 100 == 0 else ' and ' + two_digits(num % 100))
        return two_digits(num)

    n = int(round(n))
    if n < 0:
        return 'Minus ' + number_to_words(-n)

    parts = []
    if n >= 10000000:
        parts.append(two_digits(n // 10000000) + ' Crore')
        n %= 10000000
    if n >= 100000:
        parts.append(two_digits(n // 100000) + ' Lakh')
        n %= 100000
    if n >= 1000:
        parts.append(two_digits(n // 1000) + ' Thousand')
        n %= 1000
    if n > 0:
        parts.append(three_digits(n))

    return ' '.join(parts).strip()


# ---------------------------------------------------------------------------
#  Styles
# ---------------------------------------------------------------------------

def _get_styles():
    """Return a dict of ParagraphStyles used in the invoice."""
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'InvTitle', parent=base['Heading1'],
            fontSize=14, alignment=1, spaceAfter=4, textColor=colors.HexColor('#222222'),
        ),
        'company': ParagraphStyle(
            'Company', parent=base['Normal'],
            fontSize=12, textColor=colors.HexColor('#d62828'), leading=14,
            alignment=2,  # right-align
        ),
        'normal': ParagraphStyle(
            'InvNormal', parent=base['Normal'],
            fontSize=9, leading=12,
        ),
        'normal_right': ParagraphStyle(
            'InvNormalR', parent=base['Normal'],
            fontSize=9, leading=12, alignment=2,
        ),
        'bold': ParagraphStyle(
            'InvBold', parent=base['Normal'],
            fontSize=9, leading=12, fontName='Helvetica-Bold',
        ),
        'bold_right': ParagraphStyle(
            'InvBoldR', parent=base['Normal'],
            fontSize=9, leading=12, fontName='Helvetica-Bold', alignment=2,
        ),
        'small': ParagraphStyle(
            'InvSmall', parent=base['Normal'],
            fontSize=8, leading=10, textColor=colors.HexColor('#555555'),
        ),
        'terms': ParagraphStyle(
            'InvTerms', parent=base['Normal'],
            fontSize=8, leading=11,
        ),
    }


# ---------------------------------------------------------------------------
#  Table helpers
# ---------------------------------------------------------------------------

_HEADER_BG = colors.HexColor('#faefef')
_BORDER = colors.HexColor('#cccccc')


def _header_table_style():
    """Style for the item / HSN header tables."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), _HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, _BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])


# ---------------------------------------------------------------------------
#  Main PDF builder
# ---------------------------------------------------------------------------

def generate_invoice_pdf(invoice):
    """Generate PDF bytes for a given Invoice instance using ReportLab (pure Python)."""

    items = list(invoice.items.all())
    customer = invoice.customer
    styles = _get_styles()

    # Company settings
    company_name = getattr(settings, 'INVOICE_COMPANY_NAME', 'JMS Advisory')
    company_address = getattr(settings, 'INVOICE_COMPANY_ADDRESS', '')
    company_gst = getattr(settings, 'INVOICE_COMPANY_GST', '')
    company_phone = getattr(settings, 'INVOICE_COMPANY_PHONE', '')
    company_email = getattr(settings, 'INVOICE_COMPANY_EMAIL', '')

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'invoices', 'jms_logo.png')
    if not os.path.exists(logo_path):
        logo_path = None

    # HSN summary
    hsn_map = defaultdict(lambda: {'taxable': 0, 'tax_pct': 0})
    for item in items:
        taxable = float(item.quantity) * float(item.unit_price)
        hsn_map[item.hsn_code]['taxable'] += taxable
        hsn_map[item.hsn_code]['tax_pct'] = int(item.tax_percentage)

    hsn_summary = []
    hsn_total_taxable = 0
    hsn_total_cgst = 0
    hsn_total_sgst = 0
    hsn_total_tax = 0

    for code, entry in hsn_map.items():
        cgst_pct = entry['tax_pct'] / 2
        sgst_pct = entry['tax_pct'] / 2
        cgst_amt = entry['taxable'] * cgst_pct / 100
        sgst_amt = entry['taxable'] * sgst_pct / 100
        total_tax = cgst_amt + sgst_amt
        hsn_summary.append({
            'code': code, 'taxable': entry['taxable'],
            'cgst_pct': cgst_pct, 'cgst_amt': cgst_amt,
            'sgst_pct': sgst_pct, 'sgst_amt': sgst_amt,
            'total_tax': total_tax,
        })
        hsn_total_taxable += entry['taxable']
        hsn_total_cgst += cgst_amt
        hsn_total_sgst += sgst_amt
        hsn_total_tax += total_tax

    amount_in_words = number_to_words(float(invoice.grand_total))
    tax_in_words = number_to_words(float(invoice.tax_total))

    # ---- Build flowables ----
    elements = []
    page_w = A4[0] - 30 * mm  # usable width (15 mm margins each side)

    # -- Header (logo + company info) --
    logo_cell = ''
    if logo_path:
        try:
            logo_cell = Image(logo_path, width=22 * mm, height=22 * mm)
        except Exception:
            logo_cell = ''

    company_block = Paragraph(
        f'<b>{company_name}</b><br/>'
        f'<font size="8">GSTIN: {company_gst}</font><br/>'
        f'<font size="8">{company_phone} | {company_email}</font><br/>'
        f'<font size="8">{company_address}</font>',
        styles['normal_right'],
    )

    header_data = [[logo_cell, company_block]]
    header_table = Table(header_data, colWidths=[25 * mm, page_w - 25 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, _BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    # -- Title --
    elements.append(Paragraph('TAX INVOICE', styles['title']))
    elements.append(Spacer(1, 3 * mm))

    # -- Billing / Shipping box --
    billing_text = (
        f'<b>Invoice No:</b> {invoice.invoice_number}<br/>'
        f'<b>Invoice Date:</b> {invoice.billing_date}<br/><br/>'
        f'<b>Bill To:</b><br/>'
        f'<b>Customer:</b> {customer.name}<br/>'
        f'{invoice.billing_to or ""}<br/>'
        f'<b>GSTIN:</b> {getattr(customer, "gst_number", "N/A") or "N/A"}<br/>'
        f'<b>Contact Person:</b> {getattr(customer, "contact_person_1", "N/A") or "N/A"}<br/>'
        f'<b>Contact Number:</b> {getattr(customer, "contact_number", "N/A") or "N/A"}'
    )
    shipping_text = (
        f'<b>Order Date:</b> {invoice.order_date}<br/>'
        f'<b>Order Reference:</b> {invoice.order_reference or "N/A"}<br/><br/>'
        f'<b>Ship To:</b><br/>'
        f'{invoice.shipping_to or invoice.billing_to or ""}'
    )
    if invoice.note:
        shipping_text += f'<br/><br/><b>Note:</b> {invoice.note}'

    bill_ship_data = [[
        Paragraph(billing_text, styles['normal']),
        Paragraph(shipping_text, styles['normal']),
    ]]
    bill_ship_table = Table(bill_ship_data, colWidths=[page_w / 2, page_w / 2])
    bill_ship_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, _BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(bill_ship_table)
    elements.append(Spacer(1, 4 * mm))

    # -- Items table --
    col_widths = [
        page_w * 0.05,  # Sr
        page_w * 0.28,  # Description
        page_w * 0.12,  # HSN
        page_w * 0.07,  # Qty
        page_w * 0.08,  # Unit
        page_w * 0.14,  # Unit Price
        page_w * 0.08,  # Tax
        page_w * 0.18,  # Amount
    ]
    item_header = ['Sr.', 'Description', 'HSN', 'Qty', 'Unit', 'Unit Price', 'Tax', 'Amount']
    item_rows = [item_header]

    for idx, item in enumerate(items, 1):
        desc = str(item.description)
        if item.note_for_product:
            desc += f'\n({item.note_for_product})'
        item_rows.append([
            str(idx),
            Paragraph(desc.replace('\n', '<br/>'), styles['small']),
            str(item.hsn_code),
            str(item.quantity),
            str(item.unit),
            f'{float(item.unit_price):,.2f}',
            f'{item.tax_percentage}%',
            f'{float(item.amount):,.2f}',
        ])

    # Total row
    item_rows.append([
        '', Paragraph('<b>Total:</b>', styles['normal']),
        '', '', '', '', '',
        Paragraph(f'<b>{float(invoice.grand_total):,.2f}</b>', styles['normal']),
    ])

    item_table = Table(item_rows, colWidths=col_widths, repeatRows=1)
    ts = _header_table_style()
    # Bold the last row
    last_row = len(item_rows) - 1
    ts.add('FONTNAME', (0, last_row), (-1, last_row), 'Helvetica-Bold')
    item_table.setStyle(ts)
    elements.append(item_table)
    elements.append(Spacer(1, 3 * mm))

    # -- Amount in words --
    elements.append(Paragraph(
        f'<b>Total Amount (in words):</b> INR {amount_in_words} only', styles['normal']
    ))
    elements.append(Spacer(1, 4 * mm))

    # -- HSN table --
    elements.append(Paragraph('<b>HSN-wise Tax Breakdown:</b>', styles['normal']))
    elements.append(Spacer(1, 2 * mm))

    hsn_col_widths = [
        page_w * 0.14, page_w * 0.16, page_w * 0.10,
        page_w * 0.16, page_w * 0.10, page_w * 0.16, page_w * 0.18,
    ]
    hsn_header = ['HSN/SAC', 'Taxable', 'CGST %', 'CGST Amt', 'SGST %', 'SGST Amt', 'Total Tax']
    hsn_rows = [hsn_header]
    for h in hsn_summary:
        hsn_rows.append([
            str(h['code']),
            f"{h['taxable']:,.2f}",
            f"{h['cgst_pct']:.1f}%",
            f"{h['cgst_amt']:,.2f}",
            f"{h['sgst_pct']:.1f}%",
            f"{h['sgst_amt']:,.2f}",
            f"{h['total_tax']:,.2f}",
        ])
    hsn_rows.append([
        'Total',
        f'{hsn_total_taxable:,.2f}', '',
        f'{hsn_total_cgst:,.2f}', '',
        f'{hsn_total_sgst:,.2f}',
        f'{hsn_total_tax:,.2f}',
    ])

    hsn_table = Table(hsn_rows, colWidths=hsn_col_widths, repeatRows=1)
    hsn_ts = _header_table_style()
    hsn_last = len(hsn_rows) - 1
    hsn_ts.add('FONTNAME', (0, hsn_last), (-1, hsn_last), 'Helvetica-Bold')
    hsn_table.setStyle(hsn_ts)
    elements.append(hsn_table)
    elements.append(Spacer(1, 3 * mm))

    # -- Tax in words --
    elements.append(Paragraph(
        f'<b>Tax Amount (in words):</b> INR {tax_in_words} only', styles['normal']
    ))
    elements.append(Spacer(1, 4 * mm))

    # -- Terms & Conditions --
    payment_terms = invoice.payment_terms or '_______________________________'
    terms_text = (
        f'<b>Terms &amp; Conditions</b><br/>'
        f'Payment Terms: {payment_terms}<br/>'
        f'Bank A/c: Nyra Enterprise<br/>'
        f'Kotak Mahindra Bank<br/>'
        f'A/c No.: 6450832888<br/>'
        f'IFSC: KKBK0002573 (Vastrapur Branch)<br/><br/>'
        f'<b>Declaration:</b> This invoice reflects the actual price of goods sold. '
        f'All particulars are true.'
    )
    elements.append(Paragraph(terms_text, styles['terms']))
    elements.append(Spacer(1, 12 * mm))

    # -- Signature --
    sig_data = [['', 'Authorised Signatory']]
    sig_table = Table(sig_data, colWidths=[page_w * 0.65, page_w * 0.35])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, 0), 9),
        ('LINEABOVE', (1, 0), (1, 0), 0.5, colors.black),
        ('TOPPADDING', (1, 0), (1, 0), 4),
    ]))
    elements.append(sig_table)

    # ---- Render to bytes ----
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    doc.build(elements)
    return buf.getvalue()
