import os
from datetime import timedelta
from unittest import mock, result

import django

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.payment_stripe.models import Subscription

from .models import ChildProfile, JobRun, Playlist
from .permissions import PlaylistGenerationPermission
from .services import build_playlist, fetch_transcript


User = get_user_model()


class PlaylistGenerationPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="parent@example.com", password="pass1234", name="Parent")

    def test_allows_first_free_playlist_without_subscription(self):
        request = APIRequestFactory().post("/api/v1/parents/playlists/")
        request.user = self.user

        permission = PlaylistGenerationPermission()

        self.assertTrue(permission.has_permission(request, None))

    def test_allows_playlist_generation_when_subscription_is_still_active(self):
        Subscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_test",
            stripe_subscription_id="sub_test",
            package="package-1",
            billing_interval="monthly",
            is_active=True,
            current_period_end=timezone.now() + timedelta(days=10),
        )

        request = APIRequestFactory().post("/api/v1/parents/playlists/")
        request.user = self.user

        permission = PlaylistGenerationPermission()

        self.assertTrue(permission.has_permission(request, None))

    def test_blocks_playlist_generation_after_free_allowance_when_subscription_has_expired(self):
        Subscription.objects.create(
            user=self.user,
            stripe_customer_id="cus_test",
            stripe_subscription_id="sub_test",
            package="package-1",
            billing_interval="monthly",
            is_active=False,
            current_period_end=timezone.now() - timedelta(days=1),
        )
        Playlist.objects.create(user=self.user, status="ready")

        request = APIRequestFactory().post("/api/v1/parents/playlists/")
        request.user = self.user

        permission = PlaylistGenerationPermission()

        self.assertFalse(permission.has_permission(request, None))


# class ParentsDashboardTests(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         self.user = User.objects.create_user(email="parent@example.com", password="pass1234", name="Parent")
#         self.other_user = User.objects.create_user(email="other@example.com", password="pass1234", name="Other")

#         self.child = ChildProfile.objects.create(
#             parent=self.user,
#             age_band="6-8",
#             language="English",
#             preferences={"tone": "calm"},
#         )

#     def test_free_plan_save_limit(self):
#         self.client.force_authenticate(self.user)

#         Playlist.objects.create(
#             user=self.user,
#             child_profile=self.child,
#             filters_json={"age_band": "6-8"},
#             session_length=10,
#             status="ready",
#             is_saved=True,
#             title="Saved 1",
#         )
#         p2 = Playlist.objects.create(
#             user=self.user,
#             child_profile=self.child,
#             filters_json={"age_band": "6-8"},
#             session_length=10,
#             status="ready",
#             is_saved=False,
#             title="Saved 2",
#         )

#         resp = self.client.post(f"/api/v1/parents/playlists/{p2.id}/save/")
#         self.assertEqual(resp.status_code, 400)
#         self.assertIn("only 1 saved playlist", resp.data.get("message", "").lower())

#     @mock.patch("apps.parents.views.generate_parent_playlist.delay")
#     def test_playlist_creation_queues_job(self, mock_delay):
#         self.client.force_authenticate(self.user)

#         payload = {
#             "child_profile_id": self.child.id,
#             "filters": {"content_type": "Educational", "tone": "Calm"},
#             "session_length": 10,
#         }
#         resp = self.client.post("/api/v1/parents/playlists/", payload, format="json")
#         self.assertEqual(resp.status_code, 201)
#         self.assertTrue("playlist_id" in resp.data["data"])
#         self.assertTrue("job_id" in resp.data["data"])

#         job_id = resp.data["data"]["job_id"]
#         self.assertTrue(JobRun.objects.filter(id=job_id, user=self.user, status="queued").exists())
#         mock_delay.assert_called_once()

#     def test_build_playlist_prefers_multiple_videos_for_target_duration(self):
#         candidates = [
#             {"video_id": "vid1", "duration": 700, "title": "Video 1"},
#             {"video_id": "vid2", "duration": 500, "title": "Video 2"},
#             {"video_id": "vid3", "duration": 1182, "title": "Video 3"},
#         ]
#         selected = build_playlist(candidates, session_length_minutes=20)

