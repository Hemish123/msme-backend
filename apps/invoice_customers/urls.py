from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceCustomerListCreateView.as_view(), name='invoice-customer-list-create'),
    path('dropdown/', views.InvoiceCustomerDropdownView.as_view(), name='invoice-customer-dropdown'),
    path('<int:pk>/', views.InvoiceCustomerDetailView.as_view(), name='invoice-customer-detail'),
]
