import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.utils import timezone
from isodate import parse_duration
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

from .models import YouTubeVideoCache

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


RISK_KEYWORDS = [
    "violence",
    "violent",
    "blood",
    "gore",
    "kill",
    "murder",
    "gun",
    "weapon",
    "horror",
    "scary",
    "terror",
    "adult",
    "sex",
    "sexual",
    "drugs",
    "alcohol",
    "swear",
    "curse",
    "explicit",
]

EMOTIONAL_TONES = {
    "calm",
    "energetic",
    "playful",
    "neutral",
    "intense",
    "dramatic",
    "soothing",
    "excited",
}


def _parse_age_band(child_age_band: str) -> Tuple[int, int]:
    if not child_age_band:
        return 0, 18
    try:
        if "-" in child_age_band:
            age_min, age_max = child_age_band.split("-", 1)
            return int(age_min.strip()), int(age_max.strip())
        value = int(child_age_band.strip())
        return value, value
    except Exception:
        return 0, 18


def _clamp_score(value, default: int = 0) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return default


def _normalize_risk_flags(value) -> List[str]:
    if not isinstance(value, list):
        return []
    cleaned = []
    seen = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            cleaned.append(normalized)
    return cleaned


def _normalize_emotional_tone(value: str) -> str:
    tone = (value or "").strip().lower()
    return tone if tone in EMOTIONAL_TONES else "neutral"


def _language_to_codes(language: Optional[str]) -> List[str]:
    if not language:
        return ["en"]

    normalized = language.strip().lower()
    mapping = {
        "english": ["en"],
        "hindi": ["hi"],
        "spanish": ["es"],
        "french": ["fr"],
        "german": ["de"],
        "urdu": ["ur"],
    }
    if normalized in mapping:
        return mapping[normalized]
    if len(normalized) == 2 and normalized.isalpha():
        return [normalized]
    return [normalized[:2]]


def _find_risk_hits(text: str) -> List[str]:
    """Match whole words only so titles like 'counting skills' are not flagged for 'kill'."""
    hits = []
    seen = set()
    for keyword in RISK_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text, flags=re.IGNORECASE):
            normalized = keyword.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                hits.append(normalized)
    return hits


def _passes_tone_filter(analysis: Dict, filters: Dict) -> bool:
    desired = (filters.get("tone") or "").strip().lower()
    if not desired:
        return True
    actual = _normalize_emotional_tone(analysis.get("emotional_tone", "neutral"))
    if "calm" in desired and actual in {"intense", "dramatic"}:
        return False
    if "energetic" in desired or "playful" in desired:
        return True
    return True


def is_video_suitable(analysis: Dict, filters: Dict, *, relaxed: bool = False) -> bool:
    if _normalize_risk_flags(analysis.get("risk_flags")):
        return False

    safety_score = _clamp_score(analysis.get("safety_score"), default=0)
    approved = bool(analysis.get("suitable")) or bool(analysis.get("approved"))

    if approved:
        if relaxed:
            return True
        return _passes_tone_filter(analysis, filters)

    if relaxed and safety_score >= 55:
        return True

    return False


def _build_fallback_analysis(video: YouTubeVideoCache, child_age_band: str, filters: Dict) -> Dict:
    age_min, age_max = _parse_age_band(child_age_band)
    text_source = "\n".join(
        [
            video.transcript_text or "",
            video.title or "",
            video.description or "",
        ]
    ).lower()
    risk_hits = _find_risk_hits(text_source)
    has_transcript = bool(video.transcript_text)
    description_length = len(video.description or "")
    confidence = "high" if has_transcript else "medium" if description_length > 80 else "low"

    safety_score = 92 - (len(risk_hits) * 18)
    if not has_transcript:
        safety_score -= 12

    educational_score = 55
    educational_keywords = [
        "learn",
        "education",
        "science",
        "math",
        "story",
        "history",
        "nature",
        "reading",
        "phonics",
        "count",
    ]
    for keyword in educational_keywords:
        if keyword in text_source:
            educational_score += 4
    educational_score = min(100, educational_score)

    tone = "calm"
    intense_keywords = ["fight", "battle", "scary", "horror", "panic", "scream"]
    energetic_keywords = ["dance", "challenge", "fast", "exciting", "adventure"]
    if any(keyword in text_source for keyword in intense_keywords):
        tone = "intense"
    elif any(keyword in text_source for keyword in energetic_keywords):
        tone = "energetic"

    has_metadata = description_length > 25 or len((video.title or "").strip()) > 8
    approved = not risk_hits and (has_transcript or has_metadata)
    reason = (
        "Transcript-based screening found no mature themes and the content appears age-appropriate."
        if approved and has_transcript
        else "Metadata-based screening suggests the content may be suitable, but transcript verification was unavailable."
        if approved
        else "Potential safety risks were detected in the available transcript or metadata."
    )

    return {
        "video_id": video.video_id,
        "age_min": age_min,
        "age_max": age_max,
        "approved": approved,
        "safety_score": _clamp_score(safety_score, default=0),
        "educational_score": _clamp_score(educational_score, default=0),
        "emotional_tone": tone,
        "risk_flags": risk_hits,
        "reason": reason,
        "has_transcript": has_transcript,
        "analysis_source": "fallback",
        "confidence": confidence,
        "suitable": approved,
        "filters": {
            "content_type": filters.get("content_type"),
            "tone": filters.get("tone"),
            "language": filters.get("language"),
        },
    }


