from calendar import month_name

from django.conf import settings
import secrets
from rest_framework.permissions import IsAuthenticated
from sqlalchemy.orm import Query
from voluptuous import Number
from .utils import BaseAPIView
from rest_framework import request, status
from .service import ( get_youtube_competitors, refresh_profile_data, tiktok_login,
    tiktok_callback_service,
    youtube_auth,
    youtube_callback_service,
    refresh_tiktok_token_service,
    titkok_profile_details_service,
    get_all_titok_videos,
    sync_youtube_videos,
    instagram_callback_service,
    trigger_instagram_sync,
    instagram_auth,
    sync_instagram_media, 
    refresh_youtube_token,
    instagram_refresh_token_service,
)   
from .serializers import (ChannelAuditSerializer, CreatorProfileSerializers, TiktokProfileSerializer, 
    YoutubeProfileSerializer,
    InstagramProfileSerializer,
    TiktokProfileDetailsSerializer,
    YoutubeProfileDetailsSerializer,
    InstagramProfileDetailSerializer
)
from .models import (
    CreatorProfile,
    PlatformChoices,
    TiktokProfile,
    YoutubeProfile,
    InstagramProfile,
    TiktokCredentials,
    YoutubeCredentials,
    InstagramCredentials,
    TiktokProfileMedia,
    YoutubeProfileMedia,
    InstagramProfileMedia
)
from django.conf import settings
from django.contrib.auth import get_user_model
# Create your views here.
from datetime import timezone
from django.shortcuts import redirect

User = get_user_model()


def filter_queryset_by_month(queryset, request):

    month = request.GET.get("month")

    if not month:
        return queryset

    try:
        month_number = int(month)

    except ValueError:
        raise ValueError(
            "Invalid month parameter. Use numbers 1-12."
        )

    if month_number < 1 or month_number > 12:
        raise ValueError(
            "Month must be between 1 and 12."
        )

    queryset = queryset.filter(created_at__month=month_number)

    year = request.GET.get("year")

    if year and year.isdigit():
        queryset = queryset.filter(
            created_at__year=int(year)
        )

    return queryset

""" 
    ================================
        TIKTOK LOGIN AUTH VIEW
    ================================
"""
class TiktokLoginView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        
        # tiktok_login from service.py
        auth_url = tiktok_login(request)
        
        return self.success_response(message="Tiktok authenticatoi url", data=auth_url, status_code= status.HTTP_200_OK)
    
""" 
    ================================
        TIKTOK CALLBACK VIEW
    ================================
"""
from rest_framework.response import Response
class TiktokCallBackView(BaseAPIView):
    
    permission_classes = []

    def get(self, request):
        try:
            response = tiktok_callback_service(request)
        except Exception as e:
            return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/tiktok/failure")
            # return self.error_response(
            #     message="failed",
            #     data={
            #         "response": response if isinstance(response, (dict, list, str, int, float, bool)) else str(response),
            #         "exception": str(e)
            #     }
            # )
        # return self.success_response(
        #     message="TikTok connected successfully",
        #     data=response,
        #     status_code=200
        # )
        
        return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/tiktok/success")
        
        
""" 
    ================================
        TIKTOK REFRESH TOKEN VIEW
    ================================
"""       
class TiktokRefreshTokenView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            profile_instance = CreatorProfile.objects.filter(user=request.user).first()
            
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="No tiktok profile founed",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        refresh_tokne_message = refresh_tiktok_token_service(profile_instance=profile_instance)
        
        return self.success_response(
            message=refresh_tokne_message,
            status_code=status.HTTP_200_OK
        )
    
