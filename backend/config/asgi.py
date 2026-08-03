"""
ASGI 入口：HTTP 走 Django 原生 ASGI，WebSocket 走 Channels + JWT 鉴权。
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from users.middleware import JWTAuthMiddleware          # noqa: E402
from users.routing import websocket_urlpatterns         # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
