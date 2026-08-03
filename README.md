<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./web/src/assets/logo.svg">
    <img alt="AiTeach Logo" src="./web/src/assets/logo.svg" width="120" height="120">
  </picture>
</p>

<h1 align="center">AiTeach（学径）</h1>

<p align="center">
  <strong>多智能体个性化学习平台</strong><br>
  自适应学习规划 · AI 对话辅导 · 知识图谱 · 智能出题测评 · 视频课程生成
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?logo=django" alt="Django">
  <img src="https://img.shields.io/badge/Vue-3%20beta-4FC08D?logo=vue.js" alt="Vue 3">
  <img src="https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-FF4438?logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/Celery-5.3-37814A?logo=celery" alt="Celery">
  <img src="https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain" alt="LangChain">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

---

## 📖 项目简介

**AiTeach（学径）** 是一个基于 AI 的智能教育系统，采用**多智能体（Multi-Agent）架构**为用户提供真正个性化的学习体验。系统通过多轮对话构建用户画像，自动生成学习计划，并借助 AI 私教提供全天候的学科辅导。

### 核心功能

| 功能模块 | 描述 |
|---------|------|
| 🧠 **AI 对话辅导** | 多智能体私教，支持学科问答、出题练习、视频推荐、课件生成 |
| 📋 **学习计划** | 自动生成个性化学习计划，支持动态调整与基线计划 |
| 🧩 **知识图谱** | 3D 可视化知识星图，展示知识点关联与掌握程度 |
| 📝 **智能出题** | 自动生成练习题与综合测评，支持多种题型 |
| 📹 **视频课程** | AI 视频课程生成（接入 B 站教学资源推荐） |
| 📚 **电子书架** | 书籍阅读与 AI 对话助手 |
| 👤 **用户画像** | 通过多轮对话构建用户画像，持续更新学习偏好与知识水平 |
| 📊 **学习记录** | 学习时长统计、资源历史、报告生成 |

---

## 🏗️ 系统架构

