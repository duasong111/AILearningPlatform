from django.conf import settings
from django.db import models


class QuizGenerationRecord(models.Model):
    """题目生成记录（需要持久化）。"""

    STATE_GENERATING = "generating"
    STATE_COMPLETE = "complete"
    STATE_ERROR = "error"
    STATE_CHOICES = [
        (STATE_GENERATING, "生成中"),
        (STATE_COMPLETE, "已完成"),
        (STATE_ERROR, "失败"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_generation_records")
    subject = models.ForeignKey("users.Subject", on_delete=models.CASCADE, related_name="quiz_generation_records")
    task_id = models.CharField("任务 ID", max_length=64, unique=True)
    extra_prompt = models.TextField("额外提示词", blank=True, default="")
    requested_count = models.PositiveIntegerField("请求题目数量", null=True, blank=True)
    node_id = models.CharField("知识点 ID", max_length=32, blank=True, default="")
    node_name = models.CharField("知识点名称", max_length=100, blank=True, default="")
    plan = models.ForeignKey(
        "plan.LearningPlan",
        on_delete=models.SET_NULL,
        related_name="quiz_generation_records",
        null=True,
        blank=True,
    )
    state = models.CharField("状态", max_length=20, choices=STATE_CHOICES, default=STATE_GENERATING)
    questions = models.JSONField("题目列表", default=list, blank=True)
    error_message = models.TextField("错误信息", blank=True, default="")
    # 题级作答进度: { "0": {"answered": true, "correct": true}, ... } — key 是 batch 内 idx (str)
    item_progress = models.JSONField("题级作答进度", default=dict, blank=True)
    # 是否激活: 已全答完或被显式停用的不再出现在 active-queue
    is_active = models.BooleanField("激活中", default=True)
    # 来源: normal / plan — active-queue 排序时 plan 优先
    source = models.CharField("来源", max_length=16, default="normal")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "题目生成记录"
        verbose_name_plural = "题目生成记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"quiz:{self.task_id} ({self.user_id})"


class PracticeAnalysisRecord(models.Model):
    """答题解析记录，仅 with_answer 模式持久化。"""

    MODE_WITH_ANSWER = "with_answer"
    MODE_CHOICES = [
        (MODE_WITH_ANSWER, "带答案解析"),
    ]

    STATE_GENERATING = "generating"
    STATE_COMPLETE = "complete"
    STATE_ERROR = "error"
    STATE_CHOICES = [
        (STATE_GENERATING, "生成中"),
        (STATE_COMPLETE, "已完成"),
        (STATE_ERROR, "失败"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_analysis_records")
    subject = models.ForeignKey("users.Subject", on_delete=models.CASCADE, related_name="practice_analysis_records")
    quiz_generation = models.ForeignKey(
        QuizGenerationRecord,
        on_delete=models.SET_NULL,
        related_name="practice_analysis_records",
        null=True,
        blank=True,
    )
    task_id = models.CharField("任务 ID", max_length=64, unique=True)
    quiz_task_id = models.CharField("题目任务 ID", max_length=64)
    question_index = models.PositiveIntegerField("题目索引", default=0)
    mode = models.CharField("模式", max_length=20, choices=MODE_CHOICES, default=MODE_WITH_ANSWER)
    user_answer = models.TextField("用户回答", null=True, blank=True)
    state = models.CharField("状态", max_length=20, choices=STATE_CHOICES, default=STATE_GENERATING)
    analysis = models.JSONField("解析结果", default=dict, blank=True)
    error_message = models.TextField("错误信息", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "答题解析记录"
        verbose_name_plural = "答题解析记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"practice:{self.task_id} ({self.user_id})"


class ExamSession(models.Model):
    """基于 Dify 工作流的测评会话。"""

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "进行中"),
        (STATUS_COMPLETED, "已完成"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_sessions")
    search_query = models.CharField("考察范围", max_length=200)
    mcq_count = models.PositiveIntegerField("选择题数量", default=0)
    qa_count = models.PositiveIntegerField("问答题数量", default=0)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    multiple_choice = models.JSONField("选择题列表", default=list)
    essay = models.JSONField("问答题列表", default=list)
    mcq_answers = models.JSONField("选择题答案", default=dict)   # {str(id): "A"/"B"/...}
    essay_answers = models.JSONField("问答题答案", default=dict)  # {str(id): 文本}
    mcq_score = models.FloatField("选择题得分率", null=True, blank=True)
    analysis = models.JSONField("AI 分析结果", default=dict, blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    completed_at = models.DateTimeField("完成时间", null=True, blank=True)

    class Meta:
        verbose_name = "测评会话"
        verbose_name_plural = "测评会话"
        ordering = ["-created_at"]

    @property
    def mcq_correct(self) -> int:
        if not self.mcq_answers or not self.multiple_choice:
            return 0
        return sum(
            1 for q in self.multiple_choice
            if self.mcq_answers.get(str(q["id"]), "").upper() == q.get("answer", "").upper()
        )

    def __str__(self):
        return f"exam:{self.id} ({self.user_id}) {self.search_query}"


class PracticeSession(models.Model):
    """代码实践会话 —— 两阶段 LLM 生成（需求→大纲→交互 HTML 场景）。"""

    STATUS_GENERATING = "generating"
    STATUS_READY = "ready"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_GENERATING, "生成中"),
        (STATUS_READY, "已完成"),
        (STATUS_ERROR, "失败"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_sessions")
    search_query = models.CharField("实践主题", max_length=200)
    language = models.CharField("编程语言", max_length=20, default="python")
    scene_count = models.PositiveIntegerField("场景数量", default=3)
    outlines = models.JSONField("大纲数据", default=list)
    scenes = models.JSONField("场景列表", default=list)  # [{title, html, widgetType, widgetConfig}]
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default=STATUS_GENERATING)
    error_message = models.TextField("错误信息", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "实践会话"
        verbose_name_plural = "实践会话"
        ordering = ["-created_at"]

    def __str__(self):
        return f"practice:{self.id} ({self.user_id}) {self.search_query}"
