from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    SignupSerializer, LoginSerializer, ProfileSerializer, RoleSelectionSerializer,
    PasswordResetRequestSerializer, PasswordResetChangeSerializer, ChangePasswordSerializer,
    SignupOTPVerifySerializer, PasswordResetResendOTPSerializer
)
from rest_framework import generics
User = get_user_model()

from django.db import transaction
from django.core.files.base import ContentFile
from urllib.parse import urlparse
import requests
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Error








# ===== Helper Function =====
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"success": True, "message": message, "status": status_code, "data": data or []},
            status=status_code
        )

    def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"success": False, "message": message, "status": status_code, "data": data or []},
            status=status_code
        )


class PlatformAccountListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.viral_builder.models import PlatformAccount
        from .serializers import PlatformAccountSerializer

        accounts = PlatformAccount.objects.filter(user=request.user).order_by("created_at")
        data = PlatformAccountSerializer(accounts, many=True).data
        return Response(
            {"success": True, "message": "Platform accounts fetched", "status": 200, "data": data},
            status=status.HTTP_200_OK,
        )


def _upsert_platform_account(user, platform: str, external_id: str | None, display_name: str | None = None, profile_url: str | None = None, meta: dict | None = None):
    """
    Best-effort helper to create/update PlatformAccount on OAuth connect.
    """
    if not external_id:
        return

    from apps.viral_builder.models import PlatformAccount

    defaults = {
        "display_name": display_name or "",
        "profile_url": profile_url or "",
        "meta": meta or {},
    }

    account, _ = PlatformAccount.objects.update_or_create(
        user=user,
        platform=platform,
        external_id=str(external_id),
        defaults=defaults,
    )
    return account


def _fetch_youtube_channel_profile(access_token: str) -> dict:
    """
    Fetch YouTube channel profile for the authenticated user (mine=true).
    """
    try:
        import requests

        res = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet,statistics,topicDetails", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        data = res.json()
        items = data.get("items") or []
        if res.status_code >= 400 or not items:
            return {}

        item = items[0]
        snippet = item.get("snippet") or {}
        stats = item.get("statistics") or {}
        channel_id = item.get("id")
        title = snippet.get("title") or ""
        description = snippet.get("description") or ""
        thumbnails = snippet.get("thumbnails") or {}
        topic_categories = (item.get("topicDetails") or {}).get("topicCategories") or []
        category = "Unknown"
        if topic_categories:
            category = topic_categories[0].split("/")[-1].replace("_", " ").title()
        profile = thumbnails.get("high") or thumbnails.get("default") or {}
        return {
            "channel_id": channel_id,
            "title": title,
            "description": description,
            "profile_url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else "",
            "thumbnail": profile.get("url"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "category": category,
        }
    except Exception:
        return {}


def _fetch_youtube_competitors(access_token: str, channel_profile: dict, limit: int = 5) -> list:
    """
    Fetch competitor channels related to the connected channel's niche/category.
    """
    try:
        own_channel_id = channel_profile.get("channel_id")
        api_key = getattr(settings, "YOUTUBE_API_KEY", None) or os.environ.get("YOUTUBE_API_KEY")
        headers = {"Authorization": f"Bearer {access_token}"} if access_token and not api_key else {}

        description = channel_profile.get("description", "") or ""
        description_terms = " ".join(description.split()[:12]).strip()
        queries = []

        primary_query = " ".join(
            part for part in [channel_profile.get("title", ""), channel_profile.get("category", "")]
            if part and part != "Unknown"
        ).strip()
        if primary_query:
            queries.append(primary_query)
        if channel_profile.get("title"):
            queries.append(channel_profile.get("title", ""))
        if channel_profile.get("category") and channel_profile.get("category") != "Unknown":
            queries.append(channel_profile.get("category", ""))
        if description_terms:
            queries.append(description_terms)
        if channel_profile.get("title") and description_terms:
            queries.append(f"{channel_profile.get('title', '')} {description_terms}".strip())
        queries.append("youtube creators")

        channel_ids = []
        seen_queries = set()
        for query in queries:
            normalized_query = (query or "").strip()
            if not normalized_query or normalized_query in seen_queries:
                continue
            seen_queries.add(normalized_query)

            params = {
                "part": "snippet",
                "q": normalized_query,
                "type": "channel",
                "maxResults": 20,
                "order": "relevance",
            }
            if api_key:
                params["key"] = api_key

            search_res = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                headers=headers,
                timeout=20,
            )
            search_data = search_res.json()
            if search_res.status_code >= 400:
                continue

            for item in search_data.get("items") or []:
                channel_id = (item.get("snippet") or {}).get("channelId")
                if not channel_id or channel_id == own_channel_id or channel_id in channel_ids:
                    continue
                channel_ids.append(channel_id)
                if len(channel_ids) >= 15:
                    break

            if len(channel_ids) >= limit:
                break

        if not channel_ids:
            return []

        channel_params = {
            "part": "snippet,statistics,topicDetails",
            "id": ",".join(channel_ids),
        }
        if api_key:
            channel_params["key"] = api_key

        channels_res = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params=channel_params,
            headers=headers,
            timeout=20,
        )
        channels_data = channels_res.json()
        if channels_res.status_code >= 400:
            return []

        competitors = []
        for item in channels_data.get("items") or []:
            competitor_channel_id = item.get("id")
            if not competitor_channel_id or competitor_channel_id == own_channel_id:
                continue

            snippet = item.get("snippet") or {}
            stats = item.get("statistics") or {}
            thumbs = snippet.get("thumbnails") or {}
            profile_pic = (thumbs.get("high") or thumbs.get("default") or {}).get("url")

            topic_categories = (item.get("topicDetails") or {}).get("topicCategories") or []
            competitor_category = "Unknown"
            if topic_categories:
                competitor_category = topic_categories[0].split("/")[-1].replace("_", " ").title()

            competitors.append(
                {
                    "channel_id": competitor_channel_id,
                    "channel_name": snippet.get("title", ""),
                    "channel_url": f"https://www.youtube.com/channel/{competitor_channel_id}",
                    "profile_pic": profile_pic,
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "category": competitor_category,
                }
            )

            if len(competitors) >= limit:
                break

        return competitors
    except Exception:
        return []