### 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                         Clients                               │
│            Browser (Vue 3 SPA)      Mobile (Future)           │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS / WSS
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                      CDN / Nginx (Future)                     │
│                   静态资源 / 反向代理 / SSL                    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     Frontend (Vue 3)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐│
│  │PrimeVue/ │  │ Pinia    │  │  Vue     │  │    Axios     ││
│  │Element+  │  │ State    │  │  Router  │  │  HTTP + WS   ││
│  │UI 组件库 │  │状态管理  │  │ 路由守卫 │  │  通信层      ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   WebSocket Composables                     │ │
│  │    use_conv_ws.ts (对话流)   use_profile_chat_ws.ts (画像)│ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API (JWT) / WebSocket (WS Token)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (Django + ASGI)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Daphne (ASGI Server)                    │  │
│  │              端口 8000 / WebSocket 路由                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Django REST Framework API                    │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│  │
│  │  │ Users  │ │  Plan  │ │  Quiz  │ │ Video  │ │Learning││  │
│  │  │认证/   │ │学习    │ │出题    │ │视频    │ │学习    ││  │
│  │  │对话/   │ │计划    │ │练习    │ │课程    │ │记录    ││  │
│  │  │知识图谱│ │基线/   │ │考试    │ │生成    │ │聚合    ││  │
│  │  │用户画像│ │调整器  │ │队列    │ │        │ │        ││  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘│  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Channels WebSocket 消费者 (Consumers)          │  │
│  │         ChatConsumer / ProfileConsumer (JWT 认证)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 LLM 多智能体核心层                         │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐    │  │
│  │  │  Chat      │ │  Tutor     │ │ Profile / Plan     │    │  │
│  │  │  Agent     │ │  Agent     │ │ Agents             │    │  │
│  │  │  通用对话  │ │  私教调度   │ │ 画像评估/计划生成  │    │  │
│  │  └─────┬──────┘ └─────┬──────┘ └────────────────────┘    │  │
│  │        │               ▼                                     │  │
│  │        │   ┌─────────────────────────────┐                 │  │
│  │        │   │     子智能体调度            │                 │  │
│  │        │   │ Quiz/Video/Doc Assistant   │                 │  │
│  │        │   └─────────────────────────────┘                 │  │
│  │        │               │                                     │  │
│  │        ▼               ▼                                     │  │
│  │  ┌──────────────────────────────────────────────┐         │  │
│  │  │        LangChain Chains / Tools               │         │  │
│  │  │  quiz_chain / practice_chain / plan_chain   │         │  │
│  │  │  video_chain / knowledge_tools / plan_tools │         │  │
│  │  └──────────────────────────────────────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Celery 异步任务层 (Redis Broker)                │  │
│  │    tasks.py (LLM 调度) / plan/tasks.py / quiz/tasks.py   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌────────────────┐ ┌────────────┐ ┌────────────────────────┐
│   PostgreSQL   │ │   Redis    │ │    Dify Workflow       │
│   (主数据库)    │ │(缓存/队列/ │ │  (B站推荐/知识库检索/   │
│   端口 5432    │ │  WebSocket)│ │   题库生成)            │
│                │ │  端口 6379 │ │                        │
└────────────────┘ └────────────┘ └────────────────────────┘
```

### 技术选型决策

- **Django + DRF**：高生产力的 Python Web 框架，ORM + Admin + Auth 一站式解决
- **Daphne ASGI**：支持 Django Channels 的 ASGI 服务器，优于 uvicorn 对 Django 的兼容性
- **Channels + Redis**：WebSocket 长连接支持，所有 LLM 流式输出实时推送前端
- **Celery + Redis**：所有耗时的 LLM 调用异步化，不阻塞 HTTP 请求响应
- **LangChain**：模块化 LLM 调用抽象，支持多 Provider 热切换
- **Pinia + 持久化**：前端状态本地持久化，刷新页面不丢状态

---

## 🛠️ 技术栈详解

### 后端 (backend/)

#### 核心框架

| 技术 | 版本 | 说明 |
|------|------|------|
| **Django** | 5.2+ | Web 框架，提供 ORM、Admin、Auth、Middleware |
| **Django REST Framework** | 3.14+ | RESTful API 框架，序列化器 + 视图集 + 过滤 |
| **daphne** | 4.0+ | ASGI 服务器，替代 gunicorn 处理 ASGI + WebSocket |
| **channels** | 4.0+ | WebSocket 支持，Channel Layer + Consumer 抽象 |
| **channels-redis** | 4.0+ | Redis 后端的 Channel Layer，支持跨进程 WebSocket |

#### 数据层

| 技术 | 版本 | 说明 |
|------|------|------|
| **PostgreSQL** | 16+ | 主数据库，使用 psycopg2-binary 驱动 |
| **Redis** | 7+ | 多用途：django-redis 缓存 + Celery Broker + Channels Layer |
| **django-redis** | 5.4+ | Redis 缓存后端，SOCKET_TIMEOUT=5 防死连接 |
| **psycopg2-binary** | 2.9+ | PostgreSQL 驱动，支持连接池 + keepalive |

#### 异步任务

| 技术 | 版本 | 说明 |
|------|------|------|
| **Celery** | 5.3+ | 分布式异步任务队列，Redis 作为 Broker |
| **django-celery-results** | — | Celery TaskResult 持久化到 DB（可选） |

#### 认证与安全

| 技术 | 说明 |
|------|------|
| **djangorestframework-simplejwt** | JWT Access Token（2小时）+ Refresh Token（7天），自动轮转 |
| **django-cors-headers** | CORS 跨域支持 |
| **django-filter** | DRF 后端过滤查询参数 |
| ** argon2** | 密码哈希（通过 Django 内置） |

#### LLM / AI

| 技术 | 版本 | 说明 |
|------|------|------|
| **LangChain** | 0.3+ | LLM 调用抽象框架，Runnable / Chain / Agent 抽象 |
| **langchain-core** | 0.3+ | LangChain 核心：PromptTemplate、LLMChain、Agent |
| **langchain-openai** | 0.2+ | OpenAI GPT 模型封装 |
| **langchain-anthropic** | 0.2+ | Anthropic Claude 模型封装 |
| **langchain-community** | 0.3+ | 第三方集成（Dify、ChromaDB 等） |
| **pydantic** | 2.0+ | LLM 输出结构化数据验证，Agent 工具 schema |

#### 其他 Python 库

| 技术 | 说明 |
|------|------|
| **gunicorn** | WSGI 服务器（备用） |
| **Pillow** | 图片处理（用户头像等） |
| **python-dotenv** | `.env` 环境变量加载 |
| **requests** | HTTP 客户端（Dify 工作流调用） |

#### 支持的 LLM Provider

系统支持通过 `LLM_PROVIDER` 环境变量热切换，无需改代码：

| Provider | 环境变量值 | 默认模型 | Base URL |
|----------|-----------|---------|---------|
| **MiMo** (小米) | `mimo` | `mimo-v2.5-pro` | `https://api.xiaomimimo.com/v1` |
| **MiniMax** | `minimax` | `MiniMax-M3` | `https://api.minimaxi.com/v1` |
| **OpenAI** | `openai` | `gpt-4o-mini` | `https://api.openai.com/v1` |
| **Anthropic** | `anthropic` | `claude-sonnet-4-6-20250514` | `https://api.anthropic.com` |
| **ZhipuAI** (智谱) | `zhipu` | `glm-5.2` | `https://yuanyuaicloud.cn/v1` |

