from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('Company', 'Company'),
        ('Subscription', 'Subscription'),
        ('Security', 'Security'),
        ('System', 'System'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    link = models.CharField(max_length=255, blank=True, help_text="URL to redirect when clicked")
    
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title}"


class EmailTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g. company_created, payment_success")
    subject = models.CharField(max_length=255)
    html_body = models.TextField(help_text="Supports dynamic placeholders like {{ company_name }}")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class EmailLog(models.Model):
    STATUS_CHOICES = (('Pending', 'Pending'), ('Sent', 'Sent'), ('Failed', 'Failed'))
    
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.to_email} - {self.subject} ({self.status})"


class AdminNotificationSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    # Channel preferences
    receive_in_app = models.BooleanField(default=True)
    receive_email = models.BooleanField(default=True)
    
    # Granular Event Toggles
    notify_company_events = models.BooleanField(default=True)
    notify_subscription_events = models.BooleanField(default=True)
    notify_security_events = models.BooleanField(default=True)
    notify_system_events = models.BooleanField(default=True)

    def __str__(self):
        return f"Settings for {self.user.username}"
