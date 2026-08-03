"""学习记录接口。

POST /api/learning/study-sessions/accumulate/
    前端每 1 分钟调用一次, 累加学习时长。
    Body: {"subject": "data_structure", "activity_type": "chat", "minutes": 1}

GET /api/learning/study-sessions/
    查询学习记录, 支持按学科、活动类型、日期范围筛选。
    Query: ?subject=<code>&activity_type=<type>&start=2026-01-01&end=2026-01-31

GET /api/learning/study-sessions/summary/
    按天聚合统计, 返回每天的各类型时长。
    Query: ?subject=<code>&start=2026-01-01&end=2026-01-31

GET /api/learning/exercises/
    习题记录聚合(刷题 + 综合测评) —— 真数据接口

GET /api/learning/resource-history/
    资源历史聚合 —— 当前返空 list(等待打开书/视频上报接通)

GET /api/learning/reports/
    富周报列表(最近 12 周) —— 真数据

GET /api/learning/reports/<int:id>/
    取单周富周报(按 id=week_start 距 epoch 天数) —— 真数据
"""

from datetime import date, timedelta

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Subject

from . import aggregates
from .models import Book, BookReadingSession, StudySession
from .serializers import (
    AccumulateSerializer,
    BookReadingSessionCreateSerializer,
    BookReadingSessionSerializer,
    BookSerializer,
    ExerciseRecordSerializer,
    ResourceHistoryItemSerializer,
    RichWeeklyReportSerializer,
    StudySessionSerializer,
)


class StudySessionViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """学习时长记录 ViewSet。"""

    serializer_class = StudySessionSerializer
    permission_classes = [IsAuthenticated]
    queryset = StudySession.objects.all()

    def get_queryset(self):
        qs = StudySession.objects.filter(user=self.request.user).select_related("subject")

        # 按学科 code 过滤
        subject_code = self.request.query_params.get("subject")
        if subject_code:
            qs = qs.filter(subject__name=subject_code)

        # 按活动类型过滤
        activity_type = self.request.query_params.get("activity_type")
        if activity_type:
            qs = qs.filter(activity_type=activity_type)

        # 按日期范围过滤
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)

        return qs.order_by("-date", "activity_type")

    @action(detail=False, methods=["post"], url_path="accumulate")
    def accumulate(self, request):
        """累加学习时长。

        前端每分钟调用一次, 按 (user, subject, date, activity_type) 聚合。
        """
        serializer = AccumulateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            subject = Subject.objects.get(user=request.user, name=data["subject"])
        except Subject.DoesNotExist:
            raise ValidationError({"subject": f"学科 '{data['subject']}' 不存在"})

        today = timezone.now().date()
        session, created = StudySession.objects.get_or_create(
            user=request.user,
            subject=subject,
            date=today,
            activity_type=data["activity_type"],
            defaults={"duration_minutes": data["minutes"]},
        )
        if not created:
            session.duration_minutes += data["minutes"]
            session.save(update_fields=["duration_minutes", "updated_at"])

        return Response(
            StudySessionSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """按天聚合学习时长。

        返回格式:
        [
            {"date": "2026-01-15", "activity_type": "chat", "total_minutes": 30},
            {"date": "2026-01-15", "activity_type": "video", "total_minutes": 45},
            ...
        ]
        """
        qs = self.get_queryset()
        aggregated = (
            qs.values("date", "activity_type")
            .annotate(total_minutes=Sum("duration_minutes"))
            .order_by("-date", "activity_type")
        )
        return Response(list(aggregated))

    @action(detail=False, methods=["get"], url_path="total")
    def total(self, request):
        """统计指定日期范围内的总学习时长 (按活动类型分)。

        返回格式:
        {
            "total_minutes": 300,
            "by_type": {"chat": 60, "reading": 90, "video": 80, "quiz": 40, "exam": 30}
        }
        """
        qs = self.get_queryset()
        by_type = {}
        total = 0
        for row in qs.values("activity_type").annotate(total=Sum("duration_minutes")):
            by_type[row["activity_type"]] = row["total"]
            total += row["total"]
        return Response({"total_minutes": total, "by_type": by_type})


# ============================================================
# 学习记录聚合 —— 真数据接口 (不动 StudySessionViewSet)
#   三个 viewset 都只读 GET list, 内部调 aggregates.* 产出前端要的 shape.
#   queryset 故意空 —— 数据来自聚合模块, 不走 ORM 模型 viewset.
# ============================================================


class ExerciseRecordViewSet(viewsets.GenericViewSet):
    """GET /api/learning/exercises/

    聚合 quiz_practiceanalysisrecord + quiz_examsession → ExerciseRecord[]
    字段 snake_case 对齐前端 `types/learning.d.ts: ExerciseRecord`
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExerciseRecordSerializer
    queryset = StudySession.objects.none()  # 占位, 不参与 ORM

    def list(self, request, *args, **kwargs):
        subject_code = request.query_params.get("subject")
        correct_raw = request.query_params.get("correct")
        correct = None
        if correct_raw is not None:
            correct = correct_raw.lower() in {"1", "true", "yes"}

        start = _parse_date(request.query_params.get("start"))
        end = _parse_date(request.query_params.get("end"))

        try:
            limit = int(request.query_params.get("limit", 100))
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 500))

        result = aggregates.compute_exercise_records(
            request.user,
            subject_code=subject_code,
            correct=correct,
            start=start,
            end=end,
            limit=limit,
        )
        serializer = ExerciseRecordSerializer(result["items"], many=True)
        return Response({"items": serializer.data, "total": result["total"]})


class ResourceHistoryViewSet(viewsets.GenericViewSet):
    """GET /api/learning/resource-history/

    资源历史行 —— 主路径聚合 BookReadingSession (明细, 真有"哪本书"),
    兜底聚合 StudySession(activity_type='reading') (聚合, 模糊到"学科·阅读").

    字段 snake_case 对齐前端 `types/learning.d.ts: ResourceHistoryItem`.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceHistoryItemSerializer
    queryset = StudySession.objects.none()

    def list(self, request, *args, **kwargs):
        items: list[dict] = []
        seen_ids: set[int] = set()  # BookReadingSession.id 去重

        # 主路径: BookReadingSession (一次打开 = 1 行明细, 真有"哪本书")
        for s in (
            BookReadingSession.objects
            .filter(user=request.user)
            .select_related("book", "subject")
            .order_by("-opened_at")[:100]
        ):
            seen_ids.add(s.id)
            items.append({
                "id": s.id,
                "timestamp": s.opened_at.isoformat(),
                "resource_name": s.book.title,
                "type": "pdf",  # book 都是 PDF
                "duration_min": s.duration_min,
                "subject": s.subject.name,
            })

        # 兜底: 老的 StudySession(reading) 仍展示 (按 (user, subject, date) 聚合)
        for s in (
            StudySession.objects
            .filter(user=request.user, activity_type=StudySession.TYPE_READING)
            .select_related("subject")
            .order_by("-created_at")[:100]
        ):
            # StudySession 跟 BookReadingSession 数字 id 独立, 不会冲突
            items.append({
                "id": f"sess_{s.id}",  # 加前缀避免跟 BookReadingSession.id 冲突
                "timestamp": s.created_at.isoformat(),
                "resource_name": f"{s.subject.get_display_name() or s.subject.name} · 阅读",
                "type": "pdf",
                "duration_min": s.duration_minutes,
                "subject": s.subject.name,
            })

        # 按时间倒序, 截 100
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        return Response({"items": items[:100]})


class WeeklyReportViewSet(viewsets.GenericViewSet):
    """GET /api/learning/reports/<int:id>/

    id = week_start 距 epoch days (周一), 用周一日期定位唯一一周.

    list 端点: 最近 12 周 RichWeeklyReport[]
    detail 端点: 单周 RichWeeklyReport
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RichWeeklyReportSerializer
    queryset = StudySession.objects.none()

    def list(self, request, *args, **kwargs):
        reports = aggregates.compute_weekly_reports_list(request.user, max_weeks=12)
        serializer = RichWeeklyReportSerializer(reports, many=True)
        return Response({"items": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        # 兼容前端 `${ENDPOINTS.REPORTS}${id}/`, id 是 week_start 距 epoch days
        week_id = kwargs.get(self.lookup_field or "pk")
        try:
            week_id = int(week_id)
        except (TypeError, ValueError):
            return Response({"error": "invalid week id"}, status=status.HTTP_400_BAD_REQUEST)
        week_start = date(1970, 1, 1) + timedelta(days=week_id)
        report = aggregates.compute_rich_report(request.user, week_start=week_start)
        serializer = RichWeeklyReportSerializer(report)
        return Response(serializer.data)


def _parse_date(raw: str | None) -> date | None:
    """前端传 ISO date 字符串 (YYYY-MM-DD), 这里宽松解析."""
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


# ============================================================
# 书架打开书事件 (BookViewSet + ReadingSessionViewSet)
#   不动 StudySession / StudySessionViewSet / 已有聚合 viewset.
# ============================================================


class BookViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """GET /api/learning/books/  +  /api/learning/books/<id>/

    书元数据列表, 当前后端是镜像, 前端 BOOKS_CONFIG 仍为真理源.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BookSerializer
    queryset = Book.objects.select_related("subject").all()

    def get_queryset(self):
        qs = super().get_queryset()
        subject_code = self.request.query_params.get("subject")
        if subject_code:
            qs = qs.filter(subject__name=subject_code)
        return qs.order_by("code")


class ReadingSessionViewSet(viewsets.GenericViewSet):
    """一次"打开书"事件的 CRUD viewset.

    GET  /api/learning/reading-sessions/                              列表 (最近 100)
    POST /api/learning/reading-sessions/open/     body: {book_code}    打开书 -> 建 1 行
    POST /api/learning/reading-sessions/heartbeat/ body: {reading_session_id} 累加 1 分钟
    POST /api/learning/reading-sessions/close/   body: {reading_session_id} 关闭
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BookReadingSessionSerializer
    queryset = BookReadingSession.objects.none()

    def list(self, request, *args, **kwargs):
        sessions = (
            BookReadingSession.objects
            .filter(user=request.user)
            .select_related("book", "subject")
            .order_by("-opened_at")[:100]
        )
        serializer = BookReadingSessionSerializer(sessions, many=True)
        return Response({"items": serializer.data})

    @action(detail=False, methods=["post"], url_path="open")
    def open(self, request):
        serializer = BookReadingSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = get_object_or_404(Book, code=serializer.validated_data["book_code"])
        session = BookReadingSession.objects.create(
            user=request.user,
            book=book,
            subject=book.subject,
        )
        return Response(
            BookReadingSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="heartbeat")
    def heartbeat(self, request):
        rid = request.data.get("reading_session_id")
        if not rid:
            return Response(
                {"error": "reading_session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session = get_object_or_404(BookReadingSession, id=rid, user=request.user)
        session.duration_min = (session.duration_min or 0) + 1
        session.last_heartbeat_at = timezone.now()
        session.save(update_fields=["duration_min", "last_heartbeat_at"])
        return Response(BookReadingSessionSerializer(session).data)

    @action(detail=False, methods=["post"], url_path="close")
    def close(self, request):
        rid = request.data.get("reading_session_id")
        if not rid:
            return Response(
                {"error": "reading_session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session = get_object_or_404(BookReadingSession, id=rid, user=request.user)
        session.status = BookReadingSession.STATUS_CLOSED
        session.closed_at = timezone.now()
        session.save(update_fields=["status", "closed_at"])
        return Response(BookReadingSessionSerializer(session).data)
