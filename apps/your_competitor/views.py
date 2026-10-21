from django.shortcuts import render
from django.http import HttpResponse

import requests
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import CompetitorData
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
from rest_framework.views import APIView
from rest_framework import status
def test(request):
    return HttpResponse("Your Competitor API is working!")
from rest_framework import permissions
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY


def extract_channel_id(url):
    
    """Extracts the channel ID from different YouTube URL formats."""
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    elif "/@" in url or "/c/" in url:
        username = url.split("/")[-1].replace("@", "")
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": username,
                "type": "channel",
                "maxResults": 1,
                "key": YOUTUBE_API_KEY
            }
        ).json()
        if resp.get("items"):
            return resp["items"][0]["snippet"]["channelId"]
    return None


def get_channel_keywords(channel_id):
    """Fetches channel title and description to use as search keywords."""
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "part": "snippet,statistics",
            "id": channel_id,
            "key": YOUTUBE_API_KEY
        }
    ).json()

    if not resp.get("items"):
        return None, None, None

    item = resp["items"][0]
    title = item["snippet"]["title"]
    description = item["snippet"]["description"]
    subscriber_count = item["statistics"].get("subscriberCount", "N/A")

    keywords = title + " " + description
    return keywords, title, subscriber_count


def calculate_engagement_rate(channel_id):
    """Calculates average engagement rate from recent videos."""
    # Get latest 5 videos from the channel
    search_resp = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "id",
            "channelId": channel_id,
            "order": "date",
            "maxResults": 5,
            "type": "video",
            "key": YOUTUBE_API_KEY
        }
    ).json()

    video_ids = [
        item["id"]["videoId"]
        for item in search_resp.get("items", [])
        if "videoId" in item.get("id", {})
    ]
    if not video_ids:
        return None

    # Get video statistics
    stats_resp = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": YOUTUBE_API_KEY
        }
    ).json()

    total_views = 0
    total_likes = 0
    total_comments = 0

    for vid in stats_resp.get("items", []):
        stats = vid["statistics"]
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        total_views += views
        total_likes += likes
        total_comments += comments

    if total_views == 0:
        return None

    engagement_rate = ((total_likes + total_comments) / total_views) * 100
    return round(engagement_rate, 2)


def find_competitors(keywords):
    """Searches YouTube for competitor channels based on keywords."""
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": keywords,
            "type": "channel",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY
        }
    ).json()

    competitors = []
    for item in resp.get("items", []):
        channel_id = item["snippet"]["channelId"]
        engagement_rate = calculate_engagement_rate(channel_id)

        competitors.append({
            "name": item["snippet"]["title"],
            "channelId": channel_id,
            "url": f"https://www.youtube.com/channel/{channel_id}",
            "thumbnail": item["snippet"]["thumbnails"]["default"]["url"],
            "engagement_rate": f"{engagement_rate}%" if engagement_rate is not None else "N/A"
        })
    return competitors


@api_view(["POST"])
def competitor_channels(request):
    """
    POST request with {"channel_url": "YouTube Channel Link"} → returns competitor list with engagement rate.
    """
    channel_url = request.data.get("channel_url")
    if not channel_url:
        return Response({"error": "Missing channel_url"}, status=400)

    channel_id = extract_channel_id(channel_url)
    if not channel_id:
        return Response({"error": "Invalid YouTube channel URL"}, status=400)

    keywords, channel_name, subscriber_count = get_channel_keywords(channel_id)
    if not keywords:
        return Response({"error": "Channel not found"}, status=404)

    competitors = find_competitors(keywords)

    return Response({
        "input_channel": {
            "name": channel_name,
            "channelId": channel_id,
            "subscribers": subscriber_count,
            "url": f"https://www.youtube.com/channel/{channel_id}"
        },
        "competitors": competitors
    })

class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
    def error_response(self, message="Your request rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
class MyCompetitorDataAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            item = CompetitorData.objects.get(user=request.user)
        except CompetitorData.DoesNotExist:
            return self.error_response(
                message="No competitor data found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return self.success_response(
            message="Competitor data retrieved successfully",
            data={
                "user_id": item.user.id,
                "user_email": item.user.email,
                "fetched_date": item.fetched_date,
                "data": item.data
            },
            status_code=status.HTTP_200_OK
        )

from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import CompetitorData
from django.contrib.auth import get_user_model
User = get_user_model()

def fetch_competitors_for_user(user_id):
    user = get_object_or_404(User, id=user_id)

    channel_id = extract_channel_id(user.youtube_link)
    if not channel_id:
        return {"status": "error", "message": "No valid channel_id"}

    keywords, channel_name, subscriber_count = get_channel_keywords(channel_id)
    if not keywords:
        return {"status": "error", "message": "No keywords"}

    competitors = find_competitors(keywords)

    data_to_save = {
        "input_channel": {
            "name": channel_name,
            "channelId": channel_id,
            "subscribers": subscriber_count,
            "url": f"https://www.youtube.com/channel/{channel_id}"
        },
        "competitors": competitors
    }

    CompetitorData.objects.update_or_create(
        user=user,
        defaults={
            "fetched_date": timezone.now(),
            "data": data_to_save
        }
    )

    return {"status": "success", "message": f"Competitors updated for {user.email}"}
