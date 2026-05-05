import django_filters
from .models import Customer, PaymentRecord


class CustomerFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    tier = django_filters.CharFilter(method='filter_by_tier')
    status = django_filters.CharFilter(method='filter_by_status')
    date_from = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Customer
        fields = ['search', 'tier', 'status', 'date_from', 'date_to']

    def filter_by_tier(self, queryset, name, value):
        tier_param = value.upper()
        if not tier_param:
            return queryset
            
        request = getattr(self, 'request', None)
        if not request or not request.user:
            return queryset
            
        from apps.dashboard.views import get_customer_combined_stats
        stats = get_customer_combined_stats(request.user)
        matching_ids = [s['customer_id'] for s in stats if s['tier'] == tier_param]
        return queryset.filter(id__in=matching_ids)

    def filter_by_status(self, queryset, name, value):
        status_param = value.upper()
        if not status_param:
            return queryset
            
        request = getattr(self, 'request', None)
        if not request or not request.user:
            return queryset
            
        from apps.dashboard.views import get_customer_combined_stats
        stats = get_customer_combined_stats(request.user)
        
        matching_ids = []
        for s in stats:
            if status_param == 'OVERDUE' and s.get('overdue_count', 0) > 0:
                matching_ids.append(s['customer_id'])
            elif status_param == 'PAID' and s.get('overdue_count', 0) == 0 and s.get('total_invoices', 0) > 0:
                matching_ids.append(s['customer_id'])
                
        return queryset.filter(id__in=matching_ids)


class PaymentRecordFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(lookup_expr='iexact')
    date_from = django_filters.DateFilter(field_name='invoice_date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='invoice_date', lookup_expr='lte')

    class Meta:
        model = PaymentRecord
        fields = ['status', 'date_from', 'date_to']
