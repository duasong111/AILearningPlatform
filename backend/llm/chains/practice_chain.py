"""Practice Chain：分析 quiz chain 生成的题目。"""

import json

from django.core.cache import cache
from langchain_core.messages import HumanMessage, SystemMessage

from ..agents.llm_factory import build_llm
from ..prompts.practice_prompts import (
    PRACTICE_WITHOUT_ANSWER_SYSTEM_PROMPT,
    PRACTICE_WITH_ANSWER_SYSTEM_PROMPT,
)
from ..schemas.practice_schema import PracticeAnalysis
from .quiz_chain import quiz_result_key


class QuizNotFoundError(Exception):
    """Quiz 结果在 Redis 中不存在或已过期。"""
    pass


class QuestionIndexError(Exception):
    """指定的题目索引超出范围。"""
    pass


def _load_quiz_from_store(quiz_task_id: str) -> list[dict]:
    """优先从 Redis，其次从数据库加载题目列表。

    注意：此函数包含同步 cache 调用，如果在 async 上下文中使用，
    需要通过 sync_to_async 包装。
    """
    result_json = cache.get(quiz_result_key(quiz_task_id))
    if result_json is not None:
        try:
            questions = json.loads(result_json)
        except (json.JSONDecodeError, TypeError) as e:
            raise QuizNotFoundError(f"Quiz 结果 JSON 解析失败: {e}")
        if not isinstance(questions, list):
            raise QuizNotFoundError(f"Quiz 结果格式错误，期望 list，得到 {type(questions)}")
        return questions

    from quiz.models import QuizGenerationRecord

    record = QuizGenerationRecord.objects.filter(task_id=quiz_task_id).only("questions").first()
    if record is None or not isinstance(record.questions, list) or not record.questions:
        raise QuizNotFoundError(
            f"Quiz task {quiz_task_id} 的结果不存在或已过期，且数据库中也没有可用题目"
        )

    return record.questions


def _load_subject_info(quiz_task_id: str) -> tuple[str, str]:
    """从 quiz 结果中提取学科信息。"""
    # quiz result 里没有直接的 subject 信息，需要从其他地方获取
    # 但我们可以从第一个题目的 knowledge_node_name 推断学科
    # 或者让调用方传入 subject_display 和 subject_code
    # 这里先返回占位符，实际实现时可能需要调整
    return "未知学科", "unknown"


def _default_input_modes(question: dict) -> list[str]:
    """为旧题目结构补默认作答方式。"""
    if question.get("question_type") == "choice":
        return ["choice", "text", "image"]
    if question.get("code_snippet"):
        return ["code", "text", "image"]
    return ["text", "image"]


def _normalize_question_for_analysis(question: dict) -> dict:
    """兼容旧版 quiz 结果，补齐强结构题目字段。"""
    normalized = dict(question)
    normalized.setdefault("topic", normalized.get("knowledge_node_name", "未知主题"))
    normalized.setdefault("bloom_level", "理解")
    normalized.setdefault("title", normalized.get("question_text", "未命名题目"))
    normalized.setdefault("question_context", None)
    normalized.setdefault("code_snippet", None)
    normalized.setdefault("input_modes", _default_input_modes(normalized))
    normalized.setdefault("image_base64", None)
    normalized.setdefault("approach", "先定位题目考查的核心概念，再逐步分析题干条件。")
    normalized.setdefault("hints", [])
    normalized.setdefault("steps", [])
    normalized.setdefault("knowledge", [])
    normalized.setdefault("deep_analysis", normalized.get("explanation") or "")
    normalized.setdefault("pitfalls", [])
    normalized.setdefault("next_steps", [])
    return normalized


def _build_analysis_messages(
    *,
    mode: str,
    question: dict,
    user_answer: str | None,
    subject_display: str,
    subject_code: str,
) -> list:
    """根据模式构建发给 LLM 的消息。"""
    normalized_question = _normalize_question_for_analysis(question)
    question_payload = dict(normalized_question)
    if question_payload.get("image_base64"):
        question_payload["image_base64"] = "已提供 base64 图片内容"

    # 根据模式选择不同的 system prompt
    if mode == "with_answer":
        system_prompt = PRACTICE_WITH_ANSWER_SYSTEM_PROMPT.format(
            subject_display=subject_display,
            subject_code=subject_code,
        )

        user_content = json.dumps(
            {
                "question": question_payload,
                "user_answer": user_answer,
                "has_user_answer": bool(user_answer),
            },
            ensure_ascii=False,
            indent=2,
        )

    else:  # without_answer
        system_prompt = PRACTICE_WITHOUT_ANSWER_SYSTEM_PROMPT.format(
            subject_display=subject_display,
            subject_code=subject_code,
        )

        user_content = json.dumps(
            {
                "question": question_payload,
                "instruction": "请输出答题前阶段的引导式结构化分析，不要泄露完整答案。",
            },
            ensure_ascii=False,
            indent=2,
        )

    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]


