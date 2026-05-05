from django.db import models
from django.conf import settings


class Customer(models.Model):
    """Customer of an MSME business."""
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    company = models.CharField(max_length=255, blank=True, default='')
    gstin = models.CharField(max_length=15, blank=True, default='', verbose_name='GSTIN')
    address = models.TextField(blank=True, default='')
    msme_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Zoho Books-style fields (Invoice module unification) ────────────────

    customer_type = models.CharField(
        max_length=20,
        choices=[('Business', 'Business'), ('Individual', 'Individual')],
        default='Business'
    )
    salutation = models.CharField(
        max_length=10,
        choices=[('Mr.', 'Mr.'), ('Mrs.', 'Mrs.'), ('Ms.', 'Ms.'),
                 ('Dr.', 'Dr.'), ('Prof.', 'Prof.')],
        blank=True, default=''
    )
    first_name = models.CharField(max_length=100, blank=True, default='')
    last_name = models.CharField(max_length=100, blank=True, default='')
    display_name = models.CharField(max_length=255, blank=True, default='')
    work_phone = models.CharField(max_length=20, blank=True, default='')
    mobile = models.CharField(max_length=20, blank=True, default='')
    customer_language = models.CharField(max_length=50, default='English')

    # GST / Tax fields
    gst_treatment = models.CharField(
        max_length=50,
        choices=[
            ('Registered Business - Regular', 'Registered Business - Regular'),
            ('Registered Business - Composition', 'Registered Business - Composition'),
            ('Unregistered Business', 'Unregistered Business'),
            ('Consumer', 'Consumer'),
            ('Overseas', 'Overseas'),
            ('Special Economic Zone', 'Special Economic Zone'),
            ('Deemed Export', 'Deemed Export'),
        ],
        blank=True, default=''
    )
    place_of_supply = models.CharField(max_length=100, blank=True, default='')
    pan_number = models.CharField(max_length=10, blank=True, default='')
    tax_preference = models.CharField(
        max_length=20,
        choices=[('Taxable', 'Taxable'), ('Tax Exempt', 'Tax Exempt')],
        default='Taxable'
    )
    currency = models.CharField(max_length=10, default='INR')
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    payment_terms_days = models.IntegerField(default=0)  # 0 = Due on Receipt

    # Billing Address
    billing_attention = models.CharField(max_length=100, blank=True, default='')
    billing_country = models.CharField(max_length=100, blank=True, default='India')
    billing_street1 = models.CharField(max_length=255, blank=True, default='')
    billing_street2 = models.CharField(max_length=255, blank=True, default='')
    billing_city = models.CharField(max_length=100, blank=True, default='')
    billing_state = models.CharField(max_length=100, blank=True, default='')
    billing_zip = models.CharField(max_length=10, blank=True, default='')

    # Shipping Address
    shipping_attention = models.CharField(max_length=100, blank=True, default='')
    shipping_country = models.CharField(max_length=100, blank=True, default='India')
    shipping_street1 = models.CharField(max_length=255, blank=True, default='')
    shipping_street2 = models.CharField(max_length=255, blank=True, default='')
    shipping_city = models.CharField(max_length=100, blank=True, default='')
    shipping_state = models.CharField(max_length=100, blank=True, default='')
    shipping_zip = models.CharField(max_length=10, blank=True, default='')

    # Contact Persons (stored as JSON array)
    contact_persons = models.JSONField(default=list, blank=True)
    # Format: [{"salutation":"Mr.","first_name":"John","last_name":"Doe",
    #            "email":"john@co.com","work_phone":"+91...","mobile":"+91..."}]

    # Legacy invoice-module fields
    contact_person_2 = models.CharField(max_length=100, blank=True, default='')

    # Remarks / internal notes
    remarks = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']
        unique_together = ['name', 'msme_owner']

    def __str__(self):
        return f"{self.name} ({self.company})" if self.company else self.name


class PaymentRecord(models.Model):
    """Individual payment/invoice record for a customer."""
    STATUS_CHOICES = [
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partial'),
        ('OVERDUE', 'Overdue'),
        ('PENDING', 'Pending'),
        ('LATE', 'Late'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='payment_records'
    )
    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_date = models.DateField(null=True, blank=True)
    days_late = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-invoice_date']

    def save(self, *args, **kwargs):
        if self.paid_date and self.due_date:
            self.days_late = max(0, (self.paid_date - self.due_date).days)
        if self.paid_date:
            if self.paid_amount >= self.amount:
                self.status = 'LATE' if self.days_late > 0 else 'PAID'
            else:
                self.status = 'PARTIAL'
        elif self.due_date:
            from django.utils import timezone
            if self.due_date < timezone.now().date():
                self.status = 'OVERDUE'
            else:
                self.status = 'PENDING'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"
