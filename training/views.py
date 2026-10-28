from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from company.models import Company, Staff
from .models import (
    TrainingMaterial, TrainingRecord, StaffOnboarding,
    OnboardingChecklistItem, SupportTicket, TicketComment
)


def get_company(request):
    try:
        return Company.objects.get(owner=request.user)
    except Company.DoesNotExist:
        return None


# ──────────────────────────── DASHBOARD ────────────────────────────

@login_required
def training_dashboard(request):
    company = get_company(request)
    if company is None:
        # Superadmin has no company — send them to the admin dashboard
        return redirect('admin_dashboard')

    total_staff = Staff.objects.filter(company=company).count()
    total_materials = TrainingMaterial.objects.filter(company=company, is_active=True).count()
    open_tickets = SupportTicket.objects.filter(company=company, status__in=['OPEN', 'IN_PROGRESS']).count()
    active_onboardings = StaffOnboarding.objects.filter(company=company, status__in=['NOT_STARTED', 'IN_PROGRESS']).count()
    completed_records = TrainingRecord.objects.filter(company=company, status='COMPLETED').count()
    critical_tickets = SupportTicket.objects.filter(company=company, status='OPEN', priority='CRITICAL').count()

    recent_tickets = SupportTicket.objects.filter(company=company).order_by('-created_at')[:5]
    recent_records = TrainingRecord.objects.filter(company=company).order_by('-updated_at')[:5]
    recent_onboardings = StaffOnboarding.objects.filter(company=company).order_by('-join_date')[:5]

    return render(request, 'training/dashboard.html', {
        'company': company,
        'total_staff': total_staff,
        'total_materials': total_materials,
        'open_tickets': open_tickets,
        'active_onboardings': active_onboardings,
        'completed_records': completed_records,
        'critical_tickets': critical_tickets,
        'recent_tickets': recent_tickets,
        'recent_records': recent_records,
        'recent_onboardings': recent_onboardings,
    })


# ──────────────────────────── MATERIALS ────────────────────────────

@login_required
def material_list(request):
    company = get_company(request)
    q = request.GET.get('q', '')
    mtype = request.GET.get('type', '')

    materials = TrainingMaterial.objects.filter(
        company=company,
        is_active=True
    )

    if q:
        materials = materials.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    if mtype:
        materials = materials.filter(material_type=mtype)

    # Add tag list for template 
    for material in materials:
        material.tag_list = [
            tag.strip()
            for tag in (material.tags or '').split(',')
            if tag.strip()
        ]

    return render(request, 'training/material_list.html', {
        'company': company,
        'materials': materials,
        'q': q,
        'mtype': mtype,
        'type_choices': TrainingMaterial.MATERIAL_TYPE_CHOICES,
    })


def material_create(request):
    company = get_company(request)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        material_type = request.POST.get('material_type')
        file_url = request.POST.get('file_url')
        tags = request.POST.get('tags')
        material = TrainingMaterial.objects.create(
            company=company, title=title, description=description,
            material_type=material_type, file_url=file_url, tags=tags,
            created_by=request.user,
        )
        if request.FILES.get('file_upload'):          # ← add this
            material.file_upload = request.FILES['file_upload']
            material.save()
        messages.success(request, 'Training material added successfully.')
        return redirect('training:material_list')
    return render(request, 'training/material_form.html', {
        'company': company,
        'type_choices': TrainingMaterial.MATERIAL_TYPE_CHOICES,
    })


def material_edit(request, pk):
    company = get_company(request)
    material = get_object_or_404(TrainingMaterial, pk=pk, company=company)
    if request.method == 'POST':
        material.title = request.POST.get('title')
        material.description = request.POST.get('description')
        material.material_type = request.POST.get('material_type')
        material.file_url = request.POST.get('file_url')
        material.tags = request.POST.get('tags')
        if request.FILES.get('file_upload'):          # ← add this
            material.file_upload = request.FILES['file_upload']
        material.save()
        return redirect('training:material_list')
    return render(request, 'training/material_form.html', {
        'company': company, 'material': material,
        'type_choices': TrainingMaterial.MATERIAL_TYPE_CHOICES,
    })


@login_required
def material_delete(request, pk):
    company = get_company(request)
    material = get_object_or_404(TrainingMaterial, pk=pk, company=company)
    material.is_active = False
    material.save()
    messages.success(request, 'Material removed.')
    return redirect('training:material_list')


