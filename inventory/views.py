import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, Count, F
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import (
    Category, Warehouse, Location, UnitOfMeasure, Product,
    StockRecord, Receipt, ReceiptItem, DeliveryOrder, DeliveryItem,
    InventoryAdjustment, AdjustmentItem, InternalTransfer, TransferItem
)

# --- AUTH VIEWS ---

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
        elif password != password_confirm:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, "Registration successful! Welcome to the IMS Dashboard.")
            return redirect('inventory:dashboard')
            
    return render(request, 'inventory/auth/signup.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect('inventory:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'inventory/auth/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('inventory:login')


def otp_reset_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        step = request.POST.get('step', '1')
        
        if step == '1':
            user = User.objects.filter(email=email).first()
            if user:
                # Simulate OTP generation
                otp = str(random.randint(100000, 999999))
                request.session['reset_otp'] = otp
                request.session['reset_email'] = email
                # Store the mock OTP in a success message so user can see/use it!
                messages.success(request, f"OTP Sent! For demo purposes, your OTP is: {otp}")
                return render(request, 'inventory/auth/otp_verify.html', {'email': email})
            else:
                messages.error(request, "No user found with that email address.")
        elif step == '2':
            otp_entered = request.POST.get('otp')
            new_password = request.POST.get('password')
            new_password_confirm = request.POST.get('password_confirm')
            
            session_otp = request.session.get('reset_otp')
            session_email = request.session.get('reset_email')
            
            if otp_entered != session_otp:
                messages.error(request, "Invalid OTP code.")
                return render(request, 'inventory/auth/otp_verify.html', {'email': session_email})
            elif new_password != new_password_confirm:
                messages.error(request, "Passwords do not match.")
                return render(request, 'inventory/auth/otp_verify.html', {'email': session_email})
            else:
                user = User.objects.filter(email=session_email).first()
                if user:
                    user.set_password(new_password)
                    user.save()
                    # Clean session
                    request.session.pop('reset_otp', None)
                    request.session.pop('reset_email', None)
                    messages.success(request, "Password reset successful! Please log in with your new password.")
                    return redirect('inventory:login')
                else:
                    messages.error(request, "An error occurred during password reset.")
                    
    return render(request, 'inventory/auth/otp_request.html')


# --- PROFILE VIEW ---

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('inventory:profile')
    return render(request, 'inventory/profile.html')


# --- DASHBOARD VIEW ---

@login_required
def dashboard_view(request):
    # Retrieve dynamic filters from GET parameters
    doc_type = request.GET.get('doc_type', '')
    status_filter = request.GET.get('status', '')
    warehouse_id = request.GET.get('warehouse', '')
    category_id = request.GET.get('category', '')
    
    # Calculate KPIs
    total_products = Product.objects.filter(is_active=True).count()
    
    # Low stock calculation: StockRecords where current_stock <= reorder_point
    low_stock_query = StockRecord.objects.filter(current_stock__lte=F('reorder_point'))
    if warehouse_id:
        low_stock_query = low_stock_query.filter(location__warehouse_id=warehouse_id)
    if category_id:
        low_stock_query = low_stock_query.filter(product__category_id=category_id)
    low_stock_count = low_stock_query.count()
    
    pending_receipts = Receipt.objects.filter(status__in=['draft', 'pending']).count()
    pending_deliveries = DeliveryOrder.objects.filter(status__in=['draft', 'picking', 'packed']).count()
    scheduled_transfers = InternalTransfer.objects.filter(status='scheduled').count()
    
    # Fetch lists for table display based on filters
    receipts = Receipt.objects.all()
    deliveries = DeliveryOrder.objects.all()
    adjustments = InventoryAdjustment.objects.all()
    transfers = InternalTransfer.objects.all()
    
    if status_filter:
        receipts = receipts.filter(status=status_filter)
        deliveries = deliveries.filter(status=status_filter)
        adjustments = adjustments.filter(status=status_filter)
        transfers = transfers.filter(status=status_filter)
        
    if warehouse_id:
        # filter receipts where item is at location in warehouse
        receipts = receipts.filter(items__location__warehouse_id=warehouse_id).distinct()
        deliveries = deliveries.filter(items__location__warehouse_id=warehouse_id).distinct()
        adjustments = adjustments.filter(items__location__warehouse_id=warehouse_id).distinct()
        transfers = transfers.filter(Q(from_location__warehouse_id=warehouse_id) | Q(to_location__warehouse_id=warehouse_id)).distinct()
        
    if category_id:
        receipts = receipts.filter(items__product__category_id=category_id).distinct()
        deliveries = deliveries.filter(items__product__category_id=category_id).distinct()
        adjustments = adjustments.filter(items__product__category_id=category_id).distinct()
        transfers = transfers.filter(items__product__category_id=category_id).distinct()

    # Get categories and warehouses for filter dropdowns
    categories = Category.objects.all()
    warehouses = Warehouse.objects.all()
    
    # Construct combined operations history
    operations = []
    
    if not doc_type or doc_type == 'Receipts':
        for r in receipts[:10]:
            operations.append({
                'id': r.id,
                'type': 'Receipt',
                'ref': r.reference_number,
                'party': r.supplier,
                'status': r.get_status_display(),
                'status_class': 'bg-warning' if r.status in ['draft', 'pending'] else ('bg-success' if r.status == 'validated' else 'bg-danger'),
                'date': r.received_at,
                'url': reverse('inventory:receipt_detail', args=[r.id])
            })
            
    if not doc_type or doc_type == 'Delivery':
        for d in deliveries[:10]:
            operations.append({
                'id': d.id,
                'type': 'Delivery Order',
                'ref': d.reference_number,
                'party': d.customer_name or 'N/A',
                'status': d.get_status_display(),
                'status_class': 'bg-info' if d.status in ['draft', 'picking', 'packed'] else ('bg-success' if d.status in ['shipped', 'delivered'] else 'bg-danger'),
                'date': d.created_at,
                'url': reverse('inventory:delivery_detail', args=[d.id])
            })
            
    if not doc_type or doc_type == 'Internal':
        for t in transfers[:10]:
            operations.append({
                'id': t.id,
                'type': 'Internal Transfer',
                'ref': t.reference_number,
                'party': f"{t.from_location} -> {t.to_location}",
                'status': t.get_status_display(),
                'status_class': 'bg-warning' if t.status in ['draft', 'scheduled'] else ('bg-success' if t.status == 'completed' else 'bg-danger'),
                'date': t.created_at,
                'url': reverse('inventory:transfer_detail', args=[t.id])
            })
            
    if not doc_type or doc_type == 'Adjustments':
        for a in adjustments[:10]:
            operations.append({
                'id': a.id,
                'type': 'Adjustment',
                'ref': a.reference_number,
                'party': a.reason,
                'status': a.get_status_display(),
                'status_class': 'bg-warning' if a.status in ['draft', 'pending'] else ('bg-success' if a.status == 'approved' else 'bg-danger'),
                'date': a.created_at,
                'url': reverse('inventory:adjustment_detail', args=[a.id])
            })
            
    # Sort operations by date descending
    operations.sort(key=lambda x: x['date'], reverse=True)
    operations = operations[:15]
    
    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'pending_receipts': pending_receipts,
        'pending_deliveries': pending_deliveries,
        'scheduled_transfers': scheduled_transfers,
        'operations': operations,
        'categories': categories,
        'warehouses': warehouses,
        'selected_doc_type': doc_type,
        'selected_status': status_filter,
        'selected_warehouse': warehouse_id,
        'selected_category': category_id,
    }
    return render(request, 'inventory/dashboard.html', context)


