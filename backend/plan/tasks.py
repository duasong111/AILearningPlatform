"""Plan app 的 Celery 任务。

generate_initial_plans:
    画像完成时由 signal 触发，整合规则层 + LLM 层生成个性化学习计划。
    规则层 (plan_templates.build_personalized_plan_spec) 做步骤筛选和时间压缩，
    LLM 层 (plan_adjuster.adjust_plan_order) 做兴趣优先重排序。
"""

import asyncio
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def _build_profile_summary(profile) -> dict:
    """从 UserProfile 构造画像摘要 (与 signals._build_profile_summary 一致)。"""
    if profile is None:
        return {}
    common_mistakes = profile.common_mistakes or []
    interest_direction = profile.interest_direction or []
    return {
        "learning_goal": {
            "goal": getattr(profile, "course", None),
            "priority": int(profile.learning_goal_score or 0),
        },
        "knowledge_base": {
            "level": int(profile.knowledge_base or 0),
            "strong_areas": [],
            "weak_areas": list(common_mistakes),
            "recommended_courses": [profile.course] if profile.course else [],
        },
        "cognitive_style": {
            "description": "",
            "score": int(profile.cognitive_style or 0),
        },
        "available_time": int(profile.available_time or 0),
        "interest_direction": list(interest_direction),
    }


async def _generate_plans_async(subject_id: int, profile_id: int) -> int:
    """异步生成个性化学习计划，返回创建数量。"""
    from users.models import Subject, UserProfile
    from plan.models import LearningPlan
    from plan.plan_templates import build_personalized_plan_spec
    from plan.plan_adjuster import adjust_plan_order

    from asgiref.sync import sync_to_async

    subject = await sync_to_async(Subject.objects.get)(id=subject_id)
    profile = await sync_to_async(UserProfile.objects.get)(id=profile_id)
    profile_summary = _build_profile_summary(profile)

    # 1. 规则层: 步骤筛选 + 时间压缩
    specs = build_personalized_plan_spec(subject.name, profile_summary)
    if not specs:
        logger.warning("generate_initial_plans: no specs for subject=%s", subject.name)
        return 0

    # 2. LLM 层: 兴趣优先重排序
    specs = await adjust_plan_order(specs, profile_summary, subject.get_display_name())

    # 3. 入库
    base_time = timezone.now()
    cumulative_minutes = 0
    plan_rows: list[LearningPlan] = []

    for idx, spec in enumerate(specs, start=1):
        cumulative_minutes += spec["expected_minutes"]
        expected_at = base_time + timedelta(minutes=cumulative_minutes)
        plan_rows.append(LearningPlan(
            subject=subject,
            target_agent=spec["target_agent"],
            plan_difficulty="medium",
            node_id=spec["node_id"],
            node_name=spec["node_name"],
            node_type=spec["node_type"],
            order=idx,
            action_type=spec["action_type"],
            difficulty=spec["difficulty"],
            state=LearningPlan.STATE_PENDING,
            expected_minutes=spec["expected_minutes"],
            expected_completion_time=expected_at,
            memory={
                "step_label": spec["step_label"],
                "step_type": spec["step_type"],
                "step_order": spec["step_order"],
                "step_desc": spec["step_desc"],
                "summary": spec["summary"],
                "tag": spec["tag"],
            },
        ))

    await sync_to_async(LearningPlan.objects.bulk_create)(plan_rows, batch_size=100)
    logger.info(
        "generate_initial_plans: subject=%s count=%s profile_id=%s",
        subject.name, len(plan_rows), profile_id,
    )
    return len(plan_rows)


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def generate_initial_plans(self, *, subject_id: int, profile_id: int):
    """画像完成后生成个性化学习计划。

    由 plan.signals.create_initial_plans_on_profile_complete 触发。
    规则层 + LLM 层均在异步函数中执行。
    """
    try:
        count = asyncio.run(_generate_plans_async(subject_id, profile_id))
        logger.info("generate_initial_plans task done: %s plans created", count)
    except Exception:  # noqa: BLE001
        logger.exception(
            "generate_initial_plans task failed: subject_id=%s profile_id=%s",
            subject_id, profile_id,
        )
