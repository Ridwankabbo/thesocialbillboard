from django.urls import path
from .views import ChannelDataView, AuditReportView, DownloadReportView, ListReportsView, AuditListView, AuditDetailsView, BadgeRankingAnalysisView

# from apps.dashboard.views import YouTubeAnalyzerAPIView
# from apps.dashboard.youtube_utils import *




urlpatterns = [
    path('YT-channel-data/', ChannelDataView.as_view(), name='channel-data'), #
    path('audit-report/', AuditReportView.as_view(), name='audit-report'),
    path('audit-report/<int:report_id>/download/', DownloadReportView.as_view(), name='download-report'),
    path('audit-reports/', ListReportsView.as_view(), name='list-reports'),
    
    path('audit-list/', AuditListView.as_view(), name='audit-list'),
    path('audit-detail/<int:pk>/view/', AuditDetailsView.as_view(), name='audit-detail'),
    path('badge-ranking-analysis/', BadgeRankingAnalysisView.as_view(), name='badge-ranking-analysis'),


    # new audit review
    # path('youtube-channel-data/', YouTubeAnalyzerAPIView.as_view(), name='channel-data'),
]

