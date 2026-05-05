from django.db import models


from django.conf import settings

class InvoiceCustomer(models.Model):
    """
    Invoice module customers — completely separate from MSME PayTrack Customer model.
    Used for generating invoices and sending emails.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    registered_address = models.TextField()
    contact_number = models.CharField(max_length=20)
    contact_person_1 = models.CharField(max_length=100)
    contact_person_2 = models.CharField(max_length=100, blank=True, default='')
    gst_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'invoice_customers'
        ordering = ['-created_at']
        verbose_name = 'Invoice Customer'
        verbose_name_plural = 'Invoice Customers'

    def __str__(self):
        return self.name
