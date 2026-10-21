# core/views.py

from asyncio.log import logger
import datetime
from io import BytesIO
from time import timezone
from django.http import HttpResponse
import requests
from django.conf import settings
from datetime import datetime, timedelta
import calendar
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.dashboard.service.monthly_aggregate import get_monthly_views_for_user
from apps.dashboard.youtube_utils import analyze_youtube_data_with_openai, extract_youtube_channel_id, fetch_youtube_channel_data, fetch_youtube_recent_videos, fetch_youtube_video_stats
from apps.your_competitor.views import extract_channel_id
RAPIDAPI_KEY = settings.RAPIDAPI_KEY
RAPIDAPI_HOST = settings.RAPIDAPI_HOST
# from apps.dashboard.social_utils import fetch_youtube_video_data
from rest_framework.views import APIView
from rest_framework.response import Response
from .instagram_utils import *
from apps.creators_explore.models import Creator
from apps.dashboard.serializers import *
from apps.dashboard.tiktok_utils import *
# from .utils import *
from apps.creator_dashboard.models import YoutubeProfile
from apps.users.views import BaseAPIView
from django.conf import settings
from .tiktok_utils import *
from datetime import datetime
from apps.dashboard.instagram_utils import analyze_instagram_data_with_openai
# from apps.dashboard.utils import parse_percentage
# Updated Social Media added and fetch store imiditately after user add youtube link 
class UpdateSocialLinksView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        user = request.user
        old_link = user.youtube_link  # ✅ keep track of old youtube link

        serializer = UserSocialLinkSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user.refresh_from_db()
            # ✅new logic: if youtube_link added or changed → run competitor fetch
            if user.youtube_link and user.youtube_link != old_link:
                from apps.your_competitor.views import fetch_competitors_for_user
                # from apps.your_competitor.views import fetch_competitors_for_user
                fetch_competitors_for_user(user.id)
                print("Fun Callde")
                return self.success_response(
                    message="Social links updated and competitors fetched successfully",
                    data=serializer.data,
                    status_code=status.HTTP_200_OK
                )
            print("No Fun Callde")
            return self.success_response(
                message="Social links updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return self.error_response(
            message="Validation failed",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

# youtuber analysis
# from .youtube_utils import *



class YouTubeAnalyzerAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        url = request.query_params.get("url") or getattr(request.user, "youtube_link", None)

        if not url:
            return Response(
                {"success": False, "message": "Missing YouTube link for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        identifier = extract_youtube_channel_id(url)
        if not identifier:
            return Response(
                {"success": False, "message": "Invalid YouTube URL format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1. Fetch channel data
            channel_data = fetch_youtube_channel_data(identifier)
            if not channel_data:
                return Response(
                    {"success": False, "message": "Could not retrieve YouTube channel data."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 2. Analyze with OpenAI
            ai_analysis = analyze_youtube_data_with_openai(channel_data)
            # print("AI Analysis:", ai_analysis)
            # 3. Save or update in Creator model
            name = request.user.name or channel_data["title"]

            subscribers = channel_data["stats"].get("subscriber_count", "0")
            engagement = parse_percentage(ai_analysis.get("engagement_rate"))
            growth = parse_percentage(ai_analysis.get("growth_str", "+0%"))

            creator_obj, created = Creator.objects.update_or_create(
                platform="youtube",
                defaults={
                    "name": name,
                    "subscribers": subscribers,
                    "engagement": engagement,
                    "growth": growth,
                    "ai_score": round(ai_analysis.get("ai_score", 0), 1)

                }
            )


            response_data = {
                "success": True,
                "data": {
                    "id": None,  # Since no DB save, id is None
                    "name": channel_data.get("title", ""),
                    "platform": "YouTube",
                    "subscribers": channel_data["stats"].get("subscriber_count", 0),
                    "engagement": f"{ai_analysis.get('engagement_rate', 0)}%",
                    "growth": f"{ai_analysis.get('growth_rate', 0)}%",
                    "score": ai_analysis.get("ai_score", 0),
                    "ai_analysis": ai_analysis,

                    # --- Extra AI metrics ---
                    "performance_overview": ai_analysis.get("performance_overview", 0),
                    "platform_breakdown": ai_analysis.get("platform_breakdown", [{
                        "platform": "YouTube",
                        "subscribers": channel_data["stats"].get("subscriber_count", 0),
                        "ai_score": ai_analysis.get("ai_score", 0)
                    }])
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class TikTokAnalyzerAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # ✅ Always read TikTok link from user profile
        url = getattr(request.user, "tiktok_link", None)

        if not url:
            return Response(
                {"success": False, "message": "TikTok link not found in user profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Extract username from TikTok URL
        username_info = extract_username(url=url)
        if not username_info or username_info.get("platform") != "tiktok":
            return Response(
                {"success": False, "message": "Invalid TikTok URL format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = username_info["username"]

        try:
            # ✅ Fetch TikTok data
            tiktok_data = fetch_tiktok_user_info(username)
            if not tiktok_data or "error" in tiktok_data:
                return Response(
                    {"success": False, "message": "Could not retrieve TikTok user data."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # ✅ AI Analysis
            openai_analysis = analyze_tiktok_data_with_openai(tiktok_data)

            # ✅ Save or update Creator data
            creator_obj, created = Creator.objects.update_or_create(
                name=request.user.name,
                platform="tiktok",
                defaults={
                    "subscribers": str(tiktok_data.get("follower_count", "0")),
                    "engagement": f"{openai_analysis.get('engagement_rate', 0)}%",
                    "growth": f"+{openai_analysis.get('activity_level', 0)}%",
                    "ai_score": openai_analysis.get("ai_score", 0.0),
                    "profile_image": tiktok_data.get("profile_pic", ""),
                },
            )

            # ✅ Response — combines model data + fetched TikTok stats
            return Response({
                "success": True,
                "data": {
                    "id": creator_obj.id,
                    "name": creator_obj.name,
                    "platform": creator_obj.platform,
                    "profile_image": creator_obj.profile_image,

                    # Raw TikTok stats
                    "subscribers": tiktok_data.get("follower_count", 0),
                    "following": tiktok_data.get("following_count", 0),
                    "likes": tiktok_data.get("like_count", 0),
                    "videos": tiktok_data.get("video_count", 0),
                    "total_views": tiktok_data.get("total_view_count", 0),
                    "comments": tiktok_data.get("total_comment_count", 0),
                    "shares": tiktok_data.get("total_share_count", 0),

                    # Computed + AI data
                    "engagement": f"{openai_analysis.get('engagement_rate', 0)}%",
                    "growth": f"+{openai_analysis.get('activity_level', 0)}%",
                    "score": creator_obj.score(),
                    "created": created,
                    "ai_analysis": openai_analysis,
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"success": False, "message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# instagram analysis
class InstagramAnalyticsAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        url = request.query_params.get("url") or getattr(request.user, "instagram_link", None)
        if not url:
            return Response(
                {"success": False, "message": "Missing Instagram link."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract username from profile link
        username_info = extract_username(url=url)
        if not username_info or username_info.get("platform") != "instagram":
            return Response(
                {"success": False, "message": "Invalid Instagram URL format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = username_info["username"]

        try:
            # Fetch Instagram data from RapidAPI
            insta_data = fetch_instagram_user_info(username)
            if not insta_data or "error" in insta_data:
                return Response(
                    {"success": False, "message": "Could not retrieve Instagram user data."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # AI-based Analysis
            openai_analysis = analyze_instagram_data_with_openai(insta_data)
            ai_score = openai_analysis.get("ai_score", 0.0)
            # Save or Update Creator object in DB
            creator_obj, created = Creator.objects.update_or_create(
                name=request.user.name,
                platform="instagram",
                defaults={
                    "subscribers": insta_data.get("follower_count", "0"),
                    "engagement": f"{openai_analysis.get('engagement_rate', 0)}%",
                    "growth": f"+{openai_analysis.get('activity_level', 0)}%",
                    "ai_score": ai_score,
                    "profile_image": insta_data.get("profile_pic_url", ""),
                }
            )
            openai_analysis["ai_score"] = ai_score

            # Customised API Response
            return Response({
                            "success": True,
                            "data": {
                                "id": creator_obj.id,
                                "name": creator_obj.name,
                                "platform": creator_obj.platform,
                                "profile_image": creator_obj.profile_image,

                                # ✅ Use insta_data (fetched values)
                                "subscribers": insta_data.get("follower_count", 0),
                                "following": insta_data.get("following_count", 0),
                                "likes": insta_data.get("like_count", 0),
                                "posts": insta_data.get("post_count", 0),

                                # ✅ Stored fields from your model
                                "engagement": creator_obj.engagement,
                                "growth": creator_obj.growth,
                                "overall score": creator_obj.score(),
                                "created": created,

                                # ✅ Extra profile info
                                "username": insta_data.get("username"),
                                "full_name": insta_data.get("full_name"),
                                "bio": insta_data.get("bio"),
                                "profile_pic_url": insta_data.get("profile_pic_url"),
                                "is_verified": insta_data.get("is_verified"),
                                "is_private": insta_data.get("is_private"),
                                "category": insta_data.get("category_name"),
                                "external_url": insta_data.get("external_url"),

                                # ✅ AI Analysis
                                "ai_analysis": openai_analysis,
                            },
                        }, status=status.HTTP_200_OK)


        except Exception as e:
            return Response(
                {"success": False, "message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def _format_creator_subs(val):
    if not val:
        return "0"
    if val >= 1_000_000:
        return f"{val/1_000_000:.1f}M"
    if val >= 1000:
        return f"{val/1000:.1f}K"
    return str(val)


def _creator_ranking_metrics(item):
    engagement = item.engagement_rate or 0.0
    growth = item.growth_rate or 0.0
    subs = item.total_subscribers or 0
    ai_score = round(min(10.0, 1.0 + (subs / 100_000) * 0.4 + engagement * 0.4 + growth * 0.2), 2)
    return engagement, growth, subs, ai_score


def get_current_user_rank(user):
    """Return the authenticated user's leaderboard rank and stats."""
    from apps.creator_dashboard_leaderboard.service import get_leaderboard_data

    try:
        leaderboard = list(get_leaderboard_data(platform=None))
    except Exception:
        leaderboard = []

    profile = next((item for item in leaderboard if item.user_id == user.id), None)
    if not profile:
        return {
            "rank": "N/A",
            "subscribers": "0",
            "engagement": "0%",
            "growth": "0%",
            "profile_image": "",
            "ai_score": 0,
        }

    engagement, growth, subs, ai_score = _creator_ranking_metrics(profile)
    profile_image = profile.user.profile_pic.url if profile.user.profile_pic else ""

    return {
        "rank": getattr(profile, "rank", "N/A"),
        "subscribers": _format_creator_subs(subs),
        "engagement": f"{round(engagement, 1)}%",
        "growth": f"+{round(growth, 1)}%" if growth >= 0 else f"{round(growth, 1)}%",
        "profile_image": profile_image,
        "ai_score": ai_score,
    }


TOP_RANK_CREATORS_LIMIT = 10


# Helper function to get top creators
def get_top_creators():
    """Helper function: returns top 10 unique creators using get_leaderboard_data"""
    from apps.creator_dashboard_leaderboard.service import get_leaderboard_data

    try:
        queryset = list(get_leaderboard_data(platform=None))[:TOP_RANK_CREATORS_LIMIT]
    except Exception:
        queryset = []

    data = []
    for item in queryset:
        profile_image = item.user.profile_pic.url if item.user.profile_pic else ""
        # 1. Safely grab the related profile object if it exists (returns None if missing)
        yt_profile = getattr(item, 'youtube_profile', None)
    
        # 2. Extract the ID safely without crashing
        channel_id = yt_profile.youtube_channel_id if yt_profile else ""
        engagement, growth, subs, ai_score = _creator_ranking_metrics(item)

        data.append({
            "rank": item.rank,
            "creator": item.user.name,
            "channel_id":channel_id,
            "platform": str(item.platform).title(),
            "subscribers": _format_creator_subs(subs),
            "engagement": f"{round(engagement, 1)}%",
            "growth": f"+{round(growth, 1)}%" if growth >= 0 else f"{round(growth, 1)}%",
            "profile_image": profile_image,
            "ai_score": ai_score,
        })
    return data



class CreatorRankingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    """JSON API"""
    def get(self, request, *args, **kwargs):
        
        return Response({
            "top_creators": get_top_creators(),
            "current_user_rank": get_current_user_rank(request.user),
        })



from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
class CreatorRankingDownloadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    """PDF Download API"""
    def get(self, request, *args, **kwargs):
        data = get_top_creators()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("Top 10 Creators Ranking", styles["Title"]))
        elements.append(Spacer(1, 12))

        # Table header
        table_data = [["Rank", "Creator", "Platform", "Subscribers", "Engagement", "Growth", "AI Score"]]

        # Table rows
        for d in data:
            table_data.append([
                d["rank"],
                d["creator"],
                d["platform"],
                d["subscribers"],
                d["engagement"],
                d["growth"],
                d["ai_score"],
            ])

        table = Table(table_data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="top_creators.pdf"'
        return response


from datetime import datetime, timedelta, timezone
def parse_percentage(val):
    try:
        if isinstance(val, str):
            val = val.replace("%", "").replace("+", "").replace("-", "").strip()
            return float(val) / 100
        elif isinstance(val, (int, float)):
            return float(val)
    except Exception as e:
        logger.warning(f"Error parsing percentage '{val}': {e}")
    return 0.0


def parse_range_to_dates(range_key: str):
    """Return (start_datetime, end_datetime). end is now (UTC)."""
    now = datetime.now(timezone.utc)
    if not range_key or range_key in ("30d", "30"):
        start = now - timedelta(days=30)
    elif range_key in ("7d", "7"):
        start = now - timedelta(days=7)
    elif range_key in ("90d", "90"):
        start = now - timedelta(days=90)
    elif range_key in ("all", "0", "alltime"):
        start = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        # default 30d
        start = now - timedelta(days=30)
    return start, now

def parse_iso_datetime(s):
    """Robust ISO -> datetime with UTC tzinfo. Handles trailing Z."""
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        try:
            # last resort: parse without timezone
            return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def top_n_content_from_items(items, n=4):
    """
    items: list of dicts with keys: title, views, likes, comments, published_at, thumbnail, url, platform
    return top n sorted by views (safe).
    """
    items_clean = []
    for it in items:
        try:
            views = int(it.get("views", 0) or 0)
        except:
            views = 0
        items_clean.append({**it, "views": views})
    items_sorted = sorted(items_clean, key=lambda x: x["views"], reverse=True)
    return items_sorted[:n]

# ----------------- Fallback AI Scorer (production-grade) -----------------

def fallback_ai_score(engagement_percent: float, activity_level: float, followers: int) -> float:
    """
    engagement_percent: already in percent (e.g., 4.5)
    activity_level: posts per 1k followers or similar normalized metric
    followers: integer
    Returns score 2.0 - 8.5 (0-10 internal scale mapped later by callers if needed)
    """
    # safety
    try:
        eng = float(engagement_percent)
    except Exception:
        eng = 0.0
    try:
        act = float(activity_level)
    except Exception:
        act = 0.0
    try:
        fol = float(followers)
    except Exception:
        fol = 0.0

    # Normalize extremes
    eng = min(eng, 25.0)         # cap engagement to 25%
    act = min(act, 20.0)         # cap activity to 20 (posts/1k)
    fol_norm = min(fol / 500000.0, 1.0)

    score = (
        (eng / 2.0) * 0.45 +   # engagement weight
        (act / 2.0) * 0.35 +   # activity weight
        (fol_norm * 10.0) * 0.20  # follower weight
    )

    score = max(2.0, min(score, 8.5))
    return round(score, 1)


# ----------------- Platform analyzers (hybrid AI + fallback) -----------------

def try_call_openai(prompt: str, schema=None, timeout_seconds=12):
    """
    Calls OpenAI and expects JSON-like response. Returns parsed dict or raises.
    We keep it small and strict to avoid long tokens.
    """
    try:
        # Using the same style you used earlier — adapt model and client if different
        resp = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a strict JSON generator. Output only JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=250,
            timeout=timeout_seconds,
        )
        body = resp.choices[0].message.content
        # ensure string
        if isinstance(body, dict):
            return body
        return json.loads(body)
    except Exception as e:
        # surface the exception to caller to decide fallback
        raise e

from .utils import generate_ai_insight, range_filter

# ------------------ INSIGHT PERFORMANCE API (OPTION-B AI ENGINE) ------------------

class InsightPerformanceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile_and_platform_profile(self, user, platform_name):
        from apps.creator_dashboard.models import CreatorProfile
        try:
            profile = CreatorProfile.objects.get(user=user)
        except CreatorProfile.DoesNotExist:
            return None, None

        if platform_name == "youtube":
            from apps.creator_dashboard.models import YoutubeProfile
            return profile, YoutubeProfile.objects.filter(profile=profile).first()
        elif platform_name == "tiktok":
            from apps.creator_dashboard.models import TiktokProfile
            return profile, TiktokProfile.objects.filter(profile=profile).first()
        elif platform_name == "instagram":
            from apps.creator_dashboard.models import InstagramProfile
            return profile, InstagramProfile.objects.filter(profile=profile).first()
        return profile, None

    def _youtube_insight(self, profile, yt_profile, range_key):
        from apps.creator_dashboard.models import YoutubeProfileMedia
        from django.db.models import Sum
        from datetime import timedelta
        from django.utils import timezone

        videos = YoutubeProfileMedia.objects.filter(profile=profile)
        
        # Apply range filtering
        now = timezone.now()
        if range_key == "7d":
            videos = videos.filter(created_at__gte=now - timedelta(days=7))
        elif range_key == "30d":
            videos = videos.filter(created_at__gte=now - timedelta(days=30))
        elif range_key == "90d":
            videos = videos.filter(created_at__gte=now - timedelta(days=90))

        post_count = videos.count()
        total_views = videos.aggregate(Sum('view_count'))['view_count__sum'] or 0
        total_likes = videos.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
        total_comments = videos.aggregate(Sum('comment_count'))['comment_count__sum'] or 0
        
        followers = yt_profile.subscribers_count
        avg_views = round(total_views / post_count, 2) if post_count > 0 else 0.0

        ai = generate_ai_insight("YouTube", followers, total_views, total_likes, total_comments, post_count, avg_views)
        if not ai:
            ai = {}

        # Top content
        top_items = []
        for v in videos.order_by('-view_count')[:4]:
            top_items.append({
                "id": v.video_id,
                "title": v.title,
                "views": v.view_count,
                "likes": v.likes_count,
                "comments": v.comment_count,
                "shares": v.share_count,
                "created_time": v.created_at.isoformat() if v.created_at else ""
            })

        return {
            "profile": {
                "name": yt_profile.channel_title or yt_profile.profile.user.name or "YouTube Channel",
                "platform": "YouTube",
                "followers": followers
            },
            "performance_overview": {
                "engagement_rate": ai.get("engagement_rate", 0.0),
                "new_followers": int(followers * (ai.get("growth_rate", 0.0) / 100.0)),
                "posts": post_count,
                "avg_view_per_post": ai.get("avg_views_per_post", avg_views),
                "ai_score": ai.get("ai_score", 0.0),
                "growth_rate": ai.get("growth_rate", 0.0),
            },
            "top_content": top_items,
            "growth_suggestions": ai.get("growth_suggestions", []),
        }

    def _tiktok_insight(self, profile, tt_profile, range_key):
        from apps.creator_dashboard.models import TiktokProfileMedia
        from django.db.models import Sum
        from datetime import timedelta
        from django.utils import timezone

        videos = TiktokProfileMedia.objects.filter(profile=profile)
        
        # Apply range filtering
        now = timezone.now()
        if range_key == "7d":
            videos = videos.filter(created_at__gte=now - timedelta(days=7))
        elif range_key == "30d":
            videos = videos.filter(created_at__gte=now - timedelta(days=30))
        elif range_key == "90d":
            videos = videos.filter(created_at__gte=now - timedelta(days=90))

        post_count = videos.count()
        total_views = videos.aggregate(Sum('view_count'))['view_count__sum'] or 0
        total_likes = videos.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
        total_comments = videos.aggregate(Sum('comment_count'))['comment_count__sum'] or 0
        
        followers = tt_profile.followers_count
        avg_views = round(total_views / post_count, 2) if post_count > 0 else 0.0

        ai = generate_ai_insight("TikTok", followers, total_views, total_likes, total_comments, post_count, avg_views)
        if not ai:
            ai = {}

        # Top content
        top_items = []
        for v in videos.order_by('-view_count')[:4]:
            top_items.append({
                "id": v.video_id,
                "title": v.title,
                "views": v.view_count,
                "likes": v.likes_count,
                "comments": v.comment_count,
                "shares": v.share_count,
                "created_time": v.created_at.isoformat() if v.created_at else ""
            })

        return {
            "profile": {
                "name": tt_profile.username or tt_profile.profile.user.name or "TikTok Profile",
                "platform": "TikTok",
                "followers": followers
            },
            "performance_overview": {
                "engagement_rate": ai.get("engagement_rate", 0.0),
                "new_followers": int(followers * (ai.get("growth_rate", 0.0) / 100.0)),
                "posts": post_count,
                "avg_view_per_post": ai.get("avg_views_per_post", avg_views),
                "ai_score": ai.get("ai_score", 0.0),
                "growth_rate": ai.get("growth_rate", 0.0),
            },
            "top_content": top_items,
            "growth_suggestions": ai.get("growth_suggestions", []),
        }

    def _instagram_insight(self, profile, ig_profile, range_key):
        from apps.creator_dashboard.models import InstagramProfileMedia
        from django.db.models import Sum
        from datetime import timedelta
        from django.utils import timezone

        videos = InstagramProfileMedia.objects.filter(profile=profile)
        
        # Apply range filtering
        now = timezone.now()
        if range_key == "7d":
            videos = videos.filter(created_at__gte=now - timedelta(days=7))
        elif range_key == "30d":
            videos = videos.filter(created_at__gte=now - timedelta(days=30))
        elif range_key == "90d":
            videos = videos.filter(created_at__gte=now - timedelta(days=90))

        post_count = videos.count()
        total_views = videos.aggregate(Sum('view_count'))['view_count__sum'] or 0
        total_likes = videos.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
        total_comments = videos.aggregate(Sum('comment_count'))['comment_count__sum'] or 0
        
        followers = ig_profile.followers_count
        avg_views = round(total_views / post_count, 2) if post_count > 0 else 0.0

        ai = generate_ai_insight("Instagram", followers, total_views, total_likes, total_comments, post_count, avg_views)
        if not ai:
            ai = {}

        # Top content
        top_items = []
        for v in videos.order_by('-view_count')[:4]:
            top_items.append({
                "id": v.video_id,
                "title": v.title,
                "views": v.view_count,
                "likes": v.likes_count,
                "comments": v.comment_count,
                "shares": v.share_count,
                "created_time": v.created_at.isoformat() if v.created_at else ""
            })

        return {
            "profile": {
                "name": ig_profile.username or ig_profile.profile.user.name or "Instagram Profile",
                "platform": "Instagram",
                "followers": followers
            },
            "performance_overview": {
                "engagement_rate": ai.get("engagement_rate", 0.0),
                "new_followers": int(followers * (ai.get("growth_rate", 0.0) / 100.0)),
                "posts": post_count,
                "avg_view_per_post": ai.get("avg_views_per_post", avg_views),
                "ai_score": ai.get("ai_score", 0.0),
                "growth_rate": ai.get("growth_rate", 0.0),
            },
            "top_content": top_items,
            "growth_suggestions": ai.get("growth_suggestions", []),
        }

    def get(self, request):
        platform = request.query_params.get("platform")
        range_key = request.query_params.get("range", "30d")

        if not platform:
            return Response({"success": False, "message": "Platform query parameter is required"}, 400)

        platform = platform.lower()
        profile, plat_profile = self._get_profile_and_platform_profile(request.user, platform)

        if not profile:
            return Response({"success": False, "message": "Creator profile not found"}, 404)

        if not plat_profile:
            return Response({"success": False, "message": f"{platform.title()} profile is not connected"}, 400)

        if platform == "youtube":
            data = self._youtube_insight(profile, plat_profile, range_key)
        elif platform == "tiktok":
            data = self._tiktok_insight(profile, plat_profile, range_key)
        elif platform == "instagram":
            data = self._instagram_insight(profile, plat_profile, range_key)
        else:
            return Response({"success": False, "message": "Invalid platform"}, 400)

        return Response({"success": True, "data": data}, 200)


from xhtml2pdf import pisa
from io import BytesIO
from django.http import FileResponse

class InsightperformanceDownloadPDFView(InsightPerformanceAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.creator_dashboard.models import CreatorProfile, YoutubeProfile, TiktokProfile, InstagramProfile
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=404)

        platform = request.query_params.get("platform")
        if platform:
            platform = platform.lower()
        else:
            # Default to first connected platform
            if YoutubeProfile.objects.filter(profile=profile).exists():
                platform = "youtube"
            elif TiktokProfile.objects.filter(profile=profile).exists():
                platform = "tiktok"
            elif InstagramProfile.objects.filter(profile=profile).exists():
                platform = "instagram"
            else:
                return Response({"error": "No social media platform connected"}, status=400)

        # Get the corresponding platform profile
        plat_profile = None
        if platform == "youtube":
            plat_profile = YoutubeProfile.objects.filter(profile=profile).first()
        elif platform == "tiktok":
            plat_profile = TiktokProfile.objects.filter(profile=profile).first()
        elif platform == "instagram":
            plat_profile = InstagramProfile.objects.filter(profile=profile).first()

        if not plat_profile:
            return Response({"error": f"{platform.title()} profile is not connected"}, status=400)

        try:
            # Generate insight data
            range_key = request.query_params.get("range", "30d")
            if platform == "youtube":
                data = self._youtube_insight(profile, plat_profile, range_key)
            elif platform == "tiktok":
                data = self._tiktok_insight(profile, plat_profile, range_key)
            elif platform == "instagram":
                data = self._instagram_insight(profile, plat_profile, range_key)
            else:
                return Response({"error": "Invalid platform"}, status=400)

            name = request.user.name or data["profile"]["name"] or "Creator"
            followers = data["profile"]["followers"]
            engagement = data["performance_overview"]["engagement_rate"]
            growth = data["performance_overview"].get("growth_rate", 0.0)
            ai_score = data["performance_overview"]["ai_score"]
            posts = data["performance_overview"]["posts"]
            avg_views = data["performance_overview"]["avg_view_per_post"]
            new_followers = data["performance_overview"]["new_followers"]

            # Generate HTML
            html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; font-size: 12px; }}
                        h1 {{ text-align: center; color: #C00; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    <h1>{platform.title()} Channel Insight Report</h1>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Platform:</strong> {platform.title()}</p>
                    <p><strong>Followers/Subscribers:</strong> {followers}</p>
                    <p><strong>Engagement Rate:</strong> {engagement:.2f}%</p>
                    <p><strong>Growth Rate:</strong> {growth:.2f}%</p>
                    <p><strong>AI Score:</strong> {ai_score}</p>
                    <p><strong>New Followers:</strong> {new_followers}</p>
                    <p><strong>Posts Analyzed:</strong> {posts}</p>
                    <p><strong>Avg Views/Post:</strong> {avg_views:.2f}</p>
                </body>
                </html>
            """

            # Generate PDF
            result = BytesIO()
            pisa_status = pisa.CreatePDF(html, dest=result)

            if pisa_status.err:
                return Response({"error": "Failed to generate PDF"}, status=500)

            result.seek(0)
            filename = f"{name.replace(' ', '_')}_{platform}_insight_report.pdf"

            return FileResponse(result, as_attachment=True, filename=filename, content_type='application/pdf')

        except Exception as e:
            logger.exception("PDF Generation Failed")
            return Response({"error": f"Unexpected error: {str(e)}"}, status=500)
    



def fetch_tiktok_video_data(username, count=10):
    """
    Fetch videos for a TikTok username using RapidAPI scraper endpoint.
    """
    url = f"https://{RAPIDAPI_HOST}/user/videos"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST,
        "Accept": "application/json",
    }
    params = {"username": username, "count": count}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("videos", [])
    except Exception as e:
        logger.error("Failed to fetch TikTok videos for %s: %s", username, e)
        return []



from .social_utils import *
class TopVideosAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_top_videos(self, videos, count=4):
        try:
            return sorted(videos, key=lambda v: int(v.get("views", 0)), reverse=True)[:count]
        except Exception:
            return videos[:count]

    def get(self, request, *args, **kwargs):
        data = {}
        youtube_link = getattr(request.user, "youtube_link", "")
        if youtube_link:
            channel_id = extract_channel_id(youtube_link)
            if channel_id:
                videos = fetch_youtube_video_stats(channel_id, count=20)
                data["youtube"] = self.get_top_videos(videos)
            else:
                data["youtube"] = []
        else:
            data["youtube"] = []

        return Response({"success": True, "data": data}, status=200)

# Performance Overview and platform breakdown analysis



from .service.monthly import build_performance_overview
from .service.metrics import build_engagement_metrics, get_30d_metrics
from .service.platform_score import build_platform_breakdown

from apps.dashboard.youtube_utils import (
    extract_youtube_channel_id,
    fetch_youtube_channel_data,
    analyze_youtube_data_with_openai,
)
from apps.dashboard.instagram_utils import (
    fetch_instagram_user_info,
    fetch_instagram_posts,
    analyze_instagram_insights,
)
from apps.dashboard.tiktok_utils import (
    fetch_tiktok_user_info,
    fetch_tiktok_video_data,
    analyze_tiktok_data_with_openai,
)
# from apps.dashboard.social_utils import extract_username


# --------------------------------------------------
# helpers
# --------------------------------------------------

def humanize(n: int):
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def safe_int(v):
    try:
        return int(v)
    except Exception:
        return 0


# --------------------------------------------------
# MAIN VIEW
# --------------------------------------------------

class CreatorAnalyticsOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # --------------------------------------------------
    # PLATFORM ANALYSIS (single platform)
    # --------------------------------------------------
    def analyze_platform(self, user, platform: str, url: str):
        if not url:
            return None

        # ---------------- YOUTUBE ----------------
        if platform == "youtube":
            cid = extract_youtube_channel_id(url)
            if not cid:
                return None

            channel = fetch_youtube_channel_data(cid)
            if not channel:
                return None

            ai = analyze_youtube_data_with_openai(channel)

            return {
                "platform": "YouTube",
                "subscribers": safe_int(channel["stats"].get("subscriber_count")),
                "total_views": safe_int(channel["stats"].get("view_count")),
                "engagement_rate": float(ai.get("engagement_rate", 0)),
                "view_rate": float(ai.get("view_rate", 0)),
                "comment_rate": float(ai.get("comment_rate", 0)),
                "growth": float(ai.get("growth_rate", 0)),
                "ai_score": float(ai.get("ai_score", 0)) * 10,  # → 0–100
                "monthly_items": channel.get("videos", []),  # for monthly aggregation
            }

        # ---------------- INSTAGRAM ----------------
        if platform == "instagram":
            parsed = extract_username(url)
            if not parsed:
                return None

            username = parsed["username"]
            profile = fetch_instagram_user_info(username)
            posts = fetch_instagram_posts(username, count=90) or []

            insight = analyze_instagram_insights(profile, posts, "30d")

            return {
                "platform": "Instagram",
                "subscribers": safe_int(profile.get("follower_count")),
                "total_views": sum(safe_int(p.get("views")) for p in posts),
                "engagement_rate": float(insight.get("engagement_rate", 0)),
                "view_rate": float(insight.get("avg_view_per_post", 0)),
                "comment_rate": 0.0,
                "growth": float(insight.get("growth_rate", 0)),
                "ai_score": float(insight.get("ai_score", 0)) * 10,
                "monthly_items": posts,
            }

        # ---------------- TIKTOK ----------------
        if platform == "tiktok":
            parsed = extract_username(url)
            if not parsed:
                return None

            username = parsed["username"]
            profile = fetch_tiktok_user_info(
                user.tiktok_open_id,
                user.tiktok_access_token
            )

            videos = fetch_tiktok_video_data(
                user.tiktok_open_id,
                user.tiktok_access_token,
                count=60
            )

            total_views = sum(safe_int(v.get("views")) for v in videos)
            total_likes = sum(safe_int(v.get("likes")) for v in videos)
            total_comments = sum(safe_int(v.get("comments")) for v in videos)

            followers = max(safe_int(profile.get("follower_count")), 1)
            engagement_rate = ((total_likes + total_comments) / followers) * 100

            ai = analyze_tiktok_data_with_openai({
                "follower_count": followers,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
            })

            return {
                "platform": "TikTok",
                "subscribers": followers,
                "total_views": total_views,
                "engagement_rate": round(engagement_rate, 2),
                "view_rate": round((total_views / followers) * 100, 2),
                "comment_rate": round((total_comments / followers) * 100, 2),
                "growth": float(ai.get("activity_level", 0)),
                "ai_score": float(ai.get("ai_score", 0)),
                "monthly_items": videos,
            }

        return None

    # --------------------------------------------------
    # MAIN GET
    # --------------------------------------------------
    def get(self, request):
        user = request.user

        url_map = {
            "youtube": user.youtube_link,
            "instagram": user.instagram_link,
            "tiktok": user.tiktok_link,
        }

        # 1️⃣ collect platform data (single pass)
        platforms_data = []
        for key, url in url_map.items():
            if not url:
                continue
            data = self.analyze_platform(user, key, url)
            if data:
                platforms_data.append(data)

        if not platforms_data:
            return Response(
                {"success": False, "message": "No platform connected."},
                status=400,
            )

        # 2️⃣ totals
        total_subscribers = sum(p["subscribers"] for p in platforms_data)
        total_views = sum(p["total_views"] for p in platforms_data)

        # 3️⃣ performance overview (last 6 completed months)
        # NOTE: here you should aggregate monthly views from monthly_items
        # for now assume you already prepared monthly_views dict
        monthly_views = get_monthly_views_for_user(platforms_data)
        performance_overview = build_performance_overview(monthly_views)

        # 4️⃣ engagement metrics (30d vs prev 30d)
        current_30d, previous_30d = get_30d_metrics(
            platforms_data,
            total_subscribers
        )
        engagement_metrics = build_engagement_metrics(
            current_30d,
            previous_30d
        )


        # 5️⃣ platform breakdown
        platform_breakdown = build_platform_breakdown([
            {
                "platform": p["platform"],
                "ai_score": p["ai_score"],
                "engagement": p["engagement_rate"],
                "growth": p["growth"],
            }
            for p in platforms_data
        ])

        # 6️⃣ AI score (best platform weighted)
        ai_score = round(
            sum(p["ai_score"] for p in platforms_data) / len(platforms_data),
            1
        )

        # 7️⃣ icons
        icons = {
            p["platform"].lower(): humanize(p["subscribers"])
            for p in platforms_data
        }

        # --------------------------------------------------
        # FINAL RESPONSE (UI-MATCHED)
        # --------------------------------------------------
        return Response({
            "success": True,
            "data": {
                "profile": {
                    "name": user.name,
                    "avatar": getattr(user, "profile_image", None),
                    "platform_icons": icons,
                },

                "summary_cards": {
                    "total_subscribers": {
                        "value": total_subscribers,
                        "label": humanize(total_subscribers),
                    },
                    "engagement_rate": {
                        "value": engagement_metrics["engagement_rate"]["value"],
                        "label": f'{engagement_metrics["engagement_rate"]["value"]}%',
                    },
                },

                "performance_top": {
                    "total_views": {
                        "value": total_views,
                        "label": humanize(total_views),
                    },
                    "growth_rate": {
                        "value": engagement_metrics["view_rate"]["trend"],
                        "label": f'{engagement_metrics["view_rate"]["trend"]:+.1f}%',
                    },
                    "ai_score": {
                        "value": ai_score,
                        "label": f"{ai_score}/100",
                        "tooltip": (
                            "Confidence score showing how likely this idea is to perform "
                            "well based on trends, views, and engagement."
                        ),
                    },
                },

                "performance_overview": performance_overview,
                "engagement_metrics": engagement_metrics,
                "platform_breakdown": platform_breakdown,
            },
        })
