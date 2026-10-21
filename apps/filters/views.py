# import requests
# from django.conf import settings
# from rest_framework import status
# from rest_framework.views import APIView
# from rest_framework.response import Response


# # -----------------------------------
# # Base API View
# # -----------------------------------
# class BaseAPIView(APIView):
#     def success_response(self, message, data=None, status_code=status.HTTP_200_OK):
#         return Response({"status": "success", "message": message, "data": data or []}, status=status_code)

#     def error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST):
#         return Response({"status": "error", "message": message}, status=status_code)


# # -----------------------------------
# # Top List API View
# # -----------------------------------
# class TopListAPIView(BaseAPIView):
#     def get(self, request):
#         platform = request.query_params.get('platform', 'youtube').lower()
#         genre = request.query_params.get('genre')
#         ai_score_min = float(request.query_params.get('ai_score_min', 1))
#         ai_score_max = float(request.query_params.get('ai_score_max', 10))
#         region = request.query_params.get('region', 'US')
#         sort_by = request.query_params.get('sort_by', 'trending')

#         if platform not in ['youtube', 'tiktok', 'instagram']:
#             return self.error_response("Invalid platform", status_code=status.HTTP_400_BAD_REQUEST)

#         # Step 1: Fetch platform data
#         if platform == 'youtube':
#             video_list = self.fetch_youtube_videos(region, genre)
#         elif platform == 'tiktok':
#             video_list = self.fetch_tiktok_videos(genre or "funny")
#         elif platform == 'instagram':
#             video_list = self.fetch_instagram_profiles(genre or "insta")
#         else:
#             video_list = []

#         if not video_list:
#             return self.success_response("No data found for given filters.", data=[], status_code=status.HTTP_200_OK)

#         # Step 2: Calculate AI score
#         final_list = self.calculate_ai_score(video_list, ai_score_min, ai_score_max)

#         # Step 3: Sort
#         sorted_list = self.sort_videos(final_list, sort_by)

#         return self.success_response("Top list fetched successfully.", data=sorted_list)

#     # --------------------------
#     # Fetch YouTube Data
#     # --------------------------
#     def fetch_youtube_videos(self, region, genre):
#         search_url = "https://www.googleapis.com/youtube/v3/search"
#         params = {
#             "part": "snippet",
#             "regionCode": region,
#             "q": genre or "Education",
#             "type": "channel",
#             "maxResults": 6,
#             "key": settings.YOUTUBE_API_KEY
#         }
#         try:
#             search_res = requests.get(search_url, params=params)
#             search_data = search_res.json()

#             videos = []
#             channel_ids = [item["id"]["channelId"] for item in search_data.get("items", [])]
#             if not channel_ids:
#                 return videos

#             # Fetch channel details
#             channel_url = "https://www.googleapis.com/youtube/v3/channels"
#             channel_params = {
#                 "part": "snippet,statistics",
#                 "id": ",".join(channel_ids),
#                 "key": settings.YOUTUBE_API_KEY
#             }
#             channel_res = requests.get(channel_url, params=channel_params)
#             channel_data = channel_res.json()

#             for idx, item in enumerate(channel_data.get("items", []), start=1):
#                 stats = item.get("statistics", {})
#                 snippet = item.get("snippet", {})
#                 channel_id = item.get("id")

#                 subscribers = self.format_number(stats.get("subscriberCount", "0"))
#                 views = self.format_number(stats.get("viewCount", "0"))

#                 videos.append({
#                     "rank": idx,
#                     "platform": "YouTube",
#                     "channel": snippet.get("title"),
#                     "channel_link": f"https://www.youtube.com/channel/{channel_id}",
#                     "country": region,
#                     "safety_tag": "Parent-Rated",
#                     "genre": genre or "Education",
#                     "age_range": "3-6",
#                     "subscribers": subscribers,
#                     "views": views,
#                     "ai_score": 0
#                 })
#             return videos
#         except Exception as e:
#             print("DEBUG - YouTube Fetch Error:", e)
#             return []

#     # --------------------------
#     # Fetch TikTok Data
#     # --------------------------
#     def fetch_tiktok_videos(self, keyword):
#         url = "https://tiktok-api23.p.rapidapi.com/api/search/video"
#         querystring = {"keyword": keyword, "cursor": "0", "search_id": "0"}
#         headers = {
#             "x-rapidapi-key": settings.RAPIDAPI_KEY,
#             "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
#         }

#         try:
#             response = requests.get(url, headers=headers, params=querystring)
#             data = response.json()

#             items = data.get("item_list", [])
#             if not items:
#                 print("DEBUG - No TikTok items found in item_list.")
#                 return []

