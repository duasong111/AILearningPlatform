from rest_framework import serializers

from .models import ExamSession, PracticeAnalysisRecord, PracticeSession, QuizGenerationRecord


class QuizGenerationRecordSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source="subject.id", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_display = serializers.SerializerMethodField()
    actual_count = serializers.SerializerMethodField()
    plan_id = serializers.IntegerField(source="plan.id", read_only=True, allow_null=True)

    class Meta:
        model = QuizGenerationRecord
        fields = [
            "id", "task_id", "subject_id", "subject_name", "subject_display",
            "extra_prompt", "requested_count", "actual_count",
            "node_id", "node_name", "plan_id",
            "state", "questions", "error_message",
            "created_at", "completed_at", "updated_at",
        ]
        read_only_fields = fields

    def get_subject_display(self, obj):
        return obj.subject.get_display_name()

    def get_actual_count(self, obj):
        return len(obj.questions or [])


class PracticeAnalysisRecordSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source="subject.id", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_display = serializers.SerializerMethodField()
    quiz_generation_id = serializers.IntegerField(source="quiz_generation.id", read_only=True)

    class Meta:
        model = PracticeAnalysisRecord
        fields = [
            "id", "task_id", "quiz_task_id", "quiz_generation_id",
            "subject_id", "subject_name", "subject_display",
            "question_index", "mode", "user_answer",
            "state", "analysis", "error_message",
            "created_at", "completed_at", "updated_at",
        ]
        read_only_fields = fields

    def get_subject_display(self, obj):
        return obj.subject.get_display_name()


class ExamSessionSerializer(serializers.ModelSerializer):
    mcq_correct = serializers.SerializerMethodField()

    class Meta:
        model = ExamSession
        fields = [
            "id", "search_query", "mcq_count", "qa_count", "status",
            "multiple_choice", "essay", "mcq_answers", "essay_answers",
            "mcq_score", "mcq_correct", "analysis", "created_at", "completed_at",
        ]
        read_only_fields = [
            "id", "status", "multiple_choice", "essay",
            "mcq_score", "mcq_correct", "analysis", "created_at", "completed_at",
        ]

    def get_mcq_correct(self, obj):
        return obj.mcq_correct


class PracticeSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PracticeSession
        fields = [
            "id", "search_query", "language", "scene_count",
            "outlines", "scenes", "status", "error_message",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "outlines", "scenes", "error_message",
            "created_at", "updated_at",
        ]
