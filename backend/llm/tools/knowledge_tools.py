"""
知识星图工具：AI agent 在画像构建流中可读 / 改 KnowledgeNode 分数。

- `get_knowledge_map`: 读整张知识星图
- `assess_and_update_knowledge_score`: **不能传分数**，只能传 evidence；
  内部调 KnowledgeAssessor（自适应跳变 + 解析失败重试 1 次）算 delta 再写回，
  并把本次 evidence 追加到 KnowledgeNode.evidence_log（审计追溯用）。

工具用 RunnableConfig 把 user_id / subject_code / round 注入，
避免 LLM 看到这些无关参数。
"""
import json
import time
from typing import Annotated

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolArg

from llm.agents.knowledge_assessor import get_assessor
from users.models import KnowledgeNode, Subject


def _get_subject(user_id: int, subject_code: str) -> Subject:
    """按 code 或 中文显示名查 Subject。LLM 容易传显示名。"""
    subject = Subject.objects.filter(user_id=user_id, name=subject_code).first()
    if subject:
        return subject
    code_by_display = {display: code for code, display in Subject.SUBJECT_CHOICES}
    if subject_code in code_by_display:
        subject = Subject.objects.filter(user_id=user_id, name=code_by_display[subject_code]).first()
        if subject:
            return subject
    raise ValueError(
        f"subject '{subject_code}' not found for user {user_id}. "
        f"Valid codes: {[c[0] for c in Subject.SUBJECT_CHOICES]}"
    )


def update_knowledge_score_from_evidence(
    *,
    user_id: int,
    subject_code: str,
    node_id: str,
    evidence: str,
    round_num: int = 0,
    metadata: dict | None = None,
) -> str:
    """根据证据更新知识点掌握度，供工具和后台任务复用。"""
    subject = _get_subject(user_id, subject_code)
    node = KnowledgeNode.objects.filter(subject=subject, node_id=node_id).first()
    if not node:
        return f"Error: node_id '{node_id}' not found in subject '{subject_code}'"

    prev_score = node.mastery
    result = get_assessor().assess(
        node_name=node.name,
        prev_score=prev_score,
        evidence=evidence or "（无证据）",
    )

    # 解析失败两次：不写库，原分不动
    if result.actual_delta == 0 and "parse_failed" in result.rationale:
        return (
            f"SKIP: {node.name} unchanged (prev={prev_score}) | "
            f"assessor parse failed: {result.raw_outputs}"
        )

    new_entry = {
        "round": round_num,
        "ts": int(time.time()),
        "evidence": evidence,
        "prev": prev_score,
        "new": result.new_score,
        "delta_norm": result.delta_norm,
        "actual_delta": result.actual_delta,
        "max_delta_used": result.max_delta_used,
        "rationale": result.rationale,
    }
    if isinstance(metadata, dict) and metadata:
        new_entry["metadata"] = metadata
    log = list(node.evidence_log or [])
    log.append(new_entry)

    node.mastery = result.new_score
    node.evidence_log = log
    node.save(update_fields=["mastery", "evidence_log", "updated_at"])

    return (
        f"OK: {node.name} {prev_score}->{result.new_score} "
        f"(Δ{result.actual_delta:+d}, adaptive_max={result.max_delta_used}) | "
        f"round={round_num} evidence#{len(log)} | {result.rationale}"
    )


@tool
def get_knowledge_map(
    subject_code: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """获取指定学科的完整知识星图。
    返回 JSON 数组：[{node_id, name, mastery, last_evidence_round?}, ...]
    如果学科下没有任何知识点，返回空数组 []。
    """
    user_id = config["configurable"]["user_id"]
    subject = _get_subject(user_id, subject_code)
    nodes = KnowledgeNode.objects.filter(subject=subject).order_by("node_id")
    return json.dumps(
        [
            {
                "node_id": n.node_id,
                "name": n.name,
                "mastery": n.mastery,
                "evidence_count": len(n.evidence_log or []),
            }
            for n in nodes
        ],
        ensure_ascii=False,
    )


@tool
def assess_and_update_knowledge_score(
    subject_code: str,
    node_id: str,
    evidence: str,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """根据用户对话证据更新某个知识点的掌握度。

    ⚠️ **不能直接传分数** —— 本工具不接受 new_score 参数。
    内部调用独立的 KnowledgeAssessor agent（自适应跳变 + 解析失败重试），
    根据你提供的 evidence 和该节点历史分值自动算 delta，并钳到自适应上限内：
      - prev < 30  → 最多 ±25
      - prev < 60  → 最多 ±20
      - prev < 90  → 最多 ±15
      - prev >= 90 → 最多 ±10
    评估 evidence 会追加到 evidence_log 用于审计。

    Args:
        subject_code: 学科 code（如 "data_structure"）
        node_id: 知识点 id（如 "DS01"）
        evidence: 用户对话中体现的认知证据，例：
                  "用户准确区分了栈(LIFO)和队列(FIFO)，并能举例栈的应用"
                  "用户混淆了堆和栈，错误地认为堆是 FIFO"

    Returns:
        形如 "OK: <name> <prev>-><new> | <rationale>" 的字符串。
        若 evidence 解析连续 2 次失败，返回 "SKIP: parse_failed"（不写库）。
    """
    user_id = config["configurable"]["user_id"]
    round_num = int(config["configurable"].get("round", 0))
    return update_knowledge_score_from_evidence(
        user_id=user_id,
        subject_code=subject_code,
        node_id=node_id,
        evidence=evidence,
        round_num=round_num,
    )


# 供后台评估 agent 使用
KNOWLEDGE_TOOLS = [get_knowledge_map, assess_and_update_knowledge_score]
