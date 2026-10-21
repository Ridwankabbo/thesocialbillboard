import requests
from django.conf import settings


def get_top_tiktok_video_url(username):
    url = "https://tiktok-api23.p.rapidapi.com/user/posts"
    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": "tiktok-api23.p.rapidapi.com"
    }
    params = {
        "username": username,
        "limit": 4  # fetch more videos for better comparison
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        posts = data.get("data", [])
        if not posts:
            return None  # No video found

        # Find video with max views
        top_video = max(posts, key=lambda v: int(v.get("stats", {}).get("playCount", 0)))

        video_id = top_video.get("id")
        video_url = top_video.get("video", {}).get("url")

        return {
            "video_id": video_id,
            "caption": top_video.get("desc", ""),
            "views": int(top_video.get("stats", {}).get("playCount", 0)),
            "video_url": video_url or f"https://www.tiktok.com/@{username}/video/{video_id}"
        }

    except requests.RequestException as e:
        print(f"TikTok API error: {e}")
        return None
    