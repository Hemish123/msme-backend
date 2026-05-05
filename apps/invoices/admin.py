from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'billing_date', 'grand_total',
                    'status', 'email_sent', 'created_at']
    list_filter = ['status', 'email_sent', 'billing_date']
    search_fields = ['invoice_number', 'customer__name']
    ordering = ['-created_at']
    inlines = [InvoiceItemInline]
    readonly_fields = ['subtotal', 'tax_total', 'grand_total', 'email_sent',
                       'email_sent_at', 'created_at', 'updated_at']
