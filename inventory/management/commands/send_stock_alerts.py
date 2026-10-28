"""
Management command: send_stock_alerts

Sends two types of email alerts ONLY to companies on the BUSINESS plan (Rs. 1299):
  1. Low Stock Alert  — products whose stock_quantity <= low_stock_limit
  2. Expiry Stock Alert — batches that are expired OR expiring within 30 days

Usage:
    python manage.py send_stock_alerts              # both alerts
    python manage.py send_stock_alerts --type low_stock
    python manage.py send_stock_alerts --type expiry

Recommended cron (daily at 8 AM):
    0 8 * * * /path/to/venv/bin/python /path/to/manage.py send_stock_alerts
"""

from datetime import timedelta, date

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.db.models import F
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage

from company.models import Company
from inventory.models import Product, ProductBatch


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _attach_logo(msg):
    """Attach the CWS logo as an inline image referenced by cid:logo."""
    logo_path = finders.find('accounts/images/logo.png')
    if logo_path:
        with open(logo_path, 'rb') as f:
            mime_img = MIMEImage(f.read())
            mime_img.add_header('Content-ID', '<logo>')
            mime_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            msg.attach(mime_img)


def _send_html_email(subject, template_name, context, recipient_email):
    """Render an HTML email template and send it with an inline logo."""
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
#  Management Command
# ─────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        'Send low-stock and/or expiry stock email alerts to all active '
        'BUSINESS plan companies (Rs. 1299 plan).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['low_stock', 'expiry', 'both'],
            default='both',
            help=(
                'Which alert type to send: '
                '"low_stock", "expiry", or "both" (default: both).'
            ),
        )

    # ── Entry point ──────────────────────────
    def handle(self, *args, **options):
        alert_type = options['type']
        today = date.today()
        alert_date = today.strftime('%d %b %Y')

        self.stdout.write(self.style.NOTICE(
            f'[send_stock_alerts] Starting — type={alert_type}, date={alert_date}'
        ))

        # Fetch only BUSINESS plan companies with an active subscription
        business_companies = Company.objects.filter(
            plan_type='BUSINESS',
            is_subscription_active=True,
        ).select_related('owner')

        if not business_companies.exists():
            self.stdout.write(self.style.WARNING(
                'No active BUSINESS plan companies found. Exiting.'
            ))
            return

        self.stdout.write(
            f'Found {business_companies.count()} active BUSINESS plan company(ies).'
        )

        low_sent = low_skipped = low_errors = 0
        exp_sent = exp_skipped = exp_errors = 0

        for company in business_companies:
            owner = company.owner
            recipient = owner.email
            name = owner.first_name or owner.username

            # ── 1. LOW STOCK ALERT ──────────────────
            if alert_type in ('low_stock', 'both'):
                result = self._send_low_stock_alert(
                    company, name, recipient, alert_date
                )
                if result == 'sent':
                    low_sent += 1
                elif result == 'skipped':
                    low_skipped += 1
                else:
                    low_errors += 1

            # ── 2. EXPIRY STOCK ALERT ───────────────
            if alert_type in ('expiry', 'both'):
                result = self._send_expiry_alert(
                    company, name, recipient, alert_date
                )
                if result == 'sent':
                    exp_sent += 1
                elif result == 'skipped':
                    exp_skipped += 1
                else:
                    exp_errors += 1

        # ── Final summary ─────────────────────────
        if alert_type in ('low_stock', 'both'):
            self.stdout.write(self.style.SUCCESS(
                f'Low Stock Alerts  — Sent: {low_sent} | '
                f'Skipped (no items): {low_skipped} | Errors: {low_errors}'
            ))
        if alert_type in ('expiry', 'both'):
            self.stdout.write(self.style.SUCCESS(
                f'Expiry Alerts     — Sent: {exp_sent} | '
                f'Skipped (no items): {exp_skipped} | Errors: {exp_errors}'
            ))

    # ─────────────────────────────────────────
    #  Low Stock Alert
    # ─────────────────────────────────────────
    def _send_low_stock_alert(self, company, name, recipient, alert_date):
        """
        Find all products where stock_quantity <= low_stock_limit.
        Send an email if any are found; skip otherwise.
        Returns: 'sent' | 'skipped' | 'error'
        """
        low_stock_products = (
            Product.objects.filter(
                company=company,
                stock_quantity__lte=F('low_stock_limit'),
            )
            .values('name', 'sku', 'stock_quantity', 'low_stock_limit')
        )

        if not low_stock_products.exists():
            self.stdout.write(
                f'  [{company.name}] Low-stock: no products below threshold — skipped.'
            )
            return 'skipped'

        count = low_stock_products.count()
        dashboard_url = (
            getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            + '/inventory/alerts/'
        )

        context = {
            'name': name,
            'company_name': company.name,
            'low_stock_count': count,
            'low_stock_products': list(low_stock_products),
            'alert_date': alert_date,
            'dashboard_url': dashboard_url,
        }

        try:
            _send_html_email(
                subject=(
                    f'\u26a0\ufe0f Low Stock Alert \u2014 {count} product(s) '
                    f'need restocking | {company.name}'
                ),
                template_name='inventory/emails/low_stock_alert.html',
                context=context,
                recipient_email=recipient,
            )
            self.stdout.write(self.style.SUCCESS(
                f'  [{company.name}] Low-stock alert sent to {recipient} ({count} products).'
            ))
            return 'sent'

        except Exception as exc:
            self.stderr.write(
                f'  [{company.name}] ERROR sending low-stock alert to {recipient}: {exc}'
            )
            return 'error'

    # ─────────────────────────────────────────
    #  Expiry Stock Alert
    # ─────────────────────────────────────────
    def _send_expiry_alert(self, company, name, recipient, alert_date):
        """
        Find expired batches and batches expiring within 30 days.
        Send an email if any are found; skip otherwise.
        Returns: 'sent' | 'skipped' | 'error'
        """
        today = date.today()
        near_limit = today + timedelta(days=30)

        # Expired batches (expiry_date < today)
        expired_qs = (
            ProductBatch.objects.filter(
                company=company,
                is_active=True,
                expiry_date__lt=today,
            )
            .select_related('product')
            .order_by('expiry_date')
        )

        expired_batches = [
            {
                'product__name': b.product.name,
                'batch_number': b.batch_number,
                'expiry_date': b.expiry_date.strftime('%d %b %Y'),
                'quantity': b.quantity,
            }
            for b in expired_qs
        ]

        # Near-expiry batches (today <= expiry_date <= today + 30 days)
        near_expiry_qs = (
            ProductBatch.objects.filter(
                company=company,
                is_active=True,
                expiry_date__gte=today,
                expiry_date__lte=near_limit,
            )
            .select_related('product')
            .order_by('expiry_date')
        )

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
            self.stdout.write(
                f'  [{company.name}] Expiry: no expired/near-expiry batches — skipped.'
            )
            return 'skipped'

        dashboard_url = (
            getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            + '/inventory/reports/near-expiry/'
        )

        context = {
            'name': name,
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
                    f'\U0001f6a8 Expiry Stock Alert \u2014 '
                    f'{expired_count} expired, {near_expiry_count} near-expiry '
                    f'| {company.name}'
                ),
                template_name='inventory/emails/expiry_stock_alert.html',
                context=context,
                recipient_email=recipient,
            )
            self.stdout.write(self.style.SUCCESS(
                f'  [{company.name}] Expiry alert sent to {recipient} '
                f'({expired_count} expired, {near_expiry_count} near-expiry).'
            ))
            return 'sent'

        except Exception as exc:
            self.stderr.write(
                f'  [{company.name}] ERROR sending expiry alert to {recipient}: {exc}'
            )
            return 'error'