#### 后端 API 模块

| 模块 (Django App) | 主要模型 | 核心视图/功能 |
|------------------|---------|------------|
| **users** | `User`, `Subject`, `Conversation`, `Message`, `KnowledgeNode` | 认证、JWT 刷新、用户画像、知识图谱、WebSocket Consumers |
| **plan** | `LearningPlan`, `PlanAdjustLog` | 计划 CRUD、基线计划生成、Celery 定时调整 |
| **quiz** | `QuizGenerationRecord`, `PracticeSession`, `ExamSession` | 出题、练习分析、队列管理、Dify 题库生成 |
| **video** | `VideoCourseRecord` | 视频课程 CRUD、OpenMAIC 视频生成任务 |
| **learning** | `StudySession`, `ReadingSession`, `Book` | 学习时长聚合、阅读会话心跳、资源历史 |

#### LLM 核心层 (llm/)

```
llm/
├── config.py              # LLM Provider 配置（from_env 单例模式）
├── runtime.py             # LLM 运行时状态（Redis key 管理）
├── tasks.py               # Celery 异步任务：llm_chat / llm_stream
├── reasoning_patch.py     # reasoning_content 字段兼容补丁
├── state_keys.py          # Redis state key 常量定义
│
├── agents/                # LangChain Agent 实现
│   ├── chat_agent.py              # 通用对话 Agent
│   ├── tutor_agent.py             # 多智能体私教 Agent（核心调度器）
│   ├── plan_agent.py              # 学习计划生成 Agent
│   ├── profile_conversation_agent.py  # 画像对话 Agent
│   ├── profile_evaluator_agent.py    # 画像评估 Agent
│   ├── practice_generator.py          # 练习题生成 Agent
│   ├── knowledge_assessor.py          # 知识点掌握评估 Agent
│   ├── doc_writer.py                  # 图文文档生成 Agent
│   └── llm_factory.py                # LLM 实例工厂（多 Provider）
│
├── chains/                # LangChain Chain 实现
│   ├── quiz_chain.py              # 出题 Chain（LangChain LCEL）
│   ├── practice_chain.py          # 练习分析 Chain
│   ├── plan_chain.py              # 计划生成 Chain
│   └── video_chain.py             # 视频课程生成 Chain
│
├── prompts/               # Prompt 模板（System / Human Message）
│   ├── chat_prompts.py
│   ├── exam_prompts.py
│   ├── plan_prompts.py
│   ├── practice_prompts.py
│   ├── profile_prompts.py
│   ├── quiz_prompts.py
│   └── video_prompts.py
│
├── schemas/               # Pydantic Output Schema（LLM 结构化输出）
│   ├── quiz_schema.py
│   ├── practice_schema.py
│   └── video_schema.py
│
├── sub_agents/           # 子智能体实现（Tutor Agent 调度）
│   ├── quiz_sub_agent.py
│   ├── exam_sub_agent.py
│   ├── plan_sub_agent.py
│   └── video_sub_agent.py
│
└── tools/                # LangChain Tools（Agent 可调用的工具）
    ├── knowledge_tools.py    # 知识节点查询、掌握度查询
    ├── plan_tools.py         # 计划查询、进度更新
    └── profile_tools.py      # 画像查询、更新
```

