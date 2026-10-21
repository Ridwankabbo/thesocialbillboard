from django.shortcuts import render
from rest_framework.response import Response
from .utils import BaseAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .service import get_leaderboard_data
from .serializers import LeaderboardSerializer
from rest_framework.permissions import IsAuthenticated
# Create your views here.


class LeaderboardView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform = request.query_params.get("platform")
        time = request.query_params.get("time")

        try:
            # leaderboard = get_leaderboard_data(platform=platform, time=time)

            leaderboard = list(get_leaderboard_data(platform=platform))

            current_user_profile = next(
                (item for item in leaderboard if item.user_id == request.user.id),
                None
            )

            if current_user_profile:
                try:
                    from apps.creator_dashboard.tasks import sync_single_creator_profile
                    sync_single_creator_profile.delay(current_user_profile.id)
                except Exception:
                    pass

            current_rank = getattr(current_user_profile, 'rank', 'N/A')
            current_subs = getattr(current_user_profile, 'total_subscribers', 0) or 0
            current_engagement = getattr(current_user_profile, 'engagement_rate', 0) or 0
            current_growth = getattr(current_user_profile, 'growth_rate', 0.0) or 0.0
            
            current_image_url = None
            if current_user_profile and current_user_profile.user.profile_pic:
                current_image_url = request.build_absolute_uri(current_user_profile.user.profile_pic.url)

            serializer = LeaderboardSerializer(leaderboard, many=True, context={'request': request})

            data = {
                "current_user_rank": {
                    "rank": current_rank,
                    "subscribers": self._format_subs(current_subs),
                    "engagement_rate": f"{round(current_engagement, 1)}%",
                    "growth_rate": f"{round(current_growth, 1)}%",
                    "profile_image": current_image_url
                },
                "leaderboard": serializer.data
            }

            return self.success_response(
                message="Leaderboard data retrieved successfully",
                data=data,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def _format_subs(self, val):
        if not val:
            return "0"
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f} M"
        return f"{val/1000:.1f} K"