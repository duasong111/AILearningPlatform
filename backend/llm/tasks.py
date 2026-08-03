import asyncio
import json
import logging
import os

from asgiref.sync import sync_to_async
from celery import shared_task
from django.utils import timezone
from langchain_core.messages import AIMessage

from .agents.chat_agent import astream_chat_events, row_to_lc_message
from .agents.plan_agent import astream_plan_events, astream_plan_reply
from .agents.profile_common import MAX_ROUNDS, current_round_from_history
from .agents.profile_conversation_agent import astream_profile_reply
from .agents.profile_evaluator_agent import _profile_is_complete, evaluate_profile_round
from .chains.plan_chain import build_learning_plan
from .common import extract_json
from .runtime import amark_complete, apublish_event, mark_complete, mark_error, write_runtime_state

logger = logging.getLogger(__name__)


def _backfill_video_to_plan(
    *,
    user_id: int,
    record_id: int,
    video_uuid: str,
    state: str,
) -> None:
    """把 video_uuid + state 回填到对应 plan 上."""
    from plan.models import LearningPlan

    plans = LearningPlan.objects.filter(subject__user_id=user_id)
    for plan in plans:
        memory = dict(plan.memory or {})
        if memory.get("video_record_id") == record_id:
            # 新逻辑: 直接挂在 plan.memory 上
            memory["video_uuid"] = video_uuid
            memory["video_state"] = state
            plan.memory = memory
            plan.save(update_fields=["memory", "updated_at"])
            continue
        # 兼容老逻辑: 写在 items[] 里
        items = memory.get("items")
        if not isinstance(items, list):
            continue
        changed = False
        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("video_record_id") == record_id:
                it["video_uuid"] = video_uuid
                it["video_state"] = state
                changed = True
        if changed:
            memory["items"] = items
            plan.memory = memory
            plan.save(update_fields=["memory", "updated_at"])


def _load_context(conversation_id: int, ai_message_id: int, user_message_id: int):
    from django.db import close_old_connections
    from users.models import Conversation, Message

    # Celery task 启动后第一次访问数据库前，先清理死连接
    close_old_connections()

    conversation = Conversation.objects.select_related("subject", "subject__user").get(id=conversation_id)
    rows = list(
        Message.objects.filter(conversation_id=conversation_id)
        .exclude(id=ai_message_id)
        .order_by("created_at", "id")
    )
    current_user = None
    history_rows = []
    for row in rows:
        if row.id == user_message_id and current_user is None:
            current_user = row
            break
        history_rows.append(row)
    if current_user is None:
        raise Message.DoesNotExist(f"user message {user_message_id} not found in conversation {conversation_id}")
    ai_message = Message.objects.get(id=ai_message_id, conversation_id=conversation_id)
    return conversation, current_user, ai_message, history_rows


def _save_ai_message(ai_message_id: int, content: str, meta: dict | None = None) -> None:
    from django.db import close_old_connections
    from users.models import Message

    # 异步任务跑完 LLM 流式后, 数据库连接可能已经过期, 写库前刷新一下
    close_old_connections()
    updates = {"content": content}
    if meta:
        updates["meta"] = meta
    Message.objects.filter(id=ai_message_id).update(**updates)


def _save_sub_agent_message(conversation_id: int, subagent_type: str, content: str, extra_meta: dict | None = None) -> int:
    """将子智能体的输出保存为独立的 DB 消息（role='tool'），可在历史记录中渲染为带标签的气泡。"""
    from django.db import close_old_connections
    from users.models import Message

    close_old_connections()
    meta = {"sub_agent_type": subagent_type}
    if extra_meta:
        meta.update(extra_meta)
    msg = Message.objects.create(
        conversation_id=conversation_id,
        role="tool",
        content=content,
        meta=meta,
    )
    return msg.id


def _extract_exam_card(sub_output: str) -> dict | None:
    """从出题助手的测评输出中提取试卷卡片数据（标题、题量、session_id）。"""
    import re
    match = re.search(r"/app/exam\?session=(\d+)", sub_output)
    if not match:
        return None
    try:
        from quiz.models import ExamSession
        session = ExamSession.objects.get(id=int(match.group(1)))
        return {
            "title": session.search_query,
            "mcq_count": session.mcq_count,
            "essay_count": session.qa_count,
            "session_id": session.id,
        }
    except Exception:
        return None


def _fmt_duration(raw: str) -> str:
    """将 B 站时长格式化为可读文本。输入如 "189:45" 或 "4511:45"（分:秒）。"""
    if not raw or ":" not in raw:
        return raw
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            if minutes >= 60:
                h = minutes // 60
                m = minutes % 60
                return f"{h}小时{m}分{seconds}秒" if m > 0 else f"{h}小时{seconds}秒"
            return f"{minutes}分{seconds}秒"
        elif len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{h}小时{m}分{s}秒" if h > 0 else f"{m}分{s}秒"
        return raw
    except (ValueError, TypeError):
        return raw


