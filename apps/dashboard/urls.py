from django.urls import path
from . import views

urlpatterns = [
    path('stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('payment-trend/', views.PaymentTrendView.as_view(), name='dashboard-payment-trend'),
    path('top-customers/', views.TopCustomersView.as_view(), name='dashboard-top-customers'),
    path('defaulters/', views.DefaultersView.as_view(), name='dashboard-defaulters'),
    path('credit-distribution/', views.CreditDistributionView.as_view(), name='dashboard-credit-distribution'),
]
