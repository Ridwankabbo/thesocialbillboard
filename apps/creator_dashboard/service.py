# views.py
from django.shortcuts import redirect
from django.conf import settings
import secrets
import uuid
import requests
from urllib.parse import urlencode, quote
from django.core import signing
from .utils import BaseAPIView
from rest_framework import status
from rest_framework.response import Response
from datetime import datetime
from .models import (
    CreatorProfile,
    PlatformChoices,
    TiktokProfile,
    YoutubeProfile,
    InstagramProfile,
    TiktokCredentials,
    YoutubeCredentials,
    InstagramCredentials,
    TiktokProfileMedia,
    YoutubeProfileMedia,
    InstagramProfileMedia
)
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.viral_builder.models import PlatformAccount

from .utils import generate_code_verifier, generate_code_challenge, generate_code_verifier_from_state_id

User = get_user_model()


""" ============================= HELPER METHODS ========================== """

def save_tokens(user, platform, token_json):
    profile, created = CreatorProfile.objects.get_or_create(user=user)

    defaults = {
        "access_token": token_json.get("access_token"),
        "access_expires_in": token_json.get("expires_in"),
        "scope": token_json.get("scope"),
        "token_type": token_json.get("token_type", "Bearer"),
        "updated_at": timezone.now()
    }
    
    if token_json.get("refresh_token"):
        defaults["refresh_token"] = token_json.get("refresh_token")

    if platform == PlatformChoices.TIKTOK:
        credentials, created = TiktokCredentials.objects.update_or_create(
            profile=profile,
            defaults={
                **defaults,
                "platform": platform,
                "open_id": token_json.get("open_id"),
                "refresh_expires_in": token_json.get("refresh_expires_in"),
            }
        )
    elif platform == PlatformChoices.YOUTUBE:
        credentials, created = YoutubeCredentials.objects.update_or_create(
            profile=profile,
            defaults={
                **defaults,
                "platform": platform,
                "open_id": token_json.get("open_id"),
            }
        )
    elif platform == PlatformChoices.INSTAGRAM:
        credentials, created = InstagramCredentials.objects.update_or_create(
            profile=profile,
            defaults={
                **defaults,
                "platform": platform,
            }
        )

    return credentials
    


""" =========================================================================== """


"""
    ============================
        START TIKTOK SERVICE 
    ============================
"""

def save_tiktok_profile(profile, user_data):
    defaults = {
        "tiktok_user_id": user_data.get("open_id"),
        "username": user_data.get("display_name"),
        "followers_count": int(user_data.get("follower_count") or 0),
        "following_count": int(user_data.get("following_count") or 0),
        "view_count": int(user_data.get("view_count") or 0),
        "video_count": int(user_data.get("video_count") or 0),
        "updated_at": timezone.now(),
    }

    TiktokProfile.objects.update_or_create(profile=profile, defaults=defaults)

# ================ LOGIN SERVICE =============
def tiktok_login(request):
    state_nonce = str(uuid.uuid4())
    state_payload = {
        "uid": request.user.id,
        "nonce": state_nonce,
    }
    state = signing.dumps(state_payload, salt="tiktok_auth")

    code_verifier = generate_code_verifier_from_state_id(state_nonce)
    code_challenge = generate_code_challenge(code_verifier)

    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={settings.TIKTOK_CLIENT_KEY}"
        "&response_type=code"
        "&scope=user.info.basic,user.info.profile,user.info.stats,video.list"
        f"&redirect_uri={quote(settings.TIKTOK_REDIRECT_URI, safe='')}"
        f"&state={quote(state, safe='')}"
        f"&code_challenge={code_challenge}"
        "&code_challenge_method=S256"
    )

    return auth_url


