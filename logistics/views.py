from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from company.models import Company, Staff
from .models import Driver, EVehicle, DeliveryOrder, DeliveryTracking, ChargingLog, VehicleMaintenance


# ──────────────────────── HELPER ────────────────────────

def get_company(request):
    """Return company for owner or staff-linked user."""
    try:
        return Company.objects.get(owner=request.user)
    except Company.DoesNotExist:
        pass
    try:
        return request.user.staff.company
    except Exception:
        return None


def is_owner(request, company):
    """Return True if the logged-in user is the company owner."""
    return company is not None and company.owner == request.user


def find_duplicate_driver_field(company, phone, email, license_number, exclude_pk=None):
    """
    Returns an error message if phone, email, or license_number already
    exists for another driver in this company, else None.
    """
    qs = Driver.objects.filter(company=company)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if phone and qs.filter(phone=phone).exists():
        return "A driver with this phone number already exists."
    if email and qs.filter(email__iexact=email).exists():
        return "A driver with this email address already exists."
    if license_number and qs.filter(license_number__iexact=license_number).exists():
        return "A driver with this license number already exists."
    return None


# ──────────────────────── DASHBOARD ────────────────────────

@login_required
def logistics_dashboard(request):
    company = get_company(request)
    if company is None:
        return redirect('admin_dashboard')

    total_vehicles       = EVehicle.objects.filter(company=company).count()
    available_vehicles   = EVehicle.objects.filter(company=company, status='AVAILABLE').count()
    in_use_vehicles      = EVehicle.objects.filter(company=company, status='IN_USE').count()
    low_battery_vehicles = EVehicle.objects.filter(company=company, current_battery_percent__lt=20).count()

    pending_deliveries    = DeliveryOrder.objects.filter(company=company, status='PENDING').count()
    in_transit_deliveries = DeliveryOrder.objects.filter(company=company, status='IN_TRANSIT').count()
    delivered_today       = DeliveryOrder.objects.filter(
        company=company,
        status='DELIVERED',
        delivered_at__date=timezone.now().date()
    ).count()
    failed_deliveries = DeliveryOrder.objects.filter(company=company, status='FAILED').count()

    upcoming_maintenance = VehicleMaintenance.objects.filter(
        company=company,
        status='SCHEDULED',
        scheduled_date__gte=timezone.now().date()
    ).order_by('scheduled_date')[:5]

    recent_deliveries = DeliveryOrder.objects.filter(company=company).order_by('-created_at')[:6]
    vehicles          = EVehicle.objects.filter(company=company).order_by('status')[:6]

    return render(request, 'logistics/dashboard.html', {
        'company':              company,
        'is_owner':             is_owner(request, company),   # ← FIXED
        'total_vehicles':       total_vehicles,
        'available_vehicles':   available_vehicles,
        'in_use_vehicles':      in_use_vehicles,
        'low_battery_vehicles': low_battery_vehicles,
        'pending_deliveries':   pending_deliveries,
        'in_transit_deliveries':in_transit_deliveries,
        'delivered_today':      delivered_today,
        'failed_deliveries':    failed_deliveries,
        'upcoming_maintenance': upcoming_maintenance,
        'recent_deliveries':    recent_deliveries,
        'vehicles':             vehicles,
    })


# ──────────────────────── E-VEHICLE CRUD ────────────────────────

@login_required
def vehicle_list(request):
    company       = get_company(request)
    q             = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    type_filter   = request.GET.get('type', '')

    vehicles = EVehicle.objects.filter(company=company)

    if q:
        vehicles = vehicles.filter(
            Q(vehicle_id__icontains=q) |
            Q(registration_number__icontains=q) |
            Q(model_name__icontains=q)
        )
    if status_filter:
        vehicles = vehicles.filter(status=status_filter)
    if type_filter:
        vehicles = vehicles.filter(vehicle_type=type_filter)

    return render(request, 'logistics/vehicle_list.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),   # ← FIXED
        'vehicles':       vehicles,
        'q':              q,
        'status_filter':  status_filter,
        'type_filter':    type_filter,
        'status_choices': EVehicle.STATUS_CHOICES,
        'type_choices':   EVehicle.TYPE_CHOICES,
    })


