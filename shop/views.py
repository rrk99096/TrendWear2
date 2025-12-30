from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, F
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Sum, Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string # <--- Needed for HTML email
from django.utils.html import strip_tags
import json
import random
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from .models import DeliveryBoy
from .models import Product, CustomUser, Order, Cart, SaleOrder, RentBooking, Delivery, DeliveryBoy, DeliveryProfile
# UPDATED IMPORTS: No 'Order' or 'OrderItem'. We use SaleOrder and RentBooking.
from .models import (
    CustomUser, Product, ProductVariant, ProductImage, 
    Cart, CartItem, SaleOrder, RentBooking
)
from .forms import UserRegisterForm, UserLoginForm
from django.db.models import Count
from .models import Order, RentBooking 

def collection(request):
    # 1. Fetch one random product for each main category to use as a cover image
    men_cover = Product.objects.filter(category='Men', thumbnail__isnull=False).order_by('?').first()
    women_cover = Product.objects.filter(category='Women', thumbnail__isnull=False).order_by('?').first()
    kids_cover = Product.objects.filter(category='Kids', thumbnail__isnull=False).order_by('?').first()

    # 2. Get all unique Sub-Categories (e.g., "Shirt", "Saree")
    # This finds all sub-categories that actually have products in them
    sub_cats = Product.objects.values('sub_category').annotate(count=Count('id')).order_by('-count')

    context = {
        'men_cover': men_cover,
        'women_cover': women_cover,
        'kids_cover': kids_cover,
        'sub_cats': sub_cats
    }
    return render(request, 'collection.html', context)

def view_category(request, category_name):
    # 1. Fetch products for this specific category (e.g., "Women")
    # We use __iexact to make it case-insensitive (Women matches women)
    products = Product.objects.filter(category__iexact=category_name)
    
    # 2. If no products found, maybe it's a Sub-Category? (e.g., "Sarees")
    if not products.exists():
        products = Product.objects.filter(sub_category__iexact=category_name)

    context = {
        'category_name': category_name,
        'products': products
    }
    return render(request, 'category_detail.html', context)

def rentals(request):
    # 1. Fetch Items (Ordered by ID for stable pagination)
    products_list = Product.objects.filter(
        variants__rent_price_per_day__gt=0
    ).distinct().order_by('-id') 
    
    # 2. Setup Pagination (9 items per page)
    paginator = Paginator(products_list, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 3. Handle AJAX "Load More" Request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        data = []
        for prod in page_obj:
            variant = prod.variants.first()
            price = variant.rent_price_per_day if variant else 0
            
            # Build clean JSON object for JS
            item = {
                'id': prod.id,
                'name': prod.name,
                'category': str(prod.category),
                'image': prod.thumbnail.url if prod.thumbnail else '',
                'price': price,
                'url': reverse('product_detail', args=[prod.id]) 
            }
            data.append(item)
        
        return JsonResponse({
            'data': data, 
            'has_next': page_obj.has_next()
        })

    # 4. Standard Page Load
    return render(request, 'rentals.html', {'featured_rentals': page_obj})

def home(request):
    # 1. Start with ALL products
    products = Product.objects.prefetch_related('variants').all().order_by('-created_at')
    
    # 2. Get Filter Parameters from URL
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '') # 'rent' or 'buy'

    # 3. Apply Text Search (Name or Sub-category)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(sub_category__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 4. Apply Category Filter (Men, Women, Kids)
    if category_filter and category_filter != 'All':
        products = products.filter(category=category_filter)

    # 5. Apply Type Filter (Rent vs Buy)
    if type_filter == 'rent':
        # Show items explicitly marked as Rentable
        products = products.filter(is_rentable=True)
    elif type_filter == 'buy':
        # Show items that have at least one variant with a sale price > 0
        products = products.filter(variants__sale_price__gt=0).distinct()

    context = {
        'products': products,
        # Pass values back so the search bar remembers what you typed
        'search_query': search_query,
        'category_filter': category_filter,
        'type_filter': type_filter,
    }
    return render(request, 'index.html', context)

# ==========================================
# 1. INVENTORY & ADMIN VIEWS
# ==========================================

def is_superuser(user):
    return user.is_superuser

# shop/views.py

