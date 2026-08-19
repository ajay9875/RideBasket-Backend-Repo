from django.urls import path
from . import views

urlpatterns = [
    # Health Check Route -> http://127.0.0.1:8000/api/health/
    path('health/', views.check_health, name='check_health'),

    # ✅ AUTH ENDPOINTS
    # Authentication, OTP & Password Reset
    path('auth/send-login-otp/', views.send_login_otp_view, name='send_login_otp'),
    path('auth/send-register-otp/', views.send_register_otp_view, name='send_register_otp'),
    path('auth/register/', views.register_driver_view, name='register_driver'),

    # Login OTP Verify
    #path('auth/verify-login-otp/', views.verify_login_otp_view, name='verify_login_otp'),
    
    # Registration OTP Verify
    #path('auth/verify-register-otp/', views.verify_register_otp_view, name='verify_register_otp'),

    path('auth/verify-otp/', views.verify_auth_otp_view, name='verify_register_otp'),

    # Driver Endpoints
    path('driver/<str:driver_id>/profile/', views.update_driver_profile_view, name='update_driver_profile'),

    path('driver/<int:driver_id>/documents/', views.driver_documents_view, name='driver-documents'),
    path('driver/<int:driver_id>/active-ride/', views.active_ride_view, name='active-ride'),
    path('driver/<int:driver_id>/payout/', views.instant_payout_view, name='instant-payout'),
    
    # Ride Endpoints
    path('ride/<str:ride_id>/accept/', views.accept_ride_view, name='accept-ride'),
    path('ride/<str:ride_id>/complete/', views.complete_ride_view, name='complete-ride'),
    path('ride/<str:ride_id>/chat/', views.ride_chat_view, name='ride-chat'),

]