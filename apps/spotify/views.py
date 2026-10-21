# from rest_framework.views import APIView
# from rest_framework.response import Response
# import requests
# import base64
# import os
# from rest_framework import status, permissions
# from .models import SpotifyData

# # CLIENT_ID = config("SPOTIFY_CLIENT_ID")
# # CLIENT_SECRET = config("SPOTIFY_CLIENT_SECRET")


# # def get_spotify_token():
# #     auth_url = 'https://accounts.spotify.com/api/token'
# #     auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
# #     headers = {
# #         'Authorization': f'Basic {auth_header}',
# #         'Content-Type': 'application/x-www-form-urlencoded'
# #     }
# #     data = {'grant_type': 'client_credentials'}
# #     response = requests.post(auth_url, headers=headers, data=data)
# #     return response.json().get('access_token')


# # class PodcastCategoryAPIView(BaseAPIView):
# #     def get(self, request):
# #         token = get_spotify_token()
# #         print("Spotify Token:", token)
# #         query = request.query_params.get('q', 'parenting')
# #         limit = request.query_params.get('limit', 10)

# #         url = f"https://api.spotify.com/v1/search?q={query}&type=show&market=US&limit={limit}"
# #         headers = {'Authorization': f'Bearer {token}'}
# #         response = requests.get(url, headers=headers)

# #         if response.status_code != 200:
# #             return self.error_response(
# #                 "Failed to fetch podcast data from Spotify.",
# #                 status_code=response.status_code
# #             )

# #         data = response.json().get('shows', {}).get('items', [])
# #         result = []
# #         for show in data:
# #             result.append({
# #                 "title": show.get('name'),
# #                 "description": show.get('description'),
# #                 "publisher": show.get('publisher'),
# #                 "spotify_url": show.get('external_urls', {}).get('spotify'),
# #                 "image": show.get('images', [{}])[0].get('url', None)
# #             })

# #         return self.success_response("Podcasts fetched successfully", data=result)



# # class BaseAPIView(APIView):
# #     def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
# #         return Response(
# #             {"success": True, "message": message, "status": status_code, "data": data or {}},
# #             status=status_code
# #         )

# #     def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
# #         return Response(
# #             {"success": False, "message": message, "status": status_code, "data": data or {}},
# #             status=status_code
# #         )


# class PodcastCategoryAPIView(APIView):
#     def get(self, request):
#         try:
#             obj = SpotifyData.objects.get(name="spotify_latest_parenting")
#             return Response({
#                 "success": True,
#                 "message": "Latest Spotify data fetched",
#                 "data": obj.data
#             }, status=status.HTTP_200_OK)
#         except SpotifyData.DoesNotExist:
#             return Response({
#                 "success": False,
#                 "message": "No Spotify data found",
#                 "data": {}
#             }, status=status.HTTP_404_NOT_FOUND)








# app/spotify/views.py
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SpotifyData
from .services import fetch_and_store_spotify_podcasts

class PodcastCategoryAPIView(APIView):
    """
    ভিউ লজিক:
    - আগে DB থেকে name="spotify_latest_parenting" খুঁজবে
    - না পেলে: সাথে সাথে API কল করে DB-তে সেভ করবে, তারপর রিটার্ন
    - পেলে: 'stale' হলে (ধরি 6 ঘন্টা পুরোনো) রিফ্রেশ করে দেবে
    - চাইলে ?refresh=1 কুয়েরি প্যারাম দিয়ে ফোর্স-রিফ্রেশ করা যাবে
    """
    STALE_AFTER = timedelta(hours=6)

    def get(self, request):
        force_refresh = request.query_params.get("refresh") in ("1", "true", "True")
        name = "spotify_latest_parenting"

        try:
            obj = SpotifyData.objects.get(name=name)
            is_stale = not obj.fetched_at or (timezone.now() - obj.fetched_at) > self.STALE_AFTER

            if force_refresh or is_stale:
                items = fetch_and_store_spotify_podcasts(name=name)
                if items is None:
                    # API ডাউন/টোকেন ইস্যু হলে ফ্যালব্যাক: পুরোনো ডাটা দেখাই
                    return Response({
                        "success": True,
                        "message": "Showing cached Spotify data (refresh failed).",
                        "data": obj.data
                    }, status=status.HTTP_200_OK)
                return Response({
                    "success": True,
                    "message": "Fresh Spotify data fetched",
                    "data": items
                }, status=status.HTTP_200_OK)

            # not stale: cached
            return Response({
                "success": True,
                "message": "Latest Spotify data (cached)",
                "data": obj.data
            }, status=status.HTTP_200_OK)

        except SpotifyData.DoesNotExist:
            # DB-তে একদমই নেই → এখনই ফেচ করে সেভ
            items = fetch_and_store_spotify_podcasts(name=name)
            if items is None:
                return Response({
                    "success": False,
                    "message": "Could not fetch data from Spotify right now.",
                    "data": []
                }, status=status.HTTP_502_BAD_GATEWAY)

            return Response({
                "success": True,
                "message": "Fresh Spotify data fetched",
                "data": items
            }, status=status.HTTP_200_OK)
