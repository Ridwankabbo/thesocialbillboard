from django.db import models
from django.conf import settings
from django.db.models import Sum
# Create your models here.

User = settings.AUTH_USER_MODEL 


""" ================ UNIVERSAL CLASS ================ """

class PlatformChoices(models.TextChoices):
    YOUTUBE = 'YOUTUBE', 'Youtube'
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    TIKTOK = 'TIKTOK', 'Tiktok'
    NOT_SELECTED = ' NOT_SELECTED', "Not_selected"

""" =================================================="""
    
""" 
    ============================= 
        CRETOR PROFILE 
    =============================
"""
class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='creator_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user}"
    
""" 
    ============================= 
        Tiktok PROFILE 
    =============================
"""
class TiktokProfile(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='tiktok_profile')
    tiktok_user_id = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    followers_count = models.BigIntegerField(default=0)
    following_count = models.BigIntegerField(default=0)
    video_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    view_count = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.profile.user} "
""" 
    ============================= 
        Youtube PROFILE 
    =============================
"""
class YoutubeProfile(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='youtube_profile')
    youtube_channel_id = models.CharField(max_length=255, null=True, blank=True)
    channel_title = models.CharField(max_length=255, null=True, blank=True)
    channel_description = models.CharField(max_length=255, null=True, blank=True)
    channel_type = models.CharField(max_length=100, null=True, blank=True)
    subscribers_count = models.IntegerField(default=0)
    view_count = models.BigIntegerField(default=0)
    video_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.profile.user} "
""" 
    ============================= 
        Instagram PROFILE 
    =============================
"""   
class InstagramProfile(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='instagram_profile')
    instagram_user_id = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    followers_count = models.BigIntegerField(default=0)
    following_count = models.BigIntegerField(default=0)
    media_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    view_count = models.BigIntegerField(default=0)
    def __str__(self):
        return f"{self.profile.user} "

""" 
    =================================
        CRETOR PROFILE CREDENTIALS
    =================================
"""
class TiktokCredentials(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='tiktok_credentials')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    access_expires_in = models.IntegerField(null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_expires_in = models.IntegerField(null=True, blank=True)
    scope = models.CharField(max_length=255, null=True, blank=True)
    token_type = models.CharField(max_length=50, blank=True)
    open_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.profile.user} - {self.platform}"
    
class YoutubeCredentials(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='youtube_credentials')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    access_expires_in = models.IntegerField(null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_expires_in = models.IntegerField(null=True, blank=True)
    scope = models.CharField(max_length=255, null=True, blank=True)
    token_type = models.CharField(max_length=50, blank=True)
    open_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.profile.user} - {self.platform}"
    
class InstagramCredentials(models.Model):
    profile = models.OneToOneField(CreatorProfile, on_delete=models.CASCADE, related_name='instagram_credentials')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    access_expires_in = models.IntegerField(null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_expires_in = models.IntegerField(null=True, blank=True)
    scope = models.CharField(max_length=255, null=True, blank=True)
    token_type = models.CharField(max_length=50, blank=True)
    open_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.profile.user} - {self.platform}"
    
    
""" 
    ============================= 
        PROFILE VIDEOS
    =============================
"""
class TiktokProfileMedia(models.Model):
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name='tiktok_profile_media')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    tiktok_profile = models.ForeignKey(TiktokProfile, on_delete=models.CASCADE, related_name='profile_media', null=True, blank=True)
    video_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True)
    likes_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.profile.user}"
    
class YoutubeProfileMedia(models.Model):
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name='youtube_profile_media')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    youtube_profile = models.ForeignKey(YoutubeProfile, on_delete=models.CASCADE, related_name='profile_media', null=True, blank=True)
    video_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True)
    likes_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.profile.user}"

class InstagramProfileMedia(models.Model):
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name='instagram_profile_media')
    platform = models.CharField(max_length=20, choices=PlatformChoices.choices, default=PlatformChoices.NOT_SELECTED)
    instagram_profile = models.ForeignKey(InstagramProfile, on_delete=models.CASCADE, related_name='profile_media', null=True, blank=True)
    video_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True)
    likes_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.profile.user}"
""" 
    ============================= 
        INSTAGRAM WEBHOOK 
    =============================
"""
class InstagramWebhookEvent(models.Model):
    """
    Model to store Instagram webhook events:
    - posts: New post/media published
    - likes: Post received likes/reactions
    - comments: Post received comments
    - views: Media received views (stories, reels)
    - shares: Media was shared
    """
    
    EVENT_TYPE_CHOICES = [
        ('post', 'New Post'),
        ('like', 'Post Like/React'),
        ('comment', 'Post Comment'),
        ('view', 'Media View'),
        ('share', 'Media Share'),
    ]
    
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name='instagram_webhook_events')
    media_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    
    # Event details
    caption = models.TextField(null=True, blank=True)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    comment_text = models.TextField(null=True, blank=True)  # For comment events
    commenter_id = models.CharField(max_length=255, null=True, blank=True)
    reaction_type = models.CharField(max_length=50, null=True, blank=True)  # like, love, haha, wow, sad, angry
    
    # Raw webhook data
    raw_webhook_data = models.JSONField(default=dict, null=True, blank=True)
    
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.profile.user} - {self.event_type} - {self.media_id}"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['profile', '-timestamp']),
            models.Index(fields=['media_id', '-timestamp']),
        ]



