from django.db import models
from django.contrib.auth.models import User
from company.models import Company, Staff


class TrainingMaterial(models.Model):
    MATERIAL_TYPE_CHOICES = (
        ('VIDEO', 'Video'),
        ('DOCUMENT', 'Document'),
        ('PRESENTATION', 'Presentation'),
        ('QUIZ', 'Quiz'),
        ('MANUAL', 'Manual'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='training_materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, default='DOCUMENT')
    file_url = models.URLField(blank=True, null=True)
    file_upload = models.FileField(upload_to='training/materials/', blank=True, null=True)
    tags = models.CharField(max_length=200, blank=True, null=True, help_text="Comma-separated tags")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class TrainingRecord(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='training_records')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='training_records')
    material = models.ForeignKey(TrainingMaterial, on_delete=models.CASCADE, related_name='records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    completion_date = models.DateField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('staff', 'material')

    def __str__(self):
        return f"{self.staff.name} - {self.material.title}"


class StaffOnboarding(models.Model):
    STATUS_CHOICES = (
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='onboardings')
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE, related_name='onboarding')
    join_date = models.DateField()
    target_completion_date = models.DateField(blank=True, null=True)
    actual_completion_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_STARTED')
    mentor = models.ForeignKey(
        Staff, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mentored_onboardings'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-join_date']

    def __str__(self):
        return f"{self.staff.name} Onboarding"

    @property
    def completion_percentage(self):
        tasks = self.checklist_items.all()
        if not tasks.exists():
            return 0
        completed = tasks.filter(is_completed=True).count()
        return int((completed / tasks.count()) * 100)


class OnboardingChecklistItem(models.Model):
    onboarding = models.ForeignKey(StaffOnboarding, on_delete=models.CASCADE, related_name='checklist_items')
    task = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.task



class SupportTicket(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed'),
    )
    CATEGORY_CHOICES = (
        ('HARDWARE', 'Hardware'),
        ('SOFTWARE', 'Software'),
        ('NETWORK', 'Network'),
        ('ACCESS', 'Access & Permissions'),
        ('TRAINING', 'Training'),
        ('BILLING', 'Billing'),
        ('OTHER', 'Other'),
    )

    company = models.ForeignKey('company.Company', on_delete=models.CASCADE, related_name='support_tickets')
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')

    raised_by_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='raised_tickets'
    )

    resolution_notes = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import random, string
            self.ticket_id = 'TKT-' + ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id}: {self.title}"

    @property
    def is_closable_by_company(self):
        return self.status == 'RESOLVED'


class TicketComment(models.Model):
    AUTHOR_TYPE_CHOICES = (
        ('COMPANY', 'Company'),
        ('ADMIN', 'Admin'),
    )

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    author_type = models.CharField(max_length=10, choices=AUTHOR_TYPE_CHOICES)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.ticket.ticket_id} by {self.author}"