# 1. UPDATED: List only Products (Parent items)
@user_passes_test(is_superuser, login_url='login')
def inventory_list(request):
    # Fetch all products with variants pre-loaded
    products = Product.objects.prefetch_related('variants').all().order_by('-created_at')
    return render(request, 'inventory/list.html', {'products': products})

@user_passes_test(is_superuser, login_url='login')
def update_stock(request, variant_id):
    if request.method == 'POST':
        variant = get_object_or_404(ProductVariant, id=variant_id)
        variant.stock_quantity = request.POST.get('stock')
        variant.sale_price = request.POST.get('price')
        variant.save()
        messages.success(request, "Updated successfully.")
    return redirect('inventory') # Stays on List Page

@user_passes_test(is_superuser, login_url='login')
def add_variant(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        
        # 1. Get Form Data
        size = request.POST.get('size')
        color = request.POST.get('color')
        stock = request.POST.get('stock')
        sale_price = request.POST.get('price')
        
        # 2. AUTO-CALCULATE RENT LOGIC
        rent_price = 0
        if product.is_rentable:
            try:
                # 10% of Sale Price
                rent_price = round(float(sale_price) * 0.10, 2)
            except (ValueError, TypeError):
                rent_price = 0
        
        # 3. Create Variant
        ProductVariant.objects.create(
            product=product,
            size=size,
            color=color,
            stock_quantity=stock,
            sale_price=sale_price,
            rent_price_per_day=rent_price
        )
        
        messages.success(request, f"Variant added. Rent price set to ${rent_price}/day.")
    
    return redirect('inventory')

@user_passes_test(is_superuser, login_url='login')
def delete_variant(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variant.delete()
    messages.success(request, "Variant deleted.")
    return redirect('inventory')

@user_passes_test(is_superuser, login_url='login')
def delete_product(request, product_id):
    # 1. Get the product or show 404 if not found
    product = get_object_or_404(Product, id=product_id)
    
    # 2. Delete it (this also deletes variants/images due to cascade)
    product.delete()
    
    # 3. Show success message and go back to inventory list
    messages.success(request, "Product deleted successfully.")
    return redirect('inventory')

# 3. UPDATED: Stock Update should redirect back to Detail Page, not List
@user_passes_test(is_superuser, login_url='login')
def update_stock(request, variant_id):
    if request.method == 'POST':
        new_stock = request.POST.get('stock')
        variant = get_object_or_404(ProductVariant, id=variant_id)
        variant.stock_quantity = new_stock
        variant.save()
        messages.success(request, "Stock updated.")
        # Redirect back to the specific product page
    return redirect('inventory')


# shop/views.py

# shop/views.py

@user_passes_test(is_superuser, login_url='login')
def add_product(request):
    if request.method == 'POST':
        # --- 1. PRODUCT BASIC INFO ---
        name = request.POST.get('name')
        category = request.POST.get('category')
        sub_category = request.POST.get('sub_category')
        desc = request.POST.get('description')
        thumbnail = request.FILES.get('thumbnail')
        is_rentable = request.POST.get('is_rentable') == 'on'

        # Create Parent Product
        new_product = Product.objects.create(
            name=name,
            category=category,
            sub_category=sub_category,
            description=desc,
            thumbnail=thumbnail,
            is_rentable=is_rentable
        )

        # --- 2. MULTIPLE VARIANTS HANDLING ---
        sizes = request.POST.getlist('size[]')
        colors = request.POST.getlist('color[]')
        stocks = request.POST.getlist('stock[]')
        sale_prices = request.POST.getlist('sale_price[]')
        
        # Loop through the lists
        for i in range(len(sizes)):
            
            # LOGIC: Calculate Rent as 10% of Sale Price
            try:
                s_price = float(sale_prices[i])
                # If product is rentable, calculate 10%. Otherwise 0.
                if is_rentable:
                    r_price = round(s_price * 0.10, 2) 
                else:
                    r_price = 0
            except (ValueError, TypeError):
                s_price = 0
                r_price = 0
            
            ProductVariant.objects.create(
                product=new_product,
                size=sizes[i],
                color=colors[i],
                stock_quantity=stocks[i],
                sale_price=s_price,
                rent_price_per_day=r_price  # <--- Auto-calculated value
            )

        # --- 3. IMAGES ---
        images = request.FILES.getlist('images') 
        for img in images:
            ProductImage.objects.create(product=new_product, image=img)
        
        messages.success(request, f"Product added! Rent prices set to 10% of sale price.")
        return redirect('inventory')

    return render(request, 'inventory/add.html')

# ==========================================
# 2. PRODUCT & HOME VIEWS
# ==========================================

def home(request):
    products = Product.objects.prefetch_related('variants').all()
    return render(request, 'index.html', {'products': products})

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    variants = product.variants.all()
    images = product.images.all()
    
    context = {
        'product': product,
        'variants': variants,
        'images': images,
        'initial_variant': variants.first() if variants.exists() else None
    }
    return render(request, 'product_detail.html', context)

# ==========================================
# 3. AUTHENTICATION (OTP & Register)
# ==========================================

def send_otp_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            if CustomUser.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already registered. Please login.'})
            
            otp = str(random.randint(100000, 999999))
            request.session['otp'] = otp
            request.session['otp_email'] = email 
            
            send_mail(
                'Verify your TrendWear Account',
                f'Your verification code is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'status': 'success', 'message': 'OTP sent to your email!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        entered_otp = request.POST.get('otp_code') 
        
        if form.is_valid():
            session_otp = request.session.get('otp')
            session_email = request.session.get('otp_email')
            form_email = form.cleaned_data['email']
            
            if str(entered_otp) != str(session_otp):
                messages.error(request, "Invalid OTP Code.")
            elif session_email != form_email:
                messages.error(request, "Email mismatch.")
            else:
                try:
                    user = form.save() 
                    # Assuming you have a custom backend or default
                    login(request, user) 
                    return redirect('home')
                except Exception as e:
                    messages.error(request, f"System Error: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegisterForm()

    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # --- PROFESSIONAL REDIRECT LOGIC ---
            
            # 1. Check if user is a Delivery Boy
            if DeliveryBoy.objects.filter(user=user).exists():
                return redirect('delivery_dashboard')
            
            # 2. Check if user is an Admin/Superuser
            elif user.is_superuser:
                # Optional: Redirect admin straight to inventory
                return redirect('admin_dashboard') 
            
            # 3. Regular Customer -> Go to Home (or where they were going)
            else:
                next_url = request.GET.get('next')
                return redirect(next_url) if next_url else redirect('home')
                
    else:
        form = UserLoginForm()
    
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

# ==========================================
# 4. CART SYSTEM
# ==========================================

@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # 1. Handle POST Request (Form Submission)
    if request.method == 'POST':
        variant_id = request.POST.get('variant_id')
        action = request.POST.get('action') 
        quantity = int(request.POST.get('quantity', 1))

        # Check if Variant is selected
        if not variant_id:
            messages.error(request, "Please select a size and color.")
            return redirect('product_detail', id=product_id)

        variant = get_object_or_404(ProductVariant, id=variant_id)
        is_rental_bool = (action == 'rent')

        # --- RENTAL SECURITY CHECKS ---
        if is_rental_bool:
            start_str = request.POST.get('start_date')
            end_str = request.POST.get('end_date')

            if not start_str or not end_str:
                messages.error(request, "Please select rental dates.")
                return redirect('product_detail', id=product_id)

            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
            today = timezone.now().date()
            min_allowed_date = today + timedelta(days=2)

            # Rule 1: Not in past
            if start_date < today:
                messages.error(request, "Cannot book dates in the past.")
                return redirect('product_detail', id=product_id)
            
            # Rule 2: 2-Day Advance Notice
            if start_date < min_allowed_date:
                messages.error(request, "Bookings must be made at least 2 days in advance.")
                return redirect('product_detail', id=product_id)
            
            # Rule 3: End date after Start date
            if end_date < start_date:
                messages.error(request, "End date cannot be before start date.")
                return redirect('product_detail', id=product_id)

        # --- STOCK CHECK (Only for Sales) ---
        elif action == 'buy':
            if variant.stock_quantity < quantity:
                messages.error(request, f"Sorry, only {variant.stock_quantity} left in stock!")
                return redirect('product_detail', id=product_id)

        # --- SAVE TO CART ---
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            is_rental=is_rental_bool, 
            defaults={'quantity': 0, 'price_at_add': 0}
        )

        # Update Rental Dates if applicable
        if is_rental_bool:
            cart_item.rental_start_date = start_date
            cart_item.rental_end_date = end_date
            cart_item.price_at_add = variant.rent_price_per_day
        else:
            cart_item.price_at_add = variant.sale_price

        cart_item.quantity += quantity
        cart_item.save()

        messages.success(request, "Added to bag!")
        return redirect('view_cart')

    # 2. Handle Non-POST Request (Safety Fallback)
    # If someone tries to visit /add-to-cart/1/ directly in browser, send them back
    return redirect('product_detail', id=product_id)

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed.")
    return redirect('view_cart')

@login_required(login_url='login')
def update_cart(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        try:
            qty = int(request.POST.get('quantity'))
            if qty > 0:
                cart_item.quantity = qty
                cart_item.save()
            else:
                cart_item.delete()
        except ValueError:
            pass
    return redirect('view_cart')

@login_required(login_url='login')
def view_cart(request):
    # Get or create the cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # optimize query to fetch product info efficiently
    cart_items = cart.items.select_related('product', 'variant').all()
    
    total = cart.total_price()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total': total
    }
    return render(request, 'cart.html', context)

# ==========================================
# 5. CHECKOUT & ORDERS (UPDATED LOGIC)
# ==========================================

@login_required
def checkout(request):
    try:
        cart = request.user.cart
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect('home')

    cart_items = cart.items.all()
    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    total_price = cart.total_price()

    if request.method == 'POST':
        # 1. SAVE ADDRESS DETAILS FIRST
        # We try to get the existing profile or create a new one
        profile, created = DeliveryProfile.objects.get_or_create(user=request.user)
        
        profile.phone = request.POST.get('phone')
        profile.address = request.POST.get('address')
        profile.city = request.POST.get('city')
        profile.zip_code = request.POST.get('zip_code')
        profile.state = request.POST.get('state')
        profile.save()

        # 2. CREATE THE ORDER (Standard Logic)
        new_order = Order.objects.create(
            user=request.user,
            total_price=total_price
        )

        Delivery.objects.create(order=new_order, status='Pending')

        for item in cart_items:
            if item.is_rental:
                RentBooking.objects.create(
                    parent_order=new_order,
                    user=request.user,
                    variant=item.variant,
                    start_date=item.rental_start_date,
                    end_date=item.rental_end_date,
                    quantity=item.quantity,
                    total_price=item.total_cost(),
                    status='Pending'
                )
            else:
                SaleOrder.objects.create(
                    parent_order=new_order,
                    user=request.user,
                    variant=item.variant,
                    quantity=item.quantity,
                    total_price=item.total_cost(),
                    status='Pending'
                )

        cart.items.all().delete()
        
        messages.success(request, "Order placed successfully! Address saved.")
        return redirect('order_success')

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'user': request.user # Pass user to pre-fill form
    })


@login_required
def order_success(request):
    return render(request, 'order_success.html')
@login_required
def order_success(request):
    return render(request, 'order_success.html')

@login_required
def my_orders(request):
    """
    Fetches Parent Orders with all related data (Delivery, Sales, Rentals)
    optimized for the accordion view.
    """
    orders = Order.objects.filter(user=request.user)\
        .select_related('delivery_info')\
        .prefetch_related(
            'sale_items__variant__product', 
            'rent_items__variant__product'
        )\
        .order_by('-created_at')
    
    return render(request, 'orders.html', {'orders': orders})

def home(request):
    # 1. Start with ALL products (prefetch variants to speed up loading)
    products = Product.objects.prefetch_related('variants').all().order_by('-created_at')
    
    # 2. Get Filter Parameters from the URL (sent by the search bar)
    search_query = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '') # 'rent' or 'buy'

    # 3. Apply Text Search (Name, Sub-category, or Description)
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(sub_category__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # 4. Apply Category Filter (Men, Women, Kids)
    if category_filter and category_filter != 'All':
        products = products.filter(category=category_filter)

    # 5. Apply Type Filter (Rent vs Buy)
    if type_filter == 'rent':
        # Show items explicitly marked as Rentable
        products = products.filter(is_rentable=True)
    elif type_filter == 'buy':
        # Show items that have at least one variant with a sale price > 0
        products = products.filter(variants__sale_price__gt=0).distinct()

    # 6. Pass data back to the template
    context = {
        'products': products,
        'search_query': search_query,     # To keep the text in the input
        'category_filter': category_filter, # To keep the dropdown selected
        'type_filter': type_filter,         # To keep the toggle active
    }
    return render(request, 'index.html', context)

# shop/views.py

@login_required
def delivery_dashboard(request):
    # 1. Check if user is a delivery boy
    if not hasattr(request.user, 'deliveryboy'):
        return redirect('home')
    
    driver_profile = request.user.deliveryboy

    # 2. FETCH TASKS
    # Logic: "Show me everything assigned to me, EXCEPT things I already delivered or were cancelled."
    my_tasks = Delivery.objects.filter(
        delivery_boy=driver_profile
    ).exclude(
        status__in=['Delivered', 'Cancelled', 'Failed']
    ).order_by('-assigned_at')
    
    return render(request, 'delivery_dashboard.html', {'tasks': my_tasks})

from django.core.mail import send_mail
from django.conf import settings
import random

@login_required
def update_task_status(request, delivery_id):
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        # Security Check
        if not hasattr(request.user, 'deliveryboy') or delivery.delivery_boy != request.user.deliveryboy:
            messages.error(request, "Unauthorized.")
            return redirect('delivery_dashboard')

        new_status = request.POST.get('new_status')
        
        if new_status in ['Shipped', 'Out for Delivery']:
            delivery.status = new_status
            
            # IF 'OUT FOR DELIVERY': Send simple notification (NO OTP)
            if new_status == 'Out for Delivery':
                delivery.otp = None # Reset any old OTP
                
                user = delivery.order.user
                if user.email:
                    send_mail(
                        f"Order #{delivery.order.id} is Out for Delivery",
                        f"Hi {user.first_name},\n\nYour order is on the way! Our agent has started the ride.\n\nYou will receive an OTP when the agent arrives at your location.",
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True
                    )
            
            delivery.save()
            messages.success(request, f"Status updated to {new_status}")
            
    return redirect('delivery_dashboard')

# 2. NEW VIEW: GENERATE OTP (When Driver Arrives)
@login_required
def send_delivery_otp(request, delivery_id):
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        # Generate Just-In-Time OTP
        otp_code = str(random.randint(100000, 999999))
        delivery.otp = otp_code
        delivery.save()
        
        # Send Email
        user = delivery.order.user
        if user.email:
            try:
                send_mail(
                    f"Delivery OTP: {otp_code}",
                    f"Hi {user.first_name},\n\nThe delivery agent is at your location.\n\n🔐 YOUR OTP: {otp_code}\n\nPlease share this with the agent to receive your package.",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False
                )
                messages.success(request, "OTP sent to customer's email!")
            except:
                messages.error(request, "Failed to send email. Try again.")
        else:
            messages.error(request, "Customer has no email address.")

    return redirect('delivery_dashboard')

# 3. COMPLETE DELIVERY (Verify OTP)
@login_required
def complete_delivery(request, delivery_id):
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        order = delivery.order
        entered_otp = request.POST.get('otp')
        
        if entered_otp == delivery.otp:
            delivery.status = 'Delivered'
            delivery.delivered_at = timezone.now()
            delivery.save() # Triggers Invoice Email Signal
            messages.success(request, "Delivery Successful!")
            rental_items = RentBooking.objects.filter(parent_order=order) 

            for item in rental_items:
                item.status = 'Active'  # This marks it as Active
                item.save()
        else:
            messages.error(request, "❌ Wrong OTP. Try again.")
            
    return redirect('delivery_dashboard')

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser, login_url='login')
def admin_dashboard(request):
    # --- 1. EXISTING KEY METRICS ---
    total_revenue = Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_orders = Order.objects.count()
    total_products = Product.objects.count()
    total_users = CustomUser.objects.filter(is_superuser=False).count()
    
    # --- 2. EXISTING STATUS ALERTS ---
    pending_orders = Order.objects.filter(delivery_info__status='Pending').count()
    # Note: Using 'distinct()' ensures we count unique products, not just variants
    low_stock_count = Product.objects.filter(variants__stock_quantity__lt=5).distinct().count()
    
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    active_rentals_count = RentBooking.objects.filter(
        status__in=['Active', 'Shipped', 'Overdue']
    ).count()

    # --- 3. NEW: CHART DATA GENERATION ---
    
    # A. Sales Trend (Last 7 Days)
    today = timezone.now().date()
    dates = []
    sales_data = []

    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        # Sum total_price of orders created on this specific date
        daily_sales = Order.objects.filter(created_at__date=date).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        dates.append(date.strftime("%b %d")) # Format: "Dec 25"
        sales_data.append(float(daily_sales))

    # B. Rental Status Breakdown
    # We count the specific statuses needed for the Doughnut Chart
    status_counts = {
        'Active': RentBooking.objects.filter(status='Active').count(),
        'Returned': RentBooking.objects.filter(status='Returned').count(),
        'Overdue': RentBooking.objects.filter(status='Overdue').count(),
    }

    # --- 4. CONTEXT ---
    context = {
        # Existing Metrics
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_users': total_users,
        'pending_orders': pending_orders,
        'active_rentals_count': active_rentals_count,
        'low_stock_count': low_stock_count,
        'recent_orders': recent_orders,
        
        # New Chart Data (Converted to JSON for JavaScript)
        'chart_dates': json.dumps(dates),
        'chart_sales': json.dumps(sales_data),
        'chart_status_labels': json.dumps(list(status_counts.keys())),
        'chart_status_data': json.dumps(list(status_counts.values())),
    }

    return render(request, 'admin_dashboard.html', context)