def _extract_video_data(sub_output: str) -> dict | None:
    """从视频助手的输出中提取 B 站视频数据。

    兼容两种格式：
    1. 机器格式：bvid:xxx / title:xxx / duration:xxx / pic:xxx
    2. 人类格式：BVID：BVxxx / 时长：xx / 标题行在 BVID 上一行
    """
    import re

    bvid = ""
    title = ""
    duration = ""
    pic = ""
    m = re.search(r"(?:bvid|BVID)\s*[:：]\s*(BV[0-9A-Za-z]+)", sub_output)
    if m:
        bvid = m.group(1).strip()
    m = re.search(r"title:(.+?)(?:\n|$)", sub_output)
    if m:
        title = m.group(1).strip()
    m = re.search(r"duration:(\S+)", sub_output)
    if m:
        duration = _fmt_duration(m.group(1).strip())
    else:
        m = re.search(r"时长\s*[:：]\s*(.+?)(?:\n|$)", sub_output)
        if m:
            duration = m.group(1).strip()
    m = re.search(r"pic:(\S+)", sub_output)
    if m:
        pic = m.group(1).strip()

    if bvid and not title:
        lines = [line.strip() for line in sub_output.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if re.search(r"(?:bvid|BVID)\s*[:：]\s*" + re.escape(bvid), line):
                if idx > 0:
                    candidate = lines[idx - 1]
                    candidate = re.sub(r"^[\d①②③④⑤⑥⑦⑧⑨⑩]+[.、]?\s*", "", candidate)
                    candidate = re.sub(r"^[0-9]+️⃣\s*", "", candidate)
                    if candidate not in {"推荐视频", "📚 推荐视频"}:
                        title = candidate
                break

    if not bvid:
        return None
    return {
        "bvid": bvid,
        "title": title,
        "duration": duration,
        "pic": pic if not pic else (pic if pic.startswith("http") else f"https:{pic}"),
    }


async def _check_and_trigger_calibration(conversation, ai_message_id: int) -> None:
    """检查是否需要触发知识图谱校准，每5条消息触发一次。"""
    from users.models import Message

    # 统计当前对话的消息总数
    total_messages = await sync_to_async(
        Message.objects.filter(conversation=conversation).count
    )()

    # 每5条消息触发一次校准
    if total_messages > 0 and total_messages % 5 == 0:
        logger.info(
            "知识图谱校准触发: conversation_id=%d, 消息数=%d",
            conversation.id, total_messages
        )

        # 发送校准开始事件
        await apublish_event(
            ai_message_id,
            conversation.id,
            {
                "type": "calibration_start",
                "ai_message_id": ai_message_id,
                "total_messages": total_messages,
            }
        )

        # 触发后台校准任务
        from .tasks import run_knowledge_calibration_task
        run_knowledge_calibration_task.delay(
            conversation_id=conversation.id,
            ai_message_id=ai_message_id,
        )
    else:
        logger.debug(
            "知识图谱校准跳过: conversation_id=%d, 消息数=%d (需 %%5==0)",
            conversation.id, total_messages
        )


def _extract_doc_scenes(sub_output: str) -> dict | None:
    """从实践助手的输出中提取课件场景数据。

    解析输出中的 session_id:<id>，查询 PracticeSession 获取场景列表。
    """
    import re
    match = re.search(r"session_id:(\d+)", sub_output)
    if not match:
        return None
    try:
        from quiz.models import PracticeSession
        session = PracticeSession.objects.get(id=int(match.group(1)))
        return {
            "title": session.search_query,
            "language": session.language,
            "scene_count": session.scene_count,
            "scenes": session.scenes,
        }
    except Exception:
        return None


def _load_knowledge_snapshot(subject) -> list[dict]:
    from users.models import KnowledgeNode

    nodes = KnowledgeNode.objects.filter(subject=subject).order_by("node_id")
    return [
        {
            "node_id": node.node_id,
            "name": node.name,
            "mastery": node.mastery,
            "evidence_count": len(node.evidence_log or []),
        }
        for node in nodes
    ]


def _create_learning_plan(*, subject, conversation, plan_data: dict) -> dict:
    from plan.models import LearningPlan

    # difficulty 字段可能是数字（1-5）或字符串（low/medium/high），统一转为 int
    _DIFF_MAP = {"low": 1, "medium": 3, "high": 5}

    def _parse_difficulty(val) -> int:
        if val is None:
            return 1
        if isinstance(val, (int, float)):
            return int(val)
        if isinstance(val, str):
            return _DIFF_MAP.get(val.strip().lower(), 1)
        return 1

    plan = LearningPlan.objects.create(
        subject=subject,
        conversation=conversation,
        target_agent=plan_data["target_agent"],
        plan_difficulty=plan_data.get("difficulty") or plan_data.get("plan_difficulty") or LearningPlan.DIFFICULTY_MEDIUM,
        node_id=str(plan_data.get("node_id") or ""),
        node_name=plan_data.get("node_name") or plan_data.get("summary") or "",
        node_type=plan_data.get("node_type") or "",
        action_type=plan_data.get("action_type") or LearningPlan.ACTION_STUDY,
        difficulty=_parse_difficulty(plan_data.get("difficulty")),
        memory=plan_data.get("memory") or {},
        state=plan_data.get("state") or LearningPlan.STATE_PENDING,
        expected_minutes=int(plan_data.get("expected_minutes") or 30),
    )
    return plan.to_dict()


def _normalize_selected_plan_ids(meta: dict | None) -> list[int]:
    if not isinstance(meta, dict):
        return []
    raw_ids = meta.get("selected_plan_ids")
    if not isinstance(raw_ids, list):
        return []
    normalized: list[int] = []
    for value in raw_ids:
        try:
            normalized.append(int(value))
        except (TypeError, ValueError):
            continue
    # 去重并保序
    return list(dict.fromkeys(normalized))


def _get_conversation_agent_payload(conversation) -> dict:
    payload = getattr(conversation, "agent_payload", None)
    return payload if isinstance(payload, dict) else {}


def _resolve_selected_plan_ids(conversation, current_user) -> list[int]:
    payload_plan_ids = _normalize_selected_plan_ids(_get_conversation_agent_payload(conversation))
    if payload_plan_ids:
        return payload_plan_ids
    return _normalize_selected_plan_ids(current_user.meta)


def _build_plan_handoff(plan: dict) -> dict:
    memory = plan.get("memory") if isinstance(plan.get("memory"), dict) else {}
    focus_nodes = memory.get("focus_nodes") if isinstance(memory.get("focus_nodes"), list) else []
    return {
        "from_agent": "plan",
        "next_agent": plan.get("target_agent"),
        "payload": {
            "mode": "plan_driven",
            "plan_id": plan.get("id"),
            "difficulty": plan.get("difficulty"),
            "focus_nodes": focus_nodes,
        },
        "extra_prompt": str(memory.get("prompt") or "").strip() or None,
    }


def _save_conversation_handoff(conversation_id: int, handoff: dict) -> None:
    from users.models import Conversation

    Conversation.objects.filter(id=conversation_id).update(handoff=handoff or {})


def _build_practice_knowledge_evidence(*, question: dict, analysis_result: dict, user_answer: str) -> str:
    result = analysis_result.get("result") if isinstance(analysis_result.get("result"), dict) else {}
    verdict = str(result.get("verdict") or "ungraded")
    is_correct = result.get("is_correct")
    if is_correct is True or verdict == "correct":
        verdict_text = "用户回答正确，体现出较好的掌握情况"
    elif is_correct is False or verdict == "wrong":
        verdict_text = "用户回答错误，体现出理解偏差或掌握不牢"
    else:
        verdict_text = f"本次答题判定为 {verdict}"

    question_text = str(question.get("question_text") or question.get("title") or "").strip()
    correct_answer = str(result.get("correct_answer") or question.get("correct_answer") or "").strip()
    summary = str(result.get("summary") or analysis_result.get("analysis") or "").strip()
    node_name = str(question.get("knowledge_node_name") or question.get("topic") or "未知知识点").strip()

    return (
        f"知识点：{node_name}。"
        f"题目：{question_text or '（未提供题干）'}。"
        f"用户答案：{user_answer.strip() or '（空）'}。"
        f"参考答案：{correct_answer or '（未提供）'}。"
        f"判定：{verdict_text}。"
        f"解析摘要：{summary or '（无）'}。"
    )


def _extract_practice_verdict(analysis_result: dict) -> tuple[str, bool | None]:
    result = analysis_result.get("result") if isinstance(analysis_result.get("result"), dict) else {}
    verdict = str(result.get("verdict") or "ungraded")
    is_correct = result.get("is_correct")
    if isinstance(is_correct, bool):
        return verdict, is_correct
    if verdict == "correct":
        return verdict, True
    if verdict == "wrong":
        return verdict, False
    return verdict, None


def _should_remove_common_mistake(node, *, mastery_threshold: int = 60, consecutive_correct_required: int = 2) -> bool:
    if node is None or int(getattr(node, "mastery", 0) or 0) < mastery_threshold:
        return False

    log = list(getattr(node, "evidence_log", None) or [])
    correct_count = 0
    for entry in reversed(log):
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        if metadata.get("source") != "practice_with_answer":
            continue
        if metadata.get("is_correct") is True:
            correct_count += 1
            if correct_count >= consecutive_correct_required:
                return True
            continue
        return False
    return False


def _maybe_update_profile_from_practice(*, quiz_record, question: dict, analysis_result: dict):
    verdict, is_correct = _extract_practice_verdict(analysis_result)
    node_name = str(question.get("knowledge_node_name") or "").strip()
    if not node_name:
        return None

    from users.models import KnowledgeNode
    from users.profile_store import add_common_mistake, remove_common_mistake

    node = KnowledgeNode.objects.filter(
        subject=quiz_record.subject,
        node_id=str(question.get("knowledge_node_id") or "").strip(),
    ).only("mastery", "evidence_log").first()

    if is_correct is False or verdict == "wrong":
        common_mistakes = add_common_mistake(quiz_record.subject, node_name)
        return {
            "common_mistakes": common_mistakes,
            "added_node": node_name,
            "removed_node": None,
        }

    if is_correct is True or verdict == "correct":
        if _should_remove_common_mistake(node):
            common_mistakes = remove_common_mistake(quiz_record.subject, node_name)
            return {
                "common_mistakes": common_mistakes,
                "added_node": None,
                "removed_node": node_name,
            }
        return None

    return None


def _maybe_update_knowledge_from_practice(*, quiz_record, question_index: int, analysis_result: dict, user_answer: str | None):
    if not user_answer or not str(user_answer).strip():
        return None
    questions = quiz_record.questions if isinstance(quiz_record.questions, list) else []
    if question_index < 0 or question_index >= len(questions):
        return None

    question = questions[question_index]
    if not isinstance(question, dict):
        return None

    node_id = str(question.get("knowledge_node_id") or "").strip()
    if not node_id:
        return None

    evidence = _build_practice_knowledge_evidence(
        question=question,
        analysis_result=analysis_result,
        user_answer=str(user_answer),
    )

    from .tools.knowledge_tools import update_knowledge_score_from_evidence

    update_result = update_knowledge_score_from_evidence(
        user_id=quiz_record.user_id,
        subject_code=quiz_record.subject.name,
        node_id=node_id,
        evidence=evidence,
        round_num=0,
        metadata={
            "source": "practice_with_answer",
            "is_correct": _extract_practice_verdict(analysis_result)[1],
        },
    )
    return {
        "node_id": node_id,
        "node_name": str(question.get("knowledge_node_name") or "").strip() or None,
        "result": update_result,
        "profile_update": _maybe_update_profile_from_practice(
            quiz_record=quiz_record,
            question=question,
            analysis_result=analysis_result,
        ),
    }


# ── 调度意图解析（从模型输出中匹配子智能体名称） ──

# (匹配词列表, subagent_type)
# 注意：关键词要足够明确，避免日常对话误触发。
# 业务要求：出题 / 测评 / 考试 / 试卷 一律只走 practice_quiz，绝不分发到 exam。
_SCHEDULER_NAME_PATTERNS: list[tuple[list[str], str]] = [
    (["完整测评", "正式考试", "模拟考试", "测评", "考试", "出一份试卷", "出一套试卷",
      "试卷", "给我出题", "帮我出题", "来几道题", "出几道题", "出几道练习题",
      "来份试卷", "来一套题", "考考我", "做个测试", "做个练习"], "practice_quiz"),
    (["找教学视频", "搜索教学视频", "推荐视频", "找个视频"], "video"),
    (["生成课件", "创建课件", "生成实践场景", "生成教学场景"], "doc_assistant"),
    (["生成图解", "画图解", "生成流程图", "画流程图", "生成思维导图",
      "生成图文文档", "生成知识文档"], "doc_writer"),
]


def _parse_scheduler_intent(content: str) -> str | None:
    """从模型调度语中识别目标子智能体。"""
    if not content:
        return None
    for keywords, sa_type in _SCHEDULER_NAME_PATTERNS:
        for kw in keywords:
            if kw in content:
                return "practice_quiz" if sa_type == "exam" else sa_type
    return None


# ── 调度分发器映射 ──

_SCHEDULER_DISPATCHERS: dict[str, tuple[str, str, int]] = {
    "doc_assistant": ("doc_assistant", "实践助手", 1),  # 只生成 1 个实践场景
    "doc_writer": ("doc_writer", "图文助手", 1),  # 只生成 1 个章节，避免卡顿
    "video": ("video", "视频助手", 0),
    "practice_quiz": ("practice_quiz", "出题助手", 3),  # 生成 3 道练习题
}


def _build_dispatcher(subagent_type: str, user_id: int, user_text: str,
                      conversation_id: int, ai_message_id: int,
                      fallback_content: str, subject=None):
    """构建调度分发异步函数。返回一个 async callable。"""
    # 兜底保护：任何残留的 exam 调度都强制改写为 practice_quiz。
    if subagent_type == "exam":
        subagent_type = "practice_quiz"
    info = _SCHEDULER_DISPATCHERS.get(subagent_type)
    if not info:
        async def _unknown():
            logger.warning("tutor agent: 未知调度类型=%s", subagent_type)
            return fallback_content
        return _unknown

    _sa_type, _sa_name, _default_count = info

    async def _dispatch():
        logger.info("tutor agent: 调度 %s 接管。user_text=%s", _sa_type, user_text[:100])
        # sub_agent_start 时给前端下发"生成中"标志，让骨架屏立刻渲染。
        # practice_quiz 是出题场景，骨架屏预渲染 3 道占位；其它子能力走老逻辑不带 meta。
        start_event: dict = {
            "type": "sub_agent_start",
            "sub_agent_type": _sa_type,
            "ai_message_id": ai_message_id,
        }
        if _sa_type == "practice_quiz":
            start_event["meta"] = {
                "quiz_status": "generating",
                "expected_count": _default_count,
            }
        await apublish_event(ai_message_id, conversation_id, start_event)
        try:
            # 根据类型选择工具工厂和调用参数
            if _sa_type == "doc_assistant":
                from .agents.tutor_agent import _make_doc_assistant_tools
                tools = _make_doc_assistant_tools(user_id)
                sub_output = await sync_to_async(tools[0].invoke)(
                    {"topic": user_text.strip(), "language": "zh-CN", "scene_count": _default_count})
            elif _sa_type == "doc_writer":
                from .agents.tutor_agent import _make_doc_writer_tools
                tools = _make_doc_writer_tools(user_id)
                sub_output = await sync_to_async(tools[0].invoke)(
                    {"topic": user_text.strip(), "language": "zh-CN", "section_count": _default_count})
            elif _sa_type == "video":
                from .agents.tutor_agent import _make_video_tools
                tools = _make_video_tools(subject)
                sub_output = await sync_to_async(tools[0].invoke)({"topic": user_text.strip()})
            elif _sa_type == "practice_quiz":
                # 出 3 道选择题快测，对话气泡内嵌卡片渲染，不创建 ExamSession
                from .agents.tutor_agent import _make_practice_quiz_tools
                tools, quiz_questions = _make_practice_quiz_tools(user_id, subject)
                # tools[0] 是纯 async 函数，不走 LangChain BaseTool，直接传 kwargs 调用
                sub_output = await tools[0](
                    search_query=user_text.strip(),
                    mcq_count=_default_count,
                    extra_prompt=user_text.strip(),
                )
            else:
                sub_output = f"未知调度类型：{_sa_type}"

            if hasattr(sub_output, "content"):
                sub_output = str(sub_output.content)
            elif not isinstance(sub_output, str):
                sub_output = str(sub_output)

            # 提取元数据并构建摘要文本
            extra_meta = None
            sub_event_meta = None
            display_text = sub_output

            if _sa_type in ("doc_assistant", "doc_writer"):
                doc_scenes = await sync_to_async(_extract_doc_scenes)(sub_output)
                if doc_scenes:
                    extra_meta = {"doc_scenes": doc_scenes}
                    sub_event_meta = {"doc_scenes": doc_scenes}
                    label = "课件" if _sa_type == "doc_assistant" else "图文文档"
                    unit = "场景" if _sa_type == "doc_assistant" else "章节"
                    action = "交互学习" if _sa_type == "doc_assistant" else "阅读"
                    display_text = f"{label}「{doc_scenes['title']}」已生成，共 {doc_scenes['scene_count']} 个{unit}，下方可直接{action}。"
            elif _sa_type == "video":
                video_data = await sync_to_async(_extract_video_data)(sub_output)
                if video_data:
                    extra_meta = {"video": video_data}
                    sub_event_meta = {"video": video_data}
                    display_text = f"已找到「{video_data['title']}」"
                    if video_data.get("duration"):
                        display_text += f"（{video_data['duration']}）"
                    display_text += "，下方可直接观看。"
            elif _sa_type == "practice_quiz":
                # 题目已在 tools[0].ainvoke 调用期间写入 quiz_questions 闭包，
                # 直接读走即可。失败兜底：模型返回错误串时给空列表，前端按错误文案渲染。
                if quiz_questions:
                    extra_meta = {"questions": quiz_questions}
                    sub_event_meta = {
                        "quiz_status": "complete",
                        "questions": quiz_questions,
                        "count": len(quiz_questions),
                    }

            sub_msg_id = await sync_to_async(_save_sub_agent_message)(
                conversation_id, _sa_type, sub_output, extra_meta,
            )
            sub_event: dict = {"type": "sub_agent_end", "sub_agent_type": _sa_type,
                               "content": display_text, "ai_message_id": ai_message_id,
                               "sub_message_id": sub_msg_id}
            if sub_event_meta:
                sub_event["meta"] = sub_event_meta
            await apublish_event(ai_message_id, conversation_id, sub_event)

            return fallback_content or f"好的，我让{_sa_name}帮你处理。"
        except Exception as _fe:
            logger.exception("%s dispatch failed: %s", _sa_type, _fe)
            err_event: dict = {
                "type": "sub_agent_end",
                "sub_agent_type": _sa_type,
                "content": f"处理失败：{_fe}",
                "ai_message_id": ai_message_id,
                "sub_message_id": 0,
            }
            if _sa_type == "practice_quiz":
                err_event["meta"] = {"quiz_status": "error", "message": str(_fe)}
            await apublish_event(ai_message_id, conversation_id, err_event)
            return fallback_content or f"好的，我让{_sa_name}帮你处理。"

    return _dispatch


def _extract_think_from_content(text: str) -> tuple[str, str]:
    """从文本中分离 `<think>...</think>` / `<thinking>...</thinking>` 思考块和正文。

    MiniMax M3 / DeepAgent 会把推理过程包裹在 think/thinking 标签中，
    直接输出在 `content` 字段。这个函数提取思考块内容并返回清理后的正文。

    返回: (thinking_text, clean_body)
    """
    import re
    thinking_parts = re.findall(r"<think(?:ing)?>(.*?)</think(?:ing)?>", text, flags=re.DOTALL)
    thinking = "\n".join(p.strip() for p in thinking_parts if p.strip())
    # 去除完整的 <think>...</think> / <thinking>...</thinking> 块
    clean = re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.DOTALL)
    # 兜底：去除残余的未配对标签
    clean = re.sub(r"</?think(?:ing)?>", "", clean)
    # 清理可能残留的空白行
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return thinking, clean.strip()


