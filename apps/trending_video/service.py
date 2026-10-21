import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings
import openai
import json
import re
from django.utils import timezone
from .models import *
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
openai.api_key = settings.OPENAI_API_KEY



def fetch_and_store_smartmatch_data():
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

    results = []

    def get_channel_data(channel_id):
        cached = cache.get(f"channel_data_{channel_id}")
        if cached:
            return cached

        channel_url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            "part": "snippet,statistics,brandingSettings",
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

        ai_score, age_rating = analyze_channel(snippet)

        result = {
            "name": snippet["title"],
            "category": snippet.get("customUrl", "Unknown"),
            "followers": int(stats.get("subscriberCount", 0)),
            "growth_rate": f"{estimate_growth(channel_id):+.2f}%",
            "ai_score": ai_score,
            "age_rating": age_rating,
            "thumbnail_url": snippet["thumbnails"]["high"]["url"],
            "cover_photo_url": branding.get("image", {}).get("bannerExternalUrl"),
            "profile_photo_url": snippet["thumbnails"]["default"]["url"],
            "channel_url": f"https://www.youtube.com/channel/{channel_id}"
        }
        print("Processed channel:", result["name"])

        try:
            SmartMatchAiData.objects.update_or_create(
                name=result["name"],
                defaults={
                    "data": result,
                    "fetched_at": timezone.now()
                }
            )
        except IntegrityError as e:
            print("DB write error:", e)

        cache.set(f"channel_data_{channel_id}", result, timeout=3600)
        return result

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

            print("Raw AI response:", text)

            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in AI response")

            data = json.loads(match.group())
            return data.get("score", "N/A"), data.get("age_rating", "Unknown")

        except Exception as e:
            print("AI error:", e)
            return "N/A", "Unknown"

    def estimate_growth(channel_id):
        import random
        return random.uniform(-3, 10)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_channel_data, cid): cid for cid in channel_ids}
        for future in as_completed(futures):
            data = future.result()
            if data:
                results.append(data)

    return results  # return raw data, no HTTP stuff