# --- PRODUCT & CATEGORY MANAGEMENT ---

@login_required
def product_list(request):
    q = request.GET.get('q', '')
    cat_id = request.GET.get('category', '')
    
    products = Product.objects.filter(is_active=True)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
    if cat_id:
        products = products.filter(category_id=cat_id)
        
    categories = Category.objects.all()
    
    # Calculate stock levels per location for products
    for p in products:
        p.stock_records = StockRecord.objects.filter(product=p)
        p.total_qty = p.stock_records.aggregate(total=Sum('current_stock'))['total'] or 0
        
    context = {
        'products': products,
        'categories': categories,
        'selected_category': cat_id,
        'q': q,
    }
    return render(request, 'inventory/products/list.html', context)


@login_required
def product_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        uom_id = request.POST.get('uom')
        description = request.POST.get('description', '')
        initial_qty = request.POST.get('initial_qty', '0')
        location_id = request.POST.get('initial_location', '')
        
        category = Category.objects.filter(id=category_id).first() if category_id else None
        uom = get_object_or_404(UnitOfMeasure, id=uom_id)
        
        if not name or not sku:
            messages.error(request, "Name and SKU are required.")
            return redirect('inventory:product_create')
            
        if Product.objects.filter(sku=sku).exists():
            messages.error(request, f"SKU {sku} already exists.")
            return redirect('inventory:product_create')
            
        with transaction.atomic():
            product = Product.objects.create(
                name=name, sku=sku, category=category, uom=uom, description=description
            )
            
            # handle initial stock
            if initial_qty and int(initial_qty) > 0 and location_id:
                location = get_object_or_404(Location, id=location_id)
                StockRecord.objects.create(
                    product=product,
                    location=location,
                    current_stock=int(initial_qty)
                )
                
        messages.success(request, f"Product {product.name} created successfully.")
        return redirect('inventory:product_list')
        
    categories = Category.objects.all()
    uoms = UnitOfMeasure.objects.all()
    locations = Location.objects.all()
    return render(request, 'inventory/products/form.html', {
        'categories': categories,
        'uoms': uoms,
        'locations': locations,
        'title': 'Create Product'
    })


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        category_id = request.POST.get('category')
        uom_id = request.POST.get('uom')
        description = request.POST.get('description', '')
        
        category = Category.objects.filter(id=category_id).first() if category_id else None
        uom = get_object_or_404(UnitOfMeasure, id=uom_id)
        
        if not name or not sku:
            messages.error(request, "Name and SKU are required.")
            return redirect('inventory:product_update', pk=pk)
            
        if Product.objects.filter(sku=sku).exclude(pk=pk).exists():
            messages.error(request, f"SKU {sku} already exists.")
            return redirect('inventory:product_update', pk=pk)
            
        product.name = name
        product.sku = sku
        product.category = category
        product.uom = uom
        product.description = description
        product.save()
        
        messages.success(request, f"Product {product.name} updated successfully.")
        return redirect('inventory:product_list')
        
    categories = Category.objects.all()
    uoms = UnitOfMeasure.objects.all()
    return render(request, 'inventory/products/form.html', {
        'product': product,
        'categories': categories,
        'uoms': uoms,
        'title': 'Update Product'
    })


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = False
    product.save()
    messages.success(request, f"Product {product.name} deleted successfully.")
    return redirect('inventory:product_list')


