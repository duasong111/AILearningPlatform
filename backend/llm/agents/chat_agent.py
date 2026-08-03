"""普通聊天 Agent 的 LangChain 执行器。"""
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..prompts.chat_prompts import CHAT_AGENT_SYSTEM_PROMPT
from ..tools.knowledge_tools import get_knowledge_map
from ..tools.profile_tools import get_user_profile
from .llm_factory import build_llm


def _normalize_message_meta(meta) -> dict:
    return meta if isinstance(meta, dict) else {}


def _build_user_message_content(content: str, meta: dict | None) -> str:
    normalized_meta = _normalize_message_meta(meta)
    if not normalized_meta:
        return content
    hidden_context = json.dumps(normalized_meta, ensure_ascii=False)
    return (
        f"{content}\n\n"
        "【以下是前端同步的隐藏上下文，仅供你理解当前场景，不要直接向用户复述字段名或原始 JSON】\n"
        f"{hidden_context}"
    )


def row_to_lc_message(
    role: str,
    content: str,
    *,
    meta=None,
    tool_call_id: str = "",
    tool_name: str = "",
    tool_calls=None,
) -> BaseMessage:
    if role == "user":
        return HumanMessage(content=_build_user_message_content(content, meta))
    if role == "assistant":
        return AIMessage(content=content, tool_calls=tool_calls or [])
    if role == "tool":
        return ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name or "")
    raise ValueError(f"unknown role {role!r}")


@dataclass
class ChatAgentEvent:
    type: str
    content: str = ""
    tool_name: str = ""
    tool_args: dict | str | None = None
    tool_output: str = ""
    tool_call_id: str = ""


def build_system_prompt(subject_display: str, subject_code: str, extra_prompt: str | None = None) -> str:
    prompt = CHAT_AGENT_SYSTEM_PROMPT.format(
        subject_display=subject_display,
        subject_code=subject_code,
    )
    if extra_prompt:
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    return prompt


def _content_to_text(content) -> str:
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


def _normalize_tool_args(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return str(value)


def _get_stream_text(chunk) -> str:
    content = getattr(chunk, "content", "")
    return _content_to_text(content)


def _get_stream_reasoning(chunk) -> str:
    additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}
    reasoning = additional_kwargs.get("reasoning_content", "")
    return _content_to_text(reasoning)


def _extract_ai_text_from_event(event: dict) -> str:
    data = event.get("data", {})
    output = data.get("output")
    if isinstance(output, AIMessage):
        return _content_to_text(output.content)
    if isinstance(output, dict):
        messages = output.get("messages") or []
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                return _content_to_text(msg.content)
    if isinstance(output, list):
        for msg in reversed(output):
            if isinstance(msg, AIMessage):
                return _content_to_text(msg.content)
    return ""


async def astream_chat_events(
    *,
    subject_display: str,
    subject_code: str,
    user_id: int,
    history_messages: list[BaseMessage],
    extra_prompt: str | None = None,
) -> AsyncIterator[ChatAgentEvent]:
    agent = create_agent(
        build_llm(streaming=True, enable_thinking=True),
        [get_knowledge_map, get_user_profile],
        system_prompt=build_system_prompt(subject_display, subject_code, extra_prompt),
    )
    config = RunnableConfig(
        configurable={
            "user_id": user_id,
            "subject_code": subject_code,
            "round": 0,
        },
        recursion_limit=50,
    )
    emitted_text = ""
    thinking_active = False
    yield ChatAgentEvent(type="start")
    async for event in agent.astream_events(
        {"messages": history_messages},
        config=config,
        version="v2",
    ):
        event_name = event.get("event")
        if event_name == "on_tool_start":
            data = event.get("data", {})
            yield ChatAgentEvent(
                type="tool_call",
                tool_name=event.get("name", ""),
                tool_args=_normalize_tool_args(data.get("input")),
                tool_call_id=str(event.get("run_id", "")),
            )
            continue

        if event_name == "on_tool_end":
            data = event.get("data", {})
            yield ChatAgentEvent(
                type="tool_result",
                tool_name=event.get("name", ""),
                tool_output=_content_to_text(data.get("output")),
                tool_call_id=str(event.get("run_id", "")),
            )
            continue

        if event_name == "on_chat_model_stream":
            data = event.get("data", {})
            chunk = data.get("chunk")
            reasoning = _get_stream_reasoning(chunk)
            if reasoning:
                if not thinking_active:
                    thinking_active = True
                    yield ChatAgentEvent(type="thinking_start")
                yield ChatAgentEvent(type="thinking_chunk", content=reasoning)

            text = _get_stream_text(chunk)
            if text:
                if thinking_active:
                    thinking_active = False
                    yield ChatAgentEvent(type="thinking_end")
                emitted_text += text
                yield ChatAgentEvent(type="chunk", content=text)
            continue

        if event_name == "on_chat_model_end":
            final_text = _extract_ai_text_from_event(event)
            if final_text and len(final_text) > len(emitted_text):
                delta = final_text[len(emitted_text):]
                emitted_text = final_text
                if delta:
                    yield ChatAgentEvent(type="chunk", content=delta)
    if thinking_active:
        yield ChatAgentEvent(type="thinking_end")
    yield ChatAgentEvent(type="end")
