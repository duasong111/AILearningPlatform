import json
import logging
import time

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from .state_keys import (
    TTL_SEC,
    conv_ai_state,
    conv_channel_group,
    conv_current_ai_msg,
    msg_channel_group,
    msg_content,
    msg_meta,
    msg_started_at,
    msg_state,
)

logger = logging.getLogger(__name__)


def _publish_group(group_name: str, data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group_name, {"type": "event.relay", "data": data})
    except Exception as exc:
        logger.warning("channel layer group_send failed: %s", exc)


async def _apublish_group(group_name: str, data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        await layer.group_send(group_name, {"type": "event.relay", "data": data})
    except Exception as exc:
        logger.warning("channel layer async group_send failed: %s", exc)


def publish_event(message_id: int, conversation_id: int, data: dict) -> None:
    """同时广播到 message 和 conversation 两级 group。"""
    _publish_group(msg_channel_group(message_id), data)
    _publish_group(conv_channel_group(conversation_id), data)


async def apublish_event(message_id: int, conversation_id: int, data: dict) -> None:
    """异步广播到 message 和 conversation 两级 group。"""
    await _apublish_group(msg_channel_group(message_id), data)
    await _apublish_group(conv_channel_group(conversation_id), data)


def write_runtime_state(
    *,
    message_id: int,
    conversation_id: int,
    state: str | None = None,
    content: str | None = None,
    meta: dict | None = None,
    started_at: float | None = None,
    ai_state: str | None = None,
    current_ai_msg: int | None = None,
) -> None:
    """批量写 Redis 瞬时状态。"""
    mapping = {}
    if state is not None:
        mapping[msg_state(message_id)] = state
    if content is not None:
        mapping[msg_content(message_id)] = content
    if meta is not None:
        mapping[msg_meta(message_id)] = json.dumps(meta, ensure_ascii=False)
    if started_at is not None:
        mapping[msg_started_at(message_id)] = started_at
    if ai_state is not None:
        mapping[conv_ai_state(conversation_id)] = ai_state
    if current_ai_msg is not None:
        mapping[conv_current_ai_msg(conversation_id)] = current_ai_msg
    if not mapping:
        return
    try:
        cache.set_many(mapping, TTL_SEC)
    except Exception as exc:
        logger.warning("cache.set_many failed: %s", exc)


def read_runtime_meta(message_id: int) -> dict:
    raw = cache.get(msg_meta(message_id))
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def mark_generating(message_id: int, conversation_id: int) -> None:
    write_runtime_state(
        message_id=message_id,
        conversation_id=conversation_id,
        state="generating",
        content="",
        meta={},
        started_at=time.time(),
        ai_state="generating",
        current_ai_msg=message_id,
    )


def mark_complete(message_id: int, conversation_id: int, content: str, meta: dict | None = None) -> None:
    write_runtime_state(
        message_id=message_id,
        conversation_id=conversation_id,
        state="complete",
        content=content,
        meta=meta or {},
        ai_state="idle",
        current_ai_msg=message_id,
    )
    publish_event(
        message_id,
        conversation_id,
        {"type": "complete", "ai_message_id": message_id, "content": content, "meta": meta or {}},
    )


async def amark_complete(message_id: int, conversation_id: int, content: str, meta: dict | None = None) -> None:
    write_runtime_state(
        message_id=message_id,
        conversation_id=conversation_id,
        state="complete",
        content=content,
        meta=meta or {},
        ai_state="idle",
        current_ai_msg=message_id,
    )
    await apublish_event(
        message_id,
        conversation_id,
        {"type": "complete", "ai_message_id": message_id, "content": content, "meta": meta or {}},
    )


def mark_error(message_id: int, conversation_id: int, error_message: str) -> None:
    write_runtime_state(
        message_id=message_id,
        conversation_id=conversation_id,
        state=f"error:{error_message}",
        ai_state="idle",
        current_ai_msg=message_id,
    )
    publish_event(
        message_id,
        conversation_id,
        {"type": "error", "ai_message_id": message_id, "message": error_message},
    )
