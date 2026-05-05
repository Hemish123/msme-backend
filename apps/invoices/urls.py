from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice-list'),
    path('create/', views.InvoiceCreateView.as_view(), name='invoice-create'),
    path('next-number/', views.NextInvoiceNumberView.as_view(), name='invoice-next-number'),
    path('stats/', views.InvoiceStatsView.as_view(), name='invoice-stats'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<int:pk>/pdf/', views.InvoicePDFView.as_view(), name='invoice-pdf'),
    path('<int:pk>/resend-email/', views.ResendInvoiceEmailView.as_view(), name='invoice-resend-email'),
]