# --- CATEGORY MANAGEMENT ---

@login_required
def category_list(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            if Category.objects.filter(name=name).exists():
                messages.error(request, "Category already exists.")
            else:
                Category.objects.create(name=name, description=description)
                messages.success(request, "Category created successfully.")
                return redirect('inventory:category_list')
    return render(request, 'inventory/categories/list.html', {'categories': categories})


# --- RECEIPTS (INCOMING STOCK) ---

@login_required
def receipt_list(request):
    receipts = Receipt.objects.all()
    return render(request, 'inventory/receipts/list.html', {'receipts': receipts})


@login_required
def receipt_create(request):
    if request.method == 'POST':
        supplier = request.POST.get('supplier')
        notes = request.POST.get('notes', '')
        
        if not supplier:
            messages.error(request, "Supplier name is required.")
            return redirect('inventory:receipt_create')
            
        ref = f"REC-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        receipt = Receipt.objects.create(
            reference_number=ref,
            supplier=supplier,
            notes=notes,
            created_by=request.user
        )
        return redirect('inventory:receipt_detail', pk=receipt.pk)
        
    return render(request, 'inventory/receipts/create.html')


@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    if request.method == 'POST' and receipt.status == 'draft':
        # Add item to receipt
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        qty = int(request.POST.get('quantity', 0))
        unit_price = float(request.POST.get('unit_price', 0))
        
        product = get_object_or_404(Product, id=product_id)
        location = get_object_or_404(Location, id=location_id)
        
        if qty <= 0:
            messages.error(request, "Quantity must be greater than zero.")
        else:
            ReceiptItem.objects.create(
                receipt=receipt,
                product=product,
                location=location,
                quantity=qty,
                unit_price=unit_price
            )
            messages.success(request, f"Added {qty} units of {product.name} to receipt.")
            return redirect('inventory:receipt_detail', pk=pk)
            
    products = Product.objects.filter(is_active=True)
    locations = Location.objects.filter(is_active=True)
    return render(request, 'inventory/receipts/detail.html', {
        'receipt': receipt,
        'products': products,
        'locations': locations,
    })