def get_and_save_tiktok_user_info(access_token):
    url = "https://open.tiktokapis.com/v2/user/info/"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    params = {
        "fields": "open_id,union_id,avatar_url,display_name,follower_count,likes_count,video_count"
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        return {"error": "Failed to fetch user info", "details": response.json()}

    return response.json().get("data", {}).get("user", {})


# ================ CALLBACK SERVICE ============
def tiktok_callback_service(request):   
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    if error:
        raise Exception(error)

    if not code or not state:
        raise Exception("Missing code or state")

    try:
        state_payload = signing.loads(state, salt="tiktok_auth", max_age=600)
    except signing.SignatureExpired:
        raise Exception("State expired")
    except signing.BadSignature:
        raise Exception("Invalid state")

    user_id = state_payload.get("uid")
    state_nonce = state_payload.get("nonce")

    if not user_id or not state_nonce:
        raise Exception("Invalid state")

    try:
        user = User.objects.get(id=int(user_id))
    except (ValueError, User.DoesNotExist):
        raise Exception("Invalid user")

    code_verifier = generate_code_verifier_from_state_id(state_nonce)
    if not code_verifier:
        raise Exception("Missing code verifier")

    # Exchange code for token
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"

    data = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(token_url, data=data, headers=headers)
    token_json = response.json()
    access_token = token_json.get("access_token")

    save_tokens(user, PlatformChoices.TIKTOK, token_json)

    user_data = get_and_save_tiktok_user_info(access_token)

    profile, _ = CreatorProfile.objects.get_or_create(user=user)

    save_tiktok_profile(profile, user_data)

    # Create or update PlatformAccount for viral_builder compatibility
    PlatformAccount.objects.update_or_create(
        user=user,
        platform="tiktok",
        external_id=user_data.get("open_id"),
        defaults={
            "display_name": user_data.get("display_name"),
            "profile_url": f"https://www.tiktok.com/@{user_data.get('display_name')}",
            "meta": user_data,
        }
    )
    
    user.tiktok_link = True
    user.save()

    return token_json
# ================ PROFILE DETAILS SERVICES =============
def titkok_profile_details_service(profile_instance, access_token):
  
    user_url = "https://open.tiktokapis.com/v2/user/info/"
    if not access_token:
        print("Missing access token")
        return None
    fields = "open_id,display_name,avatar_url,follower_count,likes_count,video_count,views_count"
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    params = {
        "fields": fields
    }

    try:
        response = requests.get(user_url, headers=headers, params=params)
        response_data = response.json()
        
        user_data = response_data.get("data", {}).get("user")

        if response.status_code == 200 and user_data:
            TiktokProfile.objects.update_or_create(
                profile=profile_instance,
                defaults={
                    "tiktok_user_id": user_data.get("open_id"),
                    "username": user_data.get("display_name"),
                    "followers_count": int(user_data.get("follower_count") or 0),
                    "following_count": int(user_data.get("following_count") or 0),
                    "video_count": int(user_data.get("video_count") or 0),
                    "view_count": int(user_data.get("views_count") or 0),
                    "updated_at": timezone.now(),
                }
            )
            print(f"Updated TikTok profile: {profile_instance}")
            return profile_instance

        print(f"TikTok Profile Error: {response_data}")
        return None

    except Exception as e:
        print(f"Request failed: {e}")
        return None
    
# ================ GET ALL TIKTOK VIDEOS =============

def get_tiktok_timestrap(create_time):
    
    from datetime import datetime, timezone
    
    if not create_time:
        return None
    try:
        time = datetime.fromtimestamp(int(create_time), tz=timezone.utc)
        return time
    except (ValueError, TypeError):
        return None



def get_all_titok_videos(profile, access_token):
    fields = "id,title,view_count,like_count,comment_count,share_count,create_time"
    TIKTOK_VIDEO_LIST_URL = f"https://open.tiktokapis.com/v2/video/list/?fields={fields}"
    
    all_videos = []
    
    cursor = 0
    while True:
        request = requests.post(
            TIKTOK_VIDEO_LIST_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                # "access_token":f"{access_token}",
                "cursor": cursor,
                "max_count":20
            }
        )
        
        response = request.json()
        
        if "data" not in response:
            raise Exception(f"Error: {response}")
            return []
        
        videos = response["data"].get("videos", [])
      
        for v in videos:
            video_id = v.get("id")
            title = v.get('title')
            like_count =v.get('like_count')
            comment_count = v.get('comment_count')
            view_count = v.get('view_count')
            share_count = v.get('share_count')

           
            created_at = get_tiktok_timestrap(v.get('create_time'))
            
            try:
                video_profile =TiktokProfileMedia.objects.update_or_create(
                    profile=profile,
                    platform = PlatformChoices.TIKTOK,
                    video_id=video_id,                
                    defaults={
                        "title":title,
                        "likes_count":like_count,
                        "view_count":view_count,
                        "comment_count":comment_count,
                        "share_count":share_count,
                        "created_at": created_at
                    }
                )
            except TiktokProfileMedia.DoesNotExist :
                return "No Video not found"

        has_more = response["data"].get("has_more", False)
        cursor = response["data"].get("cursor", 0)
        
        if not has_more:
            break
    
    return TiktokProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.TIKTOK)


