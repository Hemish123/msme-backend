from rest_framework import serializers
from .models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = '__all__'
        read_only_fields = ['id', 'days_late', 'status', 'created_at']


class PaymentRecordListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = PaymentRecord
        fields = ['id', 'customer', 'customer_name', 'invoice_number', 'invoice_date',
                  'due_date', 'amount', 'paid_amount', 'paid_date', 'days_late',
                  'status', 'created_at']


class PaymentAnalyticsMiniSerializer(serializers.ModelSerializer):
    tier = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAnalytics
        fields = ['total_invoices', 'total_amount', 'total_paid', 'on_time_count',
                  'late_count', 'overdue_count', 'avg_days_late', 'payment_score', 'last_payment_date', 'tier']

    def get_tier(self, obj):
        return PaymentAnalytics.get_tier(obj.payment_score)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'phone', 'company', 'gstin',
            'address', 'created_at', 'updated_at',
            # Zoho-style fields
            'customer_type', 'salutation', 'first_name', 'last_name',
            'display_name', 'work_phone', 'mobile', 'customer_language',
            # GST / Tax
            'gst_treatment', 'place_of_supply', 'pan_number',
            'tax_preference', 'currency', 'opening_balance', 'payment_terms_days',
            # Billing Address
            'billing_attention', 'billing_country', 'billing_street1',
            'billing_street2', 'billing_city', 'billing_state', 'billing_zip',
            # Shipping Address
            'shipping_attention', 'shipping_country', 'shipping_street1',
            'shipping_street2', 'shipping_city', 'shipping_state', 'shipping_zip',
            # Contact Persons
            'contact_persons', 'contact_person_2',
            # Remarks
            'remarks',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        request = self.context.get('request')
        if request and request.user:
            qs = Customer.objects.filter(name__iexact=value, msme_owner=request.user)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError("A customer with this exact name already exists in your account.")
        return value


class CustomerListSerializer(serializers.ModelSerializer):
    analytics = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'company', 'gstin',
                  'created_at', 'analytics']

    def get_analytics(self, obj):
        try:
            pa = obj.analytics
            return PaymentAnalyticsMiniSerializer(pa).data
        except PaymentAnalytics.DoesNotExist:
            return {
                'total_invoices': 0,
                'total_amount': '0',
                'total_paid': '0',
                'on_time_count': 0,
                'late_count': 0,
                'overdue_count': 0,
                'avg_days_late': 0,
                'payment_score': 50,
                'last_payment_date': None,
                'tier': 'SILVER'
            }



class CustomerDetailSerializer(serializers.ModelSerializer):
    analytics = PaymentAnalyticsMiniSerializer(read_only=True)
    recent_payments = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'phone', 'company', 'gstin',
            'address', 'created_at', 'updated_at', 'analytics', 'recent_payments',
            # Zoho-style fields
            'customer_type', 'salutation', 'first_name', 'last_name',
            'display_name', 'work_phone', 'mobile', 'customer_language',
            # GST / Tax
            'gst_treatment', 'place_of_supply', 'pan_number',
            'tax_preference', 'currency', 'opening_balance', 'payment_terms_days',
            # Billing Address
            'billing_attention', 'billing_country', 'billing_street1',
            'billing_street2', 'billing_city', 'billing_state', 'billing_zip',
            # Shipping Address
            'shipping_attention', 'shipping_country', 'shipping_street1',
            'shipping_street2', 'shipping_city', 'shipping_state', 'shipping_zip',
            # Contact Persons
            'contact_persons', 'contact_person_2',
            # Remarks
            'remarks',
        ]

    def get_recent_payments(self, obj):
        records = obj.payment_records.all()[:10]
        return PaymentRecordListSerializer(records, many=True).data


class CustomerDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invoice/inventory customer dropdowns."""
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'gstin', 'display_name',
            'billing_street1', 'billing_city', 'billing_state',
            'billing_zip', 'billing_country', 'address',
            'shipping_street1', 'shipping_city', 'shipping_state',
            'shipping_zip', 'shipping_country',
        ]


class CustomerSummarySerializer(serializers.Serializer):
    customer = CustomerSerializer()
    analytics = PaymentAnalyticsMiniSerializer()
    credit_days = serializers.IntegerField()
    tier = serializers.CharField()
