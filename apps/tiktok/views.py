import requests
from rest_framework import permissions, status
from .serializers import TikTokVideoQuerySerializer
from apps.users.models import TikTokOAuthToken
from rest_framework.views import APIView
from rest_framework.response import Response

TIKTOK_VIDEO_QUERY_URL = "https://open.tiktokapis.com/v2/video/query/"

DEFAULT_VIDEO_FIELDS = [
    "id", "title", "cover_image_url", "share_url",
    "like_count", "comment_count", "share_count", "view_count",
    "create_time", "duration"
]


class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"success": True, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )

    def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"success": False, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )



class TikTokQueryVideosAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TikTokVideoQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Invalid payload", data=serializer.errors)

        video_ids = serializer.validated_data["video_ids"]
        fields_list = serializer.validated_data.get("fields") or DEFAULT_VIDEO_FIELDS
        fields = ",".join(fields_list)

        # user এর token আছে কিনা
        try:
            token_obj = request.user.tiktok_oauth
        except Exception:
            return self.error_response("TikTok not connected for this user", status_code=status.HTTP_400_BAD_REQUEST)

        if not token_obj.access_token:
            return self.error_response("TikTok access token missing", status_code=status.HTTP_400_BAD_REQUEST)

        # TikTok API call
        try:
            res = requests.post(
                TIKTOK_VIDEO_QUERY_URL,
                params={"fields": fields},
                headers={
                    "Authorization": f"Bearer {token_obj.access_token}",
                    "Content-Type": "application/json",
                },
                json={"filters": {"video_ids": video_ids}},
                timeout=25,
            )
            data = res.json()
        except Exception as e:
            return self.error_response("TikTok request failed", data={"detail": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if res.status_code >= 400:
            return self.error_response("TikTok API error", data=data, status_code=res.status_code)

        return self.success_response("TikTok videos queried", data=data)







import requests
from rest_framework import permissions, status
from .serializers import TikTokVideoListSerializer
from apps.users.models import TikTokOAuthToken

TIKTOK_VIDEO_LIST_URL = "https://open.tiktokapis.com/v2/video/list/"

DEFAULT_LIST_FIELDS = ["id", "title", "cover_image_url", "create_time"]

class TikTokListVideosAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TikTokVideoListSerializer(data=request.data or {})
        if not serializer.is_valid():
            return self.error_response("Invalid payload", data=serializer.errors)

        payload = {}
        cursor = serializer.validated_data.get("cursor")
        max_count = serializer.validated_data.get("max_count", 10)

        payload["max_count"] = max_count
        if cursor is not None:
            payload["cursor"] = cursor

        fields_list = serializer.validated_data.get("fields") or DEFAULT_LIST_FIELDS
        fields = ",".join(fields_list)

        # user token check
        try:
            token_obj = request.user.tiktok_oauth
        except Exception:
            return self.error_response("TikTok not connected for this user", status_code=status.HTTP_400_BAD_REQUEST)

        if not token_obj.access_token:
            return self.error_response("TikTok access token missing", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            res = requests.post(
                TIKTOK_VIDEO_LIST_URL,
                params={"fields": fields},
                headers={
                    "Authorization": f"Bearer {token_obj.access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=25,
            )
            data = res.json()
        except Exception as e:
            return self.error_response("TikTok request failed", data={"detail": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if res.status_code >= 400:
            return self.error_response("TikTok API error", data=data, status_code=res.status_code)

        return self.success_response("TikTok videos listed", data=data)
