from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

# ==========================================
# 1. CUSTOM USER
# ==========================================
class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    role = models.CharField(max_length=20, default='customer')
    
    def __str__(self):
        return self.email

# ==========================================
# 2. PRODUCT MODELS
# ==========================================
class Product(models.Model):
    CATEGORY_CHOICES = (
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Kids', 'Kids'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True) 
    thumbnail = models.ImageField(upload_to='product_thumbnails/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Men')
    sub_category = models.CharField(max_length=50, blank=True, null=True) 
    is_rentable = models.BooleanField(default=False, verbose_name="Available for Rent")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_for_sale(self):
        return self.variants.filter(sale_price__gt=0).exists()

    @property
    def is_for_rent(self):
        return self.is_rentable and self.variants.filter(rent_price_per_day__gt=0).exists()

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=20, default='Standard')
    stock_quantity = models.PositiveIntegerField(default=0)
    
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rent_price_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.color} - {self.size}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/')
    
    def __str__(self):
        return f"Image for {self.product.name}"

# ==========================================
# 3. CART SYSTEM
# ==========================================
class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.email}"

    def total_price(self):
        return sum(item.total_cost() for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    
    quantity = models.PositiveIntegerField(default=1)
    
    is_rental = models.BooleanField(default=False)
    rental_start_date = models.DateField(null=True, blank=True)
    rental_end_date = models.DateField(null=True, blank=True)
    
    price_at_add = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def total_cost(self):
        if self.is_rental and self.rental_start_date and self.rental_end_date:
            delta = self.rental_end_date - self.rental_start_date
            days = delta.days if delta.days > 0 else 1
            return self.price_at_add * days * self.quantity
        else:
            return self.price_at_add * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# ==========================================
# 4. ORDER MODELS (SALES & RENTALS)
# ==========================================

class SaleOrder(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_SHIPPED = 'Shipped'
    STATUS_DELIVERED = 'Delivered'
    STATUS_RETURNED = 'Returned'
    STATUS_CANCELLED = 'Cancelled'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_RETURNED, 'Returned'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    # Link to the Parent Order (The "Package")
    parent_order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='sale_items', 
        null=True, 
        blank=True
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, **kwargs):
        # 1. NEW SALE: Deduct Stock
        if not self.pk: 
            self.variant.stock_quantity -= self.quantity
            self.variant.save()
        
        # 2. STATUS CHANGE: Handle Returns/Cancellations
        else:
            if self.status in [self.STATUS_RETURNED, self.STATUS_CANCELLED]:
                if self.__original_status not in [self.STATUS_RETURNED, self.STATUS_CANCELLED]:
                    self.variant.stock_quantity += self.quantity
                    self.variant.save()

        super().save(*args, **kwargs)
        self.__original_status = self.status

    def __str__(self):
        return f"Sale #{self.id} - {self.status}"


class RentBooking(models.Model):
    STATUS_PENDING = 'Pending'
    STATUS_APPROVED = 'Approved'
    STATUS_SHIPPED = 'Shipped'
    STATUS_ACTIVE = 'Active'      
    STATUS_RETURNED = 'Returned'   
    STATUS_OVERDUE = 'Overdue'
    STATUS_CANCELLED = 'Cancelled' 

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_SHIPPED, 'Shipped / On Way'),
        (STATUS_ACTIVE, 'Active / With Customer'),
        (STATUS_RETURNED, 'Returned'),
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    # --- FIELDS ---
    parent_order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='rent_items', 
        null=True, 
        blank=True
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE)
    
    start_date = models.DateField()
    end_date = models.DateField()
    
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    order_date = models.DateTimeField(auto_now_add=True)

    # Smart Return Fields (New)
    returned_at = models.DateTimeField(null=True, blank=True)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # --- LOGIC ---

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original status to detect changes
        self.__original_status = self.status

    @property
    def calculate_pending_late_fee(self):
        """Calculates late fee if today > end_date and item not returned yet."""
        if self.status == self.STATUS_RETURNED:
            return self.late_fee
            
        today = timezone.now().date()
        if today > self.end_date:
            overdue_days = (today - self.end_date).days
            # Late fee = Days Late * Daily Rent Price
            daily_rent = self.variant.rent_price_per_day if self.variant.rent_price_per_day else 0
            return overdue_days * daily_rent
        return 0.00

    def save(self, *args, **kwargs):
        # 1. NEW RENTAL: Deduct Stock directly
        if not self.pk:
            # Atomic update to prevent race conditions
            ProductVariant.objects.filter(id=self.variant.id).update(
                stock_quantity=F('stock_quantity') - self.quantity
            )
        
        # 2. EXISTING RENTAL: Check for Return/Cancel to Restock
        else:
            # If status changed to Returned or Cancelled...
            if self.status in [self.STATUS_RETURNED, self.STATUS_CANCELLED]:
                # ...and it wasn't ALREADY Returned or Cancelled
                if self.__original_status not in [self.STATUS_RETURNED, self.STATUS_CANCELLED]:
                    ProductVariant.objects.filter(id=self.variant.id).update(
                        stock_quantity=F('stock_quantity') + self.quantity
                    )
                    
                    # If returned, set the timestamp automatically if not set
                    if self.status == self.STATUS_RETURNED and not self.returned_at:
                        self.returned_at = timezone.now()

        super().save(*args, **kwargs)
        self.__original_status = self.status

    def __str__(self):
        return f"Rent #{self.id} - {self.status}"
# ==========================================
# 5. DELIVERY SYSTEM
# ==========================================

class DeliveryBoy(models.Model):
    # Change related_name to 'deliveryboy'
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='deliveryboy')
    
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=20)
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monthly Salary")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.first_name

class Order(models.Model):
    """
    Parent Order Model: Groups multiple SaleOrders or RentBookings into a single transaction.
    This is required for the Delivery system to track one 'Package' instead of individual items.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: You can link this to SaleOrders using a ForeignKey in SaleOrder later if needed
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.email}"

class Delivery(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Failed', 'Failed'),
    )

    # Links to the parent 'Order' model
    order = models.OneToOneField(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='delivery_info'
    )
    
    delivery_boy = models.ForeignKey(
        DeliveryBoy, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='deliveries'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    admin_note = models.TextField(blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.id}"
    
class DeliveryProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"

# SIGNAL: Automatically create a profile when a User is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        DeliveryProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    instance.delivery_profile.save()