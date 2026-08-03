from django.contrib import admin

from .models import StudySession


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "subject", "activity_type", "date", "duration_minutes", "updated_at"]
    list_filter = ["activity_type", "date", "subject__name"]
    search_fields = ["user__email", "subject__name"]
    readonly_fields = ["created_at", "updated_at"]
