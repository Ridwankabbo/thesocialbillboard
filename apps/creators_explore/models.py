from django.db import models
from django.utils import timezone

class Creator(models.Model):
    PLATFORM_CHOICES = [("YouTube", "YouTube"), ("TikTok", "TikTok"), ("Instagram", "Instagram")]

    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    followers = models.BigIntegerField(default=0)
    image = models.URLField(max_length=1024, blank=True)
    genre = models.CharField(max_length=100, default="General")
    country = models.CharField(max_length=100, default="Unknown")
    age_group = models.CharField(max_length=50, default="18-35")
    channel_url = models.URLField(max_length=1024)
    fetched_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.platform})"
