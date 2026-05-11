from django.db import models
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem

INVOICE_STATUS = [
    ('DRAFT', 'Draft'), ('SENT', 'Sent'),
    ('PAID', 'Paid'), ('OVERDUE', 'Overdue'),
]

TEMPLATE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('elegant', 'Elegant'),
    ('minimal', 'Minimal'),
]


from django.conf import settings

class Invoice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    invoice_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='invoices'
    )
    order_date = models.DateField()
    billing_date = models.DateField()
    billing_to = models.TextField(blank=True, default='')
    shipping_to = models.TextField(blank=True, default='')
    order_reference = models.CharField(max_length=100, blank=True, default='')
    payment_terms = models.CharField(max_length=100, blank=True, default='')
    note = models.TextField(blank=True, default='')
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='DRAFT')
    template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='classic')
    reminder_scheduled_at = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'invoices'
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Sync to PaymentRecord
        from apps.customers.models import PaymentRecord
        from apps.customers.bulk_upload import _recompute_analytics
        from django.utils import timezone
        import datetime
        
        status_map = {
            'DRAFT': 'PENDING',
            'SENT': 'PENDING',
            'PAID': 'PAID',
            'OVERDUE': 'OVERDUE'
        }
        
        if self.status != 'DRAFT':
            # Try to calculate a due_date based on payment_terms
            due_date = self.billing_date
            if self.payment_terms and 'Net' in self.payment_terms:
                try:
                    days = int(''.join(filter(str.isdigit, self.payment_terms)))
                    due_date = self.billing_date + datetime.timedelta(days=days)
                except ValueError:
                    pass
            
            pr, created = PaymentRecord.objects.update_or_create(
                customer=self.customer,
                invoice_number=self.invoice_number,
                defaults={
                    'invoice_date': self.billing_date,
                    'due_date': due_date,
                    'amount': self.grand_total,
                    'paid_amount': self.grand_total if self.status == 'PAID' else 0,
                    'status': status_map.get(self.status, 'PENDING'),
                }
            )
            
            if self.status == 'PAID' and not pr.paid_date:
                pr.paid_date = timezone.now().date()
                pr.save()
        else:
            PaymentRecord.objects.filter(customer=self.customer, invoice_number=self.invoice_number).delete()

        _recompute_analytics(self.customer)

    def delete(self, *args, **kwargs):
        customer = self.customer
        inv_num = self.invoice_number
        super().delete(*args, **kwargs)
        
        from apps.customers.models import PaymentRecord
        from apps.customers.bulk_upload import _recompute_analytics
        
        PaymentRecord.objects.filter(customer=customer, invoice_number=inv_num).delete()
        _recompute_analytics(customer)

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items'
    )
    inventory_item = models.ForeignKey(
        InventoryItem, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoice_items'
    )
    description = models.CharField(max_length=255)
    note_for_product = models.CharField(max_length=255, blank=True, default='')
    hsn_code = models.CharField(max_length=20, blank=True, default='')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=20, blank=True, default='')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_percentage = models.IntegerField(default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        app_label = 'invoices'

    def __str__(self):
        return f"{self.description} (Invoice: {self.invoice.invoice_number})"
