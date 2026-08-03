from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from ..prompts.profile_prompts import PROFILE_CONVERSATION_SYSTEM_PROMPT
from .llm_factory import build_llm
from .profile_common import MAX_ROUNDS, dumps_profile


def build_system_prompt(
    subject_display: str,
    current_round: int,
    profile_summary: dict,
    next_question: str | None,
    is_complete: bool,
    max_rounds: int = MAX_ROUNDS,
    extra_prompt: str | None = None,
) -> str:
    summary = dumps_profile(profile_summary) if profile_summary else "（暂无）"
    prompt = PROFILE_CONVERSATION_SYSTEM_PROMPT.format(
        subject_display=subject_display,
        current_round=current_round,
        max_rounds=max_rounds,
        profile_summary=summary,
        is_complete="true" if is_complete else "false",
        next_question=next_question or "（无）",
    )
    if extra_prompt:
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    return prompt


async def astream_profile_reply(
    *,
    subject_display: str,
    current_round: int,
    profile_summary: dict,
    next_question: str | None,
    is_complete: bool,
    history_messages: list[BaseMessage],
    max_rounds: int = MAX_ROUNDS,
    extra_prompt: str | None = None,
) -> AsyncIterator[str]:
    llm = build_llm(streaming=True)
    system_prompt = build_system_prompt(
        subject_display,
        current_round,
        profile_summary,
        next_question,
        is_complete,
        max_rounds,
        extra_prompt,
    )
    messages: list[BaseMessage] = [SystemMessage(content=system_prompt), *history_messages]

    # OpenAI 兼容 API 要求至少一条 user/human 消息，否则返回
    # "invalid params, chat content is empty (2013)"。开场白场景
    # (current_user=None, history=[]) 注入一条简短的占位消息。
    if not any(isinstance(m, HumanMessage) for m in messages):
        messages.append(
            HumanMessage(content="（用户尚未发言，请主动开始对话并提出第一个问题）")
        )

    async for chunk in llm.astream(messages):
        content = getattr(chunk, "content", "")
        if isinstance(content, str) and content:
            yield content
