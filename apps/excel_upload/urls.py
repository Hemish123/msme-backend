from django.urls import path
from . import views

urlpatterns = [
    path('excel/', views.ExcelUploadView.as_view(), name='excel-upload'),
    path('status/<int:pk>/', views.UploadStatusView.as_view(), name='upload-status'),
    path('history/', views.UploadHistoryView.as_view(), name='upload-history'),
]
