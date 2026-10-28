import re
from django import forms
from django.core.exceptions import ValidationError
from .models import Driver, EVehicle, DeliveryOrder, DeliveryTracking, ChargingLog, VehicleMaintenance

# Indian DL: starts with 2-letter state code, followed by alphanumeric, 8-16 chars total
# Covers formats like: MH28BP88514, MH20 2023 0012345, DL0420110149646
DL_REGEX = re.compile(r'^[A-Z]{2}[A-Z0-9]{6,14}$')

# Indian mobile: 10 digits, starts with 6-9
PHONE_REGEX = re.compile(r'^[6-9][0-9]{9}$')


class DriverForm(forms.ModelForm):

    def clean_name(self):
        value = self.cleaned_data.get('name', '').strip()
        if value and not re.match(r'^[A-Za-z\s]+$', value):
            raise ValidationError('Name should only contain alphabetic characters and spaces.')
        return value

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', value)
        if not PHONE_REGEX.match(digits):
            raise ValidationError(
                'Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.'
            )
        return digits

    def clean_email(self):
        value = self.cleaned_data.get('email', '')
        if not value:
            return value
        value = value.strip().lower()
        if len(value) > 254:
            raise ValidationError('Email address is too long (max 254 characters).')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValidationError('Please enter a valid email address.')
        return value

    def clean_license_number(self):
        value = self.cleaned_data.get('license_number', '')
        if not value:
            return value
        normalized = value.replace(' ', '').upper()
        if not DL_REGEX.match(normalized):
            raise ValidationError(
                'Invalid licence number. Must start with a 2-letter state code '
                'followed by alphanumeric characters (e.g. MH28BP88514 or MH2020230012345).'
            )
        return normalized

    class Meta:
        model = Driver
        fields = '__all__'


class EVehicleForm(forms.ModelForm):
    class Meta:
        model = EVehicle
        fields = '__all__'


class DeliveryOrderForm(forms.ModelForm):
    class Meta:
        model = DeliveryOrder
        fields = '__all__'


class DeliveryTrackingForm(forms.ModelForm):
    class Meta:
        model = DeliveryTracking
        fields = '__all__'


class ChargingLogForm(forms.ModelForm):
    class Meta:
        model = ChargingLog
        fields = '__all__'


class VehicleMaintenanceForm(forms.ModelForm):
    class Meta:
        model = VehicleMaintenance
        fields = '__all__'