---

### 前端 (web/)

#### 构建与开发

| 技术 | 版本 | 说明 |
|------|------|------|
| **Vite** | 8.0+ | 构建工具，HMR 热更新，支持 ESM Native |
| **Vue** | 3 beta | 响应式框架，Composition API + `<script setup>` |
| **TypeScript** | 6.0+ | 类型系统，严格模式（`strict: true`） |
| **vue-tsc** | 3.2+ | TypeScript 类型检查 |
| **Vitest** | 4.1+ | 单元测试框架 |
| **Prettier** | 3.8+ | 代码格式化（集成 ESLint） |

#### UI 组件库

| 技术 | 版本 | 说明 |
|------|------|------|
| **PrimeVue** | 4.5+ | 主要 UI 组件库，组件丰富（DataTable、Dialog 等） |
| **Element Plus** | 2.14+ | 辅助 UI 库（Form、Input、Select 等） |
| **Tailwind CSS** | 4.3+ | 工具类 CSS，快速布局 |
| **motion-v** | 2.3+ | 动画库（Framer Motion for Vue） |
| **typed.js / typeit** | — | 打字机效果动画 |
| **postprocessing** | 6.39+ | 后处理效果（Bloom、Glow 等） |

#### 状态管理与路由

| 技术 | 版本 | 说明 |
|------|------|------|
| **Pinia** | 3.0+ | Vue 3 官方推荐状态管理 |
| **pinia-plugin-persistedstate** | 4.7+ | Pinia 状态持久化（localStorage） |
| **Vue Router** | 5.1+ | SPA 路由，导航守卫（JWT 校验） |

#### HTTP 通信

| 技术 | 版本 | 说明 |
|------|------|------|
| **Axios** | 1.17+ | HTTP 客户端，统一拦截器（请求 auth / 响应刷新 token） |
| **WebSocket** | Native | 通过 Composables 封装（`use_conv_ws.ts` 等） |

#### 3D 与数据可视化

| 技术 | 版本 | 说明 |
|------|------|------|
| **Three.js** | 0.184+ | 3D 渲染引擎（知识星图背景等） |
| **3d-force-graph** | 1.80+ | 力导向图 3D 可视化（知识节点关系） |
| **ECharts** | 6.1+ | 图表库（学习报告统计） |
| **ogl** | 1.0+ | 轻量 WebGL 库（高性能渲染） |

#### 文档与媒体

| 技术 | 版本 | 说明 |
|------|------|------|
| **markdown-it** | 14.2+ | Markdown 解析 |
| **markdown-it-texmath** | 1.0+ | Markdown 内联数学公式 |
| **KaTeX** | 0.17+ | 数学公式渲染（比 MathJax 更快） |
| **highlight.js** | 11.11+ | 代码语法高亮 |
| **pdfjs-dist** | 6.0+ | PDF 渲染（电子书阅读器） |
| **simple-mind-map** | 0.14+ | 思维导图组件 |

#### 前端目录结构

