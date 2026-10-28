from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.forms import modelform_factory, inlineformset_factory
from django import forms
from training.staff_views import staff_login_required

from inventory.models import (
    Product, Category, PurchaseOrder, PurchaseOrderItem, 
    SalesOrder, SalesOrderItem, Customer
)
from company.models import StaffDeleteRequest, StaffActivityLog

def log_staff_action(staff, action_type, module, obj, extra=None):
    StaffActivityLog.objects.create(
        company=staff.company,
        staff=staff,
        action_type=action_type,
        module=module,
        object_id=obj.pk,
        object_repr=str(obj),
        extra_data=extra,
    )

# --- PRODUCTS ---

ProductForm = modelform_factory(
    Product,
    fields=['name', 'sku', 'category', 'purchase_price', 'selling_price', 'low_stock_limit'],
    widgets={
        'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'sku': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'category': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'purchase_price': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500', 'step': '0.01'}),
        'selling_price': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500', 'step': '0.01'}),
        'low_stock_limit': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
    }
)

@staff_login_required
def staff_product_list(request, staff=None):
    company = staff.company
    
    LOW_STOCK_LIMIT = 5
    from datetime import date, timedelta
    today = date.today()
    near_limit = today + timedelta(days=30)
    
    products = Product.objects.filter(company=company).order_by('-id')
    
    from inventory.models import ProductBatch
    from django.db.models import Sum, Q, Value, IntegerField
    from django.db.models.functions import Coalesce
    
    product_data = []
    
    for p in products:
        all_batches = ProductBatch.objects.filter(
            company=company, product=p, is_active=True
        )
        total_stock = all_batches.aggregate(total=Sum("quantity"))["total"] or 0
        
        active_batches = all_batches.filter(
            Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
            quantity__gt=0
        )
        sellable_stock = active_batches.aggregate(total=Sum("quantity"))["total"] or 0
        
        if sellable_stock == 0:
            stock_status = "out_of_stock"
        elif 1 <= sellable_stock <= LOW_STOCK_LIMIT:
            stock_status = "low_stock"
        else:
            stock_status = "in_stock"
            
        product_data.append({
            "product": p,
            "batch_stock": sellable_stock,
            "total_stock": total_stock,
            "is_low_stock": stock_status == "low_stock",
            "is_out_of_stock": stock_status == "out_of_stock",
            "is_in_stock": stock_status == "in_stock",
        })

    return render(request, 'staff/staff_product_list.html', {
        'staff': staff,
        'company': company,
        'product_data': product_data
    })

from inventory.forms import ProductForm as OwnerProductForm
from inventory.models import ProductBatch
from django.db.models import Sum, Q
from datetime import date

@staff_login_required
def staff_product_create(request, staff=None):
    company = staff.company
    categories = Category.objects.filter(company=company)

    if request.method == 'POST':
        form = OwnerProductForm(request.POST, company=company)
        if form.is_valid():
            product = form.save(commit=False)
            product.company = company

            from company.currency_utils import convert_to_inr, get_exchange_rates
            cur = company.display_currency
            if cur != 'INR':
                rates = get_exchange_rates()
                product.purchase_price = convert_to_inr(product.purchase_price, cur, rates)
                product.selling_price = convert_to_inr(product.selling_price, cur, rates)

            initial_stock = form.cleaned_data.get("stock_quantity", 0)
            product.stock_quantity = 0 
            product.save()

            expiry_date = request.POST.get('default_expiry_date')
            if initial_stock > 0:
                ProductBatch.objects.create(
                    company=company,
                    product=product,
                    batch_number="INITIAL-STOCK",
                    expiry_date=expiry_date if expiry_date else None,
                    quantity=initial_stock,
                    is_active=True
                )

            from inventory.views import reconcile_product_stock
            reconcile_product_stock(company)

            log_staff_action(staff, 'CREATE', 'PRODUCT', product)
            messages.success(request, f"Product '{product.name}' created successfully.")
            return redirect('staff_product_list')
    else:
        form = OwnerProductForm(company=company)
        
    return render(request, 'staff/staff_product_form.html', {
        'staff': staff, 'company': company, 'form': form, 'title': 'Add Product', 'categories': categories
    })

@staff_login_required
def staff_product_edit(request, pk, staff=None):
    company = staff.company
    product = get_object_or_404(Product, pk=pk, company=company)
    categories = Category.objects.filter(company=company)

    if request.method == 'POST':
        form = OwnerProductForm(request.POST, instance=product, company=company)
        if form.is_valid():
            product = form.save(commit=False)

            from company.currency_utils import convert_to_inr, get_exchange_rates
            cur = company.display_currency
            if cur != 'INR':
                rates = get_exchange_rates()
                product.purchase_price = convert_to_inr(product.purchase_price, cur, rates)
                product.selling_price = convert_to_inr(product.selling_price, cur, rates)

            new_stock = form.cleaned_data.get("stock_quantity", 0)

            today = date.today()
            old_stock = (
                ProductBatch.objects.filter(
                    Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
                    company=company,
                    product=product,
                    quantity__gt=0,
                    is_active=True
                )
                .aggregate(total=Sum("quantity"))["total"] or 0
            )

            diff = new_stock - old_stock

            product.save(update_fields=[
                "name", "sku", "category", "purchase_price", "selling_price", "is_expiry_tracked",
            ])

            if diff != 0:
                batch, _ = ProductBatch.objects.get_or_create(
                    company=company,
                    product=product,
                    batch_number="MANUAL-EDIT",
                    defaults={
                        "expiry_date": None,
                        "quantity": 0,
                        "is_active": True,
                    },
                )
                batch.quantity += diff
                if batch.quantity < 0:
                    batch.quantity = 0
                batch.save(update_fields=["quantity"])

            from inventory.views import reconcile_product_stock
            reconcile_product_stock(company)

            log_staff_action(staff, 'EDIT', 'PRODUCT', product)
            messages.success(request, f"Product '{product.name}' updated successfully.")
            return redirect('staff_product_list')
    else:
        form = OwnerProductForm(instance=product, company=company)
        
    return render(request, 'staff/staff_product_form.html', {
        'staff': staff, 'company': company, 'form': form, 'title': 'Edit Product', 'product': product, 'categories': categories
    })