""" 
    ==================================
        TIKTOK PROFILE VIEW
    ==================================
"""
from django.shortcuts import get_object_or_404
class TiktokProfileView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        month = request.GET.get('month')
        try:
            profile = get_object_or_404(CreatorProfile, user=user)
            creds = TiktokCredentials.objects.get(profile=profile)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Creator profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except TiktokCredentials.DoesNotExist:
            return self.error_response(
                message="TikTok not connected",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 2. Refresh TikTok data every time the endpoint is hit
        refresh_profile_data(profile, platform="tiktok")

        # 3. Get all videos for this profile and platform
        video_queryset = TiktokProfileMedia.objects.filter(
            profile=profile,
            platform=PlatformChoices.TIKTOK
        )

        try:
            video_queryset = filter_queryset_by_month(video_queryset, request)
        except ValueError as e:
            return self.error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 4. SERIALIZE THE PROFILE (One object, not a list)
        serializer = TiktokProfileDetailsSerializer(profile, context={"videos": video_queryset})

        return self.success_response(
            message="Videos synced successfully",
            data=serializer.data,
            status_code=200
        )
        
        
""" 
    =======================================
        GET YOUTUBE PROFILE DETAILS VIEW
    =======================================
"""     

class YoutubeAuthView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        url = youtube_auth(request)
        
        return self.success_response(
            message='Successfully created auth url',
            data=url,
            status_code=status.HTTP_200_OK
        )
        
    
# """ 
#     =============================
#         DISCONNECT YOUTUBE
#     =============================
# """
# from .service import revoke_youtube
# class DisconnectYoutubeView(BaseAPIView):
#     permission_classes = [IsAuthenticated]
#     def get(self, request):
#         profile = CreatorProfile.objects.get(user=request.user)
#         creds = YoutubeCredentials.objects.filter(
#                 profile=profile,
#                 platform=PlatformChoices.YOUTUBE
#             ).first()
#         revoke = revoke_youtube(token=creds.access_token)
#         youtube_profile = YoutubeProfile.objects.get(profile=profile).delete()
#         youtube_media = YoutubeProfileMedia.objects.get(profile=profile).delete()

#         return self.success_response(
#             message='Youtube disconnected successfull',
#             data=revoke
#         )
    
    
    
    
    
    
    
    

""" 
    ================================
        YOUTUBE CALLBACK VIEW
    ================================
"""    
class YoutubeCallbackView(BaseAPIView):

    def get(self, request):
        try:
            response= youtube_callback_service(request)
        except Exception as e:
            # return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/youtube/failure")
            return self.error_response(
                message="Auth failed",
                data=str(e)
            )

        # return self.success_response(
        #     message="YouTube connected successfully",
        #     data=response,
        #     status_code=200
        # )
        
        return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/youtube/success")
        # return self.error_response(
        #     message="Auth failed",
        #     data=response
        # )

""" 
    ================================
        YOUTUBE SYNC VIDEOS VIEW
    ================================
"""
class YoutubeVideosSyncView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = CreatorProfile.objects.get(user=request.user)
        creds = YoutubeCredentials.objects.filter(
            profile=profile,
            platform=PlatformChoices.YOUTUBE
        ).first()

        if not creds:
            return self.error_response(
                message="YouTube not connected",
                status_code=400
            )

        try:
            refresh_profile_data(profile, platform="youtube")
            all_videos = YoutubeProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.YOUTUBE)
            try:
                all_videos = filter_queryset_by_month(all_videos, request)
            except ValueError as e:
                return self.error_response(
                    message=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            serializer = YoutubeProfileDetailsSerializer(
                profile, 
                context={"videos": all_videos} 
            )
        except Exception as e:
            return self.error_response(
                message="Sync failed",
                data=str(e),
                status_code=400
            )

        return self.success_response(
            message="Youtube vides synced",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    

""" 
    ================================
        YOUTUBE TOKEN REFRESH VIEW
    ================================
"""
class YoutubeRefreshTokenView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile_instance = CreatorProfile.objects.filter(user=request.user).first()
            
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="No youtube profile found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        refresh_token_message = refresh_youtube_token(profile=profile_instance)
        
        return self.success_response(
            message=refresh_token_message,
            status_code=status.HTTP_200_OK
        )

        
  
""" 
    ================================
        INSTRAGRAM AUTH VIEW
    ================================
"""      
class InstagramAuthView(BaseAPIView):
    
    def get(self, request):
        url = instagram_auth(request)
        
        return self.success_response(
            message="Instragram auth url",
            data= url,
            status_code= status.HTTP_200_OK
        )


# """ 
#     ================================
#         INSTAGRAM WEEBHOOK
#     ================================
# """
# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# import json
# VERIFY_TOKEN = settings.INSTAGRAM_VERIFY_TOKEN


# @csrf_exempt
# def instagram_webhook(request):
#     VERIFY_TOKEN = settings.INSTAGRAM_VERIFY_TOKEN

#     if request.method == "GET":
#         if (
#             request.GET.get("hub.mode") == "subscribe"
#             and request.GET.get("hub.verify_token") == VERIFY_TOKEN
#         ):
#             return HttpResponse(request.GET.get("hub.challenge"))

#         return HttpResponse("Forbidden", status=403)

#     if request.method == "POST":
#         data = json.loads(request.body.decode("utf-8"))

#         ig_account_id = data.get("entry", [{}])[0].get("id")

#         if not ig_account_id:
#             return HttpResponse("No IG ID", status=400)

#         # handle event here
#         return HttpResponse("OK", status=200)

""" 
    ================================
        INSTAGRAM CALLBACK VIEW
    ================================
"""
from rest_framework.views import APIView
class InstagramCallbackView(BaseAPIView, APIView ):

    def get(self, request):
        try:
            response = instagram_callback_service(request)
        except Exception as e:
            return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/instagram/failure")
            # return self.success_response(
            #     message="Failed",
            #     data=str(e)
            #     # status_code=status.HTTP
            # )
        # return self.success_response(
        #     message="Instagram connected successfully",
        #     data=response,
        #     status_code=200
        # )
        
        return redirect("https://thesocialbillboard.com/dashboard/settings/linked-profile/status/instagram/success")
        

""" 
    ================================
        INSTAGRAM SYNC VIEW
    ================================
"""
class InstagramSyncView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=404
            )

        try:
            creds = InstagramCredentials.objects.get(
            profile=profile,
            platform=PlatformChoices.INSTAGRAM
        )
        except InstagramCredentials.DoesNotExist:
            return self.error_response(
                message="Instagram not connected",
                status_code=400
            )

        try:
            refresh_profile_data(profile, platform="instagram")
            media = InstagramProfileMedia.objects.filter(profile=profile, platform=PlatformChoices.INSTAGRAM)
            try:
                media = filter_queryset_by_month(media, request)
            except ValueError as e:
                return self.error_response(
                    message=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            serializer = InstagramProfileDetailSerializer(
                profile,
                context={"videos": media}
            )
        except Exception as e:
            return self.error_response(
                message="Sync failed",
                data=str(e),
                status_code=400
            )

        return self.success_response(
            message="Instagram media synced",
            data=serializer.data,
            status_code=200
        )
    

""" 
    ================================
        INSTAGRAM TOKEN REFRESH VIEW
    ================================
"""
class InstagramRefreshTokenView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        try:
            profile_instance = CreatorProfile.objects.get(user=request.user)

        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        instagram_refresh_token_message = instagram_refresh_token_service(profile_instance=profile_instance)

        return self.success_response(
            message=instagram_refresh_token_message,
            status_code=status.HTTP_200_OK
        )

""" 
    ================================
        INSTAGRAM WEBHOOK INFO VIEW
    ================================
"""
class InstagramWebhookInfoView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get webhook configuration info for Instagram
        Shows the webhook URL and instructions
        """
        webhook_url = request.build_absolute_uri('/v1/plartfrom/instagram/webhook/')
        verify_token = settings.INSTAGRAM_VERIFY_TOKEN
        
        return self.success_response(
            message="Webhook configuration info",
            data={
                "webhook_url": webhook_url,
                "verify_token": verify_token,
                "instructions": "Configure this webhook URL in your Facebook App's Instagram Product Webhooks section"
            },
            status_code=200
        )

""" 
    ================================
        CREATOR PROFILE VIEW
    ================================
""" 
class CreatorProfileView(BaseAPIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=404
            )

        # Refresh all connected platform data for dashboard overview
        try:
            refresh_profile_data(profile)
        except Exception as e:
            print(f"Creator dashboard refresh failed: {e}")

        serializer = CreatorProfileSerializers(profile)
        
        return self.success_response(
            message="Successfully fetch profile details",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        

"""
    ============================
        COMPETITORS API VIEW
    ============================
"""
from .models import YoutubeProfile
class CompetitiorsAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
            try:
                creds = YoutubeCredentials.objects.get(
                    profile=profile,
                    platform=PlatformChoices.YOUTUBE
                )
            except YoutubeCredentials.DoesNotExist:
                return self.error_response(
                    message="YouTube not connected",
                    status_code=400
                )
            try:
                yt_profile = YoutubeProfile.objects.get(profile=profile)
            except YoutubeProfile.DoesNotExist:
                return self.error_response(
                    message="YouTube profile not connected",
                    status_code=400
                )
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=404
            )
        try:
            from .service import get_or_determine_content_type
            topic = get_or_determine_content_type(yt_profile)

            competitors = get_youtube_competitors(creds.access_token, topic)
            return self.success_response(
                message="Successfully fetched competitors",
                data=competitors,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            return self.error_response(
                message="Failed to fetch competitors",
                data=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class TiktokDisconnectView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        TiktokCredentials.objects.filter(profile=profile).delete()
        TiktokProfile.objects.filter(profile=profile).delete()
        TiktokProfileMedia.objects.filter(profile=profile).delete() 
        user = User.objects.get(id=request.user.id)
        user.tiktok_link = False
        user.save()

        return self.success_response(
            message="TikTok disconnected successfully",
            status_code=status.HTTP_200_OK
        )


class YoutubeDisconnectView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        YoutubeCredentials.objects.filter(profile=profile).delete()
        YoutubeProfile.objects.filter(profile=profile).delete()
        YoutubeProfileMedia.objects.filter(profile=profile).delete()
        user = User.objects.get(id=request.user.id)
        user.youtube_link = False
        user.save()

        return self.success_response(
            message="YouTube disconnected successfully",
            status_code=status.HTTP_200_OK
        )


class InstagramDisconnectView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
        except CreatorProfile.DoesNotExist:
            return self.error_response(
                message="Profile not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        InstagramCredentials.objects.filter(profile=profile).delete()
        InstagramProfile.objects.filter(profile=profile).delete()
        InstagramProfileMedia.objects.filter(profile=profile).delete()
        user = User.objects.get(id=request.user.id)
        user.instagram_link = False
        user.save()

        return self.success_response(
            message="Instagram disconnected successfully",
            status_code=status.HTTP_200_OK
        )
    
