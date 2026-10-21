from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.parents.models import JobRun

from apps.creator_dashboard.models import CreatorProfile, YoutubeProfile

from .models import PlatformAccount, ViralBuilderRun, ViralIdea
from .services import humanize_generation_error


User = get_user_model()


class ViralBuilderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="pass1234",
            name="Creator",
            youtube_link="https://www.youtube.com/channel/UC_TEST_CHANNEL",
        )
        self.other_user = User.objects.create_user(email="other@example.com", password="pass1234", name="Other")
        self.channel = PlatformAccount.objects.create(
            user=self.user,
            platform="youtube",
            external_id="UC_TEST_CHANNEL",
            display_name="Test Channel",
        )

    @mock.patch("apps.viral_builder.views.viral_builder_generate.delay")
    def test_run_accepts_creator_profile_id_when_platform_account_missing(self, mock_delay):
        self.channel.delete()
        profile = CreatorProfile.objects.create(user=self.user)
        YoutubeProfile.objects.create(
            profile=profile,
            youtube_channel_id="UC_TEST_CHANNEL",
            channel_title="Test Channel",
        )

        self.client.force_authenticate(self.user)
        payload = {
            "channel_account_id": profile.id,
            "content_type": "long_form",
            "goal": "growth",
            "toggles": {"strict_alignment": True, "brand_safe_only": False},
        }

        resp = self.client.post("/api/v1/creator/viral-builder/run/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        run_id = resp.data["data"]["run_id"]
        run = ViralBuilderRun.objects.get(id=run_id)
        self.assertEqual(run.channel_account.platform, "youtube")
        self.assertEqual(run.channel_account.external_id, "UC_TEST_CHANNEL")

    @mock.patch("apps.viral_builder.views.viral_builder_generate.delay")
    def test_run_creation_queues_job(self, mock_delay):
        self.client.force_authenticate(self.user)
        payload = {
            "channel_account_id": self.channel.id,
            "content_type": "long_form",
            "goal": "growth",
            "toggles": {"strict_alignment": True, "brand_safe_only": True},
        }

        resp = self.client.post("/api/v1/creator/viral-builder/run/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue("run_id" in resp.data["data"])
        self.assertTrue("job_id" in resp.data["data"])

        run_id = resp.data["data"]["run_id"]
        job_id = resp.data["data"]["job_id"]

        self.assertTrue(ViralBuilderRun.objects.filter(id=run_id, user=self.user, status="queued").exists())
        self.assertTrue(JobRun.objects.filter(id=job_id, user=self.user, status="queued").exists())
        mock_delay.assert_called_once()

    def test_permissions_run_detail(self):
        run = ViralBuilderRun.objects.create(
            user=self.user,
            channel_account=self.channel,
            content_type="shorts",
            goal="engagement",
            toggles={"strict_alignment": True},
        )

        self.client.force_authenticate(self.other_user)
        resp = self.client.get(f"/api/v1/creator/viral-builder/run/{run.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_idea_output_shape(self):
        self.client.force_authenticate(self.user)
        run = ViralBuilderRun.objects.create(
            user=self.user,
            channel_account=self.channel,
            content_type="shorts",
            goal="engagement",
            toggles={"strict_alignment": True},
            status="done",
        )

        ViralIdea.objects.create(
            run=run,
            headline="Headline",
            suggested_title="Suggested",
            hook_structure="Hook",
            format_guidance="Format",
            suggested_cta="CTA",
            why_fits_channel="Reason",
            tags=["tag1"],
            safety_flags=[],
            viral_gap={"source_platform": "tiktok"},
        )

        resp = self.client.get(f"/api/v1/creator/viral-builder/run/{run.id}/")
        self.assertEqual(resp.status_code, 200)
        ideas = resp.data["data"].get("ideas")
        self.assertTrue(isinstance(ideas, list))
        self.assertTrue(len(ideas) == 1)
        idea = ideas[0]
        for key in [
            "headline",
            "suggested_title",
            "hook_structure",
            "format_guidance",
            "suggested_cta",
            "why_fits_channel",
            "tags",
            "safety_flags",
            "viral_gap",
        ]:
            self.assertIn(key, idea)

    def test_save_idea_permissions(self):
        run = ViralBuilderRun.objects.create(
            user=self.user,
            channel_account=self.channel,
            content_type="shorts",
            goal="engagement",
            toggles={"strict_alignment": True},
            status="done",
        )
        idea = ViralIdea.objects.create(
            run=run,
            headline="Headline",
            suggested_title="Suggested",
            hook_structure="Hook",
            format_guidance="Format",
            suggested_cta="CTA",
            why_fits_channel="Reason",
            tags=[],
            safety_flags=[],
            viral_gap={},
        )

        self.client.force_authenticate(self.other_user)
        resp = self.client.post(f"/api/v1/creator/viral-builder/ideas/{idea.id}/save/")
        self.assertEqual(resp.status_code, 404)

    def test_humanize_generation_error_for_quota(self):
        err = Exception("Error code: 429 - {'error': {'code': 'insufficient_quota'}}")
        message = humanize_generation_error(err)
        self.assertIn("quota exceeded", message.lower())

    def test_humanize_generation_error_for_youtube_timeout(self):
        err = Exception("HTTPSConnectionPool(host='www.googleapis.com'): ConnectTimeoutError timed out")
        message = humanize_generation_error(err)
        self.assertIn("youtube api timeout", message.lower())
