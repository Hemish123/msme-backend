from django.urls import path
from . import views

urlpatterns = [
    path('', views.InventoryListCreateView.as_view(), name='inventory-list-create'),
    path('dropdown/', views.InventoryDropdownView.as_view(), name='inventory-dropdown'),
    path('<int:pk>/', views.InventoryDetailView.as_view(), name='inventory-detail'),
]
