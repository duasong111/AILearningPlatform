"""Plan Chain：学习计划生成逻辑

生成计划后，memory.prompt 字段是给下一个 Agent 的前置提示词。
前端拿到 plan.memory.prompt 后，创建新会话时直接拼入 extra_prompt：

    POST /api/conversations/
    {
        "agent": plan.target_agent,
        "extra_prompt": plan.memory.prompt
    }

每个 Agent 启动时会读取 conversation.extra_prompt 并注入系统提示词。

返回的 memory 完整结构：
    {
        "summary":           str,   # 计划摘要（展示用）
        "reason":            str,   # 制定原因（展示用）
        "next_step":         str,   # 下一步建议（展示用）
        "focus_nodes":      list,   # 重点知识点名称列表（展示用）
        "profile_complete": bool,   # 画像是否完整
        "subject_code":      str,   # 学科代码
        "subject_display":   str,   # 学科中文名
        "prompt":            str,   # ★ 前置提示词，直接作为 extra_prompt
    }

prompt 内容由后端根据 target_agent 自动生成，前端无需自行拼接：
    profile  → 引导补齐画像缺失维度
    practice → 围绕薄弱知识点出题（含具体知识点名和 mastery 值）
    chat     → 围绕学习目标展开讨论

前端完整使用示例（伪代码）：
    // 1. 从 WS complete 事件中拿到 plan
    const plan = wsEvent.meta.plan

    // 2. 创建新会话，prompt 直接传给下一个 Agent
    const conv = await POST('/api/conversations/', {
        subject_id: currentSubjectId,
        agent: plan.target_agent,
        title: plan.memory.summary,
        extra_prompt: plan.memory.prompt
    })

    // 3. 前端自行管理计划生命周期
    await PATCH(`/api/plans/${plan.id}/`, { state: 'running' })
    // ... 用户完成学习后 ...
    await PATCH(`/api/plans/${plan.id}/`, { state: 'success' })

本模块有两条生成路径（前端无需关心）：
- LLM 路径：PLAN_BUILDER_SYSTEM_PROMPT 引导 LLM 输出包含 prompt 的 JSON
- Fallback 路径：_build_agent_prompt() 根据 target_agent 确定性生成 prompt
两条路径的返回结构完全一致。
"""

import json
from datetime import timedelta

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from ..common import dumps_profile, extract_json, format_history, profile_is_complete
from ..prompts.plan_prompts import PLAN_BUILDER_SYSTEM_PROMPT

import logging
logger = logging.getLogger(__name__)


