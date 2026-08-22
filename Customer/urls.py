# Customer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Customer OTP Verification
    # Registration Flow
    path('customer/send-register-otp/', views.send_customer_register_otp_view, name='customer_send_register_otp'),
    path('customer/verify-register-otp/', views.verify_customer_register_otp_view, name='customer_verify_register_otp'),  # ✅ New
    path('customer/register/', views.register_customer_view, name='customer_register'),
    
    # Login Flow
    path('customer/send-login-otp/', views.send_customer_login_otp_view, name='customer_send_login_otp'),
    path('customer/verify-login-otp/', views.verify_customer_login_otp_view, name='customer_verify_login_otp'),  #
]