#             results = []
#             for idx, item in enumerate(items, start=1):
#                 author = item.get("author", {})
#                 author_stats = item.get("authorStats", {})
#                 stats = item.get("stats", {})

#                 results.append({
#                     "rank": idx,
#                     "platform": "TikTok",
#                     "channel": author.get("uniqueId", "Unknown"),
#                     "channel_link": f"https://www.tiktok.com/@{author.get('uniqueId', '')}",
#                     "country": "N/A",
#                     "safety_tag": "General",
#                     "genre": keyword,
#                     "age_range": "13+",
#                     "subscribers": self.format_number(author_stats.get("followerCount", 0)),
#                     "views": self.format_number(stats.get("playCount", 0)),
#                     "ai_score": 0
#                 })
#             return results

#         except Exception as e:
#             print("DEBUG - TikTok Fetch Error:", e)
#             return []

#     # --------------------------
#     # Fetch Instagram Data
#     # --------------------------
#     def fetch_instagram_profiles(self, keyword):
#         search_url = "https://instagram-scraper-20251.p.rapidapi.com/searchuser/"
#         search_query = {"keyword": keyword}
#         headers = {
#             "x-rapidapi-key": settings.RAPIDAPI_KEY,
#             "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
#         }

#         try:
#             # Step 1: Search profiles
#             search_response = requests.get(search_url, headers=headers, params=search_query)
#             search_data = search_response.json()
#             items = search_data.get("data", {}).get("items", [])

#             if not items:
#                 print("DEBUG - No Instagram profiles found in search.")
#                 return []

#             results = []
#             for idx, user in enumerate(items[:6], start=1):  # Limit to top 6 profiles
#                 username = user.get("username")
#                 follower_count = 0

#                 # Step 2: Get follower count for each profile
#                 try:
#                     userinfo_url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
#                     userinfo_query = {"username_or_id": username}
#                     userinfo_res = requests.get(userinfo_url, headers=headers, params=userinfo_query)
#                     userinfo_data = userinfo_res.json()
#                     follower_count = userinfo_data.get("data", {}).get("follower_count", 0)
#                 except Exception as e:
#                     print(f"DEBUG - Failed to fetch follower count for {username}: {e}")

#                 results.append({
#                     "rank": idx,
#                     "platform": "Instagram",
#                     "channel": username,
#                     "channel_link": f"https://www.instagram.com/{username}",
#                     "country": "N/A",
#                     "safety_tag": "General",
#                     "genre": keyword,
#                     "age_range": "13+",
#                     "subscribers": self.format_number(follower_count),
#                     "views": "0",
#                     "ai_score": 0
#                 })

#             return results

#         except Exception as e:
#             print("DEBUG - Instagram Fetch Error:", e)
#             return []


#     # --------------------------
#     # AI Score Calculation
#     # --------------------------
#     def calculate_ai_score(self, videos, ai_score_min, ai_score_max):
#         final_videos = []
#         for v in videos:
#             try:
#                 subs = self.parse_number(v.get("subscribers", "0"))
#                 views = self.parse_number(v.get("views", "0"))
#                 views_score = min(10, views / 1_000_000)  # 1M views = score 10
#                 subs_score = min(10, subs / 100_000)      # 100k subs = score 10
#                 activity_score = 7.0
#                 score = round((views_score * 0.5) + (subs_score * 0.3) + (activity_score * 0.2), 2)
#             except Exception as e:
#                 print("DEBUG - AI Score Calculation Error:", e)
#                 score = 5.0

#             if ai_score_min <= score <= ai_score_max:
#                 v['ai_score'] = score
#                 final_videos.append(v)
#         return final_videos

#     # --------------------------
#     # Sorting
#     # --------------------------
#     def sort_videos(self, videos, sort_by):
#         try:
#             if sort_by == 'subscribers':
#                 return sorted(videos, key=lambda x: self.parse_number(x['subscribers']), reverse=True)
#             elif sort_by == 'views':
#                 return sorted(videos, key=lambda x: self.parse_number(x['views']), reverse=True)
#         except Exception as e:
#             print("DEBUG - Sort Error:", e)
#         return videos

#     # --------------------------
#     # Number Formatting
#     # --------------------------
#     def format_number(self, num):
#         try:
#             num = int(num)
#         except:
#             return str(num)
#         if num >= 1_000_000_000:
#             return f"{num / 1_000_000_000:.2f}B"
#         elif num >= 1_000_000:
#             return f"{num / 1_000_000:.2f}M"
#         elif num >= 1_000:
#             return f"{num / 1_000:.2f}K"
#         return str(num)

