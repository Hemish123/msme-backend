from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, Count, F, Q
from django.db.models.functions import TruncMonth, TruncYear

from utils.response import api_response
from apps.customers.models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics
from .serializers import PaymentAnalyticsSerializer


class YearlyAnalyticsView(APIView):
    """Year-wise payment volume."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = PaymentRecord.objects.filter(
            customer__msme_owner=request.user
        ).annotate(
            year=TruncYear('invoice_date')
        ).values('year').annotate(
            total_due=Sum('amount'),
            total_paid=Sum('paid_amount'),
            invoice_count=Count('id')
        ).order_by('year')

        data = [{
            'year': r['year'].year if r['year'] else None,
            'total_due': float(r['total_due'] or 0),
            'total_paid': float(r['total_paid'] or 0),
            'invoice_count': r['invoice_count'],
        } for r in records]

        return api_response(data=data)


class CustomerScoresView(APIView):
    """All customers with scores for scatter plot."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        analytics = PaymentAnalytics.objects.filter(
            customer__msme_owner=request.user
        ).select_related('customer')

        data = [{
            'customer_id': a.customer.id,
            'customer_name': a.customer.name,
            'avg_days_late': a.avg_days_late,
            'total_amount': float(a.total_amount),
            'total_invoices': a.total_invoices,
            'payment_score': a.payment_score,
            'tier': PaymentAnalytics.get_tier(a.payment_score),
        } for a in analytics]

        return api_response(data=data)


class MonthlyHeatmapView(APIView):
    """Payment heatmap data for calendar display."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = PaymentRecord.objects.filter(
            customer__msme_owner=request.user,
            paid_date__isnull=False
        ).values('paid_date').annotate(
            payment_count=Count('id'),
            total_amount=Sum('paid_amount')
        ).order_by('paid_date')

        data = [{
            'date': r['paid_date'].isoformat(),
            'count': r['payment_count'],
            'amount': float(r['total_amount'] or 0),
        } for r in records]

        return api_response(data=data)