# ──────────────────────────── TRAINING RECORDS ────────────────────────────

@login_required
def record_list(request):
    company = get_company(request)
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')
    records = TrainingRecord.objects.filter(company=company).select_related('staff', 'material')
    if status_filter:
        records = records.filter(status=status_filter)
    if staff_filter:
        records = records.filter(staff_id=staff_filter)
    staff_list = Staff.objects.filter(company=company)
    return render(request, 'training/record_list.html', {
        'company': company, 'records': records, 'staff_list': staff_list,
        'status_filter': status_filter, 'staff_filter': staff_filter,
        'status_choices': TrainingRecord.STATUS_CHOICES,
    })


@login_required
def record_create(request):
    company = get_company(request)
    staff_list = Staff.objects.filter(company=company)
    materials = TrainingMaterial.objects.filter(company=company, is_active=True)
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        material_id = request.POST.get('material')
        status = request.POST.get('status', 'PENDING')
        score = request.POST.get('score') or None
        due_date = request.POST.get('due_date') or None
        completion_date = request.POST.get('completion_date') or None
        notes = request.POST.get('notes')
        staff = get_object_or_404(Staff, pk=staff_id, company=company)
        material = get_object_or_404(TrainingMaterial, pk=material_id, company=company)
        if TrainingRecord.objects.filter(company=company, staff=staff, material=material).exists():
            messages.error(request, f'A training record for {staff.name} with \"{material.title}\" already exists. Edit the existing record instead.')
            return render(request, 'training/record_form.html', {
                'company': company, 'staff_list': staff_list, 'materials': materials,
                'status_choices': TrainingRecord.STATUS_CHOICES,
            })
        TrainingRecord.objects.create(
            company=company, staff=staff, material=material,
            status=status, score=score, due_date=due_date,
            completion_date=completion_date, notes=notes
        )
        messages.success(request, 'Training record created.')
        return redirect('training:record_list')
    return render(request, 'training/record_form.html', {
        'company': company, 'staff_list': staff_list, 'materials': materials,
        'status_choices': TrainingRecord.STATUS_CHOICES,
    })


@login_required
def record_edit(request, pk):
    company = get_company(request)
    record = get_object_or_404(TrainingRecord, pk=pk, company=company)
    staff_list = Staff.objects.filter(company=company)
    materials = TrainingMaterial.objects.filter(company=company, is_active=True)
    if request.method == 'POST':
        record.status = request.POST.get('status')
        record.score = request.POST.get('score') or None
        record.due_date = request.POST.get('due_date') or None
        record.completion_date = request.POST.get('completion_date') or None
        record.notes = request.POST.get('notes')
        record.save()
        messages.success(request, 'Record updated.')
        return redirect('training:record_list')
    return render(request, 'training/record_form.html', {
        'company': company, 'record': record, 'staff_list': staff_list,
        'materials': materials, 'status_choices': TrainingRecord.STATUS_CHOICES,
    })


# ──────────────────────────── ONBOARDING ────────────────────────────

@login_required
def onboarding_list(request):
    company = get_company(request)
    status_filter = request.GET.get('status', '')

    onboardings = (
        StaffOnboarding.objects
        .filter(company=company)
        .select_related('staff', 'mentor')
        .prefetch_related('checklist_items')
    )

    if status_filter:
        onboardings = onboardings.filter(status=status_filter)

    # Add counts for template
    for ob in onboardings:
        ob.completed_tasks = ob.checklist_items.filter(
            is_completed=True
        ).count()

        ob.total_tasks = ob.checklist_items.count()

    return render(request, 'training/onboarding_list.html', {
        'company': company,
        'onboardings': onboardings,
        'status_filter': status_filter,
        'status_choices': StaffOnboarding.STATUS_CHOICES,
    })


