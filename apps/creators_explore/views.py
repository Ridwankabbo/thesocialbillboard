# import requests
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from django.conf import settings
# from rest_framework import status, permissions


# class BaseAPIView(APIView):
#     def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
#         return Response(
#             {"success": True, "message": message, "status": status_code, "data": data or {}},
#             status=status_code
#         )

#     def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
#         return Response(
#             {"success": False, "message": message, "status": status_code, "data": data or {}},
#             status=status_code
#         )




# # -----------------------------------
# # Country Fallback Map (Optional)
# # -----------------------------------
# DEFAULT_COUNTRY_MAP = {
#     "taylorswift": "US",
#     "charlidamelio": "US",
#     "khaby.lame": "IT",
#     "jlo": "US",
#     "cristiano": "PT"
# }

# # -----------------------------------
# # Fallback TikTok and Instagram Users
# # -----------------------------------
# FALLBACK_TIKTOK_USERS = [
#     "charlidamelio", "khaby.lame", "addisonre", "bellapoarch", "zachking",
#     "dixiedamelio", "mrbeast", "lorengray", "spencerx", "willsmith"
# ]

# FALLBACK_INSTAGRAM_USERS = [
#     "cristiano", "kimkardashian", "therock", "arianagrande", "kyliejenner",
#     "beyonce", "selenagomez", "jlo", "leomessi", "taylorswift"
# ]


# # -----------------------------------
# # Genre Detector
# # -----------------------------------
# def detect_genre(text):
#     text = (text or "").lower()
#     if any(word in text for word in ["music", "song", "singer", "album"]):
#         return "Music"
#     if any(word in text for word in ["funny", "comedy", "laugh"]):
#         return "Comedy"
#     if any(word in text for word in ["game", "gaming", "esports"]):
#         return "Gaming"
#     if any(word in text for word in ["diy", "craft", "handmade"]):
#         return "DIY"
#     if any(word in text for word in ["fitness", "workout", "gym"]):
#         return "Fitness"
#     if any(word in text for word in ["fashion", "style", "model"]):
#         return "Fashion"
#     return "General"


# # -----------------------------------
# # TikTok API Headers
# # -----------------------------------
# TIKTOK_HEADERS = {
#     "x-rapidapi-key": settings.RAPIDAPI_KEY,
#     "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
# }


# # -----------------------------------
# # Fetch TikTok User Data
# # -----------------------------------
# def fetch_tiktok_data(username):
#     url = "https://tiktok-api23.p.rapidapi.com/api/user/info"
#     try:
#         res = requests.get(url, headers=TIKTOK_HEADERS, params={"uniqueId": username})
#         data = res.json()
#     except Exception:
#         return None

#     if res.status_code != 200 or "userInfo" not in data:
#         return None

#     user_info = data["userInfo"]
#     user = user_info.get("user", {})
#     stats = user_info.get("stats", {})

#     genre = detect_genre(user.get("signature", ""))

#     return {
#         "name": user.get("nickname", user.get("uniqueId", "Unknown")),
#         "platform": "TikTok",
#         "followers": stats.get("followerCount", 0),
#         "image": user.get("avatarLarger", ""),
#         "genre": genre,
#         "country": user.get("region", DEFAULT_COUNTRY_MAP.get(username, "Unknown")),
#         "age_group": "18-30",
#         "channel_url": f"https://www.tiktok.com/@{user.get('uniqueId', username)}"
#     }


# # -----------------------------------
# # Fetch Trending TikTok Users (Fallback)
# # -----------------------------------
# def fetch_trending_tiktok_users():
#     users = []
#     for uname in FALLBACK_TIKTOK_USERS:
#         user_data = fetch_tiktok_data(uname)
#         if user_data:
#             users.append(user_data)
#         if len(users) >= 10:
#             break
#     return users


# # -----------------------------------
# # Fetch YouTube Channel Data
# # -----------------------------------
# def fetch_youtube_channel_data(channel_id):
#     url = (
#         "https://www.googleapis.com/youtube/v3/channels"
#         f"?part=snippet,statistics&id={channel_id}&key={settings.YOUTUBE_API_KEY}"
#     )

