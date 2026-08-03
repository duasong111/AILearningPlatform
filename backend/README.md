# AiTeach 后端服务

基于 Django + LangChain 的 AI 学习画像助手后端服务。

## 功能特性

- 用户认证 (JWT)
- 用户画像构建 Agent (对话式)
- 支持多种 LLM Provider (MiMo / OpenAI / Anthropic)
- 流式响应 (SSE)
- Docker Compose 一键部署

## 环境要求

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

## 环境配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd backend
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env.dev

# 编辑配置
vim .env.dev
```

主要配置项：

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# PostgreSQL (本地开发)
POSTGRES_HOST=localhost
POSTGRES_DB=aiteach
POSTGRES_USER=aiteach
POSTGRES_PASSWORD=your-password

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM Provider
LLM_PROVIDER=mimo                    # mimo / openai / anthropic
MIMO_API_KEY=your-mimo-api-key
MIMO_MODEL=mimo-v2.5-pro
```

### 3. Docker Compose 部署 (推荐)

```bash
# 0. macOS 上先启 Docker Desktop (首次需要)
open -a Docker
# 等 `docker info` 退出 0 (约 10-30s, 看右上角鲸鱼图标变绿)

# 1. 切换到 Docker 环境配置
make docker   # 等价于: ln -sf .env.docker .env

# 2. 首次构建 + 启动 (后台)
docker compose up -d --build
# 之后: docker compose up -d (跳过 build)

# 3. 跑迁移 (entrypoint 已自动跑, 手动跑:
docker compose exec web python manage.py migrate --noinput

# 4. 创建超级用户 (可选)
docker compose exec web python manage.py createsuperuser

# 5. 查看状态 / 日志
make ps       # = docker compose ps
make logs     # = docker compose logs -f web
```

#### 3.1 服务端口速查

| 服务 | 容器内端口 | 宿主机端口 | URL |
|---|---|---|---|
| web (daphne) | 38000 | 38000 | http://localhost:38000 |
| frontend (vite) | 35173 | 35173 | http://localhost:35173 |
| db (postgres) | 5432 | 35432 | — |
| redis | 6379 | 36379 | — |
| celery | — | — | 后台 worker, 无端口 |

注意: **前端是 35173, 后端 API 实际是 38000** —— Vite dev server 把 `/api/*` / `/ws/*` proxy 到 web 容器。
浏览器开 **http://localhost:35173**, 不要开 38000.

#### 3.2 常见问题

- **`Cannot connect to the Docker daemon`**: Docker Desktop 没启, 跑 `open -a Docker` 再试
- **build 时 apt-get update 404**: 之前 sources.list 写成了 trixie, 现已修成 bookworm (跟 python:3.12-slim 一致)
- **`No module named 'deepagents'`**: requirements.txt 已加 `deepagents>=0.6.12`, 重新 build (`docker compose up -d --build --no-cache web celery`)
- **LLM 走错 provider**: 容器内 `LLM_PROVIDER` 默认在 `.env.docker` (已改 minimax), 跟本地 dev 一致

### 4. 本地开发

```bash
# 切换到本地开发环境
make dev      # 或: ln -sf .env.dev .env

# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 运行开发服务器
python manage.py runserver
```

## 5. 生产环境 Docker 部署（详细手册）

> 上一节 3 是本地快速试跑。本节是 **生产服务器从零到上线** 的完整流程，按顺序照做就行。
> 适用场景：单台 Linux 服务器（2 vCPU / 4GB 起步） 或 macOS Docker Desktop 长期挂机。

### 5.1 服务器准备（一次性）

#### 操作系统 + 内核

- **Linux**：Ubuntu 22.04 LTS / Debian 12（bookworm）/ RHEL 9 都行。**4 GB 内存** + **2 vCPU** 起步，**20 GB 磁盘**。
- **macOS**：Docker Desktop 4.x+，**Resources ≥ 4 CPU / 6 GB 内存 / 60 GB 磁盘**。
- 内核要求 ≥ 4.15（支持 cgroup v2）。`uname -r` 验证。

#### 安装 Docker

