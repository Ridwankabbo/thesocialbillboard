from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from apps.parents.models import JobRun
from apps.users.views import BaseAPIView

from .models import ViralBuilderRun, ViralIdea, PlatformAccount
from .serializers import (
    ViralBuilderRunCreateSerializer,
    ViralBuilderRunSerializer,
    ViralIdeaSerializer,
    PlartformAccountSerializer
)
from .tasks import viral_builder_generate
from apps.payment_stripe.views import HasPackage2Subscription



class GetPlartformAccount(BaseAPIView):
    
    def get(self, request):
        plartform_account = PlatformAccount.objects.filter(user=request.user, platform = 'youtube').first()
        serializer = PlartformAccountSerializer(plartform_account)
        return Response({
            "id": serializer.data.get('id')
        })

class ViralBuilderRunCreateAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated, HasPackage2Subscription]

    def post(self, request):
        serializer = ViralBuilderRunCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return self.error_response("Validation error", data=serializer.errors)

        run = serializer.save()

        job = JobRun.objects.create(
            user=request.user,
            task_name="viral_builder_generate",
            status="queued",
            meta={"run_id": run.id},
        )

        run.meta = {"job_id": str(job.id)}
        run.save(update_fields=["meta"])

        viral_builder_generate.delay(run.id, str(job.id))

        return self.success_response(
            message="Viral Builder run queued",
            data={
                "run_id": run.id,
                "job_id": str(job.id),
                "status": run.status,
            },
            status_code=status.HTTP_201_CREATED,
        )


class ViralBuilderRunDetailAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, run_id):
        run = ViralBuilderRun.objects.filter(id=run_id, user=request.user).first()
        if not run:
            return self.error_response("Run not found", status_code=status.HTTP_404_NOT_FOUND)

        run_data = ViralBuilderRunSerializer(run).data
        ideas_data = []
        if run.status == "done":
            ideas = ViralIdea.objects.filter(run=run).order_by("-created_at")
            ideas_data = ViralIdeaSerializer(ideas, many=True).data

        return self.success_response(
            message="Viral Builder run fetched",
            data={
                "run": run_data,
                "ideas": ideas_data,
            },
            status_code=status.HTTP_200_OK,
        )


class ViralIdeaSaveAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response("Idea not found", status_code=status.HTTP_404_NOT_FOUND)

        return self.success_response(
            message="Idea save status fetched",
            data={
                "idea_id": idea.id,
                "is_saved": idea.is_saved,
                "saved_at": idea.saved_at,
            },
            status_code=status.HTTP_200_OK,
        )

    def post(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response("Idea not found", status_code=status.HTTP_404_NOT_FOUND)

        if idea.is_saved:
            return self.success_response(
                message="Idea already saved",
                data={"idea_id": idea.id, "is_saved": True},
                status_code=status.HTTP_200_OK,
            )

        idea.is_saved = True
        idea.saved_at = timezone.now()
        idea.save(update_fields=["is_saved", "saved_at"])

        return self.success_response(
            message="Idea saved",
            data={"idea_id": idea.id, "is_saved": True},
            status_code=status.HTTP_200_OK,
        )
        
class DeleteViralbuilderPlaylistAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    
    def delete(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response(
                message="Idea not found",
                status_code = status.HTTP_404_NOT_FOUND
            )
        idea.delete()
        return self.success_response(
            message = "Idea deleted successfully",
            data = {"idea_id":idea_id}
        )


class ViralIdeaSendToPlanAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated ]

    def get(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response("Idea not found", status_code=status.HTTP_404_NOT_FOUND)

        return self.success_response(
            message="Idea send-to-plan status fetched",
            data={
                "idea_id": idea.id,
                "sent_to_plan_at": idea.sent_to_plan_at,
            },
            status_code=status.HTTP_200_OK,
        )

    def post(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response("Idea not found", status_code=status.HTTP_404_NOT_FOUND)

        idea.sent_to_plan_at = timezone.now()
        idea.save(update_fields=["sent_to_plan_at"])

        return self.success_response(
            message="Idea sent to plan",
            data={"idea_id": idea.id, "sent_to_plan_at": idea.sent_to_plan_at},
            status_code=status.HTTP_200_OK,
        )
        
    def delete(self, request, idea_id):
        idea = ViralIdea.objects.select_related("run").filter(id=idea_id, run__user=request.user).first()
        if not idea:
            return self.error_response("Idea not found", status_code=status.HTTP_404_NOT_FOUND)
        idea.sent_to_plan_at = None
        idea.save(update_fields=["sent_to_plan_at"])
        
        return self.success_response(
            message="Idea removed from plan",
            data={"idea_id": idea.id, "sent_to_plan_at": idea.sent_to_plan_at},
            status_code=status.HTTP_200_OK,
        )

class ViralIdeaSavedListAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ideas = (
            ViralIdea.objects.select_related("run")
            .filter(run__user=request.user, is_saved=True)
            .order_by("-saved_at", "-created_at")
        )
        ideas_data = ViralIdeaSerializer(ideas, many=True).data

        return self.success_response(
            message="Saved ideas fetched",
            data={"count": len(ideas_data), "ideas": ideas_data},
            status_code=status.HTTP_200_OK,
        )


class ViralIdeaSentToPlanListAPIView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ideas = (
            ViralIdea.objects.select_related("run")
            .filter(run__user=request.user, sent_to_plan_at__isnull=False)
            .order_by("-sent_to_plan_at", "-created_at")
        )
        ideas_data = ViralIdeaSerializer(ideas, many=True).data

        return self.success_response(
            message="Sent-to-plan ideas fetched",
            data={"count": len(ideas_data), "ideas": ideas_data},
            status_code=status.HTTP_200_OK,
        )
