from django.urls import path
from apps.dashbord_analytics.views import (
    YouTubeAnalyticsAPIView,
    YouTubeCompetitorByUsernameAPIView,
)

urlpatterns = [
    path("youtube/analytics/", YouTubeAnalyticsAPIView.as_view()),
    path("youtube/competitors/", YouTubeCompetitorByUsernameAPIView.as_view()),
]


