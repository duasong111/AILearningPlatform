"""Plan Tools：供 Plan Agent 在对话中按需查询与调整计划。

设计：
  - 270 个 plan 不会一次性塞进 LLM 上下文。
  - LLM 根据用户输入（如"链表我比较熟悉"）主动调用 query_plans 检索。
  - 工具集遵循"查询 → 详情 → 修改"三段式：
      1. query_plans(...)   按条件筛选，返回简要列表
      2. get_plan_detail()  获取单个 plan 的完整内容
      3. update_plan_state() / skip_plan() / mark_plan_completed() 状态变更
"""

import json
from datetime import datetime, timedelta
from typing import Annotated, Any, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

from plan.models import LearningPlan

from .knowledge_tools import _get_subject


_VALID_TARGET_AGENTS = {"chat", "profile", "practice", "plan", "video"}
_VALID_STATES = {"pending", "running", "success", "failed", "skipped"}
_VALID_STEP_TYPES = {"reading", "video", "quiz", "qa", "chapter_quiz"}
_VALID_ACTION_TYPES = {"study", "practice", "chat", "video"}


def _serialize_plan_brief(plan: LearningPlan) -> dict[str, Any]:
    """查询工具用的简要字段。"""
    memory = plan.memory or {}
    return {
        "plan_id": plan.id,
        "target_agent": plan.target_agent,
        "summary": memory.get("summary"),
        "node_id": plan.node_id,
        "node_name": plan.node_name,
        "step_type": memory.get("step_type"),
        "step_label": memory.get("step_label"),
        "step_order": memory.get("step_order"),
        "tag": memory.get("tag"),
        "action_type": plan.action_type,
        "expected_minutes": plan.expected_minutes,
        "expected_completion_time": (
            plan.expected_completion_time.isoformat()
            if plan.expected_completion_time else None
        ),
        "state": plan.state,
        "completed": plan.completed,
        "actual_completion_time": (
            plan.actual_completion_time.isoformat()
            if plan.actual_completion_time else None
        ),
    }


def _serialize_plan_full(plan: LearningPlan) -> dict[str, Any]:
    """详情工具用的完整字段。"""
    return {
        "plan_id": plan.id,
        "subject_name": plan.subject.name,
        "target_agent": plan.target_agent,
        "plan_difficulty": plan.plan_difficulty,
        "node_id": plan.node_id,
        "node_name": plan.node_name,
        "node_type": plan.node_type,
        "action_type": plan.action_type,
        "difficulty": plan.difficulty,
        "order": plan.order,
        "state": plan.state,
        "completed": plan.completed,
        "expected_minutes": plan.expected_minutes,
        "expected_completion_time": (
            plan.expected_completion_time.isoformat()
            if plan.expected_completion_time else None
        ),
        "actual_completion_time": (
            plan.actual_completion_time.isoformat()
            if plan.actual_completion_time else None
        ),
        "memory": plan.memory or {},
        "create_time": plan.create_time.isoformat() if plan.create_time else None,
        "success_time": plan.success_time.isoformat() if plan.success_time else None,
    }


@tool
def query_plans(
    config: Annotated[RunnableConfig, InjectedToolArg],
    node_name: Optional[str] = None,
    step_type: Optional[str] = None,
    state: Optional[str] = None,
    target_agent: Optional[str] = None,
    action_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 20,
) -> str:
    """按条件查询用户的计划。

    LLM 应根据用户输入自主选择过滤条件。例如：
      - "链表我比较熟悉" → query_plans(node_name="链表")
      - "先把视频看完" → query_plans(step_type="video", state="pending")
      - "已经做完的练习" → query_plans(action_type="practice", state="success")
      - "看看所有 5 步的进度" → query_plans(node_name="数组")

    Args:
        node_name: 按节点名模糊匹配
        step_type: reading/video/quiz/qa/chapter_quiz
        state: pending/running/success/failed/skipped
        target_agent: chat/profile/practice/plan/video
        action_type: study/practice/chat/video
        tag: 基础/核心/进阶/挑战（按难度）
        limit: 最多返回条数，默认 20

    Returns:
        JSON 数组，每条为 plan 简要字段。
    """
    user_id = config["configurable"]["user_id"]
    subject_code = config["configurable"].get("subject_code")
    if not subject_code:
        return "Error: 工具调用缺少 subject_code"

    try:
        subject = _get_subject(user_id, subject_code)
    except ValueError as e:
        return f"Error: {e}"

    qs = LearningPlan.objects.filter(subject=subject)

    if step_type:
        if step_type not in _VALID_STEP_TYPES:
            return f"Error: step_type 必须是 {sorted(_VALID_STEP_TYPES)}，收到 {step_type}"
        qs = qs.filter(memory__step_type=step_type)

    if state:
        if state not in _VALID_STATES:
            return f"Error: state 必须是 {sorted(_VALID_STATES)}，收到 {state}"
        qs = qs.filter(state=state)

    if target_agent:
        if target_agent not in _VALID_TARGET_AGENTS:
            return f"Error: target_agent 必须是 {sorted(_VALID_TARGET_AGENTS)}，收到 {target_agent}"
        qs = qs.filter(target_agent=target_agent)

    if action_type:
        if action_type not in _VALID_ACTION_TYPES:
            return f"Error: action_type 必须是 {sorted(_VALID_ACTION_TYPES)}，收到 {action_type}"
        qs = qs.filter(action_type=action_type)

    if tag:
        qs = qs.filter(memory__tag=tag)

    if node_name:
        qs = qs.filter(node_name__icontains=node_name)

    qs = qs.order_by("expected_completion_time", "id")
    plans = list(qs[:limit])

    return json.dumps(
        [_serialize_plan_brief(p) for p in plans],
        ensure_ascii=False,
        indent=2,
    )