def _should_refresh_platform(platform, target):
    if platform is None:
        return True
    if isinstance(platform, str):
        return platform.lower() == target.lower()
    return platform == target


def refresh_tiktok_data(profile, access_token):
    if not access_token:
        raise Exception("Missing TikTok access token")

    get_all_titok_videos(profile, access_token)
    user_data = get_and_save_tiktok_user_info(access_token)
    if user_data:
        save_tiktok_profile(profile, user_data)

    return TiktokProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.TIKTOK)


def refresh_youtube_data(profile, access_token):
    if not access_token:
        raise Exception("Missing YouTube access token")

    try:
        sync_youtube_videos(profile, access_token)
    except Exception as e:
        if "401 Unauthorized" in str(e):
            new_token = refresh_youtube_token(profile)
            sync_youtube_videos(profile, new_token)
        else:
            raise

    return YoutubeProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.YOUTUBE)


def refresh_instagram_data(profile, access_token):
    if not access_token:
        raise Exception("Missing Instagram access token")

    return sync_instagram_media(profile, access_token)


def refresh_profile_data(profile, platform=None):
    results = {}

    if _should_refresh_platform(platform, "tiktok"):
        creds = TiktokCredentials.objects.filter(profile=profile).first()
        if creds:
            results["tiktok"] = refresh_tiktok_data(profile, creds.access_token)
        elif platform is not None:
            raise Exception("TikTok not connected")

    if _should_refresh_platform(platform, "youtube"):
        creds = YoutubeCredentials.objects.filter(profile=profile, platform=PlatformChoices.YOUTUBE).first()
        if creds:
            results["youtube"] = refresh_youtube_data(profile, creds.access_token)
        elif platform is not None:
            raise Exception("YouTube not connected")

    if _should_refresh_platform(platform, "instagram"):
        creds = InstagramCredentials.objects.filter(profile=profile, platform=PlatformChoices.INSTAGRAM).first()
        if creds:
            results["instagram"] = refresh_instagram_data(profile, creds.access_token)
        elif platform is not None:
            raise Exception("Instagram not connected")

    return results


# ================ GET VIDEOS METRICS =============
def get_videos_metrics(access_token, video_idS):
    fields  = "id,view_count,like_count,comment_count,share_count"
    TIKTOK_VIDEO_QUERY_URL = f"https://open.tiktokapis.com/v2/video/query/?fields={fields}"

    response = requests.post(
        TIKTOK_VIDEO_QUERY_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "filters": {
                "video_ids": video_idS
            } 
        }
    )    
    
    return response.json()
    
# ================ REFRESH TOKEN SERVICES =============
def refresh_tiktok_token_service(profile_instance):
    try:
        creds = TiktokCredentials.objects.get(profile=profile_instance, platform=PlatformChoices.TIKTOK)
    except TiktokCredentials.DoesNotExist:
        raise Exception("TikTok credentials not found")

    if not creds or not creds.refresh_token:
        raise Exception("No refresh token available")

    url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "grant_type": 'refresh_token',
        "refresh_token": creds.refresh_token,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(url, data=data, headers=headers)
    new_tokens = res.json()
    print("TikTok token refresh response:", new_tokens)
    creds.access_token = new_tokens.get('access_token')
    creds.refresh_token = new_tokens.get('refresh_token')
    creds.refresh_expires_in = new_tokens.get('refresh_expires_in')
    if new_tokens.get('expires_in'):
        creds.access_expires_in = new_tokens.get('expires_in')
    creds.updated_at = timezone.now()
    creds.save()

    return "tiktok refresh token updated"

"""
    =========================
        END TIKTOK SERVICE 
    =========================
"""







"""
    ==============================
        STRART YOUTUBE SERVICE 
    ==============================
"""
from googleapiclient.discovery import build
from urllib.parse import urlencode
YOUTUBE_API_KEY=settings.YOUTUBE_API_KEY

import requests, re

YOUTUBE_CLIENT_ID= settings.GOOGLE_CLIENT_ID
YOUTUBE_CLIENT_SECRET=settings.GOOGLE_CLIENT_SECRET
YOUTUBE_REDIRECT_URL = settings.YOUTUBE_REDIRECT_URI
TEST_YOUTUBE_REDIRECT_URI = settings.TEST_YOUTUBE_REDIRECT_URI

