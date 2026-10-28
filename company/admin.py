from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'plan_type', 'is_subscription_active', 'subscription_end')
    list_filter = ('plan_type', 'is_subscription_active')
    search_fields = ('name', 'email')
