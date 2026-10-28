from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('company', '0011_company_phone'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainingMaterial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('material_type', models.CharField(choices=[('VIDEO', 'Video'), ('DOCUMENT', 'Document'), ('PRESENTATION', 'Presentation'), ('QUIZ', 'Quiz'), ('MANUAL', 'Manual')], default='DOCUMENT', max_length=20)),
                ('file_url', models.URLField(blank=True, null=True)),
                ('file_upload', models.FileField(blank=True, null=True, upload_to='training/materials/')),
                ('tags', models.CharField(blank=True, help_text='Comma-separated tags', max_length=200, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_materials', to='company.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='TrainingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('completion_date', models.DateField(blank=True, null=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_records', to='company.company')),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='training.trainingmaterial')),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='training_records', to='company.staff')),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('staff', 'material')}},
        ),
        migrations.CreateModel(
            name='StaffOnboarding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('join_date', models.DateField()),
                ('target_completion_date', models.DateField(blank=True, null=True)),
                ('actual_completion_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('NOT_STARTED', 'Not Started'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed')], default='NOT_STARTED', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='onboardings', to='company.company')),
                ('mentor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mentored_onboardings', to='company.staff')),
                ('staff', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='onboarding', to='company.staff')),
            ],
            options={'ordering': ['-join_date']},
        ),
        migrations.CreateModel(
            name='OnboardingChecklistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task', models.CharField(max_length=200)),
                ('is_completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('onboarding', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checklist_items', to='training.staffonboarding')),
            ],
            options={'ordering': ['order']},
        ),
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.CharField(editable=False, max_length=20, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('category', models.CharField(choices=[('HARDWARE', 'Hardware'), ('SOFTWARE', 'Software'), ('NETWORK', 'Network'), ('ACCESS', 'Access & Permissions'), ('TRAINING', 'Training'), ('OTHER', 'Other')], default='OTHER', max_length=20)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM', max_length=10)),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], default='OPEN', max_length=20)),
                ('resolution_notes', models.TextField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to='company.staff')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to='company.company')),
                ('raised_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='raised_tickets', to='company.staff')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
