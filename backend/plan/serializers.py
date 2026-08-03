"""Plan serializers.

LearningPlanItem 已合并到 LearningPlan，这里只剩 LearningPlanSerializer。
"""

from rest_framework import serializers

from .models import LearningPlan


class LearningPlanSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source="subject.id", read_only=True)
    conversation_id = serializers.IntegerField(
        source="conversation.id", read_only=True, allow_null=True,
    )
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_display = serializers.SerializerMethodField()

    class Meta:
        model = LearningPlan
        fields = [
            "id",
            "subject_id",
            "conversation_id",
            "subject_name",
            "subject_display",
            "target_agent",
            "node_id",
            "node_name",
            "node_type",
            "order",
            "action_type",
            "difficulty",
            "plan_difficulty",
            "memory",
            "state",
            "completed",
            "expected_minutes",
            "expected_completion_time",
            "actual_completion_time",
            "create_time",
            "success_time",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "subject_id",
            "conversation_id",
            "subject_name",
            "subject_display",
            "order",
            "create_time",
            "success_time",
            "updated_at",
        ]

    def get_subject_display(self, obj):
        return obj.subject.get_display_name()
