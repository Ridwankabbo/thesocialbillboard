from django.contrib import admin
from django import forms
from unfold.admin import ModelAdmin, TabularInline
from .models import CustomPlaylist, CustomPlaylistItems
# Register your models here.

class CustomPlaylistItemsInline(TabularInline):
    model = CustomPlaylistItems
    extra = 0
    fields = ['id', 'playlist', 'item_url',]
    readonly_fields = ['uploaded_at']
    
class CustomPlaylistAdminForm(forms.ModelForm):
    # ১. মডেলে না থাকলে এখানে ফর্মের ভেতর ফিল্ডটি ডিফাইন করুন (এটি অটোমেটিক required থাকে)
    playlist_length = forms.IntegerField(label="Playlist Length (Minutes)")

    class Meta:
        model = CustomPlaylist
        fields = '__all__'
        
@admin.register(CustomPlaylist)
class CustomPlaylistAdmin(ModelAdmin):
    # form = CustomPlaylistAdminForm
    inlines = [CustomPlaylistItemsInline]
    list_display = ['id', 'name', 'playlist_thumbnails', 'age_group', 'language', 'playlist_length', 'tone', 'time_of_the_day', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
# admin.site.register(CustomPlaylist, CustomPlaylistAdmin)
