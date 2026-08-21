# Customer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Customer Registration Flow
    path('customer/send-register-otp/', views.send_customer_register_otp_view, name='customer_send_register_otp'),
    path('customer/register/', views.register_customer_view, name='customer_register'),
    
    # Customer Login Flow
    path('customer/send-login-otp/', views.send_customer_login_otp_view, name='customer_send_login_otp'),
    
    # Customer OTP Verification
    path('customer/verify-otp/', views.verify_customer_auth_otp_view, name='customer_verify_otp'),
]