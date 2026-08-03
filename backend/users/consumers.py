"""WebSocket consumers。

- ConversationStreamConsumer: 基于 conversation_id 的统一对话 WS，负责发消息和接收流
"""
import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.db.models import Q

from llm.runtime import read_runtime_meta
from llm.state_keys import conv_ai_state, conv_channel_group, conv_current_ai_msg, msg_content, msg_state

from .models import Conversation
from .serializers import MessageSerializer


class ConversationStreamConsumer(AsyncJsonWebsocketConsumer):
    """WS /ws/conversations/<conversation_id>/

    前端连上某个会话后：
    - C->S: {"type":"message","content":"...","role":"user","meta":{...}}
    - S->C: {"type":"accepted", ...}
    - S->C: {"type":"resume"|"chunk"|"complete"|"error", ...}
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close(code=4401)
            return
        self.user = user
        self.conversation_id = int(self.scope["url_route"]["kwargs"]["conversation_id"])
        self.conversation = await self._get_conversation_owned()
        if not self.conversation:
            await self.close(code=4403)
            return

        self._polling = True
        self._tracked_ai_message_id = None
        self._sent_content_len = 0
        self._terminal_sent = False
        self.group_name = conv_channel_group(self.conversation_id)
        await self.accept()
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        try:
            await self._send_recent_history()
            await self._send_conversation_state()
        except Exception as exc:
            # 发送历史消息失败时记录日志，但不断开连接
            import logging
            logging.getLogger(__name__).warning("Error sending initial state: %s", exc)

        self._poll_task = asyncio.create_task(self._poll_conversation_state())

    async def disconnect(self, code):
        self._polling = False
        if hasattr(self, "_poll_task"):
            self._poll_task.cancel()
        if hasattr(self, "group_name"):
            try:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            except Exception:
                pass

    async def receive_json(self, data, **kwargs):
        if data.get("type") != "message":
            await self.send_json({"type": "error", "message": "unsupported event type"})
            return

        content = (data.get("content") or "").strip()
        role = data.get("role", "user")
        meta = data.get("meta")
        if not content:
            await self.send_json({"type": "error", "message": "content is required"})
            return
        if meta is not None and not isinstance(meta, dict):
            await self.send_json({"type": "error", "message": "meta must be an object"})
            return

        payload = await self._create_message(content=content, role=role, meta=meta or {})
        if payload is None:
            await self.send_json({"type": "error", "message": "Conversation not found"})
            return
        self._track_message(payload.get("ai_message_id"))
        await self.send_json({"type": "accepted", "conversation_id": self.conversation_id, **payload})

    async def event_relay(self, event):
        data = event.get("data", {})
        self._update_tracking_from_event(data)
        await self.send_json(data)

    async def _send_conversation_state(self):
        ai_state = cache.get(conv_ai_state(self.conversation_id), "idle")
        current_ai_message_id = cache.get(conv_current_ai_msg(self.conversation_id))
        self._track_message(current_ai_message_id)
        await self.send_json({
            "type": "state",
            "conversation_id": self.conversation_id,
            "ai_state": ai_state,
            "current_ai_message_id": current_ai_message_id,
        })

        if not current_ai_message_id:
            return

        current_state = cache.get(msg_state(current_ai_message_id))
        if current_state == "generating":
            partial = cache.get(msg_content(current_ai_message_id), "") or ""
            if partial:
                self._sent_content_len = len(partial)
                await self.send_json({
                    "type": "resume",
                    "conversation_id": self.conversation_id,
                    "ai_message_id": current_ai_message_id,
                    "content": partial,
                })
        elif current_state == "complete":
            content = cache.get(msg_content(current_ai_message_id), "") or ""
            self._sent_content_len = len(content)
            self._terminal_sent = True
            await self.send_json({
                "type": "complete",
                "conversation_id": self.conversation_id,
                "ai_message_id": current_ai_message_id,
                "content": content,
                "meta": read_runtime_meta(current_ai_message_id),
            })
        elif current_state and str(current_state).startswith("error:"):
            self._terminal_sent = True
            await self.send_json({
                "type": "error",
                "conversation_id": self.conversation_id,
                "ai_message_id": current_ai_message_id,
                "message": str(current_state)[len("error:"):],
            })

    async def _send_recent_history(self):
        messages = await self._get_recent_round_messages()
        await self.send_json({
            "type": "history",
            "conversation_id": self.conversation_id,
            "messages": messages,
        })

    async def _poll_conversation_state(self):
        while getattr(self, "_polling", False):
            await asyncio.sleep(0.2)
            current_ai_message_id = cache.get(conv_current_ai_msg(self.conversation_id))
            if not current_ai_message_id:
                continue

            if current_ai_message_id != self._tracked_ai_message_id:
                self._track_message(current_ai_message_id)

            current_state = cache.get(msg_state(current_ai_message_id))
            content = cache.get(msg_content(current_ai_message_id), "") or ""

            if current_state == "generating":
                if len(content) > self._sent_content_len:
                    delta = content[self._sent_content_len:]
                    self._sent_content_len = len(content)
                    await self.send_json({
                        "type": "chunk",
                        "conversation_id": self.conversation_id,
                        "ai_message_id": current_ai_message_id,
                        "content": delta,
                    })
                continue

            if current_state == "complete" and not self._terminal_sent:
                self._sent_content_len = len(content)
                self._terminal_sent = True
                await self.send_json({
                    "type": "complete",
                    "conversation_id": self.conversation_id,
                    "ai_message_id": current_ai_message_id,
                    "content": content,
                    "meta": read_runtime_meta(current_ai_message_id),
                })
                continue

            if current_state and str(current_state).startswith("error:") and not self._terminal_sent:
                self._terminal_sent = True
                await self.send_json({
                    "type": "error",
                    "conversation_id": self.conversation_id,
                    "ai_message_id": current_ai_message_id,
                    "message": str(current_state)[len("error:"):],
                })

    def _track_message(self, ai_message_id):
        if not ai_message_id:
            return
        if ai_message_id != self._tracked_ai_message_id:
            self._tracked_ai_message_id = ai_message_id
            self._sent_content_len = 0
            self._terminal_sent = False

    def _update_tracking_from_event(self, data: dict):
        ai_message_id = data.get("ai_message_id")
        self._track_message(ai_message_id)
        if data.get("type") in ("chunk", "resume"):
            content = data.get("content", "") or ""
            self._sent_content_len += len(content)
        elif data.get("type") == "complete":
            content = data.get("content", "") or ""
            self._sent_content_len = len(content)
            self._terminal_sent = True
        elif data.get("type") == "error":
            self._terminal_sent = True

    @database_sync_to_async
    def _get_conversation_owned(self):
        return Conversation.objects.filter(
            id=self.conversation_id,
            subject__user=self.user,
        ).first()

    @database_sync_to_async
    def _create_message(self, *, content: str, role: str, meta: dict):
        from .views import _create_message_and_maybe_chat_sync

        user_msg, ai_msg_id, ai_state = _create_message_and_maybe_chat_sync(
            user=self.user,
            conversation_id=self.conversation_id,
            content=content,
            role=role,
            meta=meta,
        )
        if user_msg is None:
            return None
        return {
            "user_message": MessageSerializer(user_msg).data,
            "ai_message_id": ai_msg_id,
            "ai_state": ai_state,
        }

    @database_sync_to_async
    def _get_recent_round_messages(self):
        recent_messages = list(
            self.conversation.messages.filter(
                Q(role="user") | Q(role="assistant", content__gt="") | Q(role="tool", content__gt="")
            ).order_by("-created_at")[:12]
        )
        recent_messages.reverse()
        return MessageSerializer(recent_messages, many=True).data
