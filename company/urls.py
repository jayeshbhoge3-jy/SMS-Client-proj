"""
FULL REPLACEMENT for: SMS/company/urls.py
Add the three new staff URL patterns (delete, regenerate, and the existing ones).
"""

from django.urls import path
from .views import company_dashboard, company_login, company_logout, company_settings
from . import views

urlpatterns = [
    path("login/",                              company_login,                      name="company_login"),
    path("dashboard/",                          company_dashboard,                  name="company_dashboard"),
    path('new-entry/',                          views.new_entry,                    name='new_entry'),
    path('reports/',                            views.reports_page,                 name='reports'),
    path("stock/add/",                          views.add_stock,                    name="add_stock"),
    path("dispatch/",                           views.dispatcher,                   name="dispatch"),

    # ── Staff management ──────────────────────────────────────────────────────
    path("staff/",                              views.staff_list,                   name="staff_list"),
    path("staff/add/",                          views.add_staff,                    name="add_staff"),
    path("staff/<int:staff_id>/delete/",        views.delete_staff,                 name="delete_staff"),
    path("staff/<int:staff_id>/regenerate/",    views.regenerate_staff_credentials, name="regenerate_staff_credentials"),
    path("staff/<int:staff_id>/resend-invite/",  views.resend_staff_invite,           name="resend_staff_invite"),
    # ─────────────────────────────────────────────────────────────────────────

    path("export/",                             views.export_data,                  name="export_data"),
    path("export/download/",                    views.export_data_download,         name="export_data_download"),
    path("transactions/",                       views.transactions_list,            name="transactions_list"),
    path("settings/",                           company_settings,                   name="company_settings"),
    path("check-email/",                        views.check_email,                  name="check_email"),
    path("logout/",                             company_logout,                     name="company_logout"),
    path('inventory/stock-movement/export-stock/',          views.export_stock_movement_pdf,    name='export_stock_movement_pdf'),
    path('inventory/stock-movement/export-stock/<int:pk>/', views.export_stock_movement_pdf,    name='export_products_stock_movement_pdf'),
    path("delete-entry/<int:entry_id>/",        views.delete_entry,                 name="delete_entry"),
    path("forgot-password/",                    views.forgot_password,              name="forgot_password"),
    path("forgot-password/verify-otp/",         views.verify_otp,                  name="verify_otp"),
    path("forgot-password/resend-otp/",         views.resend_otp,                  name="resend_otp"),
    path("forgot-password/reset_password/",     views.reset_password,              name="reset_password"),
    path("verify-old-password/",                views.verify_old_password,          name="verify_old_password"),
    path('pricing/',                            views.pricing,                      name='pricing'),
    path('create-order/',                       views.create_order,                 name='create_order'),
    path('payment-success/',                    views.payment_success,              name='payment_success'),
    path('payment-failed/',                     views.payment_failed,               name='payment_failed'),

    path('transport/add/',views.add_transport,name='add_transport'),

    path(
    'transport/list/',
    views.transport_list,
    name='transport_list'
    ),
    path(
    'transport/edit/<int:pk>/',
    views.edit_transport,
    name='edit_transport'
    ),
    path(
    'transport/delete/<int:pk>/',
    views.delete_transport,
    name='delete_transport'
    ),

path('transport/export-excel/', views.export_transport_excel, name='export_transport_excel'),
path('transport/export-pdf/',   views.export_transport_pdf,   name='export_transport_pdf'),



path(
    "send-password-otp/",
    views.send_password_otp,
    name="send_password_otp"
),

path(
    "verify-password-otp/",
    views.verify_password_otp,
    name="verify_password_otp"
),

    # --- Owner Inventory Views ---
    path('staff-activity/', views.owner_staff_activity, name='owner_staff_activity'),
    path('delete-requests/', views.owner_delete_requests, name='owner_delete_requests'),
    path('delete-requests/<int:pk>/approve/', views.owner_approve_delete, name='owner_approve_delete'),
    path('delete-requests/<int:pk>/reject/', views.owner_reject_delete, name='owner_reject_delete'),
]