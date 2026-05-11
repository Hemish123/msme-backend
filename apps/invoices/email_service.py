import threading
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from apps.invoices.pdf_generator import generate_invoice_pdf


class InvoiceEmailService:
    """Service for sending invoice emails with PDF attachments."""

    def send_invoice_email(self, invoice, is_reminder=False):
        """Send invoice email with PDF attachment."""
        try:
            pdf_bytes = generate_invoice_pdf(invoice)
            user = getattr(invoice, 'user', None)
            company = user.company_name if user and user.company_name else getattr(settings, 'INVOICE_COMPANY_NAME', 'Your Company')
            contact_email = user.company_email if user and user.company_email else settings.DEFAULT_FROM_EMAIL

            if is_reminder:
                subject = f"Reminder: Invoice #{invoice.invoice_number} from {company} is due"
                intro_text = f"This is a gentle reminder regarding your invoice #{invoice.invoice_number} which is currently pending.\n\n"
            else:
                subject = f"Invoice #{invoice.invoice_number} from {company}"
                intro_text = f"Please find attached your invoice #{invoice.invoice_number}.\n\n"

            body = (
                f"Dear {invoice.customer.name},\n\n"
                f"{intro_text}"
                f"Invoice Details:\n"
                f"  Invoice Number : {invoice.invoice_number}\n"
                f"  Billing Date   : {invoice.billing_date}\n"
                f"  Payment Terms  : {invoice.payment_terms or 'N/A'}\n"
                f"  Grand Total    : ₹{invoice.grand_total}\n\n"
                f"Kindly make the payment within the agreed terms.\n\n"
                f"For queries, reach us at {contact_email}.\n\n"
                f"Thank you for your business!\n\n"
                f"Best regards,\n{company}"
            )

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invoice.customer.email],
            )
            email.attach(
                f"Invoice_{invoice.invoice_number.replace('/', '-')}.pdf",
                pdf_bytes,
                'application/pdf'
            )
            email.send(fail_silently=False)

            invoice.email_sent = True
            invoice.email_sent_at = timezone.now()
            invoice.status = 'SENT'
            invoice.save(update_fields=['email_sent', 'email_sent_at', 'status'])

        except Exception as e:
            print(f"[InvoiceEmail] Failed to send email for {invoice.invoice_number}: {e}")

    def send_async(self, invoice):
        """Fire-and-forget in a daemon thread — doesn't block the API response."""
        t = threading.Thread(target=self.send_invoice_email, args=[invoice])
        t.daemon = True
        t.start()
