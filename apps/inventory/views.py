from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import InventoryItem
from .serializers import InventoryItemSerializer, InventoryDropdownSerializer


class InventoryListCreateView(generics.ListCreateAPIView):
    """List all inventory items or create a new one. Supports ?customer=<id> filter."""
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['product_name', 'hsn_code']
    ordering_fields = ['product_name', 'created_at', 'unit_price']
    filterset_fields = ['customer']

    def get_queryset(self):
        return InventoryItem.objects.filter(is_active=True, user=self.request.user).select_related('customer')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InventoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an inventory item."""
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InventoryItem.objects.filter(user=self.request.user)


class InventoryDropdownView(APIView):
    """Lightweight list for invoice form product dropdown — no pagination."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = InventoryItem.objects.filter(is_active=True, user=request.user).order_by('product_name')
        customer_id = request.query_params.get('customer')
        if customer_id:
            items = items.filter(customer_id=customer_id)
        serializer = InventoryDropdownSerializer(items, many=True)
        return Response(serializer.data)
