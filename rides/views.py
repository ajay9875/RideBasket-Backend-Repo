from django.contrib.sites import requests
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404

from rides.models import (
    Driver, VehicleDocument, Ride,
    EarningsTransaction, AppNotification, ChatMessage
)
from rides.serializers import (
    DriverSerializer, VehicleDocumentSerializer, RideSerializer,
    EarningsTransactionSerializer, AppNotificationSerializer, ChatMessageSerializer
)
import logging
import datetime
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import random
from django.utils import timezone
from datetime import timedelta
from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Driver
from .serializers import DriverSerializer

import random
import requests
from django.utils import timezone
from datetime import timedelta
from django.db import models
from decouple import config
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Driver
from .serializers import DriverSerializer

import random
import logging
import requests
from django.utils import timezone
from datetime import timedelta
from django.db import models
from decouple import config
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Driver
from .serializers import DriverSerializer


# Setup logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
def check_health(request):
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        db_engine = connection.settings_dict['ENGINE'].split('.')[-1]
        
        return Response({
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "database": {
                "connected": True,
                "engine": db_engine,
                "host": connection.settings_dict.get('HOST', 'localhost'),
                "name": connection.settings_dict.get('NAME')
            }
        }, status=status.HTTP_200_OK)

    except OperationalError as e:
        return Response({
            "status": "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

# 1. Define the home_view function first
def home_view(request):
    return HttpResponse("Welcome to the Ridebasket Backend API!")

@api_view(['POST'])
def send_register_otp_view(request):
    """
    Send OTP for registration.
    Creates a temporary driver with name and phone only.
    Email and vehicle details will be added during final registration.
    """
    try:
        # ----- 1. VALIDATE INPUT -----
        phone = request.data.get('phone')
        name = request.data.get('name', '').strip()
        
        if not phone:
            logger.warning("Send OTP failed: Phone number missing")
            return Response({
                'success': False,
                'message': 'Phone number is required.',
                'code': 'PHONE_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not name:
            logger.warning("Send OTP failed: Name missing")
            return Response({
                'success': False,
                'message': 'Full name is required.',
                'code': 'NAME_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clean phone number
        phone_number = str(phone).strip().replace("+", "")
        
        # Validate phone number format (10-15 digits)
        if not phone_number.isdigit() or len(phone_number) < 10 or len(phone_number) > 15:
            logger.warning(f"Send OTP failed: Invalid phone format - {phone_number}")
            return Response({
                'success': False,
                'message': 'Invalid phone number format. Please enter a valid phone number.',
                'code': 'INVALID_PHONE_FORMAT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📤 Registration OTP request for: {phone_number} - Name: {name}")
        
        # ----- 2. CLEANUP ORPHANED TEMP DRIVERS (OLDER THAN 24 HOURS) -----
        try:
            orphaned_drivers = Driver.objects.filter(
                email__isnull=True,  # No email set (temp driver)
                otp_created_at__lt=timezone.now() - timedelta(hours=24)  # Older than 24 hours
            )
            orphaned_count = orphaned_drivers.count()
            if orphaned_count > 0:
                logger.info(f"🗑️ Deleting {orphaned_count} orphaned temp drivers older than 24 hours")
                orphaned_drivers.delete()
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")  # Don't fail the request
        
        # ----- 3. CHECK IF DRIVER EXISTS -----
        existing_driver = Driver.objects.filter(phone_number=phone_number).first()
        
        if existing_driver:
            # ✅ Check if it's a temp driver (no email)
            if existing_driver.email is None or existing_driver.email == '':
                logger.info(f"📱 Reusing existing temp driver: {phone_number}")
                driver = existing_driver
                driver.full_name = name  # ✅ Update name
            else:
                # ✅ Real registered driver
                logger.warning(f"Registration failed: Phone already registered - {phone_number}")
                return Response({
                    'success': False,
                    'message': 'Phone number already registered. Please login instead.',
                    'code': 'DRIVER_EXISTS',
                    'exists': True
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # ----- 4. CREATE TEMPORARY DRIVER -----
            try:
                driver = Driver.objects.create(
                    phone_number=phone_number,
                    full_name=name,
                    email=None,
                    vehicle_category=None,
                    vehicle_model=None,
                    vehicle_number=None,
                    registration_certificate=None,
                    kyc_status=Driver.KYCStatus.PENDING,
                    is_online=False,
                    wallet_balance=0.00,
                    total_earnings=0.00,
                    rating=5.00
                )
                logger.info(f"✅ New temp driver created: {phone_number} - {name}")
                    
            except Exception as db_error:
                logger.error(f"Database error while creating driver: {str(db_error)}")
                return Response({
                    'success': False,
                    'message': 'Unable to process your request. Please try again.',
                    'code': 'DATABASE_ERROR'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ----- 5. GENERATE AND SAVE OTP -----
        try:
            otp_code = str(random.randint(1000, 9999))
            logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
            
            driver.otp_code = otp_code
            driver.otp_created_at = timezone.now()
            driver.save()
            
            logger.info(f"✅ OTP saved for: {phone_number}")

        #-----------------  Temperary Bypass   --------------------
            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': otp_code,
                'code': 'OTP_SENT',
            }, status=status.HTTP_200_OK)
        #----------------------------------------------------------
                
        except Exception as db_error:
            logger.error(f"Database error while saving OTP: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ----- 6. SEND SMS (BYPASSED FOR NOW) -----
        api_key = config('SMS_API_TOKEN', default='')
        api_url = config('SMS_API_URL', default='')

        if not api_key or not api_url:
            logger.warning(f"⚠️ SMS gateway not configured. Debug OTP: {otp_code}")
            return Response({
                'success': True,
                'message': 'OTP generated successfully. (Debug Mode - SMS not sent)',
                'debug_otp': otp_code,
                'is_debug': True
            }, status=status.HTTP_200_OK)

        try:
            sms_subject = "RIDEBASKET"
            message_body = f"Your [{sms_subject}] verification code is {otp_code}. Valid for 5 minutes. Do not share with anyone."
            
            payload = {
                "authkey": api_key,
                "mobile": phone_number,
                "otp": otp_code,
                "message": message_body
            }
            
            sms_response = requests.post(api_url, data=payload, timeout=10)
            
            if sms_response.status_code == 200:
                logger.info(f"✅ SMS sent successfully to {phone_number}")
            else:
                logger.warning(f"⚠️ SMS API returned status: {sms_response.status_code}")
                
            try:
                res_data = sms_response.json()
            except ValueError:
                res_data = {"raw_text": sms_response.text}

            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': otp_code,
                'gateway_response': res_data
            }, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ SMS gateway timeout for {phone_number}")
            return Response({
                'success': False,
                'message': 'OTP request timed out. Please try again.',
                'code': 'TIMEOUT_ERROR'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            
        except requests.exceptions.RequestException as req_error:
            logger.error(f"📡 SMS gateway error: {str(req_error)}")
            return Response({
                'success': False,
                'message': 'Unable to send OTP at the moment. Please try again later.',
                'code': 'SMS_GATEWAY_ERROR'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_register_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# ✅ REGISTER DRIVER - Complete Registration
# ============================================
@api_view(['POST'])
def register_driver_view(request):
    try:
        raw_phone = request.data.get('phone_number') or request.data.get('phone')
        if not raw_phone:
            return Response({
                'success': False, 
                'message': 'Phone number is required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = str(raw_phone).strip().replace("+", "")
        email = request.data.get('email', '').strip()
        full_name = request.data.get('full_name', '').strip()
        
        if not full_name:
            return Response({
                'success': False,
                'message': 'Full name is required.',
                'code': 'NAME_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ Check if driver already exists by phone or email
        existing_driver = Driver.objects.filter(
            models.Q(phone_number=phone_number) | models.Q(email=email)
        ).first()
        
        if existing_driver:
            # ✅ If it's a temp driver (no email), update it instead of returning error
            if existing_driver.phone_number == phone_number and (existing_driver.email is None or existing_driver.email == ''):
                # ✅ Update temp driver with all details
                logger.info(f"📝 Updating temp driver: {phone_number}")
                existing_driver.full_name = full_name
                existing_driver.email = email
                existing_driver.vehicle_category = request.data.get('vehicle_type', 'SEDAN')
                existing_driver.vehicle_model = request.data.get('vehicle_model', '')
                existing_driver.vehicle_number = request.data.get('plate_number', '')
                existing_driver.registration_certificate = request.data.get('registration_certificate', '')
                existing_driver.kyc_status = Driver.KYCStatus.PENDING
                existing_driver.save()
                
                serializer = DriverSerializer(existing_driver)
                return Response({
                    'success': True,
                    'message': 'Registration successful. Please login.',
                    'driver': serializer.data
                }, status=status.HTTP_200_OK)
            
            # ✅ Check if email conflict (email belongs to another driver)
            if email and existing_driver.email == email and existing_driver.phone_number != phone_number:
                return Response({
                    'success': False,
                    'message': 'Email already registered.',
                    'code': 'EMAIL_EXISTS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Real existing driver - return error
            error_messages = []
            if existing_driver.phone_number == phone_number:
                error_messages.append("Phone number already registered")
            if email and existing_driver.email == email:
                error_messages.append("Email already registered")

            if len(error_messages) == 1:
                error = error_messages[0]
            else:
                error = "Email and phone number already registered"
            
            return Response({
                'success': False,
                'message': error,
                'exists': True
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ Create new driver (if no temp driver exists)
        driver = Driver.objects.create(
            phone_number=phone_number,
            full_name=full_name,
            email=email,
            vehicle_category=request.data.get('vehicle_type', 'SEDAN'),
            vehicle_model=request.data.get('vehicle_model', ''),
            vehicle_number=request.data.get('plate_number', ''),
            registration_certificate=request.data.get('registration_certificate', ''),
            kyc_status=Driver.KYCStatus.PENDING,
            is_online=False,
            wallet_balance=0.00,
            total_earnings=0.00,
            rating=5.00
        )

        serializer = DriverSerializer(driver)
        return Response({
            'success': True,
            'message': 'Registration successful. Please login.',
            'driver': serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'success': False,
            'message': f"An unexpected error occurred during registration: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# ============================================
# ✅ SEND OTP - Login (NO AUTO-CREATION)
# ============================================
@api_view(['POST'])
def send_login_otp_view(request):
    """
    Send OTP to the provided phone number for login.
    ONLY allows existing users. Does NOT create new users.
    """
    try:
        # ----- 1. VALIDATE INPUT -----
        phone = request.data.get('phone')
        if not phone:
            logger.warning("Send OTP failed: Phone number missing")
            return Response({
                'success': False,
                'message': 'Phone number is required.',
                'code': 'PHONE_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clean phone number
        phone_number = str(phone).strip().replace("+", "")
        
        # Validate phone number format (10-15 digits)
        if not phone_number.isdigit() or len(phone_number) < 10 or len(phone_number) > 15:
            logger.warning(f"Send OTP failed: Invalid phone format - {phone_number}")
            return Response({
                'success': False,
                'message': 'Invalid phone number format. Please enter a valid phone number.',
                'code': 'INVALID_PHONE_FORMAT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"📤 Login OTP request for: {phone_number}")
        
        # ----- 2. CHECK IF DRIVER EXISTS -----
        try:
            driver = Driver.objects.filter(phone_number=phone_number).first()
            
            if not driver:
                logger.warning(f"Login failed: Driver not found - {phone_number}")
                return Response({
                    'success': False,
                    'message': 'Account not found. Please register first.',
                    'code': 'DRIVER_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as db_error:
            logger.error(f"Database error while checking driver: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ----- 3. GENERATE OTP -----
        otp_code = 1234  # Temporary OTP for testing
        # otp_code = str(random.randint(1000, 9999))
        logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
        
        # ----- 4. SAVE OTP TO DATABASE -----
        try:
            driver.otp_code = otp_code
            driver.otp_created_at = timezone.now()
            driver.save()
            logger.info(f"✅ OTP updated for existing driver: {phone_number}")


        #-----------------  Temperary Bypass   --------------------
            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': otp_code,
                'code': 'OTP_SENT',
            }, status=status.HTTP_200_OK)
        #----------------------------------------------------------

                
        except Exception as db_error:
            logger.error(f"Database error while saving OTP: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ----- 5. SEND SMS (BYPASSED FOR NOW) -----
        api_key = config('SMS_API_TOKEN', default='')
        api_url = config('SMS_API_URL', default='')

        # Send SMS
        try:
            sms_subject = "RIDEBASKET"
            message_body = f"Your [{sms_subject}] verification code is {otp_code}. Valid for 5 minutes. Do not share with anyone."
            
            payload = {
                "authkey": api_key,
                "mobile": phone_number,
                "otp": otp_code,
                "message": message_body
            }
            
            sms_response = requests.post(api_url, data=payload, timeout=10)
            
            if sms_response.status_code == 200:
                logger.info(f"✅ SMS sent successfully to {phone_number}")
            else:
                logger.warning(f"⚠️ SMS API returned status: {sms_response.status_code}")
                
            try:
                res_data = sms_response.json()
            except ValueError:
                res_data = {"raw_text": sms_response.text}

            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': otp_code,
                'gateway_response': res_data
            }, status=status.HTTP_200_OK)
            
        except requests.exceptions.Timeout:
            logger.error(f"⏰ SMS gateway timeout for {phone_number}")
            return Response({
                'success': False,
                'message': 'OTP request timed out. Please try again.',
                'code': 'TIMEOUT_ERROR'
            }, status=status.HTTP_504_GATEWAY_TIMEOUT)
            
        except requests.exceptions.RequestException as req_error:
            logger.error(f"📡 SMS gateway error: {str(req_error)}")
            return Response({
                'success': False,
                'message': 'Unable to send OTP at the moment. Please try again later.',
                'code': 'SMS_GATEWAY_ERROR'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_auth_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# ✅ VERIFY OTP - With Flow Support (Login/Registration)
# ============================================
@api_view(['POST'])
def verify_auth_otp_view(request):
    """
    Verify OTP for both Login and Registration flows.
    
    For Login: 
        - Verifies OTP for existing drivers only
        - Returns driver data for login session
    
    For Registration:
        - Verifies OTP for temp drivers only
        - Returns driver data to proceed with registration
    """
    # ----- 1. GET AND VALIDATE INPUT -----
    phone = request.data.get('phone')
    otp = request.data.get('otp')
    flow = request.data.get('flow', 'Login')  # ✅ Get flow type (login/registration)
    
    if not phone or not otp:
        return Response({
            'success': False,
            'message': 'Phone and OTP are required',
            'code': 'MISSING_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Clean phone number
    phone = str(phone).strip().replace("+", "")
    otp = str(otp).strip()
    
    # Validate OTP format (4-6 digits)
    if not otp.isdigit() or len(otp) < 4 or len(otp) > 6:
        return Response({
            'success': False,
            'message': 'Invalid OTP format. Please enter a valid OTP.',
            'code': 'INVALID_OTP_FORMAT'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"🔍 Verifying OTP for: {phone} (Flow: {flow})")
    
    # ----- 2. FIND DRIVER -----
    driver = Driver.objects.filter(phone_number=phone).first()
    if not driver:
        logger.warning(f"Verify OTP failed: Driver not found - {phone}")
        return Response({
            'success': False,
            'message': 'Driver not found. Please register first.',
            'code': 'DRIVER_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # ----- 3. FLOW-SPECIFIC CHECKS -----
    
    # ✅ For LOGIN flow: Driver must be a real registered driver (email exists)
    if flow == 'Login':
        if driver.email is None or driver.email == '':
            logger.warning(f"Login failed: Registration incomplete for {phone}")
            return Response({
                'success': False,
                'message': 'Please complete your registration first.',
                'code': 'REGISTRATION_INCOMPLETE'
            }, status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"📱 Login OTP verification for: {phone}")
    
    # ✅ For REGISTRATION flow: Driver must be a temp driver (email is None)
    elif flow == 'Registration':
        if driver.email is not None and driver.email != '':
            logger.warning(f"Registration failed: Phone already registered - {phone}")
            return Response({
                'success': False,
                'message': 'Phone number already registered. Please login instead.',
                'code': 'ALREADY_REGISTERED'
            }, status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"📝 Registration OTP verification for: {phone}")

    else:
        logger.warning(f"Verify OTP failed: Invalid flow type - {flow}")
        return Response({
            'success': False,
            'message': 'Invalid flow type. Must be either "Login" or "Registration".',
            'code': 'INVALID_FLOW'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 4. CHECK OTP -----
    if not driver.otp_code:
        logger.warning(f"Verify OTP failed: No OTP requested for {phone}")
        return Response({
            'success': False,
            'message': 'No OTP requested. Please request OTP first.',
            'code': 'NO_OTP_REQUESTED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if str(driver.otp_code) != str(otp):
        logger.warning(f"Verify OTP failed: Invalid OTP for {phone}")
        return Response({
            'success': False,
            'message': 'Invalid OTP. Please try again.',
            'code': 'INVALID_OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 5. CHECK OTP EXPIRY (5 minutes) -----
    if driver.otp_created_at:
        expiry_time = driver.otp_created_at + timedelta(minutes=5)
        if timezone.now() > expiry_time:
            logger.warning(f"Verify OTP failed: OTP expired for {phone}")
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new OTP.',
                'code': 'OTP_EXPIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 6. CLEAR OTP AND SAVE -----
    driver.otp_code = None
    driver.otp_created_at = None
    driver.save()
    
    logger.info(f"✅ OTP verified successfully for {phone} (Flow: {flow})")
    
    # ----- 7. RETURN RESPONSE -----
    return Response({
        'success': True,
        'message': 'OTP verified successfully',
        'flow': flow,  # ✅ Return flow for client reference
        'driver': DriverSerializer(driver).data
    }, status=status.HTTP_200_OK)

"""@api_view(['POST'])
def verify_auth_otp_view(request):
    phone_number = request.data.get('phone_number')
    otp_input = request.data.get('otp')

    if not phone_number or not otp_input:
        return Response({'success': False, 'error': 'Phone number and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = Driver.objects.filter(phone_number=phone_number).first()
    if not driver:
        return Response({'success': False, 'error': 'Driver not found.'}, status=status.HTTP_404_NOT_FOUND)

    if otp_input == getattr(driver, 'otp_code', None) or otp_input == '1234':
        serializer = DriverSerializer(driver)
        return Response({
            'success': True,
            'message': 'OTP verified successfully.',
            'driver': serializer.data
        }, status=status.HTTP_200_OK)

    return Response({'success': False, 'error': 'Invalid OTP code.'}, status=status.HTTP_400_BAD_REQUEST)"""

@api_view(['PUT', 'PATCH'])
def update_driver_profile_view(request, driver_id):
    """
    Update driver profile - full_name, bio, profile_photo
    """
    try:
        driver = Driver.objects.get(id=driver_id)
    except Driver.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Driver not found.',
            'code': 'DRIVER_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get data from request
    full_name = request.data.get('full_name')
    bio = request.data.get('bio')
    profile_photo_url = request.data.get('profile_photo_url')
    
    # Update fields if provided
    if full_name:
        driver.full_name = full_name
    if bio is not None:
        driver.bio = bio
    if profile_photo_url:
        driver.profile_photo_url = profile_photo_url
    
    driver.save()
    
    return Response({
        'success': True,
        'message': 'Profile updated successfully.',
        'driver': DriverSerializer(driver).data
    }, status=status.HTTP_200_OK)
    
@api_view(['GET'])
def driver_documents_view(request, driver_id):
    docs = VehicleDocument.objects.filter(driver_id=driver_id)
    serializer = VehicleDocumentSerializer(docs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def active_ride_view(request, driver_id):
    ride = RideRequest.objects.filter(
        driver_id=driver_id,
        status__in=['ACCEPTED', 'ARRIVED', 'IN_PROGRESS']
    ).first()
    if ride:
        return Response(RideRequestSerializer(ride).data)
    return Response(None, status=status.HTTP_200_OK)

@api_view(['POST'])
def accept_ride_view(request, ride_id):
    ride = get_object_or_404(RideRequest, ride_id=ride_id)
    ride.status = 'ACCEPTED'
    ride.save()
    return Response(RideRequestSerializer(ride).data)

@api_view(['POST'])
def complete_ride_view(request, ride_id):
    ride = get_object_or_404(RideRequest, ride_id=ride_id)
    ride.status = 'COMPLETED'
    ride.save()

    # Credit driver wallet
    profile = ride.driver
    if profile:
        profile.wallet_balance += ride.fare_amount
        profile.save()

        # Record transaction
        EarningsTransaction.objects.create(
            driver=profile,
            transaction_id=f"TXN-{ride.ride_id}",
            title=f"Ride Fare - {ride.passenger_name}",
            amount=ride.fare_amount,
            transaction_type='CREDIT'
        )

    return Response({'success': True, 'ride': RideRequestSerializer(ride).data})

@api_view(['POST'])
def instant_payout_view(request, driver_id):
    profile = get_object_or_404(DriverProfile, id=driver_id)
    amount = float(request.data.get('amount', 0))

    if amount <= 0 or profile.wallet_balance < amount:
        return Response({'error': 'Insufficient balance or invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

    profile.wallet_balance -= amount
    profile.save()

    EarningsTransaction.objects.create(
        driver=profile,
        transaction_id=f"POUT-{profile.id}-{int(amount)}",
        title="Instant Bank Payout",
        amount=amount,
        transaction_type='PAYOUT'
    )
    return Response({'success': True, 'new_balance': profile.wallet_balance})

@api_view(['GET', 'POST'])
def ride_chat_view(request, ride_id):
    if request.method == 'GET':
        messages = ChatMessage.objects.filter(ride__ride_id=ride_id).order_by('created_at')
        return Response(ChatMessageSerializer(messages, many=True).data)
    elif request.method == 'POST':
        ride = get_object_or_404(RideRequest, ride_id=ride_id)
        msg = ChatMessage.objects.create(
            ride=ride,
            sender_type=request.data.get('sender_type', 'DRIVER'),
            message_text=request.data.get('message_text', '')
        )
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)