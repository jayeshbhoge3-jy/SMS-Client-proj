"""
Staff portal views.
Add these to: training/views.py   (or a new file training/staff_views.py and import in training/urls.py)
"""

import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.db.models import Q

from company.models import Staff
from .models import (
    TrainingMaterial, TrainingRecord, StaffOnboarding,
    OnboardingChecklistItem, SupportTicket, TicketComment,
)
from inventory.models import Product, PurchaseOrder, SalesOrder
from company.models import StaffDeleteRequest
from django.utils import timezone

# ─────────────────────────── HELPERS ───────────────────────────────

def get_staff_user(request):
    """Return the Staff record for the logged-in staff user, or None."""
    try:
        return Staff.objects.select_related('company').get(user=request.user)
    except Staff.DoesNotExist:
        return None


def staff_login_required(view_func):
    """Decorator: must be logged in AND have a linked Staff record."""
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('staff_login')
        staff = get_staff_user(request)
        if not staff:
            messages.error(request, "No staff account found. Please contact your company admin.")
            logout(request)
            return redirect('staff_login')
        return view_func(request, *args, staff=staff, **kwargs)

    return wrapper


# ─────────────────────────── AUTH ──────────────────────────────────

def staff_login(request):
    """Staff login page — separate from company-owner and superadmin logins."""
    if request.user.is_authenticated:
        staff = get_staff_user(request)
        if staff:
            return redirect('staff_dashboard')
        # Logged in as someone else — log them out first
        logout(request)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if not user:
            user = authenticate(request, username=username.lower(), password=password)

        if user:
            # Verify this user has a Staff profile
            try:
                staff = Staff.objects.get(user=user)
            except Staff.DoesNotExist:
                messages.error(request, "This portal is for staff members only.")
                return render(request, 'staff/staff_login.html')

            login(request, user)
            messages.success(request, f"Welcome back, {staff.name}!")
            next_url = request.GET.get('next', 'staff_dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'staff/staff_login.html')


def staff_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('staff_login')


def staff_accept_invite(request, token):
    """
    Staff member clicks the invite link from their email.
    They set a password and their account becomes active.
    """
    try:
        staff = Staff.objects.get(invite_token=token, invite_accepted=False)
    except Staff.DoesNotExist:
        return render(request, 'staff/invite_expired.html')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, 'staff/staff_accept_invite.html', {'staff': staff})

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'staff/staff_accept_invite.html', {'staff': staff})

        # Create or update the Django User
        username = staff.email.split('@')[0].lower().replace('.', '_')
        # Ensure unique username
        base = username
        counter = 1
        while User.objects.filter(username=username).exclude(pk=getattr(staff.user, 'pk', None)).exists():
            username = f"{base}{counter}"
            counter += 1

        if staff.user:
            user = staff.user
            user.username = username
            user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(
                username=username,
                email=staff.email,
                password=password,
                first_name=staff.name.split()[0] if staff.name else '',
                last_name=' '.join(staff.name.split()[1:]) if len(staff.name.split()) > 1 else '',
            )

        # Link user, mark invite accepted, rotate token for security
        staff.user = user
        staff.username = username
        staff.invite_accepted = True
        staff.invite_token = uuid.uuid4()  # invalidate old link
        staff.save()

        login(request, user)
        messages.success(request, f"Welcome to the portal, {staff.name}! Your account is ready.")
        return redirect('staff_dashboard')

    return render(request, 'staff/staff_accept_invite.html', {'staff': staff})


# ─────────────────────────── DASHBOARD ─────────────────────────────

@staff_login_required
def staff_dashboard(request, staff=None):
    company = staff.company

    my_records = TrainingRecord.objects.filter(staff=staff).select_related('material')
    pending = my_records.filter(status='PENDING').count()
    in_progress = my_records.filter(status='IN_PROGRESS').count()
    completed = my_records.filter(status='COMPLETED').count()

    try:
        onboarding = StaffOnboarding.objects.prefetch_related('checklist_items').get(staff=staff)
    except StaffOnboarding.DoesNotExist:
        onboarding = None

    my_tickets = SupportTicket.objects.filter(
        company=company, raised_by_user=staff.user
    ).order_by('-created_at')[:5]

    recent_records = my_records.order_by('-updated_at')[:5]

    total_products = Product.objects.filter(company=company).count()
    total_po = PurchaseOrder.objects.filter(company=company).count()
    total_so = SalesOrder.objects.filter(company=company).count()
    pending_delete_requests = StaffDeleteRequest.objects.filter(requested_by=staff, status='PENDING').count()

    return render(request, 'staff/staff_dashboard.html', {
        'staff': staff,
        'company': company,
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'onboarding': onboarding,
        'my_tickets': my_tickets,
        'recent_records': recent_records,
        'total_products': total_products,
        'total_po': total_po,
        'total_so': total_so,
        'pending_delete_requests': pending_delete_requests,
    })


# ─────────────────────────── MY TRAINING ───────────────────────────

