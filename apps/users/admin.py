from django.contrib import admin
from .models import User, TikTokOAuthToken, InstagramOAuthToken
from unfold.admin import ModelAdmin
# Register your models here.

# admin.site.register(User)
# admin.site.register(TikTokOAuthToken)
# admin.site.register(InstagramOAuthToken)

@admin.register(User)
class CustomAdminClass(ModelAdmin):
    list_display = ('id', 'email', 'name', 'user_type', 'is_staff', 'is_active')
    
    search_fields = ('email', 'name')

    list_filter = ('user_type', 'is_staff', 'is_active')
    
    ordering = ('id',)

@admin.register(TikTokOAuthToken)
class TikTokOAuthTokenAdminClass(ModelAdmin):
    pass

@admin.register(InstagramOAuthToken)
class InstagramOAuthTokenAdminClass(ModelAdmin):
    pass




# admin.py

from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import User, TikTokOAuthToken, InstagramOAuthToken, YouTubeOAuthToken

@admin.register(YouTubeOAuthToken)
class YouTubeOAuthTokenAdminClass(ModelAdmin):
    pass
