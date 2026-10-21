

from django.urls import path
from .views import *
from .tiktok_utils import *

urlpatterns = [
    path('youtube-analyze/', YouTubeAnalyzerAPIView.as_view(), name='youtube-analyze'), # overView folder
    # Instagram
    path("instagram-analyze/", InstagramAnalyticsAIView.as_view(), name="instagram-analyze"),# overView folder

    path('update-social-links/', UpdateSocialLinksView.as_view(), name='update-social-links'),# overView folder

    # TikTok
    path('tiktok-analyze/', TikTokAnalyzerAPIView.as_view(), name='tiktok-analyze'),# overView folder

    path('creator-analytics-overview/', CreatorAnalyticsOverviewAPIView.as_view(), name='creator-analytics-overview'),

    # Creator Ranking
    path("top-rank-creators/", CreatorRankingAPIView.as_view(), name="top-creators"),# overView folder
    path("creator-ranking/download/", CreatorRankingDownloadAPIView.as_view(), name="creator-ranking-download"), # leaderboard folder


    path("insight-performance/", InsightPerformanceAPIView.as_view(), name="insight-performance"),# overView folder
    path('insight-performance/download/', InsightperformanceDownloadPDFView.as_view(), name='insight-download'),  # leaderboard folder
    path('user-top-videos/', TopVideosAPIView.as_view(), name='user-top-videos'),# overView folder

]