import json
from googleapiclient.discovery import build
from django.conf import settings
from openai import OpenAI
from apps.payment_stripe.views import HasPackage1Subscription
from rest_framework import permissions
# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


    # Convert age range to text
def convert_age_range_to_text(age_range_str):
    """
    Converts age range like "5-8" or "13+" to "5+", "13+" format.
    """
    if not age_range_str or age_range_str.lower() == "unknown":
        return "N/A"

    try:
        if "-" in age_range_str:
            min_age = age_range_str.split("-")[0].strip()
            return f"{min_age}+"
        elif "+" in age_range_str:
            return age_range_str.strip()
        else:
            return "N/A"
    except Exception:
        return "N/A"



def get_ai_rating(kid_age, comment):
    prompt = f"""
Return ONLY valid JSON with this structure:
{{
  "age_appropriateness": string,
  "educational_value": string,
  "emotional_impact": string,
  "cultural_sensitivity": string
}}

Analyze the following parent's review:
Kid Age: {kid_age}
Comment: {comment}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict JSON API. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        print("OpenAI Error (get_ai_rating):", e)
        return {
            "age_appropriateness": "",
            "educational_value": "",
            "emotional_impact": "",
            "cultural_sensitivity": ""
        }

# =============================
# GPT: AI summary
# =============================
def generate_ai_summary(channel_info):
    prompt = f"""
Return ONLY valid JSON with this structure:
{{
  "safe_for_age": "string",
  "badge": "string",
  "badge_reason": "string",
  "rated_by": number,
  "trending": true/false
}}

Analyze this YouTube channel data:
Title: {channel_info['title']}
Description: {channel_info.get('description', '')}
Country: {channel_info.get('country', 'N/A')}
Subscribers: {channel_info['subscriberCount']}
Total Views: {channel_info['viewCount']}
Videos: {channel_info['videoCount']}
Engagement Rate: {channel_info['engagementRate']}%
Is In Top 10 Trending: {channel_info.get('is_in_top_10', False)}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict JSON API. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print("OpenAI Error (AI Summary):", e)
        return {
            "safe_for_age": "Unknown",
            "badge": "None",
            "badge_reason": "Could not analyze",
            "rated_by": 0,
            "trending": False
        }


# =============================
# GPT: Age rating (detailed)
# =============================
def generate_age_rating(channel_info):
    permission_classes = [permissions.IsAuthenticated, HasPackage1Subscription]
    prompt = f"""
Return ONLY valid JSON with this structure:
{{
  "age_appropriateness": float (0.0 to 10.0),
  "educational_value": float (0.0 to 10.0),
  "emotional_impact": float (0.0 to 10.0),
  "cultural_sensitivity": float (0.0 to 10.0),
  "safe_reason": "string"
}}

Analyze this YouTube channel data:
Title: {channel_info['title']}
Description: {channel_info.get('description', '')}
Country: {channel_info.get('country', 'N/A')}
Subscribers: {channel_info['subscriberCount']}
Total Views: {channel_info['viewCount']}
Videos: {channel_info['videoCount']}
Engagement Rate: {channel_info['engagementRate']}%
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict JSON API. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print("OpenAI Error (Age Rating):", e)
        return {
            "age_appropriateness": "",
            "educational_value": "",
            "emotional_impact": "",
            "cultural_sensitivity": "",
            "safe_reason": ""
        }


# =============================
# Helper: Calculate AI Score
# =============================
def calculate_ai_score(rating_data: dict) -> str:
    # permission_classes = [permissions.IsAuthenticated, HasPackage1Subscription]
    try:    
        scores = [
            rating_data.get("age_appropriateness", 0),
            rating_data.get("educational_value", 0),
            rating_data.get("emotional_impact", 0),
            rating_data.get("cultural_sensitivity", 0),
        ]
    except (ValueError, TypeError):
        scores = [0.0, 0.0, 0.0, 0.0]
    valid_scores = [s for s in scores if s is not None]
    score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
    if score > 8:
        return "Stellar"
    elif score > 5:
        return "Solid"
    elif score > 3:
        return "Balanced"
    elif score > 0:
        return "Fading"
    else:
        return "N/A"


# =============================
# GPT: Age range for channel
# =============================
def get_age_range_for_channel(title, description):
    prompt = f"""
Return ONLY valid JSON with this structure:
{{
  "recommended_age_range": "string",
  "reason": "string"
}}

Analyze the following YouTube channel and determine the most appropriate audience age range:
Title: {title}
Description: {description}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict JSON API. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print("OpenAI Error (Age Range):", e)
        return {"recommended_age_range": "Unknown", "reason": "Could not analyze"}


