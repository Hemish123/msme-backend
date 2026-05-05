from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Sum, Avg, Count, Q

from utils.response import api_response, api_error
from utils.permissions import IsOwner
from .models import Customer, PaymentRecord
from .serializers import (
    CustomerSerializer, CustomerListSerializer, CustomerDetailSerializer,
    PaymentRecordListSerializer, CustomerSummarySerializer, CustomerDropdownSerializer
)
from .filters import CustomerFilter, PaymentRecordFilter
from apps.payments.models import PaymentAnalytics, CreditTimeline
from apps.payments.serializers import CreditTimelineSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = CustomerFilter
    search_fields = ['name', 'company', 'email', 'gstin']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(
            msme_owner=self.request.user
        ).select_related('analytics').prefetch_related('payment_records')

    def perform_create(self, serializer):
        serializer.save(msme_owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                data=serializer.data,
                message='Customer created successfully',
                status_code=status.HTTP_201_CREATED
            )
        return api_error(errors=serializer.errors)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return api_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CustomerSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response(data=serializer.data, message='Customer updated')
        return api_error(errors=serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(message='Customer deleted', status_code=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='dropdown')
    def dropdown(self, request):
        """Lightweight list for invoice/inventory customer dropdowns — no pagination."""
        customers = Customer.objects.filter(
            msme_owner=request.user
        ).order_by('name')
        serializer = CustomerDropdownSerializer(customers, many=True)
        return api_response(data=serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-upload',
            parser_classes=[MultiPartParser, FormParser])
    def bulk_upload(self, request):
        """Upload an Excel file to bulk-import customers."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return api_error(message='No file uploaded')

        # Validate file extension
        name = file_obj.name.lower()
        if not (name.endswith('.xlsx') or name.endswith('.xls')):
            return api_error(message='Only .xlsx and .xls files are accepted')

        # Validate file size (10MB max)
        if file_obj.size > 10 * 1024 * 1024:
            return api_error(message='File size exceeds 10MB limit')

        from .bulk_upload import parse_and_import
        result = parse_and_import(file_obj, request.user)
        return api_response(data=result, message='Bulk upload completed')

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        customer = self.get_object()

        # PaymentRecord contains both uploaded and synced manual invoices
        records = customer.payment_records.all()
        filterset = PaymentRecordFilter(request.GET, queryset=records)
        if filterset.is_valid():
            records = filterset.qs
            
        pa_data = PaymentRecordListSerializer(records, many=True).data
        pa_data.sort(key=lambda x: x.get('invoice_date') or '', reverse=True)

        return api_response(data=pa_data)

    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        customer = self.get_object()
        try:
            analytics = customer.analytics
            total_invoices = analytics.total_invoices
            total_amount = float(analytics.total_amount)
            total_paid = float(analytics.total_paid)
            on_time_count = analytics.on_time_count
            late_count = analytics.late_count
            overdue_count = analytics.overdue_count
            avg_days_late = analytics.avg_days_late
            score = analytics.payment_score
            last_payment = analytics.last_payment_date
        except PaymentAnalytics.DoesNotExist:
            total_invoices = 0
            total_amount = 0
            total_paid = 0
            on_time_count = 0
            late_count = 0
            overdue_count = 0
            avg_days_late = 0
            score = 50.0  # New customer base score → SILVER
            last_payment = None

        tier = PaymentAnalytics.get_tier(score)
        credit_days = PaymentAnalytics.get_credit_days(tier)

        # Override with manually assigned credit if valid
        from datetime import date
        latest_credit = CreditTimeline.objects.filter(
            customer=customer,
            valid_until__gte=date.today()
        ).order_by('-assigned_at').first()

        if latest_credit:
            credit_days = latest_credit.credit_days
            tier = latest_credit.tier

        data = {
            'customer': CustomerSerializer(customer).data,
            'analytics': {
                'total_invoices': total_invoices,
                'total_amount': str(total_amount),
                'total_paid': str(total_paid),
                'on_time_count': on_time_count,
                'late_count': late_count,
                'overdue_count': overdue_count,
                'avg_days_late': avg_days_late,
                'payment_score': score,
                'last_payment_date': last_payment,
                'tier': tier,
            },
            'credit_days': credit_days,
            'tier': tier,
        }
        return api_response(data=data)

    @action(detail=True, methods=['get'], url_path='credit-history')
    def credit_history(self, request, pk=None):
        customer = self.get_object()
        credits = CreditTimeline.objects.filter(customer=customer)
        serializer = CreditTimelineSerializer(credits, many=True)
        return api_response(data=serializer.data)

    @action(detail=True, methods=['post'], url_path='assign-credit')
    def assign_credit(self, request, pk=None):
        customer = self.get_object()
        credit_days = request.data.get('credit_days')
        reason = request.data.get('reason', '')

        if not credit_days or int(credit_days) not in [7, 15, 30, 45, 60, 90]:
            return api_error(message='Invalid credit days. Choose from: 7, 15, 30, 45, 60, 90')

        try:
            analytics = customer.analytics
            score = analytics.payment_score
        except PaymentAnalytics.DoesNotExist:
            score = 50.0

        tier = PaymentAnalytics.get_tier(score)

        from datetime import date, timedelta
        credit = CreditTimeline.objects.create(
            customer=customer,
            assigned_by=request.user,
            credit_days=int(credit_days),
            reason=reason,
            score=score,
            tier=tier,
            valid_until=date.today() + timedelta(days=365)
        )
        serializer = CreditTimelineSerializer(credit)
        return api_response(
            data=serializer.data,
            message='Credit timeline of %s days assigned' % credit_days,
            status_code=status.HTTP_201_CREATED
        )