async def analyze_quiz_question(
    *,
    quiz_task_id: str,
    question_index: int = 0,
    mode: str = "with_answer",
    user_answer: str | None = None,
    subject_display: str = "未知学科",
    subject_code: str = "unknown",
) -> PracticeAnalysis:
    """
    分析 quiz chain 生成的某道题目。

    Args:
        quiz_task_id: quiz chain 的 task_id，用于从 Redis 读取题目
        question_index: 题目在列表中的索引（从 0 开始）
        mode: 分析模式，"with_answer" 或 "without_answer"
        user_answer: 用户的回答（仅 with_answer 模式有效）
        subject_display: 学科中文名
        subject_code: 学科代码

    Returns:
        PracticeAnalysis: 分析结果

    Raises:
        QuizNotFoundError: quiz 结果不存在或已过期
        QuestionIndexError: 题目索引超出范围
    """
    from asgiref.sync import sync_to_async

    # 1. 从 Redis 加载题目
    questions = await sync_to_async(_load_quiz_from_store, thread_sensitive=True)(quiz_task_id)

    # 2. 验证索引
    if question_index < 0 or question_index >= len(questions):
        raise QuestionIndexError(
            f"题目索引 {question_index} 超出范围，共 {len(questions)} 道题"
        )

    question = _normalize_question_for_analysis(questions[question_index])

    # 3. 构建消息
    messages = _build_analysis_messages(
        mode=mode,
        question=question,
        user_answer=user_answer,
        subject_display=subject_display,
        subject_code=subject_code,
    )

    # 4. 调用 LLM 生成分析
    llm = build_llm(streaming=False, temperature=0.7)
    structured_llm = llm.with_structured_output(PracticeAnalysis)

    # LLM 偶发返回 markdown 代码块包裹的 JSON 或 JSON 字符串值中有未转义字符，
    # with_structured_output 的内置解析器无法处理，需多级降级。
    try:
        result = await structured_llm.ainvoke(messages)
    except Exception:
        # 降级 1：手动调用 LLM，剥离代码块后解析
        raw_result = await llm.ainvoke(messages)
        raw_text = raw_result.content if isinstance(raw_result.content, str) else str(raw_result.content)
        try:
            result = _parse_practice_analysis(raw_text)
        except Exception:
            # 降级 2：带显式提示重试一次 LLM 调用
            retry_messages = list(messages) + [
                HumanMessage(
                    content=(
                        "上次输出不是合法的 JSON。请严格输出纯 JSON，要求：\n"
                        "1. 不要用 ```json 代码块包裹\n"
                        '2. 字符串值中的双引号必须用 \\" 转义\n'
                        "3. 字符串值中的换行必须用 \\n 转义\n"
                        "4. 只输出 JSON 对象本身"
                    )
                )
            ]
            raw_result = await llm.ainvoke(retry_messages)
            raw_text = raw_result.content if isinstance(raw_result.content, str) else str(raw_result.content)
            result = _parse_practice_analysis(raw_text)

    return result


def _parse_practice_analysis(raw_text: str) -> PracticeAnalysis:
    """从 LLM 原始输出中提取并解析 PracticeAnalysis。

    处理 markdown 代码块包裹（```json ... ```）及常见 JSON 格式问题。
    """
    import re

    text = raw_text.strip()

    # 剥离 markdown 代码块
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # 尝试直接提取 JSON 对象（从第一个 { 到最后一个 }）
    if not text.startswith('{'):
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            text = text[start:end + 1]

    try:
        return PracticeAnalysis.model_validate_json(text)
    except Exception:
        # 尝试 json.loads 后再校验（json.loads 对某些容错更好）
        try:
            import json as _json
            parsed = _json.loads(text)
            return PracticeAnalysis.model_validate(parsed)
        except Exception:
            pass
        # 最后尝试：逐行修复常见的未转义问题
        # 将字符串值内部的裸换行替换为 \n
        fixed = text.replace('\n', '\\n')
        return PracticeAnalysis.model_validate_json(fixed)