def save_youtube_profile_meta(profile, channel):
    description = channel["snippet"].get("description", "") or ""
    defaults = {
        "youtube_channel_id": channel["id"],
        "channel_title": channel["snippet"]["title"],
        "channel_description": description[:255],
        "subscribers_count": int(channel["statistics"].get("subscriberCount") or 0),
        "view_count": int(channel["statistics"].get("viewCount") or 0),
        "video_count": int(channel["statistics"].get("videoCount") or 0),
        "updated_at": timezone.now(),
    }

    YoutubeProfile.objects.update_or_create(profile=profile, defaults=defaults)
    
    

    
    

# ==================== YOUTUBE AUTH SERVICE ==============
def youtube_auth(request):
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth?"
    state = str(request.user.id)
    params = {
        "client_id": YOUTUBE_CLIENT_ID,
        "redirect_uri": YOUTUBE_REDIRECT_URL,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
        "prompt": "consent select_account",
        "state": state,
    }
    auth_url = GOOGLE_AUTH_URL+urlencode(params)
    
    
    return auth_url
# ==================== YOUTUBE CALLBACK ==================
def youtube_callback_service(request):
    code = request.GET.get("code")
    state = request.GET.get('state') 
    user_id = re.sub(r"\D", "", state)   
    user = User.objects.get(id=int(user_id))

    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": YOUTUBE_REDIRECT_URL,
        }
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")
    save_tokens(user, PlatformChoices.YOUTUBE, token_json)

    yt_res = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"part": "snippet,statistics", "mine": "true"}
    )
    yt_data = yt_res.json()
    if "error" in yt_data:
        raise Exception(yt_data["error"].get("message", str(yt_data["error"])))
    if not yt_data.get("items"):
        raise Exception("No YouTube channel found for this Google account.")
    channel = yt_data["items"][0]
    profile = CreatorProfile.objects.get(user=user)

    save_youtube_profile_meta(profile, channel)

    # Create or update PlatformAccount for viral_builder compatibility
    PlatformAccount.objects.update_or_create(
        user=user,
        platform="youtube",
        external_id=channel["id"],
        defaults={
            "display_name": channel["snippet"]["title"],
            "profile_url": f"https://www.youtube.com/channel/{channel['id']}",
            "meta": channel,
        }
    )
    user.youtube_link = True
    user.save()
    print(yt_data)
    return yt_data
# ==================== REFRESH YOUTUBE TOKEN ==================
def refresh_youtube_token(profile):
    try:
        creds = YoutubeCredentials.objects.get(profile=profile, platform=PlatformChoices.YOUTUBE)
    except YoutubeCredentials.DoesNotExist:
        raise Exception("YouTube credentials not found")
    
    if not creds.refresh_token:
        return {"error": "No refresh token available"},
        
    res = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": creds.refresh_token,
            "grant_type": "refresh_token",
        }
    )
    
    token_json = res.json()

    if "error" in token_json:
        return {"error": "Failed to refresh token", "details": token_json}
        
    creds.access_token = token_json.get("access_token")
    if token_json.get("expires_in"):
        creds.access_expires_in = token_json.get("expires_in")
    creds.updated_at = timezone.now()
    creds.save()
    
    return "YouTube token refreshed successfully"

# ======================= GET UPLOADS PLAYLIST ID ===================
# service.py

def get_uploads_playlist_id(access_token):
    url = "https://www.googleapis.com/youtube/v3/channels"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"part": "contentDetails", "mine": "true"}

    res = requests.get(url, headers=headers, params=params)
    data = res.json()
    
    if res.status_code == 401:
        return {"401 Unauthorized: Invalid or expired access token"}

    if "error" in data:
        error_msg = data["error"].get("message", str(data["error"]))
        return {"error": error_msg}

    if not data.get("items"):
        # If 'items' is empty but there is no 'error' key, 
        # it means the account simply has no YouTube channel.
        return {"error": "No channel found"}

    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# ====================== FETCH VIDEOS FROM PLAYLIST =======================
