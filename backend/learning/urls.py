from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StudySessionViewSet,       # 已有 — 不动
    ExerciseRecordViewSet,     # 上一个 plan 加的 — 不动
    ResourceHistoryViewSet,    # 已有 + 本次 plan 改写 — 不动 viewset 本身
    WeeklyReportViewSet,       # 上一个 plan 加的 — 不动
    BookViewSet,               # 本次 plan 新加
    ReadingSessionViewSet,      # 本次 plan 新加
)

router = DefaultRouter()
router.register(r"study-sessions", StudySessionViewSet, basename="study-session")        # 已有
router.register(r"exercises", ExerciseRecordViewSet, basename="exercise-record")          # 已有
router.register(r"resource-history", ResourceHistoryViewSet, basename="resource-history") # 已有
router.register(r"reports", WeeklyReportViewSet, basename="weekly-report")               # 已有
router.register(r"books", BookViewSet, basename="book")                                    # 新
router.register(r"reading-sessions", ReadingSessionViewSet, basename="reading-session")   # 新

urlpatterns = [
    path("learning/", include(router.urls)),
]
