from django.urls import path
from . import views

urlpatterns = [
    # Health Check Route -> http://127.0.0.1:8000/api/health/
    path('health/', views.check_health, name='check_health'),

    # Driver Endpoints
    path('driver/<int:driver_id>/', views.driver_profile_view, name='driver-profile'),
    path('driver/<int:driver_id>/documents/', views.driver_documents_view, name='driver-documents'),
    path('driver/<int:driver_id>/active-ride/', views.active_ride_view, name='active-ride'),
    path('driver/<int:driver_id>/payout/', views.instant_payout_view, name='instant-payout'),
    
    # Ride Endpoints
    path('ride/<str:ride_id>/accept/', views.accept_ride_view, name='accept-ride'),
    path('ride/<str:ride_id>/complete/', views.complete_ride_view, name='complete-ride'),
    path('ride/<str:ride_id>/chat/', views.ride_chat_view, name='ride-chat'),

    # Authentication, OTP & Password Reset
    path('auth/send-otp/', views.send_auth_otp_view, name='send_auth_otp'),
    path('auth/verify-otp/', views.verify_auth_otp_view, name='verify_auth_otp'),
    path('auth/reset-password/', views.reset_password_view, name='reset_password'),
]