#!/bin/bash
set -e

echo "=== AI Teach Backend 环境初始化 ==="

# 进入 backend 目录
cd "$(dirname "$0")"

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 需要 Python 3"
    exit 1
fi

echo "1. 安装 Python 依赖..."
pip install -q -r requirements.txt

echo "2. 检查 Django 配置..."
python manage.py check --deploy 2>/dev/null || python manage.py check

echo "3. 创建数据库迁移（如需要）..."
python manage.py makemigrations --no-input 2>/dev/null || true

echo ""
echo "=== 环境初始化完成 ==="
echo ""
echo "启动方式:"
echo "  本地开发: python manage.py runserver"
echo "  Docker:    docker-compose up -d"
echo ""
echo "注意: 本地运行需要先启动 PostgreSQL 和 Redis"