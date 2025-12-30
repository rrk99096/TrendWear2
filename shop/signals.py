from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string # Required for HTML Invoice
from django.utils.html import strip_tags            # Required for Email Fallback
from django.conf import settings
from .models import Delivery, RentBooking

# 1. NOTIFY CUSTOMER ON DELIVERY STATUS CHANGE
@receiver(post_save, sender=Delivery)
def send_delivery_status_email(sender, instance, created, **kwargs):
    order = instance.order
    user = order.user
    status = instance.status
    
    # Safety check: Do not crash if user has no email
    if not user.email:
        return
    
    subject = f"Order #{order.id} Update: {status}"

    # --- SCENARIO A: OUT FOR DELIVERY (SEND OTP) ---
    if status == 'Out for Delivery':
        # Retrieve the OTP stored in the model
        otp_code = instance.otp
        
        message = (
            f"Hi {user.first_name},\n\n"
            f"Good news! Your order #{order.id} is out for delivery today.\n\n"
            f"🔐 YOUR SECURE DELIVERY OTP: {otp_code}\n\n"
            f"Please share this code with the delivery agent to receive your package."
        )
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        print(f"📧 OTP EMAIL SENT to {user.email}: {otp_code}")

    # --- SCENARIO B: DELIVERED (SEND HTML INVOICE) ---
    elif status == 'Delivered':
        subject = f"Receipt for Order #{order.id} - Delivered"
        
        try:
            # 1. Render the HTML Invoice Template
            html_message = render_to_string('emails/invoice.html', {'order': order})
            
            # 2. Create plain text version for older email clients
            plain_message = strip_tags(html_message)
            
            # 3. Send the HTML Email
            send_mail(
                subject=subject,
                message=plain_message, # Fallback text
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message, # The fancy invoice
                fail_silently=False
            )
            print(f"✅ INVOICE SENT to {user.email}")
        except Exception as e:
            print(f"❌ ERROR sending invoice: {e}")

    # --- SCENARIO C: FAILED / OTHER (SIMPLE TEXT) ---
    elif status == 'Failed':
        message = f"Hi {user.first_name},\n\nWe attempted to deliver your order #{order.id} but failed. Our delivery agent will try again soon."
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        print(f"📧 STATUS UPDATE SENT: {status}")


# 2. NOTIFY CUSTOMER ON RENTAL STATUS (e.g. Overdue)
@receiver(post_save, sender=RentBooking)
def send_rental_status_email(sender, instance, created, **kwargs):
    user = instance.user
    product_name = instance.variant.product.name
    status = instance.status

    # Safety check
    if not user.email:
        return

    subject = f"Rental Update: {product_name}"
    message = ""

    if status == 'Shipped':
        message = f"Hi {user.first_name},\n\nYour rental item '{product_name}' has been shipped! It should arrive soon."
        
    elif status == 'Overdue':
        message = f"URGENT: Hi {user.first_name},\n\nYour rental for '{product_name}' is now OVERDUE. Please return it immediately to avoid further late fees."

    # Send Email
    if message:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        print(f"📧 RENTAL EMAIL SENT to {user.email}: {status}")