from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.urls import path
from .models import Notification
from django.utils import timezone
from . import views

def is_superadmin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_superadmin)
def get_unread_notifications(request):
    """
    AJAX endpoint to fetch the latest 5 unread notifications and the total count.
    """
    notifications = Notification.objects.filter(user=request.user, is_read=False, is_archived=False)
    count = notifications.count()
    recent = notifications[:5]
    
    data = {
        'count': count,
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'category': n.category,
                'link': n.link,
                'crated_at': timezone.localtime(n.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            } for n in recent
        ]
    }
    return JsonResponse(data)

@login_required
@user_passes_test(is_superadmin)
@require_POST
def mark_notification_read(request, notif_id):
    """
    AJAX endpoint to mark a single notification as read.
    """
    try:
        notif = Notification.objects.get(id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Not found'}, status=404)

@login_required
@user_passes_test(is_superadmin)
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})