def _normalize_llm_analysis(raw_analysis: Dict, video: YouTubeVideoCache, child_age_band: str, filters: Dict) -> Dict:
    age_min, age_max = _parse_age_band(child_age_band)
    risk_flags = _normalize_risk_flags(raw_analysis.get("risk_flags"))
    approved = bool(raw_analysis.get("approved"))
    has_transcript = bool(video.transcript_text)
    confidence = "high" if has_transcript else "medium"

    analysis = {
        "video_id": video.video_id,
        "age_min": int(raw_analysis.get("age_min", age_min) or age_min),
        "age_max": int(raw_analysis.get("age_max", age_max) or age_max),
        "approved": approved,
        "safety_score": _clamp_score(raw_analysis.get("safety_score"), default=0),
        "educational_score": _clamp_score(raw_analysis.get("educational_score"), default=0),
        "emotional_tone": _normalize_emotional_tone(raw_analysis.get("emotional_tone", "neutral")),
        "risk_flags": risk_flags,
        "reason": (raw_analysis.get("reason") or "").strip() or "No explanation provided.",
        "has_transcript": has_transcript,
        "analysis_source": "openai",
        "confidence": confidence,
        "suitable": approved,
        "filters": {
            "content_type": filters.get("content_type"),
            "tone": filters.get("tone"),
            "language": filters.get("language"),
        },
    }

    if not has_transcript:
        analysis["reason"] = (
            f"{analysis['reason']} Transcript unavailable, so this is a metadata-assisted assessment."
        ).strip()

    return analysis


def _build_analysis_prompt(video: YouTubeVideoCache, child_age_band: str, filters: Dict) -> str:
    age_min, age_max = _parse_age_band(child_age_band)
    transcript_excerpt = (video.transcript_text or "").strip()
    if transcript_excerpt:
        transcript_excerpt = transcript_excerpt[:12000]
    else:
        transcript_excerpt = "TRANSCRIPT_UNAVAILABLE"

    return f"""
You are evaluating a YouTube video for a children's playlist curation engine.

Return ONLY valid JSON with this exact shape:
{{
  "video_id": "{video.video_id}",
  "age_min": {age_min},
  "age_max": {age_max},
  "approved": true,
  "safety_score": 91,
  "educational_score": 84,
  "emotional_tone": "calm",
  "risk_flags": [],
  "reason": "Suitable nature education video with calm tone and no detected mature themes."
}}

Rules:
- `approved` must be false if the content appears unsafe for ages {age_min}-{age_max}.
- `safety_score` and `educational_score` must be integers from 0 to 100.
- `emotional_tone` must be one of: calm, energetic, playful, neutral, intense, dramatic, soothing, excited.
- `risk_flags` must be short lowercase strings.
- If transcript is unavailable, rely on metadata more conservatively.
- Do not include markdown or any text outside JSON.

Child age band: {child_age_band or "unknown"}
Desired content type: {filters.get("content_type") or "not specified"}
Desired tone: {filters.get("tone") or "not specified"}
Language preference: {filters.get("language") or "not specified"}

Video metadata:
Title: {video.title or ""}
Description: {video.description or ""}
Duration seconds: {video.duration or 0}
Published at: {video.publish_date.isoformat() if video.publish_date else "unknown"}

Transcript excerpt:
{transcript_excerpt}
""".strip()


