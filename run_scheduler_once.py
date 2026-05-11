import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.invoices.scheduler import process_scheduled_reminders
process_scheduled_reminders()
print("Processed reminders!")