@login_required
def receipt_item_delete(request, pk):
    item = get_object_or_404(ReceiptItem, pk=pk)
    receipt_id = item.receipt.id
    if item.receipt.status == 'draft':
        item.delete()
        messages.success(request, "Item removed from receipt.")
    return redirect('inventory:receipt_detail', pk=receipt_id)


@login_required
def receipt_validate(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    if receipt.status != 'draft':
        messages.error(request, "This receipt has already been validated or cancelled.")
        return redirect('inventory:receipt_detail', pk=pk)
        
    if not receipt.items.exists():
        messages.error(request, "Cannot validate an empty receipt.")
        return redirect('inventory:receipt_detail', pk=pk)
        
    # Transaction atomic validation to ensure stock ledger integrity
    with transaction.atomic():
        for item in receipt.items.all():
            stock_record, created = StockRecord.objects.get_or_create(
                product=item.product,
                location=item.location,
                defaults={'current_stock': 0}
            )
            stock_record.current_stock += item.quantity
            stock_record.save()
            
        receipt.status = 'validated'
        receipt.validated_at = timezone.now()
        receipt.save()
        
    messages.success(request, f"Receipt {receipt.reference_number} validated. Stock updated.")
    return redirect('inventory:receipt_detail', pk=pk)


# --- DELIVERY ORDERS (OUTGOING STOCK) ---

@login_required
def delivery_list(request):
    deliveries = DeliveryOrder.objects.all()
    return render(request, 'inventory/deliveries/list.html', {'deliveries': deliveries})


@login_required
def delivery_create(request):
    if request.method == 'POST':
        customer = request.POST.get('customer')
        notes = request.POST.get('notes', '')
        
        ref = f"DEL-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        delivery = DeliveryOrder.objects.create(
            reference_number=ref,
            customer_name=customer,
            notes=notes,
            created_by=request.user
        )
        return redirect('inventory:delivery_detail', pk=delivery.pk)
        
    return render(request, 'inventory/deliveries/create.html')


