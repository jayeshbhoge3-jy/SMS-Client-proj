from django.utils.translation import gettext_lazy as _
import re
from django import forms
from .models import Vendor


class VendorForm(forms.ModelForm):

    class Meta:
        model = Vendor
        fields = "__all__"

    
    # GST NUMBER VALIDATION
    
    def clean_gst_number(self):
        gst = self.cleaned_data.get("gst_number", "").upper()

        if not gst:
            raise forms.ValidationError(_("GST number is required."))

        gst_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'

        if not re.match(gst_regex, gst):
            raise forms.ValidationError(
                "Invalid GST format. (e.g., 22AAAAA0000A1Z5)"
            )

        # Prevent duplicate GST
        if Vendor.objects.filter(gst_number=gst).exists():
            raise forms.ValidationError(_("Vendor with this GST already exists."))

        return gst


    
    # PRIMARY CONTACT – FIRST NAME
    
    def clean_primary_contact_first_name(self):
        name = self.cleaned_data.get("primary_contact_first_name", "")

        if not name:
            raise forms.ValidationError(_("First name is required."))

        if len(name) > 20:
            raise forms.ValidationError(_("First name cannot exceed 20 characters."))

        if not re.match(r'^[A-Za-z]+$', name):
            raise forms.ValidationError(
                "First name should contain only alphabetic characters."
            )

        return name


    
    # PRIMARY CONTACT – LAST NAME
    
    def clean_primary_contact_last_name(self):
        name = self.cleaned_data.get("primary_contact_last_name", "")

        if not name:
            raise forms.ValidationError(_("Last name is required."))

        if len(name) > 20:
            raise forms.ValidationError(_("Last name cannot exceed 20 characters."))

        if not re.match(r'^[A-Za-z]+$', name):
            raise forms.ValidationError(
                "Last name should contain only alphabetic characters."
            )

        return name


    
    # VENDOR NAME
    
    def clean_company_name(self):
        name = self.cleaned_data.get("company_name", "")

        if not name:
            raise forms.ValidationError(_("Vendor name is required."))

        if len(name) > 50:
            raise forms.ValidationError(_("Vendor name cannot exceed 50 characters."))

        if not re.match(r'^[A-Za-z][A-Za-z\s&.\-]*$', name):
            raise forms.ValidationError(
                "Vendor name must start with a letter and contain only alphabets, spaces, &, . or -"
            )

        return name


    
    # DISPLAY NAME
    
    def clean_display_name(self):
        name = self.cleaned_data.get("display_name", "")

        if not name:
            raise forms.ValidationError(_("Display name is required."))

        if len(name) > 50:
            raise forms.ValidationError(_("Display name cannot exceed 50 characters."))

        if not re.match(r'^[A-Za-z][A-Za-z\s&.\-]*$', name):
            raise forms.ValidationError(
                "Display name must start with a letter and contain only alphabets, spaces, &, . or -"
            )

        return name


    
    # EMAIL VALIDATION
    
    def clean_email(self):
        email = self.cleaned_data.get("email", "")

        if not email:
            raise forms.ValidationError(_("Email address is required."))

        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_regex, email):
            raise forms.ValidationError(_("Enter a valid email address."))

        return email


    
    # PHONE NUMBER
    
    def clean_mobile(self):
        mobile = self.cleaned_data.get("mobile", "")

        if not mobile:
            raise forms.ValidationError(_("Phone number is required."))

        if not mobile.isdigit():
            raise forms.ValidationError(_("Phone number must contain only digits."))

        if len(mobile) != 10:
            raise forms.ValidationError(_("Phone number must be exactly 10 digits."))

        return mobile


    
    # ADDRESS
    
    def clean_address(self):
        address = self.cleaned_data.get("address", "")

        if not address:
            raise forms.ValidationError(_("Address is required."))

        if len(address) > 500:
            raise forms.ValidationError(_("Address cannot exceed 500 characters."))

        if not re.search(r'[A-Za-z]', address):
            raise forms.ValidationError(_("Address must contain meaningful text."))

        return address




from django import forms
from .models import Transport
from django import forms
from .models import Transport

class TransportForm(forms.ModelForm):

    class Meta:
        model = Transport
        exclude = ['company']

        widgets = {
            'vehicle_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'driver_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'driver_mobile': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'source_location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'destination_location': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'dispatch_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
                }
            ),

            'expected_delivery_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
                }
            ),

            'transport_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),

            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),
        }

    def clean_driver_mobile(self):
        mobile = self.cleaned_data.get('driver_mobile', '')
        
        # Check if mobile number already exists, excluding the current instance if editing
        query = Transport.objects.filter(driver_mobile=mobile)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise forms.ValidationError("Mobile number already exists")
            
        return mobile