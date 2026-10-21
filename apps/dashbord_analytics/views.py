import requests
from django.conf import settings

YOUTUBE_ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"

def fetch_youtube_analytics(access_token, start_date, end_date):
    params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,watchTimeMinutes,averageViewDuration,subscribersGained,subscribersLost",
        "dimensions": "day",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    res = requests.get(
        YOUTUBE_ANALYTICS_URL,
        params=params,
        headers=headers,
        timeout=20,
    )

    if res.status_code >= 400:
        raise Exception(res.json())

    return res.json()


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import YouTubeOAuthToken
from .views import refresh_youtube_access_token


YOUTUBE_DATA_API_URL = "https://www.googleapis.com/youtube/v3"


def _resolve_channel_id_from_username(username: str):
    cleaned = username.strip().replace("@", "")
    if not cleaned:
        return None

    # 1) Try handle lookup: /@handle
    by_handle = requests.get(
        f"{YOUTUBE_DATA_API_URL}/search",
        params={
            "part": "snippet",
            "q": cleaned,
            "type": "channel",
            "maxResults": 1,
            "key": settings.YOUTUBE_API_KEY,
        },
        timeout=20,
    ).json()

    items = by_handle.get("items", [])
    if items:
        return items[0]["snippet"].get("channelId")
    return None


def _get_channel_meta(channel_id: str):
    res = requests.get(
        f"{YOUTUBE_DATA_API_URL}/channels",
        params={
            "part": "snippet,statistics",
            "id": channel_id,
            "key": settings.YOUTUBE_API_KEY,
        },
        timeout=20,
    ).json()
    items = res.get("items", [])
    if not items:
        return None

    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})

    return {
        "channel_id": channel_id,
        "channel_name": snippet.get("title"),
        "description": snippet.get("description", ""),
        "profile_photo": snippet.get("thumbnails", {}).get("default", {}).get("url"),
        "subscribers": statistics.get("subscriberCount", "N/A"),
        "channel_link": f"https://www.youtube.com/channel/{channel_id}",
    }


def _search_competitor_channels(keyword: str, exclude_channel_id: str, limit: int = 5):
    res = requests.get(
        f"{YOUTUBE_DATA_API_URL}/search",
        params={
            "part": "snippet",
            "q": keyword,
            "type": "channel",
            "maxResults": 15,
            "key": settings.YOUTUBE_API_KEY,
        },
        timeout=20,
    ).json()

    competitors = []
    for item in res.get("items", []):
        channel_id = item.get("snippet", {}).get("channelId")
        if not channel_id or channel_id == exclude_channel_id:
            continue

        channel_meta = _get_channel_meta(channel_id)
        if not channel_meta:
            continue

        competitors.append({
            "channel_name": channel_meta["channel_name"],
            "channel_link": channel_meta["channel_link"],
            "profile_photo": channel_meta["profile_photo"],
            "subscribers": channel_meta["subscribers"],
        })

        if len(competitors) >= limit:
            break

    return competitors


class YouTubeAnalyticsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not start_date or not end_date:
            return Response(
                {"detail": "start_date and end_date required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            yt = request.user.youtube_oauth
        except YouTubeOAuthToken.DoesNotExist:
            return Response(
                {"detail": "YouTube not connected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if yt.is_expired():
            yt = refresh_youtube_access_token(yt)

        try:
            data = fetch_youtube_analytics(
                yt.access_token,
                start_date,
                end_date,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class YouTubeCompetitorByUsernameAPIView(APIView):
    """
    Input: {"youtube_username": "MrBeast", "limit": 5}
    Returns: channel + 5-10 competitor channels with link, photo, subscribers.
    """

    def post(self, request):
        youtube_username = (request.data.get("youtube_username") or "").strip()
        raw_limit = request.data.get("limit", 5)

        if not youtube_username:
            return Response(
                {"success": False, "message": "youtube_username is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "limit must be a number between 5 and 10"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if limit < 5 or limit > 10:
            return Response(
                {"success": False, "message": "limit must be between 5 and 10"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        channel_id = _resolve_channel_id_from_username(youtube_username)
        if not channel_id:
            return Response(
                {"success": False, "message": "Could not find YouTube channel for this username"},
                status=status.HTTP_404_NOT_FOUND,
            )

        input_channel = _get_channel_meta(channel_id)
        if not input_channel:
            return Response(
                {"success": False, "message": "Input channel details not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        keyword = f"{input_channel['channel_name']} {input_channel['description']}"
        competitors = _search_competitor_channels(keyword, exclude_channel_id=channel_id, limit=limit)

        return Response(
            {
                "success": True,
                "input_channel": {
                    "channel_name": input_channel["channel_name"],
                    "channel_link": input_channel["channel_link"],
                    "profile_photo": input_channel["profile_photo"],
                    "subscribers": input_channel["subscribers"],
                },
                "competitors": competitors,
                "count": len(competitors),
            },
            status=status.HTTP_200_OK,
        )