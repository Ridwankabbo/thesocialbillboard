from django.urls import path

from . import views

urlpatterns = [
    path('creator-dashboard/leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]