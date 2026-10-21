from rest_framework import serializers
from .models import Newsletter

class NewsLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Newsletter
        fields = ['email', 'created_at']