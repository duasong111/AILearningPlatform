#!/bin/bash
# ============================================================================
# 一键部署脚本 —— 拉新代码 + 重建镜像 + 跑迁移 + 滚动重启
#   使用: ./scripts/deploy.sh            (在 backend 目录)
#   或:   cd /opt/aiteach && ./backend/scripts/deploy.sh
# ============================================================================
set -e

# 自动定位到 backend 目录 (脚本所在目录的上一级)
cd "$(dirname "$0")/.."

echo "=== 1. git pull ==="
git pull

echo ""
echo "=== 2. 重建 web / celery 镜像 ==="
docker compose build web celery

echo ""
echo "=== 3. 跑数据库迁移 ==="
docker compose exec -T web python manage.py migrate --noinput

echo ""
echo "=== 4. 滚动重启 (旧容器停 + 新容器起) ==="
docker compose up -d

echo ""
echo "=== 5. 等 30s 看 health ==="
sleep 30
docker compose ps

echo ""
echo "=== 6. 端到端烟测 ==="
# 期望 400 (空 body, 但服务活)
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:38000/api/auth/login/ \
  -H 'Content-Type: application/json' -d '{}' -m 10)
echo "  POST /api/auth/login/  HTTP $code  (期望 400)"

echo ""
echo "=== ✓ deploy done ==="
echo "  看实时日志: docker compose logs -f web"
echo "  停服务:       docker compose down"
