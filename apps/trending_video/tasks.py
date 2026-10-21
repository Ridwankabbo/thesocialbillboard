from celery import shared_task
from django.utils import timezone
from .models import SmartMatchAiData
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.cache import cache
from django.conf import settings
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY # Replace with your actual key
from .views import analyze_channel,estimate_growth  # Assuming this function is defined in views.py
@shared_task
def fetch_and_store_smart_matchai_youtube_data():
    trending_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "chart": "mostPopular",
        "regionCode": "US",
        "maxResults": 50,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(trending_url, params=params)
    items = response.json().get("items", [])
    channel_ids = list({item['snippet']['channelId'] for item in items})[:20]

    creators = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_channel_data, cid): cid for cid in channel_ids}
        for future in as_completed(futures):
            data = future.result()
            if data:
                creators.append(data)

    
    SmartMatchAiData.objects.update_or_create(
        name="smartAiChoice_latest_parenting",
        defaults={
            "data": creators,
            "fetched_at": timezone.now()
        }
    )
    return f"{len(creators)} AiChoice videos updated in DB."


def get_channel_data(channel_id):
    cached = cache.get(f"channel_data_{channel_id}")
    if cached:
        return cached

    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics,brandingSettings,topicDetails",
        "id": channel_id,
        "key": YOUTUBE_API_KEY
    }

    r = requests.get(channel_url, params=params)
    items = r.json().get("items", [])
    if not items:
        return None

    data = items[0]
    snippet = data["snippet"]
    stats = data["statistics"]
    branding = data.get("brandingSettings", {})
    topics = data.get("topicDetails", {}).get("topicCategories", [])
    category = topics[0].split("/")[-1].replace("_", " ") if topics else "Unknown"


    ai_score, age_rating = analyze_channel(snippet)
    
    recent_videos = get_recent_videos(channel_id)
    growth_rates = estimate_growth_rate(recent_videos)
    try:
        growth_rate_str = f"{growth_rates:+.2f}%" if isinstance(growth_rates, (int, float)) else str(growth_rates)
    except Exception:
        growth_rate_str = "N/A"

    result = {
        "name": snippet["title"],
        "category": category,
        "followers": int(stats.get("subscriberCount", 0)),
        "growth_rate": growth_rate_str,
        "ai_score": ai_score,
        "age_rating": age_rating,
        "thumbnail_url": snippet["thumbnails"]["high"]["url"],
        "cover_photo_url": branding.get("image", {}).get("bannerExternalUrl"),
        "profile_photo_url": snippet["thumbnails"]["default"]["url"],
        "channel_url": f"https://www.youtube.com/channel/{channel_id}"
    }

    cache.set(f"channel_data_{channel_id}", result, timeout=3600)
    return result




# top ten uk creator data save task 


from celery import shared_task
from django.utils import timezone
from apps.trending_video.models import TopTenUkCreatorsAiData
import requests
from .views import *

