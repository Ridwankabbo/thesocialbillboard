from django.db import models
import logging

logger = logging.getLogger(__name__)

class Creator(models.Model):
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
    ]

    name = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    profile_image = models.URLField(blank=True, null=True)
    subscribers = models.CharField(max_length=50)  # "12.5M"
    engagement = models.CharField(max_length=10)   # "5%"
    growth = models.CharField(max_length=10)       # "+11%"
    ai_score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("name", "platform")

    def parse_subscribers(self):
        """
        Convert 12.5M -> 12500000, 12K -> 12000, or return numeric value.
        """
        try:
            val = str(self.subscribers).upper().replace(" ", "").strip()

            if "M" in val:
                return int(float(val.replace("M", "")) * 1_000_000)
            elif "K" in val:
                return int(float(val.replace("K", "")) * 1_000)
            else:
                return int(float(val))  # Handles raw numbers like 12000
        except Exception as e:
            logger.warning(f"[parse_subscribers] Invalid value: '{self.subscribers}' — {e}")
            return 0

    def parse_percentage(self, value):
        """
        Convert "5%" or "+11%" to float value like 5.0 or 11.0.
        """
        try:
            val = str(value).replace("%", "").replace("+", "").replace("-", "").strip()
            return float(val)
        except Exception as e:
            logger.warning(f"[parse_percentage] Invalid value: '{value}' — {e}")
            return 0.0

    def score(self):
        """
        Calculate a composite score using weights for subscribers, engagement, and growth.
        """
        try:
            subs = self.parse_subscribers()
            engagement = self.parse_percentage(self.engagement)
            growth = self.parse_percentage(self.growth)

            # You can tweak these weights
            return round((subs / 1_000_000) * 0.6 + engagement * 0.3 + growth * 0.1, 4)
        except Exception as e:
            logger.error(f"[score] Failed to calculate score: {e}")
            return 0.0