def _analyze_video_with_openai(video: YouTubeVideoCache, child_age_band: str, filters: Dict) -> Optional[Dict]:
    if not getattr(settings, "OPENAI_API_KEY", None):
        return None

    model = getattr(settings, "PARENTS_PLAYLIST_OPENAI_MODEL", "gpt-4o-mini")
    prompt = _build_analysis_prompt(video, child_age_band, filters)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a strict JSON API for child-safety video analysis. Return JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=400,
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return None
        return json.loads(content)
    except Exception as exc:
        logger.warning("OpenAI video analysis failed for %s: %s", video.video_id, exc)
        return None


def _parse_duration_seconds(iso_duration: str) -> int:
    try:
        return int(parse_duration(iso_duration).total_seconds())
    except Exception:
        return 0



def _playlist_search_queries(filters: Dict) -> List[str]:
    content_type = filters.get("content_type", "")
    tone = filters.get("tone", "")
    time_of_day = filters.get("time_of_day", "")
    language = filters.get("language", "")
    age_band = filters.get("age_band", "")
    session_length = filters.get("session_length", "")
    admin_prompt = (filters.get("admin_prompt") or "").strip()[:120]

    duration_str = f"{session_length} minutes" if session_length else ""

    primary_parts = [content_type, tone, time_of_day, age_band, language, duration_str, admin_prompt]
    primary = " ".join([p for p in primary_parts if p]).strip()

    queries = [
        primary,
        " ".join([content_type, "kids", age_band, language, duration_str]).strip(),
        " ".join([content_type, "children", tone, duration_str]).strip(),
        " ".join([content_type, "kids educational videos", duration_str]).strip(),
        " ".join(["children learning videos", duration_str]).strip(),
        " ".join(["kids", content_type, duration_str]).strip(),
    ]
    seen = set()
    ordered = []
    for query in queries:
        normalized = " ".join(query.split())
        if normalized and normalized.lower() not in seen:
            seen.add(normalized.lower())
            ordered.append(normalized)
    return ordered

MIN_LONG_FORM_SECONDS = 600


# def _session_length_duration_range(session_length: Optional[int]) -> Tuple[int, int]:
#     if not isinstance(session_length, int) or session_length <= 0:
#         return 600, 3600

#     if session_length == 10:
#         return 7 * 60, 12 * 60
#     if session_length == 20:
#         return 15 * 60, 25 * 60
#     if session_length == 30:
#         return 25 * 60, 35 * 60

#     lower = max(60, int(session_length * 0.7) * 60)
#     upper = int(session_length * 1.3) * 60
#     return lower, upper

def _session_length_duration_range(session_length: Optional[int]) -> Tuple[int, int]:
    if not isinstance(session_length, int) or session_length <= 0:
        return 120, 3600  # Allow down to 2-minute videos

    if session_length == 10:
        return 90, 480    # Allow 1.5 mins to 8 mins video items
    if session_length == 20:
        return 120, 900   # Allow 2 mins to 15 mins video items
        
    lower = max(60, int(session_length * 0.4) * 60)
    upper = int(session_length * 1.3) * 60
    return lower, upper


def _filters_min_duration_seconds(filters):
    session_length = filters.get("session_length")
    if isinstance(session_length, int):
        min_duration, _ = _session_length_duration_range(session_length)
        return min_duration

    age_band = filters.get("age_band")
    mapping = {
        "3-5": 180,     # 3 min
        "6-8": 300,     # 5 min
        "9-12": 420,    # 7 min
        "13-14": 480,   # 8 min
        "15-16": 600,   # 10 min
        "17-18": 600,
    }
    return mapping.get(age_band, MIN_LONG_FORM_SECONDS)


def _filters_max_duration_seconds(filters) -> Optional[int]:
    session_length = filters.get("session_length")
    if isinstance(session_length, int):
        _, max_duration = _session_length_duration_range(session_length)
        return max_duration
    return None


