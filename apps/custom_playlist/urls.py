from django.urls import path
from .views import (
    CustomPlaylistListAPIView,
    CustomPlaylistDetailsAPIView,
    SavedCustomPlaylistAPIView,
)
urlpatterns = [
    path('v1/playlist/custom/get-list/', CustomPlaylistListAPIView.as_view(), name='custom-playlist'),
    path('v1/playlist/custom/get-list/', CustomPlaylistListAPIView.as_view(), name='custom-playlist-filter'),
    path('v1/playlist/custom/get-list/<int:playlist_id>/', CustomPlaylistDetailsAPIView.as_view(), name='custom-playlist-detail'),
    path('v1/playlist/custom/saved/', SavedCustomPlaylistAPIView.as_view(), name='saved-custom-playlist'),
]
