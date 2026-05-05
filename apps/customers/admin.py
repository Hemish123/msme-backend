from django.contrib import admin
from .models import Customer, PaymentRecord


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email', 'phone', 'gstin', 'customer_type',
                    'gst_treatment', 'place_of_supply', 'msme_owner', 'created_at']
    search_fields = ['name', 'company', 'email', 'gstin', 'display_name',
                     'first_name', 'last_name', 'pan_number']
    list_filter = ['created_at', 'msme_owner', 'customer_type', 'gst_treatment',
                   'tax_preference', 'currency']
    ordering = ['name']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'email', 'phone', 'company', 'msme_owner',
                       'customer_type', 'salutation', 'first_name', 'last_name',
                       'display_name', 'work_phone', 'mobile', 'customer_language')
        }),
        ('GST / Tax', {
            'fields': ('gstin', 'gst_treatment', 'place_of_supply', 'pan_number',
                       'tax_preference', 'currency', 'opening_balance', 'payment_terms_days')
        }),
        ('Billing Address', {
            'fields': ('billing_attention', 'billing_country', 'billing_street1',
                       'billing_street2', 'billing_city', 'billing_state', 'billing_zip'),
            'classes': ('collapse',)
        }),
        ('Shipping Address', {
            'fields': ('shipping_attention', 'shipping_country', 'shipping_street1',
                       'shipping_street2', 'shipping_city', 'shipping_state', 'shipping_zip'),
            'classes': ('collapse',)
        }),
        ('Contact & Notes', {
            'fields': ('address', 'contact_persons', 'contact_person_2', 'remarks'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'invoice_date', 'due_date',
                    'amount', 'paid_amount', 'status', 'days_late']
    search_fields = ['invoice_number', 'customer__name']
    list_filter = ['status', 'invoice_date']
    ordering = ['-invoice_date']
