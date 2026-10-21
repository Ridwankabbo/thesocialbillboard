import logging
import re
import requests
import googleapiclient.discovery
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def extract_youtube_channel_id(link):
    """
    Extracts the channel ID from a YouTube URL.
    Supports full channel links, user links, and handle-based links (@username).
    """
    if "youtube.com/channel/" in link:
        match = re.search(r"youtube\.com/channel/([a-zA-Z0-9_-]+)", link)
        return match.group(1) if match else None

    elif "youtube.com/user/" in link:
        username = link.split("youtube.com/user/")[-1].strip("/")
        return get_channel_id_by_username(username)

    elif "youtube.com/@" in link:
        handle = link.split("youtube.com/@")[-1].strip("/")
        return get_channel_id_by_handle(handle)

    return None

def get_channel_id_by_username(username):
    """
    Uses the YouTube API to resolve a channel ID from a username.
    """
    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
        request = youtube.channels().list(
            part="id",
            forUsername=username
        )
        response = request.execute()
        if response.get('items'):
            return response['items'][0]['id']
    except Exception as e:
        error_msg = str(e).lower()
        if "quotaexceeded" in error_msg or "rate limit" in error_msg or "403" in error_msg:
            logger.error(f"YouTube API token limit reached while fetching channel ID for username {username}.")
        else:
            logger.error(f"Failed to fetch channel ID by username {username}: {e}")
    return None

def get_channel_id_by_handle(handle):
    """
    Resolves a YouTube handle (e.g., @BBC) to a channel ID using web scraping or alternate API.
    Currently uses a workaround via requests and redirect.
    """
    try:
        response = requests.get(f"https://www.youtube.com/@{handle}", allow_redirects=True)
        match = re.search(r'"channelId":"(UC[\w-]{22})"', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        logger.error(f"Failed to resolve handle @{handle}: {e}")
    return None
