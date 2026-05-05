from django.contrib import admin
from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'hsn_code', 'unit', 'unit_price', 'tax_percentage',
                    'stock_quantity', 'customer', 'is_active']
    list_filter = ['unit', 'tax_percentage', 'is_active', 'customer']
    search_fields = ['product_name', 'hsn_code']
    ordering = ['product_name']