**Linux 一键脚本**：
```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER  # 当前用户加入 docker 组, 免 sudo
newgrp docker                  # 立即生效
docker --version                # ≥ 20.10
docker compose version          # ≥ v2 (新版 compose 是 docker compose 子命令)

# 防火墙放行
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (如果走 nginx)
sudo ufw allow 443/tcp   # HTTPS
# 注意: 容器端口 (38000/35173/35432/36379) 不要直接放, 通过 nginx 反代
```

**macOS**：安装 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)，启动后系统栏出鲸鱼图标。

#### 准备项目目录

```bash
# 推荐: 把项目放 /opt/aiteach (Linux) 或 ~/Projects (macOS)
sudo mkdir -p /opt/aiteach && sudo chown $USER:$USER /opt/aiteach
cd /opt/aiteach
git clone <your-fork-url> aiteach
cd aiteach
```

### 5.2 首次部署

#### Step 1：环境变量

```bash
cd backend
# 复制模板, 改 secret + LLM key
cp .env.example .env.docker

# 用 vim/nano 编辑以下 4 个必填项
#   SECRET_KEY         = 一串 50+ 字符随机 (python -c "import secrets; print(secrets.token_urlsafe(64))")
#   POSTGRES_PASSWORD  = 一串 32+ 字符
#   MINIMAX_API_KEY    = 你的 LLM key (或换 mimo/openai)
#   LLM_PROVIDER       = minimax / mimo / openai

# 关键: 这是生产 secret, 千万别 commit 到 git
chmod 600 .env.docker
```

#### Step 2：构建 + 启动

```bash
make docker   # = ln -sf .env.docker .env (切换环境)

# 首次构建 (会拉 base 镜像 + apt 装 gcc/libpq + pip 装 100+ 包, 约 5-10 分钟)
docker compose build

# 后台启动 5 个 service
docker compose up -d

# 看启动日志 (entrypoint 会自动跑 makemigrations + migrate)
docker compose logs -f web
# 看到 "Listening on 0.0.0.0:38000" 或 "Uvicorn running on..." 即可 Ctrl+C
```

#### Step 3：烟测

```bash
# 等 30-60s 让 healthcheck 转 healthy
docker compose ps
# 期望 4/4 healthy: db, redis, web (可能 starting), celery

# 端到端
curl -X POST http://localhost:38000/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"<your-admin>","password":"<pw>"}' -m 10 | python3 -c "import sys,json; print('token len =', len(json.load(sys.stdin).get('access','')))"
# 期望: token len = 200+

# 看 LLM 链路 (创建 superuser 调一次 quiz generate)
docker compose exec -T web python manage.py createsuperuser
curl -X POST http://localhost:38000/api/quiz/auto-generate/ \
  -H 'Content-Type: application/json' -H "Authorization: Bearer ${TOKEN}" \
  -d '{"subject_id":1,"count":1}' -m 60 -w "\n  HTTP %{http_code}\n" -o /dev/null
```

#### Step 4：配置反向代理（生产推荐）

**不要把 daphne 38000 直接暴露公网**（无 HTTPS / 无静态文件 / 无 WebSocket 反代）。用 nginx：

```bash
sudo apt install -y nginx
sudo tee /etc/nginx/sites-available/aiteach <<'EOF'
upstream aiteach_web { server 127.0.0.1:38000; }
upstream aiteach_frontend { server 127.0.0.1:35173; }

server {
    listen 80;
    server_name api.your-domain.com;  # 改
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    ssl_certificate     /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    # 客户端 API
    location /api/  { proxy_pass http://aiteach_web; proxy_set_header Host $host; }
    # 客户端 WebSocket
    location /ws/   {
        proxy_pass http://aiteach_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}

# 另一个 server block 跑 frontend (35173)
# 实际推荐: vite build → 静态文件 → nginx 直接 serve, 不要用 dev server
# 详见 5.6 节
EOF
sudo ln -s /etc/nginx/sites-available/aiteach /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

申请 HTTPS 证书：
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.your-domain.com
```

### 5.3 日常运维命令

