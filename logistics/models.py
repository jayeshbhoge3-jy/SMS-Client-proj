from django.db import models
from django.contrib.auth.models import User
from company.models import Company, Staff
from django.core.validators import MinValueValidator
import uuid


# ─────────────────────────── DRIVER ───────────────────────────

class Driver(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('ON_LEAVE', 'On Leave'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='drivers')
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    license_expiry = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    joined_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'phone'],
                name='unique_driver_phone_per_company'
            ),
            models.UniqueConstraint(
                fields=['company', 'license_number'],
                name='unique_driver_license_per_company',
                condition=~models.Q(license_number=None) & ~models.Q(license_number=''),
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.status == 'ACTIVE'


# ─────────────────────────── E-VEHICLE ───────────────────────────

class EVehicle(models.Model):
    TYPE_CHOICES = (
        ('TWO_WHEELER', 'Two Wheeler (E-Bike / E-Scooter)'),
        ('THREE_WHEELER', 'Three Wheeler (E-Auto / Cargo Trike)'),
        ('FOUR_WHEELER', 'Four Wheeler (E-Van / E-Car)'),
        ('CARGO_VAN', 'Cargo E-Van'),
        ('MINI_TRUCK', 'Mini E-Truck'),
    )

    STATUS_CHOICES = (
        ('AVAILABLE', 'Available'),
        ('IN_USE', 'In Use'),
        ('CHARGING', 'Charging'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('INACTIVE', 'Inactive'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='evehicles')
    vehicle_id = models.CharField(max_length=20, unique=True, help_text="e.g. EV-001")
    vehicle_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    registration_number = models.CharField(max_length=20, unique=True)
    model_name = models.CharField(max_length=100, help_text="e.g. Tata Ace EV, Ather 450X")
    manufacturer = models.CharField(max_length=100)

    battery_capacity_kwh = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Battery capacity in kWh"
    )
    range_per_charge_km = models.PositiveIntegerField(help_text="Estimated range per full charge (km)")
    current_battery_percent = models.PositiveIntegerField(
        default=100,
        help_text="Current battery level (0–100)"
    )

    assigned_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_vehicles'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    last_charged_at = models.DateTimeField(null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['vehicle_id']

    def __str__(self):
        return f"{self.vehicle_id} – {self.model_name} ({self.registration_number})"

    @property
    def is_low_battery(self):
        return self.current_battery_percent < 20

    @property
    def estimated_remaining_km(self):
        return int((self.current_battery_percent / 100) * self.range_per_charge_km)


# ─────────────────────────── DELIVERY ORDER ───────────────────────────

class DeliveryOrder(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='delivery_orders')
    order_number = models.CharField(max_length=30, unique=True, editable=False)

    # Recipient
    recipient_name = models.CharField(max_length=150)
    recipient_phone = models.CharField(max_length=15)
    recipient_email = models.EmailField(blank=True, null=True)
    delivery_address = models.TextField()
    pickup_address = models.TextField(blank=True, null=True, help_text="Leave blank if picking up from company")
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    # Assignment
    assigned_vehicle = models.ForeignKey(
        EVehicle,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries'
    )
    assigned_driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries'
    )

    # Details
    package_description = models.CharField(max_length=300)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Dates
    scheduled_date = models.DateField()
    scheduled_time_slot = models.CharField(max_length=50, blank=True, help_text="e.g. 10:00 AM – 12:00 PM")
    delivered_at = models.DateTimeField(null=True, blank=True)
    estimated_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Proof
    delivery_notes = models.TextField(blank=True, null=True)
    failure_reason = models.CharField(max_length=300, blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"DO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} → {self.recipient_name}"


# ─────────────────────────── DELIVERY TRACKING ───────────────────────────

class DeliveryTracking(models.Model):
    EVENT_CHOICES = (
        ('ORDER_CREATED', 'Order Created'),
        ('ASSIGNED', 'Driver & Vehicle Assigned'),
        ('PICKED_UP', 'Package Picked Up'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered Successfully'),
        ('FAILED_ATTEMPT', 'Delivery Attempt Failed'),
        ('RETURNED', 'Returned to Sender'),
        ('CANCELLED', 'Cancelled'),
    )

    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.CASCADE,
        related_name='tracking_events'
    )
    event = models.CharField(max_length=30, choices=EVENT_CHOICES)
    description = models.CharField(max_length=300, blank=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.delivery_order.order_number} – {self.get_event_display()}"


# ─────────────────────────── CHARGING LOG ───────────────────────────

class ChargingLog(models.Model):
    vehicle = models.ForeignKey(EVehicle, on_delete=models.CASCADE, related_name='charging_logs')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='charging_logs')
    charged_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    battery_before = models.PositiveIntegerField(help_text="Battery % before charging")
    battery_after = models.PositiveIntegerField(help_text="Battery % after charging")
    units_consumed_kwh = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    charging_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    charged_at = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-charged_at']

    def __str__(self):
        return f"{self.vehicle.vehicle_id} charged on {self.charged_at.strftime('%d %b %Y')}"


# ─────────────────────────── VEHICLE MAINTENANCE ───────────────────────────

class VehicleMaintenance(models.Model):
    TYPE_CHOICES = (
        ('BATTERY_CHECK', 'Battery Check'),
        ('TYRE_CHANGE', 'Tyre Change'),
        ('BRAKE_SERVICE', 'Brake Service'),
        ('GENERAL_SERVICE', 'General Service'),
        ('MOTOR_CHECK', 'Motor Check'),
        ('ACCIDENTAL_REPAIR', 'Accidental Repair'),
        ('OTHER', 'Other'),
    )

    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    vehicle = models.ForeignKey(EVehicle, on_delete=models.CASCADE, related_name='maintenance_logs')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='maintenance_logs')
    maintenance_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vendor_name = models.CharField(max_length=150, blank=True, null=True)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.vehicle.vehicle_id} – {self.get_maintenance_type_display()}"