@login_required
def onboarding_create(request):
    company = get_company(request)
    staff_list = Staff.objects.filter(company=company)
    if request.method == 'POST':
        staff_id = request.POST.get('staff')
        join_date = request.POST.get('join_date')
        target_date = request.POST.get('target_completion_date') or None
        mentor_id = request.POST.get('mentor') or None
        notes = request.POST.get('notes')
        staff = get_object_or_404(Staff, pk=staff_id, company=company)
        mentor = Staff.objects.filter(pk=mentor_id, company=company).first() if mentor_id else None
        onboarding = StaffOnboarding.objects.create(
            company=company, staff=staff, join_date=join_date,
            target_completion_date=target_date, mentor=mentor, notes=notes
        )
        # Default checklist items
        default_tasks = [
            'Complete HR paperwork', 'System access setup', 'Introduction to team',
            'Review company policies', 'Role-specific training', 'Shadow senior staff',
            'Complete initial training modules', 'First week review meeting',
        ]
        for i, task in enumerate(default_tasks):
            OnboardingChecklistItem.objects.create(onboarding=onboarding, task=task, order=i)
        messages.success(request, f'Onboarding started for {staff.name}.')
        return redirect('training:onboarding_detail', pk=onboarding.pk)
    return render(request, 'training/onboarding_form.html', {
        'company': company, 'staff_list': staff_list,
    })


@login_required
def onboarding_detail(request, pk):
    company = get_company(request)
    onboarding = get_object_or_404(StaffOnboarding, pk=pk, company=company)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_task':
            task_id = request.POST.get('task_id')
            item = get_object_or_404(OnboardingChecklistItem, pk=task_id, onboarding=onboarding)
            item.is_completed = not item.is_completed
            item.completed_at = timezone.now() if item.is_completed else None
            item.save()
            # Update onboarding status
            pct = onboarding.completion_percentage
            if pct == 0:
                onboarding.status = 'NOT_STARTED'
            elif pct == 100:
                onboarding.status = 'COMPLETED'
                onboarding.actual_completion_date = timezone.now().date()
            else:
                onboarding.status = 'IN_PROGRESS'
            onboarding.save()
        elif action == 'add_task':
            task = request.POST.get('task')
            if task:
                max_order = onboarding.checklist_items.count()
                OnboardingChecklistItem.objects.create(onboarding=onboarding, task=task, order=max_order)
        return redirect('training:onboarding_detail', pk=pk)
    return render(request, 'training/onboarding_detail.html', {
        'company': company, 'onboarding': onboarding,
        'checklist': onboarding.checklist_items.all(),
    })


# ──────────────────────────── SUPPORT TICKETS (Company Side) ────────────────────────────

@login_required
def ticket_list(request):
    company = get_company(request)
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    q = request.GET.get('q', '')

    tickets = SupportTicket.objects.filter(company=company)

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if q:
        tickets = tickets.filter(Q(title__icontains=q) | Q(ticket_id__icontains=q))

    return render(request, 'training/ticket_list.html', {
        'company': company,
        'tickets': tickets,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'q': q,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    })


@login_required
def ticket_create(request):
    """Company user creates a new support ticket."""
    company = get_company(request)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'OTHER')

        if not title or not description:
            messages.error(request, 'Title and description are required.')
            return render(request, 'training/ticket_form.html', {
                'company': company,
                'category_choices': SupportTicket.CATEGORY_CHOICES,
            })

        SupportTicket.objects.create(
            company=company,
            title=title,
            description=description,
            category=category,
            priority='MEDIUM',          # always starts at MEDIUM; only admin can change it
            raised_by_user=request.user,
            status='OPEN',
        )
        messages.success(request, 'Support ticket submitted. Our team will review it shortly.')
        return redirect('training:ticket_list')

    return render(request, 'training/ticket_form.html', {
        'company': company,
        'category_choices': SupportTicket.CATEGORY_CHOICES,
    })


@login_required
def ticket_detail(request, pk):
    """
    Company view of a ticket.
    - Company can add comments at any time (except CLOSED).
    - Company can CLOSE the ticket only when status == RESOLVED (admin resolved it).
    - Company cannot change status to anything else.
    """
    company = get_company(request)
    ticket = get_object_or_404(SupportTicket, pk=pk, company=company)
    comments = ticket.comments.select_related('author').order_by('created_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Add a comment ──
        if action == 'comment':
            body = request.POST.get('body', '').strip()
            if body and ticket.status != 'CLOSED':
                TicketComment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    author_type='COMPANY',
                    body=body,
                )
                messages.success(request, 'Comment added.')
            return redirect('training:ticket_detail', pk=pk)

        # ── Close ticket (only allowed when RESOLVED) ──
        if action == 'close':
            if ticket.status == 'RESOLVED':
                ticket.status = 'CLOSED'
                ticket.closed_at = timezone.now()
                ticket.save()
                messages.success(request, 'Ticket closed. Thank you for confirming the resolution.')
            else:
                messages.error(request, 'You can only close a ticket after admin has resolved it.')
            return redirect('training:ticket_detail', pk=pk)

    return render(request, 'training/ticket_detail.html', {
        'company': company,
        'ticket': ticket,
        'comments': comments,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    })


