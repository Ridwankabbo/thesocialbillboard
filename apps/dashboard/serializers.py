from rest_framework import serializers
from apps.users.models import User
from .models import Creator

class UserSocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['youtube_link', 'instagram_link', 'tiktok_link']



class SocialAnalyzerSerializer(serializers.Serializer):
    url = serializers.URLField()
    platform = serializers.ChoiceField(choices=['youtube', 'tiktok', 'instagram'])