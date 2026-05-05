from datetime import date
from apps.invoices.models import Invoice


def generate_invoice_number():
    """Generate the next invoice number in Indian fiscal year format (e.g. 25-26/001)."""
    today = date.today()
    # Indian fiscal year: April 1 – March 31
    if today.month >= 4:
        fy_start, fy_end = today.year, today.year + 1
    else:
        fy_start, fy_end = today.year - 1, today.year

    prefix = f"{str(fy_start)[2:]}-{str(fy_end)[2:]}"  # e.g. "25-26"

    last = Invoice.objects.filter(
        invoice_number__startswith=prefix
    ).order_by('-created_at').first()

    if last:
        try:
            next_seq = int(last.invoice_number.split('/')[1]) + 1
        except (IndexError, ValueError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}/{next_seq:03d}"