@shared_task
def fetch_and_store_top_uk_creators():
    trending_url = "https://www.googleapis.com/youtube/v3/videos"
    trending_params = {
        "part": "snippet",
        "chart": "mostPopular",
        "regionCode": "GB",
        "maxResults": 50,
        "key": YOUTUBE_API_KEY
    }

    trending_response = requests.get(trending_url, params=trending_params)
    trending_data = trending_response.json()

    if "items" not in trending_data:
        print("No trending videos found")
        return

    channel_to_category = {}
    for item in trending_data["items"]:
        snippet = item.get("snippet", {})
        channel_id = snippet.get("channelId")
        category_id = snippet.get("categoryId")
        if channel_id:
            channel_to_category[channel_id] = category_id

    channel_ids = list(channel_to_category.keys())
    if not channel_ids:
        print("No channel IDs found")
        return

    category_url = "https://www.googleapis.com/youtube/v3/videoCategories"
    category_params = {
        "part": "snippet",
        "regionCode": "GB",
        "key": YOUTUBE_API_KEY
    }

    category_response = requests.get(category_url, params=category_params)
    category_data = category_response.json()
    category_map = {
        item["id"]: item["snippet"]["title"]
        for item in category_data.get("items", [])
    }

    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
        "part": "snippet,statistics",
        "id": ",".join(channel_ids[:50]),
        "key": YOUTUBE_API_KEY
    }

    channel_response = requests.get(channel_url, params=channel_params)
    channel_data = channel_response.json()

    if "items" not in channel_data:
        print("No channel data found")
        return

    creators = []
    for item in channel_data["items"]:
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        channel_id = item.get("id")

        recent_videos = get_recent_videos(channel_id)
        growth_rate = estimate_growth_rate(recent_videos)

        creators.append({
            "name": snippet.get("title"),
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "channel_id": channel_id,
            "profile_picture": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "category": category_map.get(channel_to_category.get(channel_id, ""), "Unknown"),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "growth_rate":str(growth_rate)
        })

    sorted_creators = sorted(creators, key=lambda x: x["subscribers"], reverse=True)[:10]

    
    TopTenUkCreatorsAiData.objects.update_or_create(
        name="top_uk_creators",
        defaults={
            "data": sorted_creators,
            "fetched_at": timezone.now()
        }
    )
    return f"{len(sorted_creators)} Top Ten Uk Creators updated in DB."



# safe channel curated for child

from celery import shared_task
from django.utils import timezone
from apps.trending_video.models import SafeChannelCurratedForChild
from django.core.cache import cache

# Import your helper functions
# from .utils import search_channels_by_query, get_channel_info

@shared_task
def fetch_and_store_safe_channels(query=None):
    # Expanded keyword list for kids-related content
    keywords = [
        "kids", 
        "preschool learning", 
        "cartoon for children"
    ]

    results = []

    for keyword in keywords:
        channel_ids = search_channels_by_query(keyword)
        if not channel_ids:
            continue

        for cid in channel_ids:
            info = get_channel_info(cid)
            if info and info not in results:
                results.append(info)

    # Store in DB
    SafeChannelCurratedForChild.objects.update_or_create(
        name="safe_channels_for_children",
        defaults={
            "data": results,
            "fetched_at": timezone.now()
        }
    )
    return f"{len(results)} safe-for-children channels updated in DB."




# top chart climbing task
from celery import shared_task
from django.utils import timezone
from apps.trending_video.models import ClimbingTheChart

# Import your helper functions
# from .utils import get_trending_channels, get_channel_details, get_recent_videos, estimate_growth_rate, analyze_channel

@shared_task
def fetch_and_store_trending_channels():
    channel_ids = get_trending_channels()
    if not channel_ids:
        print("No trending channels found")
        return
    all_channel_data = []
    for channel_id in channel_ids:
        details = get_channel_details(channel_id)
        if not details:
            continue

        name = details['snippet']['title']
        description = details['snippet'].get('description', '')
        followers = int(details['statistics'].get('subscriberCount', 0))
        thumbnail_url = details['snippet']['thumbnails']['high']['url']
        cover_photo_url = details.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl', '')
        channel_url = f"https://www.youtube.com/channel/{channel_id}"

        recent_videos = get_recent_videos(channel_id)
        growth_rate = estimate_growth_rate(recent_videos)
        ai_score, age_rating = analyze_channels(name, description)

        channel_data = {
            "name": name,
            "channel_url": channel_url,
            "category" : details.get("category", "Unknown"),
            "followers": followers,
            "growth_rate": str(growth_rate),
            "ai_score": ai_score,
            "age_rating": age_rating,
            "thumbnail_url": thumbnail_url,
            "cover_photo_url": cover_photo_url
        }
        all_channel_data.append(channel_data)
        ClimbingTheChart.objects.update_or_create(
            name="climbing_the_chart_latest_pretens",
            defaults={
                "data": all_channel_data,
                "fetched_at": timezone.now()
            }
        )