def _youtube_search(
    query: str,
    *,
    safe_search: str,
    language: str,
    max_results: int,
    min_duration_seconds: int = MIN_LONG_FORM_SECONDS,
    max_duration_seconds: Optional[int] = None,
) -> List[Dict]:
    try:
        search_params = {
            "part": "snippet",
            "q": query,
            "maxResults": max_results,
            "type": "video",
            "safeSearch": safe_search,
            "relevanceLanguage": "en",
            "key": settings.YOUTUBE_API_KEY,
        }

        response = requests.get("https://www.googleapis.com/youtube/v3/search", params=search_params, timeout=20)
        response.raise_for_status()
        resp = response.json()
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            logger.error(
                "YouTube API token limit reached or quota exceeded during search. Please check your API usage."
            )
        else:
            logger.error("YouTube search failed for query '%s': %s", query, e)
        return []

    video_order: List[str] = []
    for item in resp.get("items", []):
        video_id = None
        item_id = item.get("id", {})
        if isinstance(item_id, dict):
            video_id = item_id.get("videoId")
        elif isinstance(item_id, str):
            video_id = item_id
        if video_id:
            video_order.append(video_id)

    if not video_order:
        return []

    try:
        details_params = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_order),
            "maxResults": max_results,
            "key": settings.YOUTUBE_API_KEY,
        }
        details_response = requests.get("https://www.googleapis.com/youtube/v3/videos", params=details_params, timeout=20)
        details_response.raise_for_status()
        details_resp = details_response.json()
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            logger.error("YouTube API token limit reached or quota exceeded while fetching video details.")
        else:
            logger.error("YouTube video details failed for query '%s': %s", query, e)
        return []

    details_by_id = {item.get("id"): item for item in details_resp.get("items", [])}
    items: List[Dict] = []

    for video_id in video_order:
        detail = details_by_id.get(video_id)
        if not detail:
            continue

        duration_iso = detail.get("contentDetails", {}).get("duration", "")
        duration_seconds = _parse_duration_seconds(duration_iso)
        
        if duration_seconds <= 60:
            continue
            
        if max_duration_seconds is not None and duration_seconds > max_duration_seconds:
            continue

        snippet = detail.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {}) or {}
        thumbnail_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        items.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "duration_seconds": duration_seconds,
                "duration_iso": duration_iso,
                "thumbnail_url": thumbnail_url,
            }
        )

    return items


def youtube_search_candidates(filters: Dict) -> List[Dict]:
    age_band = filters.get("age_band", "")
    language = filters.get("language", "")

    safe_search = "strict"
    if age_band in ("15-16", "17-18"):
        safe_search = "moderate"

    max_results = int(getattr(settings, "PARENTS_PLAYLIST_SEARCH_MAX_RESULTS", 50))
    seen_ids = set()
    merged: List[Dict] = []
    min_duration_seconds = _filters_min_duration_seconds(filters)
    max_duration_seconds = _filters_max_duration_seconds(filters)

    for query in _playlist_search_queries(filters):
        if len(merged) >= 100:
            break
        batch = _youtube_search(
            query,
            safe_search=safe_search,
            language=language,
            max_results=max_results,
            min_duration_seconds=min_duration_seconds,
            max_duration_seconds=max_duration_seconds,
        )
        for item in batch:
            vid = item["video_id"]
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            merged.append(item)
            if len(merged) >= 100:
                break

    return merged


def fetch_video_details(video_ids: List[str]) -> None:
    if not video_ids:
        return

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            params = {
                "part": "snippet,contentDetails",
                "id": ",".join(batch),
                "key": settings.YOUTUBE_API_KEY,
            }
            response = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params, timeout=20)
            response.raise_for_status()
            resp = response.json()
        except Exception as e:
            error_msg = str(e).lower()
            if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
                logger.error("YouTube API token limit reached or quota exceeded while fetching video details.")
            else:
                logger.error("YouTube video details failed: %s", e)
            continue

        for item in resp.get("items", []):
            vid = item.get("id")
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            duration = _parse_duration_seconds(content_details.get("duration", ""))
            publish_date = None
            published_at = snippet.get("publishedAt")
            if published_at:
                try:
                    publish_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except Exception:
                    publish_date = None

            YouTubeVideoCache.objects.update_or_create(
                video_id=vid,
                defaults={
                    "channel_id": snippet.get("channelId", ""),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "duration": duration,
                    "publish_date": publish_date,
                },
            )


