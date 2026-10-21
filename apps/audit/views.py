from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import permissions
from django.conf import settings
from .serializers import ChannelDataSerializer, AuditRequestSerializer, ChannelAuditReportSerializer, AuditListSerializer
from .services import YouTubeService, OpenAIService
from .pdf_generator import PDFGenerator
from .models import ChannelAuditReport
import logging
from apps.parents.views import  *
from apps.creator_dashboard.models import (
    CreatorProfile,
)

from .utils import *
from django.core.exceptions import ObjectDoesNotExist
logger = logging.getLogger(__name__)


from apps.parents.utils import get_channel_overview

class ChannelDataView(ChannelOverviewAPIView):
    """
    API endpoint to fetch basic YouTube channel data for the logged-in user's profile.
    """
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
            youtube_channel_id = profile.youtube_profile.youtube_channel_id
        except CreatorProfile.DoesNotExist:
            return Response(
                {"error": "Creator profile not found for the user."},
                status=status.HTTP_404_NOT_FOUND
            )
        except ObjectDoesNotExist:
            return Response(
                {"error": "Creator profile not found for the user."},
                status=status.HTTP_404_NOT_FOUND
            )
        channel_id = youtube_channel_id
    
        if not channel_id:
            return Response(
                {"error": "Invalid YouTube link in profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. YouTube service  channel data  fetch
        youtube_service = YouTubeService(access_token=profile.youtube_credentials.access_token)
        try:
            channel_data = get_channel_overview(channel_id)
            return Response(channel_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching channel data for {channel_id}: {e}", exc_info=True)
            return Response(
                {"error": f"Could not fetch channel data: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from apps.payment_stripe.views import HasPackage2Subscription
from datetime import date
from rest_framework import permissions

class AuditReportView(APIView):
    """
    API endpoint to generate a niche-alignment AI audit report
    for the logged-in user's YouTube channel.

    Flow:
        1. Fetch channel information via get_channel_overview().
        2. Fetch the last 10 public videos (title, description, tags, published_at).
        3. Build a single prompt and call the LLM.
        4. Save the report + PDF and return the serialised result.
    """
    permission_classes = [permissions.IsAuthenticated, HasPackage2Subscription]

    def post(self, request):

        try:
            profile = CreatorProfile.objects.get(user=request.user)
            youtube_channel_id = profile.youtube_profile.youtube_channel_id
        except (CreatorProfile.DoesNotExist, ObjectDoesNotExist):
            return Response(
                {"error": "Creator profile not found for the user."},
                status=status.HTTP_404_NOT_FOUND
            )

        channel_id = youtube_channel_id
        if not channel_id:
            return Response(
                {"error": "Invalid YouTube link in profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
        pdf_generator = PDFGenerator()
        report_type = "niche_alignment"

        try:
            # --- Step 1: Fetch channel information ---
            channel_data = get_channel_overview(channel_id)
            if not channel_data:
                return Response(
                    {"error": "Could not retrieve channel data. Check Channel ID."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # --- Step 2: Fetch last 10 public videos ---
            # Public video/playlist data requires only an API key, not OAuth credentials.
            youtube_service = YouTubeService(access_token=profile.youtube_credentials.access_token, api_key=settings.YOUTUBE_API_KEY)
            videos = youtube_service.get_last_10_videos(channel_id)
            logger.info(
                f"Fetched {len(videos)} videos for channel {channel_id} to build audit prompt."
            )

            # --- Step 3: Build prompt & call LLM (single request) ---
            report_date = date.today().isoformat()
            ai_insights = openai_service.generate_niche_alignment_report(
                channel_data=channel_data,
                videos=videos,
                report_date=report_date,
            )

            # --- Step 4: Save report in DB ---
            report_instance = ChannelAuditReport.objects.create(
                user=request.user,
                channel_id=channel_id,
                report_type=report_type,
                report_data={
                    "channel_data": channel_data,
                    "ai_insights": ai_insights,
                    "videos_audited": [
                        {
                            "title": v.get("title"),
                            "published_at": v.get("published_at"),
                        }
                        for v in videos
                    ],
                },
                custom_prompt_used="",
            )

            # --- Step 5: Generate & save PDF ---
            html_content = pdf_generator.generate_html_for_pdf(
                channel_data=channel_data,
                ai_insights=ai_insights,
                report_type=report_type,
                custom_prompt="",
            )
            pdf_bytes = pdf_generator.generate_pdf_from_html(html_content)

            report_instance.pdf_report.save(
                f"{channel_id}_{report_type}_audit_{report_instance.pk}.pdf",
                content=pdf_bytes,
                save=True,
            )

            serializer = ChannelAuditReportSerializer(report_instance, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(
                f"Error generating niche-alignment audit report for {channel_id}: {e}",
                exc_info=True,
            )
            return Response(
                {
                    "message": "An error occurred while generating the audit report.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )





   ####### this is nur's code
# class AuditReportView(APIView):
#     """
#     API endpoint to request and generate an AI-powered audit report.
#     """
#     def post(self, request):
#         serializer = AuditRequestSerializer(data=request.data)
#         if serializer.is_valid():
#             channel_id = serializer.validated_data['channel_id']
#             report_type = serializer.validated_data['report_type']
#             custom_prompt = serializer.validated_data.get('custom_prompt', '')

#             youtube_service = YouTubeService(api_key=settings.YOUTUBE_API_KEY)
#             openai_service = OpenAIService(api_key=settings.OPENAI_API_KEY)
#             pdf_generator = PDFGenerator()

#             try:
#                 # 1. Fetch YouTube data
#                 channel_data = youtube_service.get_channel_data(channel_id)
#                 if not channel_data:
#                     return Response(
#                         {"error": "Could not retrieve channel data from YouTube API. Check Channel ID or API key."},
#                         status=status.HTTP_404_NOT_FOUND
#                     )

#                 # Fetch comments for sentiment/engagement analysis if needed
#                 comments_data = []
#                 if report_type in ['sentiment', 'engagement']:
#                     comments_data = youtube_service.get_channel_comments(channel_id)
#                     if not comments_data:
#                         logger.warning(f"No comments found for channel {channel_id} for {report_type} audit.")
#                         # Proceed with audit, but AI might report lack of comment data

#                 # 2. Prepare data for AI and generate AI insights
#                 ai_input_data = {
#                     "channel_data": channel_data,
#                     "comments_data": comments_data,
#                     "report_type": report_type,
#                     "custom_prompt": custom_prompt
#                 }
                
#                 ai_insights = openai_service.generate_audit_insights(ai_input_data)

#                 # 3. Store the report data in the database
#                 report_instance = ChannelAuditReport.objects.create(
#                     channel_id=channel_id,
#                     report_type=report_type,
#                     report_data={
#                         "channel_data": channel_data,
#                         "ai_insights": ai_insights,
#                         "comments_data_summary": comments_data[:5] # Store a small sample or summary
#                     },
#                     custom_prompt_used=custom_prompt
#                 )

#                 # 4. Generate PDF report
#                 # This is a simplified example. In a real app, you'd create a more
#                 # sophisticated HTML template for the PDF.
#                 html_content = pdf_generator.generate_html_for_pdf(
#                     channel_data=channel_data,
#                     ai_insights=ai_insights,
#                     report_type=report_type,
#                     custom_prompt=custom_prompt
#                 )
#                 pdf_bytes = pdf_generator.generate_pdf_from_html(html_content)

#                 # Save PDF to the model instance
#                 report_instance.pdf_report.save(
#                     f"{channel_id}_{report_type}_audit_{report_instance.pk}.pdf",
#                     content=pdf_bytes,
#                     save=True
#                 )

#                 serializer = ChannelAuditReportSerializer(report_instance)
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)

#             except Exception as e:
#                 logger.error(f"Error generating audit report for {channel_id} ({report_type}): {e}", exc_info=True)
#                 return Response(
#                     {"error": f"Could not generate audit report: {e}"},
#                     status=status.HTTP_500_INTERNAL_SERVER_ERROR
#                 )
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.http import FileResponse, Http404
class DownloadReportView(APIView):
    """
    API endpoint to download a specific audit report PDF.
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, report_id):
        try:
            report = ChannelAuditReport.objects.get(pk=report_id)
            if not report.pdf_report:
                return Response({"error": "PDF report not found for this audit ID."},
                                status=status.HTTP_404_NOT_FOUND)

            file_handle = report.pdf_report.open("rb")
            response = FileResponse(file_handle, content_type="application/pdf")
            filename = report.pdf_report.name.split("/")[-1]
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except ChannelAuditReport.DoesNotExist:
            return Response({"error": "Audit report not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error downloading report {report_id}")
            return Response({"error": "Could not download report."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# class DownloadReportView(APIView):
#     """
#     API endpoint to download a specific audit report PDF.
#     """
#     def get(self, request, report_id):
#         try:
#             report = ChannelAuditReport.objects.get(pk=report_id)

#             if not report.pdf_report:
#                 return Response(
#                     {"error": "PDF report not found for this audit ID."},
#                     status=status.HTTP_404_NOT_FOUND
#                 )

#             # Serve the file as a download
#             response = FileResponse(report.pdf_report.open("rb"), content_type="application/pdf")
#             response["Content-Disposition"] = f'attachment; filename="{report.pdf_report.name}"'
#             return response

#         except ChannelAuditReport.DoesNotExist:
#             return Response(
#                 {"error": "Audit report not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:
#             logger.error(f"Error downloading report {report_id}: {e}")
#             return Response(
#                 {"error": f"Could not download report: {str(e)}"},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

class ListReportsView(APIView):
    """
    API endpoint to list all generated audit reports.
    """
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        reports = ChannelAuditReport.objects.filter(user=request.user)
        serializer = ChannelAuditReportSerializer(reports, many=True, context={"request":request})
        return Response(serializer.data, status=status.HTTP_200_OK)

import math
from rest_framework.pagination import PageNumberPagination
class CustomPaginator(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        # 1. Calculate current page number from request query parameters
        try:
            current_page = int(self.request.query_params.get(self.page_query_param, 1))
        except ValueError:
            current_page = 1

        # 2. Compute total pages based on count and current page size split [stem-calculative-problem-solving]
        total_items = self.page.paginator.count
        current_size = self.get_page_size(self.request)
        total_pages = math.ceil(total_items / current_size) if current_size else 1

        # 3. Return the fully extended structural layout dictionary
        return Response({
            "count": total_items,
            "total_pages": total_pages,       # New field
            "current_page": current_page,     # New field
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data
        })
    
class AuditListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        reports = ChannelAuditReport.objects.filter(user=request.user)
        paginator = CustomPaginator()
        paginated_data = paginator.paginate_queryset(reports, request)
        serializer = AuditListSerializer(paginated_data, many=True, context={'request':request})
        result_data = paginator.get_paginated_response(serializer.data).data
        return Response(result_data, status=status.HTTP_200_OK)
    
class AuditDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, pk):
        try:
            report = ChannelAuditReport.objects.get(pk=pk)
            serializer = ChannelAuditReportSerializer(report, context={'request': request})
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ChannelAuditReport.DoesNotExist:
            return Response({
                "error": "Audit report not found."
            }, status=status.HTTP_404_NOT_FOUND)

class BadgeRankingAnalysisView(APIView):
    """
    API endpoint for badge and ranking analysis based on the last audit report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            profile = CreatorProfile.objects.get(user=request.user)
            youtube_channel_id = profile.youtube_profile.youtube_channel_id
        except (CreatorProfile.DoesNotExist, ObjectDoesNotExist):
            return Response(
                {"error": "Creator profile not found for the user."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not youtube_channel_id:
            return Response(
                {"error": "Invalid YouTube link in profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        last_report = ChannelAuditReport.objects.filter(channel_id=youtube_channel_id).order_by('-generated_at').first()

        if not last_report:
            return Response(
                {"error": "No audit report found. Please generate an audit report first."},
                status=status.HTTP_404_NOT_FOUND
            )

        channel_data = last_report.report_data.get('channel_data', {})
        
        # Heuristic Logic for Badges
        try:
            video_count = int(channel_data.get('video_count', 0) or 0)
            sub_count = int(channel_data.get('subscriber_count', 0) or 0)
            view_count = int(channel_data.get('view_count', 0) or 0)
        except (ValueError, TypeError):
            video_count, sub_count, view_count = 0, 0, 0

        # Consistency Badge
        if video_count >= 200:
            consistency = "Rock Solid"
        elif video_count >= 100:
            consistency = "Steady Feed"
        elif video_count >= 50:
            consistency = "Unwavering"
        else:
            consistency = "Ironclad"

        # Growth Badge
        ratio = view_count / max(sub_count, 1)
        if ratio > 200:
            growth = "Surging"
        elif ratio > 100:
            growth = "Aggressive"
        elif ratio > 50:
            growth = "Velocity"
        else:
            growth = "High Yield"

        # Safe for Kid Badge
        # Placeholder logic: based on channel type or default to Gold if unknown
        is_explicitly_made_for_kids = channel_data.get('made_for_kids') or channel_data.get('status', {}).get('madeForKids')
        channel_category = str(channel_data.get('category', '')).lower()
        channel_tags = [tag.lower() for tag in channel_data.get('keywords', [])]

        # Define safe keyword matches (e.g. learning, toys, gaming for kids)
        family_friendly_keywords = {'kids', 'animation', 'nursery', 'education', 'toys', 'cartoon', 'family'}
        has_family_tags = any(tag in family_friendly_keywords for tag in channel_tags)

        if is_explicitly_made_for_kids:
            safe_for_kid = "Safe Haven"    # Highest standard: certified by YouTube policies
        elif channel_category in ['education', 'entertainment'] and has_family_tags:
            safe_for_kid = "Shielded"      # Highly compliant contextual metadata
        elif "gaming" in channel_category or "vlog" in channel_category:
            safe_for_kid = "Secured Tier"  # Moderate family compatibility 
        else:
            safe_for_kid = "Conservative"  # Default generic baseline classification 

        # Niche Ranking (e.g. 8 for 8%)
        # Just a heuristic mock calculation based on sub count for demonstration
        niche_percentage = max(1, min(99, 100 - (sub_count // 10000)))

        return Response({
            "consistency_badge": consistency,
            "growth_badge": growth,
            "safe_for_kid_badge": safe_for_kid,
            "niche_percentage": niche_percentage
        }, status=status.HTTP_200_OK)
