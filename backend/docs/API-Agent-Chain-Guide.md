# AI-Teach Agent & Chain 接口文档

> 本文档面向前后端开发者，说明系统中各类 Agent / Chain 的用途、调用方式、字段含义。

---

## 目录

1. [系统总览](#1-系统总览)
2. [Agent 类型速查](#2-agent-类型速查)
3. [Chain 类型速查](#3-chain-类型速查)
4. [核心流程：对话是怎么跑起来的](#4-核心流程对话是怎么跑起来的)
5. [REST API 接口](#5-rest-api-接口)
6. [WebSocket 实时通信协议](#6-websocket-实时通信协议)
7. [Agent 详解](#7-agent-详解)
8. [Chain 详解](#8-chain-详解)
9. [数据模型与字段说明](#9-数据模型与字段说明)
10. [附录：预定义学科与知识点](#10-附录预定义学科与知识点)

---

## 1. 系统总览

```
前端 ──HTTP/WS──▶ Django REST + Channels
                      │
                      ├──▶ Celery Task（异步执行 Agent / Chain）
                      │         │
                      │         ├──▶ LLM（MiMo / OpenAI / Anthropic）
                      │         ├──▶ Tools（读写 DB）
                      │         └──▶ Redis（状态 + 事件广播）
                      │
                      └──▶ WebSocket ──▶ 前端（流式 chunk）
```

**关键概念：**

| 概念 | 说明 |
|------|------|
| **Conversation** | 一次对话会话，绑定一个 `agent` 类型，决定走哪条 AI 处理链路 |
| **Agent** | 基于 LangGraph 的智能体，可调用工具（Tool），支持多轮对话 |
| **Chain** | 基于 LangChain 的固定流水线，无工具调用，输入→结构化输出 |
| **Message** | 对话中的消息，role 可以是 `user`、`assistant`、`tool` |
| **meta** | 消息的附加元信息（JSON），不同 Agent 会往里面写不同的运行时数据 |
| **LearningPlan** | 学习计划，由 Plan Agent / Plan Chain 创建和管理 |

---

## 2. Agent 类型速查

| agent 值 | 名称 | 用途 | 有无工具 | 流式 | thinking |
|-----------|------|------|----------|------|----------|
| `chat` | 聊天助手 | 通用问答，可查知识图谱和用户画像 | ✅ `get_knowledge_map`, `get_user_profile` | ✅ | ✅ |
| `profile` | 画像构建 | 通过对话收集学习者画像（目标、基础、认知风格等） | ✅ 内部 Evaluator 有工具 | ✅ | ❌ |
| `plan` | 学习计划 | 生成/编辑学习计划 | ✅ 编辑模式下有 CRUD 工具 | ✅ | ❌ |
| `practice` | 练习出题 | 目前走 chat agent 的相同链路（预留） | — | — | — |

---

## 3. Chain 类型速查

| Chain | 用途 | 触发方式 | 输出 |
|-------|------|----------|------|
| **Quiz Chain** | 根据知识图谱出题 | Celery 任务 `run_quiz_generation_task` | `QuizQuestion[]` |
| **Practice Chain** | 深度分析某道题 | Celery 任务 `run_practice_analysis_task` | `PracticeAnalysis` |
| **Plan Chain** | 生成学习计划 | Plan Agent 内部自动调用（生成模式） | `LearningPlan` 数据 |

---

## 4. 核心流程：对话是怎么跑起来的

### 4.1 发消息 → Agent 处理 → 流式返回

```
前端发消息（WS 或 HTTP POST）
    │
    ▼
_create_message_and_maybe_chat_sync()
    │
    ├── 1. 写入 user Message 到 DB
    ├── 2. 创建 assistant 占位 Message（content=""）
    ├── 3. Redis 写入初始状态（state=generating）
    └── 4. 投递 Celery 任务 run_conversation_agent_task
              │
              ├── agent="chat"    → _run_chat_agent_async()
              ├── agent="profile" → _run_profile_agent_async()
              └── agent="plan"    → _run_plan_agent_async()
                        │
                        ▼
              流式事件通过 Redis + Channel Layer 广播
                        │
                        ▼
              前端 WS 收到 chunk / tool_call / complete 等事件
```

### 4.2 两种消息发送方式

| 方式 | 端点 | 说明 |
|------|------|------|
| **WebSocket**（推荐） | `ws://host/ws/conversations/<conversation_id>/` | 双向通信，实时收到流式回复 |
| **HTTP POST** | `POST /api/conversations/<conversation_id>/messages/` | 同步返回 `ai_message_id`，需轮询或另开 WS 收流 |

---

## 5. REST API 接口

### 5.1 认证

| Method | 路径 | 说明 | 请求体 |
|--------|------|------|--------|
| POST | `/api/auth/register/` | 注册 | `{email, username, password, password_confirm}` |
| POST | `/api/auth/login/` | 登录 | `{email, password}` → 返回 `{access, refresh, user}` |
| POST | `/api/auth/refresh/` | 刷新 Token | `{refresh}` |

> 后续接口均需 JWT 认证：`Authorization: Bearer <access_token>`

### 5.2 学科

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/subjects/` | 获取所有预定义学科列表 |
| GET | `/api/subjects/mine/` | 当前用户已选学科（含 id，下游接口用） |
| POST | `/api/subjects/` | 选学科 `{name}` → 自动初始化知识图谱 |

**GET `/api/subjects/` 响应：**
```json
{
  "subjects": [
    {"code": "data_structure", "name": "数据结构"},
    {"code": "cybersecurity", "name": "网络安全"},
    ...
  ]
}
```

**GET `/api/subjects/mine/` 响应：**
```json
{
  "subjects": [
    {"id": 1, "name": "data_structure", "display_name": "数据结构", ...}
  ]
}
```

### 5.3 对话

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/conversations/?subject=<id>&agent=<type>` | 对话列表（支持过滤） |
| POST | `/api/conversations/` | 创建对话 |
| GET | `/api/conversations/<id>/` | 对话详情（含消息 + 实时 ai_state） |
| POST | `/api/conversations/<id>/messages/` | 在对话中发消息 |

**POST `/api/conversations/` 请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `subject_id` | int | ✅ | 学科 ID（来自 `/api/subjects/mine/`） |
| `title` | string | ❌ | 对话标题，默认 "新对话" |
| `agent` | string | ❌ | Agent 类型，默认 `"chat"`。可选值：`chat` / `profile` / `plan` / `practice` |

```json
// 请求
{"subject_id": 1, "title": "学习规划", "agent": "plan"}

// 响应 (201)
{
  "id": 42,
  "subject_id": 1,
  "title": "学习规划",
  "agent": "plan",
  "extra_prompt": null,
  "messages": [],
  "ai_state": "idle",          // 当前 AI 状态："idle" 或 "generating"
  "current_ai_message_id": null,
  "created_at": "2026-06-10T...",
  "updated_at": "2026-06-10T..."
}
```

**POST `/api/conversations/<id>/messages/` 请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `content` | string | ✅ | 用户消息文本 |
| `role` | string | ❌ | 默认 `"user"` |
| `meta` | object | ❌ | 附加元信息，不同 Agent 读取不同字段（见下文） |

```json
// 请求
{"content": "帮我制定学习计划", "meta": {}}

// 响应 (201)
{
  "user_message": {
    "id": 100,
    "role": "user",
    "content": "帮我制定学习计划",
    "meta": {},
    "created_at": "..."
  },
  "ai_message_id": 101,     // AI 占位消息 ID，WS 中用此 ID 追踪流式输出
  "ai_state": "generating"   // AI 正在生成
}
```

### 5.4 消息

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/messages/?conversation_id=<id>` | 获取对话消息列表 |

### 5.5 知识节点（只读）

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/knowledge-nodes/?subject_id=<id>` | 获取知识点列表 |

```json
// 响应
[
  {
    "id": 1,
    "subject_id": 1,
    "node_id": "DS01",            // 知识点编号
    "name": "链表",                // 知识点名称
    "mastery": 65,                 // 掌握程度 0-100
    "evidence_count": 3,           // 评估次数
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### 5.6 用户画像

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/profile/?subject_id=<id>` | 获取画像 |
| PATCH | `/api/profile/?subject_id=<id>` | 更新画像 |

```json
// GET 响应
{
  "id": 1,
  "subject": {"id": 1, "name": "data_structure", "display_name": "数据结构"},
  "course": "数据结构基础",
  "knowledge_base": 60,          // 知识基础 0-100
  "cognitive_style": 70,         // 认知风格 0-100
  "learning_goal_score": 80,     // 学习目标 0-100
  "available_time": 50,          // 可用时间 0-100
  "common_mistakes": ["DS03"],   // 易错知识点 node_id 列表
  "interest_direction": ["算法优化"],
  "created_at": "...",
  "updated_at": "..."
}
```

### 5.7 学习计划

| Method | 路径 | 说明 |
|--------|------|------|
| GET | `/api/plans/?subject=<id>&state=<s>&target_agent=<a>` | 计划列表（支持过滤） |
| GET | `/api/plans/<id>/` | 计划详情 |
| PATCH | `/api/plans/<id>/` | 更新计划 |

```json
// GET 响应
[
  {
    "id": 1,
    "subject_id": 1,
    "conversation_id": 42,
    "subject_name": "data_structure",
    "subject_display": "数据结构",
    "target_agent": "practice",     // 计划推荐的 agent："chat" / "profile" / "practice"
    "difficulty": "medium",         // 难度："low" / "medium" / "high"
    "memory": {                     // 计划记忆（AI 生成的结构化信息）
      "summary": "针对链表薄弱环节进行练习",
      "reason": "链表掌握度仅 45%，低于平均水平",
      "next_step": "完成链表专项练习",
      "focus_nodes": ["DS01", "DS02"],
      "profile_complete": true
    },
    "create_time": "...",
    "success_time": null,
    "state": "pending",             // "pending" / "running" / "success" / "failed"
    "updated_at": "..."
  }
]
```

---

## 6. WebSocket 实时通信协议

### 6.1 连接

```
ws://<host>/ws/conversations/<conversation_id>/
```

连接成功后，服务端自动发送：
1. `history` — 最近消息
2. `state` — 当前 AI 状态
3. `resume` — 如果 AI 正在生成，返回已有内容（断线重连用）

### 6.2 客户端 → 服务端

```json
{
  "type": "message",
  "content": "你好，帮我看看链表知识",
  "role": "user",
  "meta": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | ✅ | 固定为 `"message"` |
| `content` | string | ✅ | 消息文本 |
| `role` | string | ❌ | 默认 `"user"` |
| `meta` | object | ❌ | 附加元信息 |

### 6.3 服务端 → 客户端 事件列表

| 事件 type | 何时发送 | 携带字段 | 说明 |
|-----------|----------|----------|------|
| `accepted` | 消息被接收 | `conversation_id`, `user_message`, `ai_message_id`, `ai_state` | 确认消息已收到，AI 开始处理 |
| `state` | 连接时 | `conversation_id`, `ai_state`, `current_ai_message_id` | 当前对话的 AI 状态快照 |
| `history` | 连接时 | `conversation_id`, `messages[]` | 最近 6 条消息 |
| `resume` | 连接时 AI 正在生成 | `conversation_id`, `ai_message_id`, `content` | 断线重连，返回已生成的部分内容 |
| `start` | AI 开始生成 | `ai_message_id` | 标记生成开始 |
| `thinking_start` | 思考开始 | `ai_message_id` | 仅 chat agent 有 thinking 能力 |
| `thinking_chunk` | 思考过程片段 | `ai_message_id`, `content` | 推理/思考内容片段 |
| `thinking_end` | 思考结束 | `ai_message_id` | 思考阶段完成 |
| `chunk` | 正文流式片段 | `ai_message_id`, `content` | AI 回复的增量文本 |
| `tool_call` | Agent 调用工具 | `ai_message_id`, `tool_name`, `tool_args`, `tool_call_id` | Agent 决定调用某个工具 |
| `tool_result` | 工具返回结果 | `ai_message_id`, `tool_name`, `tool_output`, `tool_call_id` | 工具执行完毕 |
| `end` | AI 生成结束 | `ai_message_id` | 标记生成结束 |
| `complete` | 最终完成 | `ai_message_id`, `content`, `meta` | 包含完整内容和元信息 |
| `error` | 出错 | `ai_message_id`, `message` | 错误信息 |

### 6.4 前端处理流程建议

```
连接 WS → 收到 history → 渲染历史消息
         → 收到 state   → 如果 ai_state="generating"，显示加载态
         → 收到 resume  → 恢复断线前的生成内容

发消息   → 收到 accepted → 显示用户消息 + AI 加载动画
         → 收到 thinking_start/chunk/end → 渲染思考过程（可折叠）
         → 收到 chunk    → 逐字追加 AI 回复
         → 收到 tool_call → 显示工具调用卡片（可选）
         → 收到 tool_result → 显示工具结果（可选）
         → 收到 complete → 标记完成，渲染最终 meta 信息
         → 收到 error    → 显示错误提示
```

---

## 7. Agent 详解

### 7.1 Chat Agent（`agent="chat"`）

**用途：** 通用问答助手（"小AI"），回答学习相关问题。能查询知识图谱和用户画像来提供数据驱动的回答。

**可用工具：**
| 工具名 | 说明 |
|--------|------|
| `get_knowledge_map` | 获取用户在该学科的知识星图（所有知识点 + 掌握度） |
| `get_user_profile` | 获取用户的学习画像快照 |

**meta 字段（complete 事件中）：**
```json
{"agent": "chat"}
```

**特殊能力：** 支持 thinking 流式输出，前端可展示 AI 的"推理过程"。

**典型交互：**
```
用户: "我的链表掌握得怎么样？"
AI:   [thinking_start] → [thinking_chunk: "需要查询知识图谱..."]
      [thinking_end]
      [tool_call: get_knowledge_map]
      [tool_result: {DS01: 45, DS02: 60, ...}]
      [chunk: "根据知识图谱，你的链表掌握度为 45%..."]
      [complete]
```

### 7.2 Profile Agent（`agent="profile"`）

**用途：** 通过多轮对话构建学习者画像。后台有两个协作组件：

1. **Profile Evaluator**（后台运行）：每轮对话后分析用户回答，更新画像，决定下一个问题
2. **Profile Conversation Agent**（面向用户）：根据 Evaluator 的指引生成自然语言回复

**对话轮次：** 最多 15 轮（`MAX_ROUNDS=15`），画像完整后会提示用户。

**meta 字段（complete 事件中）：**
```json
{
  "agent": "profile",
  "profile": {                          // 当前画像快照
    "course": "数据结构基础",
    "knowledge_base": 60,
    "cognitive_style": 70,
    "learning_goal_score": 80,
    "available_time": 50,
    "common_mistakes": [],
    "interest_direction": ["算法"]
  },
  "next_question": "你每天大概有多少时间学习？",
  "is_complete": false,                 // 画像是否已完整
  "saved": true,                        // 本轮是否更新了画像
  "round": 3,                           // 当前第几轮
  "max_rounds": 15,
  "subject_id": 1,
  "completion_options": []              // 画像完成后可选操作
}
```

**画像完整性判断：** 以下字段全部有值时视为完整：
- `learning_goal_score`（学习目标）
- `knowledge_base`（知识基础）
- `cognitive_style`（认知风格）
- `available_time`（可用时间）
- `interest_direction`（兴趣方向）

**前端建议：**
- 根据 `meta.is_complete` 判断是否显示"画像已完成"提示
- 根据 `meta.round` / `meta.max_rounds` 显示进度
- `meta.completion_options` 非空时可显示"继续聊天"/"下一步"按钮

### 7.3 Plan Agent（`agent="plan"`）

**用途：** 管理学习计划。支持两种模式：

#### 模式 1：生成模式（默认）

当消息 `meta` 中没有 `selected_plan_ids` 时，自动生成新学习计划。

内部流程：
1. 获取用户画像 + 知识图谱
2. 调用 **Plan Chain** 生成结构化计划
3. 保存 `LearningPlan` 到数据库
4. 流式输出计划的自然语言摘要

**请求示例：**
```json
{"content": "帮我制定一个学习计划", "meta": {}}
```

**meta 字段（complete 事件中）：**
```json
{
  "agent": "plan",
  "plan": {
    "id": 1,
    "subject_id": 1,
    "conversation_id": 42,
    "target_agent": "practice",    // 计划推荐的下一步 agent
    "difficulty": "medium",
    "memory": {
      "summary": "...",
      "reason": "...",
      "next_step": "...",
      "focus_nodes": ["DS01"],
      "profile_complete": true
    },
    "create_time": "...",
    "success_time": null,
    "state": "pending"
  },
  "saved": true,
  "subject_id": 1,
  "mode": "generate"
}
```

**Plan Chain 决策逻辑：**

| 条件 | target_agent | difficulty | 说明 |
|------|-------------|------------|------|
| 画像不完整 | `profile` | `low` | 先去完善画像 |
| 画像完整 + 最弱知识点 < 75 | `practice` | 按薄弱程度调整 | 需要练习 |
| 画像完整 + 所有知识点 ≥ 75 | `chat` | — | 水平较高，可以深入探讨 |

#### 模式 2：编辑模式

当消息 `meta` 中有 `selected_plan_ids` 时，可以读写已有计划。

**请求示例：**
```json
{
  "content": "把计划1的难度改成高",
  "meta": {"selected_plan_ids": [1]}
}
```

**可用工具（编辑模式）：**
| 工具名 | 说明 |
|--------|------|
| `get_selected_plans` | 获取指定 ID 的计划详情 |
| `list_user_plans` | 列出所有计划 |
| `update_plan` | 修改计划字段 |
| `create_plan` | 创建新计划 |
| `delete_plan` | 删除计划 |

**meta 字段（complete 事件中）：**
```json
{
  "agent": "plan",
  "subject_id": 1,
  "mode": "edit",
  "plan_ids": [1]
}
```

---

## 8. Chain 详解

Chain 是独立的异步任务，不通过对话 WS 触发，而是通过 Celery 任务调用，结果存在 Redis 中。

### 8.1 Quiz Chain（出题）

**触发方式：** Celery 任务 `run_quiz_generation_task`

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `subject_id` | int | ✅ | 学科 ID |
| `extra_prompt` | string | ❌ | 额外出题要求，如 "重点考链表" |
| `count` | int | ❌ | 题目数量。为 null 时自动决定：优先从 prompt 提取，否则随机 3-5 |

**Redis 状态：**
- `quiz:<task_id>:state` → `"generating"` / `"complete"` / `"error:<msg>"`
- `quiz:<task_id>:result` → JSON 题目列表（complete 时写入）
- TTL：3600 秒（1 小时）

**输出 Schema — `QuizQuestion`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `question_type` | string | `"choice"`（选择题）或 `"short_answer"`（简答题） |
| `difficulty` | string | `"easy"` / `"medium"` / `"hard"` |
| `knowledge_node_id` | string | 目标知识点编号，如 `"DS01"` |
| `knowledge_node_name` | string | 目标知识点名称，如 `"链表"` |
| `question_text` | string | 题目正文 |
| `options` | string[] \| null | 选择题选项（通常 4 个），简答题为 null |
| `correct_answer` | string | 正确答案。选择题填选项字母（如 `"A"`），简答题填参考答案 |
| `explanation` | string | 答案解析 |

**难度自动选择逻辑（基于知识点掌握度）：**

| 掌握度 mastery | difficulty | question_type |
|---------------|------------|---------------|
| < 50 | `easy` | `choice` |
| 50 ~ 74 | `medium` | `choice` |
| ≥ 75 | `hard` | `short_answer` |

**输出示例：**
```json
[
  {
    "question_type": "choice",
    "difficulty": "medium",
    "knowledge_node_id": "DS01",
    "knowledge_node_name": "链表",
    "question_text": "单链表中，删除节点 p 的后继节点的正确操作是？",
    "options": [
      "A. p.next = p.next.next",
      "B. p = p.next",
      "C. p.next = p",
      "D. p.prev = p.next"
    ],
    "correct_answer": "A",
    "explanation": "删除 p 的后继节点需要让 p 的 next 指针跳过后继..."
  }
]
```

### 8.2 Practice Chain（题目分析）

**触发方式：** Celery 任务 `run_practice_analysis_task`

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `quiz_task_id` | string | ✅ | Quiz Chain 的 task_id，用于从 Redis 读取题目 |
| `question_index` | int | ❌ | 分析第几题，默认 `0` |
| `mode` | string | ❌ | `"with_answer"` 或 `"without_answer"`，默认 `"with_answer"` |
| `user_answer` | string | ❌ | 用户的回答（仅 `with_answer` 模式使用） |
| `subject_display` | string | ❌ | 学科显示名，如 "数据结构" |
| `subject_code` | string | ❌ | 学科代码，如 "data_structure" |

**两种模式说明：**

| 模式 | 用途 | 行为 |
|------|------|------|
| `with_answer` | 做题后查看解析 | 讲解正确答案，分析用户回答对错，指出误解 |
| `without_answer` | 做题时求助提示 | 苏格拉底式引导，给思路和思维框架，不泄露答案 |

**Redis 状态：**
- `practice:<task_id>:state` → `"generating"` / `"complete"` / `"error:<msg>"`
- `practice:<task_id>:result` → JSON 分析结果
- TTL：3600 秒

**输出 Schema — `PracticeAnalysis`：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `mode` | string | `"with_answer"` 或 `"without_answer"` |
| `analysis` | string | 分析正文（面向用户的详细讲解或引导） |
| `key_knowledge_points` | string[] | 涉及的核心知识点列表 |
| `difficulty_assessment` | string | 难度评估：`"easy"` / `"medium"` / `"hard"` |

### 8.3 Plan Chain（计划生成）

**触发方式：** 内部调用（Plan Agent 生成模式时自动触发，不直接暴露 API）

**输入：** `subject_display`, `subject_code`, `history_messages`, `profile_summary`, `knowledge_map`

**输出（保存为 `LearningPlan.memory`）：**

```json
{
  "target_agent": "practice",
  "difficulty": "medium",
  "state": "pending",
  "memory": {
    "summary": "针对链表薄弱环节进行专项练习",
    "reason": "链表掌握度 45%，是当前最薄弱的知识点",
    "next_step": "完成 5 道链表相关练习题",
    "focus_nodes": ["DS01", "DS02"],
    "profile_complete": true
  }
}
```

---

## 9. 数据模型与字段说明

### 9.1 Conversation（对话）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 对话 ID |
| `subject_id` | int | 所属学科 |
| `title` | string | 对话标题 |
| `agent` | string | Agent 类型：`chat` / `profile` / `practice` / `plan` |
| `extra_prompt` | string \| null | 注入到系统提示词的额外指令（用于定制 Agent 行为） |
| `ai_state` | string | 运行时字段：`"idle"` / `"generating"` |
| `current_ai_message_id` | int \| null | 运行时字段：当前正在生成的 AI 消息 ID |

### 9.2 Message（消息）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 消息 ID |
| `role` | string | `"user"` / `"assistant"` / `"tool"` |
| `content` | string | 消息文本 |
| `meta` | object | 附加元信息（不同 Agent 写不同内容，见各 Agent 详解） |
| `created_at` | datetime | 创建时间 |

### 9.3 LearningPlan（学习计划）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 计划 ID |
| `subject_id` | int | 所属学科 |
| `conversation_id` | int \| null | 来源对话 |
| `subject_name` | string | 学科代码（如 `data_structure`） |
| `subject_display` | string | 学科显示名（如 `数据结构`） |
| `target_agent` | string | 推荐 agent：`chat` / `profile` / `practice` |
| `difficulty` | string | 难度：`low` / `medium` / `high` |
| `memory` | object | AI 生成的结构化计划信息（summary, reason, next_step, focus_nodes） |
| `state` | string | 状态：`pending` / `running` / `success` / `failed` |
| `create_time` | datetime | 创建时间 |
| `success_time` | datetime \| null | 完成时间 |

### 9.4 KnowledgeNode（知识节点）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 记录 ID |
| `subject_id` | int | 所属学科 |
| `node_id` | string | 知识点编号（如 `DS01`） |
| `name` | string | 知识点名称 |
| `mastery` | int | 掌握程度 0-100 |
| `evidence_count` | int | 评估证据条数 |

> ⚠️ 知识节点只读（HTTP GET），修改只能由 Agent 工具 `assess_and_update_knowledge_score` 完成。

### 9.5 UserProfile（用户画像）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 画像 ID |
| `subject` | object | 所属学科 |
| `course` | string | 课程名 |
| `knowledge_base` | int | 知识基础 0-100 |
| `cognitive_style` | int | 认知风格 0-100 |
| `learning_goal_score` | int | 学习目标 0-100 |
| `available_time` | int | 可用时间 0-100 |
| `common_mistakes` | string[] | 易错知识点 node_id 列表 |
| `interest_direction` | string[] | 兴趣方向列表 |

---

## 10. 附录：预定义学科与知识点

### 学科列表

| 代码 (code/name) | 显示名 |
|-------------------|--------|
| `data_structure` | 数据结构 |
| `cybersecurity` | 网络安全 |
| `iot` | 物联网技术 |
| `electrical_automation` | 电气自动化 |
| `mechanical_design` | 机械设计 |
| `advanced_math` | 高等数学 |
| `artificial_intelligence` | 人工智能 |

### 消息 meta 字段速查

| 场景 | meta 中的关键 | 说明 |
|------|--------------|------|
| 发消息给 Plan Agent（编辑模式） | `meta.selected_plan_ids` | `int[]` — 要编辑的计划 ID 列表 |
| Profile Agent 回复完成 | `meta.is_complete` | `bool` — 画像是否完整 |
| Profile Agent 回复完成 | `meta.round` | `int` — 当前轮次 |
| Profile Agent 回复完成 | `meta.profile` | `object` — 画像快照 |
| Profile Agent 回复完成 | `meta.completion_options` | `string[]` — 完成后操作选项 |
| Plan Agent 回复完成（生成模式） | `meta.plan` | `object` — 新建的计划详情 |
| Plan Agent 回复完成 | `meta.mode` | `"generate"` 或 `"edit"` |
| Chat Agent 回复完成 | `meta.agent` | `"chat"` |

---

> **最后更新：** 2026-06-10