#         self.assertEqual(len(selected), 2)
#         self.assertEqual([item["video_id"] for item in selected], ["vid1", "vid2"])

#     def test_permissions_cannot_access_other_user_playlist(self):
#         self.client.force_authenticate(self.other_user)

#         playlist = Playlist.objects.create(
#             user=self.user,
#             child_profile=self.child,
#             filters_json={"age_band": "6-8"},
#             session_length=10,
#             status="ready",
#             is_saved=False,
#             title="Private",
#         )

#         resp = self.client.get(f"/api/v1/parents/playlists/{playlist.id}/")
#         self.assertEqual(resp.status_code, 404)

#     @mock.patch("apps.parents.services.YouTubeTranscriptApi.get_transcript")
#     @mock.patch("apps.parents.services.requests.get")
#     def test_transcript_fetch_fallback(self, mock_requests_get, mock_get_transcript):
#         mock_requests_get.return_value.status_code = 404
#         mock_requests_get.return_value.json.return_value = {}

#         mock_get_transcript.return_value = [{"text": "hello world"}]

#         text, source = fetch_transcript("abc123", language="English", youtube_access_token="token")
#         self.assertEqual(text, "hello world")
#         self.assertEqual(source, "youtube_transcript_api")

#     @mock.patch("apps.parents.views.get_channel_top_videos")
#     @mock.patch("apps.parents.views.get_age_range_for_channel")
#     @mock.patch("apps.parents.views.convert_age_range_to_text")
#     def test_trending_top_videos_by_channel(self, mock_convert_age, mock_get_age, mock_get_channel_top):
#         mock_get_channel_top.return_value = [
#             {
#                 "video_id": "vid123",
#                 "title": "Fun Video",
#                 "channel_title": "Cool Channel",
#                 "thumbnail": "http://example.com/thumb.jpg",
#                 "url": "https://www.youtube.com/watch?v=vid123",
#                 "view_count": "1000",
#                 "age_rating": "G"
#             }
#         ]
#         mock_get_age.return_value = {"recommended_age_range": "5-8"}
#         mock_convert_age.return_value = "5+"

#         resp = self.client.get("/api/trending-top-videos/chan123/")
#         self.assertEqual(resp.status_code, 200)
#         self.assertEqual(resp.data["message"], "Channel top videos fetched successfully")
        
#         # Verify the mocked function was called with channel_id="chan123" and count=10 (default)
#         mock_get_channel_top.assert_called_once_with("chan123", 10)
        
#         # Verify response contents
#         videos = resp.data["data"]
#         self.assertEqual(len(videos), 1)
#         self.assertEqual(videos[0]["video_id"], "vid123")
#         self.assertEqual(videos[0]["age_rating"], "5+")


# import requests
# from django.conf import settings
# from django.test import TestCase


# class YouTubeAPIKeyTest(TestCase):

#     def test_youtube_api_key_is_valid(self):
#         api_key = settings.YOUTUBE_API_KEY

#         url = "https://www.googleapis.com/youtube/v3/search"

#         params = {
#             "part": "snippet",
#             "q": "test",
#             "key": api_key,
#             "maxResults": 3,
#             "type": "video",
#             "videoDuration":"long"
#         }

#         response = requests.get(url, params=params, timeout=10)
#         data = response.json()
#         print(data)
#         # Assert HTTP success
#         self.assertEqual(
#             response.status_code,
#             200,
#             msg=f"YouTube API failed: {data}"
#         )

#         # Assert response has items
#         self.assertIn("items", data)
#         self.assertGreater(len(data["items"]), 0)


# import os
# from openai import OpenAI 

# client = OpenAI(api_key=config("TEST_OPEN_API_KEY"))

# try:
#     models = client.models.list()
#     print(models,"API key is valid")
# except Exception as e:
#     print("API key is invalid or has another issue:")
#     print(e)