# =============================
# Grab 3 tags 
# =============================
def generate_tags_from_text(title, description):
    prompt = f"""
Analyze the following YouTube channel title and description and return ONLY JSON with exactly 3 relevant tags:
{{
  "tags": ["tag1", "tag2", "tag3"]
}}

Title: {title}
Description: {description}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI that only returns JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        return json.loads(response.choices[0].message.content.strip()).get("tags", [])
    except Exception as e:
        print("OpenAI Tag Error:", e)
        return []


# =============================
# Helper: Parent count based on score
# =============================
def get_parent_count_for_score(score: float) -> int:
    return int(20 + (score * 2)) if score is not None else 0


# =============================
# Helper: keyword for score
# =============================
def get_keyword_for_score(score, metric_type):
    try:
        score = float(score)
    except (ValueError, TypeError):
        score = 0.0

    # ক্লায়েন্টের গাইডলাইন অনুযায়ী ৫ এর নিচের কিওয়ার্ড ফিক্সিং
    if score < 5.0:
        if metric_type == "age": return "Restricted"
        if metric_type == "educational": return "Needs Structure"
        if metric_type == "emotional": return "Extreme Intensity"
        if metric_type == "sensitivity": return "Requires Revision"
        if metric_type == "cultural_sensitivity": return "Requires Revision" # অতিরিক্ত সেফটি চেক

    if metric_type == "age":
        if score >= 9.0: return "All Ages"
        if score >= 7.0: return "Teens & Older"
        return "Mature Audience"
        
    elif metric_type == "educational":
        if score >= 8.5: return "Actionable Insights"
        if score >= 6.5: return "Foundational"
        return "Introductory"
        
    elif metric_type == "emotional":
        if score >= 8.5: return "Balanced & Calm"
        if score >= 6.5: return "Engaging & Energetic"
        return "High Intensity"
        
    elif metric_type in ["sensitivity", "cultural_sensitivity"]:
        if score >= 8.5: return "Globally Safe"
        if score >= 6.5: return "Neutral Context"
        return "Review Advised"
    
    
# =============================
# Get dynamic trending top 10 channels
# =============================
def get_trending_top_10(count):
    youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    regions = ["US", "GB", "IN", "JP", "KR", "BR"]
    all_videos = []

    for region in regions:
        try:
            resp = youtube.videos().list(
                part="snippet,statistics", 
                chart="mostPopular",
                regionCode=region,
                maxResults=10
            ).execute()

            for item in resp['items']:
                video_id = item['id']
                snippet = item['snippet']
                stats = item.get('statistics', {})
                video_data = {
                    "video_id": video_id,
                    "title": snippet['title'],
                    "channel_title": snippet['channelTitle'],
                    "thumbnail": snippet['thumbnails']['high']['url'],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "view_count": stats.get('viewCount', '0'),
                    "age_rating": "G"  # Assume kid-safe content for simplicity
                }
                all_videos.append(video_data)

        except Exception as e:
            error_msg = str(e).lower()
            if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
                print(f"YouTube API token limit reached while fetching trending videos for region {region}.")
            else:
                print(f"Error fetching region {region}: {e}")

    # Remove duplicates by video_id
    unique_videos = {video["video_id"]: video for video in all_videos}.values()

    return list(unique_videos)[:count]


# =============================
# Get channel top videos
# =============================
def get_channel_top_videos(channel_id, count):
    youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    try:
        # Search for popular videos in the channel sorted by view count
        search_resp = youtube.search().list(
            channelId=channel_id,
            part="id",
            order="viewCount",
            type="video",
            maxResults=count
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_resp.get('items', [])]
        if not video_ids:
            return []

        # Fetch details & statistics for these videos
        videos_resp = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids)
        ).execute()

        channel_videos = []
        for item in videos_resp.get('items', []):
            video_id = item['id']
            snippet = item['snippet']
            stats = item.get('statistics', {})
            video_data = {
                "video_id": video_id,
                "title": snippet['title'],
                "channel_title": snippet['channelTitle'],
                "thumbnail": snippet['thumbnails']['high']['url'],
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "view_count": stats.get('viewCount', '0'),
                "age_rating": "G"  # Assume kid-safe content for simplicity
            }
            channel_videos.append(video_data)
        
        return channel_videos

    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching top videos for channel {channel_id}.")
        else:
            print(f"Error fetching channel top videos for {channel_id}: {e}")
        return []



# =============================
# Main: Get channel overview
# =============================
def get_channel_overview(channel_input):
    youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    trending_top_10_list = get_trending_top_10(count=10)

    try:
        # Fetch channel details
        response = youtube.channels().list(
            part="snippet,statistics,contentDetails,topicDetails",
            id=channel_input
        ).execute()

        if not response.get('items'):
            return None

        channel = response['items'][0]
        channel_id = channel['id']

        # Basic stats
        sub_count = int(channel['statistics'].get('subscriberCount', 0))
        view_count = int(channel['statistics'].get('viewCount', 0))
        video_count = int(channel['statistics'].get('videoCount', 0))
        avg_views = view_count // video_count if video_count > 0 else 0
        engagement_rate = round((avg_views / sub_count) * 100, 2) if sub_count > 0 else 0

        # Growth rate (dummy last week)
        last_week_subs = sub_count - 500
        growth_rate = round(((sub_count - last_week_subs) / last_week_subs) * 100, 2) if last_week_subs > 0 else 0

        # Category fetch
        category_name = "Unknown"
        try:
            uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            playlist_items = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=1
            ).execute()

            if playlist_items["items"]:
                first_video_id = playlist_items["items"][0]["contentDetails"]["videoId"]
                video_details = youtube.videos().list(
                    part="snippet",
                    id=first_video_id
                ).execute()

                if video_details["items"]:
                    category_id = video_details["items"][0]["snippet"]["categoryId"]
                    #  remove regionCode when using id
                    category_response = youtube.videoCategories().list(
                        part="snippet",
                        id=category_id
                    ).execute()

                    if category_response["items"]:
                        category_name = category_response["items"][0]["snippet"]["title"]
        except Exception as e:
            print("Category fetch error:", e)

        # Base channel data
        base_data = {
            "channelId": channel_id,
            "title": channel['snippet']['title'],
            "description": channel['snippet'].get('description', ''),
            "thumbnail": channel['snippet']['thumbnails']['default']['url'],
            "country": channel['snippet'].get('country', 'N/A'),
            "subscriberCount": sub_count,
            "viewCount": view_count,
            "videoCount": video_count,
            "avgViewsPerVideo": avg_views,
            "engagementRate": engagement_rate,
            "is_in_top_10": channel_id in trending_top_10_list,
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "created_at": channel['snippet'].get('publishedAt'),
            "category": category_name,
            "growth_rate_last_week": growth_rate
        }

        # GPT / AI analysis
        ai_summary = generate_ai_summary(base_data)
        age_rating_raw = generate_age_rating(base_data)
        ai_score = calculate_ai_score(age_rating_raw)
        age_range_analysis = get_age_range_for_channel(base_data["title"], base_data["description"])
        tags = generate_tags_from_text(base_data['title'], base_data['description'])

        # Rating with parent count
        rating_with_parents = {
            "age_appropriateness": {
                "score": get_keyword_for_score(age_rating_raw.get("age_appropriateness", 0), "age"),
                "parents_rated": get_parent_count_for_score(age_rating_raw.get("age_appropriateness", 0)),
            },
            "educational_value": {
                "score": get_keyword_for_score(age_rating_raw.get("educational_value", 0), "educational"),
                "parents_rated": get_parent_count_for_score(age_rating_raw.get("educational_value", 0))
            },
            "emotional_impact": {
                "score": get_keyword_for_score(age_rating_raw.get("emotional_impact", 0), "emotional"),
                "parents_rated": get_parent_count_for_score(age_rating_raw.get("emotional_impact", 0))
            },
            "cultural_sensitivity": {
                "score": get_keyword_for_score(age_rating_raw.get("cultural_sensitivity", 0), "sensitivity"),
                "parents_rated": get_parent_count_for_score(age_rating_raw.get("cultural_sensitivity", 0))
            },
            "safe_reason": age_rating_raw.get("safe_reason", "")
        }

        # Merge all data
        base_data.update(ai_summary)
        base_data["ai_score"] = ai_score
        base_data["RatingAnalysis"] = rating_with_parents
        base_data["AgeRangeAnalysis"] = age_range_analysis
        base_data["tags"] = tags

        return base_data

    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching overview for channel {channel_input}.")
        else:
            print("Error fetching channel:", e)
        return None


def get_video_overview(video_id):
    youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)

    try:
        response = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        ).execute()

        if not response.get("items"):
            return None

        video = response["items"][0]
        snippet = video["snippet"]

        tags = generate_tags_from_text(
            snippet.get("title", ""),
            snippet.get("description", "")
        )

        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "tags": tags,
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            print(f"YouTube API token limit reached while fetching overview for video {video_id}.")
        else:
            print("Video overview error:", e)
        return None
