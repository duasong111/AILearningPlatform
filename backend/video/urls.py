from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    VideoCourseGenerateView,
    VideoCourseProgressView,
    VideoCourseRecordViewSet,
    VideoCourseTaskStatusView,
)

router = DefaultRouter()
router.register(r"video-courses", VideoCourseRecordViewSet, basename="video-course")

urlpatterns = [
    path("", include(router.urls)),
    path("video-course/generate/", VideoCourseGenerateView.as_view(), name="video-course-generate"),
    path("video-course/tasks/<str:task_id>/", VideoCourseTaskStatusView.as_view(), name="video-course-task-status"),
    path("video-course/<int:record_id>/progress/", VideoCourseProgressView.as_view(), name="video-course-progress"),
]