def _strip_think_and_task_tags(text: str) -> str:
    """去除文本中的 `<think>`/`<thinking>`/`<task>` 标签及内容。"""
    import re
    # 去除 <think> / <thinking> 块
    clean = re.sub(r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.DOTALL)
    # 去除 <task> / </task> 标签及内容
    clean = re.sub(r"<task>.*?</task>", "", clean, flags=re.DOTALL)
    # 兜底：去除残余的未配对标签
    clean = re.sub(r"</?think(?:ing)?>", "", clean)
    clean = re.sub(r"</?task>", "", clean)
    # 清理可能残留的空白行
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _strip_thinking_tags(text: str) -> str:
    """去除文本中的思考块标签（兼容旧接口，返回清理后的正文）。"""
    return _strip_think_and_task_tags(text)


def _extract_subagent_output(output) -> str:
    """从 task 工具的返回值中提取子智能体的最终文本输出。

    DeepAgent 的 task 工具返回 LangGraph Command 对象：
    Command(update={"messages": [ToolMessage(content="子智能体输出", ...)], ...})
    需要从 ToolMessage 中提取 content。
    """
    if isinstance(output, str):
        return _strip_thinking_tags(output)
    # Command 对象
    if hasattr(output, "update"):
        update = output.update
        if isinstance(update, dict):
            messages = update.get("messages", [])
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    raw = str(last_msg.content) if last_msg.content else ""
                    return _strip_thinking_tags(raw)
                if isinstance(last_msg, dict):
                    raw = str(last_msg.get("content", ""))
                    return _strip_thinking_tags(raw)
    # 其他对象尝试 content 属性
    if hasattr(output, "content"):
        raw = str(output.content) if output.content else ""
        return _strip_thinking_tags(raw)
    raw = str(output) if output else ""
    return _strip_thinking_tags(raw)


