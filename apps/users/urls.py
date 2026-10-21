from django.urls import path
from .views import (
    SignupView, SignupOTPVerifyView, LoginView, ProfileView,
    PasswordResetRequestAPIView, PasswordResetOTPVerifyView, PasswordResetChangeAPIView, LogoutView, ChangePassword, GoogleLoginView,
    PlatformAccountListView, DeleteAccountAPIView, PasswordResetResendOTPView
)
from rest_framework_simplejwt.views import TokenRefreshView

from .views import TikTokAuthURLView, TikTokCallbackView
from .views import InstagramAuthURLView, InstagramCallbackView

from .views import YouTubeAuthURLView, YouTubeCallbackView

urlpatterns = [
    # Signup
    path("signup/", SignupView.as_view(), name="signup"),
    path("signup/verify-otp/", SignupOTPVerifyView.as_view(), name="signup-verify-otp"),

    # Login & Profile
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("platform-accounts/", PlatformAccountListView.as_view(), name="platform_accounts"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Password Reset
    path("password-reset/request/", PasswordResetRequestAPIView.as_view(), name="password-reset-request"),
    path("password-reset/resend-otp/", PasswordResetResendOTPView.as_view(), name="password-reset-resend-otp"),
    path("password-reset/verify-otp/", PasswordResetOTPVerifyView.as_view(), name="password-reset-verify-otp"),
    path("password-reset/change-password/", PasswordResetChangeAPIView.as_view(), name="password-reset-change"),

    # Change Password
    path("change-password/", ChangePassword.as_view(), name="change-password"),

    # Logout
    path("logout/", LogoutView.as_view(), name="logout"),

    # Login with Google
    path('google/', GoogleLoginView.as_view(), name='google_login'),

    path("tiktok/auth-url/", TikTokAuthURLView.as_view(), name="tiktok_auth_url"),
    path("v1/auth/tiktok/callback/", TikTokCallbackView.as_view(), name="tiktok_callback"),

    path("instagram/auth-url/", InstagramAuthURLView.as_view(), name="instagram_auth_url"),
    # path("v1/auth/instagram/callback/", InstagramCallbackView.as_view(), name="instagram_callback"),

    path("youtube/auth-url/", YouTubeAuthURLView.as_view(), name="youtube_auth_url"),
    path("v1/auth/youtube/callback/", YouTubeCallbackView.as_view(), name="youtube_callback"),

    # Delete Account
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete-account'),
]
