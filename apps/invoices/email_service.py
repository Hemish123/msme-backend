import threading
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from apps.invoices.pdf_generator import generate_invoice_pdf


class InvoiceEmailService:
    """Service for sending invoice emails with PDF attachments."""

    def send_invoice_email(self, invoice):
        """Send invoice email with PDF attachment."""
        try:
            pdf_bytes = generate_invoice_pdf(invoice)
            company = getattr(settings, 'INVOICE_COMPANY_NAME', 'Your Company')

            subject = f"Invoice #{invoice.invoice_number} from {company}"
            body = (
                f"Dear {invoice.customer.name},\n\n"
                f"Please find attached your invoice #{invoice.invoice_number}.\n\n"
                f"Invoice Details:\n"
                f"  Invoice Number : {invoice.invoice_number}\n"
                f"  Billing Date   : {invoice.billing_date}\n"
                f"  Payment Terms  : {invoice.payment_terms or 'N/A'}\n"
                f"  Grand Total    : ₹{invoice.grand_total}\n\n"
                f"Kindly make the payment within the agreed terms.\n\n"
                f"For queries, reach us at {settings.DEFAULT_FROM_EMAIL}.\n\n"
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
