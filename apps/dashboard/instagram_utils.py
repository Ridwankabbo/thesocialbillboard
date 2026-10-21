import json
import requests
from django.conf import settings
from openai import OpenAI
from apps.dashboard.utils import range_filter, call_ai

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# ============================================================
# 1) FETCH INSTAGRAM USER INFO
# ============================================================
def fetch_instagram_user_info(username: str):
    url = f"https://{settings.RAPIDAPI_HOST}/userinfo/"
    headers = {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": settings.RAPIDAPI_HOST,
    }

    try:
        r = requests.get(url, headers=headers, params={"username_or_id": username}, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {})

        return {
            "username": data.get("username", ""),
            "full_name": data.get("full_name", ""),
            "bio": data.get("biography", ""),
            "profile_pic_url": data.get("profile_pic_url_hd", ""),
            "is_verified": data.get("is_verified", False),
            "is_private": data.get("is_private", False),

            "follower_count": data.get("follower_count", 0),
            "following_count": data.get("following_count", 0),
            "post_count": data.get("media_count", 0),

            "category_name": data.get("category_name", ""),
            "external_url": data.get("external_url", ""),
        }

    except Exception as e:
        print("IG profile fetch error:", e)
        return {"error": str(e)}


# ============================================================
# 2) FETCH INSTAGRAM POSTS  (REAL ENDPOINT: /user/posts/)
# ============================================================
def fetch_instagram_posts(username, count=30):
    url = f"https://{settings.RAPIDAPI_HOST}/user/posts/"
    headers = {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": settings.RAPIDAPI_HOST,
    }

    try:
        r = requests.get(url, headers=headers, params={"username_or_id": username}, timeout=10)
        r.raise_for_status()

        items = r.json().get("data", {}).get("items", [])

        posts = []
        for p in items[:count]:
            posts.append({
                "likes": p.get("like_count", 0),
                "comments": p.get("comment_count", 0),
                "views": p.get("play_count", 0) or p.get("view_count", 0),
                "caption": p.get("caption_text", ""),
                "thumbnail": p.get("thumbnail_url", ""),
                "media_type": p.get("media_type", ""),

                # CRITICAL FOR range_filter()
                "created_time": p.get("device_timestamp"),
            })

        return posts

    except Exception as e:
        print("IG posts fetch error:", e)
        return []


# ============================================================
# 3) INSIGHT ENGINE (USED IN DASHBOARD)
# ============================================================
def analyze_instagram_insights(profile, posts, range_key):
    followers = int(profile.get("follower_count", 0))

    # STEP–1 Filter by last 7d/30d/90d
    selected = range_filter(posts, range_key)

    post_count = len(selected)
    total_views = sum(p.get("views", 0) for p in selected)
    total_likes = sum(p.get("likes", 0) for p in selected)
    total_comments = sum(p.get("comments", 0) for p in selected)

    avg_view_per_post = total_views / post_count if post_count else 0
    engagement_rate = ((total_likes + total_comments + total_views) / max(followers, 1)) * 100

    # STEP–2 AI Engine
    prompt = f"""
    Instagram Insights Data:

    Followers: {followers}
    Posts in Range: {post_count}
    Total Views: {total_views}
    Total Likes: {total_likes}
    Total Comments: {total_comments}
    Engagement Rate (%): {engagement_rate}
    Avg Views/Post: {avg_view_per_post}

    Return EXACT JSON:
    {{
      "ai_score": float,
      "growth_rate": float,
      "new_followers": int,
      "avg_views_per_post": float,
      "growth_suggestions": ["string", "string", "string"]
    }}
    """

    ai = call_ai(prompt)

    if not ai or "ai_score" not in ai:
        ai = {
            "ai_score": 0.0,
            "growth_rate": 0.0,
            "new_followers": 0,
            "avg_views_per_post": avg_view_per_post,
            "growth_suggestions": []
        }

    # STEP–3 Top content
    top_items = sorted(selected, key=lambda p: int(p.get("views", 0)), reverse=True)[:4]

    return {
        "engagement_rate": round(engagement_rate, 2),
        "posts": post_count,
        "avg_view_per_post": ai.get("avg_views_per_post", avg_view_per_post),
        "ai_score": ai["ai_score"] * 10,
        "new_followers": ai.get("new_followers", 0),
        "growth_rate": ai.get("growth_rate", 0),
        "top_content": top_items,
        "growth_suggestions": ai.get("growth_suggestions", []),
    }
def analyze_instagram_data_with_openai(insta_data: dict) -> dict:
    """
    Use GPT to analyze Instagram data and compute ai_score (0–10 scale).
    Ensures score is realistic, never exactly 0 or 10.
    """
    followers = insta_data.get("follower_count", 0)
    posts = insta_data.get("post_count", 0)
    likes = insta_data.get("like_count", 0)

    engagement_rate = (likes / max(followers, 1))
    activity_level = posts / max(followers / 1000, 1)

    prompt = f"""
    You are an Instagram analytics expert. Analyze this account and return ONLY JSON:
    Account Data:
      Followers: {followers}
      Posts: {posts}
      Likes: {likes}
      Engagement Rate (0–1): {engagement_rate}
      Activity Level (posts per 1k followers): {activity_level}

    Compute ai_score (float 0–10), realistic, never exactly 0 or 10.
    Weighting:
      Engagement Rate → 50%
      Activity Level → 30%
      Followers (diminishing returns) → 20%
    Return like: {{"ai_score": 7.5}}
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
        if ai_score is not None:
            # Round & safety bound (0.1–9.9)
            ai_score = round(float(ai_score), 1)
            ai_score = max(0.1, min(ai_score, 9.9))
    except Exception as e:
        print("OpenAI GPT Error:", e)

    # Fallback if GPT fails
    if ai_score is None:
        score = (
            min(engagement_rate * 50, 5) +
            min(activity_level * 3, 3) +
            min(followers / 10_000_000, 1) * 2
        )
        ai_score = round(max(0.1, min(score, 9.9)), 1)

    return {
        "engagement_rate": round(engagement_rate * 100, 2),
        "activity_level": round(activity_level, 2),
        "ai_score": ai_score
    }