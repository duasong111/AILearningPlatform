from datetime import datetime

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Subject

from .models import LearningPlan
from .serializers import LearningPlanSerializer


class LearningPlanViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = LearningPlanSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "subject",
        "conversation",
        "state",
        "target_agent",
        "action_type",
        "difficulty",
        "node_name",
    ]

    def get_queryset(self):
        qs = (
            LearningPlan.objects
            .filter(subject__user=self.request.user)
            .select_related("subject", "conversation")
        )
        # ── JSON 字段过滤（memory.step_type / memory.tag）──
        step_type = self.request.query_params.get("step_type")
        if step_type:
            qs = qs.filter(memory__step_type=step_type)

        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(memory__tag=tag)

        # 默认按 expected_completion_time 升序
        return qs.order_by("expected_completion_time", "id")

    def perform_create(self, serializer):
        """POST /api/plans/ — subject 通过 subject_name (code) 查找当前用户的 Subject"""
        subject_name = self.request.data.get("subject_name")
        if not subject_name:
            raise ValidationError({"subject_name": "此字段必填"})

        try:
            subject = Subject.objects.get(user=self.request.user, name=subject_name)
        except Subject.DoesNotExist:
            raise ValidationError({"subject_name": f"学科 '{subject_name}' 不存在或无权访问"})

        serializer.save(subject=subject)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """POST /api/plans/{id}/complete/

        便捷接口：标记 plan 为 success（actual_completion_time 自动 = now）
        Body 可选: { "actual_completion_time": "2026-06-23T10:00:00Z" }
        """
        plan = self.get_object()

        custom_time = request.data.get("actual_completion_time")
        if custom_time:
            try:
                plan.actual_completion_time = datetime.fromisoformat(
                    custom_time.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                return Response(
                    {"error": "actual_completion_time 必须是 ISO 8601 格式"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            plan.actual_completion_time = timezone.now()

        plan.state = LearningPlan.STATE_SUCCESS
        plan.save()  # save() 会自动写 success_time 和 completed
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        """POST /api/plans/{id}/skip/

        便捷接口：标记 plan 为 skipped
        Body 可选: { "reason": "用户自评熟悉" }
        """
        plan = self.get_object()
        reason = request.data.get("reason", "")
        if reason:
            memory = dict(plan.memory or {})
            memory["skip_reason"] = reason
            memory["skipped_at"] = timezone.now().isoformat()
            plan.memory = memory
        plan.state = LearningPlan.STATE_SKIPPED
        plan.save(update_fields=["state", "memory", "updated_at"])
        return Response(self.get_serializer(plan).data)