def _fetch_youtube_channel_stats(access_token: str) -> dict:
    """
    Fetch YouTube channel statistics including subscriber count, view count, video count.
    """
    try:
        import requests

        res = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics,snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        data = res.json()
        items = data.get("items") or []
        if res.status_code >= 400 or not items:
            return {}

        item = items[0]
        stats = item.get("statistics") or {}
        snippet = item.get("snippet") or {}
        
        return {
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "channel_title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
        }
    except Exception:
        return {}


def _fetch_youtube_recent_videos(access_token: str, max_results: int = 10) -> list:
    """
    Fetch recent videos from the authenticated user's YouTube channel.
    """
    try:
        import requests

        res = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "forMine": "true",
                "type": "video",
                "order": "date",
                "maxResults": max_results,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        data = res.json()
        items = data.get("items") or []
        if res.status_code >= 400:
            return []

        video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
        if not video_ids:
            return []

        # Fetch video statistics
        stats_res = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics,snippet",
                "id": ",".join(video_ids),
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        stats_data = stats_res.json()
        video_items = stats_data.get("items") or []

        videos = []
        for video in video_items:
            stats = video.get("statistics") or {}
            snippet = video.get("snippet") or {}
            thumbs = snippet.get("thumbnails") or {}
            best_thumb = thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}
            video_id = video.get("id")
            videos.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "thumbnail": best_thumb.get("url"),
                "video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "",
            })

        return videos
    except Exception:
        return []


def _calculate_youtube_ai_score(channel_stats: dict, recent_videos: list) -> dict:
    """
    Calculate an AI score based on YouTube channel performance metrics.
    Score is based on engagement rate, consistency, and growth indicators.
    """
    try:
        subscriber_count = channel_stats.get("subscriber_count", 0)
        view_count = channel_stats.get("view_count", 0)
        video_count = channel_stats.get("video_count", 0)

        if subscriber_count == 0 or video_count == 0:
            return {"ai_score": 0, "rating": "No Data", "metrics": {}}

        # Calculate average views per video
        avg_views_per_video = view_count / video_count if video_count > 0 else 0

        # Calculate engagement rate from recent videos
        total_engagement = 0
        total_views_recent = 0
        for video in recent_videos:
            views = video.get("view_count", 0)
            likes = video.get("like_count", 0)
            comments = video.get("comment_count", 0)
            total_views_recent += views
            total_engagement += likes + comments

        engagement_rate = (total_engagement / total_views_recent * 100) if total_views_recent > 0 else 0

        # Calculate view-to-subscriber ratio (indicates content quality)
        view_subscriber_ratio = (avg_views_per_video / subscriber_count * 100) if subscriber_count > 0 else 0

        # Scoring algorithm (out of 100)
        # 40% - Engagement rate (higher is better)
        # 30% - View-to-subscriber ratio (indicates loyal audience)
        # 30% - Content consistency (based on video count)

        engagement_score = min(engagement_rate * 10, 40)  # Max 40 points
        ratio_score = min(view_subscriber_ratio * 3, 30)  # Max 30 points
        consistency_score = min(video_count / 10, 30)  # Max 30 points (1 point per video, max 300 videos)

        total_score = engagement_score + ratio_score + consistency_score
        total_score = min(round(total_score), 100)  # Cap at 100

        # Determine rating
        if total_score >= 80:
            rating = "Excellent"
        elif total_score >= 60:
            rating = "Good"
        elif total_score >= 40:
            rating = "Average"
        elif total_score >= 20:
            rating = "Below Average"
        else:
            rating = "Poor"

        return {
            "ai_score": total_score,
            "rating": rating,
            "metrics": {
                "engagement_rate": round(engagement_rate, 2),
                "avg_views_per_video": int(avg_views_per_video),
                "view_subscriber_ratio": round(view_subscriber_ratio, 2),
                "engagement_score": round(engagement_score, 1),
                "ratio_score": round(ratio_score, 1),
                "consistency_score": round(consistency_score, 1),
            }
        }
    except Exception:
        return {"ai_score": 0, "rating": "Error", "metrics": {}}

