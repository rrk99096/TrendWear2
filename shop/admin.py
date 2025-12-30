from django.contrib import admin
# Consolidate all imports into one clean line
from .models import (
    CustomUser, 
    Product, 
    ProductVariant, 
    ProductImage, 
    Cart, 
    SaleOrder, 
    RentBooking
)
from .models import DeliveryBoy, Delivery, Order

# 1. Product Setup (Inlines allow editing Variants/Images inside the Product page)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    # Fields to edit directly in the Product page
    fields = ['size', 'color', 'stock_quantity', 'sale_price', 'rent_price_per_day']

class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, ProductVariantInline]
    list_display = ['name', 'category', 'sub_category', 'is_for_sale', 'is_for_rent']
    list_filter = ['category', 'sub_category']
    search_fields = ['name']

# 2. Order Setup (Optional: Customize how Orders look)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'variant', 'quantity', 'total_price', 'status', 'order_date']
    list_filter = ['status', 'order_date']
    list_editable = ['status'] 
    search_fields = ['id', 'user__email']

class RentBookingAdmin(admin.ModelAdmin):
    # Columns to show in the list
    list_display = ['id', 'user', 'variant', 'formatted_dates', 'status', 'total_price']
    list_filter = ['status', 'start_date']
    list_editable = ['status']
    search_fields = ['id', 'user__email']

    def formatted_dates(self, obj):
        return f"{obj.start_date} -> {obj.end_date}"
    formatted_dates.short_description = "Rental Period"

# 3. Register Models
admin.site.register(CustomUser)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart)

# Register the new Split Order models
admin.site.register(SaleOrder, SaleOrderAdmin)
admin.site.register(RentBooking, RentBookingAdmin)

@admin.register(DeliveryBoy)
class DeliveryBoyAdmin(admin.ModelAdmin):
    # We replace 'phone' with a custom function 'get_phone'
    list_display = ('get_name', 'vehicle_number', 'vehicle_type', 'get_phone')

    # 1. Fetch Name from the User table
    def get_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_name.short_description = 'Driver Name'

    # 2. Fetch Phone from the DeliveryProfile table
    def get_phone(self, obj):
        # We try to access the profile safely
        if hasattr(obj.user, 'delivery_profile'):
            return obj.user.delivery_profile.phone
        return "No Phone"
    get_phone.short_description = 'Phone Number'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):        # <--- FIXED: Removed '.site'
    list_display = ('id', 'user', 'total_price', 'created_at')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):     # <--- FIXED: Removed '.site'
    list_display = ('order', 'delivery_boy', 'status', 'assigned_at')
    list_filter = ('status',)