@login_required
def vehicle_add(request):
    company    = get_company(request)
    drivers    = Driver.objects.filter(company=company, status='ACTIVE')

    if request.method == 'POST':
        data = request.POST
        
        if EVehicle.objects.filter(vehicle_id=data['vehicle_id']).exists():
            messages.error(request, "Vehicle ID already exists.")
            return render(request, 'logistics/vehicle_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'drivers':        drivers,
                'status_choices': EVehicle.STATUS_CHOICES,
                'type_choices':   EVehicle.TYPE_CHOICES,
                'action':         'Add',
                'vehicle':        data,
            })

        if EVehicle.objects.filter(registration_number=data['registration_number']).exists():
            messages.error(request, "Registration Number already exists.")
            return render(request, 'logistics/vehicle_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'drivers':        drivers,
                'status_choices': EVehicle.STATUS_CHOICES,
                'type_choices':   EVehicle.TYPE_CHOICES,
                'action':         'Add',
                'vehicle':        data,
            })

        try:
            EVehicle.objects.create(
                company=company,
                vehicle_id=data['vehicle_id'],
                vehicle_type=data['vehicle_type'],
                registration_number=data['registration_number'],
                model_name=data['model_name'],
                manufacturer=data['manufacturer'],
                battery_capacity_kwh=data['battery_capacity_kwh'],
                range_per_charge_km=data['range_per_charge_km'],
                current_battery_percent=data.get('current_battery_percent', 100),
                assigned_driver_id=data.get('assigned_driver') or None,
                status=data.get('status', 'AVAILABLE'),
                purchase_date=data.get('purchase_date') or None,
                insurance_expiry=data.get('insurance_expiry') or None,
                notes=data.get('notes', ''),
            )
            messages.success(request, "E-Vehicle added successfully.")
            return redirect('vehicle_list')
        except Exception as e:
            messages.error(request, f"Error adding vehicle: {e}")

    return render(request, 'logistics/vehicle_form.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),   # ← FIXED
        'drivers':        drivers,
        'status_choices': EVehicle.STATUS_CHOICES,
        'type_choices':   EVehicle.TYPE_CHOICES,
        'action':         'Add',
    })


@login_required
def vehicle_edit(request, pk):
    company    = get_company(request)
    vehicle    = get_object_or_404(EVehicle, pk=pk, company=company)
    drivers    = Driver.objects.filter(company=company, status='ACTIVE')

    if request.method == 'POST':
        data = request.POST
        
        if EVehicle.objects.exclude(pk=vehicle.pk).filter(vehicle_id=data['vehicle_id']).exists():
            messages.error(request, "Vehicle ID already exists.")
            return render(request, 'logistics/vehicle_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'vehicle':        vehicle,
                'drivers':        drivers,
                'status_choices': EVehicle.STATUS_CHOICES,
                'type_choices':   EVehicle.TYPE_CHOICES,
                'action':         'Edit',
            })

        if EVehicle.objects.exclude(pk=vehicle.pk).filter(registration_number=data['registration_number']).exists():
            messages.error(request, "Registration Number already exists.")
            return render(request, 'logistics/vehicle_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'vehicle':        vehicle,
                'drivers':        drivers,
                'status_choices': EVehicle.STATUS_CHOICES,
                'type_choices':   EVehicle.TYPE_CHOICES,
                'action':         'Edit',
            })

        try:
            vehicle.vehicle_id              = data['vehicle_id']
            vehicle.vehicle_type            = data['vehicle_type']
            vehicle.registration_number     = data['registration_number']
            vehicle.model_name              = data['model_name']
            vehicle.manufacturer            = data['manufacturer']
            vehicle.battery_capacity_kwh    = data['battery_capacity_kwh']
            vehicle.range_per_charge_km     = data['range_per_charge_km']
            vehicle.current_battery_percent = data.get('current_battery_percent', 100)
            vehicle.assigned_driver_id      = data.get('assigned_driver') or None
            vehicle.status                  = data.get('status', vehicle.status)
            vehicle.purchase_date           = data.get('purchase_date') or None
            vehicle.insurance_expiry        = data.get('insurance_expiry') or None
            vehicle.notes                   = data.get('notes', '')
            vehicle.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect('vehicle_list')
        except Exception as e:
            messages.error(request, f"Error updating vehicle: {e}")

    return render(request, 'logistics/vehicle_form.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),   # ← FIXED
        'vehicle':        vehicle,
        'drivers':        drivers,
        'status_choices': EVehicle.STATUS_CHOICES,
        'type_choices':   EVehicle.TYPE_CHOICES,
        'action':         'Edit',
    })


