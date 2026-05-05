from django.db import models
from apps.customers.models import Customer

UNIT_CHOICES = [
    ('Nos', 'Nos'), ('Kg', 'Kg'), ('Ltr', 'Ltr'), ('Mtr', 'Mtr'),
    ('Box', 'Box'), ('Pcs', 'Pcs'), ('Set', 'Set'), ('Pair', 'Pair'),
    ('Dozen', 'Dozen'), ('Other', 'Other'),
]

TAX_CHOICES = [(0, '0%'), (5, '5%'), (12, '12%'), (18, '18%'), (28, '28%')]


from django.conf import settings

class InventoryItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inventory_items'
    )
    product_name = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=20)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='Nos')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    tax_percentage = models.IntegerField(choices=TAX_CHOICES, default=18)
    stock_quantity = models.IntegerField(default=0)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'inventory'
        ordering = ['product_name']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'

    def __str__(self):
        return self.product_name
