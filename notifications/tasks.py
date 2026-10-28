from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from .models import EmailLog, EmailTemplate
from django.template import Context, Template
from django.contrib.staticfiles import finders
from email.mime.image import MIMEImage
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_notification_email(self, email_log_id):
    """
    Celery task to send an email asynchronously.
    Reads from the EmailLog model and attempts to send it.
    """
    try:
        email_log = EmailLog.objects.get(id=email_log_id)
        if email_log.status == 'Sent':
            return  # Already sent
            
        # Create email
        # Assuming DEFAULT_FROM_EMAIL is set in settings
        from django.conf import settings
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'no-reply@creativewebsolution.info'))
        
        msg = EmailMultiAlternatives(
            subject=email_log.subject,
            body="Please view this email in an HTML compatible client.",
            from_email=from_email,
            to=[email_log.to_email]
        )
        msg.attach_alternative(email_log.body, "text/html")
        
        # Attach Logo
        logo_path = finders.find('accounts/images/logo.png')
        if logo_path:
            with open(logo_path, 'rb') as f:
                mime_image = MIMEImage(f.read())
                mime_image.add_header('Content-ID', '<logo>')
                mime_image.add_header('Content-Disposition', 'inline', filename='logo.png')
                msg.attach(mime_image)
        
        # Send
        msg.send(fail_silently=False)
        
        # Mark as sent
        email_log.status = 'Sent'
        email_log.sent_at = timezone.now()
        email_log.save()
        
        logger.info(f"Successfully sent email to {email_log.to_email}")
        
    except Exception as exc:
        logger.error(f"Failed to send email {email_log_id}: {str(exc)}")
        
        # Mark as failed
        email_log.status = 'Failed'
        email_log.error_message = str(exc)
        email_log.retry_count += 1
        email_log.save()
        
        # Retry in 5 minutes (300 seconds)
        raise self.retry(exc=exc, countdown=300)

@shared_task
def trigger_inventory_alerts():
    """
    Celery task to run the send_inventory_alerts management command asynchronously.
    """
    from django.core.management import call_command
    try:
        call_command('send_inventory_alerts')
        logger.info("Successfully triggered send_inventory_alerts command via Celery.")
    except Exception as e:
        logger.error(f"Failed to run send_inventory_alerts command: {e}")

@shared_task
def trigger_subscription_renewal(company_id, amount_paid):
    from company.models import Company
    from django.conf import settings
    from django.template.loader import render_to_string
    from notifications.models import EmailLog, Notification
    from django.contrib.auth.models import User
    
    try:
        company = Company.objects.get(id=company_id)
        super_admins = User.objects.filter(is_superuser=True)
        
        # 1. Email to Company Owner
        if company.email:
            context = {
                'company_name': company.name,
                'plan_type': company.plan_type,
                'amount_paid': amount_paid,
                'end_date': company.subscription_end.strftime("%d %b %Y") if company.subscription_end else 'N/A',
                'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            }
            html_message = render_to_string('notifications/email/subscription_renewed.html', context)
            
            email_log = EmailLog.objects.create(
                to_email=company.email,
                subject=f"Plan Renewed Successfully - {company.name}",
                body=html_message
            )
            # Route through the existing async email sender
            send_notification_email.delay(email_log.id)
            
        # 2. In-App Notification to Super Admins
        admin_message = f"Company '{company.name}' successfully renewed/upgraded to {company.plan_type} plan."
        for admin in super_admins:
            Notification.objects.create(
                user=admin,
                title=f"Plan Renewed: {company.name}",
                message=admin_message,
                category='Subscription',
                link='/admin/companies/'
            )
            
    except Exception as e:
        logger.error(f"Failed to process subscription renewal for company_id {company_id}: {e}")

@shared_task
def trigger_subscription_expiry_check():
    """
    Celery task to run the check_subscription_expiry management command asynchronously.
    Designed to be run daily via Celery Beat.
    """
    from django.core.management import call_command
    try:
        call_command('check_subscription_expiry')
        logger.info("Successfully triggered check_subscription_expiry command via Celery.")
    except Exception as e:
        logger.error(f"Failed to run check_subscription_expiry command: {e}")
