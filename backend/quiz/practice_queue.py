"""新刷题接口 - Active Quiz Queue.

设计目标:
1. 后端掌控"未答 quiz 队列"的状态. 用户刷新页面只 GET, 不 POST.
2. ready 池数量维持 >= MIN_ACTIVE; 用户答完最后一道题时按需 ref to 补.
3. plan 来源优先:  source='plan' 的 quiz 在队列顶.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from django.core.cache import cache
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Subject, KnowledgeNode
try:
    from plan.models import LearningPlan
except ImportError:
    LearningPlan = None  # 计划模块未挂载时 (如初次部署) 仍能跑
from .models import QuizGenerationRecord
from .serializers import QuizGenerationRecordSerializer

log = logging.getLogger(__name__)

# 后端维持的最小 ready 池 (刷题页面初次进入时至少看到这些题)
MIN_ACTIVE_QUIZZES = 2
# 同时 in-flight 上限 (含 generating + ready)
MAX_INFLIGHT_QUIZZES = 4
# 默认每批题数
DEFAULT_COUNT_PER_BATCH = 5


def _subject_for_user(user, name: str) -> Optional[Subject]:
    """通过用户在 mySubjects 里的 instance 找对应 Subject.  如果找不到, 退回该用户的最近 quiz 记录中的 Subject."""
    # 1) MySubject (用户明确订阅的学科)
    try:
        from users.models import MySubject
        if name:
            ms = MySubject.objects.filter(user=user, name=name).first()
            if ms:
                subj = Subject.objects.filter(name=ms.name).first()
                if subj:
                    return subj
        # 看用户订阅过的任一学科
        ms_any = MySubject.objects.filter(user=user).first()
        if ms_any:
            subj = Subject.objects.filter(name=ms_any.name).first()
            if subj:
                return subj
    except Exception:
        pass
    # 2) 退回: 该用户任意 quiz 的 Subject
    last_quiz = (
        QuizGenerationRecord.objects.filter(user=user)
        .select_related("subject")
        .order_by("-id")
        .first()
    )
    if last_quiz:
        return last_quiz.subject
    if name:
        return Subject.objects.filter(name=name).first()
    return Subject.objects.first()


def _spawn_quiz_task(
    *,
    user,
    subject: Subject,
    extra_prompt: str,
    node_id: str,
    node_name: str,
    plan_obj=None,
    source: str = "normal",
) -> QuizGenerationRecord:
    """直接创建一条 QuizGenerationRecord + 派发 celery 任务.

    跟 QuizAutoGenerateView.post 类似的逻辑, 这里返回 record 让前端记 db id.
    """
    from llm.tasks import run_quiz_generation_task
    from llm.chains.quiz_chain import quiz_meta_key, QUIZ_TTL_SEC

    task = run_quiz_generation_task.delay(
        subject_id=subject.id,
        extra_prompt=extra_prompt,
        count=DEFAULT_COUNT_PER_BATCH,
    )
    record = QuizGenerationRecord.objects.create(
        user=user,
        subject=subject,
        task_id=task.id,
        extra_prompt=extra_prompt,
        requested_count=DEFAULT_COUNT_PER_BATCH,
        node_id=node_id,
        node_name=node_name,
        plan=plan_obj,
        state=QuizGenerationRecord.STATE_GENERATING,
        source=source,
    )
    cache.set(
        quiz_meta_key(task.id),
        json.dumps(
            {
                "user_id": user.id,
                "subject_id": subject.id,
                "subject_display": subject.get_display_name(),
                "subject_code": subject.name,
                "node_id": node_id,
                "node_name": node_name,
                "plan_id": plan_obj.id if plan_obj else None,
            },
            ensure_ascii=False,
        ),
        QUIZ_TTL_SEC,
    )
    return record


def _refill_active_quizzes(*, user, subject_name: str, plan_id: Optional[int], source: str) -> int:
    """检查用户当前未答 pool 数:  ready +  in-flight <  MIN_ACTIVE + 1 时补 spawn 一个新 batch.

    Returns: 这次新 spawn 的 quiz 数.
    """
    qs = QuizGenerationRecord.objects.filter(
        user=user,
        state__in=[
            QuizGenerationRecord.STATE_GENERATING,
            QuizGenerationRecord.STATE_COMPLETE,
        ],
        is_active=True,
        subject__name=subject_name,
    )
    if plan_id:
        qs = qs.filter(plan_id=plan_id)
    else:
        qs = qs.filter(plan__isnull=True)

    # 1.  检查 ready 池 (5 题中至少 1 题未答者算 active)
    active_ready = []
    active_inflight = 0
    for rec in qs.order_by("created_at"):
        if rec.state == QuizGenerationRecord.STATE_GENERATING:
            active_inflight += 1
            continue
        # ready (complete +  questions 解析 ok)
        if not rec.questions:
            continue
        progress = rec.item_progress or {}
        answered_count = sum(1 for v in progress.values() if v.get("answered"))
        if answered_count < len(rec.questions):
            active_ready.append(rec)

    if len(active_ready) >= MIN_ACTIVE_QUIZZES:
        return 0
    need = MIN_ACTIVE_QUIZZES - len(active_ready)
    if active_inflight + len(active_ready) >= MAX_INFLIGHT_QUIZZES:
        return 0

    # 2.  准备 spawn 参数
    subject = _subject_for_user(user, subject_name)
    if subject is None:
        log.warning("refill aborted: subject not found for %s", subject_name)
        return 0
    plan_obj = None
    node_id = ""
    node_name = ""
    extra_prompt = ""
    if plan_id:
        try:
            plan_obj = LearningPlan.objects.filter(user=user, id=plan_id).first()
            if plan_obj:
                node = KnowledgeNode.objects.filter(user=user, id=plan_obj.knowledge_node_id).first()
                if node:
                    node_id = str(node.id)
                    node_name = node.name
                extra_prompt = (
                    f"【计划聚焦】当前计划上下文: {plan_obj.title or '未命名'} "
                    f"({plan_obj.subject_id or subject_name})"
                )
        except Exception:
            log.exception("plan preparation failed")

    spawned = 0
    for _ in range(min(need, MAX_INFLIGHT_QUIZZES - active_inflight - len(active_ready))):
        try:
            _spawn_quiz_task(
                user=user,
                subject=subject,
                extra_prompt=extra_prompt,
                node_id=node_id,
                node_name=node_name,
                plan_obj=plan_obj,
                source=source if plan_obj else "normal",
            )
            spawned += 1
        except Exception:
            log.exception("spawn new quiz failed")
            break
    return spawned


class ActiveQuizQueueView(APIView):
    """GET /api/quiz/active-queue/?subject=<name>&plan=<id>

    返回按优先级排序的"用户当前可以刷"的 quiz 列表 (ready-only, 不返回 generating).

    后端在准备后顺便补 ready 池. **这个 view 永远不会被前端重新创建 quiz,
    仅是队 channel.**"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db import close_old_connections
        close_old_connections()

        subject_name = (request.query_params.get("subject") or "").strip()
        plan_id_raw = (request.query_params.get("plan") or "").strip()

        if not subject_name:
            return Response({"error": "subject is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan_id = int(plan_id_raw) if plan_id_raw else None
        except ValueError:
            return Response({"error": "plan must be int"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 后端补 填 ready 池
        _refill_active_quizzes(
            user=request.user,
            subject_name=subject_name,
            plan_id=plan_id,
            source="plan" if plan_id else "normal",
        )

        # 2. 取 ready  +  in-flight 都打回去 (前端可以展示 loading)
        qs = QuizGenerationRecord.objects.filter(
            user=request.user,
            is_active=True,
            subject__name=subject_name,
        )
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        else:
            qs = qs.filter(plan__isnull=True)
        # plan-source 优先, 然后按 created_at FIFO
        records = list(
            qs.order_by("source", "created_at")
        )

        ready = []
        generating = []
        for rec in records:
            ser = QuizGenerationRecordSerializer(rec).data
            payload = {
                "id": rec.id,
                "task_id": rec.task_id,
                "subject_id": rec.subject_id,
                "subject_display": rec.subject.get_display_name(),
                "subject_code": rec.subject.name,
                "requested_count": rec.requested_count,
                "state": rec.state,
                "questions": rec.questions if rec.state == QuizGenerationRecord.STATE_COMPLETE else [],
                "item_progress": rec.item_progress or {},
                "source": rec.source,
                "created_at": rec.created_at.isoformat(),
                "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
            }
            if rec.state == QuizGenerationRecord.STATE_COMPLETE and rec.questions:
                ready.append(payload)
            elif rec.state == QuizGenerationRecord.STATE_GENERATING:
                generating.append(payload)
            # error 状态不入列

        # 重新排序: ready 内的题重新按计划源优先
        ready.sort(key=lambda p: (0 if p["source"] == "plan" else 1, p["created_at"]))

        return Response(
            {
                "subject_code": subject_name,
                "plan_id": plan_id,
                "ready": ready,
                "generating": generating,
                "min_active": MIN_ACTIVE_QUIZZES,
                "max_inflight": MAX_INFLIGHT_QUIZZES,
            },
            status=status.HTTP_200_OK,
        )


class MarkAnsweredView(APIView):
    """POST /api/quiz/mark-answered/

    body: { quiz_id: int, question_index: int, correct: bool, analysis_task_id?: str }

    1) 写回 item_progress 到 QuizGenerationRecord
    2) 检查该 quiz 的未答数 = 0 时, 标记 is_active=False, _refill 自动补下一个 quiz
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        quiz_id = request.data.get("quiz_id")
        question_index = request.data.get("question_index")
        is_correct = bool(request.data.get("correct", False))

        if quiz_id is None or question_index is None:
            return Response(
                {"error": "quiz_id and question_index are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quiz_id = int(quiz_id)
            question_index = int(question_index)
        except (TypeError, ValueError):
            return Response(
                {"error": "quiz_id and question_index must be integers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            rec = (
                QuizGenerationRecord.objects.select_for_update()
                .filter(id=quiz_id, user=request.user)
                .first()
            )
            if rec is None:
                return Response({"error": "quiz not found"}, status=status.HTTP_404_NOT_FOUND)

            progress = dict(rec.item_progress or {})
            progress[str(question_index)] = {
                "answered": True,
                "correct": is_correct,
                "answered_at": json.dumps(None),  # placeholder for serialization
            }
            rec.item_progress = progress

            # 全部答完了? active=off
            if rec.questions and all(
                progress.get(str(i), {}).get("answered")
                for i in range(len(rec.questions))
            ):
                rec.is_active = False
            rec.save(update_fields=["item_progress", "is_active", "updated_at"])

        # 触发补队列
        _refill_active_quizzes(
            user=request.user,
            subject_name=rec.subject.name,
            plan_id=rec.plan_id,
            source=rec.source if rec.source == "plan" else "normal",
        )

        return Response(
            {
                "ok": True,
                "quiz_id": quiz_id,
                "question_index": question_index,
                "progress": progress,
            },
            status=status.HTTP_200_OK,
        )
