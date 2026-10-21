from django.test import TestCase
# from django.contrib.auth import get_user_model
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from .models import (
#     CreatorProfile,
#     TiktokProfile,
#     YoutubeProfile,
#     InstagramProfile,
#     TiktokCredentials,
#     YoutubeCredentials,
#     InstagramCredentials,
#     TiktokProfileMedia,
#     YoutubeProfileMedia,
#     InstagramProfileMedia
# )

# User = get_user_model()

# class PlatformDisconnectTests(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user(email="testcreator@example.com", password="password", name="Test Creator")
#         self.profile = CreatorProfile.objects.create(user=self.user)
#         self.client.force_authenticate(user=self.user)

#     def test_tiktok_disconnect(self):
#         # Create mock data
#         TiktokCredentials.objects.create(profile=self.profile, access_token="tk_access")
#         TiktokProfile.objects.create(profile=self.profile, followers_count=100)
#         TiktokProfileMedia.objects.create(
#             profile=self.profile,
#             video_id="tt_vid",
#             created_at="2026-01-01T00:00:00Z"
#         )

#         # Call endpoint
#         response = self.client.post(reverse('tiktok-disconnect'))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.json()['message'], "TikTok disconnected successfully")

#         # Verify deletion
#         self.assertFalse(TiktokCredentials.objects.filter(profile=self.profile).exists())
#         self.assertFalse(TiktokProfile.objects.filter(profile=self.profile).exists())
#         self.assertFalse(TiktokProfileMedia.objects.filter(profile=self.profile).exists())

#     def test_youtube_disconnect(self):
#         # Create mock data
#         YoutubeCredentials.objects.create(profile=self.profile, access_token="yt_access")
#         YoutubeProfile.objects.create(profile=self.profile, subscribers_count=200)
#         YoutubeProfileMedia.objects.create(
#             profile=self.profile,
#             video_id="yt_vid",
#             created_at="2026-01-01T00:00:00Z"
#         )

#         # Call endpoint
#         response = self.client.post(reverse('youtube-disconnect'))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.json()['message'], "YouTube disconnected successfully")

#         # Verify deletion
#         self.assertFalse(YoutubeCredentials.objects.filter(profile=self.profile).exists())
#         self.assertFalse(YoutubeProfile.objects.filter(profile=self.profile).exists())
#         self.assertFalse(YoutubeProfileMedia.objects.filter(profile=self.profile).exists())

#     def test_instagram_disconnect(self):
#         # Create mock data
#         InstagramCredentials.objects.create(profile=self.profile, access_token="ig_access")
#         InstagramProfile.objects.create(profile=self.profile, followers_count=300)
#         InstagramProfileMedia.objects.create(
#             profile=self.profile,
#             video_id="ig_vid",
#             created_at="2026-01-01T00:00:00Z"
#         )

#         # Call endpoint
#         response = self.client.post(reverse('instagram-disconnect'))
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.json()['message'], "Instagram disconnected successfully")

#         # Verify deletion
#         self.assertFalse(InstagramCredentials.objects.filter(profile=self.profile).exists())
#         self.assertFalse(InstagramProfile.objects.filter(profile=self.profile).exists())
#         self.assertFalse(InstagramProfileMedia.objects.filter(profile=self.profile).exists())