# ──────────────────────────── SUPPORT TICKETS (Admin Side) ────────────────────────────

def admin_required(request):
    """Returns True if the logged-in user is a Django superuser/staff."""
    return request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)


@login_required
def admin_ticket_list(request):
    """Admin sees ALL tickets across all companies."""
    if not admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('admin_dashboard')

    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    q = request.GET.get('q', '')

    tickets = SupportTicket.objects.select_related('company', 'raised_by_user').order_by('-created_at')

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if q:
        tickets = tickets.filter(
            Q(title__icontains=q) |
            Q(ticket_id__icontains=q) |
            Q(company__name__icontains=q)
        )

    # Stats counts (always from unfiltered queryset)
    all_tickets = SupportTicket.objects.all()
    open_count       = all_tickets.filter(status='OPEN').count()
    in_progress_count = all_tickets.filter(status='IN_PROGRESS').count()
    resolved_count   = all_tickets.filter(status='RESOLVED').count()
    closed_count     = all_tickets.filter(status='CLOSED').count()

    return render(request, 'training/admin_ticket_list.html', {
        'tickets': tickets,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'q': q,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'closed_count': closed_count,
    })


@login_required
def admin_ticket_detail(request, pk):
    """
    Admin view of a ticket.
    - Admin can add comments at any time.
    - Admin can change status to IN_PROGRESS or RESOLVED (not CLOSED — that's company's action).
    - Admin can add resolution notes when marking RESOLVED.
    """
    if not admin_required(request):
        messages.error(request, 'Access denied.')
        return redirect('admin_dashboard')

    ticket = get_object_or_404(SupportTicket, pk=pk)
    comments = ticket.comments.select_related('author').order_by('created_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Add a comment ──
        if action == 'comment':
            body = request.POST.get('body', '').strip()
            if body:
                TicketComment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    author_type='ADMIN',
                    body=body,
                )
                messages.success(request, 'Comment posted.')
            return redirect('training:admin_ticket_detail', pk=pk)

        # ── Update status / resolve (admin can also set priority here) ──
        if action == 'update_status':
            new_status = request.POST.get('status')
            new_priority = request.POST.get('priority')
            resolution_notes = request.POST.get('resolution_notes', '').strip()

            # Admin can only move to IN_PROGRESS or RESOLVED, not CLOSED
            allowed = ('IN_PROGRESS', 'RESOLVED', 'OPEN')
            if new_status in allowed:
                ticket.status = new_status
                if new_status == 'RESOLVED':
                    ticket.resolution_notes = resolution_notes
                    if not ticket.resolved_at:
                        ticket.resolved_at = timezone.now()

            allowed_priorities = [p[0] for p in SupportTicket.PRIORITY_CHOICES]
            if new_priority in allowed_priorities:
                ticket.priority = new_priority

            ticket.save()
            messages.success(request, f'Ticket updated.')
            return redirect('training:admin_ticket_detail', pk=pk)

    return render(request, 'training/admin_ticket_detail.html', {
        'ticket': ticket,
        'comments': comments,
        'status_choices': [
            ('OPEN', 'Open'),
            ('IN_PROGRESS', 'In Progress'),
            ('RESOLVED', 'Resolved'),
        ],
        'priority_choices': SupportTicket.PRIORITY_CHOICES,
    })

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

@login_required
@require_POST
def add_staff_ajax(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()

        if not name or not email:
            return JsonResponse({'success': False, 'error': 'Name and email are required.'})

        company = get_company(request)

        if Staff.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'A staff member with this email already exists.'})

        staff = Staff.objects.create(company=company, name=name, email=email)
        return JsonResponse({'success': True, 'id': staff.pk, 'name': staff.name, 'email': staff.email})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})