# ===== Signup =====
class SignupView(BaseAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return self.success_response(
                "User created successfully. Please verify OTP.",
                data={"email": user.email}
            )
        return self.error_response("Signup failed.", data=serializer.errors)

class SignupOTPVerifyView(BaseAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupOTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Invalid data.", data=serializer.errors)

        otp = serializer.validated_data.get("otp")
        email = serializer.validated_data.get("email")

        try:
            user = User.objects.get(email=email, otp=otp, otp_exp__gte=timezone.now(), otp_verified=False)
        except User.DoesNotExist:
            return self.error_response("Invalid or expired OTP.")

        # Verify OTP and set user role
        user.otp_verified = True
        user.save()
        
        tokens = get_tokens_for_user(user)
        profile_data = ProfileSerializer(user, context={"request": request}).data

        return self.success_response(
            "OTP verified successfully.",
            data={"tokens": tokens, "profile": profile_data}
        )

class ChooseRoleAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RoleSelectionSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.user_type:
                return self.error_response("Role already selected.")
            serializer.update(user, serializer.validated_data)
            return self.success_response("Role selected successfully.")
        return self.error_response("Role Selection Failed", data=serializer.errors)





# ===== Login =====
class LoginView(BaseAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, email=email, password=password)
            if user:
                if not user.user_type:
                    return self.error_response(
                        "Please choose your role first.",
                        status_code=status.HTTP_403_FORBIDDEN
                    )

                tokens = get_tokens_for_user(user)
                profile_data = ProfileSerializer(user, context={"request": request}).data

                return self.success_response(
                    "Login successful",
                    data={
                        "tokens": tokens,
                        "profile": profile_data,
                    }
                )
            return self.error_response(
                "Invalid email or password",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        return self.error_response(
            "Login Failed",
            data=serializer.errors
        )








# ===== Profile =====
class ProfileView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        print("user: ",request.user)
        serializer = ProfileSerializer(request.user, context={'request': request})
        return self.success_response(data=serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return self.success_response("Profile updated", data=serializer.data)
        return self.error_response("Profile updated failed", data=serializer.errors)

# ===== Password Reset =====
class PasswordResetRequestAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return self.success_response("OTP sent to email.", data={"email": serializer.validated_data["email"]})
        return self.error_response("OTP sent failed", data=serializer.errors)
    

class PasswordResetResendOTPView(BaseAPIView):
    """
    POST /auth/password-reset/resend-otp/
    Re-sends the OTP for the password reset flow if the user lost it.
    """
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return self.success_response("Password reset OTP sent again to your email.")
        return self.error_response("Could not resend OTP.", data=serializer.errors)


class PasswordResetOTPVerifyView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        if not email:
            return self.error_response("Email is required")
        if not otp:
            return self.error_response("OTP is required.")

        try:
            user = User.objects.get(email=email, otp_exp__gte=timezone.now(), otp_verified=False)
        except User.DoesNotExist:
            return self.error_response("Invalid or expired OTP.")
        if user.otp == otp:
            user.otp_verified = True
            user.save()
            tokens = get_tokens_for_user(user)  # Access + Refresh token
            return self.success_response(
                "OTP verified successfully.",
                data={"tokens": tokens}
            )
        return self.error_response(
            message="Invalid OTP or expired OTP"
        )
        

class PasswordResetChangeAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetChangeSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.otp_verified = False
            request.user.otp = None
            request.user.otp_exp = None
            request.user.save()
            return self.success_response("Password reset successful.")
        return self.error_response("Password reset failed", data=serializer.errors)



class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        



# Authenticated endpoint: change current user's password with validation
class ChangePassword(BaseAPIView, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Password changed failed", data=serializer.errors)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return self.error_response("Old password does not match")

        user.set_password(new_password)
        user.save()
        return self.success_response("Password changed successfully")
    






# mapping content-type to extension (define somewhere central or keep this small mapping)
_CONTENTTYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

# Your ProfileSerializer should already exist
# from .serializers import ProfileSerializer

class GoogleLoginView(SocialLoginView, BaseAPIView):
    adapter_class = GoogleOAuth2Adapter
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Handle Google social login and return tokens + profile in the same
        response format as LoginView:
        {
          "success": True,
          "message": "Login successful",
          "status": 200,
          "data": {
            "tokens": { "refresh": "...", "access": "..." },
            "profile": { ...profile serializer data... }
          }
        }
        
        Request body should include:
        {
          "access_token": "google_access_token",
          "user_type": "parent" or "creator"  // Required for new users
        }
        """
        try:
            # Extract user_type from request
            user_type = request.data.get('user_type', '').strip()
            
            # Let dj-rest-auth / allauth handle the oauth flow (creates/attaches socialaccount)
            response = super().post(request, *args, **kwargs)

            user = getattr(self, "user", None)
            if user is None:
                return self.error_response(
                    "User not available after social login.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Safely read extra_data from socialaccount if available
            extra_data = {}
            try:
                sa = user.socialaccount_set.first()
                if sa:
                    extra_data = sa.extra_data or {}
            except Exception:
                extra_data = {}

            first_name = extra_data.get("given_name", "") or ""
            last_name = extra_data.get("family_name", "") or ""
            picture_url = extra_data.get("picture", None)

            combined_name = " ".join(filter(None, [first_name.strip(), last_name.strip()])).strip()
            if not combined_name:
                combined_name = extra_data.get("name") or user.name or user.email

            # Update user fields atomically
            with transaction.atomic():
                user.name = combined_name

                # Set user_type if provided and user doesn't have one yet
                if user_type and user_type in dict(User.USER_TYPE_CHOICES):
                    if not user.user_type:
                        user.user_type = user_type
                elif user_type and user_type not in dict(User.USER_TYPE_CHOICES):
                    # Invalid user_type provided
                    return self.error_response(
                        f"Invalid user_type. Must be one of: {', '.join([choice[0] for choice in User.USER_TYPE_CHOICES])}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                elif not user.user_type:
                    # New user without user_type - ask to provide it
                    return self.error_response(
                        "user_type is required for new users",
                        data={
                            "user_types": [{"value": choice[0], "label": choice[1]} for choice in User.USER_TYPE_CHOICES],
                            "user_id": user.id,
                            "email": user.email,
                            "name": user.name
                        },
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                # Download & save profile picture only if user doesn't already have one
                if picture_url and (not getattr(user, "profile_pic", None)):
                    try:
                        r = requests.get(picture_url, timeout=5)
                        if r.status_code == 200 and r.content:
                            content_type = r.headers.get("content-type", "").split(";")[0].lower()
                            ext = _CONTENTTYPE_TO_EXT.get(content_type)

                            # fallback: extract extension from URL path
                            if not ext:
                                path = urlparse(picture_url).path
                                if "." in path:
                                    guessed = path.split(".")[-1].lower()
                                    if guessed in ("jpg", "jpeg", "png", "gif", "webp"):
                                        ext = guessed

                            if not ext:
                                ext = "jpg"

                            filename = urlparse(picture_url).path.split("/")[-1] or f"profile_{user.pk}.{ext}"
                            if not filename.lower().endswith("." + ext):
                                filename = f"{filename}.{ext}"

                            user.profile_pic.save(filename, ContentFile(r.content), save=False)
                    except requests.RequestException:
                        # ignore image download errors so login isn't blocked
                        pass

                # clear OTP / mark verified to avoid blocking social users with OTP flow
                user.otp = None
                user.otp_exp = None
                user.otp_verified = True

                user.save()

            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            tokens = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

            # Use same ProfileSerializer as your LoginView / ProfileView
            profile_data = ProfileSerializer(user, context={"request": request}).data

            return self.success_response(
                "Login successful",
                data={
                    "tokens": tokens,
                    "profile": profile_data,
                }
            )

        except OAuth2Error as e:
            return self.error_response(
                "Failed to fetch Google user info. Token may be expired or invalid.",
                data={"detail": str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return self.error_response(
                "Unexpected error during social login.",
                data={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




import os
import secrets
from urllib.parse import urlencode
from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny

from .models import TikTokOAuthToken
from .serializers import TikTokCodeSerializer

import requests
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response



TIKTOK_AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USERINFO_URL = "https://open.tiktokapis.com/v2/user/info/"



DEFAULT_TIKTOK_SCOPES = (
    "user.info.basic,"
    "user.info.profile,"
    "user.info.stats,"
    "video.list"
)



class TikTokAuthURLView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_key = getattr(settings, "TIKTOK_CLIENT_KEY", None) or os.environ.get("TIKTOK_CLIENT_KEY")
        redirect_uri = getattr(settings, "TIKTOK_REDIRECT_URI", None) or os.environ.get("TIKTOK_REDIRECT_URI")

        if not client_key or not redirect_uri:
            return self.error_response("TikTok config missing (client key / redirect uri)")

        state = secrets.token_urlsafe(16)
        # চাইলে state cache করে রাখতে পারেন (security)
        cache.set(f"tiktok_oauth_state:{state}", True, timeout=10 * 60)

        params = {
            "client_key": client_key,
            "scope": DEFAULT_TIKTOK_SCOPES,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        auth_url = f"{TIKTOK_AUTHORIZE_URL}?{urlencode(params)}"
        return self.success_response("TikTok authorize url", data={"auth_url": auth_url, "state": state})





class TikTokCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    # TikTok redirects here via GET
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state", "")
        scopes = request.GET.get("scopes", "")
        if not code:
            return Response({"success": False, "message": "Missing code", "status": 400, "data": {}}, status=400)

        return Response(
            {"success": True, "message": "TikTok redirect OK", "status": 200, "data": {"code": code, "state": state, "scopes": scopes}},
            status=200
        )

        # return redirect("https://thesocialbillboard.com")

    # Your app calls this via POST (JWT required)
    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"success": False, "message": "Authentication required (JWT)", "status": 401, "data": {}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        code = request.data.get("code")
        state = request.data.get("state", "")

        if not code:
            return Response({"success": False, "message": "Missing code", "status": 400, "data": {}}, status=400)

        # optional state check
        if state and not cache.get(f"tiktok_oauth_state:{state}"):
            return Response({"success": False, "message": "Invalid/expired state", "status": 400, "data": {}}, status=400)

        client_key = getattr(settings, "TIKTOK_CLIENT_KEY", None) or os.environ.get("TIKTOK_CLIENT_KEY")
        client_secret = getattr(settings, "TIKTOK_CLIENT_SECRET", None) or os.environ.get("TIKTOK_CLIENT_SECRET")
        redirect_uri = getattr(settings, "TIKTOK_REDIRECT_URI", None) or os.environ.get("TIKTOK_REDIRECT_URI")

        if not client_key or not client_secret or not redirect_uri:
            return Response(
                {"success": False, "message": "TikTok config missing (client key/secret/redirect uri)", "status": 400, "data": {}},
                status=400
            )

        # 1) code -> token exchange
        try:
            token_res = requests.post(
                TIKTOK_TOKEN_URL,
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20,
            )
            token_json = token_res.json()
        except Exception as e:
            return Response({"success": False, "message": "Token request failed", "status": 500, "data": {"detail": str(e)}}, status=500)

        if token_res.status_code >= 400:
            return Response({"success": False, "message": "Token exchange failed", "status": token_res.status_code, "data": token_json}, status=token_res.status_code)

        token_data = token_json.get("data") or token_json
        access_token = token_data.get("access_token")
        if not access_token:
            return Response({"success": False, "message": "No access_token returned", "status": 400, "data": token_json}, status=400)

        # 2) user info fetch (basic)
        try:
            userinfo_res = requests.get(
                TIKTOK_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "open_id,union_id,avatar_url,avatar_url_100,avatar_large_url,"
                    "display_name,bio_description,profile_deep_link,is_verified,username,"
                    "follower_count,following_count,likes_count,video_count"},
                timeout=20,
            )
            userinfo_json = userinfo_res.json()
        except Exception as e:
            userinfo_json = {"detail": str(e)}

        # 3) save token to DB
        from .models import TikTokOAuthToken
        user_obj = (userinfo_json.get("data") or {}).get("user") or {}

        open_id = token_data.get("open_id") or user_obj.get("open_id")
        union_id = token_data.get("union_id") or user_obj.get("union_id")
        
        obj, _ = TikTokOAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                "open_id": open_id,
                "union_id": union_id,
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "refresh_expires_in": token_data.get("refresh_expires_in"),
                "scope": token_data.get("scope"),
                "token_type": token_data.get("token_type"),
            },
        )

        # Auto-create PlatformAccount (best effort)
        try:
            display_name = user_obj.get("display_name") or user_obj.get("username") or ""
            profile_url = user_obj.get("profile_deep_link") or ""
            _upsert_platform_account(
                request.user,
                "tiktok",
                open_id,
                display_name=display_name,
                profile_url=profile_url,
                meta={"union_id": union_id},
            )
        except Exception:
            pass

        return Response(
            {
                "success": True,
                "message": "TikTok connected successfully",
                "status": 200,
                "data": {
                    "tiktok": {"open_id": obj.open_id, "union_id": obj.union_id, "scope": obj.scope},
                    "tiktok_userinfo": userinfo_json,
                },
            },
            status=200,
        )







import os
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InstagramOAuthToken
from .serializers import InstagramCodeSerializer


# Instagram OAuth endpoints (common)
INSTAGRAM_AUTHORIZE_URL = "https://api.instagram.com/oauth/authorize"
INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"

# Long-lived token endpoints (commonly used in IG exchange flows)
IG_LONG_LIVED_EXCHANGE_URL = "https://graph.instagram.com/access_token"
IG_REFRESH_LONG_LIVED_URL = "https://graph.instagram.com/refresh_access_token"
IG_ME_URL = "https://graph.instagram.com/me"

# Permissions for Business/Creator insights + comments
# DEFAULT_IG_SCOPES = [
#     "instagram_basic",
#     "instagram_manage_insights",
#     # "instagram_manage_comments",
#     # add if you need publish: "instagram_content_publish"
# ]




DEFAULT_IG_SCOPES = [
    "instagram_business_basic",
    "instagram_business_manage_insights",
    "instagram_business_manage_comments",
    "instagram_business_manage_messages",
    "instagram_business_content_publish",
]



class InstagramAuthURLView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = getattr(settings, "INSTAGRAM_CLIENT_ID", None) or os.environ.get("INSTAGRAM_CLIENT_ID")
        redirect_uri = getattr(settings, "INSTAGRAM_REDIRECT_URI", None) or os.environ.get("INSTAGRAM_REDIRECT_URI")

        if not client_id or not redirect_uri:
            return Response(
                {"success": False, "message": "Instagram config missing (client id / redirect uri)", "status": 400, "data": {}},
                status=status.HTTP_400_BAD_REQUEST
            )

        state = secrets.token_urlsafe(16)
        cache.set(f"ig_oauth_state:{state}", True, timeout=10 * 60)

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(DEFAULT_IG_SCOPES),
            "state": state,
        }
        auth_url = f"{INSTAGRAM_AUTHORIZE_URL}?{urlencode(params)}"

        return Response(
            {"success": True, "message": "Instagram authorize url", "status": 200, "data": {"auth_url": auth_url, "state": state}},
            status=status.HTTP_200_OK
        )


class InstagramCallbackView(APIView):
    """
    GET: Instagram redirect hits here with ?code=...&state=...
    POST: Your app (frontend/postman) sends code with JWT → token exchange → save
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        err_code = request.GET.get("error_code")
        err_msg = request.GET.get("error_message") or request.GET.get("error_description")
        err = request.GET.get("error")

        # ✅ Meta error redirect
        if err_code or err_msg or err:
            return Response(
                {
                    "success": False,
                    "message": "Instagram/Facebook Login error",
                    "status": 400,
                    "data": {
                        "error": err,
                        "error_code": err_code,
                        "error_message": err_msg,
                    },
                },
                status=400,
            )

        code = request.GET.get("code")
        state = request.GET.get("state", "")
        if not code:
            return Response({"success": False, "message": "Missing code", "status": 400, "data": {}}, status=400)

        return Response({"success": True, "message": "Instagram redirect OK", "status": 200, "data": {"code": code, "state": state}}, status=200)

        # return redirect("https://thesocialbillboard.com")


    def post(self, request):
        # ✅ Must be logged in your app (JWT)
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"success": False, "message": "Authentication required (JWT)", "status": 401, "data": {}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        ser = InstagramCodeSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"success": False, "message": "Invalid payload", "status": 400, "data": ser.errors}, status=400)

        code = ser.validated_data["code"]
        state = ser.validated_data.get("state", "")

        # (optional) state check
        if state and not cache.get(f"ig_oauth_state:{state}"):
            return Response({"success": False, "message": "Invalid/expired state", "status": 400, "data": {}}, status=400)

        client_id = getattr(settings, "INSTAGRAM_CLIENT_ID", None) or os.environ.get("INSTAGRAM_CLIENT_ID")
        client_secret = getattr(settings, "INSTAGRAM_CLIENT_SECRET", None) or os.environ.get("INSTAGRAM_CLIENT_SECRET")
        redirect_uri = getattr(settings, "INSTAGRAM_REDIRECT_URI", None) or os.environ.get("INSTAGRAM_REDIRECT_URI")

        if not client_id or not client_secret or not redirect_uri:
            return Response(
                {"success": False, "message": "Instagram config missing (client id/secret/redirect uri)", "status": 400, "data": {}},
                status=400
            )

        # 1) code -> short-lived token (form-urlencoded)
        try:
            token_res = requests.post(
                INSTAGRAM_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                timeout=25,
            )
            token_json = token_res.json()
        except Exception as e:
            return Response({"success": False, "message": "Token request failed", "status": 500, "data": {"detail": str(e)}}, status=500)

        if token_res.status_code >= 400:
            return Response(
                {"success": False, "message": "Token exchange failed", "status": token_res.status_code, "data": token_json},
                status=token_res.status_code
            )

        short_access_token = token_json.get("access_token")
        ig_user_id = str(token_json.get("user_id")) if token_json.get("user_id") is not None else None
        if not short_access_token:
            return Response({"success": False, "message": "No access_token returned", "status": 400, "data": token_json}, status=400)

        # 2) try to exchange for long-lived token (best effort)
        access_token = short_access_token
        is_long_lived = False
        expires_in = None

        try:
            ll_res = requests.get(
                IG_LONG_LIVED_EXCHANGE_URL,
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": client_secret,
                    "access_token": short_access_token,
                },
                timeout=25,
            )
            ll_json = ll_res.json()
            if ll_res.status_code < 400 and ll_json.get("access_token"):
                access_token = ll_json["access_token"]
                expires_in = ll_json.get("expires_in")
                is_long_lived = True
        except Exception:
            # keep short token if exchange fails
            pass

        # 3) fetch me (best effort) to store username/id
        username = None
        try:
            me_res = requests.get(
                IG_ME_URL,
                params={"fields": "id,username", "access_token": access_token},
                timeout=20,
            )
            me_json = me_res.json()
            if me_res.status_code < 400:
                ig_user_id = ig_user_id or str(me_json.get("id") or "")
                username = me_json.get("username")
        except Exception:
            pass

        # 4) save token for this app user
        obj, _ = InstagramOAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                "instagram_user_id": ig_user_id,
                "username": username,
                "access_token": access_token,
                "token_type": token_json.get("token_type"),
                "scopes": ",".join(DEFAULT_IG_SCOPES),
                "is_long_lived": is_long_lived,
            },
        )
        obj.set_expiry_from_seconds(expires_in)
        obj.save(update_fields=["expires_in", "expires_at", "updated_at"])

        # Auto-create PlatformAccount (best effort)
        try:
            profile_url = f"https://www.instagram.com/{obj.username}/" if obj.username else ""
            _upsert_platform_account(
                request.user,
                "instagram",
                obj.instagram_user_id,
                display_name=obj.username or "",
                profile_url=profile_url,
                meta={"is_long_lived": obj.is_long_lived},
            )
        except Exception:
            pass

        return Response(
            {
                "success": True,
                "message": "Instagram connected successfully",
                "status": 200,
                "data": {
                    "instagram": {
                        "instagram_user_id": obj.instagram_user_id,
                        "username": obj.username,
                        "is_long_lived": obj.is_long_lived,
                        "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
                        "scopes": obj.scopes,
                    }
                },
            },
            status=200
        )





