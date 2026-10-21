from calendar import month_name
from collections import defaultdict

from rest_framework import serializers
from .models import (
    CreatorProfile,
    PlatformChoices, 
    InstagramWebhookEvent,
    TiktokProfileMedia,
    YoutubeProfileMedia,
    InstagramProfileMedia,
    TiktokProfile,
    YoutubeProfile,
    InstagramProfile
)

class TiktokProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiktokProfile
        fields = ['tiktok_user_id', 'username', 'followers_count', 'following_count', 'view_count', 'video_count']

class YoutubeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = YoutubeProfile
        fields = ['youtube_channel_id', 'channel_title', 'subscribers_count', 'view_count', 'video_count' ]

class InstagramProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramProfile
        fields = ['instagram_user_id', 'username', 'followers_count', 'following_count', 'view_count', 'media_count']    



class CreatorProfileSerializers(serializers.ModelSerializer):
    tiktok_profile = TiktokProfileSerializer(read_only=True)
    youtube_profile = YoutubeProfileSerializer(read_only=True)
    instagram_profile = InstagramProfileSerializer(read_only=True)
    ai_score_status = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    platform_breakdown = serializers.SerializerMethodField()
    youtube_channel_account_id = serializers.SerializerMethodField()
    engagement_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = CreatorProfile
        fields = [
            'id', 'user', 'tiktok_profile', 'youtube_profile', 'instagram_profile',
            'youtube_channel_account_id', 'ai_score_status', 'growth_rate',
            'platform_breakdown', 'engagement_rate', 'created_at',
        ]

    def get_youtube_channel_account_id(self, obj):
        from apps.viral_builder.platform_accounts import ensure_youtube_platform_account

        account = ensure_youtube_platform_account(obj.user)
        return account.id if account else None

    def get_platform_profiles(self, obj):
        return {
            'tiktok': getattr(obj, 'tiktok_profile', None),
            'youtube': getattr(obj, 'youtube_profile', None),
            'instagram': getattr(obj, 'instagram_profile', None),
        }

    def get_ai_score_status(self, obj):
        profiles = self.get_platform_profiles(obj)

        total_engagement = 0
        total_engagement += profiles['tiktok'].followers_count if profiles['tiktok'] else 0
        total_engagement += profiles['youtube'].subscribers_count if profiles['youtube'] else 0
        total_engagement += profiles['youtube'].view_count if profiles['youtube'] else 0
        total_engagement += profiles['instagram'].followers_count if profiles['instagram'] else 0
        total_engagement += (profiles['instagram'].media_count if profiles['instagram'] else 0) * 10

        
        if total_engagement > 1000000:
            return "Stellar"
        elif total_engagement > 100000:
            return "Solid"
        elif total_engagement > 10000:
            return "Balanced"
        elif total_engagement > 0:
            return "Fading"
        else:
            return "N/A"

    def get_growth_rate(self, obj):
        profiles = self.get_platform_profiles(obj)
        total_videos = 0
        total_videos += profiles['tiktok'].video_count if profiles['tiktok'] else 0
        total_videos += profiles['youtube'].video_count if profiles['youtube'] else 0
        total_videos += profiles['instagram'].media_count if profiles['instagram'] else 0

        if total_videos == 0:
            return "0.0%"

        growth = min(15.0, max(1.0, total_videos * 0.5))
        if growth > 10.0 and growth <= 15.0:
            return "Supreme"
        elif growth > 5.0 and growth <= 10.0:
            return "Remarkable"
        elif growth > 2.0 and growth <= 5.0:
            return "Steady"
        elif growth > 0.0 and growth <= 2.0:
            return "Lagging"
        else:
            return f"N/A"

    def get_platform_breakdown(self, obj):
        profiles = self.get_platform_profiles(obj)

        def safe_int(value):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0

        yt_score = safe_int(profiles['youtube'].subscribers_count if profiles['youtube'] else 0) * 2 + safe_int(profiles['youtube'].view_count if profiles['youtube'] else 0)
        tk_score = safe_int(profiles['tiktok'].followers_count if profiles['tiktok'] else 0) * 2 + safe_int(profiles['tiktok'].view_count if profiles['tiktok'] else 0)
        ig_score = safe_int(profiles['instagram'].followers_count if profiles['instagram'] else 0) * 2 + safe_int(profiles['instagram'].media_count if profiles['instagram'] else 0) * 10

        total = yt_score + tk_score + ig_score
        if total == 0:
            return {
                "youtube": 0,
                "instagram": 0,
                "tiktok": 0
            }

        return {
            "youtube": round((yt_score / total) * 100, 1),
            "instagram": round((ig_score / total) * 100, 1),
            "tiktok": round((tk_score / total) * 100, 1)
        }

    def get_engagement_rate(self, obj):
        from django.db.models import Sum

        # Tiktok
        tiktok_agg = TiktokProfileMedia.objects.filter(profile=obj).aggregate(
            total_likes=Sum('likes_count'),
            total_views=Sum('view_count')
        )
        t_likes = tiktok_agg['total_likes'] or 0
        t_views = tiktok_agg['total_views'] or 0

        # Youtube
        youtube_agg = YoutubeProfileMedia.objects.filter(profile=obj).aggregate(
            total_likes=Sum('likes_count'),
            total_views=Sum('view_count')
        )
        y_likes = youtube_agg['total_likes'] or 0
        y_views = youtube_agg['total_views'] or 0

        # Instagram
        instagram_agg = InstagramProfileMedia.objects.filter(profile=obj).aggregate(
            total_likes=Sum('likes_count'),
            total_views=Sum('view_count')
        )
        i_likes = instagram_agg['total_likes'] or 0
        i_views = instagram_agg['total_views'] or 0

        # Overall
        overall_likes = t_likes + y_likes + i_likes
        overall_views = t_views + y_views + i_views
        
        return round((overall_likes / overall_views) * 100, 2) if overall_views > 0 else 0.0
        

        
class TikTokVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiktokProfileMedia
        fields = [
            "likes_count",
            "view_count",
            "comment_count",
            "share_count"
        ]
    
class MonthOnlyVideoSerializer(serializers.Serializer):
    name = serializers.CharField()
    video = TikTokVideoSerializer(many=True)
    
    
class TiktokProfileDetailsSerializer(serializers.ModelSerializer):
    months = serializers.SerializerMethodField()
    profile = serializers.ReadOnlyField(source='id')
    platform = serializers.SerializerMethodField() 
    ai_score_status = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    profile_media = TiktokProfileSerializer(source='tiktok_profile', read_only=True)
    engagement_rate = serializers.SerializerMethodField()
    class Meta:
        model = CreatorProfile
        fields = ['id', 'profile','profile_media', 'platform', 'ai_score_status', 'growth_rate', 'engagement_rate', 'months']

    def get_platform(self, obj):
        return "tiktok"

    def get_engagement_rate(self, obj):
        videos = self.context.get("videos", [])
        if not videos:
            return 0.0
        total_likes = sum(video.likes_count for video in videos)
        total_views = sum(video.view_count for video in videos)
        if total_views > 0:
            return round((total_likes / total_views) * 100, 2)
        return 0.0

    def get_ai_score_status(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_engagement = 0
        total_engagement += tiktok_profile.followers_count if tiktok_profile else 0
        total_engagement += youtube_profile.subscribers_count if youtube_profile else 0
        total_engagement += youtube_profile.view_count if youtube_profile else 0
        total_engagement += instagram_profile.followers_count if instagram_profile else 0
        total_engagement += (instagram_profile.media_count if instagram_profile else 0) * 10
        if total_engagement > 1000000: return "Stellar"
        elif total_engagement > 100000: return "Solid"
        elif total_engagement > 10000: return "Balanced"
        elif total_engagement > 0: return "Fading"
        return "N/A"

    def get_growth_rate(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_videos = 0
        total_videos += tiktok_profile.video_count if tiktok_profile else 0
        total_videos += youtube_profile.video_count if youtube_profile else 0
        total_videos += instagram_profile.media_count if instagram_profile else 0

        if total_videos == 0: return "N/A"
        growth = min(15.0, max(1.0, total_videos * 0.5))
        if growth > 10.0 and growth <= 15.0:
            return "Supreme"
        elif growth > 5.0 and growth <= 10.0:
            return "Remarkable"
        elif growth > 2.0 and growth <= 5.0:
            return "Steady"
        elif growth > 0.0 and growth <= 2.0:
            return "Lagging"
        else:
            return f"N/A"
        

    def get_months(self, obj):
        videos = self.context.get("videos", [])
        grouped = defaultdict(list)

        for video in videos:
            month_name = video.created_at.strftime("%B")
            grouped[month_name].append({
                "video_id": video.video_id,
                "likes_count": video.likes_count,
                "view_count": video.view_count,
                "comment_count": video.comment_count,
                "share_count": video.share_count
            })

        return [
            {"name": name, "videos": vlist}
            for name, vlist in grouped.items()
        ]
        
class YoutubeProfileDetailsSerializer(serializers.ModelSerializer):
    months = serializers.SerializerMethodField()
    profile = serializers.ReadOnlyField(source='id')
    platform = serializers.SerializerMethodField() 
    ai_score_status = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    profile_media = YoutubeProfileSerializer(source='youtube_profile', read_only=True)
    engagement_rate = serializers.SerializerMethodField()
    class Meta:
        model = CreatorProfile
        fields = ['id', 'profile','profile_media', 'platform', 'ai_score_status', 'growth_rate', 'engagement_rate', 'months']

    def get_platform(self, obj):
        return "youtube"

    def get_engagement_rate(self, obj):
        videos = self.context.get("videos", [])
        if not videos:
            return 0.0
        total_likes = sum(video.likes_count for video in videos)
        total_views = sum(video.view_count for video in videos)
        if total_views > 0:
            return round((total_likes / total_views) * 100, 2)
        return 0.0

    def get_ai_score_status(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_engagement = 0
        total_engagement += tiktok_profile.followers_count if tiktok_profile else 0
        total_engagement += youtube_profile.subscribers_count if youtube_profile else 0
        total_engagement += youtube_profile.view_count if youtube_profile else 0
        total_engagement += instagram_profile.followers_count if instagram_profile else 0
        total_engagement += (instagram_profile.media_count if instagram_profile else 0) * 10

        if total_engagement > 1000000: return "Stellar"
        elif total_engagement > 100000: return "Solid"
        elif total_engagement > 10000: return "Balanced"
        elif total_engagement > 0: return "Fading"
        return "N/A"

    def get_growth_rate(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_videos = 0
        total_videos += tiktok_profile.video_count if tiktok_profile else 0
        total_videos += youtube_profile.video_count if youtube_profile else 0
        total_videos += instagram_profile.media_count if instagram_profile else 0

        if total_videos == 0: return "N/A"
        growth = min(15.0, max(1.0, total_videos * 0.5))
        if growth > 10.0 and growth <= 15.0:
            return "Supreme"
        elif growth > 5.0 and growth <= 10.0:
            return "Remarkable"
        elif growth > 2.0 and growth <= 5.0:
            return "Steady"
        elif growth > 0.0 and growth <= 2.0:
            return "Lagging"
        else:
            return f"N/A"

    def get_months(self, obj):
        videos = self.context.get("videos", [])
        grouped = defaultdict(list)

        for video in videos:
            month_name = video.created_at.strftime("%B")
            grouped[month_name].append({
                "video_id": video.video_id,
                "likes_count": video.likes_count,
                "view_count": video.view_count,
                "comment_count": video.comment_count,
                "share_count": video.share_count
            })

        return [
            {"name": name, "videos": vlist}
            for name, vlist in grouped.items()
        ]
    
# serializer.py
from collections import defaultdict

class InstagramProfileDetailSerializer(serializers.ModelSerializer):
    months = serializers.SerializerMethodField()
    profile = serializers.ReadOnlyField(source='id')
    platform = serializers.SerializerMethodField() 
    ai_score_status = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    profile_media = InstagramProfileSerializer(source='instagram_profile', read_only=True)
    engagement_rate = serializers.SerializerMethodField()
    class Meta:
        model = CreatorProfile
        fields = ['id', 'profile','profile_media', 'platform', 'ai_score_status', 'growth_rate', 'engagement_rate', 'months']

    def get_platform(self, obj):
        return "instagram"

    def get_engagement_rate(self, obj):
        videos = self.context.get("videos", [])
        if not videos:
            return 0.0
        total_likes = sum(video.likes_count for video in videos)
        total_views = sum(video.view_count for video in videos)
        if total_views > 0:
            return round((total_likes / total_views) * 100, 2)
        return 0.0

    def get_ai_score_status(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_engagement = 0
        total_engagement += tiktok_profile.followers_count if tiktok_profile else 0
        total_engagement += youtube_profile.subscribers_count if youtube_profile else 0
        total_engagement += youtube_profile.view_count if youtube_profile else 0
        total_engagement += instagram_profile.followers_count if instagram_profile else 0
        total_engagement += (instagram_profile.media_count if instagram_profile else 0) * 10

        if total_engagement > 1000000: return "Stellar"
        elif total_engagement > 100000: return "Solid"
        elif total_engagement > 10000: return "Balanced"
        elif total_engagement > 0: return "Fading"
        return "N/A"

    def get_growth_rate(self, obj):
        profile = obj
        tiktok_profile = getattr(profile, 'tiktok_profile', None)
        youtube_profile = getattr(profile, 'youtube_profile', None)
        instagram_profile = getattr(profile, 'instagram_profile', None)

        total_videos = 0
        total_videos += tiktok_profile.video_count if tiktok_profile else 0
        total_videos += youtube_profile.video_count if youtube_profile else 0
        total_videos += instagram_profile.media_count if instagram_profile else 0

        if total_videos == 0: return "N/A"
        growth = min(15.0, max(1.0, total_videos * 0.5))
        if growth > 10.0 and growth <= 15.0:
            return "Supreme"
        elif growth > 5.0 and growth <= 10.0:
            return "Remarkable"
        elif growth > 2.0 and growth <= 5.0:
            return "Steady"
        elif growth > 0.0 and growth <= 2.0:
            return "Lagging"
        else:
            return f"N/A"

    def get_months(self, obj):
        videos = self.context.get("videos", [])
        grouped = defaultdict(list)

        for video in videos:
            month_name = video.created_at.strftime("%B")
            grouped[month_name].append({
                "video_id": video.video_id,
                "likes_count": video.likes_count,
                "view_count": video.view_count,
                "comment_count": video.comment_count,
                "share_count": video.share_count
            })

        return [
            {"name": name, "videos": vlist}
            for name, vlist in grouped.items()
        ]


class InstagramWebhookEventSerializer(serializers.ModelSerializer):
    """Serializer for InstagramWebhookEvent model"""
    event_display = serializers.SerializerMethodField()
    
    class Meta:
        model = InstagramWebhookEvent
        fields = [
            'id',
            'media_id',
            'event_type',
            'event_display',
            'caption',
            'like_count',
            'comment_count',
            'view_count',
            'reaction_type',
            'comment_text',
            'commenter_id',
            'timestamp',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_event_display(self, obj):
        """Return human-readable event type"""
        return dict(obj.EVENT_TYPE_CHOICES).get(obj.event_type, obj.event_type)


class InstagramWebhookEventDetailSerializer(InstagramWebhookEventSerializer):
    """Detailed serializer including raw webhook data"""
    
    class Meta(InstagramWebhookEventSerializer.Meta):
        fields = InstagramWebhookEventSerializer.Meta.fields + ['raw_webhook_data', 'updated_at']



class ChannelAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorProfile
        fields = ["id", "user"]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        tiktok_profile = getattr(instance, "tiktok_profile", None)
        youtube_profile = getattr(instance, "youtube_profile", None)
        instagram_profile = getattr(instance, "instagram_profile", None)

        data["platform_stats"] = {
            "tiktok": {
                "follower_count": tiktok_profile.followers_count if tiktok_profile else 0,
                "likes_count": 0,
                "video_count": tiktok_profile.video_count if tiktok_profile else 0,
            },
            "youtube": {
                "subscriber_count": youtube_profile.subscribers_count if youtube_profile else 0,
                "view_count": youtube_profile.view_count if youtube_profile else 0,
                "video_count": youtube_profile.video_count if youtube_profile else 0,
            },
            "instagram": {
                "followers_count": instagram_profile.followers_count if instagram_profile else 0,
                "media_count": instagram_profile.media_count if instagram_profile else 0,
            },
        }

        return data


class CompetitorSerializer(serializers.Serializer):
    """
    Serializer for competitor creators based on YouTube content similarity
    """
    profile_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    channel_title = serializers.CharField()
    channel_id = serializers.CharField()
    subscribers = serializers.IntegerField()
    views = serializers.BigIntegerField()
    videos = serializers.BigIntegerField()
    similarity_score = serializers.FloatField(help_text="Content similarity score (0-1)")
    matching_keywords = serializers.ListField(child=serializers.CharField())


class CompetitionsResponseSerializer(serializers.Serializer):
    """
    Serializer for the competitions API response
    """
    message = serializers.CharField()
    user_keywords = serializers.ListField(child=serializers.CharField())
    total_competitors_found = serializers.IntegerField()
    competitors = CompetitorSerializer(many=True)
    
