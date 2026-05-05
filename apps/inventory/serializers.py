from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True, default='')

    class Meta:
        model = InventoryItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InventoryDropdownSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invoice form product dropdown."""
    class Meta:
        model = InventoryItem
        fields = ['id', 'product_name', 'hsn_code', 'unit', 'unit_price', 'tax_percentage']
