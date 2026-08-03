from django.contrib import admin

from .models import LearningPlan


@admin.register(LearningPlan)
class LearningPlanAdmin(admin.ModelAdmin):
    list_display = ["id", "subject", "conversation", "target_agent", "state", "create_time", "success_time"]
    search_fields = ["subject__name", "subject__user__email", "target_agent"]
    list_filter = ["state", "target_agent", "subject__name"]