```bash
# 看服务状态
docker compose ps
docker compose logs -f web        # 跟 web 日志
docker compose logs -f celery      # 跟 celery 日志
docker compose logs --tail=200 web  # 看最近 200 行

# 容器内操作
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
docker compose exec -T web python manage.py makemigrations <app>
docker compose exec -T web python manage.py migrate

# 重启单个 service
docker compose restart web
docker compose restart celery

# 整栈重启
docker compose restart

# 资源监控
docker stats --no-stream
```

### 5.4 升级流程

```bash
# 1. 拉新代码
cd /opt/aiteach/aiteach
git pull

# 2. 看有没有 schema 变更 (后端代码有 models.py 改动)
#    改了就跑迁移:
cd backend
docker compose exec -T web python manage.py migrate --noinput

# 3. 重新构建 + 滚动重启 (web 不停机)
cd /opt/aiteach/aiteach
docker compose build web celery       # 重新 build 受影响的 image
docker compose up -d                  # 自动起新容器, 停旧容器

# 4. 验证
docker compose ps                     # 看是不是新 image
curl -X POST http://localhost:38000/api/auth/login/ -d '{}' -H 'Content-Type: application/json' -m 5
# 期望 400 (服务活)
```

**回滚**（如果新版本有 bug）：
```bash
git checkout HEAD~1                    # 回退代码
docker compose build web celery
docker compose up -d
# 数据迁移**不能回滚** (manage.py migrate 没有 down-migration)
# 严重 schema 错的话: 从备份恢复
```

### 5.5 数据备份

```bash
# 1. Postgres 备份 (每天 cron, 留 7 天)
docker compose exec -T db pg_dump -U aiteach aiteach | gzip > /backup/aiteach_$(date +%F).sql.gz
# 加 cron:
# 0 3 * * * cd /opt/aiteach && /usr/local/bin/backup.sh

# 2. Redis 备份 (RDB snapshot)
docker compose exec -T redis sh -c 'redis-cli BGSAVE && cp /data/dump.rdb /backup/'

# 3. 备份文件挪到异地 (rsync / s3 / 阿里云 OSS)
# 4. 定期演练恢复:
zcat /backup/aiteach_2026-07-05.sql.gz | docker compose exec -T db psql -U aiteach aiteach
```

### 5.6 前端生产化（可选）

vite dev server 跑 35173 适合 dev，**生产不应该用**（慢、没压缩、每次都编译）。生产应该：

```bash
# 改 web/Dockerfile 为多阶段 build
# 1. 阶段: node:22 → npm ci + npm run build
# 2. 阶段: nginx:alpine → 拷 dist/ → nginx 配 SPA try_files

# 或者最简单: 用现有 web 容器跑 vite preview:
docker compose exec web sh -c "cd /app/frontend 2>/dev/null || cd /web; npm run build"
# 拷 dist/ 到 nginx 静态目录
```

### 5.7 监控 + 告警

**最小监控**（基于 docker compose 自身）：
- UptimeRobot / 阿里云云监控: 定期 GET `https://api.your-domain.com/api/auth/login/`, 期望 400
- Docker log: journald / Loki + Promtail / ELK
- 告警: 当 `docker ps` 显示 `Unhealthy` 时发邮件/Slack

**推荐 Prometheus + Grafana**（可选）：
```bash
# 加 cadvisor + node-exporter + prometheus + grafana 到 compose
# 监控: CPU/内存/磁盘/网络, 容器重启次数, daphne 请求延迟
```

### 5.8 故障排查