async def _run_tutor_agent_async(*, conversation, current_user, ai_message_id: int, history_rows) -> None:
    """运行私教多智能体（基于 DeepAgents）。"""
    from .agents.chat_agent import row_to_lc_message
    from .agents.tutor_agent import create_tutor_agent
    from .prompts.chat_prompts import TUTOR_AGENT_SYSTEM_PROMPT

    subject = conversation.subject
    user_id = subject.user_id
    subject_display = subject.get_display_name()
    subject_code = subject.name
    conversation_id = conversation.id
    extra_prompt = conversation.extra_prompt or None

    system_prompt = TUTOR_AGENT_SYSTEM_PROMPT.format(subject_display=subject_display, subject_code=subject_code)
    if extra_prompt:
        system_prompt += f"\n\n## 额外上下文\n{extra_prompt}"

    # 构建历史消息：把子智能体输出（role='tool'）转换为可读文本，让 tutor 能回答追问
    def _tool_row_to_text(row) -> str | None:
        """把子智能体消息转为可读文本摘要（用于 tutor 历史）。

        所有子智能体的输出都要展开，让 tutor 能在对话中讨论、追问。
        """
        meta = row.meta or {}
        sub_type = meta.get("sub_agent_type", "")
        if sub_type == "practice_quiz":
            q = meta.get("questions", [])
            if not q:
                return row.content
            lines = [f"【出题助手生成的题目（共{len(q)}题）】"]
            for i, item in enumerate(q, 1):
                text = item.get("question_text") or item.get("title") or "(无题干)"
                lines.append(f"{i}. {text}")
                opts = item.get("options") or []
                for oi, opt in enumerate(opts):
                    lines.append(f"   {chr(65+oi)}. {opt}")
                ans = item.get("correct_answer")
                if ans:
                    lines.append(f"   答案：{ans}")
                # 用户答案（如果有）
                user_ans = item.get("user_answer")
                if user_ans:
                    if ans and user_ans.upper() == ans.upper():
                        lines.append(f"   用户答案：{user_ans} ✓")
                    else:
                        lines.append(f"   用户答案：{user_ans} ❌")
                expl = item.get("explanation")
                if expl:
                    lines.append(f"   解析：{expl}")
            return "\n".join(lines)
        elif sub_type == "exam":
            card = meta.get("exam_card")
            if not card:
                return row.content
            # 尝试从 ExamSession 读取完整题目列表
            session_id = card.get("session_id")
            lines = [f"【出题助手生成的试卷】{card.get('title','')}（{card.get('mcq_count',0)}选择+{card.get('essay_count',0)}问答）"]
            if session_id:
                try:
                    from quiz.models import ExamSession
                    session = ExamSession.objects.get(id=session_id)
                    mcqs = session.multiple_choice or []
                    for i, mcq in enumerate(mcqs, 1):
                        q_text = mcq.get("question") or mcq.get("question_text") or "(无题干)"
                        lines.append(f"{i}. {q_text}")
                        opts = mcq.get("options") or []
                        for oi, opt in enumerate(opts):
                            lines.append(f"   {chr(65+oi)}. {opt}")
                        ans = mcq.get("answer") or mcq.get("correct_answer")
                        if ans:
                            lines.append(f"   答案：{ans}")
                        expl = mcq.get("explanation")
                        if expl:
                            lines.append(f"   解析：{expl}")
                    essays = session.essay or []
                    for i, es in enumerate(essays, len(mcqs) + 1):
                        q_text = es.get("question") or es.get("question_text") or "(无题干)"
                        lines.append(f"{i}. [问答题] {q_text}")
                        ref = es.get("reference_answer") or es.get("correct_answer")
                        if ref:
                            lines.append(f"   参考答案：{ref[:200]}...")
                except Exception:
                    pass
            return "\n".join(lines)
        elif sub_type == "video":
            v = meta.get("video")
            if not v:
                return row.content
            lines = [f"【视频助手推荐】{v.get('title','')}"]
            if v.get("bvid"):
                lines.append(f"BV号：{v.get('bvid')}")
            if v.get("duration"):
                lines.append(f"时长：{v.get('duration')}")
            # 简介（如果有）
            desc = v.get("description") or v.get("desc")
            if desc:
                lines.append(f"简介：{desc[:300]}...")
            return "\n".join(lines)
        elif sub_type in ("doc_assistant", "doc_writer"):
            doc = meta.get("doc_scenes")
            if not doc:
                return row.content
            lines = [f"【{sub_type}生成】{doc.get('title','')}"]
            scenes = doc.get("scenes") or []
            if scenes:
                lines.append(f"共 {len(scenes)} 个场景：")
                for i, sc in enumerate(scenes, 1):
                    sc_title = sc.get("title") or f"场景{i}"
                    lines.append(f"  {i}. {sc_title}")
            return "\n".join(lines)
        else:
            return row.content

    history_messages = []
    for row in history_rows:
        if row.role == "tool":
            txt = _tool_row_to_text(row)
            if txt:
                history_messages.append(AIMessage(content=txt))
        else:
            history_messages.append(
                row_to_lc_message(row.role, row.content, meta=row.meta or {}, tool_call_id=row.tool_call_id or "",
                                  tool_name=row.tool_name or "", tool_calls=row.tool_calls or [])
            )
    if current_user and current_user.role != "tool":
        history_messages.append(
            row_to_lc_message(current_user.role, current_user.content, meta=current_user.meta or {},
                              tool_call_id=current_user.tool_call_id or "", tool_name=current_user.tool_name or "",
                              tool_calls=current_user.tool_calls or [])
        )

    user_text = current_user.content if current_user else ""

    # 开场白触发（无用户消息时）：根据 extra_prompt 生成开场内容
    if not current_user and extra_prompt:
        user_text = extra_prompt

    # 显式意图优先按用户原始消息直达对应分发，
    # 不先让 tutor 自由生成，否则很容易出现“老师自己答”或误触发其它能力。
    direct_scheduled_type = _parse_scheduler_intent(user_text) if current_user else None
    if direct_scheduled_type in {"practice_quiz", "video", "doc_assistant", "doc_writer"}:
        await apublish_event(ai_message_id, conversation_id, {"type": "start", "ai_message_id": ai_message_id})
        logger.info(
            "tutor agent: direct dispatch type=%s from user_text=%s",
            direct_scheduled_type,
            user_text[:100],
        )
        fallback_map = {
            "practice_quiz": "好的，正在为你准备练习题。",
            "video": "好的，正在为你搜索相关教学视频。",
            "doc_assistant": "好的，正在为你生成课件。",
            "doc_writer": "好的，正在为你生成图文文档。",
        }
        _dispatch = _build_dispatcher(
            direct_scheduled_type,
            user_id,
            user_text,
            conversation_id,
            ai_message_id,
            fallback_map.get(direct_scheduled_type, "好的，正在为你处理。"),
            subject=subject,
        )
        full_content = await _dispatch()
        ai_meta = {"agent": "tutor"}
        await sync_to_async(_save_ai_message)(ai_message_id, full_content, ai_meta)
        await apublish_event(ai_message_id, conversation_id, {"type": "end", "ai_message_id": ai_message_id})
        await amark_complete(
            ai_message_id,
            conversation_id,
            full_content,
            meta=ai_meta,
        )
        await _check_and_trigger_calibration(conversation, ai_message_id)
        return

    from .agents.llm_factory import build_llm
    from .config import LLMProvider

    llm = build_llm(streaming=True, provider=LLMProvider.MINIMAX)
    agent = create_tutor_agent(model=llm, user_id=user_id, subject=subject)

    full_content = ""
    thinking_content = ""  # 思考过程单独存储，不混入正文
    current_sub_agent = ""
    had_real_subagent_dispatch = False
    _chunk_buffer = ""  # 批量缓冲 chunk，减少 Channel Layer 压力

    # ── <think> / <thinking> / <task> 标签检测状态机 ──
    # 这些标签都应该对用户不可见：think 是模型推理过程，task 是模型模拟的工具调用文本。
    # 流式传输中标签可能跨 chunk，需要用状态机正确拦截。
    _think_active = False       # 当前是否位于需隐藏的标签块内
    _hidden_tag_idx = 0         # 当前匹配的是哪个标签对（_HIDDEN_TAGS 索引）
    _tag_detect_buf = ""        # 小缓冲区用于跨 chunk 标签检测
    # 需要隐藏的标签对（开始标签 → 结束标签）
    _HIDDEN_TAGS = [
        ("<thinking>", "</thinking>"),
        ("<think>", "</think>"),
        ("<task>", "</task>"),
    ]

    async def _flush_chunk_buffer():
        """将缓冲区中的 chunk 批量发送，减少 Channel Layer 消息量。"""
        nonlocal _chunk_buffer
        if _chunk_buffer:
            await apublish_event(ai_message_id, conversation_id,
                                 {"type": "chunk", "ai_message_id": ai_message_id, "content": _chunk_buffer})
            # 同时写入 Redis，让轮询路径（200ms）作为备份，也支持断线重连恢复
            write_runtime_state(message_id=ai_message_id, conversation_id=conversation_id, content=full_content)
            _chunk_buffer = ""

    await apublish_event(ai_message_id, conversation_id, {"type": "start", "ai_message_id": ai_message_id})

    async for event in agent.astream_events({"messages": [*history_messages]}, version="v2"):
        event_name = event.get("event")
        event_name_lc = event.get("name", "")

        # ── 子智能体调度检测 ──
        # 只监听 on_tool_start/on_tool_end，因为 task 工具的事件结构最可靠。
        # on_chain_start/on_chain_end 是子智能体内部执行链，不作为调度信号。

        if event_name == "on_tool_start":
            # 先刷掉缓冲区中的 chunk，保证事件顺序
            await _flush_chunk_buffer()
            data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
            tool_input = data.get("input", {}) if isinstance(data, dict) else {}
            if isinstance(tool_input, dict) and "subagent_type" in tool_input:
                subagent_type = tool_input.get("subagent_type", "unknown")
                had_real_subagent_dispatch = True
                if subagent_type != current_sub_agent:
                    current_sub_agent = subagent_type
                    logger.info("tutor agent: sub_agent_start type=%s", subagent_type)
                    await apublish_event(ai_message_id, conversation_id,
                                         {"type": "sub_agent_start", "sub_agent_type": subagent_type,
                                          "ai_message_id": ai_message_id})

        elif event_name == "on_tool_end":
            await _flush_chunk_buffer()
            data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
            tool_input = data.get("input", {}) if isinstance(data, dict) else {}
            if isinstance(tool_input, dict) and "subagent_type" in tool_input:
                subagent_type = tool_input.get("subagent_type", current_sub_agent or "unknown")
                output = data.get("output", "")
                sub_output = _extract_subagent_output(output)
                logger.info("tutor agent: sub_agent_end type=%s output=%s", subagent_type, sub_output[:200])

                # 为出题助手返回的测评结果提取试卷卡片数据（用于前端渲染卡片样式）
                extra_meta = None
                sub_event_meta = None
                if subagent_type == "exam":
                    exam_card = await sync_to_async(_extract_exam_card)(sub_output)
                    if exam_card:
                        extra_meta = {"exam_card": exam_card}
                        sub_event_meta = {"exam_card": exam_card}
                elif subagent_type == "video":
                    video_data = await sync_to_async(_extract_video_data)(sub_output)
                    if video_data:
                        extra_meta = {"video": video_data}
                        sub_event_meta = {"video": video_data}
                        sub_output = (
                            f"已找到「{video_data['title']}」"
                            + (f"（{video_data['duration']}）" if video_data['duration'] else "")
                            + "，下方可直接观看。"
                        )
                elif subagent_type == "doc_assistant":
                    doc_scenes = await sync_to_async(_extract_doc_scenes)(sub_output)
                    if doc_scenes:
                        extra_meta = {"doc_scenes": doc_scenes}
                        sub_event_meta = {"doc_scenes": doc_scenes}
                        sub_output = (
                            f"课件「{doc_scenes['title']}」已生成，"
                            f"共 {doc_scenes['scene_count']} 个场景，下方可直接交互学习。"
                        )
                elif subagent_type == "doc_writer":
                    doc_scenes = await sync_to_async(_extract_doc_scenes)(sub_output)
                    if doc_scenes:
                        extra_meta = {"doc_scenes": doc_scenes}
                        sub_event_meta = {"doc_scenes": doc_scenes}
                        sub_output = (
                            f"图文文档「{doc_scenes['title']}」已生成，"
                            f"共 {doc_scenes['scene_count']} 个章节，下方可直接阅读。"
                        )

                # 将子智能体输出持久化到数据库，前端历史加载时可以渲染为带标签的独立气泡
                sub_msg_id = await sync_to_async(_save_sub_agent_message)(
                    conversation_id, subagent_type, sub_output, extra_meta,
                )
                event_data: dict = {"type": "sub_agent_end", "sub_agent_type": subagent_type,
                                    "content": sub_output, "ai_message_id": ai_message_id,
                                    "sub_message_id": sub_msg_id}
                if sub_event_meta:
                    event_data["meta"] = sub_event_meta
                await apublish_event(ai_message_id, conversation_id, event_data)
                current_sub_agent = ""

        elif event_name == "on_chat_model_stream":
            data = event.get("data", {})
            chunk = data.get("chunk")
            if chunk is None: continue

            # reasoning_patch.py 已将 reasoning_content 转移到 additional_kwargs。
            additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}
            reasoning = additional_kwargs.get("reasoning_content", "")

            # 思考内容（来自 reasoning_content）→ thinking_chunk
            if reasoning:
                thinking_content += reasoning
                await apublish_event(ai_message_id, conversation_id,
                                     {"type": "thinking_chunk", "ai_message_id": ai_message_id, "content": reasoning})

            # ── 从 content 中分离隐藏标签块和正文（状态机） ──
            raw_content = getattr(chunk, "content", "")
            if not isinstance(raw_content, str) or not raw_content:
                continue

            _tag_detect_buf += raw_content
            # 最大标签长度（</thinking> = 11），用于跨 chunk 保留缓冲
            _MAX_TAG_LEN = 11

            while _tag_detect_buf:
                if not _think_active:
                    # 扫描所有隐藏开始标签，找最早出现的
                    best_idx = -1
                    best_tag_idx = -1
                    for tag_i, (open_tag, _close_tag) in enumerate(_HIDDEN_TAGS):
                        pos = _tag_detect_buf.find(open_tag)
                        if pos != -1 and (best_idx == -1 or pos < best_idx):
                            best_idx = pos
                            best_tag_idx = tag_i

                    if best_idx == -1:
                        # 未找到任何开始标签
                        if len(_tag_detect_buf) > _MAX_TAG_LEN:
                            flush = _tag_detect_buf[:-_MAX_TAG_LEN]
                            _tag_detect_buf = _tag_detect_buf[-_MAX_TAG_LEN:]
                            if flush:
                                full_content += flush
                                _chunk_buffer += flush
                        break
                    else:
                        # 找到开始标签，之前的内容是正文
                        body_part = _tag_detect_buf[:best_idx]
                        open_tag = _HIDDEN_TAGS[best_tag_idx][0]
                        _tag_detect_buf = _tag_detect_buf[best_idx + len(open_tag):]
                        _hidden_tag_idx = best_tag_idx
                        _think_active = True
                        if body_part:
                            full_content += body_part
                            _chunk_buffer += body_part
                else:
                    # 只查找匹配的结束标签
                    close_tag = _HIDDEN_TAGS[_hidden_tag_idx][1]
                    idx = _tag_detect_buf.find(close_tag)

                    if idx == -1:
                        # 未找到结束标签
                        if len(_tag_detect_buf) > len(close_tag):
                            flush = _tag_detect_buf[:-len(close_tag)]
                            _tag_detect_buf = _tag_detect_buf[-len(close_tag):]
                            if flush:
                                thinking_content += flush
                                await apublish_event(ai_message_id, conversation_id,
                                                     {"type": "thinking_chunk", "ai_message_id": ai_message_id,
                                                      "content": flush})
                        break
                    else:
                        # 找到结束标签，之间的内容是隐藏内容
                        hidden_part = _tag_detect_buf[:idx]
                        _tag_detect_buf = _tag_detect_buf[idx + len(close_tag):]
                        _think_active = False
                        if hidden_part:
                            thinking_content += hidden_part
                            await apublish_event(ai_message_id, conversation_id,
                                                 {"type": "thinking_chunk", "ai_message_id": ai_message_id,
                                                  "content": hidden_part})

            # 批量发送正文 chunk
            if len(_chunk_buffer) >= 10:
                await _flush_chunk_buffer()

        # 记录其他事件类型，用于排查 DeepAgent 事件流结构
        elif event_name and event_name not in ("on_chat_model_start", "on_chat_model_end"):
            logger.debug("tutor agent: unhandled event=%s name=%s", event_name, event_name_lc)

    # 事件循环结束后，处理状态机中残留的内容
    if _tag_detect_buf:
        if _think_active:
            # 仍处于 <think> 块内（流结束时未闭合），将剩余内容作为思考过程
            thinking_content += _tag_detect_buf
            await apublish_event(ai_message_id, conversation_id,
                                 {"type": "thinking_chunk", "ai_message_id": ai_message_id,
                                  "content": _tag_detect_buf})
        else:
            # 不在 think 块内，剩余内容是正文
            # 但要清理可能的残余标签碎片（如 "<th" 这种永远不会闭合的片段）
            import re
            clean_rest = re.sub(r"</?t(?:h(?:i(?:n(?:k)?)?)?)?>?", "", _tag_detect_buf)
            if clean_rest:
                full_content += clean_rest
                _chunk_buffer += clean_rest

    # 事件循环结束后刷掉残留的 chunk 缓冲
    await _flush_chunk_buffer()

    # ── 清理 <task>...</task> 标签（模型未真正调用 tool 时会在文本中模拟） ──
    if full_content:
        import re
        full_content = re.sub(r"<task>.*?</task>", "", full_content, flags=re.DOTALL)
        full_content = re.sub(r"</?task>", "", full_content)
        full_content = re.sub(r"\n{3,}", "\n\n", full_content).strip()
    if thinking_content:
        import re
        thinking_content = re.sub(r"<task>.*?</task>", "", thinking_content, flags=re.DOTALL)
        thinking_content = re.sub(r"</?task>", "", thinking_content)

    # ── 调度意图解析：从模型调度语中匹配子智能体名称 ──
    logger.info("tutor agent: 模型输出预览=%s", (full_content or "<空>")[:200])
    _scheduled_type = None if had_real_subagent_dispatch else _parse_scheduler_intent(full_content)

    if _scheduled_type:
        logger.info("tutor agent: 调度标记检测=%s user_text=%s", _scheduled_type, user_text[:100])
        _dispatch = _build_dispatcher(_scheduled_type, user_id, user_text, conversation_id,
                                       ai_message_id, full_content, subject=subject)
        full_content = await _dispatch()
    elif not full_content:
        # 模型没输出调度标记也没输出内容（异常情况），保留空内容兜底
        full_content = "好的，请告诉我你需要什么帮助？"

    if full_content:
        ai_meta = {"agent": "tutor"}
        if thinking_content.strip():
            ai_meta["thinking_content"] = thinking_content
        await sync_to_async(_save_ai_message)(ai_message_id, full_content, ai_meta)

    await apublish_event(ai_message_id, conversation_id, {"type": "end", "ai_message_id": ai_message_id})
    complete_meta = {"agent": "tutor"}
    if thinking_content.strip():
        complete_meta["thinking_content"] = thinking_content
    await amark_complete(
        ai_message_id,
        conversation_id,
        full_content,
        meta=complete_meta,
    )

    # ── 知识图谱校准：每5条消息触发一次 ──
    await _check_and_trigger_calibration(conversation, ai_message_id)