#     try:
#         res = requests.get(url).json()
#     except Exception:
#         return None

#     if "items" in res and res["items"]:
#         item = res["items"][0]
#         snippet = item["snippet"]
#         stats = item["statistics"]

#         genre = detect_genre(snippet.get("description", ""))

#         return {
#             "name": snippet.get("title", "Unknown"),
#             "platform": "YouTube",
#             "followers": stats.get("subscriberCount", 0),
#             "image": snippet["thumbnails"]["high"]["url"],
#             "genre": genre,
#             "country": snippet.get("country", DEFAULT_COUNTRY_MAP.get(channel_id, "Unknown")),
#             "age_group": "18-40",
#             "channel_url": f"https://www.youtube.com/channel/{channel_id}"
#         }

#     return None


# # -----------------------------------
# # Fetch Trending YouTube Channels
# # -----------------------------------
# def fetch_trending_youtube_channels():
#     url = (
#         f"https://www.googleapis.com/youtube/v3/videos"
#         f"?part=snippet&chart=mostPopular&regionCode=US&maxResults=10&key={settings.YOUTUBE_API_KEY}"
#     )
#     try:
#         res = requests.get(url).json()
#     except Exception:
#         return []

#     channels = []
#     seen = set()
#     for video in res.get("items", []):
#         cid = video["snippet"]["channelId"]
#         if cid not in seen:
#             seen.add(cid)
#             ch_data = fetch_youtube_channel_data(cid)
#             if ch_data:
#                 channels.append(ch_data)
#     return channels


# # -----------------------------------
# # Fetch Instagram User Data
# # -----------------------------------
# def fetch_instagram_data(username):
#     url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
#     headers = {
#         "x-rapidapi-key": settings.RAPIDAPI_KEY,
#         "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
#     }

#     try:
#         res = requests.get(url, headers=headers, params={"username_or_id": username})
#         data = res.json()
#     except Exception:
#         return None

#     user = data.get("data", {})
#     if not user:
#         return None

#     genre = detect_genre(user.get("biography", ""))

#     return {
#         "name": user.get("full_name", user.get("username", "Unknown")),
#         "platform": "Instagram",
#         "followers": user.get("follower_count", 0),
#         "image": user.get("profile_pic_url_hd", user.get("profile_pic_url", "")),
#         "genre": genre,
#         "country": DEFAULT_COUNTRY_MAP.get(username, "Unknown"),
#         "age_group": "18-35",
#         "channel_url": f"https://www.instagram.com/{user.get('username', username)}/"
#     }


# # -----------------------------------
# # Fetch Trending Instagram Users (Fallback)
# # -----------------------------------
# def fetch_trending_instagram_users():
#     users = []
#     for uname in FALLBACK_INSTAGRAM_USERS:
#         ig_data = fetch_instagram_data(uname)
#         if ig_data:
#             users.append(ig_data)
#         if len(users) >= 10:
#             break
#     return users


# # -----------------------------------
# # Default Creators View
# # -----------------------------------
# class DefaultCreatorsAPIView(BaseAPIView):
#     def get(self, request):
#         creators = []
#         creators.extend(fetch_trending_tiktok_users())
#         creators.extend(fetch_trending_youtube_channels())
#         creators.extend(fetch_trending_instagram_users())

#         if not creators:
#             return self.error_response("No creators found", status_code=status.HTTP_404_NOT_FOUND)

#         return self.success_response("Creators fetched successfully", data=creators)


# # -----------------------------------
# # Search Creators View
# # -----------------------------------
# class SearchCreatorsAPIView(BaseAPIView):
#     def get(self, request):
#         username = request.GET.get("username")
#         if not username:
#             return self.error_response("username parameter is required", status_code=status.HTTP_400_BAD_REQUEST)

#         creators = []

#         # TikTok
#         tk_data = fetch_tiktok_data(username)
#         if tk_data:
#             creators.append(tk_data)

