import copy
import json
import re

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from ..prompts.profile_prompts import PROFILE_EVALUATOR_SYSTEM_PROMPT
from .llm_factory import build_llm
from .profile_common import MAX_ROUNDS, dumps_profile, extract_json, format_history


def _extract_ai_text(result) -> str:
    if isinstance(result, AIMessage):
        return result.content if isinstance(result.content, str) else str(result.content)
    return ""


def _merge_profile(candidate: dict, current_profile: dict) -> dict:
    merged = copy.deepcopy(current_profile) if current_profile else {}
    if not isinstance(candidate, dict):
        candidate = {}

    for key, value in candidate.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    merged.setdefault("learning_goal", {"goal": "", "priority": 1, "target_date": "", "difficulty_level": "beginner"})
    merged.setdefault("knowledge_base", {"level": 0, "strong_areas": [], "weak_areas": [], "recommended_courses": []})
    merged.setdefault("cognitive_style", {"style_type": "analytical", "description": "", "score": 0})
    merged.setdefault("available_time", 0)
    merged.setdefault("interest_direction", [])
    merged.setdefault("common_mistakes", [])
    merged.setdefault("course", "")
    return merged


def _has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_non_empty_list(value) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value if item is not None)


def _profile_is_complete(profile: dict) -> bool:
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


def parse_evaluation_output(text: str, current_profile: dict, current_round: int, max_rounds: int = MAX_ROUNDS) -> dict:
    parsed: dict = {}
    try:
        parsed = json.loads(extract_json(text))
    except Exception:
        parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    profile = _merge_profile(parsed.get("profile", {}), current_profile)
    next_question = parsed.get("next_question")
    if isinstance(next_question, str):
        next_question = next_question.strip() or None
    else:
        next_question = None

    if next_question is None and not parsed.get("is_complete"):
        match = re.search(r"([^。\n]*[?？])", text[-300:])
        if match:
            next_question = match.group(1).strip()

    is_complete = bool(parsed.get("is_complete")) or _profile_is_complete(profile) or current_round >= max_rounds
    if is_complete:
        next_question = None

    suggestions = parsed.get("suggestions")
    if isinstance(suggestions, list):
        suggestions = [str(s).strip() for s in suggestions if str(s).strip()][:5]
    else:
        suggestions = []

    return {
        "profile": profile,
        "is_complete": is_complete,
        "next_question": next_question,
        "suggestions": suggestions,
    }


async def evaluate_profile_round(
    *,
    subject_code: str,
    subject_display: str,
    chat_history: list[BaseMessage],
    current_profile: dict,
    current_round: int,
    max_rounds: int = MAX_ROUNDS,
) -> dict:
    transcript = format_history(chat_history)
    prompt = (
        f"学科: {subject_display} ({subject_code})\n"
        f"当前轮次: {current_round}/{max_rounds}\n"
        f"当前画像摘要:\n{dumps_profile(current_profile)}\n\n"
        f"完整对话转录:\n{transcript}\n"
    )

    llm = build_llm(streaming=False, temperature=0.1)
    response = await llm.ainvoke([
        SystemMessage(content=PROFILE_EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    text = _extract_ai_text(response)
    return parse_evaluation_output(text, current_profile, current_round, max_rounds)