async def _run_chat_agent_async(
    *,
    conversation_id: int,
    ai_message_id: int,
    user_id: int,
    subject_display: str,
    subject_code: str,
    history_rows,
    extra_prompt: str | None = None,
) -> None:
    history_messages = [
        row_to_lc_message(
            row.role,
            row.content,
            meta=row.meta or {},
            tool_call_id=row.tool_call_id or "",
            tool_name=row.tool_name or "",
            tool_calls=row.tool_calls or [],
        )
        for row in history_rows
    ]
    full_content = ""
    async for event in astream_chat_events(
        subject_display=subject_display,
        subject_code=subject_code,
        user_id=user_id,
        history_messages=history_messages,
        extra_prompt=extra_prompt,
    ):
        if event.type == "start":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "start", "ai_message_id": ai_message_id},
            )
            continue
        if event.type == "end":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "end", "ai_message_id": ai_message_id},
            )
            continue
        if event.type == "thinking_start":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "thinking_start", "ai_message_id": ai_message_id},
            )
            continue
        if event.type == "thinking_chunk":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "thinking_chunk", "ai_message_id": ai_message_id, "content": event.content},
            )
            continue
        if event.type == "thinking_end":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "thinking_end", "ai_message_id": ai_message_id},
            )
            continue
        if event.type == "chunk":
            full_content += event.content
            write_runtime_state(message_id=ai_message_id, conversation_id=conversation_id, content=full_content)
            await apublish_event(
                ai_message_id,
                conversation_id,
                {"type": "chunk", "ai_message_id": ai_message_id, "content": event.content},
            )
            continue
        if event.type == "tool_call":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {
                    "type": "tool_call",
                    "ai_message_id": ai_message_id,
                    "tool_name": event.tool_name,
                    "tool_args": event.tool_args,
                    "tool_call_id": event.tool_call_id,
                },
            )
            continue
        if event.type == "tool_result":
            await apublish_event(
                ai_message_id,
                conversation_id,
                {
                    "type": "tool_result",
                    "ai_message_id": ai_message_id,
                    "tool_name": event.tool_name,
                    "tool_output": event.tool_output,
                    "tool_call_id": event.tool_call_id,
                },
            )
    await sync_to_async(_save_ai_message, thread_sensitive=True)(ai_message_id, full_content)
    await amark_complete(
        ai_message_id,
        conversation_id,
        full_content,
        meta={"agent": "chat"},
    )

    # ── 知识图谱校准：每5条消息触发一次 ──
    from users.models import Conversation
    conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
    await _check_and_trigger_calibration(conversation, ai_message_id)


