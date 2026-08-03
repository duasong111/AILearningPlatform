import json
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage


MAX_ROUNDS = 6


def extract_json(text: str) -> str:
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
    rounds = sum(1 for msg in chat_history if isinstance(msg, HumanMessage))
    return min(rounds + 1, MAX_ROUNDS)


def format_history(chat_history: list[BaseMessage]) -> str:
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
    return json.dumps(profile or {}, ensure_ascii=False)