```
web/src/
├── main.ts                        # 入口：注册 Pinia / Router / PrimeVue / ElementPlus
├── App.vue                        # 根组件（仅 <router-view>）
│
├── router/index.ts                # 路由表 + 导航守卫（JWT 校验 / 白名单）
│
├── layouts/
│   └── AppShell.vue               # 主布局：导航栏 + 内容区 + 侧边栏
│
├── views/                         # 页面组件（按路由模块划分）
│   ├── auth/                      # 登录 / 注册
│   ├── acquisition/               # 新人引导 / 欢迎页
│   ├── onboarding/               # 选课 + 课程引导
│   ├── home/                     # 首页仪表盘
│   ├── learning/                 # 学习记录 / 报告
│   ├── galaxy/                   # 3D 知识星图
│   ├── tutor/                    # AI 私教对话
│   ├── plan/                     # 学习计划 / 课程详情 / 知识点
│   ├── book/                     # 电子书架 / 阅读器
│   ├── video/                    # 视频播放器 / 课程
│   ├── practice/                 # 刷题练习
│   ├── exam/                     # 综合测评
│   ├── profile/                  # 个人中心
│   ├── settings/                 # 设置页
│   ├── about/                    # 关于页
│   ├── demo/                     # Demo 页面
│   └── design/                   # 设计系统演示
│
├── components/                    # 可复用组件
│   ├── WelcomeModal.vue           # 欢迎弹窗
│   ├── UserWidget.vue             # 用户信息组件
│   ├── BlurText.vue               # 模糊文字效果
│   ├── MarkdownContent.vue        # Markdown 渲染组件
│   ├── StreamingMarkdown.vue     # 流式 Markdown（LLM 输出）
│   ├── effects/                   # 视觉效果
│   │   ├── FlipCard.vue           # 翻转卡片
│   │   ├── HyperspeedBackground.vue # 速度线背景
│   │   └── RotatingText.vue       # 旋转文字
│   ├── icons/                     # 图标系统（brand / nav / status / subject / ui）
│   └── ui/                        # 高级视觉效果组件
│       ├── apple-card-carousel/    # Apple 风格卡片轮播
│       ├── bending-gallery/        # 弯曲画廊
│       ├── card-3d/               # 3D 卡片
│       ├── flip-card/             # 翻转卡片
│       ├── lamp-effect/           # 台灯效果
│       └── warp-background/       # 扭曲背景
│
├── composables/                   # 组合式逻辑（Vue Composable）
│   ├── use_conv_ws.ts             # 对话 WebSocket（流式 Markdown 渲染）
│   ├── use_profile_chat_ws.ts     # 画像对话 WebSocket
│   ├── use_markdown.ts            # Markdown 渲染逻辑
│   └── useMouseState.ts           # 鼠标状态跟踪
│
├── stores/                        # Pinia 状态管理
│   ├── user.ts                    # 用户认证状态（JWT Token）
│   ├── currentSubject.ts           # 当前选中学科
│   ├── mySubjects.ts              # 用户学科列表
│   ├── mastery.ts                  # 知识掌握度
│   ├── onboarding.ts               # 引导流程状态
│   └── settings.ts                 # 用户设置
│
├── api/                           # API 层（统一 Axios 实例）
│   ├── http.ts                    # Axios 实例（baseURL / 请求拦截 / Token 刷新）
│   ├── endpoints.ts               # 所有 API 端点常量
│   ├── user.ts                    # 认证 API
│   ├── profile.ts                 # 用户画像 API
│   ├── plan.ts                    # 学习计划 API
│   ├── quiz.ts                    # 出题 / 练习 API
│   ├── video.ts                   # 视频课程 API
│   ├── learning.ts                # 学习记录 API
│   ├── subjects.ts                # 学科 API
│   ├── conversations.ts           # 对话 API
│   ├── exam.ts                    # 考试 API
│   ├── practice.ts                # 练习 API
│   └── mocks/                     # Mock 数据（开发调试用）
│
├── types/                         # TypeScript 类型定义
│   ├── response.d.ts              # 通用 API 响应结构（JWT / 错误格式）
│   ├── chat.d.ts                  # 对话相关类型
│   ├── learning.d.ts              # 学习记录类型
│   ├── shims.d.ts                 # 模块补充类型（*.d.ts）
│   └── 3d-force-graph.d.ts        # 第三方库类型补充
│
├── data/                          # 静态数据
│   ├── books.ts                   # 书架书籍数据
│   └── subject-covers.ts          # 学科封面数据
│
└── assets/                        # 静态资源
    ├── base.css                   # CSS 变量（设计 Token：颜色 / 字体 / 间距）
    ├── main.css                   # 全局样式
    ├── logo.svg                   # Logo
    ├── avatar.jpg                 # 默认头像
    ├── book/                      # 书籍封面图片
    ├── chat/                      # 对话相关图片
    └── covers/                    # 学科封面图片
```