async def _run_profile_agent_async(*, conversation, current_user, ai_message_id: int, history_rows) -> None:
    from users.profile_store import get_profile_snapshot, save_profile_snapshot

    from django.db import close_old_connections

    # Celery async task 内部可能复用过期连接，访问数据库前先清理
    close_old_connections()

    history_messages = [
        row_to_lc_message(
            row.role,
            row.content,
            meta=row.meta or {},
            tool_call_id=row.tool_call_id or "",
            tool_name=row.tool_name or "",
            tool_calls=row.tool_calls or [],
        )
        for row in history_rows
    ]
    current_round = current_round_from_history(history_messages)
    subject = conversation.subject
    current_profile = await sync_to_async(get_profile_snapshot, thread_sensitive=True)(subject)

    # current_user=None 表示开场白触发（无用户消息）
    if current_user is not None:
        conversation_messages = history_messages + [
            row_to_lc_message(
                current_user.role,
                current_user.content,
                meta=current_user.meta or {},
                tool_call_id=current_user.tool_call_id or "",
                tool_name=current_user.tool_name or "",
                tool_calls=current_user.tool_calls or [],
            )
        ]
    else:
        conversation_messages = history_messages

    # 提前完成检查：画像已完整时跳过评估；开场白（无用户消息）也跳过评估
    if _profile_is_complete(current_profile):
        evaluation = {
            "profile": current_profile,
            "is_complete": True,
            "next_question": None,
        }
    elif current_user is None:
        # 开场白：无用户输入，跳过评估，让对话 agent 自主决定问什么
        evaluation = {
            "profile": current_profile,
            "is_complete": False,
            "next_question": None,
            "suggestions": ["考研备考", "兴趣学习", "期末复习", "提升技能"],
        }
    else:
        evaluation = await evaluate_profile_round(
            subject_code=subject.name,
            subject_display=subject.get_display_name(),
            chat_history=conversation_messages,
            current_profile=current_profile,
            current_round=current_round,
            max_rounds=MAX_ROUNDS,
        )

    profile = evaluation.get("profile", {})
    if profile:
        await sync_to_async(save_profile_snapshot, thread_sensitive=True)(subject, profile)

    full_content = ""

    await apublish_event(
        ai_message_id,
        conversation.id,
        {"type": "start", "ai_message_id": ai_message_id},
    )

    async for token in astream_profile_reply(
        subject_display=subject.get_display_name(),
        current_round=current_round,
        profile_summary=profile or current_profile,
        next_question=evaluation.get("next_question"),
        is_complete=bool(evaluation.get("is_complete")),
        history_messages=conversation_messages,
        extra_prompt=conversation.extra_prompt,
    ):
        full_content += token
        write_runtime_state(message_id=ai_message_id, conversation_id=conversation.id, content=full_content)
        await apublish_event(
            ai_message_id,
            conversation.id,
            {"type": "chunk", "ai_message_id": ai_message_id, "content": token},
        )

    await apublish_event(
        ai_message_id,
        conversation.id,
        {"type": "end", "ai_message_id": ai_message_id},
    )
    await sync_to_async(_save_ai_message, thread_sensitive=True)(ai_message_id, full_content)
    await amark_complete(
        ai_message_id,
        conversation.id,
        full_content,
        meta={
            "agent": "profile",
            "profile": profile,
            "next_question": evaluation.get("next_question"),
            "is_complete": bool(evaluation.get("is_complete")),
            "suggestions": evaluation.get("suggestions", []),
            "saved": bool(profile),
            "round": current_round,
            "max_rounds": MAX_ROUNDS,
            "subject_id": subject.id,
            "completion_options": ["continue_chat", "next_step"] if evaluation.get("is_complete") else [],
        },
    )


