from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice-list'),
    path('create/', views.InvoiceCreateView.as_view(), name='invoice-create'),
    path('next-number/', views.NextInvoiceNumberView.as_view(), name='invoice-next-number'),
    path('stats/', views.InvoiceStatsView.as_view(), name='invoice-stats'),
    path('templates/', views.InvoiceTemplatesView.as_view(), name='invoice-templates'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<int:pk>/pdf/', views.InvoicePDFView.as_view(), name='invoice-pdf'),
    path('<int:pk>/resend-email/', views.ResendInvoiceEmailView.as_view(), name='invoice-resend-email'),
    path('<int:pk>/schedule-reminder/', views.ScheduleReminderView.as_view(), name='invoice-schedule-reminder'),
]
