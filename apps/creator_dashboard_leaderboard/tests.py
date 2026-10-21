from django.test import TestCase
# from django.contrib.auth import get_user_model
# from apps.creator_dashboard.models import (
#     CreatorProfile,
#     TiktokProfile,
#     YoutubeProfile,
#     InstagramProfile,
#     TiktokProfileMedia,
#     YoutubeProfileMedia,
#     InstagramProfileMedia
# )
# from apps.creator_dashboard_leaderboard.service import get_leaderboard_data

# User = get_user_model()

# class LeaderboardServiceTests(TestCase):
#     def setUp(self):
#         # Create users
#         self.user1 = User.objects.create_user(email="creator1@example.com", password="password", name="Creator One")
#         self.user2 = User.objects.create_user(email="creator2@example.com", password="password", name="Creator Two")

#         # Create profiles
#         self.profile1 = CreatorProfile.objects.create(user=self.user1)
#         self.profile2 = CreatorProfile.objects.create(user=self.user2)

#         # Setup platform profiles for creator 1
#         TiktokProfile.objects.create(profile=self.profile1, followers_count=1000)
#         YoutubeProfile.objects.create(profile=self.profile1, subscribers_count=5000)
#         InstagramProfile.objects.create(profile=self.profile1, followers_count=2000)

#         # Setup platform profiles for creator 2
#         TiktokProfile.objects.create(profile=self.profile2, followers_count=1500)
#         YoutubeProfile.objects.create(profile=self.profile2, subscribers_count=3000)
#         InstagramProfile.objects.create(profile=self.profile2, followers_count=2500)

#         # Media for Creator 1: YouTube
#         YoutubeProfileMedia.objects.create(
#             profile=self.profile1,
#             video_id="yt1",
#             view_count=10000,
#             likes_count=1000,
#             comment_count=100,
#             created_at="2026-01-01T00:00:00Z"
#         )
#         # Media for Creator 1: TikTok
#         TiktokProfileMedia.objects.create(
#             profile=self.profile1,
#             video_id="tt1",
#             view_count=5000,
#             likes_count=500,
#             comment_count=50,
#             created_at="2026-01-01T00:00:00Z"
#         )

#         # Media for Creator 2: YouTube
#         YoutubeProfileMedia.objects.create(
#             profile=self.profile2,
#             video_id="yt2",
#             view_count=20000,
#             likes_count=2000,
#             comment_count=200,
#             created_at="2026-01-01T00:00:00Z"
#         )

#     def test_get_leaderboard_data_youtube(self):
#         queryset = get_leaderboard_data(platform="YOUTUBE")
#         results = {item.id: item for item in queryset}

#         # Creator 2 has 20000 views, Creator 1 has 10000 views
#         self.assertEqual(results[self.profile2.id].rank, 1)
#         self.assertEqual(results[self.profile1.id].rank, 2)

#         self.assertEqual(results[self.profile2.id].total_subscribers, 3000)
#         self.assertEqual(results[self.profile1.id].total_subscribers, 5000)

#         self.assertEqual(results[self.profile2.id].total_views, 20000)
#         self.assertEqual(results[self.profile1.id].total_views, 10000)

#         # Engagement rate check
#         # Creator 2: (2000 + 200) * 100 / 20000 = 11.0%
#         self.assertAlmostEqual(results[self.profile2.id].engagement_rate, 11.0)
#         # Creator 1: (1000 + 100) * 100 / 10000 = 11.0%
#         self.assertAlmostEqual(results[self.profile1.id].engagement_rate, 11.0)

#     def test_get_leaderboard_data_tiktok(self):
#         queryset = get_leaderboard_data(platform="TIKTOK")
#         results = {item.id: item for item in queryset}

#         # Creator 1 has 5000 views, Creator 2 has 0 views
#         self.assertEqual(results[self.profile1.id].rank, 1)
#         self.assertEqual(results[self.profile2.id].rank, 2)

#         self.assertEqual(results[self.profile1.id].total_subscribers, 1000)
#         self.assertEqual(results[self.profile2.id].total_subscribers, 1500)

#         self.assertEqual(results[self.profile1.id].total_views, 5000)
#         self.assertEqual(results[self.profile2.id].total_views, 0)

#     def test_get_leaderboard_data_combined(self):
#         # Update Creator 2 to have Instagram as their most popular platform (6000 followers)
#         InstagramProfile.objects.filter(profile=self.profile2).update(followers_count=6000)
        
#         # Add Instagram media for Creator 2
#         InstagramProfileMedia.objects.create(
#             profile=self.profile2,
#             video_id="ig2",
#             view_count=30000,
#             likes_count=3000,
#             comment_count=300,
#             created_at="2026-01-01T00:00:00Z"
#         )

#         queryset = get_leaderboard_data(platform=None)
#         results = {item.id: item for item in queryset}

#         # Creator 2's best platform is Instagram (30000 views). Creator 1's best platform is YouTube (10000 views).
#         self.assertEqual(results[self.profile2.id].rank, 1)
#         self.assertEqual(results[self.profile1.id].rank, 2)

#         # Platform checks
#         self.assertEqual(results[self.profile1.id].platform, "YOUTUBE")
#         self.assertEqual(results[self.profile2.id].platform, "INSTAGRAM")

#         # Subscribers count of the best platform
#         self.assertEqual(results[self.profile1.id].total_subscribers, 5000) # YouTube subscribers
#         self.assertEqual(results[self.profile2.id].total_subscribers, 6000) # Instagram followers

#         # Views of the best platform
#         self.assertEqual(results[self.profile1.id].total_views, 10000) # YouTube views
#         self.assertEqual(results[self.profile2.id].total_views, 30000) # Instagram views

#     def test_growth_rate(self):
#         from django.utils import timezone
#         # Create a recent YouTube video for Creator 1 (within last 30 days)
#         YoutubeProfileMedia.objects.create(
#             profile=self.profile1,
#             video_id="yt1_recent",
#             view_count=5000,
#             likes_count=500,
#             comment_count=50,
#             created_at=timezone.now()
#         )

#         queryset = get_leaderboard_data(platform="YOUTUBE")
#         results = {item.id: item for item in queryset}

#         # For Creator 1:
#         # yt_views_recent = 5000 (created_at = timezone.now())
#         # yt_views_older = 10000 (created_at = 2026-01-01)
#         # growth_rate = 5000 * 100.0 / 10000 = 50.0%
#         self.assertAlmostEqual(results[self.profile1.id].growth_rate, 50.0)

#         # For Creator 2:
#         # yt_views_recent = 0
#         # yt_views_older = 20000
#         # growth_rate = 0.0%
#         self.assertAlmostEqual(results[self.profile2.id].growth_rate, 0.0)

