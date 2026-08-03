"""学习记录模型。

StudySession:
    记录用户在某学科下的学习时长, 按活动类型分类。
    前端每 1 分钟 POST 一次 /api/learning/study-sessions/accumulate/ → duration_minutes += 1

    查询: GET /api/learning/study-sessions/?subject=<code>&start=<date>&end=<date>
    聚合: 按天/类型汇总, 供前端学习记录页展示。
"""

from django.db import models


class StudySession(models.Model):
    """学习时长记录 (按 用户 × 学科 × 日期 × 活动类型 聚合)。"""

    TYPE_CHAT = "chat"
    TYPE_READING = "reading"
    TYPE_VIDEO = "video"
    TYPE_QUIZ = "quiz"
    TYPE_EXAM = "exam"
    TYPE_CHOICES = [
        (TYPE_CHAT, "对话"),
        (TYPE_READING, "看书"),
        (TYPE_VIDEO, "视频"),
        (TYPE_QUIZ, "刷题"),
        (TYPE_EXAM, "评测"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    subject = models.ForeignKey(
        "users.Subject",
        on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    activity_type = models.CharField("活动类型", max_length=20, choices=TYPE_CHOICES)
    date = models.DateField("日期")
    duration_minutes = models.PositiveIntegerField("学习时长(分钟)", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "学习时长记录"
        verbose_name_plural = "学习时长记录"
        # 同一用户/学科/日期/类型 只有一条记录, accumulate 时 get_or_create
        unique_together = ["user", "subject", "date", "activity_type"]
        ordering = ["-date", "activity_type"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["subject", "date"]),
        ]

    def __str__(self):
        return f"{self.user.email} {self.subject.name} {self.date} {self.activity_type} {self.duration_minutes}min"


class Book(models.Model):
    """书 —— 跟前端 BOOKS_CONFIG 对齐的元数据.

    `code` 是稳定唯一 key, 对应前端 `web/src/data/books.ts: BOOKS_CONFIG[].id`.
    `subject` 直接 FK 到 `users.Subject`, 避免维护 M2M 中间表.
    当前前端 BOOKS_CONFIG 仍为真理源, 后端这张表是镜像, 后续前端切走后端 Book
    为真理后这里就是真源.
    """

    code = models.CharField("书 code (与 BOOKS_CONFIG.id 对齐)", max_length=64, unique=True)
    title = models.CharField("书名", max_length=200)
    author = models.CharField("作者", max_length=200, blank=True, default="")
    cover_url = models.URLField("封面", max_length=500, blank=True, default="")
    pdf_url = models.URLField("PDF 链接 (前端会再做 cosUrl 替换)", max_length=500, blank=True, default="")
    chapters_total = models.PositiveIntegerField("章节数", default=0)
    subject = models.ForeignKey(
        "users.Subject",
        on_delete=models.CASCADE,
        related_name="books",
        help_text="所属学科 (跟 Subject.SUBJECT_CHOICES 对齐)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "书"
        verbose_name_plural = "书"
        ordering = ["code"]

    def __str__(self):
        return f"Book({self.code}, {self.title})"


class BookReadingSession(models.Model):
    """一次"打开书"事件 = 一行明细记录.

    每点开一次书 = 1 行, 持续累加 `duration_min`; 关书时 `status='closed'`.
    资源历史 tab 直接 group by 这次会话.
    """

    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "打开中"),
        (STATUS_CLOSED, "已关闭"),
    ]

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="book_reading_sessions"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="reading_sessions"
    )
    subject = models.ForeignKey(
        "users.Subject", on_delete=models.CASCADE, related_name="book_reading_sessions"
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    duration_min = models.PositiveIntegerField("累计时长(分钟)", default=0)
    status = models.CharField("状态", max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    class Meta:
        verbose_name = "书阅读会话"
        verbose_name_plural = "书阅读会话"
        indexes = [
            models.Index(fields=["user", "-opened_at"]),
            models.Index(fields=["book", "-opened_at"]),
        ]
        ordering = ["-opened_at"]

    def __str__(self):
        return f"ReadingSession(user={self.user_id}, book={self.book_id}, {self.status})"
