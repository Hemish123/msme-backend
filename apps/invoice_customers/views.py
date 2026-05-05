from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import InvoiceCustomer
from .serializers import InvoiceCustomerSerializer, InvoiceCustomerDropdownSerializer
from apps.customers.models import Customer


class InvoiceCustomerListCreateView(generics.ListCreateAPIView):
    """List all invoice customers or create a new one."""
    serializer_class = InvoiceCustomerSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'email', 'gst_number']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return InvoiceCustomer.objects.filter(is_active=True, user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InvoiceCustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an invoice customer."""
    serializer_class = InvoiceCustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InvoiceCustomer.objects.filter(user=self.request.user)


class InvoiceCustomerDropdownView(APIView):
    """
    Lightweight list for dropdowns — now uses unified Customer model.
    This endpoint is kept for backwards compatibility during transition.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customers = Customer.objects.filter(msme_owner=request.user).order_by('name')
        data = []
        for c in customers:
            # Build a billing address string from address fields
            addr_parts = [p for p in [c.billing_street1, c.billing_street2,
                                       c.billing_city, c.billing_state,
                                       c.billing_zip] if p]
            registered_address = ', '.join(addr_parts) if addr_parts else c.address

            data.append({
                'id': c.id,
                'name': c.display_name or c.name,
                'email': c.email,
                'registered_address': registered_address,
                'gst_number': c.gstin,
            })
        return Response(data)
