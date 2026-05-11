from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.utils import timezone

from .models import Invoice, InvoiceItem
from .serializers import InvoiceSerializer, InvoiceListSerializer
from .number_generator import generate_invoice_number
from .pdf_generator import generate_invoice_pdf
from .pdf_templates import TEMPLATE_INFO
from .email_service import InvoiceEmailService
from apps.customers.models import Customer

class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).select_related('customer')
    search_fields = ['invoice_number', 'customer__name']
    ordering_fields = ['created_at', 'grand_total', 'billing_date']


class InvoiceCreateView(generics.CreateAPIView):
    """Create a new invoice with items. Triggers async email with PDF."""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("[InvoiceCreate] Validation errors: %s" % serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        invoice = serializer.save(user=request.user)

        # Calculate totals from items
        subtotal = sum(item.quantity * item.unit_price for item in invoice.items.all())
        tax_total = sum(
            item.quantity * item.unit_price * item.tax_percentage / 100
            for item in invoice.items.all()
        )
        invoice.subtotal = subtotal
        invoice.tax_total = tax_total
        invoice.grand_total = subtotal + tax_total
        invoice.save(update_fields=['subtotal', 'tax_total', 'grand_total'])

        # Send email async (non-blocking)
        try:
            InvoiceEmailService().send_async(invoice)
        except Exception as e:
            print("[InvoiceCreate] Email send failed: %s" % e)

        return Response({
            'success': True,
            'message': 'Invoice %s created. Email sent to %s.' % (invoice.invoice_number, invoice.customer.email),
            'data': InvoiceSerializer(invoice).data
        }, status=status.HTTP_201_CREATED)

class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).select_related('customer').prefetch_related('items')


class NextInvoiceNumberView(APIView):
    """Return the next auto-generated invoice number."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'invoice_number': generate_invoice_number()})


class InvoicePDFView(APIView):
    """Download invoice as PDF."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        # Allow template override via query param (for preview)
        template_key = request.query_params.get('template', None)
        pdf_bytes = generate_invoice_pdf(invoice, template_key=template_key)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            'attachment; filename="Invoice_%s.pdf"' % invoice.invoice_number.replace("/", "-")
        )
        return response


class InvoiceTemplatesView(APIView):
    """Return list of available invoice templates."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(TEMPLATE_INFO)


class ResendInvoiceEmailView(APIView):
    """Resend invoice email manually."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        if invoice.status == 'PAID':
            return Response({
                'success': False,
                'message': 'Cannot resend email for a PAID invoice.'
            }, status=status.HTTP_400_BAD_REQUEST)
        InvoiceEmailService().send_async(invoice)
        return Response({
            'success': True,
            'message': 'Email resent to %s.' % invoice.customer.email
        })


class InvoiceStatsView(APIView):
    """Dashboard statistics for the invoice module — enhanced with recent_invoices and month stats."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_invoices = Invoice.objects.filter(user=request.user)

        total_invoices = user_invoices.count()
        total_revenue = user_invoices.filter(
            status='PAID'
        ).aggregate(total=Sum('grand_total'))['total'] or 0
        pending_amount = user_invoices.exclude(
            status='PAID'
        ).aggregate(total=Sum('grand_total'))['total'] or 0
        total_customers = Customer.objects.filter(msme_owner=request.user).count()

        # Month stats
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_invoices = user_invoices.filter(created_at__gte=month_start)
        month_revenue = month_invoices.aggregate(
            total=Sum('grand_total'))['total'] or 0
        month_paid = month_invoices.filter(
            status='PAID').aggregate(total=Sum('grand_total'))['total'] or 0

        # Recent invoices (last 5)
        recent = user_invoices.select_related('customer').order_by('-created_at')[:5]
        recent_invoices = []
        for inv in recent:
            recent_invoices.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'customer_name': inv.customer.name if inv.customer else '',
                'billing_date': str(inv.billing_date),
                'grand_total': float(inv.grand_total),
                'status': inv.status,
                'email_sent': inv.email_sent,
                'email_sent_at': str(inv.email_sent_at) if inv.email_sent_at else None,
            })

        return Response({
            'total_invoices': total_invoices,
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'total_customers': total_customers,
            'month_revenue': float(month_revenue),
            'month_paid': float(month_paid),
            'recent_invoices': recent_invoices,
        })


class ScheduleReminderView(APIView):
    """Schedule a reminder email for an invoice."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
        if invoice.status == 'PAID':
            return Response({'error': 'Cannot schedule reminder for a paid invoice'}, status=status.HTTP_400_BAD_REQUEST)
        
        scheduled_at = request.data.get('scheduled_at')
        if not scheduled_at:
            return Response({'error': 'scheduled_at is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Parse datetime
            from dateutil import parser
            dt = parser.parse(scheduled_at)
            
            invoice.reminder_scheduled_at = dt
            invoice.reminder_sent = False
            invoice.save(update_fields=['reminder_scheduled_at', 'reminder_sent'])
            return Response({'message': 'Reminder scheduled successfully', 'scheduled_at': invoice.reminder_scheduled_at})
        except Exception as e:
            return Response({'error': f'Invalid datetime format: {e}'}, status=status.HTTP_400_BAD_REQUEST)
