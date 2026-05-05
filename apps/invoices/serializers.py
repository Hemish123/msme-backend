from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'inventory_item', 'description', 'note_for_product',
                  'hsn_code', 'quantity', 'unit', 'unit_price', 'tax_percentage', 'amount']
        read_only_fields = ['id']


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ['id', 'subtotal', 'tax_total', 'grand_total',
                            'email_sent', 'email_sent_at', 'created_at', 'updated_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)

        for item_data in items_data:
            # Calculate amount for each item
            qty = item_data.get('quantity', 1)
            price = item_data.get('unit_price', 0)
            tax_pct = item_data.get('tax_percentage', 0)
            base = qty * price
            tax_amt = base * tax_pct / 100
            item_data['amount'] = base + tax_amt
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                qty = item_data.get('quantity', 1)
                price = item_data.get('unit_price', 0)
                tax_pct = item_data.get('tax_percentage', 0)
                base = qty * price
                tax_amt = base * tax_pct / 100
                item_data['amount'] = base + tax_amt
                InvoiceItem.objects.create(invoice=instance, **item_data)

            # Recalculate totals
            subtotal = sum(item.quantity * item.unit_price for item in instance.items.all())
            tax_total = sum(item.quantity * item.unit_price * item.tax_percentage / 100 for item in instance.items.all())
            instance.subtotal = subtotal
            instance.tax_total = tax_total
            instance.grand_total = subtotal + tax_total
            instance.save(update_fields=['subtotal', 'tax_total', 'grand_total'])

        return instance


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for invoice list view."""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'customer', 'customer_name', 'customer_email',
                  'billing_date', 'grand_total', 'status', 'email_sent', 'created_at']
