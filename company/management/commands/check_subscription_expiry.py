from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.conf import settings
from company.models import Company
from notifications.models import EmailLog, Notification
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Check subscription expiry and send alerts for 7-day, 3-day, and expired plans.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        # Find companies with active subscriptions
        companies = Company.objects.filter(is_subscription_active=True, subscription_end__isnull=False)
        
        # Super Admins to receive in-app notifications
        super_admins = User.objects.filter(is_superuser=True)

        processed_count = 0

        for company in companies:
            end_date = company.subscription_end.date()
            days_left = (end_date - today).days

            alert_type = None
            if days_left == 7:
                alert_type = '7_DAYS'
                title = 'Subscription Expiring in 7 Days'
            elif days_left == 3:
                alert_type = '3_DAYS'
                title = 'Subscription Expiring in 3 Days'
            elif days_left <= 0:
                alert_type = 'EXPIRED'
                title = 'Subscription Expired'
                
                # Update company status if fully expired
                company.is_subscription_active = False
                company.plan_type = 'TRIAL' # Downgrade or just mark inactive
                company.save(update_fields=['is_subscription_active', 'plan_type'])

            if alert_type:
                processed_count += 1
                
                # 1. Send Email to Company Owner
                if company.email:
                    context = {
                        'company_name': company.name,
                        'days_left': days_left,
                        'alert_type': alert_type,
                        'plan_type': company.plan_type,
                        'end_date': company.subscription_end.strftime("%d %b %Y"),
                        'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                    }
                    html_message = render_to_string('notifications/email/subscription_alert.html', context)
                    
                    email_log = EmailLog.objects.create(
                        to_email=company.email,
                        subject=f"{title} - {company.name}",
                        body=html_message
                    )
                    try:
                        from notifications.tasks import send_notification_email
                        send_notification_email.delay(email_log.id)
                    except Exception as e:
                        self.stderr.write(f"Failed to queue email for {company.name}: {e}")

                # 2. In-App Notification to Super Admins
                admin_message = f"Company '{company.name}' plan ({company.plan_type}) "
                if alert_type == 'EXPIRED':
                    admin_message += "has expired today."
                else:
                    admin_message += f"is expiring in {days_left} days."
                    
                for admin in super_admins:
                    Notification.objects.create(
                        user=admin,
                        title=f"Plan Alert: {company.name}",
                        message=admin_message,
                        category='Subscription',
                        link='/admin/companies/'
                    )

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed_count} subscription alerts.'))
