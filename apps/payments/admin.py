from django.contrib import admin
from .models import CreditTimeline, PaymentAnalytics


@admin.register(CreditTimeline)
class CreditTimelineAdmin(admin.ModelAdmin):
    list_display = ['customer', 'tier', 'credit_days', 'score', 'assigned_by', 'assigned_at', 'valid_until']
    search_fields = ['customer__name']
    list_filter = ['tier', 'credit_days', 'assigned_at']
    ordering = ['-assigned_at']


@admin.register(PaymentAnalytics)
class PaymentAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['customer', 'total_invoices', 'total_amount', 'total_paid',
                    'on_time_count', 'late_count', 'avg_days_late', 'payment_score']
    search_fields = ['customer__name']
    list_filter = ['payment_score']
    ordering = ['-payment_score']