@staff_login_required
def staff_product_delete_request(request, pk, staff=None):
    company = staff.company
    product = get_object_or_404(Product, pk=pk, company=company)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        req = StaffDeleteRequest.objects.create(
            company=company, requested_by=staff, module='PRODUCT',
            object_id=product.pk, object_repr=str(product), reason=reason
        )
        log_staff_action(staff, 'DELETE_REQUEST', 'PRODUCT', product)
        messages.success(request, f"Delete request submitted for Product '{product.name}'.")
    return redirect('staff_product_list')


# --- CATEGORIES ---

CategoryForm = modelform_factory(
    Category,
    fields=['name'],
    widgets={
        'name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'})
    }
)

@staff_login_required
def staff_category_list(request, staff=None):
    company = staff.company
    categories = Category.objects.filter(company=company)
    return render(request, 'staff/staff_category_list.html', {
        'staff': staff, 'company': company, 'categories': categories
    })

@staff_login_required
def staff_category_create(request, staff=None):
    company = staff.company
    if request.method == 'POST':
        name = request.POST.get("name")
        if not name or not name.strip():
            messages.error(request, "Category name cannot be empty or spaces only")
            return redirect("staff_category_list")
        
        if Category.objects.filter(company=company, name__iexact=name).exists():
            messages.error(request, "Category already exists")
            return redirect("staff_category_list")
        
        category = Category.objects.create(company=company, name=name)
        log_staff_action(staff, 'CREATE', 'CATEGORY', category)
        messages.success(request, f"Category '{category.name}' created.")
        return redirect('staff_category_list')
        
    return render(request, 'staff/staff_category_form.html', {
        'staff': staff, 'company': company, 'title': 'Add Category'
    })

@staff_login_required
def staff_category_edit(request, pk, staff=None):
    company = staff.company
    category = get_object_or_404(Category, pk=pk, company=company)
    if request.method == 'POST':
        name = request.POST.get("name")
        if not name or not name.strip():
            messages.error(request, "Category name cannot be empty")
        else:
            category.name = name
            category.save()
            log_staff_action(staff, 'EDIT', 'CATEGORY', category)
            messages.success(request, f"Category '{category.name}' updated.")
            return redirect('staff_category_list')
            
    return render(request, 'staff/staff_category_form.html', {
        'staff': staff, 'company': company, 'title': 'Edit Category', 'category': category
    })

@staff_login_required
def staff_category_delete_request(request, pk, staff=None):
    company = staff.company
    category = get_object_or_404(Category, pk=pk, company=company)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        StaffDeleteRequest.objects.create(
            company=company, requested_by=staff, module='CATEGORY',
            object_id=category.pk, object_repr=str(category), reason=reason
        )
        log_staff_action(staff, 'DELETE_REQUEST', 'CATEGORY', category)
        messages.success(request, f"Delete request submitted for Category '{category.name}'.")
    return redirect('staff_category_list')


# --- PURCHASE ORDERS ---

PurchaseOrderForm = modelform_factory(
    PurchaseOrder,
    fields=['vendor', 'order_number', 'status'],
    widgets={
        'vendor': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'order_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'status': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
    }
)

POItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    fields=['product', 'quantity', 'cost_price'],
    widgets={
        'product': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'quantity': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'cost_price': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500', 'step': '0.01'}),
    },
    extra=1, can_delete=True
)

@staff_login_required
def staff_po_list(request, staff=None):
    company = staff.company
    pos = PurchaseOrder.objects.filter(company=company).order_by('-created_at')
    return render(request, 'staff/staff_po_list.html', {
        'staff': staff, 'company': company, 'pos': pos
    })