# views.py

import os
import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import YouTubeOAuthToken
from .serializers import YouTubeCodeSerializer

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Minimal scopes for reading YouTube channel/videos + login identity
DEFAULT_YT_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

class YouTubeAuthURLView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", None) or os.environ.get("GOOGLE_CLIENT_ID")
        redirect_uri = getattr(settings, "YOUTUBE_REDIRECT_URI", None) or os.environ.get("YOUTUBE_REDIRECT_URI")

        if not client_id or not redirect_uri:
            return Response(
                {"success": False, "message": "YouTube config missing (GOOGLE_CLIENT_ID / YOUTUBE_REDIRECT_URI)", "status": 400, "data": {}},
                status=400
            )

        state = secrets.token_urlsafe(16)
        cache.set(f"yt_oauth_state:{state}", True, timeout=10 * 60)

        params = {
            "state": state,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(DEFAULT_YT_SCOPES),
            # IMPORTANT: offline refresh token
            "access_type": "offline",
            "prompt": "consent",
            
        }
        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return Response({"success": True, "message": "YouTube authorize url", "status": 200, "data": {"auth_url": auth_url, "state": state}}, status=200)


class YouTubeCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    # Google redirects here via GET
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state", "")
        if not code:
            return Response({"success": False, "message": "Missing code", "status": 400, "data": {}}, status=400)

        frontend_callback_uri = getattr(settings, "YOUTUBE_FRONTEND_CALLBACK_URI", None) or os.environ.get("YOUTUBE_FRONTEND_CALLBACK_URI")

        if frontend_callback_uri:
            separator = "&" if "?" in frontend_callback_uri else "?"
            clean_frontend_url = f"{frontend_callback_uri}{separator}{urlencode({'success': 'true', 'state': state, 'code': code})}"
            return redirect(clean_frontend_url)

        return Response(
            {"success": True, "message": "YouTube redirect OK", "status": 200, "data": {"code": code, "state": state}},
            status=200
        )

        # return redirect("https://thesocialbillboard.com")


    # # Google redirects here via GET
    # def get(self, request):
    #     code = request.GET.get("code")
    #     state = request.GET.get("state", "")

    #     if not code:
    #         return Response(
    #             {"success": False, "message": "Missing code", "status": 400, "data": {}},
    #             status=400
    #         )

    #     # Frontend URL
    #     frontend_url = "https://thesocialbillboard.com/youtube/connect"
    #     # frontend_url = "http://localhost:5173/youtube/connect"

    #     # Redirect frontend with code + state
    #     return redirect(f"{frontend_url}?code={code}&state={state}")



    # Your app calls this via POST (JWT required)
    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"success": False, "message": "Authentication required (JWT)", "status": 401, "data": {}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = YouTubeCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "message": "Validation failed", "status": 400, "data": serializer.errors}, status=400)

        code = serializer.validated_data["code"]
        state = serializer.validated_data.get("state", "")

        # optional state check
        if state and not cache.get(f"yt_oauth_state:{state}"):
            return Response({"success": False, "message": "Invalid/expired state", "status": 400, "data": {}}, status=400)

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", None) or os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None) or os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = getattr(settings, "YOUTUBE_REDIRECT_URI", None) or os.environ.get("YOUTUBE_REDIRECT_URI")

        if not client_id or not client_secret or not redirect_uri:
            return Response(
                {"success": False, "message": "YouTube config missing (client id/secret/redirect uri)", "status": 400, "data": {}},
                status=400
            )

        # 1) code -> token exchange
        try:
            token_res = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=20,
            )
            token_json = token_res.json()
        except Exception as e:
            return Response({"success": False, "message": "Token request failed", "status": 500, "data": {"detail": str(e)}}, status=500)

        if token_res.status_code >= 400:
            return Response({"success": False, "message": "Token exchange failed", "status": token_res.status_code, "data": token_json}, status=token_res.status_code)

        access_token = token_json.get("access_token")
        if not access_token:
            return Response({"success": False, "message": "No access_token returned", "status": 400, "data": token_json}, status=400)

        # 2) user info (email/sub) fetch (optional but useful)
        userinfo = {}
        try:
            ui_res = requests.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15
            )
            userinfo = ui_res.json() if ui_res.status_code < 400 else {}
        except Exception:
            userinfo = {}

        # 3) save token to DB
        obj, _ = YouTubeOAuthToken.objects.update_or_create(
            user=request.user,
            defaults={
                "google_sub": userinfo.get("sub"),
                "email": userinfo.get("email"),
                "access_token": token_json.get("access_token"),
                # refresh_token only comes first time or when prompt=consent
                "refresh_token": token_json.get("refresh_token") or (getattr(getattr(request.user, "youtube_oauth", None), "refresh_token", None)),
                "scope": token_json.get("scope"),
                "token_type": token_json.get("token_type"),
                "expires_in": token_json.get("expires_in"),
            },
        )
        obj.set_expiry_from_seconds(token_json.get("expires_in"))
        obj.save()

        # Auto-create PlatformAccount (required for downstream features like Viral Builder)
        profile = _fetch_youtube_channel_profile(access_token)
        channel_id = profile.get("channel_id")
        if not channel_id:
            return Response(
                {
                    "success": False,
                    "message": "YouTube connected, but no channel found for this Google account.",
                    "status": 400,
                    "data": {
                        "hint": "Open YouTube with this Google account and create/select a channel, then reconnect.",
                        "google_email": userinfo.get("email"),
                    },
                },
                status=400,
            )

        try:
            platform_account = _upsert_platform_account(
                request.user,
                "youtube",
                channel_id,
                display_name=profile.get("title") or "",
                profile_url=profile.get("profile_url") or "",
                meta={"thumbnail": profile.get("thumbnail")},
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": "YouTube token saved, but failed to link channel account.",
                    "status": 500,
                    "data": {"detail": str(e)},
                },
                status=500,
            )

        # Fetch YouTube analytics data
        channel_stats = _fetch_youtube_channel_stats(access_token)
        recent_videos = _fetch_youtube_recent_videos(access_token, max_results=10)
        competitor_channels = _fetch_youtube_competitors(access_token, profile, limit=5)
        ai_score_data = _calculate_youtube_ai_score(channel_stats, recent_videos)

        top_videos = sorted(recent_videos, key=lambda x: x.get("view_count", 0), reverse=True)[:5]

        # Prepare chart data for frontend
        video_performance_chart = [
            {
                "title": video.get("title", "")[:30] + "..." if len(video.get("title", "")) > 30 else video.get("title", ""),
                "video_id": video.get("video_id", ""),
                "video_url": video.get("video_url", ""),
                "thumbnail": video.get("thumbnail", ""),
                "views": video.get("view_count", 0),
                "likes": video.get("like_count", 0),
                "comments": video.get("comment_count", 0),
                "engagement_rate": round(
                    ((video.get("like_count", 0) + video.get("comment_count", 0)) / video.get("view_count", 1)) * 100, 2
                ) if video.get("view_count", 0) > 0 else 0,
            }
            for video in top_videos
        ]

        # Engagement metrics chart data
        engagement_metrics = {
            "total_views": channel_stats.get("view_count", 0),
            "total_subscribers": channel_stats.get("subscriber_count", 0),
            "total_videos": channel_stats.get("video_count", 0),
            "avg_views_per_video": ai_score_data.get("metrics", {}).get("avg_views_per_video", 0),
            "engagement_rate": ai_score_data.get("metrics", {}).get("engagement_rate", 0),
        }

        # Growth rate calculation (mock data - you can enhance this with YouTube Analytics API)
        growth_rate = "+12.8%"  # This would come from comparing current vs previous period

        return Response(
            {
                "success": True,
                "message": "YouTube connected successfully",
                "status": 200,
                "data": {
                    "youtube": {"email": obj.email, "scope": obj.scope},
                    "channel_account": {
                        "id": platform_account.id if platform_account else None,
                        "channel_account_id": platform_account.id if platform_account else None,
                        "platform": "youtube",
                        "external_id": channel_id,
                        "display_name": profile.get("title") or "",
                        "profile_url": profile.get("profile_url") or "",
                        "channel_id": profile.get("channel_id"),
                        "channel_url": profile.get("profile_url") or "",
                        "profile_pic": profile.get("thumbnail"),
                        "subscribers": profile.get("subscriber_count", 0),
                        "category": profile.get("category", "Unknown"),
                    },
                    "competitors": competitor_channels,
                    "google_userinfo": userinfo,
                    # Analytics Dashboard Data
                    "analytics": {
                        "total_subscribers": channel_stats.get("subscriber_count", 0),
                        "total_views": channel_stats.get("view_count", 0),
                        "total_videos": channel_stats.get("video_count", 0),
                        "growth_rate": growth_rate,
                        "ai_score": ai_score_data.get("ai_score", 0),
                        "ai_rating": ai_score_data.get("rating", "N/A"),
                    },
                    # Chart Data
                    "charts": {
                        "video_performance": video_performance_chart,
                        "engagement_metrics": engagement_metrics,
                        "ai_score_breakdown": ai_score_data.get("metrics", {}),
                    },
                },
            },
            status=200
        )