@login_required
def vehicle_delete(request, pk):
    company = get_company(request)
    if not is_owner(request, company):
        messages.error(request, "Only the company owner can delete vehicles.")
        return redirect('vehicle_list')
    vehicle = get_object_or_404(EVehicle, pk=pk, company=company)
    if request.method == 'POST':
        vehicle.delete()
        messages.success(request, "Vehicle deleted.")
    return redirect('vehicle_list')


# ──────────────────────── DELIVERY ORDERS ────────────────────────

@login_required
def delivery_list(request):
    company         = get_company(request)
    q               = request.GET.get('q', '')
    status_filter   = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')

    deliveries = DeliveryOrder.objects.filter(company=company)

    if q:
        deliveries = deliveries.filter(
            Q(order_number__icontains=q) |
            Q(recipient_name__icontains=q) |
            Q(recipient_phone__icontains=q)
        )
    if status_filter:
        deliveries = deliveries.filter(status=status_filter)
    if priority_filter:
        deliveries = deliveries.filter(priority=priority_filter)

    return render(request, 'logistics/delivery_list.html', {
        'company':          company,
        'is_owner':         is_owner(request, company),   # ← FIXED
        'deliveries':       deliveries,
        'q':                q,
        'status_filter':    status_filter,
        'priority_filter':  priority_filter,
        'status_choices':   DeliveryOrder.STATUS_CHOICES,
        'priority_choices': DeliveryOrder.PRIORITY_CHOICES,
    })


@login_required
def delivery_add(request):
    company    = get_company(request)
    vehicles   = EVehicle.objects.filter(company=company, status='AVAILABLE')
    drivers    = Driver.objects.filter(company=company, status='ACTIVE')

    if request.method == 'POST':
        data = request.POST
        try:
            order = DeliveryOrder.objects.create(
                company=company,
                recipient_name=data['recipient_name'],
                recipient_phone=data['recipient_phone'],
                recipient_email=data.get('recipient_email', ''),
                delivery_address=data['delivery_address'],
                pickup_address=data.get('pickup_address', ''),
                city=data.get('city', ''),
                pincode=data.get('pincode', ''),
                assigned_vehicle_id=data.get('assigned_vehicle') or None,
                assigned_driver_id=data.get('assigned_driver') or None,
                package_description=data['package_description'],
                weight_kg=data.get('weight_kg', 0),
                priority=data.get('priority', 'NORMAL'),
                scheduled_date=data['scheduled_date'],
                scheduled_time_slot=data.get('scheduled_time_slot', ''),
                estimated_distance_km=data.get('estimated_distance_km', 0),
                delivery_notes=data.get('delivery_notes', ''),
                created_by=request.user,
            )
            DeliveryTracking.objects.create(
                delivery_order=order,
                event='ORDER_CREATED',
                description='Order created via Logistics module.',
                recorded_by=request.user,
            )
            if order.assigned_vehicle:
                order.assigned_vehicle.status = 'IN_USE'
                order.assigned_vehicle.save()
                order.status = 'ASSIGNED'
                order.save()
                DeliveryTracking.objects.create(
                    delivery_order=order,
                    event='ASSIGNED',
                    description=f'Assigned to {order.assigned_driver} on vehicle {order.assigned_vehicle.vehicle_id}',
                    recorded_by=request.user,
                )
            messages.success(request, f"Delivery order {order.order_number} created.")
            return redirect('delivery_list')
        except Exception as e:
            messages.error(request, f"Error creating order: {e}")

    return render(request, 'logistics/delivery_form.html', {
        'company':          company,
        'is_owner':         is_owner(request, company),   # ← FIXED
        'vehicles':         vehicles,
        'drivers':          drivers,
        'priority_choices': DeliveryOrder.PRIORITY_CHOICES,
        'action':           'New',
    })


@login_required
def delivery_detail(request, pk):
    company  = get_company(request)
    order    = get_object_or_404(DeliveryOrder, pk=pk, company=company)
    tracking = order.tracking_events.order_by('timestamp')
    return render(request, 'logistics/delivery_detail.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),   # ← FIXED
        'order':          order,
        'tracking':       tracking,
        'status_choices': DeliveryOrder.STATUS_CHOICES,
    })