@staff_login_required
def staff_my_training(request, staff=None):
    company = staff.company
    records = TrainingRecord.objects.filter(staff=staff).select_related('material').order_by('-updated_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        records = records.filter(status=status_filter)

    return render(request, 'staff/staff_my_training.html', {
        'staff': staff,
        'company': company,
        'records': records,
        'status_filter': status_filter,
        'status_choices': TrainingRecord.STATUS_CHOICES,
        'today': timezone.now().date(),   # Fix: pass today for due-date comparison
    })


@staff_login_required
def staff_material_detail(request, pk, staff=None):
    """Staff can view the detail/content of a training material assigned to them."""
    record = get_object_or_404(TrainingRecord, pk=pk, staff=staff)
    material = record.material

    # Mark as IN_PROGRESS when first opened (if still Pending)
    if record.status == 'PENDING':
        record.status = 'IN_PROGRESS'
        record.save(update_fields=['status', 'updated_at'])

    return render(request, 'staff/staff_material_detail.html', {
        'staff': staff,
        'company': staff.company,
        'record': record,
        'material': material,
        'today': timezone.now().date(),
    })


# ─────────────────────────── MY ONBOARDING ─────────────────────────

@staff_login_required
def staff_my_onboarding(request, staff=None):
    company = staff.company
    try:
        onboarding = StaffOnboarding.objects.prefetch_related('checklist_items').get(staff=staff)
    except StaffOnboarding.DoesNotExist:
        onboarding = None

    return render(request, 'staff/staff_my_onboarding.html', {
        'staff': staff,
        'company': company,
        'onboarding': onboarding,
    })


@staff_login_required
def staff_toggle_checklist(request, pk, staff=None):
    """AJAX/POST: toggle a checklist item as complete/incomplete."""
    item = get_object_or_404(OnboardingChecklistItem, pk=pk, onboarding__staff=staff)
    item.is_completed = not item.is_completed
    item.completed_at = timezone.now() if item.is_completed else None
    item.save()

    # Update onboarding status
    onboarding = item.onboarding
    all_items = onboarding.checklist_items.all()
    if all_items.exists():
        if all_items.filter(is_completed=False).count() == 0:
            onboarding.status = 'COMPLETED'
            onboarding.actual_completion_date = timezone.now().date()
        elif all_items.filter(is_completed=True).count() > 0:
            onboarding.status = 'IN_PROGRESS'
        else:
            onboarding.status = 'NOT_STARTED'
        onboarding.save()

    messages.success(request, "Checklist updated.")
    return redirect('staff_my_onboarding')


# ─────────────────────────── MY TICKETS ────────────────────────────

@staff_login_required
def staff_my_tickets(request, staff=None):
    company = staff.company
    tickets = SupportTicket.objects.filter(
        company=company, raised_by_user=staff.user
    ).order_by('-created_at')

    status_filter = request.GET.get('status', '')
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    return render(request, 'staff/staff_my_tickets.html', {
        'staff': staff,
        'company': company,
        'tickets': tickets,
        'status_filter': status_filter,
        'status_choices': SupportTicket.STATUS_CHOICES,
    })


@staff_login_required
def staff_ticket_create(request, staff=None):
    company = staff.company

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'OTHER')

        if not title or not description:
            messages.error(request, "Title and description are required.")
        else:
            SupportTicket.objects.create(
                company=company,
                title=title,
                description=description,
                category=category,
                priority='MEDIUM',  # default; admin sets priority from their side
                raised_by_user=staff.user,
            )
            messages.success(request, "Ticket submitted. Our team will review it shortly.")
            return redirect('staff_my_tickets')

    return render(request, 'staff/staff_ticket_form.html', {
        'staff': staff,
        'company': company,
        'category_choices': SupportTicket.CATEGORY_CHOICES,
        # priority_choices intentionally omitted — admin sets priority
    })


@staff_login_required
def staff_ticket_detail(request, pk, staff=None):
    company = staff.company
    ticket = get_object_or_404(SupportTicket, pk=pk, company=company, raised_by_user=staff.user)
    comments = ticket.comments.select_related('author').all()

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            TicketComment.objects.create(
                ticket=ticket,
                author=staff.user,
                author_type='COMPANY',
                body=body,
            )
            ticket.save()  # bump updated_at
            messages.success(request, "Comment added.")
            return redirect('staff_ticket_detail', pk=pk)
        else:
            messages.error(request, "Comment cannot be empty.")

    return render(request, 'staff/staff_ticket_detail.html', {
        'staff': staff,
        'company': company,
        'ticket': ticket,
        'comments': comments,
    })


@staff_login_required
def staff_ticket_delete(request, pk, staff=None):
    company = staff.company
    ticket = get_object_or_404(SupportTicket, pk=pk, company=company, raised_by_user=staff.user)

    if request.method == 'POST':
        ticket.delete()
        messages.success(request, "Ticket deleted successfully.")
        return redirect('staff_my_tickets')

    return redirect('staff_ticket_detail', pk=pk)


# ─────────────── COMPANY OWNER: INVITE STAFF ───────────────────────

@login_required
def invite_staff(request, staff_id):
    """
    Company owner sends an invite email to a staff member.
    Add this to company/views.py and wire up company/urls.py.
    """
    from accounts.models import UserProfile
    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'COMPANY_OWNER':
        messages.error(request, "Access denied.")
        return redirect('company_dashboard')

    company = profile.company
    staff = get_object_or_404(Staff, pk=staff_id, company=company)

    if staff.invite_accepted:
        messages.info(request, f"{staff.name} has already accepted their invite.")
        return redirect('staff_list')  # adjust to your staff list URL name

    # Regenerate token so old links expire
    staff.invite_token = uuid.uuid4()
    staff.save()

    invite_url = request.build_absolute_uri(
        reverse('staff_accept_invite', kwargs={'token': str(staff.invite_token)})
    )

    try:
        send_mail(
            subject=f"You're invited to {company.name}'s Staff Portal",
            message=(
                f"Hi {staff.name},\n\n"
                f"You've been invited to join the {company.name} staff portal.\n\n"
                f"Click the link below to set your password and get started:\n"
                f"{invite_url}\n\n"
                f"This link is unique to you — do not share it.\n\n"
                f"Regards,\n{company.name}"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[staff.email],
            fail_silently=False,
        )
        messages.success(request, f"Invite sent to {staff.email}.")
    except Exception as e:
        messages.error(request, f"Failed to send invite email: {e}")

    return redirect('staff_list')  # adjust to your staff list URL name