def get_youtube_videos(access_token, playlist_id):
    url = "https://www.googleapis.com/youtube/v3/playlistItems"

    videos = []
    next_page_token = None

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 20,
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        res = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)
        data = res.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            if res.status_code == 401 or "unauthorized" in error_msg.lower() or "expired" in error_msg.lower():
                raise Exception(f"401 Unauthorized: {error_msg}")
            raise Exception(f"YouTube API Error: {error_msg}")

        for item in data.get("items", []):
            snippet = item["snippet"]

            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "created_at": snippet["publishedAt"]
            })

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return videos


# ======================= GET VIDEO STATUS ====================
def get_video_statistics(access_token, video_ids):
    if not video_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part": "statistics",
        "id": ",".join(video_ids)
    }

    res = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)
    data = res.json()

    if "error" in data:
        error_msg = data["error"].get("message", str(data["error"]))
        if res.status_code == 401 or "unauthorized" in error_msg.lower() or "expired" in error_msg.lower():
            raise Exception(f"401 Unauthorized: {error_msg}")
        raise Exception(f"YouTube API Error: {error_msg}")

    stats_map = {}

    for item in data.get("items", []):
        stats = item["statistics"]

        stats_map[item["id"]] = {
            "view_count": int(stats.get("viewCount", 0)),
            "likes_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
        }

    return stats_map


# =================== YOUTUBE DETAILS ======================
from datetime import datetime

def sync_youtube_videos(profile, access_token):
    playlist_id = get_uploads_playlist_id(access_token)

    if isinstance(playlist_id, dict) and "error" in playlist_id:
        raise Exception(f"YouTube error: {playlist_id['error']}")

    if isinstance(playlist_id, set):
        error_msg = list(playlist_id)[0] if playlist_id else "Unauthorized"
        raise Exception(error_msg)

    if not isinstance(playlist_id, str):
        raise Exception(f"Failed to get playlist ID: {playlist_id}")

    videos = get_youtube_videos(access_token, playlist_id)

    if not videos:
        return YoutubeProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.YOUTUBE)

    video_ids = [v["video_id"] for v in videos]

    stats_map = get_video_statistics(access_token, video_ids)

    for v in videos:
        stats = stats_map.get(v["video_id"], {})

        created_at = datetime.fromisoformat(v["created_at"].replace("Z", "+00:00"))

        YoutubeProfileMedia.objects.update_or_create(
            profile=profile,
            video_id=v["video_id"],
            defaults={
                "platform": PlatformChoices.YOUTUBE,
                "title": v["title"],
                "view_count": stats.get("view_count", 0),
                "likes_count": stats.get("likes_count", 0),
                "comment_count": stats.get("comment_count", 0),
                "created_at": created_at,
            }
        )

    return YoutubeProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.YOUTUBE)
"""
    ==============================
        STOP YOUTUBE SERVICE 
    ==============================
"""


""" ===============================
        INSTAGRAM SERVICE 
    ===============================
"""
# ==================== INSTAGRAM AUTH SERVICE ==============
def instagram_auth(request):
    url = (
        "https://www.instagram.com/oauth/authorize"
        f"?client_id={settings.INSTAGRAM_APP_ID}"
        f"&redirect_uri={settings.INSTAGRAM_REDIRECT_URI}"
        "&scope=instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments,instagram_business_content_publish"
        "&response_type=code"
        f"&state={str(request.user.id)}"
    )
    return url


