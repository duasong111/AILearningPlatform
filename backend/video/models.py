from django.conf import settings
from django.db import models


class VideoCourseRecord(models.Model):
    """视频课程生成记录（含观看进度）。"""

    STATE_GENERATING = "generating"
    STATE_COMPLETE = "complete"
    STATE_ERROR = "error"
    STATE_CHOICES = [
        (STATE_GENERATING, "生成中"),
        (STATE_COMPLETE, "已完成"),
        (STATE_ERROR, "失败"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_course_records",
    )
    subject = models.ForeignKey(
        "users.Subject",
        on_delete=models.CASCADE,
        related_name="video_course_records",
    )
    task_id = models.CharField("任务 ID", max_length=64, unique=True)
    topic = models.CharField("主题", max_length=200)
    extra_prompt = models.TextField("额外提示词", blank=True, default="")
    knowledge_node_ids = models.JSONField("指定知识点", default=list, blank=True)

    state = models.CharField("状态", max_length=20, choices=STATE_CHOICES, default=STATE_GENERATING)
    course = models.JSONField("课程大纲", default=dict, blank=True)
    video_uuid = models.CharField("OpenMAIC uuid", max_length=64, blank=True, default="")
    iframe_url = models.URLField("iframe URL", blank=True, default="")
    error_message = models.TextField("错误信息", blank=True, default="")

    # 观看进度
    viewed_scene_ids = models.JSONField("已观看 scene id 列表", default=list, blank=True)
    last_scene_id = models.CharField("最近观看 scene id", max_length=64, blank=True, default="")
    watched_seconds = models.PositiveIntegerField("累计观看秒数", default=0)
    completion_ratio = models.FloatField("完成度 0-1", default=0.0)
    completed = models.BooleanField("是否完整看完", default=False)

    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "视频课程记录"
        verbose_name_plural = "视频课程记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"video:{self.task_id} ({self.user_id}) - {self.topic}"
