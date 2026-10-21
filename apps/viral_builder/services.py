import json
import re
from datetime import datetime, timezone
from typing import Any

import requests
from django.conf import settings
from openai import OpenAI

from apps.creator_dashboard.models import (
    TiktokCredentials,
    InstagramCredentials,
    PlatformChoices,
)
from apps.dashboard import youtube_utils

from .prompts import build_viral_builder_prompt


DEFAULT_RECENT_VIDEO_LIMIT = 25


def get_recent_youtube_videos(channel_id: str, limit: int | None = None) -> list[dict]:
    limit = limit or getattr(settings, "VIRAL_BUILDER_RECENT_VIDEOS_LIMIT", DEFAULT_RECENT_VIDEO_LIMIT)
    channel_data = youtube_utils.fetch_youtube_channel_data(channel_id)
    if not channel_data:
        return []

    uploads_id = channel_data.get("uploads_id")
    if not uploads_id:
        return []

    recent = youtube_utils.fetch_youtube_recent_videos(uploads_id, limit=limit)
    video_ids = [v["video_id"] for v in recent]
    stats_map = youtube_utils.fetch_youtube_video_stats(video_ids)

    enriched = []
    for item in recent:
        vid = item["video_id"]
        stats = stats_map.get(vid, {})
        enriched.append(
            {
                "video_id": vid,
                "title": item.get("title", ""),
                "published_at": item.get("published_at"),
                "views": stats.get("views", 0),
                "likes": stats.get("likes", 0),
                "comments": stats.get("comments", 0),
            }
        )
    return enriched


def summarize_channel_themes(videos: list[dict]) -> list[str]:
    stopwords = {
        "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "with", "at", "from", "by",
        "how", "what", "why", "is", "are", "you", "your", "i", "we", "our", "my", "this", "that",
    }
    counts: dict[str, int] = {}
    for video in videos:
        title = video.get("title", "").lower()
        for word in re.findall(r"[a-z0-9']+", title):
            if len(word) < 3 or word in stopwords:
                continue
            counts[word] = counts.get(word, 0) + 1

    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:8]]


def _seconds_since(iso_time: str | None) -> int:
    if not iso_time:
        return 0
    try:
        if iso_time.endswith("Z"):
            dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(iso_time)
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return 0


def fetch_tiktok_signals(user) -> dict[str, Any] | None:
    """Fetch TikTok signals using the new CreatorProfile -> TiktokCredentials pattern."""
    try:
        creds = TiktokCredentials.objects.filter(
            profile__user=user,
            platform=PlatformChoices.TIKTOK,
            access_token__isnull=False,
        ).exclude(access_token="").first()
    except Exception:
        return None

    if not creds or not creds.access_token:
        return None

    url = "https://open.tiktokapis.com/v2/video/list/"
    fields = [
        "id",
        "title",
        "create_time",
        "like_count",
        "comment_count",
        "share_count",
        "view_count",
        "duration",
    ]

    try:
        res = requests.post(
            url,
            params={"fields": ",".join(fields)},
            headers={
                "Authorization": f"Bearer {creds.access_token}",
                "Content-Type": "application/json",
            },
            json={"max_count": 10},
            timeout=20,
        )
        data = res.json()
        if res.status_code >= 400:
            return {"connected": True, "error": data}
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    videos = data.get("data", {}).get("videos", []) or []
    if not videos:
        return {"connected": True, "recent_videos": []}

    velocity_notes = []
    duration_buckets: dict[str, int] = {}
    trimmed = []
    for vid in videos:
        views = int(vid.get("view_count", 0) or 0)
        created = vid.get("create_time")
        seconds = _seconds_since(created)
        days = max(int(seconds / 86400), 1)
        velocity = round(views / days, 2)
        velocity_notes.append(velocity)

        duration = int(vid.get("duration", 0) or 0)
        if duration <= 20:
            bucket = "0-20s"
        elif duration <= 40:
            bucket = "21-40s"
        elif duration <= 60:
            bucket = "41-60s"
        else:
            bucket = "60s+"
        duration_buckets[bucket] = duration_buckets.get(bucket, 0) + 1

        trimmed.append(
            {
                "title": vid.get("title", ""),
                "views": views,
                "likes": int(vid.get("like_count", 0) or 0),
                "comments": int(vid.get("comment_count", 0) or 0),
                "duration": duration,
                "velocity_per_day": velocity,
            }
        )

    avg_velocity = round(sum(velocity_notes) / len(velocity_notes), 2) if velocity_notes else 0
    top_buckets = sorted(duration_buckets.items(), key=lambda x: x[1], reverse=True)

    return {
        "connected": True,
        "recent_videos": trimmed,
        "avg_velocity_per_day": avg_velocity,
        "duration_patterns": [b for b, _ in top_buckets[:3]],
    }