import requests
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# ================= INSTAGRAM CALLBACK SERVICE =============
def instagram_callback_service(request):
    code = request.GET.get("code")
    user_id = request.GET.get("state")
    if not user_id:
        raise Exception("Missing state (user_id) in callback")

    try:
        user = User.objects.get(id=int(user_id))
    except (ValueError, User.DoesNotExist):
        raise Exception("Invalid user_id in state") 

    # =========================
    # STEP 1: GET SHORT TOKEN
    # =========================
    token_res = requests.post(
        "https://api.instagram.com/oauth/access_token",
        data={
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "code": code,
        }
    )

    token_json = token_res.json()

    if "access_token" not in token_json:
        raise Exception(token_json)

    short_token = token_json["access_token"]

    # =========================
    # STEP 2: LONG-LIVED TOKEN
    # =========================
    long_res = requests.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "access_token": short_token,
        }
    )

    long_json = long_res.json()

    if "access_token" not in long_json:
        raise Exception(long_json)

    access_token = long_json["access_token"]

    # =========================
    # STEP 3: GET USER PROFILE
    # =========================
    profile_res = requests.get(
        "https://graph.instagram.com/me",
        params={
            "fields": "id,username,account_type,media_count,followers_count,follows_count",
            "access_token": access_token,
        }
    )

    profile_data = profile_res.json()

    if "error" in profile_data:
        raise Exception(profile_data)

    # =========================
    # STEP 4: SAVE TO DB
    # =========================
    profile, _ = CreatorProfile.objects.get_or_create(user=user)

    InstagramCredentials.objects.update_or_create(
        profile=profile,
        platform=PlatformChoices.INSTAGRAM,
        defaults={
            "access_token": access_token,
            "token_type": "Bearer",
        }
    )

    InstagramProfile.objects.update_or_create(
        profile=profile,
        defaults={
            "instagram_user_id": profile_data.get("id"),
            "username": profile_data.get("username"),
            "followers_count": int(profile_data.get("followers_count") or 0),
            "following_count": int(profile_data.get("follows_count") or 0),
            "media_count": int(profile_data.get("media_count") or 0),
            "updated_at": timezone.now(),
        }
    )

    # Create or update PlatformAccount for viral_builder compatibility
    PlatformAccount.objects.update_or_create(
        user=user,
        platform="instagram",
        external_id=profile_data["id"],
        defaults={
            "display_name": profile_data.get("username"),
            "profile_url": f"https://www.instagram.com/{profile_data.get('username')}",
            "meta": profile_data,
        }
    )
    
    user.instagram_link = True
    user.save()
    print(long_json)
    return long_json


# ================ REFRESH INSTAGRAM TOKEN =============
def instagram_refresh_token_service(profile_instance):
    try:
        creds = InstagramCredentials.objects.get(profile=profile_instance, platform=PlatformChoices.INSTAGRAM)
    except InstagramCredentials.DoesNotExist:
        return "Instagram credentials not found"

    url = "https://graph.instagram.com/refresh_access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": creds.access_token,
    }

    res = requests.get(url, params=params)
    data = res.json()

    print("Instagram token refresh response:", data)
    if "access_token" not in data:
        raise Exception(f"Failed to refresh token: {data}")

    creds.access_token = data["access_token"]
    creds.access_expires_in = data.get("expires_in")
    creds.updated_at = timezone.now()
    creds.save()

    return "Instagram token refreshed successfully"

# ================ GET INSTAGRAM ACCESS TOKEN =============
def get_instagram_token(user):
    creds = InstagramCredentials.objects.filter(
        profile__user=user,
        platform=PlatformChoices.INSTAGRAM
    ).first()

    if not creds:
        raise Exception("Instagram credentials not found")

    return creds.access_token

# ================ SYNC INSTAGRAM MEDIA =============
def sync_instagram_media(profile, access_token):
    url = "https://graph.instagram.com/me/media"

    params = {
        "fields": "id,caption,media_type,media_url,timestamp",
        "access_token": access_token,
        "limit": 50
    }

    res = requests.get(url, params=params)
    data = res.json()


    if "error" in data:
        raise Exception(f"Instagram API Error: {data['error']}")

    media_list = data.get("data", [])

   
    if not media_list:
        return InstagramProfileMedia.objects.filter(
            profile=profile,
            platform=PlatformChoices.INSTAGRAM
        )

    
    for item in media_list:
        created_at = timezone.now()

        if item.get("timestamp"):
            try:
                created_at = datetime.fromisoformat(
                    item["timestamp"].replace("+0000", "+00:00")
                )
            except Exception:
                pass

        InstagramProfileMedia.objects.update_or_create(
            profile=profile,
            platform=PlatformChoices.INSTAGRAM,
            video_id=item.get("id"),
            defaults={
                "title": item.get("caption", ""),
                "likes_count": 0,      # Not available in Basic API
                "comment_count": 0,    # Not available in Basic API
                "view_count": 0,
                "share_count": 0,
                "created_at": created_at,
            }
        )

    
    return InstagramProfileMedia.objects.filter(
        profile=profile,
        platform=PlatformChoices.INSTAGRAM
    )

