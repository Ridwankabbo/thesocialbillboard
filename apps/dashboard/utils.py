# core/utils.py
from django.conf import settings
from googleapiclient.discovery import build
from openai import OpenAI
import requests
import json
import os
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY



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




def parse_number(value: str) -> float:
    """Convert human-readable numbers like '12.5M' into float."""
    value = value.upper().replace(" ", "")
    if value.endswith("M"):
        return float(value[:-1]) * 1_000_000
    elif value.endswith("K"):
        return float(value[:-1]) * 1_000
    elif value.endswith("B"):
        return float(value[:-1]) * 1_000_000_000
    return float(value)



import json
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_growth_suggestions(title, description):
    prompt = f"""
    Provide EXACT JSON:
    {{
       "negative": "string",
       "positive": ["string", "string"]
    }}

    Title: {title}
    Description: {description}
    """

    resp = call_ai(prompt)

    return resp or {
        "negative": "No data",
        "positive": []
    }



# new added utils for date parsing and range filtering

from datetime import datetime, timedelta, timezone

def parse_dt(dt):
    if not dt:
        return None
    try:
        if isinstance(dt, int):
            return datetime.fromtimestamp(dt, timezone.utc)
        if dt.endswith("Z"):
            dt = dt.replace("Z", "+00:00")
        return datetime.fromisoformat(dt)
    except:
        try:
            return datetime.strptime(dt[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except:
            return None


def range_filter(videos, range_key):
    now = datetime.now(timezone.utc)
    periods = {"7d": 7, "30d": 30, "90d": 90, "all": 3650}
    days = periods.get(range_key, 30)

    start = now - timedelta(days=days)
    filtered = []

    for v in videos:
        pub = parse_dt(v.get("published_at") or v.get("created_time"))
        if pub and pub >= start:
            filtered.append(v)

    return filtered


# ---------- UNIVERSAL AI CALLER (Strict JSON) ----------
import json
from openai import OpenAI
from django.conf import settings

ai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def call_ai(prompt: str, temperature: float = 0.3, max_tokens: int = 300):
    """
    Safely call OpenAI with strict JSON response.
    Handles:
    - invalid API key
    - quota exceeded (429 insufficient_quota)
    - malformed JSON
    - timeouts
    Returns: dict or None
    """

    try:
        response = ai_client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a strict JSON generator. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content.strip()

        if not content:
            return None

        # convert JSON to python dict
        return json.loads(content)

    except Exception as e:
        print("❌ OpenAI Error:", e)

        # Specific handle: insufficient quota
        if "insufficient_quota" in str(e).lower():
            return {
                "error": "quota_exceeded",
                "message": "OpenAI quota exceeded / billing required."
            }

        # fallback to None
        return None


from openai import OpenAI
import json
from django.conf import settings

ai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_ai_insight(platform, followers, total_views, total_likes, total_comments, post_count, avg_views):
    prompt = f"""
    You are a social media analytics AI.
    Based on this data:

    Platform: {platform}
    Followers: {followers}
    Posts: {post_count}
    Total Views: {total_views}
    Total Likes: {total_likes}
    Total Comments: {total_comments}
    Avg Views Per Post: {avg_views}

    Return strict JSON:
    {{
      "ai_score": float,
      "engagement_rate": float,
      "growth_rate": float,
      "avg_views_per_post": float,
      "growth_suggestions": ["string","string","string"]
    }}
    """

    try:
        res = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No text outside JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.25
        )

        data = json.loads(res.choices[0].message.content)

    except Exception as e:
        print("AI ERROR:", e)
        data = {}

    # -------- SAFETY FALLBACKS --------
    data.setdefault("ai_score", 0.0)
    data.setdefault("engagement_rate", 0.0)
    data.setdefault("growth_rate", 0.0)
    data.setdefault("avg_views_per_post", avg_views)
    data.setdefault("growth_suggestions", [])

    return data
