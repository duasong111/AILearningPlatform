"""Quiz / Practice HTTP 端点 —— 给前端用的 task 派发 + 状态查询。

后端业务逻辑都在 `llm/chains/quiz_chain.py` + `llm/chains/practice_chain.py`,
通过 Celery 任务 `run_quiz_generation_task` / `run_practice_analysis_task` 跑,
结果存到 Redis (quiz:<task_id>:state/result, practice:<task_id>:state/result)。

HTTP 协议:
  POST /api/quiz/generate/         body: {subject_id, count?, extra_prompt?}
                                  → 201 {task_id}
  GET  /api/quiz/<task_id>/state/ → 200 {state, message?}
  GET  /api/quiz/<task_id>/result/ → 200 {questions: [...]}
  POST /api/practice/analyze/     body: {quiz_task_id, question_index, user_answer, mode?, subject_display?, subject_code?}
                                  → 201 {task_id}
  GET  /api/practice/<task_id>/state/
  GET  /api/practice/<task_id>/result/
"""
import json
import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Quiz
# ──────────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quiz_generate(request):
    """POST /api/quiz/generate/  body: {subject_id, count?, extra_prompt?}
    → 启 run_quiz_generation_task Celery 任务
    → 返 201 {task_id}
    """
    from .tasks import run_quiz_generation_task

    subject_id = request.data.get("subject_id")
    if not subject_id:
        return Response(
            {"error": "subject_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    count = request.data.get("count")  # None 让后端自己决定
    if count is not None:
        try:
            count = int(count)
        except (TypeError, ValueError):
            return Response(
                {"error": "count must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    extra_prompt = str(request.data.get("extra_prompt") or "")

    async_result = run_quiz_generation_task.delay(
        subject_id=int(subject_id), count=count, extra_prompt=extra_prompt
    )
    return Response({"task_id": async_result.id}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_state(request, task_id):
    """GET /api/quiz/<task_id>/state/ → 读 redis quiz:<task_id>:state
    → 返 200 {state: 'generating'|'complete'|'error:<msg>', message?: str}
    """
    from .chains.quiz_chain import quiz_state_key

    state = cache.get(quiz_state_key(task_id)) or "unknown"
    payload: dict = {"state": state}
    if isinstance(state, str) and state.startswith("error:"):
        payload["message"] = state[len("error:") :] or state
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_result(request, task_id):
    """GET /api/quiz/<task_id>/result/ → state=complete 时才返 questions 数组。
    state=generating 时 409, state=error:... 时 410, 结果过期时 410。
    """
    from .chains.quiz_chain import quiz_result_key, quiz_state_key

    state = cache.get(quiz_state_key(task_id)) or "unknown"
    if state == "generating":
        return Response(
            {"error": "quiz still generating", "state": state},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(state, str) and state.startswith("error"):
        return Response(
            {"error": state, "state": state}, status=status.HTTP_410_GONE
        )
    raw = cache.get(quiz_result_key(task_id))
    if raw is None:
        return Response(
            {"error": "result expired or missing", "state": state},
            status=status.HTTP_410_GONE,
        )
    try:
        questions = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return Response(
            {"error": "result corrupted"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return Response({"questions": questions})


# ──────────────────────────────────────────────────────────────────
# Practice analyze
# ──────────────────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def practice_analyze(request):
    """POST /api/practice/analyze/
    body: {quiz_task_id, question_index, user_answer, mode?, subject_display?, subject_code?}
    → 启 run_practice_analysis_task
    → 返 201 {task_id}
    """
    from .tasks import run_practice_analysis_task

    required = ("quiz_task_id", "question_index", "user_answer")
    for f in required:
        if f not in request.data:
            return Response(
                {"error": f"{f} is required"}, status=status.HTTP_400_BAD_REQUEST
            )

    try:
        question_index = int(request.data["question_index"])
    except (TypeError, ValueError):
        return Response(
            {"error": "question_index must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    async_result = run_practice_analysis_task.delay(
        quiz_task_id=str(request.data["quiz_task_id"]),
        question_index=question_index,
        user_answer=str(request.data["user_answer"]),
        mode=str(request.data.get("mode", "with_answer")),
        subject_display=str(request.data.get("subject_display", "未知学科")),
        subject_code=str(request.data.get("subject_code", "unknown")),
    )
    return Response({"task_id": async_result.id}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def practice_state(request, task_id):
    """GET /api/practice/<task_id>/state/ → 读 redis practice:<task_id>:state."""
    from .tasks import practice_state_key

    state = cache.get(practice_state_key(task_id)) or "unknown"
    payload: dict = {"state": state}
    if isinstance(state, str) and state.startswith("error:"):
        payload["message"] = state[len("error:") :] or state
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def practice_result(request, task_id):
    """GET /api/practice/<task_id>/result/ → state=complete 时才返 analysis。
    状态机跟 quiz_result 一样.
    """
    from .tasks import practice_result_key, practice_state_key

    state = cache.get(practice_state_key(task_id)) or "unknown"
    if state == "generating":
        return Response(
            {"error": "practice still analyzing", "state": state},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(state, str) and state.startswith("error"):
        return Response(
            {"error": state, "state": state}, status=status.HTTP_410_GONE
        )
    raw = cache.get(practice_result_key(task_id))
    if raw is None:
        return Response(
            {"error": "result expired or missing", "state": state},
            status=status.HTTP_410_GONE,
        )
    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return Response(
            {"error": "result corrupted"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return Response(result)
