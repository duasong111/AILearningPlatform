"""
WebSocket 鉴权中间件：从 query string 读取 ?token=<jwt>，用 simplejwt 校验，
把 user 挂到 scope['user']。校验失败或缺失 → AnonymousUser。
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def _user_from_token(raw: str):
    try:
        validated = JWTAuthentication().get_validated_token(raw)
        return JWTAuthentication().get_user(validated)
    except (InvalidToken, TokenError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        qs = parse_qs((scope.get("query_string") or b"").decode())
        raw = (qs.get("token") or [None])[0]
        scope["user"] = await _user_from_token(raw) if raw else AnonymousUser()
        return await super().__call__(scope, receive, send)
