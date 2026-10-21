from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class CompetitorData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="competitor_data")
    fetched_date = models.DateTimeField(default=timezone.now)
    data = models.JSONField(default=dict)  # will store competitors + input channel info

    def __str__(self):
        return f"Competitors for {self.user.email}"