async def _run_plan_agent_async(*, conversation, current_user, ai_message_id: int, history_rows) -> None:
    """运行 Plan Agent

    支持两种模式：
    1. 生成模式（当前消息 meta 中无 selected_plan_ids）：生成新计划 + 流式回复
    2. 编辑模式（当前消息 meta 中包含 selected_plan_ids）：通过工具读写现有计划
    """
    from users.profile_store import get_profile_snapshot

    history_messages = [
        row_to_lc_message(
            row.role,
            row.content,
            meta=row.meta or {},
            tool_call_id=row.tool_call_id or "",
            tool_name=row.tool_name or "",
            tool_calls=row.tool_calls or [],
        )
        for row in history_rows
    ]
    subject = conversation.subject
    conversation_messages = history_messages + [
        row_to_lc_message(
            current_user.role,
            current_user.content,
            meta=current_user.meta or {},
            tool_call_id=current_user.tool_call_id or "",
            tool_name=current_user.tool_name or "",
            tool_calls=current_user.tool_calls or [],
        )
    ]

    # 优先从会话结构化配置读取选中的计划，再兼容旧版消息 meta。
    plan_ids = _resolve_selected_plan_ids(conversation, current_user)
    is_edit_mode = plan_ids is not None and len(plan_ids) > 0

    full_content = ""
    await apublish_event(
        ai_message_id,
        conversation.id,
        {"type": "start", "ai_message_id": ai_message_id},
    )

    if is_edit_mode:
        # 检测是否为预览模式
        is_preview = bool((current_user.meta or {}).get("preview"))
        knowledge_map = []
        if is_preview:
            knowledge_map = await sync_to_async(_load_knowledge_snapshot, thread_sensitive=True)(subject)

        # 编辑模式：使用 astream_plan_events（带工具）
        async for event in astream_plan_events(
            subject_display=subject.get_display_name(),
            subject_code=subject.name,
            user_id=subject.user_id,
            history_messages=conversation_messages,
            selected_plan_ids=plan_ids,
            extra_prompt=conversation.extra_prompt,
            preview=is_preview,
            knowledge_map=knowledge_map if is_preview else None,
        ):
            if event.type == "start":
                continue  # 已经在上面发送过 start
            elif event.type == "end":
                continue  # 会在下面发送 end
            elif event.type == "chunk":
                full_content += event.content
                write_runtime_state(message_id=ai_message_id, conversation_id=conversation.id, content=full_content)
                await apublish_event(
                    ai_message_id,
                    conversation.id,
                    {"type": "chunk", "ai_message_id": ai_message_id, "content": event.content},
                )
            elif event.type == "tool_call":
                await apublish_event(
                    ai_message_id,
                    conversation.id,
                    {
                        "type": "tool_call",
                        "ai_message_id": ai_message_id,
                        "tool_name": event.tool_name,
                        "tool_args": event.tool_args,
                        "tool_call_id": event.tool_call_id,
                    },
                )
            elif event.type == "tool_result":
                await apublish_event(
                    ai_message_id,
                    conversation.id,
                    {
                        "type": "tool_result",
                        "ai_message_id": ai_message_id,
                        "tool_name": event.tool_name,
                        "tool_output": event.tool_output,
                        "tool_call_id": event.tool_call_id,
                    },
                )

        if is_preview:
            # 预览模式：从 AI 输出中提取建议 JSON
            suggested_plan = None
            try:
                json_str = extract_json(full_content)
                if json_str:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        suggested_plan = parsed
            except Exception:
                logger.warning("plan preview: failed to extract JSON from output")

            # prompt 始终由系统确定性生成
            if suggested_plan and isinstance(suggested_plan.get("memory"), dict):
                from .chains.plan_chain import _build_agent_prompt

                target_agent = str(suggested_plan.get("target_agent") or "chat")
                difficulty = str(suggested_plan.get("difficulty") or "medium")
                memory = suggested_plan["memory"]
                focus_nodes = memory.get("focus_nodes") if isinstance(memory.get("focus_nodes"), list) else []
                summary = str(memory.get("summary") or "")
                suggested_plan["memory"]["prompt"] = _build_agent_prompt(
                    target_agent=target_agent,
                    focus_nodes=focus_nodes,
                    knowledge_map=knowledge_map,
                    difficulty=difficulty,
                    summary=summary,
                )

            plan_meta = {
                "agent": "plan",
                "subject_id": subject.id,
                "mode": "preview",
                "plan_ids": plan_ids,
                "suggested_plan": suggested_plan,
            }
        else:
            # 保存计划信息到 meta
            plan_meta = {
                "agent": "plan",
                "subject_id": subject.id,
                "mode": "edit",
                "plan_ids": plan_ids,
                "agent_payload": _get_conversation_agent_payload(conversation),
            }
    else:
        # 生成模式：生成多个计划 + 流式回复
        current_profile = await sync_to_async(get_profile_snapshot, thread_sensitive=True)(subject)
        knowledge_map = await sync_to_async(_load_knowledge_snapshot, thread_sensitive=True)(subject)
        plan_payloads = await build_learning_plan(
            subject_display=subject.get_display_name(),
            subject_code=subject.name,
            history_messages=conversation_messages,
            profile_summary=current_profile,
            knowledge_map=knowledge_map,
        )
        # 循环创建多条 plan
        saved_plans: list[dict] = []
        for plan_data in plan_payloads:
            saved = await sync_to_async(_create_learning_plan, thread_sensitive=True)(
                subject=subject,
                conversation=conversation,
                plan_data=plan_data,
            )
            saved_plans.append(saved)

        # handoff 用第一个 plan
        handoff = _build_plan_handoff(saved_plans[0]) if saved_plans else {}
        await sync_to_async(_save_conversation_handoff, thread_sensitive=True)(conversation.id, handoff)

        async for token in astream_plan_reply(
            subject_display=subject.get_display_name(),
            history_messages=conversation_messages,
            plan=saved_plans[0] if saved_plans else {},
            extra_prompt=conversation.extra_prompt,
        ):
            full_content += token
            write_runtime_state(message_id=ai_message_id, conversation_id=conversation.id, content=full_content)
            await apublish_event(
                ai_message_id,
                conversation.id,
                {"type": "chunk", "ai_message_id": ai_message_id, "content": token},
            )

        # 保存计划信息到 meta
        plan_meta = {
            "agent": "plan",
            "plans": saved_plans,
            "plan_count": len(saved_plans),
            "artifacts": {"plans": saved_plans},
            "handoff": handoff,
            "saved": True,
            "subject_id": subject.id,
            "mode": "generate",
        }

    await apublish_event(
        ai_message_id,
        conversation.id,
        {"type": "end", "ai_message_id": ai_message_id},
    )
    # 编辑模式（含 preview）的对话不持久化，只发 end 事件给前端
    if not is_edit_mode:
        await sync_to_async(_save_ai_message, thread_sensitive=True)(ai_message_id, full_content)
        await amark_complete(
            ai_message_id,
            conversation.id,
            full_content,
            meta=plan_meta,
        )


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_quiz_generation_task(self, *, subject_id: int, extra_prompt: str = "", count: int | None = None):
    """异步出题 Celery 任务。

    count 为 None 时自动决定数量：优先从 extra_prompt 提取，未提及则随机 3-5。

    结果保存在 Redis：
    - quiz:<task_id>:state → "generating" | "complete" | "error:<msg>"
    - quiz:<task_id>:result → JSON 题目列表（complete 时写入）

    前端通过 task_id 轮询状态即可。
    """
    from django.core.cache import cache

    from .chains.quiz_chain import QUIZ_TTL_SEC, agenerate_quiz, quiz_result_key, quiz_state_key

    task_id = self.request.id
    cache.set(quiz_state_key(task_id), "generating", QUIZ_TTL_SEC)
    try:
        questions = asyncio.run(
            agenerate_quiz(subject_id=subject_id, extra_prompt=extra_prompt, count=count)
        )
        result = [q.model_dump() for q in questions]
        cache.set(quiz_result_key(task_id), json.dumps(result, ensure_ascii=False), QUIZ_TTL_SEC)
        cache.set(quiz_state_key(task_id), "complete", QUIZ_TTL_SEC)
        from quiz.models import QuizGenerationRecord

        QuizGenerationRecord.objects.filter(task_id=task_id).update(
            state=QuizGenerationRecord.STATE_COMPLETE,
            questions=result,
            error_message="",
            completed_at=timezone.now(),
        )
        return result
    except Exception as exc:
        logger.exception("quiz generation failed: subject=%s task=%s", subject_id, task_id)
        cache.set(quiz_state_key(task_id), f"error:{exc}", QUIZ_TTL_SEC)
        from quiz.models import QuizGenerationRecord

        QuizGenerationRecord.objects.filter(task_id=task_id).update(
            state=QuizGenerationRecord.STATE_ERROR,
            error_message=str(exc),
            completed_at=None,
        )
        raise


PRACTICE_TTL_SEC = 3600


def practice_state_key(task_id: str) -> str:
    return f"practice:{task_id}:state"


def practice_result_key(task_id: str) -> str:
    return f"practice:{task_id}:result"


