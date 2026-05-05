from rest_framework import serializers
from .models import InvoiceCustomer


class InvoiceCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceCustomer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceCustomerDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for dropdowns."""
    class Meta:
        model = InvoiceCustomer
        fields = ['id', 'name', 'email', 'registered_address', 'gst_number']
