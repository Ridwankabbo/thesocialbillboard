from contextvars import copy_context
import requests
from django.conf import settings
import json
from openai import OpenAI
from apps.dashboard.utils import call_ai, range_filter

client = OpenAI(settings.OPENAI_API_KEY)

YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY

import re
from urllib.parse import urlparse

def extract_username(url: str) -> dict | None:
    """Extract username from TikTok, Instagram, YouTube links."""
    if not url:
        return None

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.strip("/")

    # TikTok
    if "tiktok.com" in netloc:
        match = re.search(r"@([A-Za-z0-9._]+)", path)
        if match:
            return {"platform": "tiktok", "username": match.group(1)}

    # Instagram
    if "instagram.com" in netloc or "instagr.am" in netloc:
        parts = path.split('/')
        if parts and parts[0]:
            username = parts[0]
            if username not in ['p', 'reel', 'reels', 'stories', 'explore', 'tags', 'directory', 'accounts']:
                return {"platform": "instagram", "username": username}

    # YouTube
    if "youtube.com" in netloc or "youtu.be" in netloc:
        match = re.search(r"@([A-Za-z0-9._-]+)", path)
        if match:
            return {"platform": "youtube", "username": match.group(1)}
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] in ["channel", "user", "c"]:
            return {"platform": "youtube", "username": parts[1]}

    return None


# ---------- Fetch TikTok API Data ----------
def safe_int(value):
    """
    Convert value to positive integer safely.
    - If value is None or invalid → return 0
    - Always returns absolute positive number
    """
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return 0


# def fetch_tiktok_user_info(username: str):
#     url = "https://tiktok-api23.p.rapidapi.com/api/user/info"
#     headers = {
#         "x-rapidapi-key": settings.RAPIDAPI_KEY,
#         "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
#     }
#     params = {"uniqueId": username}

#     try:
#         r = requests.get(url, headers=headers, params=params, timeout=10)
#         r.raise_for_status()
#         data = r.json().get("userInfo", {})

#         stats = data.get("stats", {})

#         return {
#             "follower_count": stats.get("followerCount", 0),
#             "following_count": stats.get("followingCount", 0),
#             "like_count": stats.get("heartCount", 0),
#             "video_count": stats.get("videoCount", 0),
#         }

#     except Exception as e:
#         print("TikTok user fetch error:", e)
#         return {"error": str(e)}
def fetch_tiktok_user_info(open_id: str, access_token: str):
    """
    TikTok Official Creator Info
    """
    url = "https://open.tiktokapis.com/v2/user/info/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    params = {
        "fields": "follower_count,following_count,likes_count,video_count"
    }

    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {}).get("user", {})

    return {
        "follower_count": data.get("follower_count", 0),
        "following_count": data.get("following_count", 0),
        "like_count": data.get("likes_count", 0),
        "video_count": data.get("video_count", 0),
    }

# def fetch_tiktok_video_data(username, count=20):
#     headers = {
#         "x-rapidapi-key": settings.RAPIDAPI_KEY,
#         "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
#     }
#     url = f"https://{settings.TIKTOK_API_HOST}/user/posts"
#     params = {"uniqueId": username, "count": count}

#     try:
#         r = requests.get(url, headers=headers, params=params, timeout=10)
#         r.raise_for_status()

#         items = r.json().get("data", [])

#         videos = []
#         for v in items[:count]:
#             videos.append({
#                 "id": v.get("id"),
#                 "views": v.get("stats", {}).get("playCount", 0),
#                 "likes": v.get("stats", {}).get("diggCount", 0),
#                 "comments": v.get("stats", {}).get("commentCount", 0),
#                 "shares": v.get("stats", {}).get("shareCount", 0),
#                 "thumbnail": v.get("video", {}).get("cover", ""),
#                 "created_time": v.get("createTime"),
#                 "desc": v.get("desc", "")
#             })

#         return videos