#         # YouTube
#         yt_search_url = (
#             f"https://www.googleapis.com/youtube/v3/search"
#             f"?part=snippet&type=channel&q={username}&key={settings.YOUTUBE_API_KEY}"
#         )
#         yt_res = requests.get(yt_search_url).json()
#         for item in yt_res.get("items", [])[:1]:
#             cid = item["snippet"]["channelId"]
#             yt_data = fetch_youtube_channel_data(cid)
#             if yt_data:
#                 creators.append(yt_data)

#         # Instagram
#         ig_data = fetch_instagram_data(username)
#         if ig_data:
#             creators.append(ig_data)

#         if not creators:
#             fallback = []
#             fallback.extend(fetch_trending_tiktok_users())
#             fallback.extend(fetch_trending_instagram_users())
#             return self.error_response(
#                 "No data found for this username. Showing fallback creators.",
#                 data={"fallback": fallback},
#                 status_code=status.HTTP_404_NOT_FOUND
#             )

#         return self.success_response("Creators fetched successfully", data=creators)


# # -----------------------------------
# # Filter Creators View
# # -----------------------------------
# class FilterCreatorsAPIView(BaseAPIView):
#     def get(self, request):
#         country = request.GET.get("country")
#         platform = request.GET.get("platform")
#         genre = request.GET.get("genre")
#         age_group = request.GET.get("age_group")

#         all_creators = []
#         all_creators.extend(fetch_trending_tiktok_users())
#         all_creators.extend(fetch_trending_youtube_channels())
#         all_creators.extend(fetch_trending_instagram_users())

#         filtered = all_creators
#         if platform:
#             filtered = [c for c in filtered if c["platform"].lower() == platform.lower()]
#         if country:
#             filtered = [c for c in filtered if c["country"].lower() == country.lower()]
#         if genre:
#             filtered = [c for c in filtered if c["genre"].lower() == genre.lower()]
#         if age_group:
#             filtered = [c for c in filtered if c["age_group"].lower() == age_group.lower()]

#         return self.success_response("Filtered creators fetched successfully", data=filtered)




import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status, permissions
from .models import Creator


class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"success": True, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )

    def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"success": False, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )




# -----------------------------------
# Country Fallback Map (Optional)
# -----------------------------------
DEFAULT_COUNTRY_MAP = {
    "taylorswift": "US",
    "charlidamelio": "US",
    "khaby.lame": "IT",
    "jlo": "US",
    "cristiano": "PT"
}

# -----------------------------------
# Fallback TikTok and Instagram Users
# -----------------------------------
FALLBACK_TIKTOK_USERS = [
    "charlidamelio", "khaby.lame", "addisonre", "bellapoarch", "zachking",
    "dixiedamelio", "mrbeast", "lorengray", "spencerx", "willsmith"
]

FALLBACK_INSTAGRAM_USERS = [
    "cristiano", "kimkardashian", "therock", "arianagrande", "kyliejenner",
    "beyonce", "selenagomez", "jlo", "leomessi", "taylorswift"
]


# -----------------------------------
# Genre Detector
# -----------------------------------
def detect_genre(text):
    text = (text or "").lower()
    if any(word in text for word in ["music", "song", "singer", "album"]):
        return "Music"
    if any(word in text for word in ["funny", "comedy", "laugh"]):
        return "Comedy"
    if any(word in text for word in ["game", "gaming", "esports"]):
        return "Gaming"
    if any(word in text for word in ["diy", "craft", "handmade"]):
        return "DIY"
    if any(word in text for word in ["fitness", "workout", "gym"]):
        return "Fitness"
    if any(word in text for word in ["fashion", "style", "model"]):
        return "Fashion"
    return "General"


# -----------------------------------
# TikTok API Headers
# -----------------------------------
TIKTOK_HEADERS = {
    "x-rapidapi-key": settings.RAPIDAPI_KEY,
    "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
}


