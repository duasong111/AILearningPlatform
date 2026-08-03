"""学习记录聚合查询。

不写表、不改表；只读 `users.Subject / users.KnowledgeNode`、
`learning.StudySession`、`quiz.PracticeAnalysisRecord`、`quiz.ExamSession`，
把已有真数据按前端学习记录页需要的 shape 计算出来。

所有函数都接收 `user`（不依赖 `request.user`），方便 view 层注入权限后的 user；
**绝不**返回别人的数据。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

from django.db.models import Q, Sum

logger = logging.getLogger(__name__)


# ============================================================
# 工具函数
# ============================================================


def week_range(d: date) -> tuple[date, date]:
    """给定任意日期，返回它所在自然周（周一到周日）的 [start, end]。

    Python `date.weekday()` 周一=0 周日=6。
    """
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


def _safe_get(d: dict | None, *path: str, default: Any = None) -> Any:
    """递归安全取嵌套 dict 的值。任一层不存在/不是 dict 就返 default。"""
    cur: Any = d or {}
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _subject_code_from_orm(subject) -> str:
    """把 ORM `Subject` 实例（或 str）归一化回前端 7 个 SubjectCode code。

    例：`<Subject: test@example.com - data_structure>` → `'data_structure'`
    """
    if subject is None:
        return ""
    if isinstance(subject, str):
        return subject
    return getattr(subject, "name", "") or ""


def _normalize_correct(c: Any) -> bool | None:
    """归一化 is_correct：bool 直接返；truthy 非 bool 视为 True；其它 None（未知判分）。"""
    if isinstance(c, bool):
        return c
    if c is None:
        return None
    if isinstance(c, (int, float)):
        return bool(c)
    if isinstance(c, str):
        s = c.strip().lower()
        if s in {"true", "yes", "1", "correct", "right"}:
            return True
        if s in {"false", "no", "0", "wrong", "incorrect"}:
            return False
    return None


def _build_summary_template(total_min: int, total_q: int, total_correct: int,
                            weak_names: list[str], top_names: list[str]) -> str:
    """用模板字符串拼 summary（不调 LLM，节省响应时延）。"""
    accuracy = (total_correct / total_q * 100) if total_q > 0 else 0
    parts: list[str] = []
    if total_min > 0:
        parts.append(f"本周共学习 {total_min} 分钟")
    if total_q > 0:
        parts.append(f"答题 {total_q} 道，命中率 {accuracy:.0f}%")
    if top_names:
        parts.append(f"表现最好：{'、'.join(top_names[:3])}")
    if weak_names:
        parts.append(f"建议巩固：{'、'.join(weak_names[:3])}")
    if not parts:
        return "本周暂无学习记录，快去刷一道题开始吧～"
    return "；".join(parts) + "。"


# ============================================================
# 1. 习题记录 —— 聚合 PracticeAnalysisRecord + ExamSession
# ============================================================


def compute_exercise_records(
    user,
    *,
    subject_code: str | None = None,
    correct: bool | None = None,
    start: date | None = None,
    end: date | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """聚合"我答过什么题、对不对"成 `ExerciseRecord[]`。

    Source A：`PracticeAnalysisRecord`（quiz 刷题的单题判分）
    Source B：`ExamSession`（综合测评已完成会的 mcq + essay）

    字段对齐前端 `ExerciseRecord`:
        id, timestamp, question, answer, correct, knowledge_node, subject
    """
    from quiz.models import ExamSession, PracticeAnalysisRecord

    items: list[dict[str, Any]] = []
    next_id = 1  # 统一给前端一个稳定递增 id（不暴露内部 db pk）

    # ---------- Source A: 刷题 PracticeAnalysisRecord ----------
    qs = (
        PracticeAnalysisRecord.objects
        .filter(user=user, state=PracticeAnalysisRecord.STATE_COMPLETE,
                mode=PracticeAnalysisRecord.MODE_WITH_ANSWER)
        .select_related("quiz_generation", "subject")
        .order_by("-created_at")
    )
    if subject_code:
        qs = qs.filter(subject__name=subject_code)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    for par in qs[:limit * 2]:  # 多取一些，下面再切 limit
        analysis = par.analysis or {}
        is_correct = _normalize_correct(_safe_get(analysis, "result", "is_correct"))

        # 取题目文本：优先从 quiz_generation.questions[i]
        question_text = ""
        knowledge_node = ""
        if par.quiz_generation_id and par.quiz_generation:
            questions = par.quiz_generation.questions or []
            if 0 <= par.question_index < len(questions):
                q = questions[par.question_index] or {}
                if isinstance(q, dict):
                    question_text = (
                        q.get("question_text")
                        or q.get("title")
                        or ""
                    )
                    knowledge_node = q.get("knowledge_node_name", "") or ""

        # 兜底：knowledge_node 从 analysis.key_knowledge_points[0]
        if not knowledge_node:
            kp = _safe_get(analysis, "key_knowledge_points", default=[])
            if isinstance(kp, list) and kp:
                knowledge_node = str(kp[0])

        if correct is not None and is_correct != correct:
            continue

        items.append({
            "id": next_id,
            "timestamp": par.created_at.isoformat() if par.created_at else "",
            "question": question_text or f"（题 #{par.question_index + 1}）",
            "answer": par.user_answer or "",
            "correct": is_correct,
            "knowledge_node": knowledge_node or "未分类",
            "subject": _subject_code_from_orm(par.subject),
        })
        next_id += 1
        if len(items) >= limit:
            break

    # ---------- Source B: 综合测评 ExamSession (completed) ----------
    if len(items) < limit:
        exam_qs = (
            ExamSession.objects
            .filter(user=user, status=ExamSession.STATUS_COMPLETED, mcq_score__isnull=False)
            .order_by("-completed_at")
        )
        # 按 subject 过滤 —— ExamSession 是按 search_query 模糊，无 subject FK
        # 简化策略：subject 过滤只对 PracticeAnalysisRecord 生效，ExamSession 全保留
        for exam in exam_qs:
            if start and exam.completed_at and exam.completed_at.date() < start:
                continue
            if end and exam.completed_at and exam.completed_at.date() > end:
                continue

            # MCQ 每题
            mcq = exam.multiple_choice or []
            mcq_answers = exam.mcq_answers or {}
            for i, q in enumerate(mcq if isinstance(mcq, list) else []):
                if not isinstance(q, dict):
                    continue
                qid = str(q.get("id", i))
                user_ans = mcq_answers.get(qid, "")
                correct_ans = q.get("answer", "")
                is_correct = _safe_get(q, "options") and (
                    user_ans.strip().upper() == (correct_ans or "").strip().upper()
                )
                is_correct = _normalize_correct(is_correct)
                if correct is not None and is_correct != correct:
                    continue
                items.append({
                    "id": next_id,
                    "timestamp": (exam.completed_at.isoformat()
                                  if exam.completed_at else exam.created_at.isoformat()),
                    "question": q.get("question") or q.get("question_text") or "",
                    "answer": user_ans,
                    "correct": is_correct,
                    "knowledge_node": str(q.get("knowledge_node_name") or q.get("topic") or "综合题"),
                    "subject": "",  # ExamSession 无 subject FK，留空
                })
                next_id += 1
                if len(items) >= limit:
                    break
            if len(items) >= limit:
                break

            # Essay 问答题（只展示，不强制判分）
            essay = exam.essay or []
            essay_answers = exam.essay_answers or {}
            for i, q in enumerate(essay if isinstance(essay, list) else []):
                if not isinstance(q, dict) or len(items) >= limit:
                    continue
                qid = str(q.get("id", i))
                user_ans = essay_answers.get(qid, "")
                items.append({
                    "id": next_id,
                    "timestamp": (exam.completed_at.isoformat()
                                  if exam.completed_at else exam.created_at.isoformat()),
                    "question": q.get("question") or q.get("question_text") or "",
                    "answer": user_ans,
                    "correct": None,  # 问答题无自动判分
                    "knowledge_node": str(q.get("knowledge_node_name") or q.get("topic") or "综合题"),
                    "subject": "",
                })
                next_id += 1

    return {
        "items": items[:limit],
        "total": len(items[:limit]),
    }


# ============================================================
# 2. 单周富周报 —— RichWeeklyReport 完整 16 字段
# ============================================================


def compute_rich_report(user, *, week_start: date) -> dict[str, Any]:
    """按 week_start（必须给周一）返回该周 RichWeeklyReport 的 dict。

    输入：用户、所在周的周一。
    输出：同前端 RichWeeklyReport 16 字段 shape，datetime/date 全部 isoformat 字符串。
    """
    from quiz.models import ExamSession, PracticeAnalysisRecord
    from users.models import KnowledgeNode

    week_end = week_start + timedelta(days=6)

    # ---- daily_minutes[7] ----
    # 取该周 7 天里每个 activity_type 累加；汇总到天维度
    from learning.models import StudySession
    sessions = (
        StudySession.objects
        .filter(user=user, date__gte=week_start, date__lte=week_end)
        .values("date", "duration_minutes")
    )
    daily_minutes: list[int] = [0] * 7
    for row in sessions:
        try:
            idx = (row["date"] - week_start).days  # 0-6
            if 0 <= idx <= 6:
                daily_minutes[idx] += int(row["duration_minutes"] or 0)
        except (TypeError, AttributeError):
            continue

    # ---- subject_distribution[] ----
    # 该用户该周有多少分钟/学科
    subj_rows = (
        StudySession.objects
        .filter(user=user, date__gte=week_start, date__lte=week_end)
        .values("subject__name")
        .annotate(minutes=Sum("duration_minutes"))
        .order_by("-minutes")
    )
    subject_distribution = [
        {"subject": _subject_code_from_orm(row["subject__name"]) or "unknown",
         "minutes": int(row["minutes"] or 0)}
        for row in subj_rows
        if row["subject__name"]
    ]

    # ---- mastery_distribution[5] (0-20/20-40/40-60/60-80/80-100) ----
    # 用该用户所有学科下 KnowledgeNode.mastery 全量分桶（跨所有学科）
    nodes = KnowledgeNode.objects.filter(subject__user=user).values_list("mastery", flat=True)
    buckets = [0] * 5
    for n in nodes:
        n = int(n or 0)
        idx = min(4, n // 20)  # 100/20=5 → 落到第 5 档（idx=4）
        if 0 <= idx <= 4:
            buckets[idx] += 1

    # ---- top_nodes[5] / weak_nodes[5] ----
    # 跨该用户所有学科，mastery 高/低取 5；并带 subject code
    node_qs = KnowledgeNode.objects.filter(subject__user=user).select_related("subject")
    top_qs = list(node_qs.order_by("-mastery", "node_id")[:5])
    weak_qs = list(node_qs.order_by("mastery", "node_id")[:5])
    top_nodes = [
        {"name": n.name, "subject": _subject_code_from_orm(n.subject),
         "mastery": int(n.mastery or 0)}
        for n in top_qs
    ]
    weak_nodes = [
        {"name": n.name, "subject": _subject_code_from_orm(n.subject),
         "mastery": int(n.mastery or 0)}
        for n in weak_qs
    ]

    # ---- daily_correctness[7] ----
    # 来源 1: PracticeAnalysisRecord 该周
    daily_correct: list[int] = [0] * 7
    daily_wrong: list[int] = [0] * 7
    par_qs = (
        PracticeAnalysisRecord.objects
        .filter(user=user, state=PracticeAnalysisRecord.STATE_COMPLETE,
                mode=PracticeAnalysisRecord.MODE_WITH_ANSWER,
                created_at__date__gte=week_start, created_at__date__lte=week_end)
    )
    for par in par_qs:
        is_correct = _normalize_correct(_safe_get(par.analysis or {}, "result", "is_correct"))
        if is_correct is None:
            continue
        try:
            idx = (par.created_at.date() - week_start).days
            if 0 <= idx <= 6:
                if is_correct:
                    daily_correct[idx] += 1
                else:
                    daily_wrong[idx] += 1
        except (TypeError, AttributeError):
            continue

    # 来源 2: ExamSession 该周 MCQ
    exam_qs = ExamSession.objects.filter(
        user=user, status=ExamSession.STATUS_COMPLETED,
        completed_at__date__gte=week_start, completed_at__date__lte=week_end,
    )
    for exam in exam_qs:
        try:
            idx = ((exam.completed_at or exam.created_at).date() - week_start).days
        except (TypeError, AttributeError):
            continue
        if not (0 <= idx <= 6):
            continue
        mcq = exam.multiple_choice or []
        mcq_answers = exam.mcq_answers or {}
        for q in mcq if isinstance(mcq, list) else []:
            if not isinstance(q, dict):
                continue
            qid = str(q.get("id", ""))
            user_ans = (mcq_answers.get(qid, "") or "").strip().upper()
            correct_ans = (q.get("answer", "") or "").strip().upper()
            if user_ans and correct_ans:
                if user_ans == correct_ans:
                    daily_correct[idx] += 1
                else:
                    daily_wrong[idx] += 1

    day_labels = []
    # 复用前端 "M/D" 习惯
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_labels.append(f"{d.month}/{d.day}")
    daily_correctness = [
        {"day": day_labels[i], "correct": daily_correct[i], "wrong": daily_wrong[i]}
        for i in range(7)
    ]

    # ---- 全周汇总 ----
    total_minutes = sum(daily_minutes)
    total_q = sum(daily_correct) + sum(daily_wrong)
    total_correct = sum(daily_correct)

    # subjects_studied: 只要该周某学科有 StudySession
    subjects_studied_codes: list[str] = []
    for s in subject_distribution:
        code = s["subject"]
        if code and code not in subjects_studied_codes:
            subjects_studied_codes.append(code)

    # nodes_mastered_count: 全量（跨周也是该用户的 mastery）
    nodes_mastered_count = KnowledgeNode.objects.filter(
        subject__user=user, mastery__gte=70,
    ).count()

    summary = _build_summary_template(
        total_min=total_minutes,
        total_q=total_q,
        total_correct=total_correct,
        weak_names=[n["name"] for n in weak_nodes],
        top_names=[n["name"] for n in top_nodes],
    )

    return {
        "id": (week_start - date(1970, 1, 1)).days,  # 用周一距 epoch 天数当稳定 id
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_minutes": total_minutes,
        "total_questions": total_q,
        "total_correct": total_correct,
        "subjects_studied": subjects_studied_codes,
        "nodes_mastered_count": nodes_mastered_count,
        "summary": summary,
        "daily_minutes": daily_minutes,
        "subject_distribution": subject_distribution,
        "mastery_distribution": buckets,
        "daily_correctness": daily_correctness,
        "top_nodes": top_nodes,
        "weak_nodes": weak_nodes,
    }


# ============================================================
# 3. 周报列表 —— 最近 N 周
# ============================================================


def compute_weekly_reports_list(user, *, max_weeks: int = 12) -> list[dict[str, Any]]:
    """计算最近 max_weeks 周（含当前周）的 RichWeeklyReport。

    返回按 week_start DESC 排序（最新在前），跟前端 mock 行为一致。
    """
    today = date.today()
    this_monday, _ = week_range(today)
    weeks: list[dict[str, Any]] = []
    for i in range(max_weeks):
        ws = this_monday - timedelta(weeks=i)
        weeks.append(compute_rich_report(user, week_start=ws))
    return weeks