@staff_login_required
def staff_po_create(request, staff=None):
    company = staff.company
    from inventory.models import Vendor
    from decimal import Decimal, InvalidOperation
    from datetime import datetime, date
    vendors = Vendor.objects.filter(company=company)
    products = Product.objects.filter(company=company)
    today = date.today()
    
    from company.currency_utils import get_currency_symbol as _get_sym
    _sym = _get_sym(company.display_currency)
    
    if request.method == 'POST':
        vendor_id = request.POST.get("vendor")

        try:
            vendor = Vendor.objects.get(id=vendor_id, company=company)
        except Vendor.DoesNotExist:
            messages.error(request, "Selected vendor does not exist.")
            return redirect("staff_po_create")

        product_ids = request.POST.getlist("product[]")
        quantities = request.POST.getlist("quantity[]")
        cost_prices = request.POST.getlist("cost_price[]")
        batch_numbers = request.POST.getlist("batch_number[]")
        expiry_dates = request.POST.getlist("expiry_date[]")

        if not product_ids:
            messages.error(request, "Please select at least one product.")
            return redirect("staff_po_create")

        for i in range(len(product_ids)):
            if not product_ids[i]: continue
            product = Product.objects.get(id=product_ids[i], company=company)
            batch_number = batch_numbers[i].strip() if i < len(batch_numbers) else None
            if batch_number:
                if PurchaseOrderItem.objects.filter(product=product, batch_number__iexact=batch_number).exists():
                    messages.error(request, f"Batch number '{batch_number}' already exists for product '{product.name}'.")
                    return redirect("staff_po_create")

        try:
            order = PurchaseOrder.objects.create(company=company, vendor=vendor, total_amount=0)
            total_amount = Decimal('0.00')

            for index, product_id in enumerate(product_ids):
                if not product_id: continue
                try:
                    product = Product.objects.get(id=product_id, company=company)
                except Product.DoesNotExist:
                    order.delete()
                    messages.error(request, "One of the selected products does not exist.")
                    return redirect("staff_po_create")

                try:
                    quantity = int(quantities[index])
                    cost_price = Decimal(cost_prices[index])
                except (ValueError, IndexError, InvalidOperation):
                    order.delete()
                    messages.error(request, "Invalid quantity or cost price.")
                    return redirect("staff_po_create")

                from company.currency_utils import convert_to_inr, get_exchange_rates as _ger
                _cur = company.display_currency
                if _cur != 'INR':
                    _rates = _ger()
                    cost_price = convert_to_inr(cost_price, _cur, _rates)

                if quantity <= 0 or quantity > 99999:
                    order.delete()
                    messages.error(request, f"Quantity boundary exceeded for '{product.name}'. Max allowed is 99,999.")
                    return redirect("staff_po_create")

                if cost_price <= 0 or cost_price >= Decimal('100000000.00'):
                    order.delete()
                    messages.error(request, f"Cost price boundary exceeded for '{product.name}'. Max allowed is {_sym}99,999,999.99.")
                    return redirect("staff_po_create")

                item_total = quantity * cost_price
                if item_total >= Decimal('100000000.00'):
                    order.delete()
                    messages.error(request, f"Total value of '{product.name}' (Qty × Price) exceeds maximum limit.")
                    return redirect("staff_po_create")
                
                if total_amount + item_total >= Decimal('100000000.00'):
                    order.delete()
                    messages.error(request, f"Overall order total exceeds maximum database limit.")
                    return redirect("staff_po_create")
                
                expiry_date = expiry_dates[index].strip() if index < len(expiry_dates) and expiry_dates[index].strip() else None
                if expiry_date:
                    try:
                        expiry_date_obj = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                    except ValueError:
                        order.delete()
                        messages.error(request, f"Invalid expiry date format for '{product.name}'.")
                        return redirect("staff_po_create")
                    if expiry_date_obj < date.today():
                        order.delete()
                        messages.error(request, f"Expiry date cannot be in the past for '{product.name}'.")
                        return redirect("staff_po_create")

                batch_number = batch_numbers[index].strip() if index < len(batch_numbers) and batch_numbers[index].strip() else None

                if product.is_expiry_tracked and (not batch_number or not expiry_date):
                    order.delete()
                    messages.error(request, f"Batch number and expiry date are required for {product.name}.")
                    return redirect("staff_po_create")

                PurchaseOrderItem.objects.create(
                    order=order, product=product, quantity=quantity, cost_price=cost_price,
                    batch_number=batch_number, expiry_date=expiry_date
                )
                total_amount += item_total

            order.total_amount = total_amount
            last_po = PurchaseOrder.objects.filter(company=company).exclude(id=order.id).order_by('-id').first()
            new_num = 1
            if last_po and last_po.order_number and last_po.order_number.startswith('PO-'):
                try:
                    new_num = int(last_po.order_number.split('-')[1]) + 1
                except ValueError:
                    new_num = PurchaseOrder.objects.filter(company=company).count() + 1
            else:
                new_num = PurchaseOrder.objects.filter(company=company).count() + 1
                
            order_number = f"PO-{new_num:02d}"
            while PurchaseOrder.objects.filter(company=company, order_number=order_number).exists():
                new_num += 1
                order_number = f"PO-{new_num:02d}"
                
            order.order_number = order_number
            order.save(update_fields=["total_amount", "order_number"])
            
            log_staff_action(staff, 'CREATE', 'PO', order)
            messages.success(request, f"Purchase Order '{order.order_number}' created.")
            return redirect('staff_po_list')
        except Exception as e:
            messages.error(request, f"Error creating purchase order: {str(e)}")
            return redirect("staff_po_create")

    return render(request, 'staff/staff_po_form.html', {
        'staff': staff, 'company': company, 'vendors': vendors, 'products': products, 'min_expiry_date': today, 'title': 'Add Purchase Order'
    })