# -----------------------------------
# Fetch TikTok User Data
# -----------------------------------
def fetch_tiktok_data(username):
    url = "https://tiktok-api23.p.rapidapi.com/api/user/info"
    try:
        res = requests.get(url, headers=TIKTOK_HEADERS, params={"uniqueId": username})
        data = res.json()
    except Exception:
        return None

    if res.status_code != 200 or "userInfo" not in data:
        return None

    user_info = data["userInfo"]
    user = user_info.get("user", {})
    stats = user_info.get("stats", {})

    genre = detect_genre(user.get("signature", ""))

    return {
        "name": user.get("nickname", user.get("uniqueId", "Unknown")),
        "platform": "TikTok",
        "followers": stats.get("followerCount", 0),
        "image": user.get("avatarLarger", ""),
        "genre": genre,
        "country": user.get("region", DEFAULT_COUNTRY_MAP.get(username, "Unknown")),
        "age_group": "18-30",
        "channel_url": f"https://www.tiktok.com/@{user.get('uniqueId', username)}"
    }


# -----------------------------------
# Fetch Trending TikTok Users (Fallback)
# -----------------------------------
def fetch_trending_tiktok_users():
    users = []
    for uname in FALLBACK_TIKTOK_USERS:
        user_data = fetch_tiktok_data(uname)
        if user_data:
            users.append(user_data)
        if len(users) >= 10:
            break
    return users


# -----------------------------------
# Fetch YouTube Channel Data
# -----------------------------------
def fetch_youtube_channel_data(channel_id):
    url = (
        "https://www.googleapis.com/youtube/v3/channels"
        f"?part=snippet,statistics&id={channel_id}&key={settings.YOUTUBE_API_KEY}"
    )

    try:
        res = requests.get(url).json()
    except Exception:
        return None

    if "items" in res and res["items"]:
        item = res["items"][0]
        snippet = item["snippet"]
        stats = item["statistics"]

        genre = detect_genre(snippet.get("description", ""))

        return {
            "name": snippet.get("title", "Unknown"),
            "platform": "YouTube",
            "followers": stats.get("subscriberCount", 0),
            "image": snippet["thumbnails"]["high"]["url"],
            "genre": genre,
            "country": snippet.get("country", DEFAULT_COUNTRY_MAP.get(channel_id, "Unknown")),
            "age_group": "18-40",
            "channel_url": f"https://www.youtube.com/channel/{channel_id}",
            "channel_id": channel_id
        }

    return None


# -----------------------------------
# Fetch Trending YouTube Channels
# -----------------------------------
def fetch_trending_youtube_channels():
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet&chart=mostPopular&regionCode=US&maxResults=10&key={settings.YOUTUBE_API_KEY}"
    )
    try:
        res = requests.get(url).json()
    except Exception:
        return []

    channels = []
    seen = set()
    for video in res.get("items", []):
        cid = video["snippet"]["channelId"]
        if cid not in seen:
            seen.add(cid)
            ch_data = fetch_youtube_channel_data(cid)
            if ch_data:
                channels.append(ch_data)
    return channels


# -----------------------------------
# Fetch Instagram User Data
# -----------------------------------
def fetch_instagram_data(username):
    url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
    headers = {
        "x-rapidapi-key": settings.RAPIDAPI_KEY,
        "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
    }

    try:
        res = requests.get(url, headers=headers, params={"username_or_id": username})
        data = res.json()
    except Exception:
        return None

    user = data.get("data", {})
    if not user:
        return None

    genre = detect_genre(user.get("biography", ""))

    return {
        "name": user.get("full_name", user.get("username", "Unknown")),
        "platform": "Instagram",
        "followers": user.get("follower_count", 0),
        "image": user.get("profile_pic_url_hd", user.get("profile_pic_url", "")),
        "genre": genre,
        "country": DEFAULT_COUNTRY_MAP.get(username, "Unknown"),
        "age_group": "18-35",
        "channel_url": f"https://www.instagram.com/{user.get('username', username)}/"
    }


