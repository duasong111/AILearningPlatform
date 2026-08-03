"""WebSocket 路由。"""
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    # 基于 conversation_id 的统一对话流：收发消息都走这个 WS
    path("ws/conversations/<int:conversation_id>/", consumers.ConversationStreamConsumer.as_asgi()),
]
