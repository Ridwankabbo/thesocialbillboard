from rest_framework.views import APIView
from rest_framework.response import Response
import requests
import openai
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework import status

# Set your keys here
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
openai.api_key = OPENAI_API_KEY
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
  
class YouTubePagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'

def get_trending_channels():
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&chart=mostPopular&maxResults=50&regionCode=US&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        video_items = response.json().get('items', [])
        channel_ids = list({item['snippet']['channelId'] for item in video_items})
        return channel_ids[:20]  # top 20 unique channels
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print("YouTube API token limit reached while fetching trending channels.")
        else:
            print(f"Error fetching trending channels: {e}")
        return []

def get_channel_details(channel_id):
    url = (
        f"https://www.googleapis.com/youtube/v3/channels"
        f"?part=snippet,statistics,brandingSettings,topicDetails"
        f"&id={channel_id}&key={YOUTUBE_API_KEY}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        items = response.json().get('items', [])
        if not items:
            return None

        details = items[0]

        # Extract category from topicDetails
        topic_categories = details.get("topicDetails", {}).get("topicCategories", [])
        if topic_categories:
            # Convert URL to readable category name
            category = topic_categories[0].split("/")[-1].replace("_", " ").title()
        else:
            category = "Unknown"

        # Attach category to details for downstream use
        details["category"] = category

        return details
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching details for channel {channel_id}.")
        else:
            print(f"Error fetching channel details for {channel_id}: {e}")
        return None


def get_recent_videos(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=date&maxResults=5&type=video&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('items', [])
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching recent videos for channel {channel_id}.")
        else:
            print(f"Error fetching recent videos for channel {channel_id}: {e}")
        return []

def estimate_growth_rate(recent_videos):
    total_views = 0
    for video in recent_videos:
        video_id = video['id']['videoId']
        stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YOUTUBE_API_KEY}"
        try:
            stats_resp = requests.get(stats_url)
            stats_resp.raise_for_status()
            stats = stats_resp.json()
            items = stats.get('items', [])
            if items:
                views = int(items[0]['statistics'].get('viewCount', 0))
                total_views += views
        except Exception as e:
            error_msg = str(e).lower()
            if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
                print(f"YouTube API token limit reached while estimating growth for video {video_id}.")
            else:
                print(f"Error estimating growth for video {video_id}: {e}")
    return f"+{round(total_views / 100000, 2)}%"  # basic growth proxy

def analyze_channels(name,description):
        
    prompt = (
        f"Based on this YouTube channel's title and description, give a rating and score.\n"
        f"Title: {name}\nDescription: {description}\n"
        f"Rate it for children using one of: 8+, 10+, 14+, 18+\n"
        f"Return ONLY a JSON like this:\n"
        f'{{"score": float from 0.0 to 10.0, "age_rating": one of "8+", "10+", "14+", "18+"}}'
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text = completion.choices[0].message.content.strip()

        print("Raw AI response:", text)  # 🔍 Debug

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in AI response")

        data = json.loads(match.group())
        return data.get("score", "N/A"), data.get("age_rating", "Unknown")

    except Exception as e:
        print("AI error:", e)
        return "N/A", "Unknown"

# Top Chart Blaster Data view 
class TrendingChannelsAPIView(BaseAPIView): 
    def get(self, request):
        data = ClimbingTheChart.objects.all().values("name", "data", "fetched_at")
        return self.success_response(
            message="Trending channels fetched successfully",
            data=list(data)
        )



# safe for children  
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from googleapiclient.discovery import build
from django.conf import settings
import openai
import random
from openai import OpenAI
client = OpenAI()
def safety_score():
    return random.randrange(70, 99)  # 101 is exclusive

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
OPENAI_API_KEY = settings.OPENAI_API_KEY
openai.api_key = OPENAI_API_KEY

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def search_channels_by_query(query):
    try:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="channel",
            maxResults=20
        ).execute()
        return [item["snippet"]["channelId"] for item in response.get("items", [])]
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while searching channels for query: {query}.")
        else:
            print(f"Error searching channels for query: {query}: {e}")
        return []


def get_channel_info(channel_id):
    try:
        data = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while getting info for channel {channel_id}.")
        else:
            print(f"Error getting info for channel {channel_id}: {e}")
        return None

    if not data.get("items"):
        return None

    item = data["items"][0]
    snippet = item["snippet"]
    stats = item.get("statistics", {})
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    subscribers = stats.get("subscriberCount", "0")
    profile_photo = snippet.get("thumbnails", {}).get("default", {}).get("url", "")
    thumbnail = snippet.get("thumbnails", {}).get("high", {}).get("url", "")
    channel_url = f"https://www.youtube.com/channel/{channel_id}"

    # AI prompt
    prompt = f"""
        Based on the title, description, transcript, and visual style, determine the most suitable minimum age rating 
        for this video. Choose ONLY from: 3+, 4+, 5+, 7+, 10+.

        Follow these rules strictly:
        - 3+: Only for preschool and very young children. Simple songs, learning shapes, colors, basic life skills.
        - 4+: For early learners, simple stories, light play, mild humor, no complex themes.
        - 5+: Slightly more advanced stories, simple challenges, mild suspense, still safe for children.
        - 7+: Content with mild cartoon violence, competitive games, or more complex themes that younger kids might not understand.
        - 10+: Content with moderate action, adventure, complex humor, mild scary elements, or themes for pre-teens.

        Respond with ONLY one of the ratings above, with no explanation or justification.

        Title: {title}
        Description: {description}
        """


    try:
        ai_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        age_rating_full = ai_response.choices[0].message.content
    except Exception as e:
        age_rating_full = "Age rating unavailable."

    return {
        "name": title,
        "description": description,
        "followers": subscribers,
        "profile_photo_url": profile_photo,
        "thumbnail_url": thumbnail,
        "channel_url": channel_url,
        "safety_score": safety_score(),  # Placeholder or implement scoring logic
        "age_rating": age_rating_full
    }


# Safe For Children Data View 
class SafeChannelListView(BaseAPIView):
    def get(self, request):
        data = SafeChannelCurratedForChild.objects.all().values("name", "data", "fetched_at")
        return self.success_response(
            message="Safe channels retrieved successfully",
            data=list(data)
        )



# top 10 uk creator this week


import requests
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
@staticmethod
def get_recent_videos(channel_id):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=date&maxResults=5&type=video&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('items', [])
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching recent videos for channel {channel_id}.")
        else:
            print(f"Error fetching recent videos for channel {channel_id}: {e}")
        return []

# @staticmethod
def estimate_growth_rate(recent_videos):
    video_ids = []
    for video in recent_videos:
        vid_id = None
        if isinstance(video.get('id'), dict):
            vid_id = video['id'].get('videoId')
        elif isinstance(video.get('id'), str):
            vid_id = video['id']
        if vid_id:
            video_ids.append(vid_id)
    if not video_ids:
        return "N/A vidid"

    video_ids = video_ids[:50]  # YouTube API max batch size

    stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={','.join(video_ids)}&key={YOUTUBE_API_KEY}"
    try:
        response = requests.get(stats_url)
        response.raise_for_status()
        stats = response.json()
        items = stats.get('items', [])

        if not items:
            print("No items returned. Full response:", stats)
            return "N/A empty"

        total_views = sum(int(item['statistics'].get('viewCount', 0)) for item in items)
        return f"+{round(total_views / 100000, 2)}%" if total_views else "N/A zero"
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print("YouTube API token limit reached while estimating growth for batch.")
        else:
            print(f"Error fetching video stats: {e}")
        return "N/A excp"

from .models import *
# top ten uk creators ai data
class TopTenUkCreatorsAiDatas(BaseAPIView):
    def get(self, request):
        record = TopTenUkCreatorsAiData.objects.filter(
            name="top_uk_creators"
        ).values("data", "fetched_at").first()

        if not record:
            return self.error_response("No data found")

        creators = record["data"]
        # Add rank based on subscribers
        ranked_creators = [
            {**creator, "rank": idx + 1}
            for idx, creator in enumerate(
                sorted(creators, key=lambda x: x["subscribers"], reverse=True)
            )
        ]

        return self.success_response(
            message="Top 10 UK creators AI data fetched successfully",
            data={
                "fetched_at": record["fetched_at"],
                "creators": ranked_creators
            }
        )

# Smart Match Ai recombined creator 


import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.conf import settings
import openai
import json
import re
from .models import SmartMatchAiData
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
openai.api_key = settings.OPENAI_API_KEY

class YouTubePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'

# Smart Match AI recombined creator view
class SmartMatchDataView(BaseAPIView):
    def get(self, request):
        data = SmartMatchAiData.objects.all().values("name", "data", "fetched_at")
        return self.success_response(
            message="Smart match data fetched successfully",
            data=list(data)
        )

def analyze_channel(snippet):
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    prompt = (
        f"Based on this YouTube channel's title and description, give a rating and score.\n"
        f"Title: {title}\nDescription: {description}\n"
        f"Rate it for children using one of: 8+, 10+, 14+, 18+\n"
        f"Return ONLY a JSON like this:\n"
        f'{{"score": float from 0.0 to 10.0, "age_rating": one of "8+", "10+", "14+", "18+"}}'
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text = completion.choices[0].message.content.strip()

        print("Raw AI response:", text)  # 🔍 Debug

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found in AI response")

        data = json.loads(match.group())
        return data.get("score", "N/A"), data.get("age_rating", "Unknown")

    except Exception as e:
        print("AI error:", e)
        return "N/A", "Unknown"


def estimate_growth(channel_id):
    # Simulated growth for now
    import random
    return random.uniform(-3, 10)





