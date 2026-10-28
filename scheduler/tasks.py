from celery import shared_task
from scheduler.jobs import send_low_stock_alerts_job, send_expiry_stock_alerts_job
import logging

logger = logging.getLogger(__name__)


@shared_task(name='scheduler.tasks.send_low_stock_alerts_task')
def send_low_stock_alerts_task():
    """Celery task — sends low stock alert emails to all BUSINESS plan companies."""
    logger.info('[Celery] send_low_stock_alerts_task triggered')
    send_low_stock_alerts_job()


@shared_task(name='scheduler.tasks.send_expiry_stock_alerts_task')
def send_expiry_stock_alerts_task():
    """Celery task — sends expiry stock alert emails to all BUSINESS plan companies."""
    logger.info('[Celery] send_expiry_stock_alerts_task triggered')
    send_expiry_stock_alerts_job()