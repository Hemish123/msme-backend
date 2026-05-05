from django.contrib import admin
from .models import InvoiceCustomer


@admin.register(InvoiceCustomer)
class InvoiceCustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'contact_number', 'gst_number', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'gst_number']
    ordering = ['-created_at']