---

## 🔌 第三方 API / 服务集成

| 服务 | 用途 | 集成方式 | 配置位置 |
|------|------|---------|---------|
| **OpenAI API** | LLM 推理（可切换 Provider） | LangChain `langchain-openai` | `backend/.env` — `OPENAI_API_KEY` |
| **Anthropic API** | LLM 推理（可切换 Provider） | LangChain `langchain-anthropic` | `backend/.env` — `ANTHROPIC_API_KEY` |
| **MiniMax API** | LLM 推理 + 书籍阅读对话 | LangChain + 前端直调 | 后端 `MINIMAX_API_KEY` + 前端 `VITE_MINIMAX_API_KEY` |
| **MiMo API** (小米) | LLM 推理（默认 Provider） | LangChain | `backend/.env` — `MIMO_API_KEY` |
| **ZhipuAI API** (智谱) | LLM 推理（可切换 Provider） | LangChain | `backend/.env` — `ZHIPU_API_KEY` |
| **Dify** | B 站视频搜索 / 知识库检索 / 题库生成 | `requests` 调用 Dify REST API | `backend/dify_workflow/.env` |
| **OpenMAIC** | AI 视频课程生成 | HTTP 轮询拉取生成进度 | 后端 `VIDEO_GEN_HOST` + 前端 `VITE_OPENMAIC_URL` |
| **Bilibili (B 站)** | 教学视频资源 | 通过 Dify 工作流接入 | Dify `bili_push.py` |

---

## 🧠 多智能体架构详解

### Agent 分层设计

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                     │
│          WebSocket 流式接收 → Markdown 渲染              │
└──────────────────────────┬──────────────────────────────┘
                           │ 事件流
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Celery 异步任务调度层 (tasks.py)            │
│        llm_chat() / llm_stream() / plan_generate()      │
└──────────────────────────┬──────────────────────────────┘
                           │ LLM 调用
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Tutor Agent (核心)                     │
│     意图识别 → 子智能体调度 → 结果聚合 → 流式输出         │
│                                                          │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │ practice_    │  │   video_     │  │  doc_        │  │
│   │ quiz         │  │   assistant  │  │  assistant   │  │
│   │ (出题)       │  │ (视频推荐)   │  │ (课件生成)   │  │
│   └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
│          │                 │                             │
│          ▼                 ▼                             │
│   ┌──────────────┐  ┌──────────────┐                     │
│   │ quiz_chain   │  │ Dify Workflow│                     │
│   │ (LangChain)  │  │ (Bili Push) │                     │
│   └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### 四大核心 Agent

#### 1. Chat Agent — 通用对话
- **职责**：回答学科问题，解释概念，提供例题
- **Chain**：`chat_prompts` → LLM → streaming response
- **工具**：无外部工具调用，直接 LLM 生成

#### 2. Tutor Agent — 多智能体私教（核心）
- **职责**：综合教学，调度子智能体处理专项任务
- **子智能体类型**：
  - `practice_quiz` — 根据知识点生成练习题
  - `video` — 搜索推荐 B 站教学视频
  - `doc_assistant` — 课件内容生成
  - `doc_writer` — 图文文档 / 知识图解生成
- **决策逻辑**：解析用户意图，按需调用对应子智能体

#### 3. Profile Agent — 用户画像
- **组成**：
  - `ProfileConversationAgent` — 多轮对话采集用户偏好
  - `ProfileEvaluatorAgent` — 分析对话内容，更新画像数据
- **画像维度**：学习目标、知识水平、学习风格、时间偏好

#### 4. Plan Agent — 学习计划
- **职责**：根据用户画像生成个性化学习计划
- **流程**：`profile_prompts` → `plan_chain` → `plan_adjuster` → DB
- **动态调整**：基于学习记录自动调整计划优先级

### 流式输出架构