@login_required
def delivery_detail(request, pk):
    delivery = get_object_or_404(DeliveryOrder, pk=pk)
    if request.method == 'POST' and delivery.status == 'draft':
        # Add item to delivery
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        qty = int(request.POST.get('quantity', 0))
        unit_price = float(request.POST.get('unit_price', 0))
        
        product = get_object_or_404(Product, id=product_id)
        location = get_object_or_404(Location, id=location_id)
        
        # Check stock availability
        stock_record = StockRecord.objects.filter(product=product, location=location).first()
        available_stock = stock_record.current_stock if stock_record else 0
        
        if qty <= 0:
            messages.error(request, "Quantity must be greater than zero.")
        elif available_stock < qty:
            messages.error(request, f"Insufficient stock at {location}. Available: {available_stock}")
        else:
            DeliveryItem.objects.create(
                delivery=delivery,
                product=product,
                location=location,
                quantity=qty,
                unit_price=unit_price
            )
            messages.success(request, f"Added {qty} units of {product.name} to delivery order.")
            return redirect('inventory:delivery_detail', pk=pk)
            
    products = Product.objects.filter(is_active=True)
    locations = Location.objects.filter(is_active=True)
    return render(request, 'inventory/deliveries/detail.html', {
        'delivery': delivery,
        'products': products,
        'locations': locations,
    })


@login_required
def delivery_item_delete(request, pk):
    item = get_object_or_404(DeliveryItem, pk=pk)
    delivery_id = item.delivery.id
    if item.delivery.status == 'draft':
        item.delete()
        messages.success(request, "Item removed from delivery order.")
    return redirect('inventory:delivery_detail', pk=delivery_id)


@login_required
def delivery_validate(request, pk):
    delivery = get_object_or_404(DeliveryOrder, pk=pk)
    if delivery.status != 'draft':
        messages.error(request, "This delivery order has already been processed.")
        return redirect('inventory:delivery_detail', pk=pk)
        
    if not delivery.items.exists():
        messages.error(request, "Cannot validate an empty delivery order.")
        return redirect('inventory:delivery_detail', pk=pk)
        
    # Validation / Execution
    with transaction.atomic():
        # Double check all stocks are still sufficient
        for item in delivery.items.all():
            stock_record = StockRecord.objects.filter(product=item.product, location=item.location).first()
            if not stock_record or stock_record.current_stock < item.quantity:
                messages.error(request, f"Validation failed! Insufficient stock for {item.product.name} at {item.location}.")
                return redirect('inventory:delivery_detail', pk=pk)
                
        # Deduct stocks
        for item in delivery.items.all():
            stock_record = StockRecord.objects.get(product=item.product, location=item.location)
            stock_record.current_stock -= item.quantity
            stock_record.save()
            
        delivery.status = 'delivered'
        delivery.delivered_at = timezone.now()
        delivery.save()
        
    messages.success(request, f"Delivery Order {delivery.reference_number} validated and completed successfully.")
    return redirect('inventory:delivery_detail', pk=pk)


# --- INTERNAL TRANSFERS ---

@login_required
def transfer_list(request):
    transfers = InternalTransfer.objects.all()
    return render(request, 'inventory/transfers/list.html', {'transfers': transfers})


@login_required
def transfer_create(request):
    if request.method == 'POST':
        from_location_id = request.POST.get('from_location')
        to_location_id = request.POST.get('to_location')
        product_id = request.POST.get('product')
        qty = int(request.POST.get('quantity', 0))
        notes = request.POST.get('notes', '')
        
        from_loc = get_object_or_404(Location, id=from_location_id)
        to_loc = get_object_or_404(Location, id=to_location_id)
        product = get_object_or_404(Product, id=product_id)
        
        if from_loc == to_loc:
            messages.error(request, "Source and destination locations cannot be the same.")
            return redirect('inventory:transfer_create')
            
        stock_record = StockRecord.objects.filter(product=product, location=from_loc).first()
        available_stock = stock_record.current_stock if stock_record else 0
        
        if qty <= 0:
            messages.error(request, "Quantity must be greater than zero.")
        elif available_stock < qty:
            messages.error(request, f"Insufficient stock at {from_loc}. Available: {available_stock}")
        else:
            ref = f"TRA-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            with transaction.atomic():
                transfer = InternalTransfer.objects.create(
                    reference_number=ref,
                    from_location=from_loc,
                    to_location=to_loc,
                    status='scheduled',
                    quantity=qty,
                    notes=notes,
                    created_by=request.user
                )
                TransferItem.objects.create(
                    transfer=transfer,
                    product=product,
                    quantity=qty
                )
            messages.success(request, f"Transfer {ref} scheduled successfully.")
            return redirect('inventory:transfer_list')
            
    locations = Location.objects.all()
    products = Product.objects.all()
    return render(request, 'inventory/transfers/create.html', {
        'locations': locations,
        'products': products
    })


