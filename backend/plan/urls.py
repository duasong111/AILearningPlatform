from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LearningPlanViewSet

router = DefaultRouter()
router.register(r"plans", LearningPlanViewSet, basename="learning-plan")

urlpatterns = [
    path("", include(router.urls)),
]