```
LLM Provider (SSE/流式)
    │
    │ chunks (Server-Sent Events)
    ▼
Celery Worker (celery tasks.py)
    │
    │ events (Redis Pub/Sub)
    ▼
Django Channels Consumer
    │
    │ WebSocket frames
    ▼
Vue use_conv_ws.ts (onmessage)
    │
    │ StreamingMarkdown.vue
    ▼
浏览器 (实时渲染 Markdown，无需等待完整响应)
```

---

## 🚀 快速启动

### 环境要求

| 依赖 | 版本要求 |
|------|---------|
| **Python** | 3.12+ |
| **Node.js** | 22.12+（前端），推荐使用 `nvm` 或 `fnm` 管理 |
| **PostgreSQL** | 16+ |
| **Redis** | 7+ |
| **Git** | 任意稳定版本 |

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/AiTeach.git
cd AiTeach
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境（Python 3.12+）
python -m venv .venv

# 激活虚拟环境
# Linux / macOS:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 使用编辑器填入真实的数据库连接、Redis 地址和 API Key
```

### 3. 数据库初始化

```bash
# 创建 PostgreSQL 数据库（请先安装 PostgreSQL 16+）
psql -U postgres
CREATE DATABASE aiteach;
CREATE USER aiteach WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aiteach TO aiteach;
\q

# 执行数据库迁移
python manage.py migrate

# 创建超级管理员（可选，用于访问 Django Admin）
python manage.py createsuperuser
```

### 4. 启动后端服务

```bash
# 开发模式（Django runserver，热重载）
python manage.py runserver

# 或使用 Daphne ASGI（支持 WebSocket）
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 5. 启动 Celery Worker（异步任务，必选）

```bash
# 新开一个终端，进入 backend 目录
celery -A config worker -l info -P solo
# Windows 上使用 solo pool 避免平台兼容问题
# 生产环境使用 prefork 或 eventlet pool
```

### 6. 前端配置与启动

```bash
cd web

# 安装 Node 依赖（Node 22.12+）
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 VITE_BASE_URL（后端地址）和 API Key

# 启动开发服务器
npm run dev
# 访问 http://localhost:5173
```

### 7. 使用 Docker 部署（推荐生产环境）

```bash
cd backend

# 配置 .env.docker（参考 .env.example）
cp .env.example .env.docker
# 填入生产环境数据库、Redis、API Key

# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f
```

### 8. 前端生产构建

```bash
cd web
npm run build
# 构建产物输出到 web/dist/，可部署到 Nginx / CDN
```

---

## ⚙️ 环境变量完整参考

> **🔒 安全提示**：`.env` 文件已加入 `.gitignore`，切勿提交到版本库。

### 后端 `backend/.env`

```bash
# ==================== Django ====================
SECRET_KEY=your-32-char-random-secret-key      # Django 密钥，生产环境务必更换
DEBUG=False                                      # 生产环境必须 False
ALLOWED_HOSTS=your-domain.com,api.your-domain.com  # 允许的 HTTP Host 头

# ==================== PostgreSQL ====================
POSTGRES_DB=aiteach                              # 数据库名称
POSTGRES_USER=aiteach                            # 数据库用户名
POSTGRRES_PASSWORD=your_db_password               # 数据库密码
POSTGRES_HOST=localhost                           # 数据库主机
POSTGRES_PORT=5432                               # 数据库端口

# ==================== Redis ====================
REDIS_URL=redis://localhost:6379/0                # Redis 连接地址

# ==================== LLM ====================
LLM_PROVIDER=mimo                                # 当前使用的 LLM Provider
LLM_TEMPERATURE=0.7                              # LLM 温度参数 (0.0~1.0)

# MiMo (LLM_PROVIDER=mimo)
MIMO_API_KEY=your-mimo-api-key
MIMO_MODEL=mimo-v2.5-pro
MIMO_BASE_URL=https://api.xiaomimimo.com/v1

# MiniMax (LLM_PROVIDER=minimax)
MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_MODEL=MiniMax-M3
MINIMAX_BASE_URL=https://api.minimaxi.com/v1

# OpenAI (LLM_PROVIDER=openai)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic (LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-sonnet-4-6-20250514
ANTHROPIC_BASE_URL=https://api.anthropic.com

# ZhipuAI (LLM_PROVIDER=zhipu)
ZHIPU_API_KEY=your-zhipu-api-key
ZHIPU_MODEL=glm-5.2
ZHIPU_BASE_URL=https://yuanyuaicloud.cn/v1

# ==================== 视频生成服务 ====================
VIDEO_GEN_HOST=<YOUR_OPENMAIC_HOST:PORT>         # OpenMAIC 视频服务地址
```

