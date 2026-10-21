from django.test import TestCase
# from django.contrib.auth import get_user_model
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APIClient
# from apps.creator_dashboard.models import (
#     CreatorProfile,
#     TiktokProfile,
#     YoutubeProfile,
#     InstagramProfile,
#     TiktokProfileMedia,
#     YoutubeProfileMedia,
#     InstagramProfileMedia
# )

# User = get_user_model()

# class InsightPerformanceAPITests(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user(email="testinsight@example.com", password="password", name="Test Insight Creator")
#         self.profile = CreatorProfile.objects.create(user=self.user)
#         self.client.force_authenticate(user=self.user)

#         # Create YouTube, TikTok and Instagram profiles
#         self.yt_profile = YoutubeProfile.objects.create(profile=self.profile, subscribers_count=500, channel_title="Test YT Channel")
#         self.tt_profile = TiktokProfile.objects.create(profile=self.profile, followers_count=800, username="test_tt")
#         self.ig_profile = InstagramProfile.objects.create(profile=self.profile, followers_count=1200, username="test_ig")

#         # Create YouTube Profile Media
#         YoutubeProfileMedia.objects.create(
#             profile=self.profile,
#             video_id="yt_vid_1",
#             title="Video 1",
#             view_count=1000,
#             likes_count=100,
#             comment_count=10,
#             created_at="2026-05-01T00:00:00Z"
#         )

#         # Create TikTok Profile Media
#         TiktokProfileMedia.objects.create(
#             profile=self.profile,
#             video_id="tt_vid_1",
#             title="TikTok Video 1",
#             view_count=2000,
#             likes_count=200,
#             comment_count=20,
#             created_at="2026-05-01T00:00:00Z"
#         )

#     def test_youtube_insight_api(self):
#         url = reverse('insight-performance')
#         response = self.client.get(url, {'platform': 'youtube', 'range': '30d'})
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         data = response.json()
#         self.assertTrue(data['success'])
#         self.assertEqual(data['data']['profile']['platform'], 'YouTube')
#         self.assertEqual(data['data']['profile']['followers'], 500)
#         self.assertEqual(len(data['data']['top_content']), 1)
#         self.assertEqual(data['data']['top_content'][0]['id'], 'yt_vid_1')

#     def test_tiktok_insight_api(self):
#         url = reverse('insight-performance')
#         response = self.client.get(url, {'platform': 'tiktok', 'range': '30d'})
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         data = response.json()
#         self.assertTrue(data['success'])
#         self.assertEqual(data['data']['profile']['platform'], 'TikTok')
#         self.assertEqual(data['data']['profile']['followers'], 800)
#         self.assertEqual(len(data['data']['top_content']), 1)
#         self.assertEqual(data['data']['top_content'][0]['id'], 'tt_vid_1')

#     def test_insight_pdf_download(self):
#         url = reverse('insight-download')
#         response = self.client.get(url, {'platform': 'tiktok'})
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response['Content-Type'], 'application/pdf')
#         self.assertTrue(response['Content-Disposition'].startswith('attachment; filename='))