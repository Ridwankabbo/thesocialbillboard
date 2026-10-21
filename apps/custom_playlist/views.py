from django.shortcuts import render
from rest_framework.decorators import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CustomPlaylist, CustomPlaylistItems
from .serializers import CustomPlaylistItemSerializer, CustomPlaylistSerializer
from rest_framework.pagination import PageNumberPagination
from apps.parents.models import ChildProfile
# Create your views here.


class PlaylistPagination(PageNumberPagination):
    
    page_size=10
    page_size_query_param = 'page_size',

class CustomPlaylistListAPIView(APIView):
    def get(self ,request):
        
        age_band = request.query_params.get('age_band', None)
        
        paginator = PlaylistPagination()
        if age_band:
            playlists = CustomPlaylist.objects.filter(age_group=age_band)
            paginated_data = paginator.paginate_queryset(playlists, request)
            serializer = CustomPlaylistSerializer(paginated_data, many=True, context={'request':request})
            response = paginator.get_paginated_response(serializer.data).data
            return Response(response, status=status.HTTP_200_OK)
        
        child_profiles = ChildProfile.objects.filter(parent=request.user)
        age_bands = [profile.age_band for profile in child_profiles]
                
        playlists = CustomPlaylist.objects.filter(age_group__in=age_bands)
        paginated_data = paginator.paginate_queryset(playlists, request)
        serializer = CustomPlaylistSerializer(paginated_data, many=True, context={'request':request})
        response = paginator.get_paginated_response(serializer.data).data
        return Response(response, status=status.HTTP_200_OK)
            
    
    
class CustomPlaylistDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, playlist_id):
        
        # playlist = request.data.get('playlist_id')
        print(playlist_id)
        playlist_items = CustomPlaylistItems.objects.filter(playlist=playlist_id)
        print(playlist_items)
        serializer = CustomPlaylistItemSerializer(playlist_items, many=True, context={'request': request})
        return Response({
            "status":True,
            "data":serializer.data,
        }, status=status.HTTP_200_OK)


from .models import SavedCustomPlaylist
from .serializers import SavedCustomPlaylistSerializer

class SavedCustomPlaylistAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        saved_playlists = SavedCustomPlaylist.objects.filter(user=request.user).order_by('-saved_at')
        paginator = PlaylistPagination()
        paginated_data = paginator.paginate_queryset(saved_playlists, request)
        serializer = SavedCustomPlaylistSerializer(paginated_data, many=True, context={'request': request})
        response = paginator.get_paginated_response(serializer.data)
        return Response(response.data, status=status.HTTP_200_OK)
        
    def post(self, request):
        custom_playlist_id = request.data.get('custom_playlist_id')
        if not custom_playlist_id:
            return Response({"error": "custom_playlist_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            custom_playlist = CustomPlaylist.objects.get(id=custom_playlist_id)
        except CustomPlaylist.DoesNotExist:
            return Response({"error": "Custom playlist not found"}, status=status.HTTP_404_NOT_FOUND)
            
        saved, created = SavedCustomPlaylist.objects.get_or_create(
            user=request.user,
            custom_playlist=custom_playlist
        )
        
        if not created:
            return Response({"message": "Playlist already saved"}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": "Playlist saved successfully"}, status=status.HTTP_201_CREATED)