# -----------------------------------
# Fetch Trending Instagram Users (Fallback)
# -----------------------------------
def fetch_trending_instagram_users():
    users = []
    for uname in FALLBACK_INSTAGRAM_USERS:
        ig_data = fetch_instagram_data(uname)
        if ig_data:
            users.append(ig_data)
        if len(users) >= 10:
            break
    return users


# -----------------------------------
# Default Creators View
# -----------------------------------
class DefaultCreatorsAPIView(BaseAPIView):
    def get(self, request):
        creators = Creator.objects.order_by('-followers')[:30]
        if not creators:
            return self.error_response("No creators found", status_code=status.HTTP_404_NOT_FOUND)

        serialized = [self.serialize_creator(c) for c in creators]
        return self.success_response("Creators fetched successfully", data=serialized)

    def serialize_creator(self, obj):
        return {
            "name": obj.name,
            "platform": obj.platform,
            "followers": obj.followers,
            "image": obj.image,
            "genre": obj.genre,
            "country": obj.country,
            "age_group": obj.age_group,
            "channel_url": obj.channel_url,
        }


# -----------------------------------
# Search Creators View
# -----------------------------------
class SearchCreatorsAPIView(BaseAPIView):
    def get(self, request):
        username = request.GET.get("username")
        if not username:
            return self.error_response("username parameter is required", status_code=status.HTTP_400_BAD_REQUEST)

        creators = []

        # TikTok
        tk_data = fetch_tiktok_data(username)
        if tk_data:
            creators.append(tk_data)

        # YouTube
        yt_search_url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&type=channel&q={username}&key={settings.YOUTUBE_API_KEY}"
        )
        yt_res = requests.get(yt_search_url).json()
        for item in yt_res.get("items", [])[:1]:
            cid = item["snippet"]["channelId"]
            yt_data = fetch_youtube_channel_data(cid)
            if yt_data:
                creators.append(yt_data)

        # Instagram
        ig_data = fetch_instagram_data(username)
        if ig_data:
            creators.append(ig_data)

        if not creators:
            fallback = []
            fallback.extend(fetch_trending_tiktok_users())
            fallback.extend(fetch_trending_instagram_users())
            return self.error_response(
                "No data found for this username. Showing fallback creators.",
                data={"fallback": fallback},
                status_code=status.HTTP_404_NOT_FOUND
            )

        return self.success_response("Creators fetched successfully", data=creators)


# -----------------------------------
# Filter Creators View
# -----------------------------------
class FilterCreatorsAPIView(APIView):
    def get(self, request):
        # Get query params
        platform = request.query_params.get('platform')
        country = request.query_params.get('country')
        genre = request.query_params.get('genre')
        age_group = request.query_params.get('age_group')
        min_followers = request.query_params.get('min_followers')
        max_followers = request.query_params.get('max_followers')

        # Initial queryset
        queryset = Creator.objects.all()

        # Apply filters
        if platform:
            queryset = queryset.filter(platform__iexact=platform)
        if country:
            queryset = queryset.filter(country__iexact=country)
        if genre:
            queryset = queryset.filter(genre__iexact=genre)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)
        if min_followers:
            queryset = queryset.filter(followers__gte=min_followers)
        if max_followers:
            queryset = queryset.filter(followers__lte=max_followers)

        # Serialize results
        data = [self.serialize_creator(creator) for creator in queryset]

        return Response({
            "success": True,
            "message": "Filtered creators fetched successfully",
            "data": data
        }, status=status.HTTP_200_OK)

    def serialize_creator(self, obj):
        return {
            "id": obj.id,
            "name": obj.name,
            "platform": obj.platform,
            "followers": obj.followers,
            "image": obj.image if obj.image else None,
            "genre": obj.genre,
            "country": obj.country,
            "age_group": obj.age_group,
            "channel_url": obj.channel_url,
        }






















