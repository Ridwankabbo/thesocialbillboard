from urllib3 import request
from rest_framework import status
from .models import *
from .serializers import *
from .utils import *
from apps.users.views import BaseAPIView
from datetime import datetime
from django.utils import timezone
from django.db.models import Count
from rest_framework import permissions
from apps.payment_stripe.views import HasPackage1Subscription
from apps.payment_stripe.models import Subscription
from .tasks import generate_parent_playlist, regenerate_parent_playlist
# -------------------------------
# Channel Overview
# -------------------------------


# get youtube data 
class ChannelOverviewAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, channel_id):
        data = get_channel_overview(channel_id)
        if not data:
            return self.error_response(
                message="Invalid channel ID or not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        return self.success_response(
            message="Channel overview fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )

# -------------------------------
# Add To Playlist
# -------------------------------

class AddChannelToPlaylistsAPIView(BaseAPIView):


    def post(self, request, video_id):
        playlist_ids = request.data.get("playlist_ids", [])

        if not playlist_ids:
            return self.error_response("No playlists selected")

        #  Get all info from overview
        overview = get_video_overview(video_id)
        if not overview:
            return self.error_response("Failed to fetch video overview")

        title = overview.get("title", "")

        # correct video link
        link = f"https://www.youtube.com/watch?v={video_id}"

        tags = overview.get("tags", [])

        added_to = []
        skipped = []

        for playlist_id in playlist_ids:
            try:
                playlist = Playlist.objects.get(id=playlist_id)

                obj, created = PlaylistChannel.objects.get_or_create(
                    playlist=playlist,

                    # NOTE:
                    # channel_id field stores YOUTUBE VIDEO ID
                    channel_id=video_id,

                    defaults={
                        "title": title,
                        "link": link,
                        "tags": tags
                    }
                )

                if created:
                    added_to.append(playlist.title)
                else:
                    skipped.append(playlist.title)

            except Playlist.DoesNotExist:
                continue

        if not added_to:
            return self.error_response("No videos added (might be duplicates)")

        return self.success_response(
            message="Video added to selected playlists",
            data={
                "added_to": added_to,
                "skipped": skipped
            }
        )




class PlaylistChannelsAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, playlist_id):
        try:
            playlist=Playlist.objects.get(id=playlist_id)

        except Playlist.DoesNotExist:
            return self.error_response(
                message="Playlist not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )
        # grabing channel in playlist
        channels = PlaylistChannel.objects.filter(playlist=playlist)
        serializer = PlaylistChannelSerializer(channels, many=True)

        return self.success_response(
            message="Channels for this playlist",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

# -------------------------------
# Playlist CRUD                  
# -------------------------------

class PlaylistAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    # Get playlist(s)
    def get(self, request, pk=None, *args, **kwargs):
        user = request.user

        if pk:
            try:
                playlist = Playlist.objects.get(user=user, pk=pk)
                serializer = PlaylistSerializer(playlist)
                return self.success_response(
                    message="Playlist fetched successfully",
                    data=serializer.data,
                    status_code=status.HTTP_200_OK
                )
            except Playlist.DoesNotExist:
                return self.error_response(
                    message="Playlist not found",
                    data={},
                    status_code=status.HTTP_200_OK
                )
        else:
            # Only show playlists of logged-in user
            playlists = Playlist.objects.filter(user=user)
            if not playlists.exists():
                return self.error_response(
                    message="No playlists found for this user",
                    data=[],
                    status_code=status.HTTP_200_OK
                )
            serializer = PlaylistSerializer(playlists, many=True)
            return self.success_response(
                message="Playlist list fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

    # Create new playlist
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = PlaylistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user)
            return self.success_response(
                message="Playlist created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        return self.error_response(
            message="Validation error",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Update playlist (partial)
    def put(self, request, pk=None, *args, **kwargs):
        user = request.user
        if not pk:
            return self.error_response(
                message="Playlist ID is required for update",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            playlist = Playlist.objects.get(user=user, pk=pk)
        except Playlist.DoesNotExist:
            return self.error_response(
                message="Playlist not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = PlaylistSerializer(playlist, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success_response(
                message="Playlist updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return self.error_response(
            message="Validation error",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Delete playlist
    def delete(self, request, pk=None, *args, **kwargs):
        user = request.user
        if not pk:
            return self.error_response(
                message="Playlist ID is required for deletion",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            playlist = Playlist.objects.get(user=user, pk=pk)
            playlist.delete()
            return self.success_response(
                message="Playlist deleted successfully",
                data={},
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Playlist.DoesNotExist:
            return self.error_response(
                message="Playlist not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )



# -------------------------------
# Review with AI rating
# -------------------------------
class ReviewAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        reviews = Review.objects.all().order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return self.success_response(message="Reviews fetched successfully", data=serializer.data, status_code=status.HTTP_200_OK)

    def post(self, request):
        kid_age = request.data.get('kid_age')
        comment = request.data.get('comment')
        playlist_id = request.data.get('playlist')
        channel_id = request.data.get('channel')

        if kid_age is None:
            return self.error_response(message="kid_age is required", status_code=status.HTTP_400_BAD_REQUEST)

        # GPT Rating
        gpt_data = get_ai_rating(kid_age, comment)

        review = Review.objects.create(
            user=request.user,
            kid_age=kid_age,
            comment=comment,
            playlist=Playlist.objects.filter(id=playlist_id).first() if playlist_id else None,
            channel=PlaylistChannel.objects.filter(id=channel_id).first() if channel_id else None,
            age_appropriateness=gpt_data.get('age_appropriateness', 0),
            educational_value=gpt_data.get('educational_value', 0),
            emotional_impact=gpt_data.get('emotional_impact', 0),
            cultural_sensitivity=gpt_data.get('cultural_sensitivity', 0),
        )
        serializer = ReviewSerializer(review)
        return self.success_response(message="Review created successfully", data=serializer.data, status_code=status.HTTP_201_CREATED)


# -------------------------------
# Feedback
# -------------------------------
class FeedbackAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        feedbacks = Feedback.objects.all().order_by('-created_at')
        serializer = FeedbackSerializer(feedbacks, many=True)
        return self.success_response(message="Feedback list fetched successfully", data=serializer.data, status_code=status.HTTP_200_OK)

    def post(self, request):
        
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return self.success_response(message="Feedback created successfully", data=serializer.data, status_code=status.HTTP_201_CREATED)
        return self.error_response(message="Validation error", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


# top trending videos (Channel specific)
class TrendingTopVideosAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, channel_id):
        try:
            count_param = request.query_params.get("count", "10")
            if not count_param.isdigit():
                return self.error_response(
                    message="Invalid count parameter. It must be an integer.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            count = int(count_param)
            if count <= 0 or count > 50:
                return self.error_response(
                    message="Count must be between 1 and 50.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            videos = get_channel_top_videos(channel_id, count)

            # Add proper age rating
            for video in videos:
                title = video.get("title", "")
                description = ""  # You could fetch via YouTube API if needed

                age_result = get_age_range_for_channel(title, description)
                raw_range = age_result.get("recommended_age_range", "Unknown")
                age_display = convert_age_range_to_text(raw_range)

                video["age_rating"] = age_display

            return self.success_response(
                message="Channel top videos fetched successfully",
                data=videos,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return self.error_response(
                message="Failed to fetch channel top videos",
                data={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



# its show a demo playlist
class CuratedPlaylistsAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            age = request.query_params.get("age")  # Example: "6" (not "5–8")
            tag = request.query_params.get("tag")  # Optional: "STEM", "Calm"

            playlists = Playlist.objects.all()

            if age:
                try:
                    age = int(age)
                    playlists = playlists.filter(age_min__lte=age, age_max__gte=age)
                except ValueError:
                    return self.error_response(
                        message="Invalid age. Must be an integer.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            if tag:
                playlists = playlists.filter(tags__icontains=tag)

            serializer = PlaylistSerializer(playlists, many=True, context={'request': request})
            return self.success_response(
                message="Playlists fetched successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.error_response(
                message="Failed to fetch playlists",
                data={"error": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# follow unfollow playlists

from .models import FollowPlaylist
class FollowPlaylistApiView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return self.error_response(
                message="Authentication credentials were not provided.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        followed_playlists = FollowPlaylist.objects.filter(user=user).select_related('playlist')
        playlists = [f.playlist for f in followed_playlists]
        serializer = PlaylistSerializer(playlists, many=True)
        return self.success_response(
            message="Followed playlists fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def post(self, request):
        if not request.user or not request.user.is_authenticated:
            return self.error_response(
                message="Authentication credentials were not provided.",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        user = request.user
        playlist_id = request.data.get("playlist_id")

        if not playlist_id:
            return self.error_response(
                message="playlist_id is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            playlist = Playlist.objects.get(id=playlist_id)
        except Playlist.DoesNotExist:
            return self.error_response(
                message="Playlist not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Check if already followed
        try:
            follow = FollowPlaylist.objects.get(user=user, playlist=playlist)
            follow.delete()
            return self.success_response(
                message="Playlist unfollowed successfully",
                data={"followed": False},
                status_code=status.HTTP_200_OK
            )
        except FollowPlaylist.DoesNotExist:
            try:
                FollowPlaylist.objects.create(user=user, playlist=playlist)
                return self.success_response(
                    message="Playlist followed successfully",
                    data={"followed": True},
                    status_code=status.HTTP_200_OK
                )
            except Exception as e:
                return self.error_response(
                    message="Something went wrong while following playlist.",
                    data={"error": str(e)},
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        

# -------------------------------
# Parents Dashboard V1 APIs
# -------------------------------

class ChildProfileAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profiles = ChildProfile.objects.filter(parent=request.user).order_by("-created_at")
        serializer = ChildProfileSerializer(profiles, many=True)
        return self.success_response(
            message="Child profiles fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = ChildProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(parent=request.user)
            return self.success_response(
                message="Child profile created successfully",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        return self.error_response(
            message="Validation error",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def put(self, request, *args, **kwargs):
        profile_id = request.data.get("id")
        if not profile_id:
            return self.error_response(
                message="Child profile ID is required for update",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = ChildProfile.objects.get(id=profile_id, parent=request.user)
        except ChildProfile.DoesNotExist:
            return self.error_response(
                message="Child profile not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ChildProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success_response(
                message="Child profile updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return self.error_response(
            message="Validation error",
            data=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def delete(self, request, *args, **kwargs):
        profile_id = request.data.get("id")
        if not profile_id:
            return self.error_response(
                message="Child profile ID is required for deletion",
                data={},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = ChildProfile.objects.get(id=profile_id, parent=request.user)
            profile.delete()
            return self.success_response(
                message="Child profile deleted successfully",
                data={},
                status_code=status.HTTP_204_NO_CONTENT
            )
        except ChildProfile.DoesNotExist:
            return self.error_response(
                message="Child profile not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )

from .permissions import PlaylistGenerationPermission, has_valid_paid_subscription

class ChildAgeBandListAPIView(BaseAPIView):
    
    def get(self, request):
        child_profiles = ChildProfile.objects.filter(parent=request.user)
        age_bands = [profile.age_band for profile in child_profiles]
        return self.success_response(
            message="Child age bands fetched successfully",
            data={"age_bands": age_bands},
            status_code=status.HTTP_200_OK
        )

class ParentPlaylistGetAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        playlists = Playlist.objects.all().order_by("-created_at")
        serializer = ParentPlaylistSerializer(playlists, many=True)
        return self.success_response(
            message="Playlists fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class ParentPlaylistCreateAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated, PlaylistGenerationPermission]

    def get(self, request):
        playlists = Playlist.objects.filter(user=request.user, status="ready", is_saved=True).order_by("-created_at")
        serializer = ParentPlaylistSerializer(playlists, many=True)
        return self.success_response(
            message="Playlists fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = ParentPlaylistCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Validation error", data=serializer.errors)

        child_profile_id = serializer.validated_data["child_profile_id"]
        filters = serializer.validated_data.get("filters") or {}
        session_length = serializer.validated_data["session_length"]

        child_profile = ChildProfile.objects.filter(id=child_profile_id, parent=request.user).first()
        if not child_profile:
            return self.error_response(
                message="Child profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        filters.setdefault("age_band", child_profile.age_band)
        filters.setdefault("language", child_profile.language)
        filters["session_length"] = session_length
        admin_prompt = ParentPlaylistPrompt.get_active_prompt()
        if admin_prompt:
            filters["admin_prompt"] = admin_prompt

        playlist = Playlist.objects.create(
            user=request.user,
            child_profile=child_profile,
            filters_json=filters,
            status="queued",
            is_saved=False,
            session_length=session_length,
            title=f"Parents Playlist {datetime.now().strftime('%Y-%m-%d')}",
        )

        job = JobRun.objects.create(
            user=request.user,
            task_name="generate_parent_playlist",
            status="queued",
            meta={"playlist_id": playlist.id},
        )

        generate_parent_playlist.delay(playlist.id, str(job.id))

        return self.success_response(
            message="Playlist generation queued",
            data={"playlist_id": playlist.id, "job_id": str(job.id)},
            status_code=status.HTTP_201_CREATED
        )
        
from .services import get_transcript
class VideoTranscriptAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, video_id):
        transcript = get_transcript(video_id)
        return self.success_response(
            message = "Transcript fetched successfully",
            data = {"video_id":video_id , "transcript":transcript}
        )
        


from .tasks import process_playlist_task


class StartPlaylistAnalysisAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, playlist_id):
        # playlist_id = request.data.get("playlist_id")
        playlist = Playlist.objects.filter(id=playlist_id, user=request.user).first()
        if not playlist:
            return self.error_response(
                message="Playlist not found",
                status_code = status.HTTP_404_NOT_FOUND
            )

        job = JobRun.objects.create(
            user=request.user,
            task_name="playlist_analysis",
            status="queued",
            meta={"playlist_id": playlist.id}
        )

        process_playlist_task.delay(str(job.id))

        return Response({
            "success": True,
            "job_id": str(job.id),
            "status": "queued"
        })


class ParentPlaylistRegenerateAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, playlist_id):
        playlist = Playlist.objects.filter(id=playlist_id, user=request.user).first()
        if not playlist:
            return self.error_response("Playlist not found", status_code=status.HTTP_404_NOT_FOUND)

        job = JobRun.objects.create(
            user=request.user,
            task_name="regenerate_parent_playlist",
            status="queued",
            meta={"playlist_id": playlist.id},
        )
        playlist.status = "queued"
        playlist.save(update_fields=["status"])

        regenerate_parent_playlist.delay(playlist.id, str(job.id))

        return self.success_response(
            message="Playlist regeneration queued",
            data={"playlist_id": playlist.id, "job_id": str(job.id)},
            status_code=status.HTTP_202_ACCEPTED
        )


class ParentPlaylistSaveAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, playlist_id):
        playlist = Playlist.objects.filter(
            id=playlist_id,
            user=request.user
        ).first()

        if not playlist:
            return self.error_response(
                "Playlist not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if playlist.is_saved:
            return self.success_response(
                message="Playlist already saved",
                data={
                    "playlist_id": playlist.id,
                    "is_saved": True
                },
                status_code=status.HTTP_200_OK
            )

        # # Paid users can save unlimited playlists
        # if not has_valid_paid_subscription(request.user):
        #     already_saved = Playlist.objects.filter(
        #         user=request.user,
        #         is_saved=True
        #     ).exclude(id=playlist.id).exists()

        #     if already_saved:
        #         return self.error_response(
        #             message="Free plan allows only one saved playlist. Please upgrade your subscription.",
        #             status_code=status.HTTP_400_BAD_REQUEST
        #         )

        playlist.is_saved = True
        playlist.save(update_fields=["is_saved"])

        return self.success_response(
            message="Playlist saved",
            data={
                "playlist_id": playlist.id,
                "is_saved": True
            },
            status_code=status.HTTP_200_OK
        )

from apps.custom_playlist.models import CustomPlaylist
from apps.custom_playlist.serializers import CustomPlaylistSerializer
class AllPlaylistbychild(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        child_profile_id = request.query_params.get("child_profile_id")
        if not child_profile_id:
            return self.error_response("child_profile_id query parameter is required")

        playlists = Playlist.objects.filter(child_profile_id=child_profile_id, user=request.user, is_saved=True).order_by("-created_at")
        child_profile = ChildProfile.objects.get(id=child_profile_id)
        custom_playlist = CustomPlaylist.objects.filter(age_group=child_profile.age_band)
        serializer = ParentPlaylistSerializer(playlists, many=True)
        custom_playlist_serializer = CustomPlaylistSerializer(custom_playlist, many=True)
        return self.success_response(
            message="Playlists for child profile fetched successfully",
            data={
                "created_by_you:":serializer.data,
                "created_by_platfrom": custom_playlist_serializer.data
                },
            status_code=status.HTTP_200_OK
        )
        
class ParentPlaylistGetDetailAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request, playlist_id):
        playlist = Playlist.objects.filter(id=playlist_id).first()
        if not playlist:
            return self.error_response("Playlist not found", status_code=status.HTTP_404_NOT_FOUND)

        playlist.last_viewed_at = timezone.now()
        playlist.save(update_fields=["last_viewed_at"])

        items = PlaylistItem.objects.filter(playlist=playlist).order_by("position")
        explanation = PlaylistExplanation.objects.filter(playlist=playlist).order_by("-created_at").first()
        analysis_map = {
            row["video_id"]: row["analysis_json"]
            for row in YouTubeVideoCache.objects.filter(video_id__in=[i.youtube_video_id for i in items]).values("video_id", "analysis_json")
        }

        item_serializer = PlaylistItemSerializer(items, many=True, context={"analysis_map": analysis_map})
        playlist_serializer = ParentPlaylistSerializer(playlist)

        video_ids = [i.youtube_video_id for i in items]
        embed_params = {
            "modestbranding": 1,
            "rel": 0,
            "controls": 1,
            "playsinline": 1,
            "autoplay": 0,
            "loop": 1,
            "playlist": ",".join(video_ids),
            "enablejsapi": 1,
            "iv_load_policy": 3,
        }

        return self.success_response(
            message="Playlist detail fetched successfully",
            data={
                "playlist": playlist_serializer.data,
                "items": item_serializer.data,
                "explanation": explanation.why_suitable_text if explanation else "",
                "status": playlist.status,
                "player": {
                    "video_ids": video_ids,
                    "embed_params": embed_params,
                },
            },
            status_code=status.HTTP_200_OK
        )


class ParentPlaylistDetailAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, playlist_id):
        playlist = Playlist.objects.filter(id=playlist_id, user=request.user).first()
        if not playlist:
            return self.error_response("Playlist not found", status_code=status.HTTP_404_NOT_FOUND)

        playlist.last_viewed_at = timezone.now()
        playlist.save(update_fields=["last_viewed_at"])

        items = PlaylistItem.objects.filter(playlist=playlist).order_by("position")
        explanation = PlaylistExplanation.objects.filter(playlist=playlist).order_by("-created_at").first()
        analysis_map = {
            row["video_id"]: row["analysis_json"]
            for row in YouTubeVideoCache.objects.filter(video_id__in=[i.youtube_video_id for i in items]).values("video_id", "analysis_json")
        }

        item_serializer = PlaylistItemSerializer(items, many=True, context={"analysis_map": analysis_map})
        playlist_serializer = ParentPlaylistSerializer(playlist)

        video_ids = [i.youtube_video_id for i in items]
        embed_params = {
            "modestbranding": 1,
            "rel": 0,
            "controls": 1,
            "playsinline": 1,
            "autoplay": 0,
            "loop": 1,
            "playlist": ",".join(video_ids),
            "enablejsapi": 1,
            "iv_load_policy": 3,
        }

        return self.success_response(
            message="Playlist detail fetched successfully",
            data={
                "playlist": playlist_serializer.data,
                "items": item_serializer.data,
                "explanation": explanation.why_suitable_text if explanation else "",
                "status": playlist.status,
                "player": {
                    "video_ids": video_ids,
                    "embed_params": embed_params,
                },
            },
            status_code=status.HTTP_200_OK
        )
    
    def delete(self, request, playlist_id):
        playlist = Playlist.objects.filter(id=playlist_id, user=request.user, is_saved=True).first()
        if not playlist:
            return self.error_response("Playlist not found or cannot be deleted", status_code=status.HTTP_404_NOT_FOUND)

        playlist.delete()
        return self.success_response(
            message="Playlist deleted successfully",
            data={},
            status_code=status.HTTP_204_NO_CONTENT
        )


class JobStatusAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        job = JobRun.objects.filter(id=job_id, user=request.user).first()
        if not job:
            return self.error_response("Job not found", status_code=status.HTTP_404_NOT_FOUND)

        data = {
            "job_id": str(job.id),
            "status": job.status,
            "task_name": job.task_name,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "error": job.error,
            "meta": job.meta,
        }
        return self.success_response(
            message="Job status fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )


class JobCancelAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        job = JobRun.objects.filter(id=job_id, user=request.user).first()
        if not job:
            return self.error_response("Job not found", status_code=status.HTTP_404_NOT_FOUND)

        if job.status == "canceled":
            return self.success_response(
                message="Job already canceled",
                data={"job_id": str(job.id), "status": job.status},
                status_code=status.HTTP_200_OK
            )

        if job.status != "queued":
            return self.error_response(
                message="Only queued jobs can be canceled",
                data={"job_id": str(job.id), "status": job.status},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        playlist_id = (job.meta or {}).get("playlist_id")
        playlist = Playlist.objects.filter(id=playlist_id, user=request.user).first() if playlist_id else None

        job.status = "canceled"
        job.error = "Canceled by user"
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error", "finished_at"])

        if playlist and playlist.status == "queued":
            playlist.status = "canceled"
            playlist.save(update_fields=["status"])

        return self.success_response(
            message="Job canceled successfully",
            data={
                "job_id": str(job.id),
                "status": job.status,
                "playlist_id": playlist.id if playlist else playlist_id,
                "playlist_status": playlist.status if playlist else None,
            },
            status_code=status.HTTP_200_OK
        )


class ParentPlaylistOverviewAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        playlists = (
            Playlist.objects.filter(user=request.user)
            .select_related("child_profile")
            .annotate(video_count=Count("items"))
            .order_by("-created_at")
        )
        serializer = ParentPlaylistOverviewSerializer(playlists, many=True)
        return self.success_response(
            message="Playlist overview fetched successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.payment_stripe.views import HasPackage2Subscription
class PremiumFeatureView(APIView):
    permission_classes = [IsAuthenticated, HasPackage2Subscription]

    def get(self, request):
        return Response({"success": True, "message": "Welcome premium user!"})
