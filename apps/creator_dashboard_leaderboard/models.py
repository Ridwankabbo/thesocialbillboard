from django.db import models
from apps.creator_dashboard.models import PlatformChoices
# Create your models here.

class LeaderboardEntry(models.Model):
    profile = models.ForeignKey('creator_dashboard.CreatorProfile', on_delete=models.CASCADE, related_name='leaderboard_entries')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    video_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    likes_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    engagement_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.profile.user.username} - {self.platform} - {self.title}"