def practice_meta_key(task_id: str) -> str:
    return f"practice:{task_id}:meta"


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_practice_analysis_task(
    self,
    *,
    quiz_task_id: str,
    question_index: int = 0,
    mode: str = "with_answer",
    user_answer: str | None = None,
    subject_display: str = "未知学科",
    subject_code: str = "unknown",
):
    """异步题目分析 Celery 任务。

    从 Redis 读取 quiz chain 生成的题目，根据 mode 进行深度分析。

    mode 可选值：
    - "with_answer"：带答案分析，讲解知识点，分析用户回答对错
    - "without_answer"：无答案引导，只给分析思路，不给答案

    结果保存在 Redis：
    - practice:<task_id>:state → "generating" | "complete" | "error:<msg>"
    - practice:<task_id>:result → JSON 分析结果（complete 时写入）

    前端通过 task_id 轮询状态即可。
    """
    from django.core.cache import cache

    from .chains.practice_chain import analyze_quiz_question

    task_id = self.request.id
    cache.set(practice_state_key(task_id), "generating", PRACTICE_TTL_SEC)
    try:
        analysis = asyncio.run(
            analyze_quiz_question(
                quiz_task_id=quiz_task_id,
                question_index=question_index,
                mode=mode,
                user_answer=user_answer,
                subject_display=subject_display,
                subject_code=subject_code,
            )
        )
        result = analysis.model_dump()
        if mode == "with_answer":
            from quiz.models import QuizGenerationRecord

            quiz_record = (
                QuizGenerationRecord.objects.filter(task_id=quiz_task_id)
                .select_related("subject")
                .only("user_id", "subject__name", "questions")
                .first()
            )
            if quiz_record is not None:
                try:
                    knowledge_update = _maybe_update_knowledge_from_practice(
                        quiz_record=quiz_record,
                        question_index=question_index,
                        analysis_result=result,
                        user_answer=user_answer,
                    )
                except Exception:
                    logger.exception(
                        "practice knowledge update failed: quiz_task=%s question_index=%s task=%s",
                        quiz_task_id,
                        question_index,
                        task_id,
                    )
                    knowledge_update = {
                        "error": "knowledge_update_failed",
                    }
                if knowledge_update is not None:
                    result["knowledge_update"] = knowledge_update
        cache.set(practice_result_key(task_id), json.dumps(result, ensure_ascii=False), PRACTICE_TTL_SEC)
        cache.set(practice_state_key(task_id), "complete", PRACTICE_TTL_SEC)
        if mode == "with_answer":
            from quiz.models import PracticeAnalysisRecord

            PracticeAnalysisRecord.objects.filter(task_id=task_id).update(
                state=PracticeAnalysisRecord.STATE_COMPLETE,
                analysis=result,
                error_message="",
                completed_at=timezone.now(),
            )
        return result
    except Exception as exc:
        logger.exception("practice analysis failed: quiz_task=%s mode=%s task=%s", quiz_task_id, mode, task_id)
        cache.set(practice_state_key(task_id), f"error:{exc}", PRACTICE_TTL_SEC)
        if mode == "with_answer":
            from quiz.models import PracticeAnalysisRecord

            PracticeAnalysisRecord.objects.filter(task_id=task_id).update(
                state=PracticeAnalysisRecord.STATE_ERROR,
                error_message=str(exc),
                completed_at=None,
            )
        raise


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_conversation_agent_task(self, *, conversation_id: int, ai_message_id: int | None, user_message_id: int | None, agent_type: str):
    from django.db import close_old_connections

    # Celery task 启动时先清理死连接，再主动验证连接可用性
    # 避免 "connection already closed" 错误（Django CONN_HEALTH_CHECKS 对 Celery 不生效）
    close_old_connections()

    # Plan agent 不写 Redis 状态（ai_message_id=None），直接执行
    if agent_type == "plan":
        from users.models import Conversation

        conversation = Conversation.objects.select_related("subject", "subject__user").get(id=conversation_id)
        
        # 从 conversation.agent_payload 恢复用户消息内容
        payload = conversation.agent_payload or {}
        user_content = payload.get("user_content", "")
        
        # 模拟一个 current_user 结构（从 agent_payload 恢复）
        current_user = type("DummyUserMsg", (), {
            "role": "user",
            "content": user_content,
            "meta": payload,  # 包含 selected_plan_ids
            "tool_call_id": "",
            "tool_name": "",
            "tool_calls": [],
        })()
        asyncio.run(
            _run_plan_agent_async(
                conversation=conversation,
                current_user=current_user,
                ai_message_id=0,  # 占位，不写 Redis
                history_rows=[],
            )
        )
        return

    write_runtime_state(
        message_id=ai_message_id,
        conversation_id=conversation_id,
        state="generating",
        current_ai_msg=ai_message_id,
        ai_state="generating",
    )
    try:
        # user_message_id=0 表示开场白触发（无用户消息）
        if user_message_id == 0 and agent_type == "profile":
            from users.models import Conversation

            conversation = Conversation.objects.select_related("subject", "subject__user").get(id=conversation_id)
            asyncio.run(
                _run_profile_agent_async(
                    conversation=conversation,
                    current_user=None,
                    ai_message_id=ai_message_id,
                    history_rows=[],
                )
            )
            return

        if user_message_id == 0 and agent_type == "tutor":
            from users.models import Conversation

            conversation = Conversation.objects.select_related("subject", "subject__user").get(id=conversation_id)
            asyncio.run(
                _run_tutor_agent_async(
                    conversation=conversation,
                    current_user=None,
                    ai_message_id=ai_message_id,
                    history_rows=[],
                )
            )
            return

        conversation, current_user, _ai_message, history_rows = _load_context(conversation_id, ai_message_id, user_message_id)
        if agent_type == "profile":
            asyncio.run(
                _run_profile_agent_async(
                    conversation=conversation,
                    current_user=current_user,
                    ai_message_id=ai_message_id,
                    history_rows=history_rows,
                )
            )
            return
        if agent_type == "tutor":
            asyncio.run(
                _run_tutor_agent_async(
                    conversation=conversation,
                    current_user=current_user,
                    ai_message_id=ai_message_id,
                    history_rows=history_rows,
                )
            )
            return

        asyncio.run(
            _run_chat_agent_async(
                conversation_id=conversation_id,
                ai_message_id=ai_message_id,
                user_id=conversation.subject.user_id,
                subject_display=conversation.subject.get_display_name(),
                subject_code=conversation.subject.name,
                history_rows=history_rows + [current_user],
                extra_prompt=conversation.extra_prompt,
            )
        )
    except Exception as exc:
        logger.exception("conversation agent task failed: conversation=%s ai_message=%s", conversation_id, ai_message_id)
        mark_error(ai_message_id, conversation_id, str(exc))
        raise


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_video_course_generation_task(
    self,
    *,
    subject_id: int,
    topic: str,
    extra_prompt: str = "",
    knowledge_node_ids: list[str] | None = None,
    user_id: int | None = None,
):
    """异步生成视频课程 Celery 任务。

    流程:
    1. 调 video_chain.generate_video_course（LLM 提取大纲 + 调 OpenMAIC init）
    2. 写 Redis 状态 + VideoCourseRecord
    """
    from django.core.cache import cache

    from .chains.video_chain import (
        VIDEO_TTL_SEC,
        generate_video_course,
        video_result_key,
        video_state_key,
    )

    task_id = self.request.id
    cache.set(video_state_key(task_id), "generating", VIDEO_TTL_SEC)
    try:
        result = asyncio.run(
            generate_video_course(
                subject_id=subject_id,
                topic=topic,
                extra_prompt=extra_prompt,
                knowledge_node_ids=knowledge_node_ids,
            )
        )
        cache.set(
            video_result_key(task_id),
            json.dumps(
                {
                    "video_uuid": result["video_uuid"],
                    "iframe_url": result["iframe_url"],
                    "course": result["course"],
                },
                ensure_ascii=False,
            ),
            VIDEO_TTL_SEC,
        )
        cache.set(video_state_key(task_id), "complete", VIDEO_TTL_SEC)
        from video.models import VideoCourseRecord

        video_uuid = result["video_uuid"]
        course = dict(result["course"] or {})

        VideoCourseRecord.objects.filter(task_id=task_id).update(
            state=VideoCourseRecord.STATE_COMPLETE,
            course=course,
            video_uuid=video_uuid,
            iframe_url=result["iframe_url"],
            error_message="",
            completed_at=timezone.now(),
        )

        # 回填 plan.memory.items[].video_uuid + video_state = 'complete'
        # (前端 plan 列表可以直接通过 video_uuid 判断是否生成完成)
        try:
            from plan.models import LearningPlan

            record_obj = VideoCourseRecord.objects.filter(task_id=task_id).first()
            if record_obj is not None:
                _backfill_video_to_plan(
                    user_id=user_id,
                    record_id=record_obj.id,
                    video_uuid=result["video_uuid"],
                    state=VideoCourseRecord.STATE_COMPLETE,
                )
        except Exception:
            # 回填失败不影响主流程
            logger.exception("failed to backfill plan memory after video complete")

        return result
    except Exception as exc:
        logger.exception(
            "video course generation failed: subject=%s task=%s user=%s",
            subject_id,
            task_id,
            user_id,
        )
        cache.set(video_state_key(task_id), f"error:{exc}", VIDEO_TTL_SEC)
        from video.models import VideoCourseRecord

        VideoCourseRecord.objects.filter(task_id=task_id).update(
            state=VideoCourseRecord.STATE_ERROR,
            error_message=str(exc),
            completed_at=None,
        )
        raise


@shared_task(bind=True, autoretry_for=(), retry_backoff=False)
def run_knowledge_calibration_task(self, *, conversation_id: int, ai_message_id: int):
    """知识图谱校准任务：分析最近对话内容，更新知识点掌握度。"""
    from users.models import Conversation, Message, KnowledgeNode
    from .tools.knowledge_tools import update_knowledge_score_from_evidence
    from .runtime import apublish_event
    import json

    try:
        conversation = Conversation.objects.select_related("subject").get(id=conversation_id)
        subject = conversation.subject
        user_id = subject.user_id

        # 获取最近5条消息作为校准依据
        messages = list(
            Message.objects.filter(conversation=conversation)
            .order_by("-created_at")[:5]
        )

        if not messages:
            logger.warning("calibration: no messages found for conversation %d", conversation_id)
            return

        # 构建对话摘要作为 evidence
        evidence_parts = []
        for m in reversed(messages):  # 按时间正序
            role_label = "用户" if m.role == "user" else "AI"
            content_preview = m.content[:200] if m.content else ""
            evidence_parts.append(f"{role_label}: {content_preview}")
        evidence = "\n".join(evidence_parts)

        # 获取知识图谱
        nodes = list(KnowledgeNode.objects.filter(subject=subject))
        if not nodes:
            logger.info("calibration: no knowledge nodes for subject %d", subject.id)
            return

        # 简单策略：根据对话内容中的关键词匹配知识点
        # 实际可以更智能：用 LLM 提取 evidence 中的知识点
        updated_nodes = []
        for node in nodes[:3]:  # 最多校准3个相关知识点
            # 简单匹配：知识点名称出现在对话中
            if node.name in evidence or any(kw in evidence for kw in node.name.split()):
                result = update_knowledge_score_from_evidence(
                    user_id=user_id,
                    subject_code=subject.name,
                    node_id=node.node_id,
                    evidence=f"对话中提及或讨论了「{node.name}」",
                    round_num=len(messages) // 5,
                )
                if result.startswith("OK:"):
                    # 解析结果：OK: 链表 50->55 (Δ+5, adaptive_max=20) | ...
                    updated_nodes.append({
                        "name": node.name,
                        "node_id": node.node_id,
                        "result": result,
                    })

        # 发送校准完成事件
        asyncio.run(apublish_event(
            ai_message_id,
            conversation_id,
            {
                "type": "calibration_end",
                "ai_message_id": ai_message_id,
                "updated_count": len(updated_nodes),
                "updated_nodes": updated_nodes,
            }
        ))

        logger.info(
            "calibration complete: conversation=%d updated=%d nodes",
            conversation_id, len(updated_nodes)
        )

    except Exception as exc:
        logger.exception("calibration failed: conversation=%d", conversation_id)
        asyncio.run(apublish_event(
            ai_message_id,
            conversation_id,
            {
                "type": "calibration_end",
                "ai_message_id": ai_message_id,
                "error": str(exc),
            }
        ))
        raise