def fetch_instagram_signals(user) -> dict[str, Any] | None:
    """Fetch Instagram signals using the new CreatorProfile -> InstagramCredentials pattern."""
    try:
        creds = InstagramCredentials.objects.filter(
            profile__user=user,
            platform=PlatformChoices.INSTAGRAM,
            access_token__isnull=False,
        ).exclude(access_token="").first()
    except Exception:
        return None

    if not creds or not creds.access_token:
        return None

    url = "https://graph.instagram.com/me/media"
    params = {
        "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count,permalink",
        "access_token": creds.access_token,
        "limit": 10,
    }

    try:
        res = requests.get(url, params=params, timeout=20)
        data = res.json()
        if res.status_code >= 400:
            return {"connected": True, "error": data}
    except Exception as exc:
        return {"connected": True, "error": str(exc)}

    items = data.get("data", []) or []
    if not items:
        return {"connected": True, "recent_posts": []}

    velocity_notes = []
    format_counts: dict[str, int] = {}
    trimmed = []
    for item in items:
        likes = int(item.get("like_count", 0) or 0)
        comments = int(item.get("comments_count", 0) or 0)
        total_engagement = likes + comments
        seconds = _seconds_since(item.get("timestamp"))
        days = max(int(seconds / 86400), 1)
        velocity = round(total_engagement / days, 2)
        velocity_notes.append(velocity)

        media_type = (item.get("media_type") or "unknown").lower()
        format_counts[media_type] = format_counts.get(media_type, 0) + 1

        trimmed.append(
            {
                "media_type": media_type,
                "likes": likes,
                "comments": comments,
                "engagement_per_day": velocity,
            }
        )

    avg_velocity = round(sum(velocity_notes) / len(velocity_notes), 2) if velocity_notes else 0
    top_formats = sorted(format_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "connected": True,
        "recent_posts": trimmed,
        "avg_engagement_per_day": avg_velocity,
        "format_patterns": [f for f, _ in top_formats[:3]],
    }


def basic_safety_filter(text: str) -> list[str]:
    flags = []
    lowered = text.lower()

    if any(term in lowered for term in ["guarantee", "guaranteed", "overnight", "instant", "secret hack"]):
        flags.append("hype_or_guarantee")

    if any(term in lowered for term in ["hate", "violence", "self-harm", "explicit", "scam"]):
        flags.append("safety_risk")

    return flags


def sanitize_idea(idea: dict) -> dict:
    return {
        "headline": str(idea.get("headline", "")).strip(),
        "suggested_title": str(idea.get("suggested_title", "")).strip(),
        "hook_structure": str(idea.get("hook_structure", "")).strip(),
        "format_guidance": str(idea.get("format_guidance", "")).strip(),
        "suggested_cta": str(idea.get("suggested_cta", "")).strip(),
        "why_fits_channel": str(idea.get("why_fits_channel", "")).strip(),
        "tags": idea.get("tags") or [],
        "safety_flags": idea.get("safety_flags") or [],
        "viral_gap": idea.get("viral_gap") or {},
    }


def generate_viral_ideas(payload: dict) -> list[dict]:
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise ValueError("OpenAI API key is missing.")

    client = OpenAI(api_key=api_key)
    model = getattr(settings, "VIRAL_BUILDER_OPENAI_MODEL", "gpt-4o-mini")

    prompt = build_viral_builder_prompt(payload)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return ONLY JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI JSON parse error: {exc}") from exc

    ideas = data.get("ideas", []) or []
    return [sanitize_idea(idea) for idea in ideas]


def humanize_generation_error(exc: Exception) -> str:
    raw = str(exc or "")
    lowered = raw.lower()

    if "insufficient_quota" in lowered or "you exceeded your current quota" in lowered:
        return "OpenAI quota exceeded. Check your OpenAI project billing/credits and try again."

    if "rate_limit" in lowered or "429" in lowered:
        return "OpenAI rate limit reached. Please retry in a short while."

    if "www.googleapis.com" in lowered and ("timed out" in lowered or "connecttimeout" in lowered):
        return "YouTube API timeout. Please retry in a few moments."

    return raw