| 现象 | 排查 |
|---|---|
| `docker compose ps` 显示 web unhealthy | `docker compose logs web` 看启动错误；80% 是 entrypoint.sh / migrate 失败 |
| `curl /api/auth/login/` 返 502 | daphne 进程死了 → `docker compose restart web`；看日志 |
| `curl /api/auth/login/` 返 500 | 后端代码错 → `docker compose logs --tail=50 web` |
| 登录返 401 但密码正确 | DB 没 user → `docker compose exec web python manage.py createsuperuser` |
| WebSocket 连不上 | nginx 需要 `proxy_set_header Upgrade` 配置 (见 5.2) |
| 刷题 / 测评返 502/500 | Dify LLM 不可达 → 看 web 日志是不是 Dify timeout |
| celery worker 不收 task | redis 没启 → `docker compose ps` 看 redis；或网络问题 |
| 数据库连接满 | 看 `docker compose exec db psql -U aiteach -c "SELECT count(*) FROM pg_stat_activity"` |
| 容器 OOM 杀掉 | `dmesg \| grep -i killed`；考虑加 `--memory 1g` 限制 |

### 5.9 生产加固清单（部署前过一遍）

- [ ] `SECRET_KEY` ≥ 50 字符随机, 不在 git 里
- [ ] `POSTGRES_PASSWORD` ≥ 32 字符, 跟 db / web / celery 三个 service 一致
- [ ] `LLM_*_API_KEY` 不在 git 里 (`.env.docker` 在 .gitignore)
- [ ] `.env.docker` 文件权限 `chmod 600`
- [ ] 服务器防火墙只开 22/80/443, **不要** 直接暴露 38000/35432/36379
- [ ] 启用 HTTPS（certbot 自动续期）
- [ ] nginx 加 rate limit（防刷）
- [ ] 配置数据库每日自动备份
- [ ] 配置日志轮转（logrotate 或 Loki）
- [ ] 启用 Docker restart 策略（已默认 `--restart unless-stopped`）
- [ ] 服务器时间同步（`chrony` / `ntp`）— 影响 JWT 过期判断
- [ ] 监控 + 告警（uptime check + 异常重启告警）

### 5.10 一键脚本（可选）

放 `backend/scripts/deploy.sh`：
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "→ git pull"
git pull
echo "→ build"
docker compose build web celery
echo "→ migrate"
docker compose exec -T web python manage.py migrate --noinput
echo "→ restart"
docker compose up -d
echo "→ wait healthy"
sleep 30
docker compose ps
echo "✓ deploy done"
```

`chmod +x backend/scripts/deploy.sh` 后，服务器上 `cd /opt/aiteach && ./backend/scripts/deploy.sh` 就升级完。

---

## API 接口

### 认证接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/auth/register/` | POST | 用户注册 |
| `/api/auth/login/` | POST | 用户登录 |
| `/api/auth/refresh/` | POST | 刷新 Token |

### 用户画像接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/profile/` | GET | 获取用户画像 |
| `/api/profile/build/stream/` | POST | 流式构建画像 (15轮对话) |

### 请求示例

```bash
# 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# 流式构建画像
curl -X POST http://localhost:8000/api/profile/build/stream/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "我想学数据结构"}' \
  --no-buffer
```

## 测试脚本

```bash
# 终端对话 (15轮)
source .env && python test/terminal_chat.py

# 流式 API 测试
source .env && python test/test_streaming.py

# MiMo API 直接测试
source .env && python test/test_mimo_api.py
```

## 项目结构

```
backend/
├── config/              # Django 配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── users/               # 用户模块
│   ├── models.py        # User, UserProfile 模型
│   ├── views.py         # 认证视图
│   ├── views_llm.py     # 画像构建视图
│   └── urls.py
├── llm/                 # LLM 模块
│   ├── config.py       # LLM 配置
│   ├── agents/         # LangChain Agents
│   │   └── profile_agent.py
│   ├── prompts/       # 对话提示词
│   │   └── profile_prompts.py
│   └── schemas/       # Pydantic Schemas
│       └── profile_schema.py
├── test/               # 测试脚本
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── requirements.txt
```

## 管理命令

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 查看 API 文档 (需要安装 drf-spectacular)
python manage.py spectacular --schema > schema.yml
```

## 开发说明

### 切换环境

```bash
make dev    # 本地开发 (.env.dev)
make docker # Docker 部署 (.env.docker)
```

### 添加依赖

```bash
# 编辑 requirements.txt
echo "package-name>=version" >> requirements.txt

# 在容器中安装
docker compose exec web pip install package-name
```

## License

MIT