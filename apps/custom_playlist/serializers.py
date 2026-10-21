from rest_framework import serializers
from .models import CustomPlaylist, CustomPlaylistItems



class CustomPlaylistSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomPlaylist
        fields= '__all__'
        
class CustomPlaylistItemSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CustomPlaylistItems
        fields = '__all__'


from .models import SavedCustomPlaylist

class SavedCustomPlaylistSerializer(serializers.ModelSerializer):
    custom_playlist = CustomPlaylistSerializer(read_only=True)
    custom_playlist_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomPlaylist.objects.all(),
        source='custom_playlist',
        write_only=True
    )

    class Meta:
        model = SavedCustomPlaylist
        fields = ['id', 'custom_playlist', 'custom_playlist_id', 'saved_at']