@login_required
def transfer_detail(request, pk):
    transfer = get_object_or_404(InternalTransfer, pk=pk)
    return render(request, 'inventory/transfers/detail.html', {'transfer': transfer})


@login_required
def transfer_validate(request, pk):
    transfer = get_object_or_404(InternalTransfer, pk=pk)
    if transfer.status != 'scheduled':
        messages.error(request, "Only scheduled transfers can be validated.")
        return redirect('inventory:transfer_detail', pk=pk)
        
    with transaction.atomic():
        # Check source stocks again
        for item in transfer.items.all():
            src_stock = StockRecord.objects.filter(product=item.product, location=transfer.from_location).first()
            if not src_stock or src_stock.current_stock < item.quantity:
                messages.error(request, f"Insufficient stock of {item.product.name} at {transfer.from_location}.")
                return redirect('inventory:transfer_detail', pk=pk)
                
        # Perform move
        for item in transfer.items.all():
            # Deduct source
            src_stock = StockRecord.objects.get(product=item.product, location=transfer.from_location)
            src_stock.current_stock -= item.quantity
            src_stock.save()
            
            # Add destination
            dest_stock, created = StockRecord.objects.get_or_create(
                product=item.product,
                location=transfer.to_location,
                defaults={'current_stock': 0}
            )
            dest_stock.current_stock += item.quantity
            dest_stock.save()
            
        transfer.status = 'completed'
        transfer.completed_at = timezone.now()
        transfer.save()
        
    messages.success(request, f"Transfer {transfer.reference_number} completed. Locations updated.")
    return redirect('inventory:transfer_detail', pk=pk)


# --- STOCK ADJUSTMENTS ---

@login_required
def adjustment_list(request):
    adjustments = InventoryAdjustment.objects.all()
    return render(request, 'inventory/adjustments/list.html', {'adjustments': adjustments})


