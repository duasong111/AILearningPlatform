"""Plan app signals。

监听事件:

  users.UserProfile.post_save
    - 画像从不完整 → 完整时，dispatch Celery task 生成个性化学习计划
    - 规则层(步骤筛选+时间压缩) + LLM层(兴趣重排序) 在 plan.tasks 中执行
    - 不防重：重复触发时再次写入，由 plan agent 启动后自主判断处理
"""

import logging
import threading

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# 内存缓存：pre_save 写入旧值，post_save 读取并清理
_state_lock = threading.Lock()
_old_profile_complete: dict[int, bool] = {}


def _build_profile_summary(profile) -> dict:
    """构造 llm.common.profile_is_complete 所需的摘要结构。"""
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


@receiver(pre_save, sender="users.UserProfile")
def stash_old_profile_completeness(sender, instance, **kwargs):
    """pre_save 缓存当前记录的完整度（用于 post_save 比较）。"""
    if instance.pk is None:
        with _state_lock:
            _old_profile_complete[0] = False
        return
    try:
        from users.models import UserProfile
        prev = UserProfile.objects.filter(pk=instance.pk).first()
        old_complete = False
        if prev is not None:
            from llm.common import profile_is_complete
            old_complete = profile_is_complete(_build_profile_summary(prev))
        with _state_lock:
            _old_profile_complete[instance.pk] = old_complete
    except Exception:  # noqa: BLE001
        logger.exception("stash_old_profile_completeness failed for pk=%s", instance.pk)


@receiver(post_save, sender="users.UserProfile")
def create_initial_plans_on_profile_complete(sender, instance, created, **kwargs):
    """画像从不完整 → 完整时，dispatch Celery task 生成个性化学习计划。

    触发条件:
      - profile 关联到 subject
      - 旧完整度 = False，新完整度 = True

    行为:
      - dispatch plan.tasks.generate_initial_plans Celery task
      - task 内执行: 规则层(步骤筛选+时间压缩) → LLM层(兴趣重排序) → bulk_create
      - 不防重：每次完整度跨越都会再写一次（数据有冗余，由 plan agent 启动后处理）
    """
    from llm.common import profile_is_complete

    new_summary = _build_profile_summary(instance)
    new_complete = profile_is_complete(new_summary)

    with _state_lock:
        old_complete = _old_profile_complete.pop(instance.pk, False if created else None)

    _old_profile_complete.pop(0, None)

    logger.info(
        "profile signal: pk=%s created=%s old_complete=%s new_complete=%s summary=%s",
        instance.pk, created, old_complete, new_complete, new_summary,
    )

    if old_complete is None:
        if not new_complete:
            return
    elif old_complete:
        return

    if not new_complete:
        return

    subject = instance.subject
    if subject is None:
        logger.warning("profile signal: subject is None, skipping plan creation")
        return

    # dispatch Celery task: 规则层(步骤筛选+时间压缩) + LLM层(兴趣重排序) + 入库
    from plan.tasks import generate_initial_plans

    generate_initial_plans.delay(subject_id=subject.id, profile_id=instance.pk)
    logger.info(
        "profile signal: dispatched generate_initial_plans task for subject=%s profile_id=%s",
        subject.name, instance.pk,
    )
