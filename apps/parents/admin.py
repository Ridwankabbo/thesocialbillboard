from django.contrib import admin
from .models import (
    ChildProfile,
    Playlist,
    PlaylistItem,
    PlaylistExplanation,
    YouTubeVideoCache,
    JobRun,
    FollowPlaylist,
    PlaylistChannel,
    Review,
    Feedback,
    ParentPlaylistPrompt,
)


admin.site.register(ChildProfile)
admin.site.register(Playlist)
admin.site.register(PlaylistItem)
admin.site.register(PlaylistExplanation)
admin.site.register(YouTubeVideoCache)
admin.site.register(JobRun)
admin.site.register(FollowPlaylist)
admin.site.register(PlaylistChannel)
admin.site.register(Review)
admin.site.register(Feedback)
admin.site.register(ParentPlaylistPrompt)
