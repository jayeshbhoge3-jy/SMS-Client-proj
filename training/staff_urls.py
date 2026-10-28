from django.urls import path
from training.staff_views import (
    staff_login,
    staff_logout,
    staff_accept_invite,
    staff_dashboard,
    staff_my_training,
    staff_material_detail,
    staff_my_onboarding,
    staff_toggle_checklist,
    staff_my_tickets,
    staff_ticket_create,
    staff_ticket_detail,
    staff_ticket_delete,
)

urlpatterns = [
    # Auth
    path('login/',                          staff_login,            name='staff_login'),
    path('logout/',                         staff_logout,           name='staff_logout'),
    path('invite/<uuid:token>/',            staff_accept_invite,    name='staff_accept_invite'),

    # Portal
    path('dashboard/',                      staff_dashboard,        name='staff_dashboard'),
    path('my-training/',                    staff_my_training,      name='staff_my_training'),
    path('my-training/<int:pk>/',           staff_material_detail,  name='staff_material_detail'),
    path('my-onboarding/',                  staff_my_onboarding,    name='staff_my_onboarding'),
    path('checklist/<int:pk>/toggle/',      staff_toggle_checklist, name='staff_toggle_checklist'),

    # Tickets
    path('my-tickets/',                     staff_my_tickets,       name='staff_my_tickets'),
    path('my-tickets/new/',                 staff_ticket_create,    name='staff_ticket_create'),
    path('my-tickets/<int:pk>/',            staff_ticket_detail,    name='staff_ticket_detail'),
    path('my-tickets/<int:pk>/delete/',     staff_ticket_delete,    name='staff_ticket_delete'),
]

from training import staff_inventory_views as views

urlpatterns += [
    # Products
    path('inventory/', views.staff_product_list, name='staff_product_list'),
    path('inventory/add/', views.staff_product_create, name='staff_product_create'),
    path('inventory/<int:pk>/edit/', views.staff_product_edit, name='staff_product_edit'),
    path('inventory/<int:pk>/delete-request/', views.staff_product_delete_request, name='staff_product_delete_request'),

    # Categories
    path('categories/', views.staff_category_list, name='staff_category_list'),
    path('categories/add/', views.staff_category_create, name='staff_category_create'),
    path('categories/<int:pk>/edit/', views.staff_category_edit, name='staff_category_edit'),
    path('categories/<int:pk>/delete-request/', views.staff_category_delete_request, name='staff_category_delete_request'),

    # Purchase Orders
    path('po/', views.staff_po_list, name='staff_po_list'),
    path('po/add/', views.staff_po_create, name='staff_po_create'),
    path('po/<int:pk>/edit/', views.staff_po_edit, name='staff_po_edit'),
    path('po/<int:pk>/submit/', views.staff_submit_purchase_order, name='staff_submit_purchase_order'),
    path('po/<int:pk>/delete-request/', views.staff_po_delete_request, name='staff_po_delete_request'),

    # Sales Orders
    path('so/', views.staff_so_list, name='staff_so_list'),
    path('so/add/', views.staff_so_create, name='staff_so_create'),
    path('so/<int:pk>/edit/', views.staff_so_edit, name='staff_so_edit'),
    path('so/<int:pk>/status/', views.staff_update_so_status, name='staff_update_so_status'),
    path('so/<int:pk>/delete-request/', views.staff_so_delete_request, name='staff_so_delete_request'),
    
    # API endpoints
    path('ajax/fefo-preview/', views.staff_fefo_preview_api, name='staff_fefo_preview_api'),
    path('ajax/available-batches/', views.staff_available_batches_api, name='staff_available_batches_api'),

    # Customers
    path('customers/', views.staff_customer_list, name='staff_customer_list'),
    path('customers/add/', views.staff_customer_create, name='staff_customer_create'),
    path('customers/<int:pk>/edit/', views.staff_customer_edit, name='staff_customer_edit'),
    path('customers/<int:pk>/delete-request/', views.staff_customer_delete_request, name='staff_customer_delete_request'),

    # My Delete Requests
    path('delete-requests/', views.staff_my_delete_requests, name='staff_my_delete_requests'),
]