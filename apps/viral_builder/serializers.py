from rest_framework import serializers

from .models import PlatformAccount, ViralBuilderRun, ViralIdea
from .platform_accounts import resolve_channel_account_for_user, user_has_youtube_connection


class ViralBuilderRunCreateSerializer(serializers.Serializer):
    channel_account_id = serializers.IntegerField()
    content_type = serializers.CharField(max_length=50)
    goal = serializers.CharField(max_length=50, required=False, allow_blank=True)
    toggles = serializers.JSONField(required=False)

    def validate_channel_account_id(self, value):
        request = self.context.get("request")
        user = request.user
        account = resolve_channel_account_for_user(user, value)
        if not account:
            raise serializers.ValidationError(
                "Channel account not found for this user. "
                "Use the id from GET /api/platform-accounts/ (YouTube account), "
                "not CreatorProfile id."
            )
        if not user_has_youtube_connection(user, account):
            raise serializers.ValidationError("YouTube account is not connected for this user.")

        return account.id

    def validate_toggles(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Toggles must be an object.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        account_id = validated_data["channel_account_id"]
        channel_account = PlatformAccount.objects.get(id=account_id, user=user)
        toggles = validated_data.get("toggles") or {}
        toggles.setdefault("strict_alignment", True)
        toggles.setdefault("brand_safe_only", False)

        return ViralBuilderRun.objects.create(
            user=user,
            channel_account=channel_account,
            content_type=validated_data["content_type"],
            goal=validated_data.get("goal", ""),
            toggles=toggles,
            status="queued",
        )


class ViralIdeaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViralIdea
        fields = [
            "id",
            "headline",
            "suggested_title",
            "hook_structure",
            "format_guidance",
            "suggested_cta",
            "why_fits_channel",
            "tags",
            "safety_flags",
            "viral_gap",
            "is_saved",
            "saved_at",
            "sent_to_plan_at",
            "created_at",
        ]


class ViralBuilderRunSerializer(serializers.ModelSerializer):
    channel_account_id = serializers.IntegerField(source="channel_account.id", read_only=True)

    class Meta:
        model = ViralBuilderRun
        fields = [
            "id",
            "channel_account_id",
            "content_type",
            "goal",
            "toggles",
            "status",
            "error",
            "created_at",
            "finished_at",
            "meta",
        ]

class PlartformAccountSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PlatformAccount
        fields = "__all__"