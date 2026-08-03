"""Quiz / Practice HTTP 端点 URL 注册。"""
from django.urls import path

from .quiz_views import (
    practice_analyze,
    practice_result,
    practice_state,
    quiz_generate,
    quiz_result,
    quiz_state,
)

urlpatterns = [
    path("quiz/generate/", quiz_generate),
    path("quiz/<str:task_id>/state/", quiz_state),
    path("quiz/<str:task_id>/result/", quiz_result),
    path("practice/analyze/", practice_analyze),
    path("practice/<str:task_id>/state/", practice_state),
    path("practice/<str:task_id>/result/", practice_result),
]
