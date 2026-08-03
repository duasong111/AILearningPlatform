#!/bin/bash

set -e

# ========================================
# 前端一键部署脚本
# 用法: npm run deploy
# ========================================

SERVER_USER="aiteach_dev"
SERVER_HOST="82.156.53.195"
REMOTE_PATH="/opt/1panel/apps/openresty/openresty/www/sites/wqandgxy.top/index/"
LOCAL_PATH="dist/"

echo "=========================="
echo "📦 开始构建..."
echo "=========================="

# 检查 dist 目录是否存在
if [ ! -d "$LOCAL_PATH" ]; then
    echo "❌ 错误: dist 目录不存在，请先运行 npm run build"
    exit 1
fi

echo "=========================="
echo "🚀 开始上传到服务器..."
echo "=========================="

# 直接上传到目标目录（需要输入密码）
rsync -avz --no-perms --no-owner --no-group --delete --progress \
    "$LOCAL_PATH" \
    "${SERVER_USER}@${SERVER_HOST}:${REMOTE_PATH}"

echo "=========================="
echo "✅ 发布完成！"
echo "=========================="
echo "🌐 访问地址: https://wqandgxy.top"
echo "=========================="