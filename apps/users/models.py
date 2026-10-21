from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import random


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)
    

class User(AbstractBaseUser, PermissionsMixin):

    USER_TYPE_CHOICES = [
        ('parent', 'Parent'),
        ('creator', 'Creator'),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    profile_pic = models.ImageField(upload_to='profile_pics', blank=True, null=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    user_type = models.CharField(max_length=50, choices=USER_TYPE_CHOICES, blank=True, null=True)

    date_joined = models.DateTimeField(default=timezone.now)


    youtube_link = models.BooleanField( default=False)
    instagram_link = models.BooleanField(default=False)
    tiktok_link = models.BooleanField(default=False)


    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_exp = models.DateTimeField(blank=True, null=True)
    otp_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    objects = UserManager()

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP
        self.otp_exp = timezone.now() + timedelta(minutes=10)
        self.otp_verified = False
        self.save()

    def __str__(self):
        return self.email
    



from django.conf import settings

class TikTokOAuthToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tiktok_oauth")

    open_id = models.CharField(max_length=255, blank=True, null=True)
    union_id = models.CharField(max_length=255, blank=True, null=True)

    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    expires_in = models.IntegerField(blank=True, null=True)  # seconds
    refresh_expires_in = models.IntegerField(blank=True, null=True)  # seconds

    scope = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"TikTokOAuthToken<{self.user_id}>"









from django.conf import settings
from django.db import models
from django.utils import timezone


class InstagramOAuthToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instagram_oauth",
    )

    instagram_user_id = models.CharField(max_length=64, blank=True, null=True)  # "user_id" from token exchange
    username = models.CharField(max_length=255, blank=True, null=True)

    access_token = models.TextField()
    token_type = models.CharField(max_length=50, blank=True, null=True)
    scopes = models.TextField(blank=True, null=True)

    expires_in = models.IntegerField(blank=True, null=True)  # seconds (if provided)
    expires_at = models.DateTimeField(blank=True, null=True)

    is_long_lived = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def set_expiry_from_seconds(self, seconds: int | None):
        if seconds:
            self.expires_in = int(seconds)
            self.expires_at = timezone.now() + timezone.timedelta(seconds=int(seconds))






# models.py (apps/users/models.py)

from django.conf import settings
from django.db import models
from django.utils import timezone


class YouTubeOAuthToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="youtube_oauth",
    )

    google_sub = models.CharField(max_length=255, blank=True, null=True)  # optional
    email = models.EmailField(blank=True, null=True)

    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)

    scope = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, blank=True, null=True)

    expires_in = models.IntegerField(blank=True, null=True)  # seconds
    expires_at = models.DateTimeField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    def set_expiry_from_seconds(self, seconds: int | None):
        if seconds:
            self.expires_in = int(seconds)
            self.expires_at = timezone.now() + timezone.timedelta(seconds=int(seconds))

    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at
