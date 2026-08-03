"""学习计划模板：节点 × 步骤 粒度。

设计：
    每个 (node, step) 组合 = 1 个 LearningPlan。
    数据结构学科 54 节点 × 5 步骤 = 270 个 plan。

    信号（plan.signals.create_initial_plans_on_profile_complete）在画像
    从不完整 → 完整时遍历本模块的 (node, step) 对，
    调用 bulk_create 把所有 plan 一次性入库（item 字段已合并到 plan）。

不防重：用户重复触发画像更新时再次写入，由 plan agent 启动后通过
query_plans 自主判断如何去重/合并。
"""

from plan.baseline_plans import BASELINE_PLANS

# ── 每个知识点的 5 步学习流程 ──────────────────────────

LEARNING_STEPS = [
    {
        "label": "看书预习",
        "type": "reading",
        "order": 1,
        "desc_tpl": "阅读「{name}」相关教材和参考资料，建立初步认知",
    },
    {
        "label": "视频学习",
        "type": "video",
        "order": 2,
        "desc_tpl": "通过视频讲解深入理解「{name}」的核心概念和原理",
    },
    {
        "label": "刷题巩固",
        "type": "quiz",
        "order": 3,
        "desc_tpl": "完成「{name}」相关练习题，检验和巩固所学内容",
    },
    {
        "label": "对话举一反三",
        "type": "qa",
        "order": 4,
        "desc_tpl": "与 AI 讨论「{name}」的实际应用和拓展问题",
    },
    {
        "label": "评测检验",
        "type": "chapter_quiz",
        "order": 5,
        "desc_tpl": "综合测试「{name}」知识点的掌握情况，查漏补缺",
    },
]


# ── 步骤 → target_agent + action_type 映射 ─────────────
# target_agent 必须 ∈ Conversation.AGENT_CHOICES（chat/profile/practice/plan/video）
# action_type 必须 ∈ LearningPlan.ACTION_CHOICES（study/practice/chat/video）

STEP_AGENT_MAP: dict[str, tuple[str, str]] = {
    "reading":      ("chat",     "study"),    # 看书预习 → chat agent 讲解
    "video":        ("video",    "video"),    # 视频学习 → video agent
    "quiz":         ("practice", "practice"), # 刷题巩固 → practice agent
    "qa":           ("chat",     "chat"),     # 对话举一反三 → chat agent
    "chapter_quiz": ("practice", "practice"), # 评测检验 → practice agent
}


# 学科代码 → 中文名映射
_SUBJECT_DISPLAY_NAMES = {
    "data_structure": "数据结构",
    "cybersecurity": "网络安全",
    "iot": "物联网",
    "electrical_automation": "电气自动化",
    "mechanical_design": "机械设计",
    "advanced_math": "高等数学",
    "artificial_intelligence": "人工智能",
}


def subject_display_name(subject_code: str) -> str:
    return _SUBJECT_DISPLAY_NAMES.get(subject_code, subject_code)


# ── 难度 → 标签 ──────────────────────────────────────

def _difficulty_tag(difficulty: int) -> str:
    if difficulty <= 1:
        return "基础"
    elif difficulty <= 2:
        return "核心"
    elif difficulty <= 3:
        return "进阶"
    return "挑战"


# ── 预计耗时：difficulty 1→30min, 5→150min ──────────

def expected_minutes_for_difficulty(difficulty: int) -> int:
    return 30 * max(1, min(int(difficulty or 1), 5))


# ── (node, step) 配对迭代器 ──────────────────────────

def iter_node_step_pairs(subject_code: str):
    """生成 (node, step) 对，每对 = 1 个 plan。

    node: dict(node_id, node_name, node_type, difficulty, expected_minutes)
    step: dict(label, type, order, desc_tpl)
    """
    nodes = BASELINE_PLANS.get(subject_code, [])
    for node in nodes:
        for step in LEARNING_STEPS:
            yield node, step


def count_pairs(subject_code: str) -> int:
    return sum(1 for _ in iter_node_step_pairs(subject_code))


def get_node_step_pairs(subject_code: str) -> list[tuple[dict, dict]]:
    """返回 (node, step) 列表（物化版，便于多次消费）。"""
    return list(iter_node_step_pairs(subject_code))


# ── 给信号用的 plan 规格构造 ──────────────────────────

def build_plan_spec(subject_code: str):
    """生成 (node, step, target_agent, action_type) 列表，供 signals 写入 DB。

    不包含 expected_completion_time / order，这些由 signals 根据
    累计 expected_minutes 计算。
    """
    specs = []
    for node, step in iter_node_step_pairs(subject_code):
        target_agent, action_type = STEP_AGENT_MAP[step["type"]]
        specs.append({
            "node_id": node["node_id"],
            "node_name": node["node_name"],
            "node_type": node["node_type"],
            "difficulty": node["difficulty"],
            "step_label": step["label"],
            "step_type": step["type"],
            "step_order": step["order"],
            "step_desc": step["desc_tpl"].format(name=node["node_name"]),
            "target_agent": target_agent,
            "action_type": action_type,
            "summary": f"{node['node_name']} · {step['label']}",
            "tag": _difficulty_tag(node["difficulty"]),
            "expected_minutes": expected_minutes_for_difficulty(node["difficulty"]),
        })
    return specs