def _fetch_transcript_via_captions_api(video_id: str, access_token: str, preferred_languages: List[str]) -> Optional[str]:
    list_url = "https://www.googleapis.com/youtube/v3/captions"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.get(list_url, headers=headers, params={"part": "snippet", "videoId": video_id}, timeout=20)
        data = res.json() if res.status_code < 400 else {}
    except Exception:
        return None

    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        return None

    def score(item):
        lang = (item.get("snippet", {}) or {}).get("language", "")
        is_pref = lang in preferred_languages
        kind = (item.get("snippet", {}) or {}).get("trackKind", "")
        return (1 if is_pref else 0, 0 if kind == "ASR" else 1)

    items.sort(key=score, reverse=True)
    caption_id = items[0].get("id")
    if not caption_id:
        return None

    download_url = f"https://www.googleapis.com/youtube/v3/captions/{caption_id}"
    try:
        srt_res = requests.get(download_url, headers=headers, params={"tfmt": "srt"}, timeout=20)
        if srt_res.status_code >= 400:
            return None
        srt_text = srt_res.text
    except Exception:
        return None

    cleaned_lines = []
    for line in srt_text.splitlines():
        if re.match(r"^\d+$", line.strip()):
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}", line.strip()):
            continue
        if line.strip():
            cleaned_lines.append(line.strip())

    return " ".join(cleaned_lines).strip() or None


def fetch_transcript(video_id: str, language: Optional[str] = None, youtube_access_token: Optional[str] = None) -> Tuple[Optional[str], str]:
    preferred_languages = _language_to_codes(language)

    if youtube_access_token:
        text = _fetch_transcript_via_captions_api(video_id, youtube_access_token, preferred_languages)
        if text:
            return text, "captions_api"

    try:
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=preferred_languages)
        text = " ".join([x.get("text", "") for x in data]).strip()
        if text:
            return text, "youtube_transcript_api"
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "403" in error_msg or "rate limit" in error_msg:
            logger.error(f"YouTubeTranscriptApi token limit reached or blocked for {video_id}.")
        else:
            logger.error(f"YouTubeTranscriptApi failed for {video_id}: {e}")
        pass

    return None, "none"


def analyze_video_for_age_safety(video: YouTubeVideoCache, child_age_band: str, filters: Dict) -> Dict:
    llm_analysis = _analyze_video_with_openai(video, child_age_band, filters)
    if llm_analysis:
        return _normalize_llm_analysis(llm_analysis, video, child_age_band, filters)
    return _build_fallback_analysis(video, child_age_band, filters)


# def build_playlist(candidate_videos: List[Dict], session_length_minutes: int) -> List[Dict]:
#     if not candidate_videos:
#         return []

#     target_seconds = max(int(session_length_minutes or 0), 1) * 60
#     valid_candidates = [item for item in candidate_videos if int(item.get("duration") or 0) > 0]
#     if not valid_candidates:
#         return [candidate_videos[0]]

#     dp = {0: []}
#     for item in valid_candidates:
#         duration = int(item.get("duration") or 0)
#         current_states = list(dp.items())
#         for total, selected in current_states:
#             new_total = total + duration
#             if new_total > target_seconds:
#                 continue
#             candidate_selection = selected + [item]
#             existing = dp.get(new_total)
#             if existing is None or len(candidate_selection) > len(existing):
#                 dp[new_total] = candidate_selection

#     if dp:
#         best_total = max(dp.keys())
#         selected = dp.get(best_total) or []
#         if selected:
#             return selected

#     for item in candidate_videos:
#         duration = int(item.get("duration") or 0)
#         if duration <= target_seconds:
#             return [item]

#     return [candidate_videos[0]]

def build_playlist(candidate_videos: List[Dict], session_length_minutes: int) -> List[Dict]:
    if not candidate_videos:
        return []

    target_seconds = max(int(session_length_minutes or 0), 1) * 60
    
    # Filter out invalid durations
    valid_candidates = [item for item in candidate_videos if int(item.get("duration") or 0) > 0]
    if not valid_candidates:
        return []

    selected: List[Dict] = []
    current_duration = 0

    # To fit 5 videos, calculate a baseline ideal duration per video
    # For a 40-minute playlist, we ideally want videos averaging ~8 minutes or less
    ideal_max_duration = target_seconds / 5  

    # Sort candidates so that videos fitting our ideal duration constraints are evaluated first
    sorted_candidates = sorted(
        valid_candidates,
        key=lambda x: (int(x.get("duration", 0)) > ideal_max_duration, x.get("duration", 0))
    )

    # First Pass: Try to fill up to target duration while matching filters
    for item in sorted_candidates:
        item_duration = int(item.get("duration") or 0)
        
        # Keep adding if it fits inside our timeframe (with a small 2-minute buffer)
        if current_duration + item_duration <= target_seconds + 120:
            selected.append(item)
            current_duration += item_duration
        
        # Stop early only if we met BOTH targets
        if current_duration >= target_seconds and len(selected) >= 5:
            break

    # Second Pass (The Enforcer Fallback): If we have fewer than 5 videos,
    # force include items from the remaining candidates even if it overflows the time budget
    if len(selected) < 5:
        for item in sorted_candidates:
            if item not in selected:
                selected.append(item)
                current_duration += int(item.get("duration") or 0)
                if len(selected) == 5:
                    break

    # Assign positions sequentially for serialization
    for index, item in enumerate(selected, start=1):
        item["position"] = index

    return selected

