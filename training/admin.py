from django.contrib import admin
from .models import TrainingMaterial, TrainingRecord, StaffOnboarding, OnboardingChecklistItem, SupportTicket


@admin.register(TrainingMaterial)
class TrainingMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'material_type', 'company', 'is_active', 'created_at')
    list_filter = ('material_type', 'is_active', 'company')
    search_fields = ('title',)


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('staff', 'material', 'status', 'score', 'completion_date')
    list_filter = ('status', 'company')
    search_fields = ('staff__name', 'material__title')


class ChecklistInline(admin.TabularInline):
    model = OnboardingChecklistItem
    extra = 0


@admin.register(StaffOnboarding)
class StaffOnboardingAdmin(admin.ModelAdmin):
    list_display = ('staff', 'join_date', 'status', 'company')
    list_filter = ('status', 'company')
    inlines = [ChecklistInline]


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    raised_by = ('ticket_id', 'title', 'priority', 'status', 'raised_by_user', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'company')
    search_fields = ('ticket_id', 'title')
