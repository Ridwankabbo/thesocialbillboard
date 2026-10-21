from apps.creator_dashboard.models import (
    CreatorProfile,
    PlatformChoices,
    YoutubeCredentials,
    YoutubeProfile,
)
from .models import PlatformAccount


def ensure_youtube_platform_account(user) -> PlatformAccount | None:
    """
    Ensure a YouTube PlatformAccount exists for the user when they have
    connected YouTube via CreatorProfile / OAuth.
    """
    existing = (
        PlatformAccount.objects.filter(user=user, platform="youtube")
        .order_by("created_at")
        .first()
    )
    if existing:
        return existing

    try:
        profile = CreatorProfile.objects.select_related("youtube_profile").get(user=user)
    except CreatorProfile.DoesNotExist:
        profile = None

    yt_profile = getattr(profile, "youtube_profile", None) if profile else None
    channel_id = getattr(yt_profile, "youtube_channel_id", None) if yt_profile else None
    if not channel_id and getattr(user, "youtube_link", None):
        channel_id = _youtube_channel_id_from_link(user.youtube_link)

    if not channel_id:
        return None

    display_name = getattr(yt_profile, "channel_title", None) or channel_id
    account, _ = PlatformAccount.objects.update_or_create(
        user=user,
        platform="youtube",
        external_id=str(channel_id),
        defaults={
            "display_name": display_name,
            "profile_url": f"https://www.youtube.com/channel/{channel_id}",
            "meta": {},
        },
    )
    return account


def resolve_channel_account_for_user(user, channel_account_id: int) -> PlatformAccount | None:
    """
    Resolve channel_account_id to the user's YouTube PlatformAccount.

    Accepts PlatformAccount.id (canonical) or CreatorProfile.id (legacy clients).
    """
    account = PlatformAccount.objects.filter(
        id=channel_account_id, user=user, platform="youtube"
    ).first()
    if account:
        return account

    profile = CreatorProfile.objects.filter(id=channel_account_id, user=user).first()
    if profile:
        return ensure_youtube_platform_account(user)

    return None


def user_has_youtube_connection(user, account: PlatformAccount) -> bool:
    has_youtube_token = YoutubeCredentials.objects.filter(
        profile__user=user,
        platform=PlatformChoices.YOUTUBE,
        access_token__isnull=False,
    ).exclude(access_token="").exists()
    has_youtube_link = bool(getattr(account, "profile_url", None)) or bool(
        getattr(user, "youtube_link", None)
    )
    return has_youtube_token or has_youtube_link


def _youtube_channel_id_from_link(link: str) -> str | None:
    link = (link or "").strip()
    if not link:
        return None
    marker = "/channel/"
    if marker in link:
        tail = link.split(marker, 1)[1]
        return tail.split("/", 1)[0] or None
    return None
