from django.urls import path
from .views import (
    TiktokLoginView,
    TiktokCallBackView,
    TiktokProfileView,
    TiktokRefreshTokenView,
    YoutubeVideosSyncView,
    YoutubeAuthView,
    YoutubeCallbackView,
    CreatorProfileView,
    InstagramAuthView,
    InstagramCallbackView,
    InstagramWebhookInfoView,
    InstagramSyncView,
    YoutubeRefreshTokenView,
    InstagramRefreshTokenView,
    CompetitiorsAPIView,
    TiktokDisconnectView,
    YoutubeDisconnectView,
    InstagramDisconnectView,
)
urlpatterns = [
    path('platform/tiktok/auth/', TiktokLoginView.as_view(), name='tiktok-auth'),
    path('platform/tiktok/callback/', TiktokCallBackView.as_view(), name='tiktok-callback'),
    path('platform/tiktok/profile/overview/', TiktokProfileView.as_view(), name='profile-details'),
    path('platform/tiktok/token/refresh/', TiktokRefreshTokenView.as_view(), name='tiktok-token-refresh'),
    path('platform/tiktok/disconnect/', TiktokDisconnectView.as_view(), name='tiktok-disconnect'),
    
    
    path('platform/youtube/auth/', YoutubeAuthView.as_view(), name='youtube-auth'),
    path('platform/youtube/callback/', YoutubeCallbackView.as_view(), name='youtube-callback'),
    path('platform/youtube/profile/overview/', YoutubeVideosSyncView.as_view(), name='youtube-details'),
    path('platform/youtube/token/refresh/', YoutubeRefreshTokenView.as_view(), name='youtube-token-refresh'),
    path('platform/youtube/disconnect/', YoutubeDisconnectView.as_view(), name='youtube-disconnect'),

    # path('platform/instagram/webhook/', instagram_webhook, name='instagram-weebhook'),
    path('platform/instagram/auth/', InstagramAuthView.as_view(), name='instagram-auth'),
    path('auth/instagram/callback/', InstagramCallbackView.as_view(), name='instagram-callback'),
    # path('v1/platform/instagram/media/', InstagramSyncView.as_view(), name='instagram-profile'),
    path('platform/instagram/profile/overview/', InstagramSyncView.as_view(), name='instagram-profile-overview'),
    path('platform/instagram/webhook/info/', InstagramWebhookInfoView.as_view(), name='instagram-webhook-info'),
    path('platform/instagram/token/refresh/', InstagramRefreshTokenView.as_view(), name='instagram-token-refresh'),
    path('platform/instagram/disconnect/', InstagramDisconnectView.as_view(), name='instagram-disconnect'),
    # path('v1/platform/instagram/profile/', InstagramSyncView.as_view(), name='instagram-profile'),
    
    
    
    path('creator/dashboard/', CreatorProfileView.as_view(), name='creator-profile'),
    path('creator/competitions/', CompetitiorsAPIView.as_view(), name='creator-competitions'),


]