#     except Exception as e:
#         print("TikTok posts fetch error:", e)
#         return []
def fetch_tiktok_video_data(open_id: str, access_token: str, count=20):
    """
    TikTok Official Creator Videos
    """
    url = "https://open.tiktokapis.com/v2/video/list/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "max_count": min(count, 20),
        "fields": [
            "id",
            "create_time",
            "view_count",
            "like_count",
            "comment_count",
            "share_count"
        ]
    }

    r = requests.post(url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()

    videos = []
    for v in r.json().get("data", {}).get("videos", []):
        videos.append({
            "id": v.get("id"),
            "views": v.get("view_count", 0),
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "shares": v.get("share_count", 0),
            "created_time": v.get("create_time"),
        })

    return videos



# ---------- Analyze with OpenAI ----------
def analyze_tiktok_data_with_openai(tiktok_data: dict) -> dict:
    """
    Analyze TikTok channel data and compute ai_score in 0–10 scale using GPT.
    """
    followers = tiktok_data.get("follower_count", 0)
    likes = tiktok_data.get("like_count", 0)
    videos = tiktok_data.get("video_count", 0)

    # --- Local calculations ---
    engagement_rate = (likes / followers) if followers > 0 else 0  # fraction 0–1
    like_follower_ratio = (likes / followers) if followers > 0 else 0
    activity_level = videos / max(followers / 1000, 1)  # videos per 1k followers

    # --- GPT Prompt ---
    prompt = f"""
    You are a TikTok analytics expert.
    Analyze this account and return ONLY a JSON object with these keys:
    ai_score (float 0–10).

    Account Data:
    Followers: {followers}
    Likes: {likes}
    Videos: {videos}
    Engagement Rate (fraction 0–1): {engagement_rate}
    Like/Followers Ratio: {like_follower_ratio}
    Activity Level (videos per 1k followers): {activity_level}

    Instructions:
    Compute ai_score on a strict 0–10 scale using this weighted formula:
    - Engagement Rate → 40%  
    - Like/Followers Ratio → 25%  
    - Activity Level → 20%  
    - Follower Base (diminishing returns) → 15%  

    Output ONLY valid JSON: {{"ai_score": <value>}}
    """

    ai_score = None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict JSON generator. Output only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=150
        )

        gpt_reply = json.loads(response.choices[0].message.content.strip())
        ai_score = gpt_reply.get("ai_score")

        # Safety bound 0–10
        if ai_score is not None:
            ai_score = max(0, min(float(ai_score), 10))
            ai_score = round(ai_score, 1)  # e.g., 5.6, 7.8

    except Exception as e:
        print("OpenAI GPT Error:", e)

    # --- Fallback if GPT fails ---
    if ai_score is None:
        score = (
            engagement_rate * 4 +  # 40% weight -> scale to 0–10
            min(like_follower_ratio, 1) * 2.5 +  # cap ratio at 1
            min(activity_level / 10, 1) * 2 +  # normalize activity
            min(followers / 1_000_000, 1) * 1.5  # follower base fraction
        )
        ai_score = round(max(0, min(score, 10)), 1)

    return {
        "engagement_rate": round(engagement_rate * 100, 2),  # for display %
        "like_follower_ratio": round(like_follower_ratio, 2),
        "activity_level": round(activity_level, 2),
        "ai_score": ai_score
    }

def analyze_tiktok_insights(profile, videos, range_key):
    followers = int(profile.get("follower_count", 0) or 0)

    # Filter by date (requires created_time in videos)
    selected = range_filter(videos, range_key)

    post_count = len(selected)
    total_views = sum(int(v.get("views", 0) or 0) for v in selected)
    total_likes = sum(int(v.get("likes", 0) or 0) for v in selected)
    total_comments = sum(int(v.get("comments", 0) or 0) for v in selected)

    engagement_rate = (total_likes + total_comments + total_views) / max(followers, 1)
    engagement_percent = round(engagement_rate * 100, 2)

    avg_views = round(total_views / post_count, 2) if post_count else 0

    # FIX 1: Correct top content function
    from apps.dashboard.utils import top_content
    top = top_content(selected, platform="tiktok")

    # ---------------- AI ONLY ----------------
    prompt = f"""
    TikTok Insights:
    Followers: {followers}
    Posts: {post_count}
    Views: {total_views}
    Likes: {total_likes}
    Comments: {total_comments}
    Engagement: {engagement_percent}

    Return JSON:
    {{
        "ai_score": float,
        "growth_rate": float,
        "new_followers": int,
        "avg_views_per_post": float,
        "growth_suggestions": []
    }}
    """

    ai = call_ai(prompt)
    if not ai:
        return None

    return {
        "engagement_rate": engagement_percent,
        "posts_this_range": post_count,
        "avg_views_per_post": ai.get("avg_views_per_post", avg_views),
        "ai_score": ai["ai_score"] * 10,
        "new_followers": ai.get("new_followers", 0),
        "growth_rate": ai.get("growth_rate", 0),
        "top_content": top,
        "growth_suggestions": ai.get("growth_suggestions", []),
        "analysis_mode": "ai"
    }