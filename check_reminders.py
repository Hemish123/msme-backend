import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.invoices.models import Invoice
from django.utils import timezone

now = timezone.now()
print(f"Current TZ Now: {now}")

reminders = Invoice.objects.filter(reminder_scheduled_at__isnull=False)
for r in reminders:
    print(f"Invoice {r.invoice_number}: Scheduled at {r.reminder_scheduled_at}, Sent: {r.reminder_sent}, Status: {r.status}")
