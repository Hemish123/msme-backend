import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.invoices.models import Invoice
from apps.customers.models import Customer
from apps.customers.bulk_upload import _recompute_analytics

# Iterate over all customers and their invoices
customers = Customer.objects.all()
count = 0
for customer in customers:
    invoices = Invoice.objects.filter(customer=customer)
    for inv in invoices:
        inv.save() # This will trigger the save override and sync to PaymentRecord
        count += 1
    _recompute_analytics(customer)

print(f"Synced {count} invoices to PaymentRecords and recomputed analytics.")
