from django.utils import timezone
from rest_framework.permissions import BasePermission

from .models import Playlist
from apps.payment_stripe.models import Subscription


def has_valid_paid_subscription(user):
    """
    Returns True if the user currently has an active paid subscription.
    A cancelled subscription remains valid until current_period_end.
    """
    try:
        sub = Subscription.objects.get(user=user)
    except Subscription.DoesNotExist:
        return False

    # Only paid packages
    if sub.package not in ["package-1", "package-2"]:
        return False

    # Subscription is valid until expiry date
    if sub.current_period_end:
        return sub.current_period_end > timezone.now()

    # Fallback if current_period_end is unavailable
    return sub.is_active


class HasPaidSubscription(BasePermission):
    message = "A valid paid subscription is required."

    def has_permission(self, request, view):
        return has_valid_paid_subscription(request.user)


class PlaylistGenerationPermission(BasePermission):
    message = (
        "You have reached the free playlist generation limit. "
        "Purchase a subscription package to continue generating playlists."
    )

    def has_permission(self, request, view):
        # Paid users have unlimited playlists
        if has_valid_paid_subscription(request.user):
            return True

        # Free users are allowed one successfully generated playlist
        successful_playlist_count = Playlist.objects.filter(
            user=request.user,
            status="completed",      # Change this if your success status differs
        ).count()

        return successful_playlist_count < 1