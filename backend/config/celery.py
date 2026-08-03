import logging
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from celery import Celery
from celery.signals import task_postrun, task_prerun, worker_ready
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
env_file = os.getenv("ENV_FILE")
if env_file:
    env_path = Path(env_file)
    if not env_path.is_absolute():
        env_path = BASE_DIR / env_path
else:
    env_path = BASE_DIR / ".env"

load_dotenv(env_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
# llm 不是 INSTALLED_APPS，autodiscover 找不到 llm/tasks.py，显式 include
# plan 在 INSTALLED_APPS 中但 tasks.py 需要 LLM 调用，一并显式 include
app.autodiscover_tasks(["llm", "plan"])
# Celery 内部 import llm.tasks 需要 llm 在 sys.path
import llm  # noqa


logger = logging.getLogger(__name__)


def _mask_url(url: str) -> str:
    """把 URL 里的密码部分换成 ***，避免日志泄露凭据。"""
    if not url:
        return "<empty>"
    try:
        parts = urlsplit(url)
        if parts.password:
            user = parts.username or ""
            host = parts.hostname or ""
            port = f":{parts.port}" if parts.port else ""
            netloc = f"{user}:***@{host}{port}" if user else f":***@{host}{port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:
        return url


@worker_ready.connect
def _selfcheck_on_worker_ready(sender=None, **kwargs):
    """worker 起来后做一次 Redis / Postgres 连通性自检，便于排查启动期连接问题。"""
    from django.conf import settings

    # --- Redis (Celery broker / result backend) ---
    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    backend_url = getattr(settings, "CELERY_RESULT_BACKEND", "")
    logger.info("[selfcheck] Redis broker  -> %s", _mask_url(broker_url))
    if backend_url and backend_url != broker_url:
        logger.info("[selfcheck] Redis backend -> %s", _mask_url(backend_url))

    try:
        import redis  # django-redis 的传递依赖，必装

        client = redis.Redis.from_url(broker_url, socket_connect_timeout=5, socket_timeout=5)
        pong = client.ping()
        logger.info("[selfcheck] Redis PING   -> %s", "PONG" if pong else "FAIL")
    except Exception as exc:
        logger.error("[selfcheck] Redis 连接失败: %s", exc)

    # --- Postgres ---
    db = settings.DATABASES.get("default", {})
    host = db.get("HOST", "")
    port = db.get("PORT", "")
    name = db.get("NAME", "")
    user = db.get("USER", "")
    logger.info(
        "[selfcheck] Postgres     -> postgresql://%s@%s:%s/%s",
        user or "<no-user>", host or "<no-host>", port or "<no-port>", name or "<no-db>",
    )

    try:
        from django.db import connection

        connection.ensure_connection()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        logger.info("[selfcheck] Postgres SELECT 1 -> OK")
    except Exception as exc:
        logger.error("[selfcheck] Postgres 连接失败: %s", exc)


# --------------------------------------------------------------------
# DB 连接自愈
#   远程 Postgres / Redis 会把 idle 连接踢掉。Celery worker（尤其是 -P solo）
#   不像 Django request 那样每个请求开/关连接，会复用 stale connection
#   导致 InterfaceError: connection already closed。
#   每个 task 前后 close_old_connections() —— 死的连接会被丢，下次 ORM 自动重连。
# --------------------------------------------------------------------
@task_prerun.connect
def _close_db_connections_before_task(*args, **kwargs):
    from django.db import close_old_connections

    close_old_connections()


@task_postrun.connect
def _close_db_connections_after_task(*args, **kwargs):
    from django.db import close_old_connections

    close_old_connections()
