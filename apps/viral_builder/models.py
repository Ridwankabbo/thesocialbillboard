from django.conf import settings
from django.db import models


class PlatformAccount(models.Model):
    PLATFORM_CHOICES = [
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
        ("instagram", "Instagram"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_accounts",
    )
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    external_id = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True)
    profile_url = models.URLField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "platform", "external_id")

    def __str__(self):
        return f"{self.user_id} - {self.platform} - {self.external_id}"


class ViralBuilderRun(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viral_builder_runs",
    )
    channel_account = models.ForeignKey(
        PlatformAccount,
        on_delete=models.CASCADE,
        related_name="viral_builder_runs",
    )
    content_type = models.CharField(max_length=50)
    goal = models.CharField(max_length=50, blank=True)
    toggles = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"ViralBuilderRun<{self.id}> - {self.status}"


class ViralIdea(models.Model):
    run = models.ForeignKey(
        ViralBuilderRun,
        on_delete=models.CASCADE,
        related_name="ideas",
    )
    headline = models.CharField(max_length=255)
    suggested_title = models.CharField(max_length=255)
    hook_structure = models.TextField()
    format_guidance = models.TextField()
    suggested_cta = models.TextField()
    why_fits_channel = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    safety_flags = models.JSONField(default=list, blank=True)
    viral_gap = models.JSONField(default=dict, blank=True)
    is_saved = models.BooleanField(default=False)
    saved_at = models.DateTimeField(null=True, blank=True)
    sent_to_plan_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ViralIdea<{self.id}>"
