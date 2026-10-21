from rest_framework import serializers

ALLOWED_VIDEO_FIELDS = {
    "id", "create_time", "cover_image_url", "share_url", "video_description",
    "duration", "height", "width", "title", "embed_html", "embed_link",
    "like_count", "comment_count", "share_count", "view_count"
}

class TikTokVideoQuerySerializer(serializers.Serializer):
    video_ids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    def validate_video_ids(self, value):
        if len(value) > 20:
            raise serializers.ValidationError("Maximum 20 video_ids allowed.")
        return value

    def validate_fields(self, value):
        invalid = [f for f in value if f not in ALLOWED_VIDEO_FIELDS]
        if invalid:
            raise serializers.ValidationError(f"Invalid fields: {invalid}")
        return value






from rest_framework import serializers

ALLOWED_VIDEO_FIELDS = {
    "id", "create_time", "cover_image_url", "share_url", "video_description",
    "duration", "height", "width", "title", "embed_html", "embed_link",
    "like_count", "comment_count", "share_count", "view_count"
}

class TikTokVideoListSerializer(serializers.Serializer):
    cursor = serializers.IntegerField(required=False)   # UTC Unix ms timestamp
    max_count = serializers.IntegerField(required=False, min_value=1, max_value=20)
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )

    def validate_fields(self, value):
        invalid = [f for f in value if f not in ALLOWED_VIDEO_FIELDS]
        if invalid:
            raise serializers.ValidationError(f"Invalid fields: {invalid}")
        return value
