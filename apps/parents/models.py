import uuid
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

# -----------------------------
# Parents Dashboard V1 Models
# -----------------------------

AGE_BAND_CHOICES = [
    ("3-5", "Early Years (3-5)"),
    ("6-8", "Primary (6-8)"),
    ("9-11", "Upper Primary (9-11)"),
    ("12-14", "Early Secondary (12-14)"),
    ("15-16", "Mid Secondary (15-16)"),
    ("17-18", "Older Teens (17-18)"),
]

PLAYLIST_STATUS_CHOICES = [
    ("queued", "Queued"),
    ("generating", "Generating"),
    ("ready", "Ready"),
    ("failed", "Failed"),
    ("canceled", "Canceled"),
]


class ChildProfile(models.Model):
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="child_profiles")
    name = models.CharField(max_length=255, blank=True, default="")
    age_band = models.CharField(max_length=10, choices=AGE_BAND_CHOICES)
    language = models.CharField(max_length=50)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parent_id} - {self.age_band}"


# for get and post playlist
class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_playlists",null=True, blank=True)
    title = models.CharField(max_length=255)
    age_min = models.IntegerField(null=True, blank=True)
    age_max = models.IntegerField(null=True, blank=True)
    tags = models.JSONField(default=list) 
    link = models.URLField(blank=True, null=True)

    # Parents Dashboard V1 fields (kept nullable for backward compatibility)
    child_profile = models.ForeignKey(ChildProfile, on_delete=models.CASCADE, related_name="playlists", null=True, blank=True)
    filters_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=PLAYLIST_STATUS_CHOICES, default="queued")
    is_saved = models.BooleanField(default=False)
    session_length = models.PositiveIntegerField(null=True, blank=True, help_text="Session length in minutes")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    def age_range(self):
        return f"{self.age_min}-{self.age_max}"

    def __str__(self):
        return self.title


class ParentPlaylistPrompt(models.Model):
    prompt_text = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_active_prompt(cls) -> str:
        prompt = (
            cls.objects.filter(is_active=True)
            .order_by("-updated_at", "-created_at")
            .values_list("prompt_text", flat=True)
            .first()
        )
        return (prompt or "").strip()

    def __str__(self):
        return f"ParentPlaylistPrompt {self.id}"

class FollowPlaylist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followed_playlists", null=True, blank=True)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="followers",null=True, blank=True)
    followed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

class PlaylistChannel(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='channels')

    # NOTE:
    # This field stores YOUTUBE VIDEO ID (not channel id).
    # Kept name for backward compatibility.
    
    channel_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    link = models.URLField()
    tags = models.JSONField(default=list)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('playlist', 'channel_id')

    def __str__(self):
        return f"{self.title} in {self.playlist.title}"


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="items")
    youtube_video_id = models.CharField(max_length=50)
    position = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    channel_id = models.CharField(max_length=100)
    thumbnail_url = models.URLField()
    video_url = models.URLField()

    class Meta:
        unique_together = ("playlist", "position")
        ordering = ["position"]

    def __str__(self):
        return f"{self.position}. {self.title}"


class PlaylistExplanation(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="explanations")
    why_suitable_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Explanation for playlist {self.playlist_id}"


class YouTubeVideoCache(models.Model):
    video_id = models.CharField(max_length=50, unique=True)
    channel_id = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    publish_date = models.DateTimeField(null=True, blank=True)
    transcript_text = models.TextField(null=True, blank=True)
    analysis_json = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    transcript_coverage_score = models.FloatField(
        default=0
    )

    transcript_word_count = models.IntegerField(
        default=0
    )

    transcript_confidence = models.FloatField(
        default=0
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.title
    

class TranscriptAnalysis(models.Model):

    video = models.ForeignKey(
        YouTubeVideoCache,
        on_delete=models.CASCADE,
        related_name="analyses"
    )

    model_name = models.CharField(
        max_length=100
    )

    prompt_version = models.CharField(
        max_length=20
    )

    age_rating = models.CharField(
        max_length=20
    )

    safety_score = models.FloatField()

    creator_score = models.FloatField()

    confidence_score = models.FloatField()

    analysis_json = models.JSONField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )


class JobRun(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    ]

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_runs")
    task_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.task_name} ({self.status})"

# post review model 
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_reviews",null=True, blank=True)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True
    )
    channel = models.ForeignKey(
        PlaylistChannel, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True
    )
    kid_age = models.IntegerField(null=True, blank=True)
    # fields from gpt_ai
    age_appropriateness = models.FloatField(null=True, blank=True)
    educational_value = models.FloatField(null=True, blank=True)
    emotional_impact = models.FloatField(null=True, blank=True)
    cultural_sensitivity = models.FloatField(null=True, blank=True)
    grade_point_by_user = models.FloatField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        target = self.channel.title if self.channel else self.playlist.title if self.playlist else "N/A"
        return f"Review {self.id} - {target}"


# post feedback
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_feedbacks",null=True, blank=True)
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="feedbacks", null=True, blank=True
    )
    channel = models.ForeignKey(
        PlaylistChannel, on_delete=models.CASCADE, related_name="feedbacks", null=True, blank=True
    )
    suggested_age = models.IntegerField()
    tags = models.JSONField(default=list)  # ["Too Fast","Calm",...]
    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.channel.title if self.channel else self.playlist.title if self.playlist else "N/A"
        return f"Feedback {self.id} - {target}"

