"""Plan Agent：学习计划对话编排

职责：
- 流式输出对话
- 调用 plan tools 读写计划
- 调用 plan chain 生成新计划

不包含：
- 计划生成的核心逻辑（在 plan_chain.py）
- 计划读写的具体实现（在 plan_tools.py）

设计原则（按节点×步骤粒度）：
  - 画像完成后该 subject 下会有 node_count * 5 个 plan（数据结构 54×5=270）
  - Plan Agent 不会一次性把这些 plan 塞进 LLM 上下文
  - LLM 通过 query_plans / get_progress_summary 按需查询
  - 用户说"链表我比较熟悉" → LLM 自调用 query_plans(node_name="链表") → 调 skip_plan / update_plan_state
  - 用户说"今天没时间" → LLM 自调用 query_plans(state="pending") → 按 expected_completion_time 重排
"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..prompts.plan_prompts import (
    PLAN_EDIT_SYSTEM_PROMPT,
    PLAN_PREVIEW_SYSTEM_PROMPT,
    PLAN_REPLY_SYSTEM_PROMPT,
)
from ..tools.plan_tools import (
    adjust_plan_difficulty,
    get_plan_detail,
    get_progress_summary,
    mark_plan_completed,
    query_plans,
    skip_plan,
    update_plan_state,
)
from .llm_factory import build_llm


@dataclass
class PlanAgentEvent:
    """Plan Agent 事件"""
    type: str  # "start", "chunk", "tool_call", "tool_result", "end"
    content: str = ""
    tool_name: str = ""
    tool_args: dict | None = None
    tool_output: str = ""
    tool_call_id: str = ""


def _normalize_tool_args(value):
    """规范化工具参数"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {"raw": value}
    return {}


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


def _get_stream_text(chunk) -> str:
    """从流式 chunk 中提取文本"""
    content = getattr(chunk, "content", "")
    return _content_to_text(content)


def build_plan_edit_instructions(selected_plan_ids: list[int] | None = None) -> str:
    """为已选中的计划构建编辑指令。"""
    if not selected_plan_ids:
        return ""
    ids_str = ", ".join(str(pid) for pid in selected_plan_ids)
    hash_ids = " ".join(f"#{pid}" for pid in selected_plan_ids)
    return f"""

## 用户当前选中的计划

用户消息中会以 #plan_id 形式引用选中的计划（如 {hash_ids}），表示用户想针对这些计划进行调整。
当前选中的计划 ID: {ids_str}

请先使用 get_plan_detail(plan_id=...) 工具查询这些计划的详细内容，再结合用户的指令进行修改。
"""


def build_system_prompt(
    subject_display: str,
    subject_code: str,
    *,
    selected_plan_ids: list[int] | None = None,
    extra_prompt: str | None = None,
) -> str:
    """构建系统提示词（编辑/协调模式）"""
    prompt = PLAN_EDIT_SYSTEM_PROMPT.format(
        subject_display=subject_display,
        subject_code=subject_code,
    )
    prompt += build_plan_edit_instructions(selected_plan_ids)
    if extra_prompt:
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    return prompt


def build_preview_system_prompt(
    subject_display: str,
    subject_code: str,
    *,
    selected_plan_ids: list[int],
    knowledge_map: list[dict],
    extra_prompt: str | None = None,
) -> str:
    """构建预览模式系统提示词（只读，不写库）"""
    km_lines = []
    for node in knowledge_map:
        name = node.get("name") or node.get("node_id") or "?"
        mastery = node.get("mastery") or 0
        km_lines.append(f"- {name}: mastery={mastery}")
    knowledge_map_text = "\n".join(km_lines) if km_lines else "暂无数据"

    prompt = PLAN_PREVIEW_SYSTEM_PROMPT.format(
        subject_display=subject_display,
        subject_code=subject_code,
        knowledge_map_text=knowledge_map_text,
        plan_ids_str=", ".join(str(pid) for pid in selected_plan_ids),
    )
    if extra_prompt:
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    return prompt


