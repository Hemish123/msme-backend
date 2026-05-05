from django.urls import path
from . import views

urlpatterns = [
    path('yearly/', views.YearlyAnalyticsView.as_view(), name='analytics-yearly'),
    path('customer-scores/', views.CustomerScoresView.as_view(), name='analytics-customer-scores'),
    path('monthly-heatmap/', views.MonthlyHeatmapView.as_view(), name='analytics-monthly-heatmap'),
]
