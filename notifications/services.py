from django.template import Template, Context
from django.contrib.auth.models import User
from .models import Notification, EmailTemplate, EmailLog, AdminNotificationSetting
from .tasks import send_notification_email

DEFAULT_EMAIL_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      body { margin: 0; padding: 0; background: #f3f4f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
      .wrapper { width: 100%; padding: 40px 0; background: #f3f4f6; }
      .main { max-width: 600px; background: #ffffff; margin: 0 auto; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.06); }
      .header { background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); padding: 40px 30px; text-align: center; }
      .header img { max-height: 40px; margin-bottom: 20px; }
      .header h1 { color: #ffffff; margin: 0; font-size: 24px; }
      .header p { color: #e0e7ff; margin-top: 10px; font-size: 15px; }
      .content { padding: 40px 30px; }
      .content p { color: #4b5563; font-size: 16px; line-height: 1.7; }
      .footer { background: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb; }
      .footer p { color: #6b7280; font-size: 13px; line-height: 1.5; margin: 0; }
    </style>
  </head>
  <body>
    <div class="wrapper">
      <div class="main">
        <div class="header">
          <img src="cid:logo" alt="CWS Inventory Logo" />
          <h1>System Notification</h1>
          <p>{{ title }}</p>
        </div>
        <div class="content">
          {{ message|safe }}
          <p style="margin-top:30px;">
            Best Regards,<br />
            <strong>SaaS Admin Team</strong>
          </p>
        </div>
        <div class="footer">
          <p>© 2026 CWS Inventory. All rights reserved.</p>
        </div>
      </div>
    </div>
  </body>
</html>
"""

def notify_admin(category, title, message_html, link=""):
    """
    Core function to notify superadmins via in-app alert and email.
    category: 'Company', 'Subscription', 'Security', 'System'
    """
    # 1. Find all superusers (Admins)
    admins = User.objects.filter(is_superuser=True)
    
    for admin in admins:
        # Check settings
        settings, created = AdminNotificationSetting.objects.get_or_create(user=admin)
        
        # Check granular permissions
        should_notify = False
        if category == 'Company' and settings.notify_company_events: should_notify = True
        elif category == 'Subscription' and settings.notify_subscription_events: should_notify = True
        elif category == 'Security' and settings.notify_security_events: should_notify = True
        elif category == 'System' and settings.notify_system_events: should_notify = True
        
        if not should_notify:
            continue
            
        # In-App Notification
        if settings.receive_in_app:
            Notification.objects.create(
                user=admin,
                title=title,
                message=message_html, # Strip tags if needed, but safe here
                category=category,
                link=link
            )
            
        # Email Notification
        if settings.receive_email and admin.email:
            # Check if template exists for this title/type
            # Fallback to default
            template_str = DEFAULT_EMAIL_HTML
            
            # Context for rendering
            context = Context({
                'title': title,
                'message': message_html,
                'link': link
            })
            
            rendered_html = Template(template_str).render(context)
            
            email_log = EmailLog.objects.create(
                to_email=admin.email,
                subject=f"[Alert] {title}",
                body=rendered_html
            )
            
            # Queue async celery task
            try:
              send_notification_email.delay(email_log.id)
            except Exception:
              # Celery not running — send synchronously as fallback
              send_notification_email(email_log.id)
