"""用户画像只读工具。"""
import json
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolArg

from users.profile_store import get_profile_snapshot

from .knowledge_tools import _get_subject


@tool
def get_user_profile(
    subject_code: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """获取当前用户在指定学科下的学习画像摘要。

    返回 JSON 对象，包含 learning_goal、knowledge_base、cognitive_style、
    available_time、interest_direction、common_mistakes、course。
    """
    user_id = config["configurable"]["user_id"]
    subject = _get_subject(user_id, subject_code)
    profile = get_profile_snapshot(subject)
    has_profile = any(
        [
            bool((profile.get("learning_goal") or {}).get("goal")),
            bool((profile.get("knowledge_base") or {}).get("level")),
            bool((profile.get("interest_direction") or [])),
            bool((profile.get("common_mistakes") or [])),
            bool(profile.get("available_time")),
            bool(profile.get("course")),
        ]
    )
    return json.dumps(
        {
            "subject_code": subject.name,
            "subject_display": subject.get_display_name(),
            "has_profile": has_profile,
            "profile": profile,
        },
        ensure_ascii=False,
    )


PROFILE_TOOLS = [get_user_profile]
