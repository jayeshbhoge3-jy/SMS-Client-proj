from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from company.currency_data import CURRENCY_CHOICES
import re

 
def validate_gst(value):
    gst_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(gst_regex, value):
        raise ValidationError("Invalid GST format (Example: 22AAAAA0000A1Z5)")

class Company(models.Model):

    PLAN_CHOICES = (
        ('TRIAL', 'Trial'),
        ('STARTER', 'Starter'),
        ('BUSINESS', 'Business'),
        ('PREMIUM', 'Premium'),
    )

    CURRENCY_CHOICES = CURRENCY_CHOICES

    LANGUAGE_CHOICES = (
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('mr', 'Marathi'),
        ('gu', 'Gujarati'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('kn', 'Kannada'),
        ('fr', 'French'),
        ('es', 'Spanish'),
    )

    name = models.CharField(max_length=50,unique=True)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    display_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    email = models.EmailField()
    phone = models.CharField(max_length=10, unique=True, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=15, validators=[validate_gst], blank=True, null=True)
    logo = models.ImageField(upload_to='company_logo/', blank=True, null=True)

    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="company_owner"
    )

    plan_type = models.CharField(max_length=20,choices=PLAN_CHOICES,default='TRIAL')
    is_subscription_active = models.BooleanField(default=False)
    subscription_start = models.DateTimeField(blank=True,null=True)
    subscription_end = models.DateTimeField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class Transaction(models.Model):
    STATUS_CHOICES = (
        ("DELIVERED", "Delivered"),
        ("PROCESSING", "Processing"),
        ("CANCELLED", "Cancelled"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    ref_id = models.CharField(max_length=20, unique=True)
    item_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ref_id
    

def validate_name(value):
    value = value.strip()

    if not value:
        raise ValidationError("This field cannot be empty.")

    if len(value) > 20:
        raise ValidationError("Maximum 20 characters allowed.")

    if not re.match(r'^[A-Za-z]+$', value):
        raise ValidationError("Only alphabetic characters are allowed.")


def validate_name(value):
    if not re.match(r'^[A-Za-z]+$', value):
        raise ValidationError("Only alphabetic characters are allowed.")

def validate_name(value):
    if not re.match(r'^[A-Za-z]+$', value):
        raise ValidationError("Only alphabetic characters are allowed.")

def validate_name(value):
    if not re.match(r'^[A-Za-z]+$', value):
        raise ValidationError("Only alphabetic characters are allowed.")





class Vendor(models.Model):

    company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        related_name='vendors',
        null=True, blank=True
    )

    salutation = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    primary_contact_first_name = models.CharField(
        max_length=20,
        validators=[validate_name]
    )

    primary_contact_last_name = models.CharField(
        max_length=20,
        validators=[validate_name]
    )

    company_name = models.CharField(
        max_length=100,
        db_index=True
    )

    display_name = models.CharField(
        max_length=100
    )

    gst_number = models.CharField(
        max_length=15,
        validators=[validate_gst],
        db_index=True,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    mobile = models.CharField(
        max_length=10
    )

    language = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    address = models.TextField(
        max_length=300
    )

    
    # SYSTEM FIELDS
    

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    
    # META OPTIONS
    

    class Meta:
        unique_together = ['company', 'gst_number']
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['company']),
            models.Index(fields=['gst_number']),
        ]

    
    # SAVE METHOD
    

    def save(self, *args, **kwargs):

        if self.gst_number:
            self.gst_number = self.gst_number.upper().strip()

        self.full_clean()
        super().save(*args, **kwargs)

    
    # STRING REPRESENTATION
    

    def __str__(self):
        return f"{self.company_name} - {self.display_name}"



from django.contrib.auth.models import User  # already imported at top of models.py

import uuid  # ← add at the very top of models.py

class Staff(models.Model):
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="staff"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_profile',
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True)   # ← ADD
    invite_accepted = models.BooleanField(default=False)               # ← ADD
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

from django.db import models
from company.models import Company

class NewEntry(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    entry_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.entry_name
    

class Payment(models.Model):

    PLAN_CHOICES = (
        ('STARTER', 'Starter'),
        ('BUSINESS', 'Business'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    plan_name = models.CharField(max_length=100,choices=PLAN_CHOICES)
    order_id = models.CharField(max_length=200,unique=True)
    payment_id = models.CharField(max_length=200,unique=True)
    razorpay_signature = models.TextField()
    payment_status = models.CharField(max_length=50)
    amount = models.IntegerField()
    currency = models.CharField(max_length=10,default="INR")
    is_verified = models.BooleanField(default=False)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.payment_id



class Transport(models.Model):
    TRANSPORT_TYPE_CHOICES = (
        ('OWN', 'Own Vehicle'),
        ('THIRD_PARTY', 'Third Party'),
        ('EV', 'E-Vehicle'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='transports'
    )

    vehicle_number = models.CharField(max_length=30)
    driver_name = models.CharField(max_length=100)
    driver_mobile = models.CharField(max_length=15)

    transport_type = models.CharField(
        max_length=20,
        choices=TRANSPORT_TYPE_CHOICES,
        default='OWN'
    )

    source_location = models.CharField(max_length=200)
    destination_location = models.CharField(max_length=200)

    dispatch_date = models.DateField()
    expected_delivery_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_number} - {self.driver_name}"
    

from django.contrib.auth.models import User

class PasswordHistory(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    password = models.CharField(
        max_length=255
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username

class StaffActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'), ('EDIT', 'Edit'), ('VIEW', 'View'),
        ('DELETE_REQUEST', 'Delete Request'), ('DELETE', 'Delete'),
    ]
    MODULE_CHOICES = [
        ('PRODUCT', 'Product'), ('CATEGORY', 'Category'),
        ('PO', 'Purchase Order'), ('SO', 'Sales Order'), ('CUSTOMER', 'Customer'),
    ]
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='staff_activity_logs')
    staff = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=255)
    extra_data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class StaffDeleteRequest(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]
    MODULE_CHOICES = [
        ('PRODUCT', 'Product'), ('CATEGORY', 'Category'),
        ('PO', 'Purchase Order'), ('SO', 'Sales Order'), ('CUSTOMER', 'Customer'),
    ]
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='delete_requests')
    requested_by = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='delete_requests')
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    object_id = models.IntegerField()
    object_repr = models.CharField(max_length=255)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']