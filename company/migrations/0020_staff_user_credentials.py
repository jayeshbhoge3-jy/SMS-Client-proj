"""
Migration 0020 — re-add `user` OneToOneField on Staff so each staff member
has a linked Django auth User for login.

Place this file at:
  SMS/company/migrations/0020_staff_user_credentials.py
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0019_remove_staff_invite_accepted_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='staff',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='staff_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='staff',
            name='username',
            field=models.CharField(
                blank=True,
                max_length=150,
                help_text='Auto-generated login username shown to the company owner.',
            ),
        ),
        migrations.AddField(
            model_name='staff',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]