@user_passes_test(is_superuser, login_url='login')
def admin_orders(request):
    # Fetch all orders (newest first)
    orders = Order.objects.select_related('user', 'delivery_info').order_by('-created_at')
    
    # Fetch all drivers (for the dropdown menu)
    drivers = DeliveryBoy.objects.select_related('user').all()

    context = {
        'orders': orders,
        'drivers': drivers
    }
    return render(request, 'admin_orders.html', context)

@user_passes_test(lambda u: u.is_superuser, login_url='login')
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    delivery, created = Delivery.objects.get_or_create(order=order)
    
    # Fetch all active delivery boys for the dropdown
    available_drivers = DeliveryBoy.objects.filter(is_active=True)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        driver_id = request.POST.get('driver_id') # Get selected driver

        # 1. ASSIGN DRIVER & GENERATE OTP (Admin Action)
        if new_status == 'Out for Delivery':
            if not driver_id:
                messages.error(request, "Please select a Delivery Boy to ship the order.")
            else:
                # Assign the driver
                driver = DeliveryBoy.objects.get(id=driver_id)
                delivery.delivery_boy = driver
                
                # Generate OTP
                otp_code = str(random.randint(100000, 999999))
                delivery.otp = otp_code
                
                delivery.status = new_status
                delivery.save() # This triggers the Email Signal with OTP
                messages.success(request, f"Assigned to {driver.user.first_name}. OTP sent to customer.")

        # 2. OTHER STATUS UPDATES
        else:
            delivery.status = new_status
            delivery.save()
            messages.success(request, f"Status updated to {new_status}")
            
        return redirect('admin_order_detail', order_id=order.id)

    context = {
        'order': order,
        'delivery': delivery,
        'drivers': available_drivers, # Pass drivers to template
        'purchased_items': order.sale_items.all(),
        'rented_items': order.rent_items.all(),
    }
    return render(request, 'admin_order_detail.html', context)

