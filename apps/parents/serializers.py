from rest_framework import serializers
from .models import (
    ChildProfile,
    Playlist,
    PlaylistItem,
    PlaylistExplanation,
    Review,
    Feedback,
    PlaylistChannel,
    YouTubeVideoCache,
)

# ✅ Simple serializers for nested output
class PlaylistSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = ['id', 'title']


class PlaylistChannelSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaylistChannel
        fields = ['id', 'title']


class PlaylistSerializer(serializers.ModelSerializer):
    age_range = serializers.SerializerMethodField()
    is_followed = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = [
            'id',
            'title',
            'age_range',
            'tags',
            'is_followed',
            'video_count'
        ]

    def get_age_range(self, obj):
        return f"{obj.age_min}-{obj.age_max}"

    def get_is_followed(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False

    def get_video_count(self, obj):
        # channels == videos
        return obj.channels.count()



# ✅ Full PlaylistChannel Serializer (if needed somewhere)
class PlaylistChannelSerializer(serializers.ModelSerializer):
    embed_url = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistChannel
        fields = [
            "id",
            "playlist",
            "channel_id",   # video_id
            "title",
            "link",         # watch URL (DB)
            "embed_url",    # iframe URL (UI)
            "tags",
            "added_at",
        ]

    def get_embed_url(self, obj):
        # channel_id == YouTube VIDEO ID
        return f"https://www.youtube.com/embed/{obj.channel_id}"


# ✅ Updated ReviewSerializer with nested channel & playlist data
class ReviewSerializer(serializers.ModelSerializer):
    playlist = PlaylistSimpleSerializer(read_only=True)
    channel = PlaylistChannelSimpleSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'kid_age',
            'comment',
            'playlist',
            'channel',
            'age_appropriateness',
            'educational_value',
            'emotional_impact',
            'cultural_sensitivity',
            'created_at',
        ]
        read_only_fields = [
            'age_appropriateness',
            'educational_value',
            'emotional_impact',
            'cultural_sensitivity',
            'created_at'
        ]


# ✅ Updated FeedbackSerializer with nested channel & playlist data
class FeedbackSerializer(serializers.ModelSerializer):
    playlist = PlaylistSimpleSerializer(read_only=True)
    channel = PlaylistChannelSimpleSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'id',
            'suggested_age',
            'tags',
            'comment',
            'playlist',
            'channel',
            'created_at',
        ]
        read_only_fields = ['created_at']


# -----------------------------
# Parents Dashboard V1
# -----------------------------

class ChildProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProfile
        fields = ["id", "name", "age_band", "language", "preferences", "created_at"]
        read_only_fields = ["id", "created_at"]


class ParentPlaylistCreateSerializer(serializers.Serializer):
    child_profile_id = serializers.IntegerField()
    filters = serializers.JSONField()
    session_length = serializers.IntegerField(min_value=1)


class PlaylistItemSerializer(serializers.ModelSerializer):
    analysis = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistItem
        fields = [
            "youtube_video_id",
            "position",
            "title",
            "duration",
            "channel_id",
            "thumbnail_url",
            "video_url",
            "analysis",
        ]

    def get_analysis(self, obj):
        analysis_map = self.context.get("analysis_map") or {}
        if obj.youtube_video_id in analysis_map:
            return analysis_map[obj.youtube_video_id]

        cache = YouTubeVideoCache.objects.filter(video_id=obj.youtube_video_id).only("analysis_json").first()
        return cache.analysis_json if cache else {}


class PlaylistExplanationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaylistExplanation
        fields = ["why_suitable_text", "created_at"]


class ParentPlaylistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Playlist
        fields = [
            "id",
            "child_profile",
            "filters_json",
            "status",
            "is_saved",
            "session_length",
            "created_at",
        ]


class ParentPlaylistOverviewSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child_profile.name", allow_null=True, read_only=True)
    playlist_title = serializers.CharField(source="title", read_only=True)
    video_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id",
            "child_name",
            "playlist_title",
            "video_count",
            "last_viewed_at",
        ]
