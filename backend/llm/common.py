"""公共工具函数

这些函数被 chains、agents、tools 等多个模块共用。
放在 llm 根目录避免循环导入。
"""

import json

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage


MAX_ROUNDS = 15


def extract_json(text: str) -> str:
    """从 LLM 输出中提取 JSON 字符串"""
    text = text.strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text


def current_round_from_history(chat_history: list[BaseMessage]) -> int:
    """从对话历史计算当前轮次"""
    rounds = sum(1 for msg in chat_history if isinstance(msg, HumanMessage))
    return min(rounds + 1, MAX_ROUNDS)


def format_history(chat_history: list[BaseMessage]) -> str:
    """将对话历史格式化为文本"""
    lines = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, ToolMessage):
            role = f"tool:{msg.name or 'unknown'}"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            role = type(msg).__name__.lower()
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines) or "(空)"


def dumps_profile(profile: dict) -> str:
    """将画像字典序列化为 JSON 字符串"""
    return json.dumps(profile or {}, ensure_ascii=False)


def _has_text(value) -> bool:
    """检查值是否为非空文本"""
    return isinstance(value, str) and bool(value.strip())


def _has_non_empty_list(value) -> bool:
    """检查值是否为非空列表"""
    return isinstance(value, list) and any(str(item).strip() for item in value if item is not None)


def profile_is_complete(profile: dict) -> bool:
    """检查用户画像是否完整

    画像完整的标准（宽松版）：5 个维度中至少满足 2 个即视为完整
    - 有学习目标 (goal 或 priority)
    - 有知识基础 (level 或 strong/weak areas 或 recommended courses)
    - 有认知风格 (description 或 score)
    - 有可用时间 (available_time > 0)
    - 有兴趣方向 (interest_direction 非空)
    """
    learning_goal = profile.get("learning_goal") or {}
    knowledge_base = profile.get("knowledge_base") or {}
    cognitive_style = profile.get("cognitive_style") or {}

    has_goal = _has_text(learning_goal.get("goal")) or int(learning_goal.get("priority") or 0) > 0
    has_knowledge = (
        int(knowledge_base.get("level") or 0) > 0
        or _has_non_empty_list(knowledge_base.get("strong_areas"))
        or _has_non_empty_list(knowledge_base.get("weak_areas"))
        or _has_non_empty_list(knowledge_base.get("recommended_courses"))
    )
    has_cognitive = _has_text(cognitive_style.get("description")) or int(cognitive_style.get("score") or 0) > 0
    has_time = int(profile.get("available_time") or 0) > 0
    has_interest = _has_non_empty_list(profile.get("interest_direction"))

    return sum([has_goal, has_knowledge, has_cognitive, has_time, has_interest]) >= 2