@user_passes_test(is_superuser, login_url='login')
def assign_driver(request, order_id):
    if request.method == 'POST':
        driver_id = request.POST.get('driver_id')
        order = get_object_or_404(Order, id=order_id)
        
        # Get the delivery record associated with this order
        delivery_task = order.delivery_info
        
        if driver_id:
            # 1. Assign the selected driver
            driver = get_object_or_404(DeliveryBoy, id=driver_id)
            delivery_task.delivery_boy = driver
            
            # 2. KEY CHANGE: Keep status as 'Pending'
            # This allows the driver to see the "Confirm Pickup" button.
            # If we set it to 'Shipped' here, the driver would skip the pickup step.
            delivery_task.status = 'Pending'
            
            delivery_task.save()
            messages.success(request, f"Driver {driver.user.first_name} assigned to Order #{order.id}. Waiting for pickup.")
        else:
            messages.error(request, "Please select a valid driver.")
            
    return redirect('admin_orders')

@user_passes_test(is_superuser, login_url='login')
def admin_users(request):
    customers = CustomUser.objects.filter(is_superuser=False, deliveryboy__isnull=True)
    drivers = DeliveryBoy.objects.select_related('user').all()
    
    context = {
        'customers': customers,
        'drivers': drivers
    }
    return render(request, 'admin_users.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_rentals(request):
    # 1. Fetch active rentals
    active_rentals = RentBooking.objects.filter(
        status__in=['Active', 'Overdue', 'Out for Delivery']
    ).select_related('user', 'variant__product').order_by('-start_date')

    context = {
        'rentals': active_rentals, # Matches {% for rental in rentals %} in HTML
    }
    return render(request, 'admin_rentals.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def process_return(request, rental_id):
    if request.method == 'POST':
        booking = get_object_or_404(RentBooking, id=rental_id)
        
        # Security check
        if booking.status == 'Returned':
            return redirect('rental_manager')

        # 1. Calculate Fees (Optional)
        # fee = booking.calculate_pending_late_fee
        
        # 2. Update Status
        booking.status = 'Returned'
        booking.returned_at = timezone.now()
        booking.save()
        
        variant = booking.variant
        # FIX: Use 'stock_quantity' instead of 'stock'
        variant.stock_quantity += 1
        variant.save() 
        
        messages.success(request, "Item returned and stock updated.")
            
    return redirect('rental_manager')

@login_required(login_url='login')
def user_profile(request):
    # 1. Fetch Active Rentals (Need attention)
    active_statuses = [
        RentBooking.STATUS_PENDING,
        RentBooking.STATUS_APPROVED, 
        RentBooking.STATUS_SHIPPED,
        RentBooking.STATUS_ACTIVE,
        RentBooking.STATUS_OVERDUE
    ]
    
    my_active_rentals = RentBooking.objects.filter(
        user=request.user, 
        status__in=active_statuses
    ).order_by('end_date')

    # 2. Fetch Order History (Completed stuff)
    my_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'active_rentals': my_active_rentals,
        'orders': my_orders
    }
    return render(request, 'profile.html', context)

@receiver(post_save, sender=Delivery)
def send_delivery_status_email(sender, instance, created, **kwargs):
    order = instance.order
    user = order.user
    status = instance.status
    
    # Only proceed if we have an email address
    if not user.email:
        return

    subject = f"Order #{order.id} Update: {status}"
    
    # A. HANDLE 'DELIVERED' - SEND INVOICE
    if status == 'Delivered':
        subject = f"Receipt for Order #{order.id} - Delivered"
        
        # 1. Render the HTML Invoice
        html_message = render_to_string('invoice.html', {'order': order})
        
        # 2. Create a plain text version for old email clients
        plain_message = strip_tags(html_message)
        
        # 3. Send HTML Email
        send_mail(
            subject=subject,
            message=plain_message, # Fallback text
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message, # <--- The fancy HTML invoice
            fail_silently=False
        )
        print(f"✅ INVOICE SENT to {user.email}")

    # B. HANDLE OTHER STATUSES (Simple Text Alerts)
    else:
        message = ""
        if status == 'Out for Delivery':
            message = f"Hi {user.first_name},\n\nGood news! Your order #{order.id} is out for delivery today. Please be available."
        elif status == 'Failed':
            message = f"Hi {user.first_name},\n\nWe attempted to deliver Order #{order.id} but failed. We will try again."

        if message:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            print(f"📧 STATUS UPDATE SENT: {status}")


# 2. NOTIFY ON RENTAL STATUS (No changes needed here, keeping it for completeness)
@receiver(post_save, sender=RentBooking)
def send_rental_status_email(sender, instance, created, **kwargs):
    user = instance.user
    product_name = instance.variant.product.name
    status = instance.status

    if not user.email: return

    subject = f"Rental Update: {product_name}"
    message = ""

    if status == 'Shipped':
        message = f"Hi {user.first_name},\n\nYour rental '{product_name}' has been shipped!"
    elif status == 'Overdue':
        message = f"URGENT: Your rental '{product_name}' is OVERDUE. Please return it immediately."

    if message:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        