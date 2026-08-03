.PHONY: help dev dev-env celery docker up down ps logs

help:
	@echo "开发环境管理命令:"
	@echo "  make dev     - 使用 daphne 启动 Django ASGI 服务"
	@echo "  make dev-env - 切换到本地开发环境 (.env.dev)"
	@echo "  make celery  - 启动 Celery worker"
	@echo "  make docker - 使用 Docker 环境 (.env.docker)"
	@echo "  make up     - 启动 Docker 服务"
	@echo "  make down   - 停止 Docker 服务"
	@echo "  make ps     - 查看容器状态"
	@echo "  make logs   - 查看容器日志"

dev:
	@echo "杀掉 8000 端口占用的进程..."
	@lsof -ti:8000 | xargs -r kill -9 2>/dev/null || true
	@echo "使用 daphne 启动 Django ASGI 服务"
	@ENV_FILE=.env daphne -b 0.0.0.0 -p 8000 --http-timeout 120 config.asgi:application

dev-env:
	@echo "切换到本地开发环境 (.env.dev)"
	@ln -sf .env.dev .env

celery:
	@echo "启动 Celery worker"
	@ENV_FILE=.env celery -A config worker -l info

docker:
	@echo "切换到 Docker 环境 (.env.docker)"
	@ln -sf .env.docker .env

up:
	docker compose up -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f web
