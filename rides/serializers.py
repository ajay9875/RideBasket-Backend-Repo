from rest_framework import serializers
from .models import (
    Driver,
    VehicleDocument,
    Ride,
    EarningsTransaction,
    AppNotification,
    ChatMessage
)

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDocument
        fields = '__all__'

class RideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = '__all__'

class EarningsTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EarningsTransaction
        fields = '__all__'

class AppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppNotification
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'