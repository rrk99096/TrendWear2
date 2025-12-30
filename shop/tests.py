from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, ProductVariant
import json
from datetime import datetime

# ... existing views ...

@login_required(login_url='login') # Force login to add to cart
@require_POST
def add_to_cart(request):
    try:
        data = json.loads(request.body)
        
        # 1. Get Data from Frontend
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        action_type = data.get('action_type') # 'buy' or 'rent'
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # 2. Get or Create Cart for User
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # 3. Get Product Details
        product = get_object_or_404(Product, id=product_id)
        variant = None
        price = product.base_price # Default
        
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id)
            price = variant.price # Override with variant price
            
        # 4. Handle Rental Logic
        is_rental = (action_type == 'rent')
        
        if is_rental:
            # Simple validation
            if not start_date or not end_date:
                return JsonResponse({'status': 'error', 'message': 'Please select rental dates.'})
            # Convert string dates to objects
            # (Assuming frontend sends YYYY-MM-DD)
            # You might want to calculate rental duration price logic here later
            pass 
        
        # 5. Add to Cart Item
        # Check if item already exists in cart (same product, same size, same type)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            is_rental=is_rental,
            rental_start_date=start_date if is_rental else None,
            rental_end_date=end_date if is_rental else None,
            defaults={'price_at_add': price}
        )
        
        if not created:
            item.quantity += 1
            item.save()
            
        # Return success with new cart count
        cart_count = cart.items.count()
        return JsonResponse({'status': 'success', 'message': 'Added to bag!', 'cart_count': cart_count})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})