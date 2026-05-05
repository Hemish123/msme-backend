import os
from collections import defaultdict
from django.template.loader import render_to_string
from django.conf import settings


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


def generate_invoice_pdf(invoice):
    """Generate PDF bytes for a given Invoice instance."""
    import weasyprint  # Lazy import

    items = list(invoice.items.all())
    customer = invoice.customer

    # Build HSN summary (CGST/SGST split)
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
            'code': code,
            'taxable': entry['taxable'],
            'cgst_pct': cgst_pct,
            'cgst_amt': cgst_amt,
            'sgst_pct': sgst_pct,
            'sgst_amt': sgst_amt,
            'total_tax': total_tax,
        })

        hsn_total_taxable += entry['taxable']
        hsn_total_cgst += cgst_amt
        hsn_total_sgst += sgst_amt
        hsn_total_tax += total_tax

    # Amount in words
    amount_in_words = number_to_words(float(invoice.grand_total))
    tax_in_words = number_to_words(float(invoice.tax_total))

    # Logo path
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'invoices', 'jms_logo.png')
    if not os.path.exists(logo_path):
        logo_path = ''

    context = {
        'invoice': invoice,
        'items': items,
        'customer': customer,
        'company_name': getattr(settings, 'INVOICE_COMPANY_NAME', 'JMS Advisory'),
        'company_address': getattr(settings, 'INVOICE_COMPANY_ADDRESS', ''),
        'company_gst': getattr(settings, 'INVOICE_COMPANY_GST', ''),
        'company_phone': getattr(settings, 'INVOICE_COMPANY_PHONE', ''),
        'company_email': getattr(settings, 'INVOICE_COMPANY_EMAIL', ''),
        'logo_path': logo_path,
        'hsn_summary': hsn_summary,
        'hsn_total_taxable': hsn_total_taxable,
        'hsn_total_cgst': hsn_total_cgst,
        'hsn_total_sgst': hsn_total_sgst,
        'hsn_total_tax': hsn_total_tax,
        'amount_in_words': amount_in_words,
        'tax_in_words': tax_in_words,
    }
    html_string = render_to_string('invoices/invoice_pdf.html', context)
    return weasyprint.HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()
