from django.contrib import admin
from .models import Driver, EVehicle, DeliveryOrder, DeliveryTracking, ChargingLog, VehicleMaintenance


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'license_number', 'status', 'company')
    list_filter = ('status', 'company')
    search_fields = ('name', 'phone', 'license_number')


@admin.register(EVehicle)
class EVehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_id', 'model_name', 'registration_number', 'vehicle_type', 'status', 'current_battery_percent', 'assigned_driver', 'company')
    list_filter = ('status', 'vehicle_type', 'company')
    search_fields = ('vehicle_id', 'registration_number', 'model_name')


class DeliveryTrackingInline(admin.TabularInline):
    model = DeliveryTracking
    extra = 0
    readonly_fields = ('timestamp',)


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'recipient_name', 'status', 'priority', 'scheduled_date', 'assigned_vehicle', 'assigned_driver', 'company')
    list_filter = ('status', 'priority', 'company')
    search_fields = ('order_number', 'recipient_name', 'recipient_phone')
    inlines = [DeliveryTrackingInline]


@admin.register(ChargingLog)
class ChargingLogAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'battery_before', 'battery_after', 'units_consumed_kwh', 'charging_cost', 'charged_at')
    list_filter = ('company',)


@admin.register(VehicleMaintenance)
class VehicleMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'maintenance_type', 'status', 'cost', 'scheduled_date', 'completed_date')
    list_filter = ('status', 'maintenance_type', 'company')