def trigger_instagram_sync(media_id):
    """
    Legacy function - fetches and saves media stats
    """
    try:
        access_token = get_instagram_token()

        url = f"https://graph.facebook.com/v19.0/{media_id}"

        res = requests.get(url, params={
            "fields": "id,caption,like_count,comments_count,timestamp",
            "access_token": access_token
        }).json()

        InstagramProfileMedia.objects.update_or_create(
            video_id=media_id,
            defaults={
                "platform": PlatformChoices.INSTAGRAM,
                "title": res.get("caption"),
                "likes_count": res.get("like_count", 0),
                "comment_count": res.get("comments_count", 0),
                "view_count": 0,
                "share_count": 0,
                "created_at": res.get("timestamp"),
            }
        )
    except Exception as e:
        print(f"Error syncing Instagram media: {str(e)}")


# ================ INSTAGRAM WEBHOOK PROCESSING ============
from .models import InstagramWebhookEvent
from datetime import datetime

def process_instagram_webhook_event(webhook_data, profile):
    """
    Process incoming Instagram webhook data and save events to database
    
    Webhook data structure:
    {
        "entry": [{
            "changes": [{
                "value": {
                    "media_id": "...",
                    "caption": "...",
                    "like_count": 10,
                    "comments_count": 5,
                    "timestamp": "2024-01-01T10:00:00+0000"
                }
            }]
        }]
    }
    """
    try:
        for entry in webhook_data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                media_id = value.get("media_id")
                if not media_id:
                    continue
                
                # Determine event type
                event_type = determine_event_type(value)
                
                # Parse timestamp
                timestamp_str = value.get("timestamp")
                timestamp = parse_webhook_timestamp(timestamp_str)
                
                # Create webhook event record
                webhook_event = InstagramWebhookEvent(
                    profile=profile,
                    media_id=media_id,
                    event_type=event_type,
                    caption=value.get("caption"),
                    like_count=value.get("like_count", 0),
                    comment_count=value.get("comments_count", 0),
                    view_count=value.get("view_count", 0),
                    comment_text=value.get("comment_text"),
                    commenter_id=value.get("commenter_id"),
                    reaction_type=value.get("reaction_type"),
                    raw_webhook_data=value,
                    timestamp=timestamp
                )
                webhook_event.save()
                
                # Update ProfileVideos model for analytics
                update_profile_video_stats(profile, media_id, value)
                
                print(f"✓ Saved webhook event: {event_type} for media {media_id}")
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        raise


def determine_event_type(webhook_value):
    """
    Determine the type of event from webhook data
    """
    # Check for comments
    if webhook_value.get("comment_text"):
        return "comment"
    
    # Check for reactions/likes
    if webhook_value.get("reaction_type"):
        return "like"
    
    # Check for views
    if webhook_value.get("view_count", 0) > 0 and not webhook_value.get("caption"):
        return "view"
    
    # Check for shares
    if webhook_value.get("share_count", 0) > 0:
        return "share"
    
    # Default: new post
    return "post"


def parse_webhook_timestamp(timestamp_str):
    """
    Parse ISO timestamp from webhook
    Format: "2024-01-01T10:00:00+0000"
    """
    if not timestamp_str:
        return timezone.now()
    
    try:
        # Handle ISO format with timezone
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        return timezone.now()


def update_profile_video_stats(profile, media_id, webhook_value):
    """
    Update ProfileVideos model with webhook data
    """
    try:
        video_data = {
            "platform": PlatformChoices.INSTAGRAM,
            "title": webhook_value.get("caption"),
            "likes_count": webhook_value.get("like_count", 0),
            "comment_count": webhook_value.get("comments_count", 0),
            "view_count": webhook_value.get("view_count", 0),
            "share_count": webhook_value.get("share_count", 0),
            "created_at": parse_webhook_timestamp(webhook_value.get("timestamp"))
        }
        
        # Only update if we have meaningful data
        if video_data.get("likes_count") > 0 or video_data.get("comment_count") > 0:
            InstagramProfileMedia.objects.update_or_create(
                video_id=media_id,
                defaults=video_data
            )
    except Exception as e:
        print(f"Error updating video stats: {str(e)}")


def get_profile_from_ig_account(ig_account_id):
    """
    Find a CreatorProfile by the Instagram account ID in the dedicated profile model.
    """
    instagram_profile = InstagramProfile.objects.filter(instagram_user_id=ig_account_id).first()
    return instagram_profile.profile if instagram_profile else None


def get_profile_from_page_id(page_id):
    """
    Find a CreatorProfile by their Facebook page ID.
    This helper is no-op because page IDs are not stored in the new platform profile tables.
    """
    return None




""" 
    ===============================
        SEARCH CHANNEL SERVICE
    ===============================
"""