def _content_to_text(content) -> str:
    """提取消息内容为文本"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return "" if content is None else str(content)


def _extract_ai_text(result) -> str:
    """从 LLM 结果中提取文本"""
    from langchain_core.messages import AIMessage

    if isinstance(result, AIMessage):
        return _content_to_text(result.content)
    if isinstance(result, dict):
        messages = result.get("messages") or []
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return _content_to_text(msg.content)
    return ""


def _normalize_target_agent(value: str | None) -> str | None:
    """规范化 target_agent"""
    if value in {"chat", "profile", "practice"}:
        return value
    return None


def _normalize_difficulty(value: str | None) -> str | None:
    """规范化 difficulty"""
    if value in {"low", "medium", "high"}:
        return value
    return None


def _pick_target_agent(profile_summary: dict, knowledge_map: list[dict]) -> str:
    """根据画像和知识图谱选择目标 agent"""
    if not profile_is_complete(profile_summary):
        return "profile"
    if knowledge_map:
        weakest = min(int(node.get("mastery") or 0) for node in knowledge_map)
        if weakest < 75:
            return "practice"
    return "chat"


def _pick_difficulty(profile_summary: dict, knowledge_map: list[dict], target_agent: str) -> str:
    """根据画像和知识图谱选择难度"""
    if target_agent == "profile":
        return "low"
    if not knowledge_map:
        return "medium"
    weakest = min(int(node.get("mastery") or 0) for node in knowledge_map)
    if weakest < 35:
        return "low"
    if weakest < 70:
        return "medium"
    if profile_is_complete(profile_summary):
        return "high"
    return "medium"


def _build_plan_summary(target_agent: str) -> str:
    """生成计划摘要"""
    if target_agent == "profile":
        return "先补齐用户画像，再根据更完整的信息安排后续学习。"
    if target_agent == "practice":
        return "先通过针对性练习巩固当前薄弱知识点。"
    return "先进入答疑/路径讨论，明确近期学习重点。"


def _build_next_step(target_agent: str) -> str:
    """生成下一步建议"""
    if target_agent == "profile":
        return "继续完成画像问答，补齐学习目标、基础和时间安排。"
    if target_agent == "practice":
        return "进入练习 agent，先做一轮围绕薄弱点的题目。"
    return "进入聊天 agent，围绕当前学习任务继续细化路径。"


def _build_agent_prompt(
    target_agent: str,
    focus_nodes: list[str],
    knowledge_map: list[dict],
    difficulty: str,
    summary: str,
) -> str:
    """确定性生成面向下一个 agent 的前置提示词。

    此函数是 memory.prompt 的唯一生成路径（LLM 不参与 prompt 生成）。
    保证 prompt 格式和内容可控。

    返回值存入 plan.memory.prompt，前端使用方式：
        POST /api/conversations/
        {"agent": plan.target_agent, "extra_prompt": plan.memory.prompt}
    """
    # 构建知识点掌握度描述
    node_details = []
    if knowledge_map and focus_nodes:
        node_map = {str(n.get("name", "")): int(n.get("mastery") or 0) for n in knowledge_map}
        for name in focus_nodes:
            mastery = node_map.get(name)
            node_details.append(f"{name}(mastery={mastery})" if mastery is not None else name)
    elif focus_nodes:
        # knowledge_map 为空时（模板模式），只列节点名
        node_details = list(focus_nodes)

    nodes_text = "、".join(node_details) if node_details else "暂无"

    if target_agent == "profile":
        return (
            f"你正在执行一个学习计划。"
            f"计划目标：{summary}"
            f"当前画像不完整，请通过问答引导用户补齐缺失的画像维度"
            f"（学习目标、知识基础、认知风格、可用时间、兴趣方向）。"
            f"请用简洁友好的方式提问，每次只问一个维度。"
        )

    if target_agent == "practice":
        return (
            f"你正在执行一个学习计划。"
            f"计划目标：{summary}"
            f"重点关注知识点：{nodes_text}。"
            f"难度：{difficulty}。"
            f"请围绕以上薄弱知识点出题，优先考察基本概念和常见操作，"
            f"逐步提升用户对薄弱点的掌握度。"
        )

    # chat
    return (
        f"你正在执行一个学习计划。"
        f"计划目标：{summary}"
        f"用户画像已相对完整，知识点掌握良好。"
        f"请围绕用户的学习目标展开讨论，帮助细化学习路径、"
        f"解答疑问、巩固已有知识。"
    )


def _weakest_focus_nodes(knowledge_map: list[dict], limit: int = 3) -> list[str]:
    """找出最薄弱的知识点"""
    ranked = sorted(knowledge_map, key=lambda item: (int(item.get("mastery") or 0), str(item.get("node_id") or "")))
    names: list[str] = []
    for item in ranked[:limit]:
        name = str(item.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def build_fallback_plan(
    *,
    subject_display: str,
    subject_code: str,
    profile_summary: dict,
    knowledge_map: list[dict],
) -> dict:
    """构建后备计划（当 LLM 生成失败时使用）"""
    target_agent = _pick_target_agent(profile_summary, knowledge_map)
    difficulty = _pick_difficulty(profile_summary, knowledge_map, target_agent)
    focus_nodes = _weakest_focus_nodes(knowledge_map)
    summary = _build_plan_summary(target_agent)
    items = _build_items_for_nodes(focus_nodes)
    return {
        "target_agent": target_agent,
        "difficulty": difficulty,
        "state": "pending",
        "memory": {
            "subject_code": subject_code,
            "subject_display": subject_display,
            "summary": summary,
            "reason": "根据当前画像完整度和知识星图薄弱点自动生成。",
            "next_step": _build_next_step(target_agent),
            "focus_nodes": focus_nodes,
            "profile_complete": profile_is_complete(profile_summary),
            "prompt": _build_agent_prompt(
                target_agent, focus_nodes, knowledge_map, difficulty, summary,
            ),
            "items": items,
        },
    }


# 每个知识点的 5 步学习流程
_LEARNING_STEPS = [
    ("看书预习", "reading", "，阅读教材和参考资料，建立初步认知"),
    ("视频学习", "video", "，通过视频讲解深入理解知识点"),
    ("刷题巩固", "quiz", "，通过练习题检验和巩固所学内容"),
    ("对话举一反三", "qa", "，与 AI 讨论拓展，加深理解"),
    ("评测检验", "chapter_quiz", "，综合测试学习效果，查漏补缺"),
]


def _build_items_for_nodes(focus_nodes: list[str], tag: str = "基础") -> list[dict]:
    """为每个知识点生成 5 步学习流程的 items"""
    items = []
    for node_name in focus_nodes:
        for step_label, step_type, desc_suffix in _LEARNING_STEPS:
            items.append({
                "name": f"{node_name} · {step_label}",
                "desc": f"针对「{node_name}」知识点{desc_suffix.lstrip('，')}",
                "tag": tag,
                "type": step_type,
                "done": False,
            })
    return items


def _normalize_memory(value, fallback: dict) -> dict:
    """规范化 memory 字段"""
    memory = value if isinstance(value, dict) else {}
    normalized = {
        "summary": str(memory.get("summary") or fallback["memory"]["summary"]),
        "reason": str(memory.get("reason") or fallback["memory"]["reason"]),
        "next_step": str(memory.get("next_step") or fallback["memory"]["next_step"]),
        "focus_nodes": memory.get("focus_nodes") if isinstance(memory.get("focus_nodes"), list) else fallback["memory"]["focus_nodes"],
        "profile_complete": bool(memory.get("profile_complete")) if "profile_complete" in memory else fallback["memory"]["profile_complete"],
        "subject_code": str(memory.get("subject_code") or fallback["memory"]["subject_code"]),
        "subject_display": str(memory.get("subject_display") or fallback["memory"]["subject_display"]),
        "prompt": str(memory.get("prompt") or fallback["memory"]["prompt"]),
        "items": memory.get("items") if isinstance(memory.get("items"), list) else fallback["memory"].get("items", []),
    }
    return normalized


def _expand_items_to_plans(
    *,
    items: list[dict],
    target_agent: str,
    difficulty: str,
    state: str,
    subject_code: str,
    subject_display: str,
    knowledge_map: list[dict],
    memory: dict,
) -> list[dict]:
    """将 memory.items 展开为多个 plan，每个 item 对应一条 LearningPlan 记录。

    每个 item 的 name 格式通常是 "知识点 · 步骤名"，从中提取 node_name。
    """
    # 构建 node_name → node_id 映射
    node_id_map: dict[str, str] = {}
    node_type_map: dict[str, str] = {}
    for node in knowledge_map:
        name = str(node.get("name") or "")
        nid = str(node.get("node_id") or node.get("id") or "")
        if name and nid:
            node_id_map[name] = nid
            node_type_map[name] = str(node.get("node_type") or node.get("type") or "concept")

    plans: list[dict] = []
    step_order = 0
    for item in items:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or "")
        # 从 "链表 · 看书预习" 中提取节点名
        if " · " in name:
            node_name = name.split(" · ")[0].strip()
            step_label = name.split(" · ", 1)[1].strip()
        else:
            node_name = name
            step_label = str(item.get("type") or "study")

        step_type = str(item.get("type") or "reading")
        step_order += 1

        # action_type 映射
        action_type_map = {
            "reading": "study",
            "video": "video",
            "quiz": "practice",
            "qa": "chat",
            "chapter_quiz": "practice",
        }
        action_type = action_type_map.get(step_type, "study")

        # 查找 node_id
        node_id = node_id_map.get(node_name, "")
        node_type = node_type_map.get(node_name, "concept")

        # 构建 step memory
        step_memory = {
            "subject_code": subject_code,
            "subject_display": subject_display,
            "summary": memory.get("summary", ""),
            "reason": memory.get("reason", ""),
            "step_label": step_label,
            "step_type": step_type,
            "step_order": step_order,
            "step_desc": str(item.get("desc") or ""),
            "tag": str(item.get("tag") or "基础"),
            "focus_nodes": memory.get("focus_nodes", []),
            "profile_complete": memory.get("profile_complete", False),
            "prompt": memory.get("prompt", ""),
        }

        plans.append({
            "target_agent": target_agent,
            "difficulty": difficulty,
            "state": state,
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "action_type": action_type,
            "memory": step_memory,
            "expected_minutes": 30,
        })

    return plans


async def build_learning_plan(
    *,
    subject_display: str,
    subject_code: str,
    history_messages: list[BaseMessage],
    profile_summary: dict,
    knowledge_map: list[dict],
) -> list[dict]:
    """
    生成学习计划（核心逻辑）

    返回多个 plan，每个 plan 对应一个知识节点的一个学习步骤。
    每个知识节点会展开为 5 个步骤（reading/video/quiz/qa/chapter_quiz），
    因此返回的 plan 数量 = 节点数 × 5。

    Returns:
        list[dict]: 每个 dict 是一个 plan 的结构化数据
    """
    from ..agents.llm_factory import build_llm

    fallback = build_fallback_plan(
        subject_display=subject_display,
        subject_code=subject_code,
        profile_summary=profile_summary,
        knowledge_map=knowledge_map,
    )

    llm = build_llm(streaming=False, temperature=0.2)
    prompt = (
        f"学科: {subject_display} ({subject_code})\n"
        f"当前画像:\n{dumps_profile(profile_summary)}\n\n"
        f"当前知识星图:\n{json.dumps(knowledge_map, ensure_ascii=False)}\n\n"
        f"对话历史:\n{format_history(history_messages)}\n"
    )

    result = await llm.ainvoke(
        [
            SystemMessage(content=PLAN_BUILDER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )
    text = _extract_ai_text(result)

    try:
        parsed = json.loads(extract_json(text))
    except Exception:
        parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    target_agent = _normalize_target_agent(parsed.get("target_agent")) or fallback["target_agent"]
    difficulty = _normalize_difficulty(parsed.get("difficulty")) or fallback["difficulty"]
    state = str(parsed.get("state") or fallback["state"]).strip() or fallback["state"]
    if state not in {"pending", "running", "success", "failed"}:
        state = fallback["state"]

    memory = _normalize_memory(parsed.get("memory"), fallback)

    # prompt 始终由系统确定性生成，不用 LLM 输出
    memory["prompt"] = _build_agent_prompt(
        target_agent=target_agent,
        focus_nodes=memory.get("focus_nodes") or [],
        knowledge_map=knowledge_map,
        difficulty=difficulty,
        summary=str(memory.get("summary") or ""),
    )

    # 从 memory.items 展开为多个 plan
    items = memory.get("items") or []
    if not items:
        # fallback: 用 fallback items
        items = fallback["memory"].get("items") or []

    plans = _expand_items_to_plans(
        items=items,
        target_agent=target_agent,
        difficulty=difficulty,
        state=state,
        subject_code=subject_code,
        subject_display=subject_display,
        knowledge_map=knowledge_map,
        memory=memory,
    )

    return plans


# ---------------------------------------------------------------------------
# 基础计划（baseline plan）
#
# 数据来源:
#   - plan/baseline_plans.py 中的 BASELINE_PLANS 静态快照（一次性生成）
#   - 顺序: prerequisite 拓扑序 + (difficulty, name, id) 稳定排序
#   - expected_minutes = 30 * difficulty
# 重新生成快照: `python plan/_gen_baseline.py`
# ---------------------------------------------------------------------------

# 学科 code → 静态知识图谱映射（仅供 _gen_baseline.py 使用，运行时无需）
SUBJECT_KNOWLEDGE_MAP = {
    "data_structure": "data_structure_map",
    "cybersecurity": "cybersecurity_map",
    "iot": "iot_map",
    "electrical_automation": "electrical_automation_map",
    "mechanical_design": "mechanical_design_map",
    "advanced_math": "advanced_math_map",
    "artificial_intelligence": "artificial_intelligence_map",
}


def _load_knowledge_map_for_subject(subject_code: str) -> dict | None:
    """根据学科 code 取回对应的静态知识图谱（users/knowledge_map.py 内的 dict）。

    仅供 plan/_gen_baseline.py 调用；运行时不再需要。
    """
    attr = SUBJECT_KNOWLEDGE_MAP.get(subject_code)
    if not attr:
        return None
    from users import knowledge_map as km_module
    return getattr(km_module, attr, None)


def _load_baseline_plans() -> dict[str, list[dict]]:
    """加载 plan/baseline_plans.py 静态快照（启动时读一次即可）。"""
    from plan.baseline_plans import BASELINE_PLANS
    return BASELINE_PLANS


def _topological_sort_by_prerequisite(km: dict) -> list[dict]:
    """按 prerequisite 关系做拓扑排序，返回节点列表（保证依赖在前面）。

    仅供 plan/_gen_baseline.py 调用；运行时不再需要。
    若存在环，回退到原顺序；孤立节点按 difficulty/name 升序稳定排序。
    """
    nodes = list(km.get("nodes") or [])
    if not nodes:
        return []

    node_index = {str(n.get("id")): n for n in nodes}
    # 依赖图：每个节点的 prerequisite 前置列表（source→target 表示 source 是 target 的前置）
    prereq_of: dict[str, list[str]] = {str(n.get("id")): [] for n in nodes}
    in_degree: dict[str, int] = {str(n.get("id")): 0 for n in nodes}

    for rel in km.get("relations") or []:
        if rel.get("type") != "prerequisite":
            continue
        src = str(rel.get("source"))
        tgt = str(rel.get("target"))
        if tgt not in prereq_of or src not in node_index:
            continue
        prereq_of[tgt].append(src)
        in_degree[tgt] += 1

    # 稳定排序键: (difficulty, name, id)
    def _sort_key(nid: str):
        n = node_index[nid]
        return (int(n.get("difficulty") or 0), str(n.get("name") or ""), nid)

    # Kahn
    available = sorted(
        [nid for nid, deg in in_degree.items() if deg == 0],
        key=_sort_key,
    )
    result: list[str] = []
    while available:
        nid = available.pop(0)
        result.append(nid)
        for tgt, deps in prereq_of.items():
            if nid in deps:
                in_degree[tgt] -= 1
                if in_degree[tgt] == 0 and tgt not in result:
                    available.append(tgt)
        # 同一层仍按 sort_key 稳定排序
        available.sort(key=_sort_key)

    # 兜底：环上残留节点追加
    if len(result) < len(nodes):
        remaining = [nid for nid in node_index.keys() if nid not in result]
        remaining.sort(key=_sort_key)
        result.extend(remaining)

    return [node_index[nid] for nid in result]


def _expected_minutes(difficulty: int) -> int:
    """难度 1-5 → 30-150 分钟（线性映射）。"""
    d = max(1, min(5, int(difficulty or 1)))
    return 30 * d


def build_baseline_plan_items(
    *,
    subject_code: str,
) -> list[dict]:
    """从 plan/baseline_plans.py 静态快照读取基础计划项列表。

    Returns:
        [
            {
                "node_id": "2",
                "node_name": "数组",
                "node_type": "structure",
                "difficulty": 1,
                "expected_minutes": 30,
            },
            ...
        ]
        顺序: prerequisite 拓扑序 + (difficulty, name) 稳定排序（生成时已固化）
    """
    plans = _load_baseline_plans()
    return list(plans.get(subject_code) or [])


def create_baseline_plan(*, subject):  # pragma: no cover
    """DEPRECATED: 已废弃。

    旧的"1 plan 包含 N items"的设计已废弃；当前每条 plan 自带节点/步骤字段，
    画像完成后由 plan.signals 一次性创建 270 条 plan。
    本函数保留签名但直接返回 None，避免误调用。
    """
    logger.warning(
        "create_baseline_plan is deprecated and now a no-op for subject=%s. "
        "Use plan.signals.create_initial_plans_on_profile_complete instead.",
        getattr(subject, "name", subject),
    )
    return None


# ---------------------------------------------------------------------------
# Agent 编排：画像补齐后调用，调整 baseline plan
# ---------------------------------------------------------------------------

# 跳过阈值：mastery 达到该值认为该节点已掌握，可剔除
SKIP_MASTERY_THRESHOLD = 80
# 重排：mastery 越低优先级越高
WEAK_PRIORITY_BOOST = 100
# action_type 启发式：按节点类型挑选默认动作（agent 可覆盖）
ACTION_TYPE_BY_NODE_TYPE = {
    "structure": "study",
    "algorithm": "practice",
    "concept": "chat",
    "tool": "video",
    "security": "practice",
    "math": "study",
}


def _get_mastery_map(subject) -> dict[str, int]:
    """读取 subject 下所有知识点的 mastery 映射 {node_id: mastery}。"""
    from users.models import KnowledgeNode

    rows = KnowledgeNode.objects.filter(subject=subject).values("node_id", "mastery")
    return {str(r["node_id"]): int(r.get("mastery") or 0) for r in rows}


def _default_action_type(node_type: str) -> str:
    return ACTION_TYPE_BY_NODE_TYPE.get(node_type, "study")


def _rank_items_by_mastery(items: list[dict], mastery_map: dict[str, int]) -> list[dict]:
    """重排序：mastery 低的在前（薄弱优先）。

    Python sorted 是稳定的，所以同 mastery 内保持输入顺序。
    """
    return sorted(items, key=lambda it: mastery_map.get(str(it["node_id"]), 0))


def _build_profile_context(profile) -> dict:
    """从 UserProfile 抽取编排所需的画像摘要。"""
    if profile is None:
        return {}
    return {
        "course": profile.course,
        "knowledge_base": profile.knowledge_base,
        "cognitive_style": profile.cognitive_style,
        "learning_goal_score": profile.learning_goal_score,
        "available_time": profile.available_time,
        "common_mistakes": profile.common_mistakes or [],
        "interest_direction": profile.interest_direction or [],
    }


def orchestrate_plan(*, plan=None, profile=None, use_llm: bool = True, subject=None):  # pragma: no cover
    """DEPRECATED: 已废弃。

    旧的"1 plan 包含 N items"的设计已废弃；当前每条 plan 自带节点/步骤字段，
    编排行为在 plan_agent LLM 中按需通过 query_plans 自主判断。
    本函数保留签名但直接返回 None。
    """
    logger.warning(
        "orchestrate_plan is deprecated and now a no-op. "
        "Plan adjustments should be done via plan_agent query_plans tools.",
    )
    return None
