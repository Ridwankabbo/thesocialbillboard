from django.urls import path
from .views import *

urlpatterns = [

  path('overview/<str:channel_id>/', ChannelOverviewAPIView.as_view(), name='channel-overview'),
  path('playlists/', PlaylistAPIView.as_view(), name='playlist-list'),
  path("playlist/<int:pk>/", PlaylistAPIView.as_view(), name="playlist-detail"),

  path('add-to-playlists/<str:video_id>/', AddChannelToPlaylistsAPIView.as_view()),
  
  path('playlists/<int:playlist_id>/channels/', PlaylistChannelsAPIView.as_view()),
  path('follow-playlists/', FollowPlaylistApiView.as_view(), name='follow-playlists'),

  path("curated-playlists/", CuratedPlaylistsAPIView.as_view(), name="curated-playlists"),

  path('reviews/', ReviewAPIView.as_view(), name='reviews'),
  path('feedbacks/', FeedbackAPIView.as_view(), name='feedbacks'),

  path('trending-top-videos/<str:channel_id>/', TrendingTopVideosAPIView.as_view(), name='trending-top-videos'),

  # Parents Dashboard V1
  path('v1/parents/children/', ChildProfileAPIView.as_view(), name='parents-children'),
  path('v1/parents/children/age-band/list/', ChildAgeBandListAPIView.as_view(), name='parents-children'),
  path('v1/parents/playlists/get/', ParentPlaylistGetAPIView.as_view(), name='parent-playlist-get'),
  path('v1/parents/playlists/', ParentPlaylistCreateAPIView.as_view(), name='parents-playlists'),
  path('v1/parents/playlists/overview/', ParentPlaylistOverviewAPIView.as_view(), name='parents-playlist-overview'),
  path('v1/parents/playlists/get/<int:playlist_id>/', ParentPlaylistGetDetailAPIView.as_view(), name='parents-playlist-detail'),
  path('v1/parents/playlists/<int:playlist_id>/', ParentPlaylistDetailAPIView.as_view(), name='parents-playlist-detail'),
  path('v1/parents/playlists/<int:playlist_id>/regenerate/', ParentPlaylistRegenerateAPIView.as_view(), name='parents-playlist-regenerate'),
  path('v1/parents/playlists/<int:playlist_id>/save/', ParentPlaylistSaveAPIView.as_view(), name='parents-playlist-save'),
  path('v1/parents/playlists/by-child/', AllPlaylistbychild.as_view(), name='parents-playlist-saved'),
  path('v1/jobs/<uuid:job_id>/', JobStatusAPIView.as_view(), name='parents-job-status'),
  path('v1/jobs/<uuid:job_id>/cancel/', JobCancelAPIView.as_view(), name='parents-job-cancel'),

  path("premium/", PremiumFeatureView.as_view(), name="premium-feature"),
  
  path("v1/parents/video/<str:video_id>/transcript/", VideoTranscriptAPIView.as_view(), name="video-transcript"),
  path("v1/parents/playlist/<int:playlist_id>/analyze/", StartPlaylistAnalysisAPIView.as_view(), name="playlist-analyze")

]
