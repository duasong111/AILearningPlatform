"""出题 chain：根据知识星图、画像和动态提示词生成结构化题目。"""
import json
import random
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field, model_validator

from ..agents.llm_factory import build_llm
from ..prompts.quiz_prompts import QUIZ_GENERATION_SYSTEM_PROMPT
from ..schemas.quiz_schema import QuizQuestion

import logging
logger = logging.getLogger(__name__)


QUIZ_TTL_SEC = 3600


def quiz_state_key(task_id: str) -> str:
    """返回 quiz 任务状态的 Redis key。"""
    return f"quiz:{task_id}:state"


def quiz_result_key(task_id: str) -> str:
    """返回 quiz 任务结果的 Redis key。"""
    return f"quiz:{task_id}:result"


def quiz_meta_key(task_id: str) -> str:
    """返回 quiz 任务元信息的 Redis key。"""
    return f"quiz:{task_id}:meta"


class _QuizBatch(BaseModel):
    """批量出题的内部包装 schema。"""

    questions: list[QuizQuestion] = Field(description="生成的题目列表")

    @model_validator(mode="before")
    @classmethod
    def _strip_wrappers(cls, data):
        """LLM 输出可能混进 markdown fence / 思考标签，pydantic JSON 解析前先清干净.

        - 思考块 (deepseek / minimax reasoning)
        -  fenced json code block (```json ... ```)
        这样无论 langchain with_structured_output 内部是 model_validate_json
        (传 str) 还是 dict, validator 都能在解析前 sanitize.
        """
        if isinstance(data, str):
            data = re.sub(r"<(?:think|reasoning)>[\s\S]*?</(?:think|reasoning)>", "", data)
            m = re.search(r"```(?:json)?\s*(.*?)\s*```", data, re.DOTALL)
            if m:
                data = m.group(1)
            data = data.strip()
        return data

_COUNT_PATTERNS = [
    re.compile(r'出\s*(\d+)\s*[道题个]'),       # 出3道题、出3道
    re.compile(r'[来给写生成]\s*(\d+)\s*[道题个]'),  # 来3道、给3道题
    re.compile(r'(\d+)\s*道'),                   # 3道
    re.compile(r'(\d+)\s*题'),                   # 3题
    re.compile(r'(\d+)\s*个'),                   # 3个
]


def _extract_count_from_prompt(prompt: str) -> int | None:
    """从提示词中提取题目数量，未提及则返回 None。"""
    for pattern in _COUNT_PATTERNS:
        match = pattern.search(prompt)
        if match:
            n = int(match.group(1))
            if 1 <= n <= 20:
                return n
    return None


def _resolve_count(count: int | None, extra_prompt: str) -> int:
    """确定最终出题数量：显式传参 > 提示词中提及 > 随机 3-5。"""
    if count is not None:
        return count
    extracted = _extract_count_from_prompt(extra_prompt)
    if extracted is not None:
        return extracted
    return random.randint(3, 5)


def _load_subject_data(subject_id: int) -> tuple[object, str, str, list[dict], dict]:
    """加载 Subject、知识星图和画像，返回结构化数据。

    注意：此函数包含同步 DB 调用，如果在 async 上下文中使用，
    需要通过 sync_to_async 包装。

    sync_to_async(thread_sensitive=True) 会把我们调到 asgiref 的工作线程，
    那个线程有它自己的 thread-local DB connection，可能是上一轮 task 留下的
    stale connection（远程 Postgres 会把 idle 连接踢掉）。
    Celery 的 task_prerun 信号只在主线程跑，碰不到这个线程。
    所以这里必须自己再 close 一次，强制下面的 ORM 调用拿新连接。
    """
    from django.db import close_old_connections
    from users.models import KnowledgeNode, Subject
    from users.profile_store import get_profile_snapshot

    close_old_connections()

    subject = Subject.objects.get(id=subject_id)
    subject_display = subject.get_display_name()
    subject_code = subject.name

    nodes = KnowledgeNode.objects.filter(subject=subject).order_by("node_id")
    knowledge_map = [
        {
            "node_id": n.node_id,
            "name": n.name,
            "mastery": n.mastery,
        }
        for n in nodes
    ]

    profile = get_profile_snapshot(subject)
    return subject, subject_display, subject_code, knowledge_map, profile


def _build_messages(
    *,
    subject_display: str,
    subject_code: str,
    knowledge_map: list[dict],
    profile: dict,
    extra_prompt: str,
    count: int,
) -> list:
    """组装发给 LLM 的消息列表。"""
    profile_summary = json.dumps(profile, ensure_ascii=False, indent=2) if profile else "（暂无画像）"
    knowledge_map_text = json.dumps(knowledge_map, ensure_ascii=False) if knowledge_map else "（暂无知识星图数据）"

    if extra_prompt.strip():
        extra_instruction = f"## 用户额外要求\n{extra_prompt.strip()}"
    else:
        extra_instruction = ""

    system_content = QUIZ_GENERATION_SYSTEM_PROMPT.format(
        subject_display=subject_display,
        subject_code=subject_code,
        profile_summary=profile_summary,
        knowledge_map=knowledge_map_text,
        extra_instruction=extra_instruction,
    )

    user_content = f"请生成 {count} 道题目。"

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]


