from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.logistics_dashboard, name='logistics_dashboard'),

    # Drivers
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/add/', views.driver_add, name='driver_add'),
    path('drivers/edit/<int:pk>/', views.driver_edit, name='driver_edit'),
    path('drivers/delete/<int:pk>/', views.driver_delete, name='driver_delete'),

    # E-Vehicles
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('vehicles/edit/<int:pk>/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/delete/<int:pk>/', views.vehicle_delete, name='vehicle_delete'),

    # Delivery Orders
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/add/', views.delivery_add, name='delivery_add'),
    path('deliveries/<int:pk>/', views.delivery_detail, name='delivery_detail'),
    path('deliveries/<int:pk>/status/', views.delivery_update_status, name='delivery_update_status'),

    # Charging Logs
    path('charging/', views.charging_log_list, name='charging_log_list'),
    path('charging/add/', views.charging_log_add, name='charging_log_add'),

    # Maintenance
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/add/', views.maintenance_add, name='maintenance_add'),
    path('maintenance/<int:pk>/update/', views.maintenance_update, name='maintenance_update'),
]