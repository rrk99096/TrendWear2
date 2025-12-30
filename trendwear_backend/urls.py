from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # The name='home' is crucial for the Navbar link to work
    path('', views.home, name='home'), 
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('send-otp/', views.send_otp_ajax, name='send_otp'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('dashboard/inventory/', views.inventory_list, name='inventory'),
    path('dashboard/inventory/add-product/', views.add_product, name='add_product'),
    path('dashboard/inventory/update-stock/<int:variant_id>/', views.update_stock, name='update_stock'),
    path('dashboard/inventory/add-variant/<int:product_id>/', views.add_variant, name='add_variant'), # NEW
    path('dashboard/inventory/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('dashboard/inventory/delete-variant/<int:variant_id>/', views.delete_variant, name='delete_variant'),
    path('collections/', views.collection, name='collection'),
    path('shop/<str:category_name>/', views.view_category, name='view_category'),
    path('rentals/', views.rentals, name='rentals'),
    path('delivery-dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/update/<int:delivery_id>/', views.update_task_status, name='update_task_status'),
    path('delivery/send-otp/<int:delivery_id>/', views.send_delivery_otp, name='send_delivery_otp'),
    path('delivery/complete/<int:delivery_id>/', views.complete_delivery, name='complete_delivery'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/order/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('dashboard/orders/', views.admin_orders, name='admin_orders'),
    path('dashboard/orders/assign-driver/<int:order_id>/', views.assign_driver, name='assign_driver'),
    path('dashboard/users/', views.admin_users, name='admin_users'),
    path('dashboard/rentals/', views.admin_rentals, name='admin_rentals'),
    path('dashboard/rentals/return/<int:booking_id>/', views.process_return, name='process_return'),
    path('profile/', views.user_profile, name='user_profile'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('admin-rentals/', views.admin_rentals, name='rental_manager'), # View redirects here
    path('admin-rentals/return/<int:rental_id>/', views.process_return, name='process_return'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 