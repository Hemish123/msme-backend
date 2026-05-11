from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from utils.template_views import CustomerTemplateView, InventoryTemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/upload/', include('apps.excel_upload.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/analytics/', include('apps.payments.analytics_urls')),
    # Invoice module URLs
    path('api/invoice-customers/', include('apps.invoice_customers.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/invoices/', include('apps.invoices.urls')),
    # Template download endpoints
    path('api/templates/customer-template/', CustomerTemplateView.as_view(), name='customer-template'),
    path('api/templates/inventory-template/', InventoryTemplateView.as_view(), name='inventory-template'),
]

from django.urls import re_path
from django.views.static import serve

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
