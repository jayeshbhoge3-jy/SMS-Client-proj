from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from company.models import Company
from inventory.models import Product, ProductBatch
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send inventory alerts (low stock, near expiry) via email to BUSINESS plan users'

    def handle(self, *args, **options):
        # Only fetch active companies with BUSINESS plan
        companies = Company.objects.filter(plan_type='BUSINESS')
        
        for company in companies:
            if not company.email:
                continue
            
            # Low Stock Check (Assuming threshold is 5 for low stock)
            low_stock_products = Product.objects.filter(
                company=company,
                stock_quantity__gt=0,
                stock_quantity__lte=5
            )
            
            low_stock_items = [{'product': product} for product in low_stock_products]
                
            # Near Expiry Check (Within 30 days)
            today = timezone.now().date()
            near_expiry_limit = today + timedelta(days=30)
            
            near_expiry_batches = ProductBatch.objects.filter(
                company=company,
                is_active=True,
                quantity__gt=0,
                expiry_date__range=(today, near_expiry_limit)
            ).select_related('product')
            
            near_expiry_items = [batch for batch in near_expiry_batches]
            
            # Expired Check (Already expired)
            expired_batches = ProductBatch.objects.filter(
                company=company,
                is_active=True,
                quantity__gt=0,
                expiry_date__lt=today
            ).select_related('product')
            
            expired_items = [batch for batch in expired_batches]
                
            if low_stock_items or near_expiry_items or expired_items:
                # Prepare Context for Template
                context = {
                    'company_name': company.name,
                    'low_stock_items': low_stock_items,
                    'near_expiry_items': near_expiry_items,
                    'expired_items': expired_items,
                    'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
                }
                
                # Render HTML Template
                html_message = render_to_string('inventory/email/inventory_alerts.html', context)
                plain_message = strip_tags(html_message)
                
                subject = f"Inventory Alerts - {company.name}"
                from_email = getattr(settings, 'EMAIL_HOST_USER', 'no-reply@cwsinventory.com')
                recipient_list = [company.email]
                
                try:
                    from notifications.models import EmailLog
                    from notifications.tasks import send_notification_email
                    
                    # Create an EmailLog entry which will be picked up by Celery
                    email_log = EmailLog.objects.create(
                        to_email=company.email,
                        subject=subject,
                        body=html_message
                    )
                    
                    # Queue async celery task
                    send_notification_email.delay(email_log.id)
                    
                    self.stdout.write(self.style.SUCCESS(f"Queued alert email to {company.name} ({company.email}) via Celery"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to queue email for {company.email}: {e}"))
                    
        self.stdout.write(self.style.SUCCESS('Successfully processed inventory alerts'))
