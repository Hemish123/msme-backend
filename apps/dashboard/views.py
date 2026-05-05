from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

from utils.response import api_response
from apps.customers.models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics


class DashboardStatsView(APIView):
    """Top-level KPI stats."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        customers = Customer.objects.filter(msme_owner=user)
        records = PaymentRecord.objects.filter(customer__msme_owner=user)
        from apps.invoices.models import Invoice
        invoices = Invoice.objects.filter(user=user)

        total_customers = customers.count()
        
        # PaymentRecord now contains both uploaded and manually created invoices
        total_amount = float(records.aggregate(s=Sum('amount'))['s'] or 0)
        total_paid = float(records.aggregate(s=Sum('paid_amount'))['s'] or 0)
        total_records = records.count()

        on_time = records.filter(status='PAID').count()
        late = records.filter(status='LATE').count()
        overdue_count = records.filter(status='OVERDUE').count()
        
        on_time_rate = round((on_time / total_records * 100), 1) if total_records > 0 else 0

        avg_days_late = records.filter(days_late__gt=0).aggregate(
            a=Avg('days_late')
        )['a'] or 0

        data = {
            'total_customers': total_customers,
            'total_invoices_value': total_amount,
            'total_collected': total_paid,
            'on_time_rate': on_time_rate,
            'avg_days_late': round(avg_days_late, 1),
            'total_invoices': total_records,
            'overdue_count': overdue_count,
            'pending_amount': total_amount - total_paid,
        }
        return api_response(data=data)


class PaymentTrendView(APIView):
    """Monthly payment data for last 12 months."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        twelve_months_ago = timezone.now().date() - timedelta(days=365)
        
        records = PaymentRecord.objects.filter(
            customer__msme_owner=request.user,
            invoice_date__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('invoice_date')
        ).values('month').annotate(
            total_due=Sum('amount'),
            total_collected=Sum('paid_amount'),
            invoice_count=Count('id'),
        )

        merged = {}
        for r in records:
            if not r['month']: continue
            m = r['month'].strftime('%Y-%m')
            merged[m] = {
                'month': m,
                'month_label': r['month'].strftime('%b %Y'),
                'total_due': float(r['total_due'] or 0),
                'total_collected': float(r['total_collected'] or 0),
                'invoice_count': r['invoice_count'],
            }

        data = []
        for m in sorted(merged.keys()):
            item = merged[m]
            item['difference'] = item['total_due'] - item['total_collected']
            data.append(item)

        return api_response(data=data)


def get_customer_combined_stats(user):
    from apps.customers.models import Customer
    from apps.payments.models import PaymentAnalytics
    
    customers = Customer.objects.filter(msme_owner=user).select_related('analytics')
    
    results = []
    for c in customers:
        try:
            pa = c.analytics
            total_invoices = pa.total_invoices
            total_amount = float(pa.total_amount)
            total_paid = float(pa.total_paid)
            on_time_count = pa.on_time_count
            late_count = pa.late_count
            overdue_count = pa.overdue_count
            avg_days_late = pa.avg_days_late
            score = pa.payment_score
        except Exception:
            total_invoices = 0
            total_amount = 0
            total_paid = 0
            on_time_count = 0
            late_count = 0
            overdue_count = 0
            avg_days_late = 0
            score = 50.0  # New customer base score
            
        results.append({
            'customer_id': c.id,
            'customer_name': c.name,
            'company': c.company,
            'total_invoices': total_invoices,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'on_time_count': on_time_count,
            'late_count': late_count,
            'avg_days_late': avg_days_late,
            'payment_score': score,
            'overdue_count': overdue_count,
            'overdue_amount': total_amount - total_paid,
            'tier': PaymentAnalytics.get_tier(score),
        })
            
    return results


class TopCustomersView(APIView):
    """Top 10 on-time payers."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = get_customer_combined_stats(request.user)
        # Filter for customers with at least one on-time payment
        on_time_payers = [s for s in stats if s['on_time_count'] > 0]
        # Sort by payment_score descending
        on_time_payers.sort(key=lambda x: x['payment_score'], reverse=True)
        top_10 = on_time_payers[:10]

        data = [{
            'customer_id': a['customer_id'],
            'customer_name': a['customer_name'],
            'company': a['company'],
            'payment_score': a['payment_score'],
            'on_time_count': a['on_time_count'],
            'total_invoices': a['total_invoices'],
            'on_time_rate': round(a['on_time_count'] / a['total_invoices'] * 100, 1) if a['total_invoices'] > 0 else 0,
            'tier': a['tier'],
            'total_amount': a['total_amount'],
        } for a in top_10]

        return api_response(data=data)


class DefaultersView(APIView):
    """Customers with overdue > 30 days."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = get_customer_combined_stats(request.user)
        # Filter for customers with actual defaults (score < 70 OR has late/overdue invoices)
        defaulters = [s for s in stats if s['overdue_count'] > 0 or s['avg_days_late'] > 0 or s['payment_score'] < 50]
        # Sort by payment_score ascending (worst first)
        defaulters.sort(key=lambda x: x['payment_score'])
        bottom_10 = defaulters[:10]

        data = [{
            'customer_id': a['customer_id'],
            'customer_name': a['customer_name'],
            'company': a['company'],
            'payment_score': a['payment_score'],
            'avg_days_late': a['avg_days_late'],
            'late_count': a['late_count'],
            'total_invoices': a['total_invoices'],
            'overdue_amount': a['overdue_amount'],
            'tier': a['tier'],
        } for a in bottom_10]

        return api_response(data=data)


class CreditDistributionView(APIView):
    """Breakdown by credit tier."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = get_customer_combined_stats(request.user)

        tiers = {
            'PLATINUM': {'count': 0, 'label': 'Platinum (85-100)', 'color': '#8B5CF6'},
            'GOLD': {'count': 0, 'label': 'Gold (70-84)', 'color': '#F59E0B'},
            'SILVER': {'count': 0, 'label': 'Silver (50-69)', 'color': '#94A3B8'},
            'BRONZE': {'count': 0, 'label': 'Bronze (30-49)', 'color': '#F97316'},
            'BLACKLIST': {'count': 0, 'label': 'Blacklist (0-29)', 'color': '#F43F5E'},
        }

        for a in stats:
            tiers[a['tier']]['count'] += 1

        data = [
            {'tier': k, 'count': v['count'], 'label': v['label'], 'color': v['color']}
            for k, v in tiers.items()
        ]

        return api_response(data=data)
