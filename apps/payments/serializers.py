from rest_framework import serializers
from .models import CreditTimeline, PaymentAnalytics


class CreditTimelineSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.email', read_only=True)

    class Meta:
        model = CreditTimeline
        fields = ['id', 'customer', 'customer_name', 'assigned_by', 'assigned_by_name',
                  'credit_days', 'reason', 'score', 'tier', 'assigned_at', 'valid_until']
        read_only_fields = ['id', 'assigned_at']


class PaymentAnalyticsSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    tier = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAnalytics
        fields = ['customer', 'customer_name', 'total_invoices', 'total_amount',
                  'total_paid', 'on_time_count', 'late_count', 'avg_days_late',
                  'last_payment_date', 'payment_score', 'tier', 'updated_at']

    def get_tier(self, obj):
        return PaymentAnalytics.get_tier(obj.payment_score)
