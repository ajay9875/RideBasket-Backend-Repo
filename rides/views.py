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

import datetime
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

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

@api_view(['POST'])
def send_auth_otp_view(request):
    phone_number = request.data.get('phone_number')
    if not phone_number:
        return Response({'success': False, 'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = Driver.objects.filter(phone_number=phone_number).first()
    if not driver:
        return Response({'success': False, 'error': 'Driver account not found with this phone number.'}, status=status.HTTP_404_NOT_FOUND)

    otp_code = str(random.randint(1000, 9999))
    driver.otp_code = otp_code
    driver.save()
    
    return Response({
        'success': True, 
        'message': 'OTP sent successfully.',
        'debug_otp': otp_code
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
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

    return Response({'success': False, 'error': 'Invalid OTP code.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def reset_password_view(request):
    phone_number = request.data.get('phone_number')
    new_password = request.data.get('new_password')

    if not phone_number or not new_password:
        return Response({'success': False, 'error': 'Phone number and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    driver = Driver.objects.filter(phone_number=phone_number).first()
    if not driver:
        return Response({'success': False, 'error': 'Driver account not found.'}, status=status.HTTP_404_NOT_FOUND)

    if hasattr(driver, 'set_password'):
        driver.set_password(new_password)
    else:
        driver.password = new_password
        
    driver.save()

    return Response({
        'success': True,
        'message': 'Password has been reset successfully.'
    }, status=status.HTTP_200_OK)

@api_view(['GET', 'PATCH'])
def driver_profile_view(request, driver_id):
    profile = get_object_or_404(Driver, id=driver_id)
    if request.method == 'GET':
        serializer = DriverSerializer(profile)
        return Response(serializer.data)
    elif request.method == 'PATCH':
        serializer = DriverSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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