@staff_login_required
def staff_po_edit(request, pk, staff=None):
    company = staff.company
    order = get_object_or_404(PurchaseOrder, id=pk, company=company)
    items = order.items.select_related("product")
    
    from django.db import transaction
    from inventory.models import ProductBatch, StockTransaction
    from django.db.models import Sum


    if request.method == "POST" and order.status == "DRAFT":
        messages.error(request, "Submit Purchase Order before receiving stock.")
        return redirect("staff_po_list")

    if order.status == "RECEIVED":
        return render(request, "staff/staff_po_detail.html", {
            "order": order, "items": items, "company": company, "staff": staff,
            "title": "Purchase Order Details"
        })

    if request.method == "POST":
        selected_items = request.POST.getlist("selected_items")
        if not selected_items:
            messages.error(request, "Select at least one item")
            return redirect("staff_po_edit", pk=pk)

        with transaction.atomic():
            for item_id in selected_items:
                qty_key = f"received_qty_{item_id}"
                received_qty = request.POST.get(qty_key)
                if not received_qty: continue
                try:
                    received_qty = int(received_qty)
                except ValueError:
                    continue

                item = get_object_or_404(PurchaseOrderItem, id=item_id, order=order)
                remaining = item.quantity - item.received_quantity
                
                if received_qty <= 0 or received_qty > remaining: continue

                product = item.product
                if product.is_expiry_tracked:
                    batch_number = item.batch_number
                    expiry_date = item.expiry_date
                else:
                    batch_number = item.batch_number or "NO-BATCH"
                    expiry_date = None

                batch, _ = ProductBatch.objects.get_or_create(
                    company=company, product=product, batch_number=batch_number,
                    defaults={"expiry_date": expiry_date, "quantity": 0}
                )
                batch.quantity += received_qty
                batch.save(update_fields=["quantity"])

                item.received_quantity += received_qty
                item.save(update_fields=["received_quantity"])

                product.purchase_price = item.cost_price
                product.stock_quantity = ProductBatch.objects.filter(
                    company=company, product=product
                ).aggregate(total=Sum("quantity"))["total"] or 0
                product.save(update_fields=["purchase_price", "stock_quantity"])

                StockTransaction.objects.create(
                    company=company, product=product, transaction_type="IN",
                    source="PURCHASE", quantity=received_qty,
                    reference_number=order.order_number, created_by=staff.user
                )

            all_received = all(i.received_quantity == i.quantity for i in order.items.all())
            any_received = any(i.received_quantity > 0 for i in order.items.all())

            if all_received:
                order.status = "RECEIVED"
            elif any_received:
                order.status = "PARTIAL"
            else:
                order.status = "ORDERED"

            order.save(update_fields=["status"])
            log_staff_action(staff, 'RECEIVE', 'PO', order)
            messages.success(request, "Selected items received successfully")
            return redirect("staff_po_edit", pk=pk)

    return render(request, "staff/staff_po_detail.html", {
        "order": order, "items": items, "company": company, "staff": staff,
        "title": "Purchase Order Details"
    })

@staff_login_required
def staff_submit_purchase_order(request, pk, staff=None):
    company = staff.company
    order = get_object_or_404(PurchaseOrder, id=pk, company=company)

    if order.status != "DRAFT":
        return redirect("staff_po_edit", pk=pk)

    order.status = "ORDERED"
    order.save(update_fields=["status"])
    log_staff_action(staff, 'EDIT', 'PO', order)

    messages.warning(request, "Draft purchase order submitted successfully.")
    return redirect("staff_po_edit", pk=pk)

@staff_login_required
def staff_po_delete_request(request, pk, staff=None):
    company = staff.company
    po = get_object_or_404(PurchaseOrder, pk=pk, company=company)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        StaffDeleteRequest.objects.create(
            company=company, requested_by=staff, module='PO',
            object_id=po.pk, object_repr=str(po), reason=reason
        )
        log_staff_action(staff, 'DELETE_REQUEST', 'PO', po)
        messages.success(request, f"Delete request submitted for PO '{po.order_number}'.")
    return redirect('staff_po_list')


# --- SALES ORDERS ---

SalesOrderForm = modelform_factory(
    SalesOrder,
    fields=['customer_name', 'order_number', 'status'],
    widgets={
        'customer_name': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'order_number': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'status': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
    }
)

SOItemFormSet = inlineformset_factory(
    SalesOrder, SalesOrderItem,
    fields=['product', 'quantity', 'price'],
    widgets={
        'product': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'quantity': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500'}),
        'price': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500', 'step': '0.01'}),
    },
    extra=1, can_delete=True
)

@staff_login_required
def staff_so_list(request, staff=None):
    company = staff.company
    from django.db.models import Sum, Value
    from django.db.models.functions import Coalesce
    orders_queryset = SalesOrder.objects.filter(company=company).annotate(
        quantity=Coalesce(Sum('items__quantity'), Value(0))
    ).order_by('-created_at')
    return render(request, 'staff/staff_so_list.html', {
        'staff': staff, 'company': company, 'orders': orders_queryset
    })

