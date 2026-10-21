from django.urls import path

from .views import (
    ViralBuilderRunCreateAPIView,
    ViralBuilderRunDetailAPIView,
    ViralIdeaSavedListAPIView,
    ViralIdeaSaveAPIView,
    ViralIdeaSentToPlanListAPIView,
    ViralIdeaSendToPlanAPIView,
    GetPlartformAccount,
    DeleteViralbuilderPlaylistAPIView,
)

urlpatterns = [
    path("v1/creator/viral-builder/run/", ViralBuilderRunCreateAPIView.as_view(), name="viral-builder-run"),
    path("v1/creator/viral-builder/run/<int:run_id>/", ViralBuilderRunDetailAPIView.as_view(), name="viral-builder-run-detail"),
    path("v1/creator/viral-builder/ideas/saved/", ViralIdeaSavedListAPIView.as_view(), name="viral-builder-idea-saved-list"),
    path("v1/creator/viral-builder/ideas/<int:idea_id>/save/", ViralIdeaSaveAPIView.as_view(), name="viral-builder-idea-save"),
    path("v1/creator/viral-builder/ideas/sent-to-plan/", ViralIdeaSentToPlanListAPIView.as_view(), name="viral-builder-idea-sent-to-plan-list"),
    path("v1/creator/viral-builder/ideas/<int:idea_id>/send-to-plan/", ViralIdeaSendToPlanAPIView.as_view(), name="viral-builder-idea-send-to-plan"),
    path("v1/creator/viral-builder/ideas/<int:idea_id>/delete/", DeleteViralbuilderPlaylistAPIView.as_view(), name="viral-builder-playlist-delete"),
    
    path('v1/plartform-account/', GetPlartformAccount.as_view(), name='plartform-account')
]