#     def parse_number(self, num_str):
#         num_str = str(num_str)
#         if num_str.endswith('B'):
#             return int(float(num_str[:-1]) * 1_000_000_000)
#         elif num_str.endswith('M'):
#             return int(float(num_str[:-1]) * 1_000_000)
#         elif num_str.endswith('K'):
#             return int(float(num_str[:-1]) * 1_000)
#         try:
#             return int(num_str)
#         except:
#             return 0




import requests
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


# -----------------------------------
# Base API View
# -----------------------------------
class BaseAPIView(APIView):
    def success_response(self, message, data=None, status_code=status.HTTP_200_OK):
        return Response({"status": "success", "message": message, "data": data or []}, status=status_code)

    def error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({"status": "error", "message": message}, status=status_code)


# -----------------------------------
# Top List API View
# -----------------------------------
class TopListAPIView(BaseAPIView):
    def get(self, request):
        platform = request.query_params.get('platform', 'youtube').lower()
        genre = request.query_params.get('genre')
        ai_score_min = float(request.query_params.get('ai_score_min', 1))
        ai_score_max = float(request.query_params.get('ai_score_max', 10))
        region = request.query_params.get('region', 'US')
        sort_by = request.query_params.get('sort_by', 'trending')

        if platform not in ['youtube', 'tiktok', 'instagram']:
            return self.error_response("Invalid platform", status_code=status.HTTP_400_BAD_REQUEST)

        # Step 1: Fetch platform data
        if platform == 'youtube':
            video_list = self.fetch_youtube_videos(region, genre)
        elif platform == 'tiktok':
            video_list = self.fetch_tiktok_videos(genre or "funny")
        elif platform == 'instagram':
            video_list = self.fetch_instagram_profiles(genre or "insta")
        else:
            video_list = []

        if not video_list:
            return self.success_response("No data found for given filters.", data=[], status_code=status.HTTP_200_OK)

        # Step 2: Calculate AI score
        final_list = self.calculate_ai_score(video_list, ai_score_min, ai_score_max)

        # Step 3: Sort
        sorted_list = self.sort_videos(final_list, sort_by)

        return self.success_response("Top list fetched successfully.", data=sorted_list)

    # --------------------------
    # Fetch YouTube Data
    # --------------------------
    def fetch_youtube_videos(self, region, genre):
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "regionCode": region,
            "q": genre or "Education",
            "type": "channel",
            "maxResults": 6,
            "key": settings.YOUTUBE_API_KEY
        }
        try:
            search_res = requests.get(search_url, params=params)
            search_data = search_res.json()

            videos = []
            channel_ids = [item["id"]["channelId"] for item in search_data.get("items", [])]
            if not channel_ids:
                return videos

            # Fetch channel details
            channel_url = "https://www.googleapis.com/youtube/v3/channels"
            channel_params = {
                "part": "snippet,statistics",
                "id": ",".join(channel_ids),
                "key": settings.YOUTUBE_API_KEY
            }
            channel_res = requests.get(channel_url, params=channel_params)
            channel_data = channel_res.json()

            for idx, item in enumerate(channel_data.get("items", []), start=1):
                stats = item.get("statistics", {})
                snippet = item.get("snippet", {})
                channel_id = item.get("id")

                subscribers = self.format_number(stats.get("subscriberCount", "0"))
                views = self.format_number(stats.get("viewCount", "0"))

                videos.append({
                    "rank": idx,
                    "platform": "YouTube",
                    "channel": snippet.get("title"),
                    "channel_link": f"https://www.youtube.com/channel/{channel_id}",
                    "country": region,
                    "safety_tag": "Parent-Rated",
                    "genre": genre or "Education",
                    "age_range": "3-6",
                    "subscribers": subscribers,
                    "views": views,
                    "ai_score": 0
                })
            return videos
        except Exception as e:
            print("DEBUG - YouTube Fetch Error:", e)
            return []

    # --------------------------
    # Fetch TikTok Data
    # --------------------------
    def fetch_tiktok_videos(self, keyword):
        url = "https://tiktok-api23.p.rapidapi.com/api/search/video"
        querystring = {"keyword": keyword, "cursor": "0", "search_id": "0"}
        headers = {
            "x-rapidapi-key": settings.RAPIDAPI_KEY,
            "x-rapidapi-host": "tiktok-api23.p.rapidapi.com"
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()

            items = data.get("item_list", [])
            if not items:
                print("DEBUG - No TikTok items found in item_list.")
                return []

            results = []
            for idx, item in enumerate(items, start=1):
                author = item.get("author", {})
                author_stats = item.get("authorStats", {})
                stats = item.get("stats", {})

                results.append({
                    "rank": idx,
                    "platform": "TikTok",
                    "channel": author.get("uniqueId", "Unknown"),
                    "channel_link": f"https://www.tiktok.com/@{author.get('uniqueId', '')}",
                    "country": "N/A",
                    "safety_tag": "General",
                    "genre": keyword,
                    "age_range": "13+",
                    "subscribers": self.format_number(author_stats.get("followerCount", 0)),
                    "views": self.format_number(stats.get("playCount", 0)),
                    "ai_score": 0
                })
            return results

        except Exception as e:
            print("DEBUG - TikTok Fetch Error:", e)
            return []

    # --------------------------
    # Fetch Instagram Data
    # --------------------------
    def fetch_instagram_profiles(self, keyword):
        search_url = "https://instagram-scraper-20251.p.rapidapi.com/searchuser/"
        search_query = {"keyword": keyword}
        headers = {
            "x-rapidapi-key": settings.RAPIDAPI_KEY,
            "x-rapidapi-host": "instagram-scraper-20251.p.rapidapi.com"
        }

        try:
            # Step 1: Search profiles
            search_response = requests.get(search_url, headers=headers, params=search_query)
            search_data = search_response.json()
            items = search_data.get("data", {}).get("items", [])

            if not items:
                print("DEBUG - No Instagram profiles found in search.")
                return []

            results = []
            for idx, user in enumerate(items[:6], start=1):  # Limit to top 6 profiles
                username = user.get("username")
                full_name = user.get("full_name", "Unknown")
                profile_pic = user.get("profile_pic_url")
                follower_count = 0
                media_count = 0

                # Step 2: Get detailed user info
                try:
                    userinfo_url = "https://instagram-scraper-20251.p.rapidapi.com/userinfo/"
                    userinfo_query = {"username_or_id": username}
                    userinfo_res = requests.get(userinfo_url, headers=headers, params=userinfo_query)
                    userinfo_data = userinfo_res.json().get("data", {})

                    follower_count = userinfo_data.get("follower_count", 0)
                    media_count = userinfo_data.get("media_count", 0)  # Use as 'views'
                    country = userinfo_data.get("country_block", "Unknown") or "Unknown"
                except Exception as e:
                    print(f"DEBUG - Failed to fetch userinfo for {username}: {e}")
                    country = "Unknown"

                results.append({
                    "rank": idx,
                    "platform": "Instagram",
                    "channel": full_name,
                    "channel_link": f"https://www.instagram.com/{username}",
                    "country": country,
                    "safety_tag": "General",
                    "genre": keyword,
                    "age_range": "Unavailable",  # Instagram does not provide this
                    "subscribers": self.format_number(follower_count),
                    "views": self.format_number(media_count),
                    "ai_score": 0,
                })

            return results

        except Exception as e:
            print("DEBUG - Instagram Fetch Error:", e)
            return []

    # --------------------------
    # AI Score Calculation
    # --------------------------
    def calculate_ai_score(self, videos, ai_score_min, ai_score_max):
        final_videos = []
        for v in videos:
            try:
                subs = self.parse_number(v.get("subscribers", "0"))
                views = self.parse_number(v.get("views", "0"))

                # -----------------------------
                # Adjusted scaling
                # -----------------------------
                views_score = min(10, (views / 500_000) * 2)  # 500K views = 10
                subs_score = min(10, (subs / 50_000) * 2)     # 50K subs = 10
                activity_score = 8.5                         # Boosted activity score

                # -----------------------------
                # Final weighted AI score
                # -----------------------------
                score = round((views_score * 0.5) + (subs_score * 0.3) + (activity_score * 0.2), 2)
                score = min(10, score)  # Max 10

            except Exception as e:
                print("DEBUG - AI Score Calculation Error:", e)
                score = 5.0

            if ai_score_min <= score <= ai_score_max:
                v['ai_score'] = score
                final_videos.append(v)
        return final_videos

    # --------------------------
    # Sorting
    # --------------------------
    def sort_videos(self, videos, sort_by):
        try:
            if sort_by == 'subscribers':
                return sorted(videos, key=lambda x: self.parse_number(x['subscribers']), reverse=True)
            elif sort_by == 'views':
                return sorted(videos, key=lambda x: self.parse_number(x['views']), reverse=True)
        except Exception as e:
            print("DEBUG - Sort Error:", e)
        return videos

    # --------------------------
    # Number Formatting
    # --------------------------
    def format_number(self, num):
        try:
            num = int(num)
        except:
            return str(num)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        return str(num)

    def parse_number(self, num_str):
        num_str = str(num_str)
        if num_str.endswith('B'):
            return int(float(num_str[:-1]) * 1_000_000_000)
        elif num_str.endswith('M'):
            return int(float(num_str[:-1]) * 1_000_000)
        elif num_str.endswith('K'):
            return int(float(num_str[:-1]) * 1_000)
        try:
            return int(num_str)
        except:
            return 0
