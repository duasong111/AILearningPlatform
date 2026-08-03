"""Video Chain: 生成视频课程，使用 OpenMAIC Mode A（视频服务自行生成全部内容）。

设计目标:
- 由 OpenMAIC 自行完成 outline/content/actions/TTS 全流程
- 我们的职责：生成一个唯一 uuid + 构建 iframe URL
- 当前部署的 OpenMAIC 不支持 Mode B（POST /api/video/{uuid}/init），走纯 Mode A
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid as uuidlib

from langchain_core.messages import HumanMessage, SystemMessage

from ..agents.llm_factory import build_llm
from ..prompts.video_prompts import (
    VIDEO_COURSE_GENERATION_SYSTEM_PROMPT,
    VIDEO_PROGRESS_EVIDENCE_TEMPLATE,
)
from ..schemas.video_schema import VideoCourse, VideoScene


VIDEO_TTL_SEC = 3600
VIDEO_GEN_HOST = os.environ.get("VIDEO_GEN_HOST", "<YOUR_OPENMAIC_HOST:PORT>")


# Redis 状态 / 结果 key（对齐 quiz/practice 的命名）
def video_state_key(task_id: str) -> str:
    return f"video_course:{task_id}:state"


def video_result_key(task_id: str) -> str:
    return f"video_course:{task_id}:result"


def video_meta_key(task_id: str) -> str:
    return f"video_course:{task_id}:meta"


# ---------------------------------------------------------------------------
# 外部 OpenMAIC 视频服务调用
# ---------------------------------------------------------------------------


def _build_iframe_url(*, desc: str, video_uuid: str) -> str:
    return f"http://{VIDEO_GEN_HOST}/video?{urllib.parse.urlencode({'desc': desc, 'uuid': video_uuid})}"


class VideoServiceError(Exception):
    """外部 OpenMAIC 视频服务调用失败。"""


# ---------------------------------------------------------------------------
# Chain 主入口
# ---------------------------------------------------------------------------


async def generate_video_course(
    *,
    subject_id: int,
    topic: str,
    extra_prompt: str = "",
    knowledge_node_ids: list[str] | None = None,
) -> dict:
    """主入口: 生成唯一 uuid → 返回 iframe URL（纯 Mode A，OpenMAIC 自行生成全部内容）。

    Mode A 下 OpenMAIC 页面加载后会自己完成 outline/content/actions/TTS 全流程。

    Args:
        subject_id: 学科 PK（仅用于日志，不走 LLM）
        topic: 课程主题（传给 iframe 的 desc 参数）
        extra_prompt: 用户的额外要求（Mode A 下未使用）
        knowledge_node_ids: 限定讲解的知识点（Mode A 下未使用）

    Returns:
        {
          "video_uuid": "...",
          "iframe_url": "http://.../video?desc=...&uuid=...",
          "course": None,  # Mode A 下不生成结构化大纲
        }
    """
    video_uuid = uuidlib.uuid4().hex[:32]
    iframe_url = _build_iframe_url(desc=topic, video_uuid=video_uuid)

    return {
        "video_uuid": video_uuid,
        "iframe_url": iframe_url,
        "course": {},
    }


def _normalize_course(course: VideoCourse) -> VideoCourse:
    """兜底: 若 LLM 给的 scene id 缺失/重复，重新编号；type 强制为 slide。"""
    outlines: list[VideoScene] = []
    for idx, scene in enumerate(course.outlines, start=1):
        scene_id = (scene.id or "").strip() or f"scene_{idx}"
        outlines.append(
            VideoScene(
                id=scene_id,
                type="slide",
                title=scene.title,
                description=scene.description,
                key_points=list(scene.key_points or []),
                order=idx,
                knowledge_node_id=(scene.knowledge_node_id or None),
            )
        )
    return VideoCourse(
        desc=course.desc,
        language_directive=course.language_directive,
        target_audience=course.target_audience,
        difficulty=course.difficulty,
        estimated_minutes=course.estimated_minutes,
        course_intro=course.course_intro,
        course_summary=course.course_summary,
        learning_objectives=list(course.learning_objectives or []),
        prerequisites=list(course.prerequisites or []),
        outlines=outlines,
    )


# ---------------------------------------------------------------------------
# 进度上报 → 知识图谱更新
# ---------------------------------------------------------------------------


def _scene_lookup(course: dict) -> dict[str, dict]:
    return {s["id"]: s for s in (course.get("outlines") or [])}


def _compute_completion(course: dict, viewed_scene_ids: list[str]) -> tuple[int, int, float]:
    """计算 (viewed_count, total_count, ratio)。"""
    total = len(course.get("outlines") or [])
    if total == 0:
        return 0, 0, 0.0
    scene_lookup = _scene_lookup(course)
    viewed = sum(1 for sid in viewed_scene_ids if sid in scene_lookup)
    return viewed, total, round(viewed / total, 4)


def _scene_knowledge_node_id(course: dict, scene_id: str) -> str | None:
    scene = _scene_lookup(course).get(scene_id)
    if not scene:
        return None
    return scene.get("knowledge_node_id") or None


def _scene_node_name(course: dict, scene_id: str, knowledge_nodes_index: dict[str, str]) -> str:
    node_id = _scene_knowledge_node_id(course, scene_id)
    if node_id and node_id in knowledge_nodes_index:
        return knowledge_nodes_index[node_id]
    scene = _scene_lookup(course).get(scene_id) or {}
    return scene.get("title") or scene_id


def build_progress_evidence(
    *,
    course: dict,
    scene_id: str,
    watched_seconds: int,
    completion_status: str,
    knowledge_nodes_index: dict[str, str],
) -> tuple[str, str] | None:
    """把"看完了 scene X"翻译成 (node_id, evidence) 文本。

    Returns:
        (knowledge_node_id, evidence_text) 或 None（场景不关联任何知识点 / 找不到场景）
    """
    scene = _scene_lookup(course).get(scene_id)
    if not scene:
        return None
    node_id = scene.get("knowledge_node_id") or None
    if not node_id:
        return None
    node_name = knowledge_nodes_index.get(node_id, scene.get("title") or scene_id)
    evidence = VIDEO_PROGRESS_EVIDENCE_TEMPLATE.format(
        course_title=course.get("desc", ""),
        scene_order=scene.get("order", 0),
        scene_title=scene.get("title", ""),
        key_points="、".join(scene.get("key_points") or []),
        watched_seconds=watched_seconds,
        completion_status=completion_status,
        node_name=node_name,
    )
    return node_id, evidence


async def apply_video_progress(
    *,
    video_course_record,
    viewed_scene_ids: list[str],
    last_scene_id: str | None,
    watched_seconds: int,
    completed: bool,
) -> dict:
    """把前端上报的 progress 应用到:
    1. 更新 VideoCourseRecord 字段 (viewed_scene_ids, completion_ratio, ...)
    2. 对每个"新看完"的 scene 调 update_knowledge_score_from_evidence 影响知识图谱
    """
    from asgiref.sync import sync_to_async
    from llm.tools.knowledge_tools import update_knowledge_score_from_evidence
    from users.models import KnowledgeNode

    subject = video_course_record.subject
    course = video_course_record.course or {}
    if not isinstance(course, dict) or not course.get("outlines"):
        return {
            "viewed_count": 0,
            "total_count": 0,
            "completion_ratio": 0.0,
            "knowledge_updates": [],
        }

    # 1. 计算当前进度
    viewed_count, total_count, ratio = _compute_completion(course, viewed_scene_ids)
    completion_status = "已完整看完所有场景" if completed else f"已完成 {viewed_count}/{total_count} 场景"

    # 2. 找出"本次新增"的 scene id（对比 DB 里的历史 viewed_scene_ids）
    previous_viewed = set(video_course_record.viewed_scene_ids or [])
    new_viewed = [sid for sid in viewed_scene_ids if sid not in previous_viewed]

    # 3. 写回 record 字段
    def _save_record():
        video_course_record.viewed_scene_ids = list(dict.fromkeys(viewed_scene_ids))
        video_course_record.last_scene_id = last_scene_id
        video_course_record.watched_seconds = max(
            int(video_course_record.watched_seconds or 0), int(watched_seconds or 0)
        )
        video_course_record.completion_ratio = ratio
        if completed:
            video_course_record.completed = True
        video_course_record.save(update_fields=[
            "viewed_scene_ids", "last_scene_id",
            "watched_seconds", "completion_ratio", "completed", "updated_at",
        ])

    await sync_to_async(_save_record, thread_sensitive=True)()

    # 4. 对新看完的 scene 触发知识图谱更新
    nodes = await sync_to_async(list)(
        KnowledgeNode.objects.filter(subject=subject).only("node_id", "name")
    )
    knowledge_nodes_index = {n.node_id: n.name for n in nodes}

    knowledge_updates: list[dict] = []
    for scene_id in new_viewed:
        evidence_pair = build_progress_evidence(
            course=course,
            scene_id=scene_id,
            watched_seconds=watched_seconds,
            completion_status=completion_status,
            knowledge_nodes_index=knowledge_nodes_index,
        )
        if not evidence_pair:
            continue
        node_id, evidence = evidence_pair
        if node_id not in knowledge_nodes_index:
            continue
        try:
            result = await sync_to_async(update_knowledge_score_from_evidence, thread_sensitive=True)(
                user_id=subject.user_id,
                subject_code=subject.name,
                node_id=node_id,
                evidence=evidence,
                round_num=0,
                metadata={
                    "source": "video_progress",
                    "video_course_id": video_course_record.id,
                    "video_uuid": video_course_record.video_uuid,
                    "scene_id": scene_id,
                },
            )
            knowledge_updates.append({
                "scene_id": scene_id,
                "node_id": node_id,
                "result": result,
            })
        except Exception as exc:  # noqa: BLE001
            knowledge_updates.append({
                "scene_id": scene_id,
                "node_id": node_id,
                "error": str(exc),
            })

    return {
        "viewed_count": viewed_count,
        "total_count": total_count,
        "completion_ratio": ratio,
        "new_viewed_scene_ids": new_viewed,
        "knowledge_updates": knowledge_updates,
    }