def _default_input_modes(question: QuizQuestion) -> list[str]:
    """根据题型和内容补齐默认作答方式。"""
    if question.question_type == "choice":
        return ["choice", "text", "image"]
    if question.code_snippet:
        return ["code", "text", "image"]
    return ["text", "image"]


def _normalize_generated_question(
    question: QuizQuestion, knowledge_map: list[dict] | None = None
) -> QuizQuestion:
    """为模型输出补齐少量可推断字段，避免前端拿到空结构。

    - knowledge_node_id / knowledge_node_name 是 LLM 偶发漏填的字段，schema 已经
      给了 default=""。这里如果发现是空的，从 knowledge_map 第一个节点兜底，
      防止下游"以知识点名拼字符串"那种地方拿到空串。
    """
    payload = question.model_dump()

    # 1. knowledge_node_* 兜底（先于其它字段，因为 title/next_steps 依赖它）
    fallback_node = (knowledge_map or [{}])[0] if knowledge_map else {}
    if not payload.get("knowledge_node_id"):
        payload["knowledge_node_id"] = fallback_node.get("node_id", "") or "UNKNOWN"
    if not payload.get("knowledge_node_name"):
        payload["knowledge_node_name"] = fallback_node.get("name", "") or "未指定知识点"

    # 2. 其它可推断字段
    if not payload.get("title"):
        payload["title"] = (question.question_text or payload["knowledge_node_name"])[:24]
    if not payload.get("input_modes"):
        payload["input_modes"] = _default_input_modes(question)
    if not payload.get("deep_analysis"):
        payload["deep_analysis"] = question.explanation
    if not payload.get("hints"):
        payload["hints"] = ["先定位本题考查的核心概念。", "再结合题目条件逐步缩小答案范围。"]
    if not payload.get("pitfalls"):
        payload["pitfalls"] = ["注意区分概念本身和题目中的具体场景。"]
    if not payload.get("next_steps"):
        payload["next_steps"] = [f"继续练习与 {payload['knowledge_node_name']} 相关的题目。"]
    return QuizQuestion(**payload)


async def agenerate_quiz(
    *,
    subject_id: int,
    extra_prompt: str = "",
    count: int | None = None,
) -> list[QuizQuestion]:
    """异步出题入口。

    Args:
        subject_id: Subject 表主键。
        extra_prompt: 动态提示词，如"侧重链表和栈"、"出 3 道关于排序的题"。
        count: 生成题目数量。传 None 时自动判断：
               优先从 extra_prompt 提取，未提及则随机 3-5。

    Returns:
        QuizQuestion 列表。
    """
    from asgiref.sync import sync_to_async
    from pydantic import ValidationError

    resolved_count = _resolve_count(count, extra_prompt)

    _, subject_display, subject_code, knowledge_map, profile = await sync_to_async(
        _load_subject_data, thread_sensitive=True
    )(subject_id)
    messages = _build_messages(
        subject_display=subject_display,
        subject_code=subject_code,
        knowledge_map=knowledge_map,
        profile=profile,
        extra_prompt=extra_prompt,
        count=resolved_count,
    )

    llm = build_llm(streaming=False, temperature=0.7)

    def _clean_str(s: str) -> str:
        s = re.sub(r"<(?:think|reasoning)>[\s\S]*?</(?:think|reasoning)>", "", s)
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, re.DOTALL)
        if m: s = m.group(1)
        return s.strip()

    structured_llm = llm.with_structured_output(_QuizBatch)

    async def _invoke_clean(msgs):
        try:
            return await structured_llm.ainvoke(msgs)
        except Exception as exc:
            logger.debug("structured output fallback: %s", exc)
            ai = await llm.ainvoke(msgs)
            text = ai.content if hasattr(ai, "content") else str(ai)
            return _QuizBatch.model_validate_json(_clean_str(text))

    # 一次 LLM 调用可能因 schema 校验失败（漏字段、类型错）抛 ValidationError。
    # 给一次重试机会，附加显式提示，避免偶发性失败让整批废掉。
    try:
        result = await _invoke_clean(messages)
    except ValidationError as exc:
        retry_messages = list(messages) + [
            HumanMessage(
                content=(
                    "上次输出违反了 schema，下面是 pydantic 的报错：\n"
                    f"{exc}\n\n"
                    "请严格按 schema 重新输出，特别注意：\n"
                    "- 每道题必须填 knowledge_node_id 和 knowledge_node_name；\n"
                    "- 所有字段类型严格匹配；\n"
                    "- 只输出 JSON，不要 markdown 标记或解释文字。"
                )
            )
        ]
        result = await _invoke_clean(retry_messages)

    return [_normalize_generated_question(q, knowledge_map) for q in result.questions]


