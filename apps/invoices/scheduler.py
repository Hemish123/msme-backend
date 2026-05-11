import logging
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

def process_scheduled_reminders():
    """Finds and sends scheduled invoice reminders."""
    from apps.invoices.models import Invoice
    from apps.invoices.email_service import InvoiceEmailService

    # Find invoices that have a scheduled reminder time <= now
    # and have not been sent yet, and are not PAID
    now = timezone.now()
    pending_reminders = Invoice.objects.filter(
        reminder_scheduled_at__lte=now,
        reminder_sent=False
    ).exclude(status='PAID')

    if not pending_reminders.exists():
        return

    email_service = InvoiceEmailService()
    for invoice in pending_reminders:
        try:
            logger.info(f"Sending scheduled reminder for invoice {invoice.invoice_number}")
            email_service.send_invoice_email(invoice, is_reminder=True)
            # Mark as sent
            invoice.reminder_sent = True
            invoice.save(update_fields=['reminder_sent'])
        except Exception as e:
            logger.error(f"Failed to send reminder for invoice {invoice.invoice_number}: {e}")

def start_scheduler():
    """Start the APScheduler for background tasks."""
    scheduler = BackgroundScheduler()
    
    # Run every 1 minute
    scheduler.add_job(
        process_scheduled_reminders,
        trigger=IntervalTrigger(minutes=1),
        id='process_scheduled_reminders',
        name='Send scheduled invoice reminders',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Invoice Reminder Scheduler started.")