def select_suitable_playlist_items(evaluations: List[Dict], filters: Dict) -> List[Dict]:
    strict = [entry["item"] for entry in evaluations if is_video_suitable(entry["analysis"], filters)]
    if strict:
        return strict

    relaxed = [
        entry["item"]
        for entry in evaluations
        if is_video_suitable(entry["analysis"], filters, relaxed=True)
    ]
    if relaxed:
        return relaxed

    ranked = sorted(
        evaluations,
        key=lambda entry: _clamp_score(entry["analysis"].get("safety_score"), default=0),
        reverse=True,
    )
    fallback = []
    for entry in ranked[:5]:
        analysis = entry["analysis"]
        if _normalize_risk_flags(analysis.get("risk_flags")):
            continue
        if _clamp_score(analysis.get("safety_score"), default=0) >= 45:
            fallback.append(entry["item"])
    return fallback


def describe_playlist_generation_failure(
    *,
    candidates: int,
    evaluated: int,
    suitable_strict: int,
    suitable_relaxed: int,
    selected: int,
) -> str:
    if candidates == 0:
        return (
            "No YouTube videos were found for this filter set. "
            "Check YOUTUBE_API_KEY and try broader filters."
        )
    if evaluated == 0:
        return "Videos were found but could not be evaluated. Check server logs for API errors."
    if selected == 0 and suitable_relaxed == 0:
        return (
            f"No videos passed child-safety screening ({evaluated} evaluated). "
            "Try different content type or tone filters."
        )
    if selected == 0:
        return (
            f"{suitable_relaxed} videos passed screening but none fit the "
            f"{candidates and 'requested session length' or 'session length'}."
        )
    if selected < 5:
        return (
            f"Could only find {selected} child-safe videos matching your criteria, "
            f"but a minimum of 5 videos is required. Please broaden your tone or content-type filters."
        )
    return "Playlist generation failed for an unknown reason."


def generate_suitability_explanation(playlist, items: List[Dict], child_age_band: str, filters: Dict) -> str:
    content_type = filters.get("content_type", "mixed content")
    tone = filters.get("tone", "balanced")
    language = filters.get("language", "your selected language")
    session = filters.get("session_length", playlist.session_length or "")

    transcript_count = sum(1 for i in items if i.get("has_transcript"))
    total = len(items)
    transcript_note = "Transcripts were available for most videos." if transcript_count >= max(1, total // 2) else "Some videos do not have transcripts, so we used titles and descriptions conservatively."

    return (
        f"This playlist is tailored for the {child_age_band} age band with {content_type} content, "
        f"a {tone} tone, and a {session} minute session length. "
        f"Language preference: {language}. "
        f"We avoid topics that may be unsafe for this age range. {transcript_note}"
    )

""" 
    ============================
        Transcript fetching 
    ============================
"""
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
)

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled


def fetch_youtube_transcript(video_id):
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    return transcript.to_raw_data()



def build_full_text(transcript):
    return " ".join([t["text"] for t in transcript])


def get_transcript(video_id):
    try:
        transcript = fetch_youtube_transcript(video_id)

        full_text = build_full_text(transcript)

        return {
            "full_text": full_text,
            "word_count": len(full_text.split()),
            "coverage": min(len(transcript) / 10, 1.0),
            "source": "youtube",
            "raw": transcript
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "disabled" in error_msg:
            err_text = "Transcripts are disabled for this video."
        elif "quota" in error_msg or "403" in error_msg or "rate limit" in error_msg:
            err_text = "YouTube API token limit reached."
        else:
            err_text = f"Failed to fetch transcript: {str(e)}"
            
        return {
            "full_text": "",
            "word_count": 0,
            "coverage": 0,
            "source": "failed",
            "error": err_text
        }