### Dify Workflow `backend/dify_workflow/.env`

```bash
# B 站视频推荐工作流 API Key
BILI_PUSH_API_KEY=your-dify-api-key

# 知识库检索工作流 API Key
KB_SEARCH_API_KEY=your-dify-api-key

# 题库生成工作流 API Key
QUIZ_GENERATOR_API_KEY=your-dify-api-key
```

### 前端 `web/.env`

```bash
# 后端 API 地址（不要带协议，http.ts 自动拼接 http://）
VITE_BASE_URL=127.0.0.1:8000

# OpenMAIC 视频服务完整 URL（含协议）
VITE_OPENMAIC_URL=http://<YOUR_OPENMAIC_HOST:PORT>

# MiniMax API Key（书籍对话功能）
VITE_MINIMAX_API_KEY=your-minimax-api-key
```

> **⚠️ Docker 部署注意**：`docker-compose.yml` 中的 Redis 连接信息请替换为你的实际地址和密码，推荐使用环境变量注入或 Docker Secret 管理敏感信息。

---

## 📐 设计系统

项目拥有完整的设计系统，基于 **oklch 色彩空间**构建，保证跨设备色彩一致性：

- **主色调**：学院蓝 `oklch(52% 0.18 255)` — 传递信任与专注感
- **辅助色**：成长青 `oklch(60% 0.14 168)` — 代表学习进步
- **AI 强调色**：靛紫 `oklch(55% 0.20 280)` — AI 活动与生成状态
- **字体**：SF Pro Display（标题）、SF Pro Text（正文）、JetBrains Mono（代码标签）
- **光效**：`oklch(65% 0.22 280 / 0.25)` — AI 生成中的发光效果

详见完整规范文档：[web/DESIGN-x.ai.md](web/DESIGN-x.ai.md)

---

## 📊 数据模型概览

```
User (用户)
  ├── Subject (学科) — 多对多
  │    └── KnowledgeNode (知识节点)
  ├── Conversation (对话) — 一对多
  │    └── Message (消息)
  ├── LearningPlan (学习计划) — 一对多
  ├── QuizGenerationRecord (出题记录)
  ├── PracticeSession (练习会话)
  ├── ExamSession (考试会话)
  ├── VideoCourseRecord (视频课程)
  ├── StudySession (学习会话)
  └── ReadingSession (阅读会话)
       └── Book (书籍)
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

```bash
# 1. Fork 本仓库
# 2. 创建特性分支
git checkout -b feature/your-feature-name

# 3. 提交（请遵循提交规范）
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update README"

# 4. 推送到分支
git push origin feature/your-feature-name

# 5. 在 GitHub 上发起 Pull Request
```

**提交信息规范**：
- `feat:` — 新功能
- `fix:` — Bug 修复
- `docs:` — 文档更新
- `refactor:` — 代码重构
- `chore:` — 构建/工具变更

---

---

##  致谢

感谢以下开源项目和 AI 服务：

- [Django](https://www.djangoproject.com/) — Web 框架
- [Vue 3](https://vuejs.org/) — 前端响应式框架
- [LangChain](https://www.langchain.com/) — LLM 应用框架
- [Celery](https://docs.celeryq.dev/) — 异步任务队列
- [PrimeVue](https://primevue.org/) — Vue 3 UI 组件库
- [Three.js](https://threejs.org/) — 3D 渲染引擎
- [ECharts](https://echarts.apache.org/) — 数据可视化图表库
- [Vite](https://vitejs.dev/) — 下一代前端构建工具
- 所有为本项目提供 API 支持的 AI 服务提供商
