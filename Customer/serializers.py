from rest_framework import serializers
from Driver.models import Rider

class RiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rider
        fields = [
            'id', 'full_name', 'email', 'phone_number', 
            'wallet_balance', 'rating', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'wallet_balance', 'rating', 'created_at']