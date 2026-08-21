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

logger = logging.getLogger(__name__)

# ============================================
# ✅ SEND OTP - Customer Registration
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
                email__isnull=True,  # No email set (temp customer)
                created_at__lt=timezone.now() - timedelta(hours=24)  # Older than 24 hours
            )
            orphaned_count = orphaned_customers.count()
            if orphaned_count > 0:
                logger.info(f"🗑️ Deleting {orphaned_count} orphaned temp customers older than 24 hours")
                orphaned_customers.delete()
        except Exception as cleanup_error:
            logger.warning(f"Cleanup error: {cleanup_error}")  # Don't fail the request
        
        # ----- 3. CHECK IF CUSTOMER EXISTS -----
        existing_customer = Rider.objects.filter(phone_number=phone_number).first()
        
        if existing_customer:
            # ✅ Check if it's a temp customer (no email)
            if existing_customer.email is None or existing_customer.email == '':
                logger.info(f"📱 Reusing existing temp customer: {phone_number}")
                customer = existing_customer
                customer.full_name = name  # ✅ Update name
                customer.save()
            else:
                # ✅ Real registered customer
                logger.warning(f"Registration failed: Phone already registered - {phone_number}")
                return Response({
                    'success': False,
                    'message': 'Phone number already registered. Please login instead.',
                    'code': 'CUSTOMER_EXISTS',
                    'exists': True
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # ----- 4. CREATE TEMPORARY CUSTOMER -----
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
        
        # ----- 5. GENERATE AND SAVE OTP -----
        try:
            # For customer, use same OTP system
            otp_code = "1234"  # For testing purposes only
            # otp_code = str(random.randint(1000, 9999))
            logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
            
            # You may need to add OTP fields to Rider model
            customer.otp_code = otp_code
            customer.otp_created_at = timezone.now()
            customer.save()
            
            logger.info(f"✅ OTP saved for: {phone_number}")

            # -----------------  Temperary Bypass   --------------------
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

        # ----- 6. SEND SMS (BYPASSED FOR NOW) -----
        # ... (same SMS logic as driver)
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_customer_register_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            Q(phone_number=phone_number) | Q(email=email)
        ).first()
        
        if existing_customer:
            # ✅ If it's a temp customer (no email), update it instead of returning error
            if existing_customer.phone_number == phone_number and (existing_customer.email is None or existing_customer.email == ''):
                # ✅ Update temp customer with all details
                logger.info(f"📝 Updating temp customer: {phone_number}")
                existing_customer.full_name = full_name
                existing_customer.email = email
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
# ✅ SEND OTP - Customer Login (NO AUTO-CREATION)
# ============================================
@api_view(['POST'])
def send_customer_login_otp_view(request):
    """
    Send OTP to the provided phone number for login.
    ONLY allows existing customers. Does NOT create new customers.
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
        try:
            customer = Rider.objects.filter(phone_number=phone_number).first()
            
            if not customer:
                logger.warning(f"Login failed: Customer not found - {phone_number}")
                return Response({
                    'success': False,
                    'message': 'Account not found. Please register first.',
                    'code': 'CUSTOMER_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as db_error:
            logger.error(f"Database error while checking customer: {str(db_error)}")
            return Response({
                'success': False,
                'message': 'Unable to process your request. Please try again.',
                'code': 'DATABASE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # ----- 3. GENERATE OTP -----
        otp_code = random.randint(1000, 9999)
        logger.debug(f"Generated OTP: {otp_code} for {phone_number}")
        
        # ----- 4. SAVE OTP TO DATABASE -----
        try:
            customer.otp_code = otp_code
            customer.otp_created_at = timezone.now()
            customer.save()
            logger.info(f"✅ OTP updated for existing customer: {phone_number}")

            # -----------------  Temperary Bypass   --------------------
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
        # ... (same SMS logic as driver)
        
    except Exception as e:
        logger.error(f"💥 Unexpected error in send_customer_login_otp_view: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# ✅ VERIFY OTP - Customer (Login/Registration)
# ============================================
@api_view(['POST'])
def verify_customer_auth_otp_view(request):
    """
    Verify OTP for both Login and Registration flows for customers.
    
    For Login: 
        - Verifies OTP for existing customers only
        - Returns customer data for login session
    
    For Registration:
        - Verifies OTP for temp customers only
        - Returns customer data to proceed with registration
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
    
    # Validate OTP format (4 digits)
    if not otp.isdigit() or len(otp) != 4:
        return Response({
            'success': False,
            'message': 'Invalid OTP format. Please enter a 4-digit OTP.',
            'code': 'INVALID_OTP_FORMAT'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    logger.info(f"🔍 Verifying OTP for customer: {phone} (Flow: {flow})")
    
    # ----- 2. FIND CUSTOMER -----
    customer = Rider.objects.filter(phone_number=phone).first()
    if not customer:
        logger.warning(f"Verify OTP failed: Customer not found - {phone}")
        return Response({
            'success': False,
            'message': 'Customer not found. Please register first.',
            'code': 'CUSTOMER_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # ----- 3. FLOW-SPECIFIC CHECKS -----
    
    # ✅ For LOGIN flow: Customer must be a real registered customer (email exists)
    if flow == 'Login':
        if customer.email is None or customer.email == '':
            logger.warning(f"Login failed: Registration incomplete for {phone}")
            return Response({
                'success': False,
                'message': 'Please complete your registration first.',
                'code': 'REGISTRATION_INCOMPLETE'
            }, status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"📱 Customer Login OTP verification for: {phone}")
    
    # ✅ For REGISTRATION flow: Customer must be a temp customer (email is None)
    elif flow == 'Registration':
        if customer.email is not None and customer.email != '':
            logger.warning(f"Registration failed: Phone already registered - {phone}")
            return Response({
                'success': False,
                'message': 'Phone number already registered. Please login instead.',
                'code': 'ALREADY_REGISTERED'
            }, status=status.HTTP_400_BAD_REQUEST)
        logger.info(f"📝 Customer Registration OTP verification for: {phone}")

    else:
        logger.warning(f"Verify OTP failed: Invalid flow type - {flow}")
        return Response({
            'success': False,
            'message': 'Invalid flow type. Must be either "Login" or "Registration".',
            'code': 'INVALID_FLOW'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 4. CHECK OTP -----
    if not customer.otp_code:
        logger.warning(f"Verify OTP failed: No OTP requested for {phone}")
        return Response({
            'success': False,
            'message': 'No OTP requested. Please request OTP first.',
            'code': 'NO_OTP_REQUESTED'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if str(customer.otp_code) != str(otp):
        logger.warning(f"Verify OTP failed: Invalid OTP for {phone}")
        return Response({
            'success': False,
            'message': 'Invalid OTP. Please try again.',
            'code': 'INVALID_OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 5. CHECK OTP EXPIRY (5 minutes) -----
    if customer.otp_created_at:
        expiry_time = customer.otp_created_at + timedelta(minutes=5)
        if timezone.now() > expiry_time:
            logger.warning(f"Verify OTP failed: OTP expired for {phone}")
            return Response({
                'success': False,
                'message': 'OTP has expired. Please request a new OTP.',
                'code': 'OTP_EXPIRED'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # ----- 6. CLEAR OTP AND SAVE -----
    customer.otp_code = None
    customer.otp_created_at = None
    customer.save()
    
    logger.info(f"✅ OTP verified successfully for {phone} (Flow: {flow})")
    
    # ----- 7. RETURN RESPONSE -----
    return Response({
        'success': True,
        'message': 'OTP verified successfully',
        'flow': flow,  # ✅ Return flow for client reference
        'customer': RiderSerializer(customer).data
    }, status=status.HTTP_200_OK)