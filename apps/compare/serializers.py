from rest_framework import serializers
from .models import ThirdPartyData

class ThirdPartyDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThirdPartyData
        fields = ['name', 'data', 'fetched_at']
