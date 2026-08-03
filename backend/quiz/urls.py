from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ExamSessionCreateView,
    ExamSessionDetailView,
    ExamSessionListView,
    ExamSessionSubmitView,
    PracticeAnalysisRecordViewSet,
    PracticeAnalyzeView,
    PracticeSessionDetailView,
    PracticeTaskStatusView,
    QuizAutoGenerateView,
    QuizGenerationRecordViewSet,
    QuizGenerateView,
    QuizTaskStatusView,
)
from .practice_queue import ActiveQuizQueueView, MarkAnsweredView

router = DefaultRouter()
router.register(r"quizzes", QuizGenerationRecordViewSet, basename="quiz-record")
router.register(r"practice-analyses", PracticeAnalysisRecordViewSet, basename="practice-analysis-record")

urlpatterns = [
    path("", include(router.urls)),
    path("quiz/generate/", QuizGenerateView.as_view(), name="quiz-generate"),
    path("quiz/auto-generate/", QuizAutoGenerateView.as_view(), name="quiz-auto-generate"),
    path("quiz/active-queue/", ActiveQuizQueueView.as_view(), name="quiz-active-queue"),
    path("quiz/mark-answered/", MarkAnsweredView.as_view(), name="quiz-mark-answered"),
    path("quiz/tasks/<str:task_id>/", QuizTaskStatusView.as_view(), name="quiz-task-status"),
    path("practice/analyze/", PracticeAnalyzeView.as_view(), name="practice-analyze"),
    path("practice/tasks/<str:task_id>/", PracticeTaskStatusView.as_view(), name="practice-task-status"),
    path("exam/sessions/", ExamSessionCreateView.as_view(), name="exam-session-create"),
    path("exam/sessions/<int:pk>/", ExamSessionDetailView.as_view(), name="exam-session-detail"),
    path("exam/sessions/<int:pk>/submit/", ExamSessionSubmitView.as_view(), name="exam-session-submit"),
    path("exam/history/", ExamSessionListView.as_view(), name="exam-history"),
    path("practice/sessions/<int:pk>/", PracticeSessionDetailView.as_view(), name="practice-session-detail"),
]
