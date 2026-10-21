from django.contrib import admin
from .models import (
    CreatorProfile,
    TiktokCredentials,
    YoutubeCredentials,
    InstagramCredentials,
    TiktokProfileMedia,
    YoutubeProfileMedia,
    InstagramProfileMedia,
    InstagramWebhookEvent
)
from unfold.admin import ModelAdmin, TabularInline

# Register your models here.

# @admin.register(CreatorProfile)
# class CreatorProfileAdmin(ModelAdmin):
#     list_display = ['user', 'created_at', 'updated_at']
#     search_fields = ['user__username']


class TiktokCredentialsInline(TabularInline):
    model = TiktokCredentials
    extra = 0
    fields = ['access_token', 'created_at']
    readonly_fields = ['created_at']
    
class YoutubeCredentialsInline(TabularInline):
    model = YoutubeCredentials
    extra = 0
    fields = ['access_token', 'created_at']
    readonly_fields = ['created_at']

class InstagramCredentialsInline(TabularInline):
    model = InstagramCredentials
    extra = 0
    fields = ['access_token', 'created_at']
    readonly_fields = ['created_at']

class TiktokProfileMediaInline(TabularInline):
    model = TiktokProfileMedia
    extra = 0
    fields = ['tiktok_profile', 'video_id', 'title', 'likes_count', 'view_count', 'comment_count', 'created_at']
    readonly_fields = ['created_at']

class YoutubeProfileMediaInline(TabularInline):
    model = YoutubeProfileMedia
    extra = 0
    fields = ['youtube_profile', 'video_id', 'title', 'likes_count', 'view_count', 'comment_count', 'created_at']
    readonly_fields = ['created_at']

class InstagramProfileMediaInline(TabularInline):
    model = InstagramProfileMedia
    extra = 0
    fields = ['title', 'likes_count', 'view_count', 'comment_count', 'created_at']
    readonly_fields = ['created_at']

class CreatorProfileAdmin(ModelAdmin):
    inlines = [TiktokCredentialsInline, YoutubeCredentialsInline, InstagramCredentialsInline, TiktokProfileMediaInline, YoutubeProfileMediaInline, InstagramProfileMediaInline]
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username']

class CreatorProfileAdmin(ModelAdmin):
    inlines = [
        TiktokCredentialsInline,
        YoutubeCredentialsInline,
        InstagramCredentialsInline, 
        TiktokProfileMediaInline,
        YoutubeProfileMediaInline,
        InstagramProfileMediaInline
]
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__username']

admin.site.register(CreatorProfile, CreatorProfileAdmin)
    
# @admin.register(CreatorCredentials)
# class CreatorCredentialsAdmin(ModelAdmin):
#     list_display = ['profile', 'platform', 'created_at']
#     list_filter = ['platform', 'created_at']
#     search_fields = ['profile__user__username']


# @admin.register(ProfileVideos)
# class ProfileVideosAdmin(ModelAdmin):
#     list_display = ['profile', 'platform', 'video_id', 'likes_count', 'comment_count', 'view_count']
#     list_filter = ['platform', 'created_at']
#     search_fields = ['profile__user__username', 'video_id']


@admin.register(InstagramWebhookEvent)
class InstagramWebhookEventAdmin(ModelAdmin):
    list_display = ['profile', 'event_type', 'media_id', 'like_count', 'comment_count', 'timestamp']
    list_filter = ['event_type', 'timestamp','timestamp']
    search_fields = ['profile__user__username', 'media_id']
    readonly_fields = ['raw_webhook_data', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Profile Info', {
            'fields': ('profile', 'media_id', 'event_type', 'timestamp')
        }),
        ('Event Details', {
            'fields': ('caption', 'like_count', 'comment_count', 'view_count', 'reaction_type')
        }),
        ('Comments', {
            'fields': ('comment_text', 'commenter_id'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('raw_webhook_data', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
