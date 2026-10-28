import uuid
from django.db import migrations, models


def populate_invite_tokens(apps, schema_editor):
    Staff = apps.get_model('company', 'Staff')
    for staff in Staff.objects.all():
        staff.invite_token = uuid.uuid4()
        staff.save(update_fields=['invite_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0021_alter_staff_username'),
    ]

    operations = [
        # Step 1: add invite_token WITHOUT unique, so existing rows don't conflict
        migrations.AddField(
            model_name='staff',
            name='invite_token',
            field=models.UUIDField(default=uuid.uuid4, unique=False),
        ),
        # Step 2: assign a distinct UUID to every existing row
        migrations.RunPython(populate_invite_tokens, migrations.RunPython.noop),
        # Step 3: now it's safe to enforce uniqueness
        migrations.AlterField(
            model_name='staff',
            name='invite_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
        # Step 4: add invite_accepted (no uniqueness issue here)
        migrations.AddField(
            model_name='staff',
            name='invite_accepted',
            field=models.BooleanField(default=False),
        ),
    ]