@tool
def get_plan_detail(
    plan_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """获取单个计划的完整详情。

    当 query_plans 返回的简要信息不够用时（如需要看 memory.full 字段），调用此工具。

    Args:
        plan_id: 计划 ID

    Returns:
        JSON 字符串，包含完整字段。
    """
    user_id = config["configurable"]["user_id"]
    try:
        plan = LearningPlan.objects.get(id=plan_id, subject__user_id=user_id)
    except LearningPlan.DoesNotExist:
        return f"Error: 计划 ID {plan_id} 不存在或无权访问"
    return json.dumps(_serialize_plan_full(plan), ensure_ascii=False, indent=2)


@tool
def get_progress_summary(
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """获取当前学科的整体学习进度统计。

    返回按 step_type / target_agent / 节点的完成/总数。

    Returns:
        JSON 字符串，包含整体 + 分组统计。
    """
    user_id = config["configurable"]["user_id"]
    subject_code = config["configurable"].get("subject_code")
    if not subject_code:
        return "Error: 工具调用缺少 subject_code"

    try:
        subject = _get_subject(user_id, subject_code)
    except ValueError as e:
        return f"Error: {e}"

    plans = list(LearningPlan.objects.filter(subject=subject))
    total = len(plans)

    by_step: dict[str, dict[str, int]] = {}
    by_agent: dict[str, dict[str, int]] = {}
    by_node: dict[str, dict[str, int]] = {}

    for plan in plans:
        st = (plan.memory or {}).get("step_type") or "unknown"
        by_step.setdefault(st, {"total": 0, "success": 0, "skipped": 0, "pending": 0})
        by_step[st]["total"] += 1
        key = plan.state if plan.state in ("success", "skipped", "pending") else "pending"
        by_step[st][key] += 1

        ag = plan.target_agent
        by_agent.setdefault(ag, {"total": 0, "success": 0, "skipped": 0, "pending": 0})
        by_agent[ag]["total"] += 1
        by_agent[ag][key] += 1

        nd = plan.node_name or "unknown"
        by_node.setdefault(nd, {"total": 0, "success": 0, "skipped": 0, "pending": 0})
        by_node[nd]["total"] += 1
        by_node[nd][key] += 1

    return json.dumps({
        "subject": subject.name,
        "total_plans": total,
        "by_step_type": by_step,
        "by_target_agent": by_agent,
        "by_node": by_node,
    }, ensure_ascii=False, indent=2)


@tool
def update_plan_state(
    plan_id: int,
    new_state: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """更新单个计划的状态。

    Args:
        plan_id: 计划 ID
        new_state: pending/running/success/failed/skipped

    Returns:
        更新结果文本。
    """
    user_id = config["configurable"]["user_id"]

    if new_state not in _VALID_STATES:
        return f"Error: state 必须是 {sorted(_VALID_STATES)}，收到 {new_state}"

    try:
        plan = LearningPlan.objects.get(id=plan_id, subject__user_id=user_id)
    except LearningPlan.DoesNotExist:
        return f"Error: 计划 ID {plan_id} 不存在或无权访问"

    plan.state = new_state
    # save() 会自动维护 success_time / actual_completion_time / completed
    plan.save()
    return f"OK: 计划 {plan_id} 已更新为 {new_state}"


@tool
def skip_plan(
    plan_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
    reason: str = "",
) -> str:
    """将计划标记为跳过。

    常用于用户说"我对这个比较熟悉，跳过"。

    Args:
        plan_id: 计划 ID
        reason: 跳过原因（写入 memory.skip_reason）

    Returns:
        更新结果文本。
    """
    user_id = config["configurable"]["user_id"]
    try:
        plan = LearningPlan.objects.get(id=plan_id, subject__user_id=user_id)
    except LearningPlan.DoesNotExist:
        return f"Error: 计划 ID {plan_id} 不存在或无权访问"

    memory = dict(plan.memory or {})
    if reason:
        memory["skip_reason"] = reason
    memory["skipped_at"] = datetime.now().isoformat()
    plan.memory = memory
    plan.state = LearningPlan.STATE_SKIPPED
    plan.save(update_fields=["state", "memory", "updated_at"])
    return f"OK: 计划 {plan_id} 已跳过" + (f"，原因：{reason}" if reason else "")


@tool
def mark_plan_completed(
    plan_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """标记计划为已完成。

    Args:
        plan_id: 计划 ID

    Returns:
        更新结果文本。
    """
    user_id = config["configurable"]["user_id"]
    try:
        plan = LearningPlan.objects.get(id=plan_id, subject__user_id=user_id)
    except LearningPlan.DoesNotExist:
        return f"Error: 计划 ID {plan_id} 不存在或无权访问"

    plan.state = LearningPlan.STATE_SUCCESS
    plan.save()  # save() 自动写 success_time / actual_completion_time / completed
    return f"OK: 计划 {plan_id} 已标记为完成"


@tool
def adjust_plan_difficulty(
    plan_id: int,
    new_difficulty: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """调整单个计划的整体难度（low/medium/high）。

    Args:
        plan_id: 计划 ID
        new_difficulty: low/medium/high

    Returns:
        更新结果文本。
    """
    user_id = config["configurable"]["user_id"]
    if new_difficulty not in {"low", "medium", "high"}:
        return f"Error: difficulty 必须是 low/medium/high，收到 {new_difficulty}"

    try:
        plan = LearningPlan.objects.get(id=plan_id, subject__user_id=user_id)
    except LearningPlan.DoesNotExist:
        return f"Error: 计划 ID {plan_id} 不存在或无权访问"

    plan.plan_difficulty = new_difficulty
    plan.save(update_fields=["plan_difficulty", "updated_at"])
    return f"OK: 计划 {plan_id} 难度调整为 {new_difficulty}"


@tool
def reschedule_plan(
    plan_ids: list[int],
    config: Annotated[RunnableConfig, InjectedToolArg],
    offset_days: int = 7,
    reason: str = "",
) -> str:
    """批量延期计划到指定天数后。

    用于"挪到下周"、"下周再做"、"延后到 X 天后"等场景。
    本质是把计划的 expected_completion_time 往后推 offset_days 天，
    状态保持 pending 不变。

    Args:
        plan_ids: 计划 ID 列表
        offset_days: 延后天数，正数=往后推，负数=往前挪。默认 7（下周）
        reason: 延期原因，写入 memory.reschedule_reason

    Returns:
        更新结果文本，列出每个 plan 的新预计完成时间。
    """
    from django.utils import timezone

    user_id = config["configurable"]["user_id"]
    if not plan_ids:
        return "Error: plan_ids 不能为空"

    plans = list(LearningPlan.objects.filter(id__in=plan_ids, subject__user_id=user_id))
    if not plans:
        return "Error: 没有找到任何 plan，请检查 ID 是否正确"

    # 按基础时间推迟 offset_days 天
    # 基础时间：原 expected_completion_time 或 now（取后者）
    base_now = timezone.now()
    success_ids = []
    missing_ids = []

    for plan in plans:
        base_time = plan.expected_completion_time or base_now
        new_time = base_time + timedelta(days=offset_days)
        plan.expected_completion_time = new_time

        memory = dict(plan.memory or {})
        if reason:
            memory["reschedule_reason"] = reason
        memory["rescheduled_at"] = base_now.isoformat()
        memory["reschedule_offset_days"] = offset_days
        plan.memory = memory

        plan.save(update_fields=["expected_completion_time", "memory", "updated_at"])
        success_ids.append((plan.id, new_time.isoformat()))

    found_set = {p.id for p in plans}
    missing_ids = [pid for pid in plan_ids if pid not in found_set]

    lines = [f"OK: 已延期 {len(success_ids)} 条计划（offset={offset_days}天）"]
    for pid, new_t in success_ids:
        lines.append(f"  - plan {pid} → {new_t}")
    if reason:
        lines.append(f"原因：{reason}")
    if missing_ids:
        lines.append(f"未找到的计划 ID：{missing_ids}")

    return "\n".join(lines)
