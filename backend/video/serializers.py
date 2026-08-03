from rest_framework import serializers

from .models import VideoCourseRecord


class VideoCourseRecordSerializer(serializers.ModelSerializer):
    subject_id = serializers.IntegerField(source="subject.id", read_only=True)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_display = serializers.SerializerMethodField()
    scene_count = serializers.SerializerMethodField()
    viewed_scene_count = serializers.SerializerMethodField()

    class Meta:
        model = VideoCourseRecord
        fields = [
            "id", "task_id",
            "subject_id", "subject_name", "subject_display",
            "topic", "extra_prompt", "knowledge_node_ids",
            "state", "course", "video_uuid", "iframe_url", "error_message",
            "viewed_scene_ids", "last_scene_id", "watched_seconds",
            "completion_ratio", "completed", "scene_count", "viewed_scene_count",
            "created_at", "completed_at", "updated_at",
        ]
        read_only_fields = fields

    def get_subject_display(self, obj):
        return obj.subject.get_display_name()

    def get_scene_count(self, obj):
        outlines = (obj.course or {}).get("outlines") or []
        return len(outlines)

    def get_viewed_scene_count(self, obj):
        return len(obj.viewed_scene_ids or [])
