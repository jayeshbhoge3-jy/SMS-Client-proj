from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    # Dashboard
    path('', views.training_dashboard, name='dashboard'),

    # Training Materials
    path('materials/', views.material_list, name='material_list'),
    path('materials/add/', views.material_create, name='material_create'),
    path('materials/<int:pk>/edit/', views.material_edit, name='material_edit'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),

    # Training Records
    path('records/', views.record_list, name='record_list'),
    path('records/add/', views.record_create, name='record_create'),
    path('records/<int:pk>/edit/', views.record_edit, name='record_edit'),

    # Staff Onboarding
    path('onboarding/', views.onboarding_list, name='onboarding_list'),
    path('onboarding/add/', views.onboarding_create, name='onboarding_create'),
    path('onboarding/<int:pk>/', views.onboarding_detail, name='onboarding_detail'),

    # Support Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/add/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),

    # Admin Support Tickets
path('admin/tickets/', views.admin_ticket_list, name='admin_ticket_list'),
path('admin/tickets/<int:pk>/', views.admin_ticket_detail, name='admin_ticket_detail'),

    # AJAX
    path('ajax/add-staff/', views.add_staff_ajax, name='add_staff_ajax'),
]