async def astream_plan_events(
    *,
    subject_display: str,
    subject_code: str,
    user_id: int,
    history_messages: list[BaseMessage],
    selected_plan_ids: list[int] | None = None,
    extra_prompt: str | None = None,
    preview: bool = False,
    knowledge_map: list[dict] | None = None,
) -> AsyncIterator[PlanAgentEvent]:
    """流式输出 Plan Agent 事件

    Args:
        subject_display: 学科显示名
        subject_code: 学科代码
        user_id: 用户 ID
        history_messages: 对话历史
        selected_plan_ids: 当前前端选中的计划 ID 列表
        extra_prompt: 额外提示词
        preview: 预览模式（只读，不写库）
        knowledge_map: 知识点掌握度（preview 模式下注入 prompt）

    Yields:
        PlanAgentEvent 事件流
    """
    if preview:
        # 预览模式：只给只读工具
        system_prompt = build_preview_system_prompt(
            subject_display,
            subject_code,
            selected_plan_ids=selected_plan_ids or [],
            knowledge_map=knowledge_map or [],
            extra_prompt=extra_prompt,
        )
        tools = [query_plans, get_plan_detail, get_progress_summary]
    else:
        # 编辑/协调模式：给全部工具（含写操作）
        system_prompt = build_system_prompt(
            subject_display,
            subject_code,
            selected_plan_ids=selected_plan_ids,
            extra_prompt=extra_prompt,
        )
        tools = [
            query_plans,
            get_plan_detail,
            get_progress_summary,
            update_plan_state,
            skip_plan,
            mark_plan_completed,
            adjust_plan_difficulty,
        ]

    agent = create_agent(
        build_llm(streaming=True),
        tools=tools,
        system_prompt=system_prompt,
    )

    config = RunnableConfig(
        configurable={
            "user_id": user_id,
            "subject_code": subject_code,
        },
        recursion_limit=50,
    )

    yield PlanAgentEvent(type="start")

    async for event in agent.astream_events(
        {"messages": history_messages},
        config=config,
        version="v2",
    ):
        event_name = event.get("event")

        if event_name == "on_tool_start":
            data = event.get("data", {})
            yield PlanAgentEvent(
                type="tool_call",
                tool_name=event.get("name", ""),
                tool_args=_normalize_tool_args(data.get("input")),
                tool_call_id=str(event.get("run_id", "")),
            )
            continue

        if event_name == "on_tool_end":
            data = event.get("data", {})
            yield PlanAgentEvent(
                type="tool_result",
                tool_name=event.get("name", ""),
                tool_output=_content_to_text(data.get("output")),
                tool_call_id=str(event.get("run_id", "")),
            )
            continue

        if event_name == "on_chat_model_stream":
            data = event.get("data", {})
            text = _get_stream_text(data.get("chunk"))
            if text:
                yield PlanAgentEvent(type="chunk", content=text)
            continue

    yield PlanAgentEvent(type="end")


async def astream_plan_reply(
    *,
    subject_display: str,
    history_messages: list[BaseMessage],
    plan: dict,
    extra_prompt: str | None = None,
) -> AsyncIterator[str]:
    """流式输出计划回复（用于生成新计划后的回复）

    兼容旧调用方式。新代码应使用 astream_plan_events。
    """
    llm = build_llm(streaming=True)
    system_prompt = PLAN_REPLY_SYSTEM_PROMPT
    if extra_prompt:
        system_prompt += f"\n\n## 额外指令\n{extra_prompt}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"学科: {subject_display}\n"
                f"计划对象:\n{json.dumps(plan, ensure_ascii=False)}\n"
            )
        ),
    ]

    async for chunk in llm.astream(messages):
        text = _content_to_text(getattr(chunk, "content", ""))
        if text:
            yield text
