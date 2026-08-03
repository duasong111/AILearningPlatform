import json

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Subject

from .models import ExamSession, PracticeAnalysisRecord, PracticeSession, QuizGenerationRecord
from .serializers import ExamSessionSerializer, PracticeAnalysisRecordSerializer, PracticeSessionSerializer, QuizGenerationRecordSerializer


def _read_cached_json(key: str):
    raw = cache.get(key)
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _get_subject_for_user_or_404(*, user, subject_id: int | str | None):
    if not subject_id:
        return None
    return Subject.objects.filter(user=user, id=subject_id).first()


def _normalize_task_state(raw_state, fallback_error: str = "") -> tuple[str, str]:
    if not raw_state:
        return "", fallback_error
    if isinstance(raw_state, str) and raw_state.startswith("error:"):
        return "error", raw_state.split("error:", 1)[1]
    return str(raw_state), fallback_error


class QuizGenerationRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = QuizGenerationRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["subject", "state"]

    def get_queryset(self):
        return QuizGenerationRecord.objects.filter(user=self.request.user).select_related("subject")


class PracticeAnalysisRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PracticeAnalysisRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["subject", "state", "quiz_generation"]

    def get_queryset(self):
        return PracticeAnalysisRecord.objects.filter(user=self.request.user).select_related("subject", "quiz_generation")


class QuizGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import close_old_connections

        from llm.chains.quiz_chain import QUIZ_TTL_SEC, quiz_meta_key
        from llm.tasks import run_quiz_generation_task

        # 公网 Postgres 会把 daphne 持有的 idle connection kill 掉，
        # 下一个 ORM 调用拿了死连接会卡到 socket timeout（几分钟）→ daphne 30s 超时被强杀
        # → 前端 axios 报 "timeout of 30000ms exceeded"。
        # 在入口先 close 一次，下面的 ORM 调用拿不到现成连接会自动重建。
        close_old_connections()

        subject_id = request.data.get("subject_id")
        extra_prompt = (request.data.get("extra_prompt") or "").strip()
        count = request.data.get("count")

        subject = _get_subject_for_user_or_404(user=request.user, subject_id=subject_id)
        if subject is None:
            return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)

        if count in ("", None):
            count = None
        else:
            try:
                count = int(count)
            except (TypeError, ValueError):
                return Response({"error": "count must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            if not 1 <= count <= 20:
                return Response({"error": "count must be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)

        task = run_quiz_generation_task.delay(
            subject_id=subject.id,
            extra_prompt=extra_prompt,
            count=count,
        )
        record = QuizGenerationRecord.objects.create(
            user=request.user,
            subject=subject,
            task_id=task.id,
            extra_prompt=extra_prompt,
            requested_count=count,
            state=QuizGenerationRecord.STATE_GENERATING,
        )
        cache.set(
            quiz_meta_key(task.id),
            json.dumps(
                {
                    "user_id": request.user.id,
                    "subject_id": subject.id,
                    "subject_display": subject.get_display_name(),
                    "subject_code": subject.name,
                },
                ensure_ascii=False,
            ),
            QUIZ_TTL_SEC,
        )
        response = QuizGenerationRecordSerializer(record).data
        response["ttl_sec"] = QUIZ_TTL_SEC
        return Response(response, status=status.HTTP_201_CREATED)


class QuizAutoGenerateView(APIView):
    """POST /api/quiz/auto-generate/

    按知识点自动出题，读取用户薄弱点 + 知识点掌握度生成靶向题目。
    如果是计划触发的（plan_id），则 mark 该计划为 running 并记录关联。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import close_old_connections

        from llm.chains.quiz_chain import QUIZ_TTL_SEC, quiz_meta_key
        from llm.tasks import run_quiz_generation_task

        close_old_connections()  # 见 QuizGenerateView.post 注释

        subject_id = request.data.get("subject_id")
        plan_id = request.data.get("plan_id")
        node_id = (request.data.get("node_id") or "").strip()
        node_name = (request.data.get("node_name") or "").strip()
        count = request.data.get("count")
        extra_prompt = request.data.get("extra_prompt", "")

        subject = _get_subject_for_user_or_404(user=request.user, subject_id=subject_id)
        if subject is None:
            return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)

        if count in ("", None):
            count = None
        else:
            try:
                count = int(count)
            except (TypeError, ValueError):
                return Response({"error": "count must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
            if not 1 <= count <= 20:
                return Response({"error": "count must be between 1 and 20"}, status=status.HTTP_400_BAD_REQUEST)

        # 如果传了 plan_id，校验 plan 属于当前用户
        plan_obj = None
        if plan_id:
            from plan.models import LearningPlan
            plan_obj = LearningPlan.objects.filter(
                id=plan_id,
                subject__user=request.user,
            ).first()

        # 构造智能提示词：结合薄弱点 + 当前知识点
        prompt_parts = []
        if extra_prompt:
            prompt_parts.append(extra_prompt)

        # 添加知识点上下文
        if node_name:
            prompt_parts.append(f"当前知识点: {node_name}")
        if node_id:
            prompt_parts.append(f"知识点 ID: {node_id}")

        # 读取用户薄弱点
        weak_areas = []
        try:
            profile = request.user.subject_profiles.filter(subject=subject).first()
            if profile:
                weak_areas = list(profile.common_mistakes or [])
        except Exception:
            pass

        # 读取用户知识点掌握程度
        weak_nodes = []
        try:
            from users.models import KnowledgeNode
            weak_nodes = list(
                KnowledgeNode.objects
                .filter(subject=subject, mastery__lt=50)
                .values_list("name", flat=True)
            )
        except Exception:
            pass

        combined_weak = list(set(weak_areas + weak_nodes))
        if combined_weak:
            if node_name:
                prompt_parts.append(
                    f"【智能出题】用户在学习「{node_name}」，"
                    f"请重点考察以下薄弱知识点: {', '.join(combined_weak[:10])}"
                )
            else:
                prompt_parts.append(
                    f"【智能出题】请重点考察以下薄弱知识点: {', '.join(combined_weak[:10])}"
                )

        final_prompt = "\n".join(prompt_parts) if prompt_parts else ""

        # 标记 plan 为 running（如果有）
        if plan_obj and plan_obj.state != "success":
            plan_obj.state = "running"
            plan_obj.save(update_fields=["state", "updated_at"])

        task = run_quiz_generation_task.delay(
            subject_id=subject.id,
            extra_prompt=final_prompt,
            count=count,
        )

        record = QuizGenerationRecord.objects.create(
            user=request.user,
            subject=subject,
            task_id=task.id,
            extra_prompt=final_prompt,
            requested_count=count,
            node_id=node_id,
            node_name=node_name,
            plan=plan_obj,
            state=QuizGenerationRecord.STATE_GENERATING,
        )

        cache.set(
            quiz_meta_key(task.id),
            json.dumps(
                {
                    "user_id": request.user.id,
                    "subject_id": subject.id,
                    "subject_display": subject.get_display_name(),
                    "subject_code": subject.name,
                    "node_id": node_id,
                    "node_name": node_name,
                    "plan_id": plan_id,
                },
                ensure_ascii=False,
            ),
            QUIZ_TTL_SEC,
        )

        response = QuizGenerationRecordSerializer(record).data
        response["ttl_sec"] = QUIZ_TTL_SEC
        return Response(response, status=status.HTTP_201_CREATED)

    def get(self, request):
        """GET /api/quiz/auto-generate/?subject_id=X

        返回待生成的计划触发的 quiz（由 plan 触发且 plan 尚未完成的 quiz）。
        用于前端在计划页点击 quiz 时检查是否已有进行中的 quiz。
        """
        subject_id = request.query_params.get("subject_id")
        if not subject_id:
            return Response({"error": "subject_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        records = (
            QuizGenerationRecord.objects
            .filter(
                user=request.user,
                subject_id=subject_id,
                state=QuizGenerationRecord.STATE_GENERATING,
            )
            .exclude(plan=None)
            .select_related("plan", "subject")
            .order_by("-created_at")
        )
        return Response(QuizGenerationRecordSerializer(records, many=True).data)


class QuizTaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        from llm.chains.quiz_chain import QUIZ_TTL_SEC, quiz_result_key, quiz_state_key

        record = QuizGenerationRecord.objects.filter(user=request.user, task_id=task_id).select_related("subject").first()
        if record is None:
            return Response({"error": "Quiz task not found"}, status=status.HTTP_404_NOT_FOUND)

        raw_state = cache.get(quiz_state_key(task_id)) or record.state
        state, error_message = _normalize_task_state(raw_state, record.error_message)
        result = _read_cached_json(quiz_result_key(task_id))
        if result is None and state == QuizGenerationRecord.STATE_COMPLETE:
            result = record.questions or []
        response = QuizGenerationRecordSerializer(record).data
        response["state"] = state
        response["error_message"] = error_message
        response["ttl_sec"] = QUIZ_TTL_SEC
        if state == QuizGenerationRecord.STATE_COMPLETE and result is not None:
            response["questions"] = result
            response["actual_count"] = len(result)
        return Response(response, status=status.HTTP_200_OK)


class PracticeAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import close_old_connections

        from llm.tasks import PRACTICE_TTL_SEC, practice_meta_key, run_practice_analysis_task

        close_old_connections()  # daphne idle 连接保险，见 QuizGenerateView.post 注释

        quiz_task_id = (request.data.get("quiz_task_id") or "").strip()
        if not quiz_task_id:
            return Response({"error": "quiz_task_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        mode = request.data.get("mode", "with_answer")
        if mode not in {"with_answer", "without_answer"}:
            return Response({"error": "mode must be with_answer or without_answer"}, status=status.HTTP_400_BAD_REQUEST)

        question_index = request.data.get("question_index", 0)
        try:
            question_index = int(question_index)
        except (TypeError, ValueError):
            return Response({"error": "question_index must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        user_answer = request.data.get("user_answer")
        if user_answer is not None:
            user_answer = str(user_answer)

        quiz_record = QuizGenerationRecord.objects.filter(user=request.user, task_id=quiz_task_id).select_related("subject").first()
        if quiz_record is None:
            return Response({"error": "Quiz task not found"}, status=status.HTTP_404_NOT_FOUND)

        task = run_practice_analysis_task.delay(
            quiz_task_id=quiz_task_id,
            question_index=question_index,
            mode=mode,
            user_answer=user_answer,
            subject_display=quiz_record.subject.get_display_name(),
            subject_code=quiz_record.subject.name,
        )
        cache.set(
            practice_meta_key(task.id),
            json.dumps(
                {
                    "user_id": request.user.id,
                    "quiz_task_id": quiz_task_id,
                    "mode": mode,
                },
                ensure_ascii=False,
            ),
            PRACTICE_TTL_SEC,
        )
        record = None
        if mode == PracticeAnalysisRecord.MODE_WITH_ANSWER:
            record = PracticeAnalysisRecord.objects.create(
                user=request.user,
                subject=quiz_record.subject,
                quiz_generation=quiz_record,
                task_id=task.id,
                quiz_task_id=quiz_task_id,
                question_index=question_index,
                mode=mode,
                user_answer=user_answer,
                state=PracticeAnalysisRecord.STATE_GENERATING,
            )

        response = {
            "task_id": task.id,
            "quiz_task_id": quiz_task_id,
            "question_index": question_index,
            "mode": mode,
            "state": PracticeAnalysisRecord.STATE_GENERATING,
            "persisted": bool(record),
            "ttl_sec": PRACTICE_TTL_SEC,
        }
        if record is not None:
            response["record"] = PracticeAnalysisRecordSerializer(record).data
        return Response(response, status=status.HTTP_202_ACCEPTED)


class PracticeTaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        from llm.tasks import PRACTICE_TTL_SEC, practice_meta_key, practice_result_key, practice_state_key

        record = PracticeAnalysisRecord.objects.filter(user=request.user, task_id=task_id).select_related("subject", "quiz_generation").first()
        if record is not None:
            raw_state = cache.get(practice_state_key(task_id)) or record.state
            state, error_message = _normalize_task_state(raw_state, record.error_message)
            result = _read_cached_json(practice_result_key(task_id))
            if result is None and state == PracticeAnalysisRecord.STATE_COMPLETE:
                result = record.analysis or {}
            response = PracticeAnalysisRecordSerializer(record).data
            response["state"] = state
            response["error_message"] = error_message
            response["ttl_sec"] = PRACTICE_TTL_SEC
            if state == PracticeAnalysisRecord.STATE_COMPLETE and result is not None:
                response["analysis"] = result
            return Response(response, status=status.HTTP_200_OK)

        meta = _read_cached_json(practice_meta_key(task_id)) or {}
        if meta.get("user_id") != request.user.id:
            return Response({"error": "Practice task not found"}, status=status.HTTP_404_NOT_FOUND)

        raw_state = cache.get(practice_state_key(task_id))
        if raw_state is None:
            return Response({"error": "Practice task not found or expired"}, status=status.HTTP_404_NOT_FOUND)
        state, error_message = _normalize_task_state(raw_state)

        response = {
            "task_id": task_id,
            "quiz_task_id": meta.get("quiz_task_id"),
            "mode": meta.get("mode"),
            "persisted": False,
            "state": state,
            "error_message": error_message,
            "ttl_sec": PRACTICE_TTL_SEC,
        }
        if state == "complete":
            response["analysis"] = _read_cached_json(practice_result_key(task_id)) or {}
        return Response(response, status=status.HTTP_200_OK)


class ExamSessionCreateView(APIView):
    """POST /api/exam/sessions/ — 调用 Dify 生成题库，创建测评会话。"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from dify_workflow.quiz_generator import call_dify_workflow_quiz_generator

        search_query = (request.data.get("search_query") or "").strip()
        if not search_query:
            return Response({"error": "search_query 不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mcq_count = int(request.data.get("mcq_count", 5))
            qa_count = int(request.data.get("qa_count", 2))
        except (TypeError, ValueError):
            return Response({"error": "mcq_count 和 qa_count 必须为整数"}, status=status.HTTP_400_BAD_REQUEST)

        if mcq_count < 0 or qa_count < 0 or mcq_count + qa_count == 0:
            return Response({"error": "题目数量不合法"}, status=status.HTTP_400_BAD_REQUEST)

        result = call_dify_workflow_quiz_generator(
            mcq_count=mcq_count,
            qa_count=qa_count,
            search_query=search_query,
            user_id=str(request.user.id),
        )
        if result is None:
            return Response({"error": "题库生成失败，请稍后重试"}, status=status.HTTP_502_BAD_GATEWAY)

        outputs = result.get("data", {}).get("outputs", {})
        multiple_choice = outputs.get("multiple_choice", [])
        essay = outputs.get("essay", [])

        session = ExamSession.objects.create(
            user=request.user,
            search_query=search_query,
            mcq_count=len(multiple_choice),
            qa_count=len(essay),
            multiple_choice=multiple_choice,
            essay=essay,
        )
        return Response(ExamSessionSerializer(session).data, status=status.HTTP_201_CREATED)


def _run_exam_analysis(session: ExamSession):
    """调用大模型分析测评结果，返回 analysis dict；失败则返回 None。"""
    import json as _json
    import logging

    from langchain_core.messages import HumanMessage, SystemMessage

    from llm.agents.llm_factory import build_llm
    from llm.config import LLMProvider
    from llm.prompts.exam_prompts import EXAM_ANALYSIS_SYSTEM

    logger = logging.getLogger(__name__)

    mcq_answers = session.mcq_answers or {}
    essay_answers = session.essay_answers or {}
    multiple_choice = session.multiple_choice or []
    essay = session.essay or []

    # 构建选择题诊断数据
    mcq_details = []
    for q in multiple_choice:
        qid = str(q["id"])
        user_pick = mcq_answers.get(qid, "")
        correct = q.get("answer", "")
        mcq_details.append({
            "id": q["id"],
            "question": q.get("question", ""),
            "options": q.get("options", {}),
            "correct": correct,
            "user_pick": user_pick or "(未作答)",
            "is_correct": user_pick.upper() == correct.upper(),
            "explanation": q.get("explanation", ""),
        })

    # 构建问答题数据
    essay_details = []
    for q in essay:
        qid = str(q["id"])
        essay_details.append({
            "id": q["id"],
            "question": q.get("question", ""),
            "reference": q.get("answer", ""),
            "scoring_points": q.get("scoring_points", []),
            "user_answer": essay_answers.get(qid, "(未作答)"),
        })

    user_prompt = f"""请分析以下测评结果并严格按 JSON 格式输出分析报告。

## 选择题结果
{_json.dumps(mcq_details, ensure_ascii=False, indent=2)}

## 问答题结果
{_json.dumps(essay_details, ensure_ascii=False, indent=2)}

请输出 JSON 分析报告："""

    try:
        llm = build_llm(streaming=False, temperature=0.3, provider=LLMProvider.MINIMAX)
        response = llm.invoke([
            SystemMessage(content=EXAM_ANALYSIS_SYSTEM),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content if hasattr(response, "content") else str(response)
        # 提取 JSON
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
        return _json.loads(raw)
    except Exception:
        logger.exception("测评分析失败")
        return None


class ExamSessionSubmitView(APIView):
    """POST /api/exam/sessions/<id>/submit/ — 提交答案，自动批改并 AI 分析。"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        session = get_object_or_404(ExamSession, pk=pk, user=request.user)
        if session.status == ExamSession.STATUS_COMPLETED:
            return Response(ExamSessionSerializer(session).data, status=status.HTTP_200_OK)

        mcq_answers = request.data.get("mcq_answers", {})
        essay_answers = request.data.get("essay_answers", {})

        # 确保 key 是字符串（JSON 兼容）
        mcq_answers = {str(k): str(v).upper() for k, v in mcq_answers.items()}
        essay_answers = {str(k): str(v) for k, v in essay_answers.items()}

        session.mcq_answers = mcq_answers
        session.essay_answers = essay_answers
        session.status = ExamSession.STATUS_COMPLETED
        session.completed_at = timezone.now()

        # 自动计算选择题得分率
        total = len(session.multiple_choice)
        if total > 0:
            correct = sum(
                1 for q in session.multiple_choice
                if mcq_answers.get(str(q["id"]), "").upper() == q.get("answer", "").upper()
            )
            session.mcq_score = round(correct / total, 4)

        # AI 分析（问答题评分 + 错题诊断 + 整体评估）
        analysis = _run_exam_analysis(session)
        if analysis is not None:
            session.analysis = analysis

        session.save()
        return Response(ExamSessionSerializer(session).data, status=status.HTTP_200_OK)


class ExamSessionListView(generics.ListAPIView):
    """GET /api/exam/history/ — 当前用户的测评历史。"""

    serializer_class = ExamSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user)


class ExamSessionDetailView(generics.RetrieveAPIView):
    """GET /api/exam/sessions/<id>/ — 获取单个测评会话详情。"""

    serializer_class = ExamSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamSession.objects.filter(user=self.request.user)


class PracticeSessionDetailView(generics.RetrieveAPIView):
    """GET /api/practice/sessions/<id>/ — 获取单个实践会话详情。"""

    serializer_class = PracticeSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PracticeSession.objects.filter(user=self.request.user)
