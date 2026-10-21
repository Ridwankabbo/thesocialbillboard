import requests
import openai
from django.conf import settings
YOUTUBE_API_KEY = settings.YOUTUBE_API_KEY
OPENAI_API_KEY = settings.OPENAI_API_KEY
openai.api_key = OPENAI_API_KEY


def get_channel_details(channel_id):
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics",
        "id": channel_id,
        "key": YOUTUBE_API_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()

    if not data.get("items"):
        return None

    item = data["items"][0]
    snippet = item["snippet"]
    stats = item["statistics"]
    channel_url = f"https://www.youtube.com/channel/{item['id']}"

    return {
        "name": snippet["title"],
        "description": snippet["description"],
        "thumbnail_url": snippet["thumbnails"]["high"]["url"],
        "profile_photo_url": snippet["thumbnails"]["default"]["url"],
        "followers": int(stats.get("subscriberCount", 0)),
        "channel_url": channel_url
    }


def search_channels_by_query(query, max_results=10):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()

    return [item["snippet"]["channelId"] for item in data.get("items", [])]


def get_age_rating_from_openai(title, description):
    prompt = f"""
Title: {title}
Description: {description}

Based on the title, description, transcript, and visual style, what is the most suitable age range for this video?
Choose from: 3-5, 6-8, 9-12, 13+. Justify the age category with examples of content cues.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a children's content classifier."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        reply = response['choices'][0]['message']['content']
        for age in ["3-5", "6-8", "9-12", "13+"]:
            if age in reply:
                return age, reply.strip()

        return "Unknown", reply.strip()

    except Exception as e:
        return "Error", str(e)
