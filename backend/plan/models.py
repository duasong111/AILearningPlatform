"""Plan models.

设计原则（节点 × 步骤 粒度）：
    一条 LearningPlan = 一个 (节点 × 步骤) 的完整执行记录。
    数据结构学科 54 节点 × 5 步骤 = 270 条 plan，每条都已包含所有必要字段。

    不再使用 LearningPlanItem（已合并到 LearningPlan）。
"""

from django.db import models
from django.utils import timezone

from users.models import Conversation


def expected_minutes_for_difficulty(difficulty: int) -> int:
    """节点 difficulty 线性映射为预计耗时（分钟）。

    difficulty=1 → 30min
    difficulty=5 → 150min
    中间值线性插值
    """
    d = max(1, min(5, int(difficulty or 1)))
    return 30 * d


class LearningPlan(models.Model):
    """学习计划（一个节点 × 一个步骤 = 一条记录）。

    字段来源：
      - 调度层：subject, conversation, target_agent, state, expected_completion_time
      - 节点信息：node_id, node_name, node_type, order, difficulty
      - 步骤信息：action_type, expected_minutes
      - 执行层：completed, actual_completion_time, success_time
    """

    # ── 状态机 ──────────────────────────────
    STATE_PENDING = "pending"
    STATE_RUNNING = "running"
    STATE_SUCCESS = "success"
    STATE_FAILED = "failed"
    STATE_SKIPPED = "skipped"
    STATE_CHOICES = [
        (STATE_PENDING, "待执行"),
        (STATE_RUNNING, "执行中"),
        (STATE_SUCCESS, "已完成"),
        (STATE_FAILED, "已失败"),
        (STATE_SKIPPED, "已跳过"),
    ]

    # ── 整体难度（计划层）──
    DIFFICULTY_LOW = "low"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HIGH = "high"
    DIFFICULTY_CHOICES = [
        (DIFFICULTY_LOW, "低"),
        (DIFFICULTY_MEDIUM, "中"),
        (DIFFICULTY_HIGH, "高"),
    ]

    # ── 步骤类型（item 提升上来）──
    ACTION_STUDY = "study"
    ACTION_PRACTICE = "practice"
    ACTION_CHAT = "chat"
    ACTION_VIDEO = "video"
    ACTION_CHOICES = [
        (ACTION_STUDY, "阅读学习"),
        (ACTION_PRACTICE, "刷题巩固"),
        (ACTION_CHAT, "对话学习"),
        (ACTION_VIDEO, "视频学习"),
    ]

    # ── 学科/对话/路由 ──
    subject = models.ForeignKey("users.Subject", on_delete=models.CASCADE, related_name="learning_plans")
    conversation = models.ForeignKey(
        "users.Conversation",
        on_delete=models.SET_NULL,
        related_name="learning_plans",
        null=True,
        blank=True,
    )
    target_agent = models.CharField("目标 agent", max_length=20, choices=Conversation.AGENT_CHOICES)

    # ── 节点信息（item 提升上来）──
    node_id = models.CharField("知识点 ID", max_length=32, db_index=True)
    node_name = models.CharField("知识点名称", max_length=100, db_index=True)
    node_type = models.CharField("知识点类型", max_length=32, blank=True, default="")
    order = models.PositiveIntegerField("计划项顺序", default=0, db_index=True)
    action_type = models.CharField(
        "推荐动作", max_length=20, choices=ACTION_CHOICES, default=ACTION_STUDY,
    )

    # ── 难度/记忆 ──
    difficulty = models.PositiveSmallIntegerField("节点难度", default=1, db_index=True)
    plan_difficulty = models.CharField(
        "计划难度",
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_MEDIUM,
    )
    memory = models.JSONField("计划记忆", default=dict, blank=True)

    # ── 状态机字段 ──
    state = models.CharField(
        "计划状态", max_length=20, choices=STATE_CHOICES, default=STATE_PENDING, db_index=True,
    )
    completed = models.BooleanField("是否完成", default=False)

    # ── 时间字段 ──
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    success_time = models.DateTimeField("完成时间", null=True, blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    expected_completion_time = models.DateTimeField(
        "预计完成时间", null=True, blank=True, db_index=True,
    )
    expected_minutes = models.PositiveIntegerField("预计耗时（分钟）", default=30)
    actual_completion_time = models.DateTimeField("实际完成时间", null=True, blank=True)

    class Meta:
        verbose_name = "学习计划"
        verbose_name_plural = "学习计划"
        ordering = ["expected_completion_time", "id"]
        indexes = [
            models.Index(fields=["subject", "state"]),
            models.Index(fields=["subject", "node_name"]),
            models.Index(fields=["subject", "target_agent"]),
        ]

    def __str__(self):
        return (
            f"{self.subject.name}#{self.id} "
            f"{self.node_name}({self.action_type}, {self.state})"
        )

    def save(self, *args, **kwargs):
        # 状态联动：success 自动写时间，completed 同步
        if self.state == self.STATE_SUCCESS:
            now = timezone.now()
            if self.actual_completion_time is None:
                self.actual_completion_time = now
            if self.success_time is None:
                self.success_time = now
            self.completed = True
        elif self.state in {self.STATE_PENDING, self.STATE_RUNNING, self.STATE_FAILED, self.STATE_SKIPPED}:
            if self.state != self.STATE_SUCCESS:
                self.completed = False
                # 切回非 success 时清掉时间戳（避免脏数据）
                if self.state != self.STATE_RUNNING and self.actual_completion_time is not None:
                    self.actual_completion_time = None
                if self.state != self.STATE_RUNNING and self.success_time is not None:
                    self.success_time = None
        super().save(*args, **kwargs)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "conversation_id": self.conversation_id,
            "target_agent": self.target_agent,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "order": self.order,
            "action_type": self.action_type,
            "difficulty": self.difficulty,
            "plan_difficulty": self.plan_difficulty,
            "memory": self.memory or {},
            "state": self.state,
            "completed": self.completed,
            "expected_minutes": self.expected_minutes,
            "expected_completion_time": (
                self.expected_completion_time.isoformat() if self.expected_completion_time else None
            ),
            "actual_completion_time": (
                self.actual_completion_time.isoformat() if self.actual_completion_time else None
            ),
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "success_time": self.success_time.isoformat() if self.success_time else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
