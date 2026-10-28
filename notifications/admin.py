from django.contrib import admin
from .models import Notification, EmailTemplate, EmailLog, AdminNotificationSetting

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'category', 'is_read', 'created_at')
    list_filter = ('category', 'is_read', 'is_archived')
    search_fields = ('title', 'message')

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'is_active')
    search_fields = ('name', 'subject')

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'subject', 'status', 'retry_count', 'sent_at')
    list_filter = ('status',)
    search_fields = ('to_email', 'subject')

@admin.register(AdminNotificationSetting)
class AdminNotificationSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'receive_in_app', 'receive_email')
