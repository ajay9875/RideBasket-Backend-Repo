import random
import logging
import requests
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from decouple import config
from Driver.models import Rider  # Updated from Driver to Rider
from .serializers import RiderSerializer  # Updated from DriverSerializer to RiderSerializer
from django.db import models  # ✅ ADD THIS IMPORT
from django.db.models import Q  # ✅ OR add this if you prefer Q

logger = logging.getLogger(__name__)

# ============================================
# ✅ SEND OTP - Customer Registration
# ============================================

# ============================================
# ✅ SEND OTP - Customer Registration (COMPLETE)
# ============================================
@api_view(['POST'])
def send_customer_register_otp_view(request):
    """
    Send OTP for customer registration.
    Creates a temporary customer with name and phone only.
    Email will be added during final registration.
    """
    try:
        # ----- 1. VALIDATE INPUT -----
        phone = request.data.get('phone')
        name = request.data.get('name', '').strip()
        email = request.data.get('email', '').strip()  # ✅ Get email from request
        
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
        
        logger.info(f"📤 Customer Registration OTP request for: {phone_number} - Name: {name}")
        
        # ----- 2. CLEANUP ORPHANED TEMP CUSTOMERS (OLDER THAN 24 HOURS) -----
        try:
            orphaned_customers = Rider.objects.filter(
                email__isnull=True,
                otp_created_at__lt=timezone.now() - timedelta(hours=24)
            )
            orphaned_count = orphaned_customers.count()
            if orphaned_count > 0:
                logger.info(f"🗑️ Deleting {orphaned_count} orphaned temp customers older than 24 hours")
                orphaned_customers.delete()
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")
        
        # ----- 3. CHECK IF PHONE EXISTS WITH A REAL EMAIL -----
        # First, check if the phone exists with a real email
        existing_customer_with_phone = Rider.objects.filter(
            phone_number=phone_number
        ).exclude(
            email__isnull=True
        ).exclude(
            email=''
        ).first()
        
        # ✅ If phone exists with a real email, check if it's the same email
        if existing_customer_with_phone:
            # If email is provided in the request
            if email:
                # Check if the email matches the existing customer's email
                if existing_customer_with_phone.email == email:
                    logger.warning(f"Registration failed: Phone and email already registered - {phone_number}")
                    return Response({
                        'success': False,
                        'message': 'This phone and email are already registered. Please login.',
                        'code': 'CUSTOMER_EXISTS',
                        'exists': True
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # ✅ Phone exists but with a DIFFERENT email - Allow registration!
                    logger.info(f"📱 Phone {phone_number} exists with different email. Creating new customer.")
                    # Check if the new email already exists
                    if Rider.objects.filter(email=email).exists():
                        return Response({
                            'success': False,
                            'message': 'This email is already registered with another account.',
                            'code': 'EMAIL_EXISTS'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Create a new customer with the same phone but different email
                    customer = Rider.objects.create(
                        phone_number=phone_number,
                        full_name=name,
                        email=email,
                        wallet_balance=0.00,
                        rating=5.00,
                        status=Rider.Status.ACTIVE
                    )
                    logger.info(f"✅ New customer created with existing phone: {phone_number}")
                    # Skip OTP, go directly to OTP generation
            else:
                # No email provided, phone exists with real email
                logger.warning(f"Registration failed: Phone already registered - {phone_number}")
                return Response({
                    'success': False,
                    'message': 'Phone number already registered. Please login instead.',
                    'code': 'CUSTOMER_EXISTS',
                    'exists': True
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # ----- 4. CHECK IF PHONE EXISTS AS TEMP CUSTOMER -----
            existing_temp_customer = Rider.objects.filter(
                phone_number=phone_number,
                email__isnull=True
            ).first()
            
            if existing_temp_customer:
                logger.info(f"📱 Reusing existing temp customer: {phone_number}")
                customer = existing_temp_customer
                customer.full_name = name
                customer.save()
            else:
                # ----- 5. CREATE TEMPORARY CUSTOMER -----
                try:
                    customer = Rider.objects.create(
                        phone_number=phone_number,
                        full_name=name,
                        email=None,  # Will be set during final registration
                        wallet_balance=0.00,
                        rating=5.00,
                        status=Rider.Status.PENDING
                    )
                    logger.info(f"✅ New temp customer created: {phone_number} - {name}")
                        
                except Exception as db_error:
                    logger.error(f"Database error while creating customer: {str(db_error)}")
                    return Response({
                        'success': False,
                        'message': 'Unable to process your request. Please try again.',
                        'code': 'DATABASE_ERROR'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ----- 6. GENERATE AND SAVE OTP -----
        try:
            otp_code = "1234"
            # otp_code = str(random.randint(1000, 9999))
            logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
            
            customer.otp_code = otp_code
            customer.otp_created_at = timezone.now()
            customer.save()
            
            logger.info(f"✅ OTP saved for: {phone_number}")

            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': otp_code,
                'code': 'OTP_SENT',
            }, status=status.HTTP_200_OK)
                
        except Exception as db_error:
            logger.error(f"Database error while saving OTP: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ----- 7. SEND SMS (BYPASSED FOR NOW) -----
        # ... (SMS logic remains the same)
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_customer_register_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# ✅ VERIFY OTP - Customer (Login/Registration)
# ============================================
# views.py - Add this function
@api_view(['POST'])
def verify_customer_register_otp_view(request):
    """
    Verify OTP for Registration flow only.
    """
    phone = request.data.get('phone')
    otp = request.data.get('otp')
    
    if not phone or not otp:
        return Response({
            'success': False,
            'message': 'Phone and OTP are required',
            'code': 'MISSING_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    phone = str(phone).strip().replace("+", "")
    otp = str(otp).strip()
    
    if not otp.isdigit() or len(otp) != 4:
        return Response({
            'success': False,
            'message': 'Invalid OTP format. Please enter a 4-digit OTP.',
            'code': 'INVALID_OTP_FORMAT'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"🔍 Verifying Registration OTP for: {phone}")
    
    customer = Rider.objects.filter(phone_number=phone).first()
    
    if not customer:
        return Response({
            'success': False,
            'message': 'Customer not found. Please register first.',
            'code': 'CUSTOMER_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # ✅ Check: Must be a temp customer (email is None or starts with 'temp_')
    if customer.email is not None and customer.email != '' and not customer.email.startswith('temp_'):
        return Response({
            'success': False,
            'message': 'Phone number already registered. Please login instead.',
            'code': 'ALREADY_REGISTERED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check OTP
    if not customer.otp_code:
        return Response({
            'success': False,
            'message': 'No OTP requested. Please request OTP first.',
            'code': 'NO_OTP_REQUESTED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if str(customer.otp_code) != str(otp):
        return Response({
            'success': False,
            'message': 'Invalid OTP. Please try again.',
            'code': 'INVALID_OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check OTP expiry (5 minutes)
    if customer.otp_created_at:
        expiry_time = customer.otp_created_at + timedelta(minutes=5)
        if timezone.now() > expiry_time:
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new OTP.',
                'code': 'OTP_EXPIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Clear OTP
    customer.otp_code = None
    customer.otp_created_at = None
    customer.save()
    
    logger.info(f"✅ Registration OTP verified for {phone}")
    
    customer_data = {
        'id': customer.id,
        'full_name': customer.full_name,
        'email': customer.email if customer.email else "",
        'phone_number': customer.phone_number,
        'wallet_balance': str(customer.wallet_balance),
        'rating': str(customer.rating),
        'status': customer.status
    }
    
    return Response({
        'success': True,
        'message': 'OTP verified successfully',
        'customer': customer_data
    }, status=status.HTTP_200_OK)

# ============================================
# ✅ REGISTER CUSTOMER - Complete Registration
# ============================================
from django.db.models import Q  # ✅ Add this import
@api_view(['POST'])
def register_customer_view(request):
    """
    Register a new customer with full details.
    Updates temp customer or creates new one with email.
    """
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
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email is required.',
                'code': 'EMAIL_REQUIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ Check if customer already exists by phone or email
        existing_customer = Rider.objects.filter(
            models.Q(phone_number=phone_number) | models.Q(email=email)
        ).first()
        
        if existing_customer:
            # ✅ If it's a temp customer (email starts with temp_ or is None), update it
            if existing_customer.phone_number == phone_number and (
                existing_customer.email is None or 
                existing_customer.email == '' or 
                existing_customer.email.startswith('temp_')
            ):
                # ✅ Update temp customer with all details
                logger.info(f"📝 Updating temp customer: {phone_number}")
                existing_customer.full_name = full_name
                existing_customer.email = email  # ✅ Set real email
                existing_customer.status = Rider.Status.ACTIVE
                existing_customer.save()
                
                serializer = RiderSerializer(existing_customer)
                return Response({
                    'success': True,
                    'message': 'Registration successful. Please login.',
                    'customer': serializer.data
                }, status=status.HTTP_200_OK)
            
            # ✅ Check if email conflict (email belongs to another customer)
            if email and existing_customer.email == email and existing_customer.phone_number != phone_number:
                return Response({
                    'success': False,
                    'message': 'Email already registered.',
                    'code': 'EMAIL_EXISTS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Real existing customer - return error
            error_messages = []
            if existing_customer.phone_number == phone_number:
                error_messages.append("Phone number already registered")
            if email and existing_customer.email == email:
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
        
        # ✅ Create new customer (if no temp customer exists)
        customer = Rider.objects.create(
            phone_number=phone_number,
            full_name=full_name,
            email=email,
            wallet_balance=0.00,
            rating=5.00,
            status=Rider.Status.ACTIVE
        )

        serializer = RiderSerializer(customer)
        return Response({
            'success': True,
            'message': 'Registration successful. Please login.',
            'customer': serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Customer registration error: {str(e)}")
        return Response({
            'success': False,
            'message': f"An unexpected error occurred during registration: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
 # Send OTP - Customer Login
# ============================================
@api_view(['POST'])
def send_customer_login_otp_view(request):
    """
    Send OTP to the provided phone number for login.
    Auto-creates customer if not exists (FOR TESTING ONLY).
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
        
        logger.info(f"📤 Customer Login OTP request for: {phone_number}")
        
        # ----- 2. CHECK IF CUSTOMER EXISTS -----
        customer = Rider.objects.filter(phone_number=phone_number).first()
        
        # ✅ Auto-create for testing if not exists
        if not customer:
            logger.info(f"🔄 Auto-creating customer: {phone_number}")
            customer = Rider.objects.create(
                phone_number=phone_number,
                full_name=f"User_{phone_number}",
                email=f"{phone_number}@temp.com",
                wallet_balance=0.00,
                rating=5.00,
                status=Rider.Status.ACTIVE
            )
            logger.info(f"✅ Auto-created customer: {phone_number}")
        
        # ✅ Check if customer is fully registered (has real email, not temp)
        if customer.email is None or customer.email == '' or customer.email.startswith('temp_'):
            logger.warning(f"Login failed: Registration incomplete for {phone_number}")
            return Response({
                'success': False,
                'message': 'Please complete your registration first.',
                'code': 'REGISTRATION_INCOMPLETE'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ----- 3. GENERATE OTP -----
        otp_code = "1234" #random.randint(1000, 9999)
        logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
        
        # ----- 4. SAVE OTP TO DATABASE -----
        try:
            customer.otp_code = otp_code
            customer.otp_created_at = timezone.now()
            customer.save()
            logger.info(f"✅ OTP updated for customer: {phone_number}")

            # -----------------  Temporary Bypass   --------------------
            return Response({
                'success': True,
                'message': 'OTP sent successfully.',
                'debug_otp': str(otp_code),
                'code': 'OTP_SENT',
            }, status=status.HTTP_200_OK)
            # ----------------------------------------------------------
                
        except Exception as db_error:
            logger.error(f"Database error while saving OTP: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ----- 5. SEND SMS (BYPASSED FOR NOW) -----
        # ... (SMS logic if needed)
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_customer_login_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================================
# views.py - Add this function
@api_view(['POST'])
def verify_customer_login_otp_view(request):
    """
    Verify OTP for Login flow only.
    """
    phone = request.data.get('phone')
    otp = request.data.get('otp')
    
    if not phone or not otp:
        return Response({
            'success': False,
            'message': 'Phone and OTP are required',
            'code': 'MISSING_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    phone = str(phone).strip().replace("+", "")
    otp = str(otp).strip()
    
    if not otp.isdigit() or len(otp) != 4:
        return Response({
            'success': False,
            'message': 'Invalid OTP format. Please enter a 4-digit OTP.',
            'code': 'INVALID_OTP_FORMAT'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"🔍 Verifying Login OTP for: {phone}")
    
    customer = Rider.objects.filter(phone_number=phone).first()
    
    if not customer:
        return Response({
            'success': False,
            'message': 'Account not found. Please register first.',
            'code': 'CUSTOMER_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # ✅ Check: Must be fully registered (not temp)
    if customer.email is None or customer.email == '' or customer.email.startswith('temp_'):
        return Response({
            'success': False,
            'message': 'Please complete your registration first.',
            'code': 'REGISTRATION_INCOMPLETE'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check OTP
    if not customer.otp_code:
        return Response({
            'success': False,
            'message': 'No OTP requested. Please request OTP first.',
            'code': 'NO_OTP_REQUESTED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if str(customer.otp_code) != str(otp):
        return Response({
            'success': False,
            'message': 'Invalid OTP. Please try again.',
            'code': 'INVALID_OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check OTP expiry (5 minutes)
    if customer.otp_created_at:
        expiry_time = customer.otp_created_at + timedelta(minutes=5)
        if timezone.now() > expiry_time:
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new OTP.',
                'code': 'OTP_EXPIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Clear OTP
    customer.otp_code = None
    customer.otp_created_at = None
    customer.save()
    
    logger.info(f"✅ Login OTP verified for {phone}")
    
    customer_data = {
        'id': customer.id,
        'full_name': customer.full_name,
        'email': customer.email,
        'phone_number': customer.phone_number,
        'wallet_balance': str(customer.wallet_balance),
        'rating': str(customer.rating),
        'status': customer.status
    }
    
    return Response({
        'success': True,
        'message': 'OTP verified successfully',
        'customer': customer_data
    }, status=status.HTTP_200_OK)