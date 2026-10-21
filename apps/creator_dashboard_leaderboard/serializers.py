from rest_framework import serializers
from apps.creator_dashboard.models import CreatorProfile
from rest_framework import serializers



class LeaderboardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.name")
    profile_image = serializers.SerializerMethodField(allow_null=True)

    total_subscribers = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_likes = serializers.IntegerField()
    total_comments = serializers.IntegerField()
    engagement_rate = serializers.FloatField()
    rank = serializers.IntegerField()
    platform = serializers.CharField(allow_null=True, required=False)
    growth_rate = serializers.FloatField(required=False)
    
    class Meta:
        model = CreatorProfile
        fields = [
            "id",
            "username",
            "profile_image",
            "total_subscribers",
            "total_views",
            "total_likes",
            "total_comments",
            "engagement_rate",
            "rank",
            "platform",
            "growth_rate",
        ]

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.user.profile_pic:
            url = obj.user.profile_pic.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None