@login_required
def delivery_update_status(request, pk):
    company = get_company(request)
    order   = get_object_or_404(DeliveryOrder, pk=pk, company=company)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        note       = request.POST.get('note', '')
        location   = request.POST.get('location', '')

        event_map = {
            'IN_TRANSIT':       'IN_TRANSIT',
            'OUT_FOR_DELIVERY': 'OUT_FOR_DELIVERY',
            'DELIVERED':        'DELIVERED',
            'FAILED':           'FAILED_ATTEMPT',
            'RETURNED':         'RETURNED',
            'CANCELLED':        'CANCELLED',
        }

        order.status = new_status
        if new_status == 'DELIVERED':
            order.delivered_at = timezone.now()
            if order.assigned_vehicle:
                order.assigned_vehicle.status = 'AVAILABLE'
                order.assigned_vehicle.save()
        elif new_status == 'OUT_FOR_DELIVERY':
            if order.assigned_vehicle and order.assigned_vehicle.status != 'IN_USE':
                order.assigned_vehicle.status = 'IN_USE'
                order.assigned_vehicle.save()
        if new_status in ('FAILED', 'CANCELLED', 'RETURNED'):
            order.failure_reason = note
            if order.assigned_vehicle:
                order.assigned_vehicle.status = 'AVAILABLE'
                order.assigned_vehicle.save()
        order.save()

        DeliveryTracking.objects.create(
            delivery_order=order,
            event=event_map.get(new_status, 'IN_TRANSIT'),
            description=note,
            location=location,
            recorded_by=request.user,
        )
        messages.success(request, f"Order status updated to {new_status}.")

    return redirect('delivery_detail', pk=pk)


# ──────────────────────── CHARGING LOG ────────────────────────

@login_required
def charging_log_list(request):
    company  = get_company(request)
    logs     = ChargingLog.objects.filter(company=company).select_related('vehicle', 'charged_by')
    vehicles = EVehicle.objects.filter(company=company)
    return render(request, 'logistics/charging_log.html', {
        'company':  company,
        'is_owner': is_owner(request, company),   # ← FIXED
        'logs':     logs,
        'vehicles': vehicles,
    })


@login_required
def charging_log_add(request):
    company = get_company(request)
    if request.method == 'POST':
        data    = request.POST
        vehicle = get_object_or_404(EVehicle, pk=data['vehicle'], company=company)
        try:
            ChargingLog.objects.create(
                vehicle=vehicle,
                company=company,
                charged_by_id=data.get('charged_by') or None,
                battery_before=data['battery_before'],
                battery_after=data['battery_after'],
                units_consumed_kwh=data.get('units_consumed_kwh', 0),
                charging_cost=data.get('charging_cost', 0),
                charged_at=data['charged_at'],
                notes=data.get('notes', ''),
            )
            vehicle.current_battery_percent = data['battery_after']
            vehicle.last_charged_at = timezone.now()
            if vehicle.status == 'CHARGING':
                vehicle.status = 'AVAILABLE'
            vehicle.save()
            messages.success(request, "Charging log added and vehicle battery updated.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('charging_log_list')


# ──────────────────────── MAINTENANCE ────────────────────────

@login_required
def maintenance_list(request):
    company    = get_company(request)
    logs       = VehicleMaintenance.objects.filter(company=company).select_related('vehicle')
    vehicles   = EVehicle.objects.filter(company=company)
    drivers    = Driver.objects.filter(company=company, status='ACTIVE')
    return render(request, 'logistics/maintenance_list.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),   # ← FIXED
        'logs':           logs,
        'vehicles':       vehicles,
        'drivers':        drivers,
        'type_choices':   VehicleMaintenance.TYPE_CHOICES,
        'status_choices': VehicleMaintenance.STATUS_CHOICES,
    })


