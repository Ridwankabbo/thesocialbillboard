from .views import TikTokQueryVideosAPIView, TikTokListVideosAPIView
from django.urls import path


urlpatterns = [
    path("tiktok/videos/query/", TikTokQueryVideosAPIView.as_view(), name="tiktok_videos_query"),
    path("tiktok/videos/list/", TikTokListVideosAPIView.as_view(), name="tiktok_videos_list"),
]