@login_required
def adjustment_create(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        location_id = request.POST.get('location')
        counted_qty = int(request.POST.get('counted_qty', 0))
        reason = request.POST.get('reason', '')
        
        product = get_object_or_404(Product, id=product_id)
        location = get_object_or_404(Location, id=location_id)
        
        # Get current recorded stock
        stock_record = StockRecord.objects.filter(product=product, location=location).first()
        recorded_qty = stock_record.current_stock if stock_record else 0
        qty_change = counted_qty - recorded_qty
        
        if counted_qty < 0:
            messages.error(request, "Counted quantity cannot be negative.")
            return redirect('inventory:adjustment_create')
            
        ref = f"ADJ-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        with transaction.atomic():
            adjustment = InventoryAdjustment.objects.create(
                reference_number=ref,
                adjustment_type='add' if qty_change >= 0 else 'remove',
                reason=reason,
                status='approved', # Auto approved for convenience
                created_by=request.user if hasattr(request.user, 'is_authenticated') else None
            )
            AdjustmentItem.objects.create(
                adjustment=adjustment,
                product=product,
                location=location,
                quantity_change=qty_change,
                previous_stock=recorded_qty,
                new_stock=counted_qty
            )
            
            # Apply update to stock record
            if not stock_record:
                stock_record = StockRecord.objects.create(product=product, location=location, current_stock=0)
            stock_record.current_stock = counted_qty
            stock_record.last_counted = timezone.now()
            stock_record.save()
            
        messages.success(request, f"Stock Adjustment {ref} applied. {product.name} stock updated to {counted_qty}.")
        return redirect('inventory:adjustment_list')
        
    products = Product.objects.filter(is_active=True)
    locations = Location.objects.filter(is_active=True)
    return render(request, 'inventory/adjustments/create.html', {
        'products': products,
        'locations': locations
    })


@login_required
def adjustment_detail(request, pk):
    adjustment = get_object_or_404(InventoryAdjustment, pk=pk)
    return render(request, 'inventory/adjustments/detail.html', {'adjustment': adjustment})


# --- MOVE HISTORY (STOCK LEDGER) ---

@login_required
def move_history_view(request):
    # Retrieve operations across receipt, delivery, transfers, adjustments and sort by date
    history = []
    
    receipts = Receipt.objects.filter(status='validated')
    for r in receipts:
        for item in r.items.all():
            history.append({
                'date': r.validated_at or r.received_at,
                'ref': r.reference_number,
                'type': 'Receipt (Incoming)',
                'product': item.product.name,
                'sku': item.product.sku,
                'location': str(item.location),
                'change': f"+{item.quantity}",
                'badge': 'success'
            })
            
    deliveries = DeliveryOrder.objects.filter(status='delivered')
    for d in deliveries:
        for item in d.items.all():
            history.append({
                'date': d.delivered_at or d.created_at,
                'ref': d.reference_number,
                'type': 'Delivery (Outgoing)',
                'product': item.product.name,
                'sku': item.product.sku,
                'location': str(item.location),
                'change': f"-{item.quantity}",
                'badge': 'danger'
            })
            
    transfers = InternalTransfer.objects.filter(status='completed')
    for t in transfers:
        for item in t.items.all():
            history.append({
                'date': t.completed_at or t.created_at,
                'ref': t.reference_number,
                'type': 'Internal Transfer',
                'product': item.product.name,
                'sku': item.product.sku,
                'location': f"{t.from_location} → {t.to_location}",
                'change': f"Moved {item.quantity}",
                'badge': 'warning'
            })
            
    adjustments = InventoryAdjustment.objects.filter(status='approved')
    for a in adjustments:
        for item in a.items.all():
            change_str = f"+{item.quantity_change}" if item.quantity_change >= 0 else f"{item.quantity_change}"
            badge_type = 'success' if item.quantity_change >= 0 else 'danger'
            history.append({
                'date': a.approved_at or a.created_at,
                'ref': a.reference_number,
                'type': f"Adjustment ({a.get_adjustment_type_display()})",
                'product': item.product.name,
                'sku': item.product.sku,
                'location': str(item.location),
                'change': change_str,
                'badge': badge_type
            })
            
    history.sort(key=lambda x: x['date'], reverse=True)
    return render(request, 'inventory/move_history.html', {'history': history})


# --- WAREHOUSE SETTINGS ---

@login_required
def warehouse_settings(request):
    warehouses = Warehouse.objects.all()
    locations = Location.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_warehouse':
            name = request.POST.get('name')
            code = request.POST.get('code')
            loc = request.POST.get('location', '')
            if name and code:
                if Warehouse.objects.filter(Q(name=name) | Q(code=code)).exists():
                    messages.error(request, "Warehouse with this name or code already exists.")
                else:
                    Warehouse.objects.create(name=name, code=code, location=loc)
                    messages.success(request, "Warehouse created successfully.")
                    return redirect('inventory:settings')
        elif action == 'create_location':
            wh_id = request.POST.get('warehouse')
            name = request.POST.get('name')
            code = request.POST.get('code', '')
            if wh_id and name:
                warehouse = get_object_or_404(Warehouse, id=wh_id)
                if Location.objects.filter(warehouse=warehouse, name=name).exists():
                    messages.error(request, "Location already exists in this warehouse.")
                else:
                    Location.objects.create(warehouse=warehouse, name=name, code=code)
                    messages.success(request, "Location created successfully.")
                    return redirect('inventory:settings')
                    
    return render(request, 'inventory/settings.html', {
        'warehouses': warehouses,
        'locations': locations
    })