def search_youtube_channels(access_token, query):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": 10,
        "order": "viewCount",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    res = requests.get(url, headers=headers, params=params)
    return res.json()

""" 
    ====================================
        GET CHANNELS DETAILS SERVICE
    ====================================
"""
def get_channel_details(search_results, access_token):
    channel_ids = [item["snippet"]["channelId"] for item in search_results.get("items", [])]
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics",
        "id": ",".join(channel_ids),
        "order": "subscriberCount",
    }
    headers = {"Authorization": f"Bearer {access_token}"}

    res = requests.get(url, headers=headers, params=params).json()
    channels = []
    for item in res.get("items", []):

        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        channel_id = item.get("id")

        # profile image
        thumbnails = snippet.get("thumbnails", {})

        image_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        # profile/channel URL
        profile_url = f"https://www.youtube.com/channel/{channel_id}"

        channels.append({
            "channel_id": channel_id,
            "title": snippet.get("title"),
            "profile_url": profile_url,
            "image_url": image_url,
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
        })

    # -------------------------
    # STEP 3: SORT
    # -------------------------
    channels.sort(
        key=lambda x: x["subscribers"],
        reverse=True
    )
    return channels
    

""" 
    ===============================
        COMPETITORS SERVICE
    ===============================
"""
def get_youtube_competitors(access_token, my_topic):
    # search_url = "https://www.googleapis.com/youtube/v3/search"
    # search_params = {
    #     'part': 'snippet',
    #     'q': my_topic,
    #     'type': 'channel',
    #     'maxResults': 10,
    #     'order': 'viewCount', # ভিউ অনুযায়ী র‍্যাঙ্ক করা হচ্ছে        
    #     'access_token': access_token
    # }

    # search_response = requests.get(search_url, params=search_params).json()
    # # print("YouTube Competitor Search Response:", search_response)
    # return search_response
    # channel_ids = [item['snippet']['channelId'] for item in search_response.get('items', [])]
    
    # if not channel_ids:
    #     return "No competitors found."
    
    youtube_results = search_youtube_channels(access_token, my_topic)
    channel_details = get_channel_details(youtube_results, access_token)
    return channel_details


def get_or_determine_content_type(youtube_profile):
    """
    Get channel content type. If not set, use OpenAI to analyze 
    channel description/title and determine content type, then save.
    """
    if youtube_profile.channel_type:
        return youtube_profile.channel_type

    title = youtube_profile.channel_title or ""
    description = youtube_profile.channel_description or ""

    if not title and not description:
        return "General"

    # Call OpenAI
    from openai import OpenAI
    import json
    
    prompt = f"""
    Based on the following YouTube channel title and description, determine the single most accurate content category or topic (e.g. 'Tech & Education', 'Cooking & Food', 'Gaming', 'Fitness', 'Fashion & Beauty', 'Business & Finance', 'Travel & Lifestyle', 'Vlogs', 'Music & Entertainment', 'ASMR', etc. Keep it very short, 1 to 3 words maximum):

    Title: {title}
    Description: {description}

    Return a strict JSON format:
    {{
        "content_type": "string"
    }}
    """

    channel_type = "General"
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You are a strict JSON generator. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=50,
        )
        body = response.choices[0].message.content.strip()
        parsed = json.loads(body)
        channel_type = parsed.get("content_type", "General")
    except Exception as e:
        print("❌ OpenAI Error in get_or_determine_content_type:", e)
        # Fallback heuristic rules
        desc_lower = description.lower()
        if "tech" in desc_lower or "code" in desc_lower or "tutorial" in desc_lower:
            channel_type = "Tech & Education"
        elif "cook" in desc_lower or "food" in desc_lower or "recipe" in desc_lower:
            channel_type = "Cooking & Food"
        elif "game" in desc_lower or "play" in desc_lower:
            channel_type = "Gaming"
        elif "fit" in desc_lower or "gym" in desc_lower or "workout" in desc_lower:
            channel_type = "Fitness"
        elif "beauty" in desc_lower or "makeup" in desc_lower or "fashion" in desc_lower:
            channel_type = "Fashion & Beauty"

    # Save to model
    youtube_profile.channel_type = channel_type
    youtube_profile.save()
    return channel_type
    
    
def revoke_youtube(token):
    
    request = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={
                "content-type": "application/x-www-form-urlencoded"
            }
        )

    return request.json