import os
import requests
from django.conf import settings
from django.utils import timezone

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

def refresh_youtube_access_token(youtube_token_obj: YouTubeOAuthToken) -> YouTubeOAuthToken:
    """
    Use refresh_token to get a fresh access_token (required for Celery jobs).
    """
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", None) or os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None) or os.environ.get("GOOGLE_CLIENT_SECRET")

    if not youtube_token_obj.refresh_token:
        raise Exception("No refresh_token stored. Reconnect YouTube with prompt=consent.")

    res = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": youtube_token_obj.refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    data = res.json()
    if res.status_code >= 400:
        raise Exception(f"Refresh token failed: {data}")

    youtube_token_obj.access_token = data.get("access_token")
    youtube_token_obj.token_type = data.get("token_type") or youtube_token_obj.token_type
    youtube_token_obj.expires_in = data.get("expires_in")
    youtube_token_obj.expires_at = timezone.now() + timezone.timedelta(seconds=int(data.get("expires_in") or 0))
    youtube_token_obj.save(update_fields=["access_token", "token_type", "expires_in", "expires_at", "updated_at"])
    return youtube_token_obj






class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete() # For Permanent Delete
        # user.is_active = False  # For Soft delete
        # user.email = f"deleted_{user.id}_{user.email}" # For Soft delete
        # user.save() # For Soft delete
        return Response({"message": "Your account has been deleted."}, status=status.HTTP_200_OK)