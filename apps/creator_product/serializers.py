from .models import CreatorProduct
from rest_framework import serializers


class CreatorProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorProduct
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']