@staff_login_required
def staff_so_create(request, staff=None):
    company = staff.company
    products = Product.objects.filter(company=company)
    
    from datetime import date, timedelta
    from django.utils import timezone
    from django.db.models import F, Q, Sum
    from inventory.models import ProductBatch, StockTransaction

    today = timezone.now().date()
    warning_near_expiry = ProductBatch.objects.filter(
        company=company, expiry_date__range=[today, today + timedelta(days=30)],
        quantity__gt=0, is_active=True
    ).exists()

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        product_ids = request.POST.getlist("product[]")
        quantities = request.POST.getlist("quantity[]")

        if not customer_name:
            messages.error(request, "Customer name is required.")
            return redirect("staff_so_create")

        if len(customer_name) > 50:
            messages.error(request, "Customer name cannot exceed 50 characters.")
            return redirect("staff_so_create")

        if not product_ids:
            messages.error(request, "Add at least one product.")
            return redirect("staff_so_create")

        allocation_mode = request.POST.get("allocation_mode", "auto")
        manual_batches_raw = request.POST.getlist("manual_batches[]")
        
        from collections import OrderedDict
        import json
        consolidated_items = OrderedDict()
        
        for i in range(len(product_ids)):
            try:
                product_id = product_ids[i]
                if not product_id or product_id == "undefined":
                    messages.error(request, "Please select a valid product.")
                    return redirect("staff_so_create")

                p_id = int(product_id)
                qty = int(quantities[i])
                
                manual_data = []
                if allocation_mode == "manual":
                    try:
                        manual_data = json.loads(manual_batches_raw[i]) if i < len(manual_batches_raw) else []
                    except json.JSONDecodeError:
                        manual_data = []
            except (IndexError, ValueError):
                messages.error(request, "Invalid product data.")
                return redirect("staff_so_create")

            if qty <= 0:
                messages.error(request, "Quantity must be greater than 0.")
                return redirect("staff_so_create")
                
            if p_id in consolidated_items:
                consolidated_items[p_id]["qty"] += qty
                if allocation_mode == "manual":
                    consolidated_items[p_id]["manual_batches"].extend(manual_data)
            else:
                consolidated_items[p_id] = {"qty": qty, "manual_batches": manual_data}

        order_items_data = []
        total_amount = 0
        from django.db import transaction
        with transaction.atomic():
            for p_id, item_data in consolidated_items.items():
                qty = item_data["qty"]
                product = get_object_or_404(Product, id=p_id, company=company)
                allocations = []
                
                if allocation_mode == "manual":
                    manual_qty_map = {}
                    for mb in item_data["manual_batches"]:
                        bid = mb.get("id")
                        if bid: manual_qty_map[bid] = manual_qty_map.get(bid, 0) + int(mb.get("quantity", 0))
                    
                    total_manual = sum(manual_qty_map.values())
                    if total_manual != qty:
                        messages.error(request, f"Manual batch allocation mismatch for {product.name}. Selected {total_manual}, needed {qty}.")
                        return redirect("staff_so_create")
                        
                    for bid, bqty in manual_qty_map.items():
                        if bqty <= 0: continue
                        batch = ProductBatch.objects.select_for_update().filter(id=bid, company=company, product=product, is_active=True).first()
                        if not batch or batch.quantity < bqty:
                            messages.error(request, f"Insufficient stock in selected batch for {product.name}.")
                            return redirect("staff_so_create")
                        allocations.append({"batch": batch, "deduct_qty": bqty})
                else:
                    batch_query = ProductBatch.objects.select_for_update().filter(
                        Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
                        company=company, product=product, quantity__gt=0, is_active=True
                    )

                    if company.plan_type == 'STARTER':
                        batches = list(batch_query.order_by("created_at"))
                    else:
                        batches = list(batch_query.order_by(F("expiry_date").asc(nulls_last=True)))

                    remaining_qty = qty
                    for batch in batches:
                        if remaining_qty <= 0: break
                        deduct_qty = min(batch.quantity, remaining_qty)
                        allocations.append({"batch": batch, "deduct_qty": deduct_qty})
                        remaining_qty -= deduct_qty
                        
                    if remaining_qty > 0:
                        messages.error(request, f"Insufficient stock for {product.name}.")
                        return redirect("staff_so_create")

                order_items_data.append({"product": product, "quantity": qty, "allocations": allocations})
                total_amount += product.selling_price * qty

            last_so = SalesOrder.objects.filter(company=company).order_by('-id').first()
            new_num = 1
            if last_so and last_so.order_number and last_so.order_number.startswith('ORD-'):
                try:
                    new_num = int(last_so.order_number.split('-')[1]) + 1
                except ValueError:
                    new_num = SalesOrder.objects.filter(company=company).count() + 1
            else:
                new_num = SalesOrder.objects.filter(company=company).count() + 1
                
            order_number = f"ORD-{new_num:02d}"
            while SalesOrder.objects.filter(company=company, order_number=order_number).exists():
                new_num += 1
                order_number = f"ORD-{new_num:02d}"
            
            order = SalesOrder.objects.create(
                company=company, order_number=order_number, customer_name=customer_name, total_amount=total_amount
            )

            from inventory.utils.stock_validation import validate_stock_change

            for item in order_items_data:
                product = item["product"]
                qty = item["quantity"]
                allocations = item["allocations"]

                SalesOrderItem.objects.create(order=order, product=product, quantity=qty, price=product.selling_price)

                for alloc in allocations:
                    batch = alloc["batch"]
                    deduct_qty = alloc["deduct_qty"]
                    validate_stock_change(batch, deduct_qty, "REMOVE")
                    batch.quantity -= deduct_qty
                    batch.save(update_fields=["quantity"])

                    StockTransaction.objects.create(
                        company=company, product=product, batch=batch, transaction_type="OUT",
                        source="SALE", quantity=deduct_qty, reference_number=order.order_number, created_by=staff.user
                    )

                product.stock_quantity = ProductBatch.objects.filter(
                    Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
                    company=company, product=product, quantity__gt=0, is_active=True
                ).aggregate(total=Sum("quantity"))["total"] or 0
                product.save(update_fields=["stock_quantity"])

            log_staff_action(staff, 'CREATE', 'SO', order)
            messages.success(request, f"Sales order {order.order_number} created successfully.")
            return redirect("staff_so_list")

    return render(request, "staff/staff_so_form.html", {
        "products": products, "warning_near_expiry": warning_near_expiry, "company": company, "staff": staff, "title": "Add Sales Order"
    })

