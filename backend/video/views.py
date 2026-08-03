"""Video 课程 REST API。"""

import json
import logging

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone as tz
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from llm.chains.video_chain import (
    VIDEO_TTL_SEC,
    video_meta_key,
    video_result_key,
    video_state_key,
)
from plan.models import LearningPlan
from users.models import Subject

from llm.agents.llm_factory import build_llm
from llm.prompts.video_prompts import VIDEO_INTRO_GENERATION_PROMPT

from .models import VideoCourseRecord
from .serializers import VideoCourseRecordSerializer

logger = logging.getLogger(__name__)


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


def _get_subject_for_user_or_404(*, user, subject_id):
    if not subject_id:
        return None
    return Subject.objects.filter(user=user, id=subject_id).first()


def _normalize_task_state(raw_state, fallback_error: str = ""):
    if not raw_state:
        return "", fallback_error
    if isinstance(raw_state, str) and raw_state.startswith("error:"):
        return "error", raw_state.split("error:", 1)[1]
    return str(raw_state), fallback_error


class VideoCourseRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """视频课程记录 CRUD（list / retrieve / delete）。"""

    serializer_class = VideoCourseRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["subject", "state", "completed"]

    def get_queryset(self):
        return VideoCourseRecord.objects.filter(user=self.request.user).select_related("subject")

    @action(detail=True, methods=["patch"], url_path="outlines")
    def patch_outlines(self, request, pk=None):
        """PATCH /api/video-courses/<id>/outlines/ — 前端回填 outlines 到后端。

        Body: { "outlines": [ { "id", "type", "title", "description", "key_points", "order" }, ... ] }
        后端仅接受有效数组，不做轮询，直接落库。
        不再自动触发简介/作业生成（交给 agent 侧处理）。
        """
        record = self.get_object()
        outlines = request.data.get("outlines")
        if not isinstance(outlines, list) or len(outlines) == 0:
            return Response(
                {"error": "outlines must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 规范化每条 outline
        normalized: list[dict] = []
        for idx, s in enumerate(outlines, start=1):
            if not isinstance(s, dict):
                continue
            try:
                order_val = int(s.get("order", idx))
            except (TypeError, ValueError):
                order_val = idx
            normalized.append({
                "id": str(s.get("id") or f"scene_{idx}"),
                "type": s.get("type", "slide"),
                "title": str(s.get("title", "")),
                "description": str(s.get("description", "")),
                "key_points": s.get("key_points") or s.get("keyPoints") or [],
                "order": order_val,
            })
        if not normalized:
            return Response(
                {"error": "outlines contained no valid entries"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        course = dict(record.course or {})
        course["outlines"] = normalized
        try:
            with transaction.atomic():
                VideoCourseRecord.objects.filter(id=record.id).update(course=course)
        except Exception:
            logger.exception("failed to save outlines from frontend PATCH")
            return Response(
                {"error": "failed to persist outlines"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        record.course = course
        logger.info("frontend patched %d outlines for record %s", len(normalized), record.id)

        serializer = self.get_serializer(record)
        return Response(serializer.data)

    def _do_generate_intro(self, record) -> dict:
        """AI 生成简介 + 课后作业并写入 record.course，返回 { intro, homework }。"""
        outlines = (record.course or {}).get("outlines") or []
        if not outlines:
            return {"intro": {}, "homework": []}

        lines = []
        for s in outlines[:20]:
            title = s.get("title", "未命名")
            desc = s.get("description", "")
            kps = s.get("key_points", [])
            lines.append(f"  场景「{title}」：{desc} 要点：{'；'.join(kps[:3])}")
        scenes_outline = "\n".join(lines)

        prompt = VIDEO_INTRO_GENERATION_PROMPT.format(
            topic=record.topic,
            scene_count=len(outlines),
            scenes_outline=scenes_outline,
        )

        llm = build_llm(streaming=False, temperature=0.7, enable_thinking=False)
        resp = llm.invoke(prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        intro_data = json.loads(raw)

        course = dict(record.course or {})
        course["intro_data"] = intro_data.get("intro", {})
        course["homework_data"] = intro_data.get("homework", [])
        record.course = course
        record.save(update_fields=["course", "updated_at"])

        return {"intro": course["intro_data"], "homework": course["homework_data"]}

    @action(detail=True, methods=["post"], url_path="intro")
    def generate_intro(self, request, pk=None):
        """POST /api/video-courses/:id/intro/ — AI 生成课程简介和课后作业。

        需要 course.outlines 已有数据（由前端通过 PATCH outlines 回填）。
        """
        record = self.get_object()

        outlines = (record.course or {}).get("outlines") or []
        if not outlines:
            return Response(
                {"error": "课程大纲为空，请先通过 PATCH outlines 回填"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self._do_generate_intro(record)
            return Response(result)
        except json.JSONDecodeError as e:
            raw_text = getattr(e, "raw", "")
            return Response(
                {"error": f"LLM 返回格式异常: {str(e)}", "raw": raw_text[:500]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="by-uuid/(?P<uuid>[^/.]+)")
    def by_uuid(self, request, uuid=None):
        """GET /api/video-courses/by-uuid/<uuid>/ — 通过 video_uuid 查找记录。"""
        record = VideoCourseRecord.objects.filter(
            user=request.user, video_uuid=uuid
        ).select_related("subject").first()
        if record is None:
            return Response(
                {"error": "Video course not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = VideoCourseRecordSerializer(record)
        return Response(serializer.data)


class VideoCourseGenerateView(APIView):
    """POST /api/video-course/generate/

    Body:
        {
          "subject_id": int,
          "topic": str,            # 必填
          "extra_prompt": str,     # 可选
          "knowledge_node_ids": [..]  # 可选，限定讲解范围
          "plan_id": int,          # 可选，绑定到 LearningPlan
          "plan_node_id": str,     # 可选，节点 id (plan.memory.items[].id)
        }

    如果传了 plan_id + plan_node_id, 创建记录时会立刻回填
    plan.memory.items[].video_record_id = record.id, 以便前端快速定位已生成的资源.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.db import close_old_connections

        from llm.tasks import run_video_course_generation_task

        # 防止 daphne idle 死连接
        close_old_connections()

        subject_id = request.data.get("subject_id")
        topic = (request.data.get("topic") or "").strip()
        extra_prompt = (request.data.get("extra_prompt") or "").strip()
        knowledge_node_ids = request.data.get("knowledge_node_ids") or []
        if not isinstance(knowledge_node_ids, list):
            return Response({"error": "knowledge_node_ids must be an array"}, status=status.HTTP_400_BAD_REQUEST)

        # 可选: 绑定到 plan memory (前端按 video_record_id 跳回视频)
        plan_id = request.data.get("plan_id")
        plan_node_id = request.data.get("plan_node_id")

        if not topic:
            return Response({"error": "topic is required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(topic) > 200:
            return Response({"error": "topic too long (max 200)"}, status=status.HTTP_400_BAD_REQUEST)

        subject = _get_subject_for_user_or_404(user=request.user, subject_id=subject_id)
        if subject is None:
            return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)

        task = run_video_course_generation_task.delay(
            subject_id=subject.id,
            topic=topic,
            extra_prompt=extra_prompt,
            knowledge_node_ids=knowledge_node_ids,
            user_id=request.user.id,
        )
        record = VideoCourseRecord.objects.create(
            user=request.user,
            subject=subject,
            task_id=task.id,
            topic=topic,
            extra_prompt=extra_prompt,
            knowledge_node_ids=knowledge_node_ids,
            state=VideoCourseRecord.STATE_GENERATING,
        )
        cache.set(
            video_meta_key(task.id),
            json.dumps({
                "user_id": request.user.id,
                "subject_id": subject.id,
                "subject_display": subject.get_display_name(),
                "subject_code": subject.name,
                "topic": topic,
            }, ensure_ascii=False),
            VIDEO_TTL_SEC,
        )

        # 立即回填 plan.memory.video_record_id (record 创建完就有 id)
        # 当前 plan 设计: 一条 LearningPlan = 一个 (节点 × 步骤) 的完整执行记录,
        # 视频类型的 step 自身就是一段视频, 直接把 video 字段挂到 plan.memory 上.
        # 这样前端在视频课列表页直接读 plan.memory.video_record_id 跳详情.
        if plan_id:
            try:
                plan = LearningPlan.objects.filter(id=plan_id, subject__user=request.user).first()
                if plan is not None:
                    memory = dict(plan.memory or {})
                    # 兼容老字段: 如果是 PlanItem.id 命中, 也回填到 plan.memory 上
                    items = list(memory.get("items") or [])
                    for it in items:
                        if isinstance(it, dict) and it.get("id") == plan_node_id:
                            # PlanItem 形态时: 改写在 item 上 (老逻辑)
                            it["video_record_id"] = record.id
                            it["video_uuid"] = ""
                            it["video_state"] = record.state
                            memory["items"] = items
                            break
                    else:
                        # 没有 items 命中: 直接挂在 plan.memory 上 (新逻辑)
                        memory["video_record_id"] = record.id
                        memory["video_uuid"] = ""
                        memory["video_state"] = record.state
                    plan.memory = memory
                    plan.save(update_fields=["memory", "updated_at"])
            except Exception:
                # 回填失败不阻塞视频生成主流程
                pass

        response = VideoCourseRecordSerializer(record).data
        response["ttl_sec"] = VIDEO_TTL_SEC
        return Response(response, status=status.HTTP_202_ACCEPTED)


class VideoCourseTaskStatusView(APIView):
    """GET /api/video-course/tasks/<task_id>/ — 轮询生成状态。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, task_id: str):
        record = VideoCourseRecord.objects.filter(
            user=request.user, task_id=task_id
        ).select_related("subject").first()
        if record is None:
            return Response({"error": "Video course task not found"}, status=status.HTTP_404_NOT_FOUND)

        raw_state = cache.get(video_state_key(task_id)) or record.state
        state, error_message = _normalize_task_state(raw_state, record.error_message)
        result = _read_cached_json(video_result_key(task_id))
        if result is None and state == VideoCourseRecord.STATE_COMPLETE:
            result = {
                "video_uuid": record.video_uuid,
                "iframe_url": record.iframe_url,
                "course": record.course,
            }

        response = VideoCourseRecordSerializer(record).data
        response["state"] = state
        response["error_message"] = error_message
        response["ttl_sec"] = VIDEO_TTL_SEC
        if state == VideoCourseRecord.STATE_COMPLETE and result is not None:
            response["video_uuid"] = result.get("video_uuid") or record.video_uuid
            response["iframe_url"] = result.get("iframe_url") or record.iframe_url
            response["course"] = result.get("course") or record.course
        return Response(response, status=status.HTTP_200_OK)


class VideoCourseProgressView(APIView):
    """POST /api/video-course/<int:record_id>/progress/

    Body:
        {
          "viewed_scene_ids": [..],
          "last_scene_id": "scene_3",
          "watched_seconds": 240,
          "completed": false
        }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, record_id: int):
        from llm.chains.video_chain import apply_video_progress

        record = VideoCourseRecord.objects.filter(
            user=request.user, id=record_id
        ).select_related("subject").first()
        if record is None:
            return Response({"error": "Video course record not found"}, status=status.HTTP_404_NOT_FOUND)

        viewed_scene_ids = request.data.get("viewed_scene_ids") or []
        last_scene_id = request.data.get("last_scene_id")
        watched_seconds = int(request.data.get("watched_seconds") or 0)
        completed = bool(request.data.get("completed") or False)

        if not isinstance(viewed_scene_ids, list):
            return Response({"error": "viewed_scene_ids must be an array"}, status=status.HTTP_400_BAD_REQUEST)

        # apply_video_progress 是 async; 同步 view 里用 asgiref.sync.async_to_sync 跑
        from asgiref.sync import async_to_sync
        result = async_to_sync(apply_video_progress)(
            video_course_record=record,
            viewed_scene_ids=viewed_scene_ids,
            last_scene_id=last_scene_id,
            watched_seconds=watched_seconds,
            completed=completed,
        )

        response = VideoCourseRecordSerializer(record).data
        response["progress_summary"] = result
        return Response(response, status=status.HTTP_200_OK)