class CreatorsAPIView(BaseAPIView):

    def get(self, request):
        # ----------------------------
        # Query params
        # ----------------------------
        username = request.query_params.get("username")
        platform = request.query_params.get("platform")
        country = request.query_params.get("country")
        genre = request.query_params.get("genre")
        age_group = request.query_params.get("age_group")
        min_followers = request.query_params.get('min_followers')
        max_followers = request.query_params.get('max_followers')

        # ----------------------------
        # CASE 1: Search Mode (External APIs)
        # ----------------------------
        if username:
            creators = []

            # TikTok
            tk_data = fetch_tiktok_data(username)
            if tk_data:
                creators.append(tk_data)

            # YouTube
            yt_search_url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet&type=channel&q={username}&key={settings.YOUTUBE_API_KEY}"
            )
            yt_res = requests.get(yt_search_url).json()
            print(yt_res)
            for item in yt_res.get("items", [])[:1]:
                cid = item["snippet"]["channelId"]
                yt_data = fetch_youtube_channel_data(cid)
                if yt_data:
                    creators.append(yt_data)

            # Instagram
            ig_data = fetch_instagram_data(username)
            if ig_data:
                creators.append(ig_data)

            if not creators:
                fallback = []
                fallback.extend(fetch_trending_tiktok_users())
                fallback.extend(fetch_trending_instagram_users())
                fallback.extend(fetch_trending_youtube_channels())
                return self.error_response(
                    "No data found for this username. Showing fallback creators.",
                    data={"fallback": fallback},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Apply filters on external API results
            creators = self.apply_filters(creators, platform, country, genre, age_group, min_followers, max_followers)

            if not creators:
                return self.error_response(
                    "No creators matched the filters.",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            return self.success_response("Creators fetched successfully", data=creators)

        # ----------------------------
        # CASE 2: Filter Mode (Database)
        # ----------------------------
        queryset = Creator.objects.all()

        if platform:
            queryset = queryset.filter(platform__iexact=platform)
        if country:
            queryset = queryset.filter(country__iexact=country)
        if genre:
            queryset = queryset.filter(genre__iexact=genre)
        if age_group:
            queryset = queryset.filter(age_group__iexact=age_group)
        if min_followers:
            queryset = queryset.filter(followers__gte=int(min_followers))
        if max_followers:
            queryset = queryset.filter(followers__lte=int(max_followers))

        # ----------------------------
        # CASE 3: Default (Top 30 by followers)
        # ----------------------------
        if not any([platform, country, genre, age_group, min_followers, max_followers]):
            queryset = queryset.order_by('-followers')[:30]

        if not queryset.exists():
            return self.error_response("No creators found", status_code=status.HTTP_404_NOT_FOUND)

        data = [self.serialize_creator(obj) for obj in queryset]
        return self.success_response("Creators fetched successfully", data=data)

    # ----------------------------
    # Serialize Database Creator
    # ----------------------------
    def serialize_creator(self, obj):
        return {
            "id": getattr(obj, "id", None),
            "name": obj.get("name") if isinstance(obj, dict) else obj.name,
            "platform": getattr(obj, "platform", None),
            "followers": getattr(obj, "followers", None),
            "image": getattr(obj, "image", None),
            "genre": getattr(obj, "genre", None),
            "country": getattr(obj, "country", None),
            "age_group": getattr(obj, "age_group", None),
            "channel_url": getattr(obj, "channel_url", None),
            "channel_id:": getattr(obj, "channel_id", None),
        }

    # ----------------------------
    # Filter Helper for External API Results
    # ----------------------------
    def apply_filters(self, creators, platform, country, genre, age_group, min_followers, max_followers):
        filtered = []
        for c in creators:
            if platform and c.get("platform", "").lower() != platform.lower():
                continue
            if country and c.get("country", "").lower() != country.lower():
                continue
            if genre and c.get("genre", "").lower() != genre.lower():
                continue
            if age_group and c.get("age_group", "").lower() != age_group.lower():
                continue
            if min_followers and int(c.get("followers", 0)) < int(min_followers):
                continue
            if max_followers and int(c.get("followers", 0)) > int(max_followers):
                continue
            filtered.append(c)
        return filtered