@staff_login_required
def staff_so_edit(request, pk, staff=None):
    company = staff.company
    order = get_object_or_404(SalesOrder, id=pk, company=company)
    items = order.items.all()

    from company.currency_utils import format_price as fmt_price, get_exchange_rates
    cur = company.display_currency
    rates = get_exchange_rates()
    from inventory.views import get_item_unit_price

    for item in items: 
        unit_price = get_item_unit_price(item)
        item.unit_price = unit_price
        item.subtotal = item.quantity * unit_price
        item.formatted_price = fmt_price(unit_price, cur, rates)
        item.formatted_subtotal = fmt_price(item.subtotal, cur, rates)

    order.formatted_total = fmt_price(order.total_amount, cur, rates)

    context = {
        'order': order,
        'items': items,
        'company': company,
        'staff': staff,
    }

    return render(request, "staff/staff_so_detail.html", context)

@staff_login_required
def staff_update_so_status(request, pk, staff=None):
    company = staff.company
    order = get_object_or_404(SalesOrder, id=pk, company=company)

    if request.method == "POST":
        new_status = request.POST.get("status")

        if order.status in ["DELIVERED", "CANCELLED"]:
            messages.error(request, "This order is in a final state and cannot be modified.")
            return redirect("staff_so_edit", pk=pk)

        order.status = new_status
        order.save(update_fields=["status"])
        log_staff_action(staff, 'UPDATE_STATUS', 'SO', order, extra={'new_status': new_status})
        messages.success(request, f"Order status updated to {new_status}")

    return redirect("staff_so_edit", pk=pk)

@staff_login_required
def staff_so_delete_request(request, pk, staff=None):
    company = staff.company
    so = get_object_or_404(SalesOrder, pk=pk, company=company)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        StaffDeleteRequest.objects.create(
            company=company, requested_by=staff, module='SO',
            object_id=so.pk, object_repr=str(so), reason=reason
        )
        log_staff_action(staff, 'DELETE_REQUEST', 'SO', so)
        messages.success(request, f"Delete request submitted for SO '{so.order_number}'.")
    return redirect('staff_so_list')


from inventory.forms import CustomerForm as OwnerCustomerForm, AddressForm, ContactPersonForm
from inventory.models import Customer, Address, ContactPerson
from django.forms import inlineformset_factory
from django.db import transaction

@staff_login_required
def staff_customer_list(request, staff=None):
    company = staff.company
    customers = Customer.objects.filter(company=company).order_by('-created_at')
    return render(request, 'staff/staff_customer_list.html', {
        'staff': staff, 'company': company, 'customers': customers
    })