# ── 画像驱动的个性化 plan 规格构造 ────────────────────

# 步骤类型 → 是否为"精简时可保留"的核心步骤
# 核心步骤: quiz (刷题巩固) + chapter_quiz (评测检验)
# 非核心:   reading (看书预习) + video (视频学习) + qa (对话举一反三)
_CORE_STEP_TYPES = {"quiz", "chapter_quiz"}


def _select_steps_for_node(node: dict, profile_summary: dict) -> list[dict]:
    """根据画像决定该节点保留哪些学习步骤。

    规则:
      1. 薄弱节点 (node_name 在 common_mistakes 中) → 保留全部 5 步
      2. 高基础 (knowledge_base >= 70) 且非薄弱 → 仅保留核心 2 步 (刷题+评测)
      3. 中基础 (knowledge_base >= 40) 且非薄弱 → 保留 3 步:
         - difficulty 1: video + quiz + chapter_quiz (跳过 reading)
         - difficulty 2+: reading + quiz + chapter_quiz (跳过 video/qa)
      4. 低基础 → 保留全部 5 步
    """
    weak_areas = profile_summary.get("knowledge_base", {}).get("weak_areas", [])
    is_weak = node["node_name"] in weak_areas
    kb_level = int(profile_summary.get("knowledge_base", {}).get("level") or 0)

    if is_weak or kb_level < 40:
        return LEARNING_STEPS

    if kb_level >= 70:
        return [s for s in LEARNING_STEPS if s["type"] in _CORE_STEP_TYPES]

    # 中基础: 3 步
    if int(node.get("difficulty") or 1) <= 1:
        keep = {"video", "quiz", "chapter_quiz"}
    else:
        keep = {"reading", "quiz", "chapter_quiz"}
    return [s for s in LEARNING_STEPS if s["type"] in keep]


def _time_compression_factor(available_time: int) -> float:
    """根据可用时间返回耗时压缩系数。

    available_time (小时/周):
      >= 6  → 1.0 (不压缩)
      3-5   → 0.8
      1-2   → 0.6
      0     → 0.5 (最少也要留点时间)
    """
    t = max(0, int(available_time or 0))
    if t >= 6:
        return 1.0
    if t >= 3:
        return 0.8
    if t >= 1:
        return 0.6
    return 0.5


def build_personalized_plan_spec(subject_code: str, profile_summary: dict):
    """根据用户画像生成个性化的 plan 规格列表。

    在 build_plan_spec 基础上应用三条规则:
      - 跳过步骤: 高基础跳过预习/视频, 仅保留刷题+评测
      - 薄弱点加权: 薄弱节点保留全部 5 步, 其余精简
      - 时间压缩: 按 available_time 缩放 expected_minutes

    返回结构与 build_plan_spec 一致, 但数量更少、耗时更精准。
    兴趣优先排序由 plan_adjuster.adjust_plan_order (LLM) 后续处理。
    """
    nodes = BASELINE_PLANS.get(subject_code, [])
    if not nodes:
        return []

    time_factor = _time_compression_factor(
        int(profile_summary.get("available_time") or 0)
    )

    specs = []
    for node in nodes:
        steps = _select_steps_for_node(node, profile_summary)
        for step in steps:
            target_agent, action_type = STEP_AGENT_MAP[step["type"]]
            base_minutes = expected_minutes_for_difficulty(node["difficulty"])
            specs.append({
                "node_id": node["node_id"],
                "node_name": node["node_name"],
                "node_type": node["node_type"],
                "difficulty": node["difficulty"],
                "step_label": step["label"],
                "step_type": step["type"],
                "step_order": step["order"],
                "step_desc": step["desc_tpl"].format(name=node["node_name"]),
                "target_agent": target_agent,
                "action_type": action_type,
                "summary": f"{node['node_name']} · {step['label']}",
                "tag": _difficulty_tag(node["difficulty"]),
                "expected_minutes": max(15, round(base_minutes * time_factor)),
            })
    return specs


# ── 给 plan_agent 用的工具输入 ─────────────────────────

def list_step_types() -> list[str]:
    return [s["type"] for s in LEARNING_STEPS]


def get_step_label(step_type: str) -> str:
    for s in LEARNING_STEPS:
        if s["type"] == step_type:
            return s["label"]
    return step_type


# ── 供命令行调试用 ──────────────────────────────────

def debug_summary():
    """打印每个学科的 (node × step) 统计。"""
    for code in BASELINE_PLANS:
        n = len(BASELINE_PLANS[code])
        total = n * len(LEARNING_STEPS)
        print(f"{code}: {n} nodes × {len(LEARNING_STEPS)} steps = {total} plans")
