from rest_framework import serializers

from .models import StudySession


class StudySessionSerializer(serializers.ModelSerializer):
    """学习时长记录序列化器。"""

    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = StudySession
        fields = [
            "id",
            "user",
            "subject",
            "subject_name",
            "activity_type",
            "date",
            "duration_minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "duration_minutes", "created_at", "updated_at"]


class AccumulateSerializer(serializers.Serializer):
    """POST /api/learning/study-sessions/accumulate/ 请求体。"""

    subject = serializers.CharField(max_length=100, help_text="学科 code, 如 data_structure")
    activity_type = serializers.ChoiceField(choices=StudySession.TYPE_CHOICES)
    minutes = serializers.IntegerField(default=1, min_value=1, max_value=60, help_text="累加分钟数, 默认 1")


# ============================================================
# 学习记录聚合接口的输出 serializer（只读, snake_case 对齐前端 types/learning.d.ts）
# ============================================================


class ExerciseRecordSerializer(serializers.Serializer):
    """习题记录行（聚合自 quiz_practiceanalysisrecord + quiz_examsession）。"""
    id = serializers.IntegerField(read_only=True)
    timestamp = serializers.CharField(read_only=True)
    question = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)
    correct = serializers.BooleanField(allow_null=True, read_only=True)
    knowledge_node = serializers.CharField(read_only=True)
    subject = serializers.CharField(read_only=True)


class ResourceHistoryItemSerializer(serializers.Serializer):
    """资源历史行（接入"打开书上报"前先返空 list，schema 留口）。"""
    id = serializers.IntegerField(read_only=True)
    timestamp = serializers.CharField(read_only=True)
    resource_name = serializers.CharField(read_only=True)
    type = serializers.ChoiceField(
        choices=["video", "article", "pdf", "interactive"], read_only=True
    )
    duration_min = serializers.IntegerField(read_only=True)
    subject = serializers.CharField(read_only=True)


class ReportSubjectSliceSerializer(serializers.Serializer):
    subject = serializers.CharField(read_only=True)
    minutes = serializers.IntegerField(read_only=True)


class ReportMasteryNodeSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    subject = serializers.CharField(read_only=True)
    mastery = serializers.IntegerField(read_only=True)


class ReportDailyCorrectnessSerializer(serializers.Serializer):
    day = serializers.CharField(read_only=True)
    correct = serializers.IntegerField(read_only=True)
    wrong = serializers.IntegerField(read_only=True)


class RichWeeklyReportSerializer(serializers.Serializer):
    """富周报（直接聚合 StudySession + PracticeAnalysisRecord + ExamSession + KnowledgeNode）。"""
    id = serializers.IntegerField(read_only=True)
    week_start = serializers.CharField(read_only=True)
    week_end = serializers.CharField(read_only=True)
    total_minutes = serializers.IntegerField(read_only=True)
    total_questions = serializers.IntegerField(read_only=True)
    total_correct = serializers.IntegerField(read_only=True)
    subjects_studied = serializers.ListField(child=serializers.CharField(), read_only=True)
    nodes_mastered_count = serializers.IntegerField(read_only=True)
    summary = serializers.CharField(read_only=True)
    daily_minutes = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    subject_distribution = ReportSubjectSliceSerializer(many=True, read_only=True)
    mastery_distribution = serializers.ListField(child=serializers.IntegerField(), read_only=True)
    daily_correctness = ReportDailyCorrectnessSerializer(many=True, read_only=True)
    top_nodes = ReportMasteryNodeSerializer(many=True, read_only=True)
    weak_nodes = ReportMasteryNodeSerializer(many=True, read_only=True)


# ============================================================
# 书架打开书事件 (Book / BookReadingSession)
# ============================================================


class BookSerializer(serializers.ModelSerializer):
    """书元数据 — 镜像前端 BOOKS_CONFIG, 后端是真理源. 字段 snake_case 对齐前端 types/learning.d.ts."""
    subject = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = None  # 实际是 learning.models.Book, 运行时设置, 避免循环 import
        fields = ["id", "code", "title", "author", "cover_url", "pdf_url", "chapters_total", "subject"]


# 真正的 BookSerializer 在 module import 末尾构造 (绕开 model -> serializer 反向循环)
def _build_book_serializer():
    from .models import Book
    class _BookSerializer(serializers.ModelSerializer):
        subject = serializers.CharField(source="subject.name", read_only=True)
        class Meta:
            model = Book
            fields = ["id", "code", "title", "author", "cover_url", "pdf_url", "chapters_total", "subject"]
    return _BookSerializer
BookSerializer = _build_book_serializer()
del _build_book_serializer


class BookReadingSessionSerializer(serializers.ModelSerializer):
    """一次"打开书"事件 (前端 ResourceHistoryItem 复用)."""
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    subject = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        from .models import BookReadingSession
        model = BookReadingSession
        fields = [
            "id", "book_id", "book_title", "subject",
            "opened_at", "last_heartbeat_at", "closed_at",
            "duration_min", "status",
        ]


class BookReadingSessionCreateSerializer(serializers.Serializer):
    """POST /api/learning/reading-sessions/open/ 请求体. 用 code 而不是 id 兼容前端 BOOKS_CONFIG."""
    book_code = serializers.CharField(max_length=64)