@staff_login_required
def staff_customer_create(request, staff=None):
    company = staff.company
    AddressFormSet = inlineformset_factory(Customer, Address, form=AddressForm, extra=1, can_delete=True)
    ContactFormSet = inlineformset_factory(Customer, ContactPerson, form=ContactPersonForm, extra=1, can_delete=True)

    if request.method == "POST":
        form = OwnerCustomerForm(request.POST)
        address_formset = AddressFormSet(request.POST, prefix="addresses")
        contact_formset = ContactFormSet(request.POST, prefix="contacts")

        if form.is_valid() and address_formset.is_valid() and contact_formset.is_valid():
            custom_has_error = False
            email = form.cleaned_data.get('email')
            mobile = form.cleaned_data.get('mobile')
            gst_number = form.cleaned_data.get('gst_number')

            if email and Customer.objects.filter(company=company, email=email).exists():
                form.add_error('email', 'A customer with this email already exists.')
                custom_has_error = True
            if mobile and Customer.objects.filter(company=company, mobile=mobile).exists():
                form.add_error('mobile', 'A customer with this mobile number already exists.')
                custom_has_error = True
            if gst_number and Customer.objects.filter(company=company, gst_number=gst_number).exists():
                form.add_error('gst_number', 'A customer with this GST number already exists.')
                custom_has_error = True

            for c_form in contact_formset:
                if c_form.cleaned_data and not c_form.cleaned_data.get('DELETE', False):
                    c_email = c_form.cleaned_data.get('email')
                    c_phone = c_form.cleaned_data.get('phone') or c_form.cleaned_data.get('mobile')
                    if c_email and ContactPerson.objects.filter(customer__company=company, email=c_email).exists():
                        c_form.add_error('email', 'A contact with this email already exists.')
                        custom_has_error = True
                    if c_phone:
                        try:
                            if ContactPerson.objects.filter(customer__company=company, phone=c_phone).exists():
                                c_form.add_error('phone' if 'phone' in c_form.fields else 'mobile', 'A contact with this phone already exists.')
                                custom_has_error = True
                        except: pass
                        try:
                            if ContactPerson.objects.filter(customer__company=company, mobile=c_phone).exists():
                                c_form.add_error('mobile' if 'mobile' in c_form.fields else 'phone', 'A contact with this mobile already exists.')
                                custom_has_error = True
                        except: pass

            for a_form in address_formset:
                if a_form.cleaned_data and not a_form.cleaned_data.get('DELETE', False):
                    a_email = a_form.cleaned_data.get('email')
                    a_phone = a_form.cleaned_data.get('phone') or a_form.cleaned_data.get('mobile')
                    if a_email and Address.objects.filter(customer__company=company, email=a_email).exists():
                        a_form.add_error('email', 'An address with this email already exists.')
                        custom_has_error = True
                    if a_phone:
                        try:
                            if Address.objects.filter(customer__company=company, phone=a_phone).exists():
                                a_form.add_error('phone' if 'phone' in a_form.fields else 'mobile', 'An address with this phone already exists.')
                                custom_has_error = True
                        except: pass
                        try:
                            if Address.objects.filter(customer__company=company, mobile=a_phone).exists():
                                a_form.add_error('mobile' if 'mobile' in a_form.fields else 'phone', 'An address with this mobile already exists.')
                                custom_has_error = True
                        except: pass

            if not custom_has_error:
                with transaction.atomic():
                    customer = form.save(commit=False)
                    customer.company = company
                    customer.save()
                    address_formset.instance = customer
                    contact_formset.instance = customer
                    address_formset.save()
                    contact_formset.save()
                    log_staff_action(staff, 'CREATE', 'CUSTOMER', customer)
                    messages.success(request, "Customer added successfully!")
                    return redirect("staff_customer_list")
            else:
                messages.error(request, "Please correct the duplicate entry errors below.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OwnerCustomerForm()
        address_formset = AddressFormSet(prefix="addresses")
        contact_formset = ContactFormSet(prefix="contacts")

    return render(request, "staff/staff_customer_form.html", {
        "form": form, "address_formset": address_formset, "contact_formset": contact_formset,
        "is_edit": False, "company": company, "staff": staff, "title": "Add Customer"
    })

@staff_login_required
def staff_customer_edit(request, pk, staff=None):
    company = staff.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    AddressFormSet = inlineformset_factory(Customer, Address, form=AddressForm, extra=0, can_delete=True)
    ContactFormSet = inlineformset_factory(Customer, ContactPerson, form=ContactPersonForm, extra=0, can_delete=True)

    if request.method == "POST":
        form = OwnerCustomerForm(request.POST, instance=customer)
        address_formset = AddressFormSet(request.POST, instance=customer, prefix="addresses")
        contact_formset = ContactFormSet(request.POST, instance=customer, prefix="contacts")

        if form.is_valid() and address_formset.is_valid() and contact_formset.is_valid():
            custom_has_error = False
            email = form.cleaned_data.get('email')
            mobile = form.cleaned_data.get('mobile')
            gst_number = form.cleaned_data.get('gst_number')

            if email and Customer.objects.filter(company=company, email=email).exclude(pk=customer.pk).exists():
                form.add_error('email', 'A customer with this email already exists.')
                custom_has_error = True
            if mobile and Customer.objects.filter(company=company, mobile=mobile).exclude(pk=customer.pk).exists():
                form.add_error('mobile', 'A customer with this mobile number already exists.')
                custom_has_error = True
            if gst_number and Customer.objects.filter(company=company, gst_number=gst_number).exclude(pk=customer.pk).exists():
                form.add_error('gst_number', 'A customer with this GST number already exists.')
                custom_has_error = True

            for c_form in contact_formset:
                if c_form.cleaned_data and not c_form.cleaned_data.get('DELETE', False):
                    c_email = c_form.cleaned_data.get('email')
                    c_phone = c_form.cleaned_data.get('phone') or c_form.cleaned_data.get('mobile')
                    contact_id = c_form.instance.pk if c_form.instance.pk else None
                    qs = ContactPerson.objects.filter(customer__company=company, email=c_email) if c_email else None
                    if qs and qs.exclude(pk=contact_id).exists():
                        c_form.add_error('email', 'A contact with this email already exists.')
                        custom_has_error = True
                    if c_phone:
                        try:
                            if ContactPerson.objects.filter(customer__company=company, phone=c_phone).exclude(pk=contact_id).exists():
                                c_form.add_error('phone' if 'phone' in c_form.fields else 'mobile', 'A contact with this phone already exists.')
                                custom_has_error = True
                        except: pass
                        try:
                            if ContactPerson.objects.filter(customer__company=company, mobile=c_phone).exclude(pk=contact_id).exists():
                                c_form.add_error('mobile' if 'mobile' in c_form.fields else 'phone', 'A contact with this mobile already exists.')
                                custom_has_error = True
                        except: pass

            for a_form in address_formset:
                if a_form.cleaned_data and not a_form.cleaned_data.get('DELETE', False):
                    a_email = a_form.cleaned_data.get('email')
                    a_phone = a_form.cleaned_data.get('phone') or a_form.cleaned_data.get('mobile')
                    addr_id = a_form.instance.pk if a_form.instance.pk else None
                    qs = Address.objects.filter(customer__company=company, email=a_email) if a_email else None
                    if qs and qs.exclude(pk=addr_id).exists():
                        a_form.add_error('email', 'An address with this email already exists.')
                        custom_has_error = True
                    if a_phone:
                        try:
                            if Address.objects.filter(customer__company=company, phone=a_phone).exclude(pk=addr_id).exists():
                                a_form.add_error('phone' if 'phone' in a_form.fields else 'mobile', 'An address with this phone already exists.')
                                custom_has_error = True
                        except: pass
                        try:
                            if Address.objects.filter(customer__company=company, mobile=a_phone).exclude(pk=addr_id).exists():
                                a_form.add_error('mobile' if 'mobile' in a_form.fields else 'phone', 'An address with this mobile already exists.')
                                custom_has_error = True
                        except: pass

            if not custom_has_error:
                with transaction.atomic():
                    customer = form.save()
                    address_formset.save()
                    contact_formset.save()
                    log_staff_action(staff, 'EDIT', 'CUSTOMER', customer)
                    messages.success(request, "Customer updated successfully!")
                    return redirect("staff_customer_list")
            else:
                messages.error(request, "Please correct the duplicate entry errors below.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = OwnerCustomerForm(instance=customer)
        address_formset = AddressFormSet(instance=customer, prefix="addresses")
        contact_formset = ContactFormSet(instance=customer, prefix="contacts")

    return render(request, "staff/staff_customer_form.html", {
        "form": form, "address_formset": address_formset, "contact_formset": contact_formset,
        "is_edit": True, "company": company, "staff": staff, "title": "Edit Customer", "customer": customer
    })

@staff_login_required
def staff_customer_delete_request(request, pk, staff=None):
    company = staff.company
    customer = get_object_or_404(Customer, pk=pk, company=company)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        StaffDeleteRequest.objects.create(
            company=company, requested_by=staff, module='CUSTOMER',
            object_id=customer.pk, object_repr=str(customer), reason=reason
        )
        log_staff_action(staff, 'DELETE_REQUEST', 'CUSTOMER', customer)
        messages.success(request, f"Delete request submitted for Customer '{customer.contact_name}'.")
    return redirect('staff_customer_list')


# --- DELETE REQUESTS (Staff view) ---

@staff_login_required
def staff_my_delete_requests(request, staff=None):
    company = staff.company
    requests = StaffDeleteRequest.objects.filter(requested_by=staff).order_by('-created_at')
    return render(request, 'staff/staff_delete_requests.html', {
        'staff': staff, 'company': company, 'requests': requests
    })


from django.http import JsonResponse
from django.utils import timezone
from django.db.models import F

@staff_login_required
def staff_fefo_preview_api(request, staff=None):
    company = staff.company
    
    product_id = request.GET.get("product")
    try:
        quantity = int(request.GET.get("quantity", 0))
    except ValueError:
        quantity = 0

    preview = []
    today = timezone.now().date()

    if product_id and quantity > 0:
        product = get_object_or_404(Product, id=product_id, company=company)

        batch_query = ProductBatch.objects.filter(
            Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
            company=company,
            product=product,
            quantity__gt=0,
            is_active=True
        )

        if company.plan_type == 'STARTER':
            batches = batch_query.order_by("created_at")
        else:
            batches = batch_query.order_by(F("expiry_date").asc(nulls_last=True))

        remaining = quantity
        for batch in batches:
            if remaining <= 0:
                break
            used = min(batch.quantity, remaining)
            preview.append({
                "batch": batch.batch_number,
                "expiry": batch.expiry_date.strftime("%Y-%m-%d") if batch.expiry_date else "No Expiry",
                "qty": used
            })
            remaining -= used
            
    return JsonResponse({
        "preview": preview,
        "max_allocatable": sum(b.quantity for b in batches) if product_id else 0
    })

@staff_login_required
def staff_available_batches_api(request, staff=None):
    company = staff.company
    product_id = request.GET.get("product")

    if not product_id:
        return JsonResponse({"batches": []})

    product = get_object_or_404(Product, id=product_id, company=company)
    today = timezone.now().date()

    batches = ProductBatch.objects.filter(
        Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
        company=company,
        product=product,
        quantity__gt=0,
        is_active=True
    ).order_by("expiry_date")

    data = []
    for batch in batches:
        data.append({
            "id": batch.id,
            "batch_number": batch.batch_number,
            "expiry_date": batch.expiry_date.strftime("%Y-%m-%d") if batch.expiry_date else "No Expiry",
            "quantity": batch.quantity
        })

    return JsonResponse({"batches": data})
