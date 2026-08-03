"""Patch LangChain OpenAI chunk parsing to preserve reasoning_content."""


_PATCHED = False


def apply_reasoning_content_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    try:
        from typing import Any, Mapping, cast

        import langchain_openai.chat_models.base
        from langchain_core.messages import (
            AIMessageChunk,
            BaseMessageChunk,
            ChatMessageChunk,
            FunctionMessageChunk,
            HumanMessageChunk,
            SystemMessageChunk,
            ToolMessageChunk,
        )
        from langchain_core.messages.tool import tool_call_chunk
    except Exception:
        return

    def _patched_convert_delta_to_message_chunk(
        _dict: Mapping[str, Any], default_class: type[BaseMessageChunk]
    ) -> BaseMessageChunk:
        id_ = _dict.get("id")
        role = cast(str, _dict.get("role"))
        content = _dict.get("content")
        reasoning = _dict.get("reasoning_content")

        # Some OpenAI-compatible providers emit reasoning_content first and content later.
        if content is None and reasoning:
            content = ""
        else:
            content = cast(str, content or "")

        additional_kwargs = {}
        if reasoning:
            additional_kwargs["reasoning_content"] = reasoning
        if _dict.get("function_call"):
            function_call = dict(_dict["function_call"])
            if "name" in function_call and function_call["name"] is None:
                function_call["name"] = ""
            additional_kwargs["function_call"] = function_call
        tool_call_chunks = []
        if raw_tool_calls := _dict.get("tool_calls"):
            try:
                tool_call_chunks = [
                    tool_call_chunk(
                        name=rtc["function"].get("name"),
                        args=rtc["function"].get("arguments"),
                        id=rtc.get("id"),
                        index=rtc["index"],
                    )
                    for rtc in raw_tool_calls
                ]
            except KeyError:
                pass

        if role == "user" or default_class == HumanMessageChunk:
            return HumanMessageChunk(content=content, id=id_)
        if role == "assistant" or default_class == AIMessageChunk:
            return AIMessageChunk(
                content=content,
                additional_kwargs=additional_kwargs,
                id=id_,
                tool_call_chunks=tool_call_chunks,
            )
        if role in ("system", "developer") or default_class == SystemMessageChunk:
            if role == "developer":
                additional_kwargs = {"__openai_role__": "developer", **additional_kwargs}
            return SystemMessageChunk(
                content=content, id=id_, additional_kwargs=additional_kwargs
            )
        if role == "function" or default_class == FunctionMessageChunk:
            return FunctionMessageChunk(content=content, name=_dict["name"], id=id_)
        if role == "tool" or default_class == ToolMessageChunk:
            return ToolMessageChunk(
                content=content, tool_call_id=_dict["tool_call_id"], id=id_
            )
        if role or default_class == ChatMessageChunk:
            return ChatMessageChunk(content=content, role=role, id=id_)
        return default_class(content=content, id=id_)

    langchain_openai.chat_models.base._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk
    _PATCHED = True
