from django.urls import path
from . import views

urlpatterns = [
    path('api/unread/', views.get_unread_notifications, name='api_unread_notifications'),
    path('api/mark-read/<int:notif_id>/', views.mark_notification_read, name='api_mark_notif_read'),
    path('api/mark-all-read/', views.mark_all_read, name='api_mark_all_read'),
]