@login_required
def maintenance_add(request):
    company = get_company(request)
    if request.method == 'POST':
        data    = request.POST
        vehicle = get_object_or_404(EVehicle, pk=data['vehicle'], company=company)
        try:
            VehicleMaintenance.objects.create(
                vehicle=vehicle,
                company=company,
                maintenance_type=data['maintenance_type'],
                status=data.get('status', 'SCHEDULED'),
                description=data.get('description', ''),
                cost=data.get('cost', 0),
                vendor_name=data.get('vendor_name', ''),
                scheduled_date=data['scheduled_date'],
                completed_date=data.get('completed_date') or None,
                created_by=request.user,
            )
            if data.get('status') == 'IN_PROGRESS':
                vehicle.status = 'MAINTENANCE'
                vehicle.save()
            messages.success(request, "Maintenance record added.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
    return redirect('maintenance_list')


@login_required
def maintenance_update(request, pk):
    company = get_company(request)
    record  = get_object_or_404(VehicleMaintenance, pk=pk, company=company)
    if request.method == 'POST':
        new_status       = request.POST.get('status', record.status)
        record.status    = new_status
        record.cost      = request.POST.get('cost', record.cost)
        record.description = request.POST.get('description', record.description)
        if new_status == 'COMPLETED':
            record.completed_date = timezone.now().date()
            if record.vehicle.status == 'MAINTENANCE':
                record.vehicle.status = 'AVAILABLE'
                record.vehicle.save()
        record.save()
        messages.success(request, "Maintenance updated.")
    return redirect('maintenance_list')

# ──────────────────────── DRIVERS ────────────────────────

@login_required
def driver_list(request):
    company = get_company(request)
    q             = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    drivers = Driver.objects.filter(company=company)

    if q:
        drivers = drivers.filter(
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(license_number__icontains=q)
        )
    if status_filter:
        drivers = drivers.filter(status=status_filter)

    return render(request, 'logistics/driver_list.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),
        'drivers':        drivers,
        'q':              q,
        'status_filter':  status_filter,
        'status_choices': Driver.STATUS_CHOICES,
    })


@login_required
def driver_add(request):
    company = get_company(request)

    if request.method == 'POST':
        data = request.POST
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        license_number = data.get('license_number', '').strip()

        dup_error = find_duplicate_driver_field(company, phone, email, license_number)
        if dup_error:
            messages.error(request, dup_error)
            return render(request, 'logistics/driver_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'status_choices': Driver.STATUS_CHOICES,
                'action':         'Add',
                'driver':         data,
            })

        try:
            Driver.objects.create(
                company=company,
                name=data['name'],
                phone=phone,
                email=email or None,
                license_number=license_number,
                license_expiry=data.get('license_expiry') or None,
                address=data.get('address', ''),
                status=data.get('status', 'ACTIVE'),
                joined_date=data.get('joined_date') or None,
                notes=data.get('notes', ''),
            )
            messages.success(request, "Driver added successfully.")
            return redirect('driver_list')
        except Exception as e:
            messages.error(request, f"Error adding driver: {e}")

    return render(request, 'logistics/driver_form.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),
        'status_choices': Driver.STATUS_CHOICES,
        'action':         'Add',
    })


@login_required
def driver_edit(request, pk):
    company = get_company(request)
    driver  = get_object_or_404(Driver, pk=pk, company=company)

    if request.method == 'POST':
        data = request.POST
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        license_number = data.get('license_number', '').strip()

        dup_error = find_duplicate_driver_field(company, phone, email, license_number, exclude_pk=driver.pk)
        if dup_error:
            messages.error(request, dup_error)
            return render(request, 'logistics/driver_form.html', {
                'company':        company,
                'is_owner':       is_owner(request, company),
                'driver':         driver,
                'status_choices': Driver.STATUS_CHOICES,
                'action':         'Edit',
            })

        try:
            driver.name            = data['name']
            driver.phone           = phone
            driver.email           = email or None
            driver.license_number  = license_number
            driver.license_expiry  = data.get('license_expiry') or None
            driver.address         = data.get('address', '')
            driver.status          = data.get('status', driver.status)
            driver.joined_date     = data.get('joined_date') or None
            driver.notes           = data.get('notes', '')
            driver.save()
            messages.success(request, "Driver updated successfully.")
            return redirect('driver_list')
        except Exception as e:
            messages.error(request, f"Error updating driver: {e}")

    return render(request, 'logistics/driver_form.html', {
        'company':        company,
        'is_owner':       is_owner(request, company),
        'driver':         driver,
        'status_choices': Driver.STATUS_CHOICES,
        'action':         'Edit',
    })


@login_required
def driver_delete(request, pk):
    company = get_company(request)
    if not is_owner(request, company):
        messages.error(request, "Only the company owner can delete drivers.")
        return redirect('driver_list')
    driver = get_object_or_404(Driver, pk=pk, company=company)
    if request.method == 'POST':
        driver.delete()
        messages.success(request, "Driver deleted.")
    return redirect('driver_list')