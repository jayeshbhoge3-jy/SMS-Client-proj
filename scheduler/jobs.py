"""
scheduler/jobs.py

Defines the scheduled jobs that run automatically once the Django server starts.

Jobs registered here:
  - send_low_stock_alerts_job   → runs daily at 08:00 AM IST
  - send_expiry_stock_alerts_job → runs daily at 08:05 AM IST

These call the same logic used by the management command
`python manage.py send_stock_alerts`, so both manual and automatic
execution stay in sync.
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage

from company.models import Company
from inventory.models import Product, ProductBatch

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Shared email helper
# ─────────────────────────────────────────────

def _attach_logo(msg):
    logo_path = finders.find('accounts/images/logo.png')
    if logo_path:
        with open(logo_path, 'rb') as f:
            mime_img = MIMEImage(f.read())
            mime_img.add_header('Content-ID', '<logo>')
            mime_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            msg.attach(mime_img)


def _send_html_email(subject, template_name, context, recipient_email):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[recipient_email],
    )
    msg.attach_alternative(html_content, 'text/html')
    _attach_logo(msg)
    msg.send(fail_silently=False)


# ─────────────────────────────────────────────
#  Job 1 — Low Stock Alert
# ─────────────────────────────────────────────

def send_low_stock_alerts_job():
    """
    Scheduled job: Send low-stock email alerts to all active BUSINESS plan
    companies (Rs. 1299). Skips companies with no products below threshold.
    """
    today = date.today()
    alert_date = today.strftime('%d %b %Y')
    dashboard_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000/') + '/inventory/alerts/'

    logger.info('[Scheduler] Low-stock alert job started — %s', alert_date)

    business_companies = Company.objects.filter(
        plan_type='BUSINESS',
        is_subscription_active=True,
    ).select_related('owner')

    sent = skipped = errors = 0

    for company in business_companies:
        owner = company.owner
        low_stock_products = (
            Product.objects.filter(
                company=company,
                stock_quantity__lte=F('low_stock_limit'),
            )
            .values('name', 'sku', 'stock_quantity', 'low_stock_limit')
        )

        if not low_stock_products.exists():
            skipped += 1
            continue

        count = low_stock_products.count()
        context = {
            'name': owner.first_name or owner.username,
            'company_name': company.name,
            'low_stock_count': count,
            'low_stock_products': list(low_stock_products),
            'alert_date': alert_date,
            'dashboard_url': dashboard_url,
        }

        try:
            _send_html_email(
                subject=f'⚠️ Low Stock Alert — {count} product(s) need restocking | {company.name}',
                template_name='inventory/emails/low_stock_alert.html',
                context=context,
                recipient_email=owner.email,
            )
            logger.info(
                '[Scheduler] Low-stock alert sent → %s (%d products)',
                owner.email, count
            )
            sent += 1
        except Exception as exc:
            logger.error(
                '[Scheduler] Failed to send low-stock alert to %s: %s',
                owner.email, exc
            )
            errors += 1

    logger.info(
        '[Scheduler] Low-stock job complete — Sent: %d | Skipped: %d | Errors: %d',
        sent, skipped, errors
    )


# ─────────────────────────────────────────────
#  Job 2 — Expiry Stock Alert
# ─────────────────────────────────────────────

def send_expiry_stock_alerts_job():
    """
    Scheduled job: Send expiry stock email alerts to all active BUSINESS plan
    companies (Rs. 1299). Covers expired batches and batches expiring within 30 days.
    """
    today = date.today()
    near_limit = today + timedelta(days=30)
    alert_date = today.strftime('%d %b %Y')
    dashboard_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000/') + '/inventory/reports/near-expiry/'

    logger.info('[Scheduler] Expiry alert job started — %s', alert_date)

    business_companies = Company.objects.filter(
        plan_type='BUSINESS',
        is_subscription_active=True,
    ).select_related('owner')

    sent = skipped = errors = 0

    for company in business_companies:
        owner = company.owner

        # Expired batches
        expired_qs = ProductBatch.objects.filter(
            company=company,
            is_active=True,
            expiry_date__lt=today,
        ).select_related('product').order_by('expiry_date')

        expired_batches = [
            {
                'product__name': b.product.name,
                'batch_number': b.batch_number,
                'expiry_date': b.expiry_date.strftime('%d %b %Y'),
                'quantity': b.quantity,
            }
            for b in expired_qs
        ]

        # Near-expiry batches
        near_expiry_qs = ProductBatch.objects.filter(
            company=company,
            is_active=True,
            expiry_date__gte=today,
            expiry_date__lte=near_limit,
        ).select_related('product').order_by('expiry_date')

        near_expiry_batches = [
            {
                'product__name': b.product.name,
                'batch_number': b.batch_number,
                'expiry_date': b.expiry_date.strftime('%d %b %Y'),
                'days_left': (b.expiry_date - today).days,
                'quantity': b.quantity,
            }
            for b in near_expiry_qs
        ]

        expired_count = len(expired_batches)
        near_expiry_count = len(near_expiry_batches)

        if expired_count + near_expiry_count == 0:
            skipped += 1
            continue

        context = {
            'name': owner.first_name or owner.username,
            'company_name': company.name,
            'expired_count': expired_count,
            'near_expiry_count': near_expiry_count,
            'expired_batches': expired_batches,
            'near_expiry_batches': near_expiry_batches,
            'alert_date': alert_date,
            'dashboard_url': dashboard_url,
        }

        try:
            _send_html_email(
                subject=(
                    f'🚨 Expiry Stock Alert — '
                    f'{expired_count} expired, {near_expiry_count} near-expiry '
                    f'| {company.name}'
                ),
                template_name='inventory/emails/expiry_stock_alert.html',
                context=context,
                recipient_email=owner.email,
            )
            logger.info(
                '[Scheduler] Expiry alert sent → %s (%d expired, %d near-expiry)',
                owner.email, expired_count, near_expiry_count
            )
            sent += 1
        except Exception as exc:
            logger.error(
                '[Scheduler] Failed to send expiry alert to %s: %s',
                owner.email, exc
            )
            errors += 1

    logger.info(
        '[Scheduler] Expiry job complete — Sent: %d | Skipped: %d | Errors: %d',
        sent, skipped, errors
    )