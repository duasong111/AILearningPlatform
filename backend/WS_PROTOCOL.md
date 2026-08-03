# WebSocket 对接文档

本文档描述当前项目中前端与后端的会话级 WebSocket 协议，覆盖：

- 通用概念
- 接入前置 HTTP 接口
- WebSocket 连接方式
- 收发消息格式
- 通用事件字段
- chat / profile / practice / plan 四类 agent 的差异

适用范围：当前后端实现的统一会话流接口。

## 1. 通用概念

### 1.1 会话（conversation）

- 一个会话对应一个 `conversation_id`
- 一个会话固定绑定一个 `agent`
  - `chat`: 普通聊天助手
  - `profile`: 用户画像构建
  - `practice`: 练习出题
  - `plan`: 学习计划构建
- 前端与后端的实时交互，统一通过会话级 WebSocket 完成

### 1.2 消息（message）

- 用户每发一条消息，后端会创建：
  - 1 条用户消息 `user_message`
  - 1 条 AI 占位消息 `ai_message_id`
- 后续所有流式事件，都围绕这条 `ai_message_id` 展开

### 1.3 AI 状态

- `idle`: 当前会话没有正在生成的 AI 回复
- `generating`: 当前会话存在一条 AI 回复正在生成

### 1.4 最近历史

- WebSocket 建连成功后，后端会先回放最近最多 3 轮对话
- 当前实现为最多返回最近 6 条有效消息：
  - 包含 `user`
  - 包含有内容的 `assistant`
  - 不包含 `tool`

## 2. 前置 HTTP 接口

虽然发送消息现在主流程走 WebSocket，但前端通常仍需要这些 HTTP 接口来创建和查询会话。

### 2.1 创建会话

`POST /api/conversations/`

请求体：

```json
{
  "subject_id": 1,
  "title": "数据结构对话",
  "agent": "chat"
}
```

或：

```json
{
  "subject_id": 1,
  "title": "数据结构画像",
  "agent": "profile"
}
```

或：

```json
{
  "subject_id": 1,
  "title": "数据结构练习",
  "agent": "practice"
}
```

或：

```json
{
  "subject_id": 1,
  "title": "数据结构学习计划",
  "agent": "plan"
}
```

### 2.2 查询会话列表

`GET /api/conversations/`

支持查询参数：

- `subject`
- `agent`

示例：

- `GET /api/conversations/?agent=chat`
- `GET /api/conversations/?agent=profile`
- `GET /api/conversations/?agent=plan`
- `GET /api/conversations/?subject=1&agent=chat`

## 3. WebSocket 连接方式

### 3.1 连接地址

```text
ws://localhost:8000/ws/conversations/<conversation_id>/?token=<jwt>
```

生产环境改成对应域名即可。

### 3.2 鉴权方式

- 使用 query string 里的 `token`
- 例如：

```text
ws://localhost:8000/ws/conversations/58/?token=eyJ...
```

### 3.3 连接失败语义

- `4401`: 未认证
- `4403`: 会话不属于当前用户或无权限

## 4. 前端发消息

前端向 WebSocket 发送：

```json
{
  "type": "message",
  "content": "根据我的画像和知识图谱，我现在应该优先学什么？",
  "role": "user",
  "meta": {
    "scene": "exam_mode",
    "selected_node_id": "DS03"
  }
}
```

说明：

- `type` 当前固定为 `message`
- `content` 必填
- `role` 当前前端应固定传 `user`
- `meta` 可选，必须是对象；用于前端把当前页面状态、选中项、模式等隐藏上下文同步给 AI
- `meta` 会存入用户消息，并在后端组装提示时作为“隐藏上下文”传给 AI，但不应直接展示给终端用户

### 4.1 plan agent 发起示例

如果当前会话的 `agent = "plan"`，前端发消息方式与其他 agent 完全一致，只是建议文案改成“生成学习计划”类请求。

说明：

- `meta.selected_plan_ids` 是 `plan` agent 是否进入编辑模式的唯一控制字段
- 当 `meta.selected_plan_ids` 存在且非空时：本轮按“编辑已有计划”处理
- 当 `meta.selected_plan_ids` 不存在或为空时：本轮按“新建计划”处理
- `plan` agent 不再通过 `extra_prompt` 或自然语言解析“命中哪些计划”

示例流程：

1. 先创建会话：

```json
{
  "subject_id": 1,
  "title": "我的学习计划",
  "agent": "plan"
}
```

2. 建立 WS 连接：

```text
ws://localhost:8000/ws/conversations/88/?token=<jwt>
```

3. 发送消息：

```json
{
  "type": "message",
  "content": "请根据我当前的画像和知识星图，帮我生成一份学习计划",
  "role": "user",
  "meta": {
    "scene": "plan_builder",
    "entry": "dashboard"
  }
}
```

4. 正常情况下会依次收到：

- `accepted`
- `start`
- 若干 `chunk`
- `end`
- `complete`

### 4.2 plan agent 编辑已有计划示例

如果用户在前端选中了计划 2、3、4，需要编辑这些计划，应直接通过 `meta.selected_plan_ids` 传给后端：

```json
{
  "type": "message",
  "content": "把这几个计划的难度都改成高，并把下一个步骤收敛成一周内可完成",
  "role": "user",
  "meta": {
    "scene": "plan_editor",
    "selected_plan_ids": [2, 3, 4]
  }
}
```

此时 `plan` agent 会进入编辑模式，并优先围绕 2、3、4 号计划调用工具。

## 5. 后端事件总览

后端会向前端推送这些事件：

- `history`
- `state`
- `accepted`
- `resume`
- `start`
- `thinking_start`
- `thinking_chunk`
- `thinking_end`
- `tool_call`
- `tool_result`
- `chunk`
- `end`
- `complete`
- `error`

不是每种 agent 都会发全量事件，详见后文。

## 6. 通用事件协议

### 6.1 history

连接建立后立即返回最近最多 3 轮对话。

```json
{
  "type": "history",
  "conversation_id": 58,
  "messages": [
    {
      "id": 101,
      "role": "user",
      "content": "我想准备数据结构面试",
      "meta": {
        "scene": "interview_prep"
      },
      "created_at": "2026-06-08T00:00:00Z"
    },
    {
      "id": 102,
      "role": "assistant",
      "content": "可以，先说说你目前掌握到什么程度。",
      "created_at": "2026-06-08T00:00:05Z"
    }
  ]
}
```

字段说明：

- `messages`: 最近有效消息列表，按时间正序

### 6.2 state

连接建立后返回当前会话运行态。

```json
{
  "type": "state",
  "conversation_id": 58,
  "ai_state": "idle",
  "current_ai_message_id": null
}
```

或：

```json
{
  "type": "state",
  "conversation_id": 58,
  "ai_state": "generating",
  "current_ai_message_id": 443
}
```

字段说明：

- `ai_state`: `idle | generating`
- `current_ai_message_id`: 当前正在生成的 AI 消息 id，没有则为 `null`

### 6.3 accepted

前端发送一条用户消息后，后端先确认已接收并已创建 AI 占位消息。

```json
{
  "type": "accepted",
  "conversation_id": 58,
  "user_message": {
    "id": 440,
    "role": "user",
    "content": "根据我的画像和知识图谱，我现在应该优先学什么？",
    "meta": {
      "scene": "exam_mode",
      "selected_node_id": "DS03"
    },
    "created_at": "2026-06-08T00:10:00Z"
  },
  "ai_message_id": 441,
  "ai_state": "generating"
}
```

字段说明：

- `user_message`: 刚写入数据库的用户消息
- `ai_message_id`: 本轮 AI 回复对应的消息 id
- `ai_state`: 当前固定为 `generating`
- `user_message.meta`: 用户随消息携带的隐藏上下文

### 6.4 resume

当会话已有一条正在生成的 AI 回复时，建连后会回放已生成内容。

```json
{
  "type": "resume",
  "conversation_id": 58,
  "ai_message_id": 441,
  "content": "根据你当前的学习情况，"
}
```

字段说明：

- `content`: 当前已累计生成的文本，不是增量

前端建议：

- 建连收到 `resume` 时，直接将该条 AI 消息内容替换为 `content`

### 6.5 chunk

AI 回复的增量文本。

```json
{
  "type": "chunk",
  "conversation_id": 58,
  "ai_message_id": 441,
  "content": "建议先补二叉树和递归基础。"
}
```

字段说明：

- `content`: 增量文本，需要前端 append 到当前 AI 消息尾部

### 6.6 start

任意 agent 开始处理本轮回复时触发。

```json
{
  "type": "start",
  "ai_message_id": 441
}
```

前端建议：

- 将这条 AI 消息标记为“开始生成”
- 可用于显示“AI 正在思考/处理中”

### 6.7 thinking_start

chat agent 的 thinking 阶段开始。

```json
{
  "type": "thinking_start",
  "ai_message_id": 441
}
```

### 6.8 thinking_chunk

chat agent 的 thinking 增量内容。

```json
{
  "type": "thinking_chunk",
  "ai_message_id": 441,
  "content": "用户在问基于当前数据的优先学习路径，先读取知识星图。"
}
```

前端建议：

- thinking 内容单独展示，不要 append 到正式回答文本

### 6.9 thinking_end

chat agent 的 thinking 阶段结束。

```json
{
  "type": "thinking_end",
  "ai_message_id": 441
}
```

### 6.10 end

任意 agent 完成内部处理流程，但还未发送最终 `complete` 事件。

```json
{
  "type": "end",
  "ai_message_id": 441
}
```

### 6.11 complete

本轮 AI 回复结束。

```json
{
  "type": "complete",
  "conversation_id": 58,
  "ai_message_id": 441,
  "content": "根据你当前的学习情况，建议先补二叉树和递归基础。",
  "meta": {
    "agent": "chat"
  }
}
```

字段说明：

- `content`: 本轮 AI 的完整最终文本
- `meta`: agent 相关扩展字段

前端建议：

- 用 `complete.content` 覆盖当前这条 AI 消息最终内容
- 同时将该消息标记为已完成

### 6.12 error

当前 AI 回复失败。

```json
{
  "type": "error",
  "conversation_id": 58,
  "ai_message_id": 441,
  "message": "stale"
}
```

字段说明：

- `message`: 错误信息，建议前端作为 toast 或消息状态展示

## 7. chat agent 专有事件

当前 `chat` agent 支持工具调用过程可视化。

### 7.1 tool_call

开始调用工具时触发。

```json
{
  "type": "tool_call",
  "ai_message_id": 441,
  "tool_name": "get_knowledge_map",
  "tool_args": {
    "subject_code": "data_structure"
  },
  "tool_call_id": "run_123"
}
```

### 7.2 tool_result

工具返回时触发。

```json
{
  "type": "tool_result",
  "ai_message_id": 441,
  "tool_name": "get_user_profile",
  "tool_output": "{\"subject_code\":\"data_structure\",\"has_profile\":true,\"profile\":{...}}",
  "tool_call_id": "run_123"
}
```

字段说明：

- `tool_name`: 工具名
- `tool_args`: 工具入参
- `tool_output`: 工具原始返回值，当前为字符串，通常是 JSON 字符串
- `tool_call_id`: 工具调用链路 id，可用于前端做 start/end 对应

### 7.3 chat complete.meta

`chat` agent 的 `complete.meta` 当前结构：

```json
{
  "agent": "chat"
}
```

后续如果扩展更多 chat 元信息，会继续放在这里。

### 7.4 chat 当前可用工具

当前 chat agent 已接入只读工具：

- `get_knowledge_map`
- `get_user_profile`

### 7.5 chat 独有事件补充

chat agent 额外会发送这些过程事件：

- `start`
- `thinking_start`
- `thinking_chunk`
- `thinking_end`
- `tool_call`
- `tool_result`
- `end`

说明：

- chat 目前不会直接调用会写库的知识点评分工具
- 因此 chat 场景下的工具调用是“查询型”而不是“修改型”

## 8. practice agent 专有字段

`practice` agent 会根据当前知识星图中的掌握度出不同难度的题，并在用户作答后直接调用更新工具。

### 8.1 practice 行为特点

- 每轮先读取当前知识星图
- 按知识点掌握度选择题目难度：
  - `mastery < 35`：简单题
  - `35 <= mastery < 70`：中等题
  - `mastery >= 70`：较难题
- 用户回答后会直接调用：
  - `assess_and_update_knowledge_score`
- 对用户的回复通常包含两部分：
  - 简短反馈
  - 下一道题

### 8.2 practice 专有事件

practice agent 当前会发送这些过程事件：

- `start`
- `tool_call`
- `tool_result`
- `chunk`
- `end`

practice 不发送 thinking 事件。

### 8.3 practice complete.meta

`practice` agent 的 `complete.meta` 当前结构：

```json
{
  "agent": "practice",
  "updated": true,
  "updated_node_id": "DS03",
  "update_result": "OK: 栈 20->35 (Δ+15, adaptive_max=25) | round=2 evidence#1 | 用户能正确解释 LIFO"
}
```

## 9. profile agent 专有字段

`profile` agent 当前没有向前端暴露 `tool_call/tool_result` 事件，也不会推送 thinking 相关事件，但会发送 `start` 和 `end`。

它的特有信息主要体现在 `complete.meta` 中。

### 9.1 profile 过程事件

profile agent 当前会发送这些过程事件：

- `start`
- `chunk`
- `end`

### 9.2 profile complete.meta

```json
{
  "agent": "profile",
  "profile": {
    "learning_goal": {
      "goal": "准备数据结构面试",
      "priority": 1,
      "target_date": "",
      "difficulty_level": "intermediate"
    },
    "knowledge_base": {
      "level": 45,
      "strong_areas": [],
      "weak_areas": ["二叉树"],
      "recommended_courses": []
    },
    "cognitive_style": {
      "style_type": "analytical",
      "description": "",
      "score": 60
    },
    "available_time": 6,
    "interest_direction": ["算法题"],
    "common_mistakes": ["递归思路不清"],
    "course": ""
  },
  "next_question": "你之前做题时，二叉树主要卡在遍历还是递归？",
  "is_complete": false,
  "saved": true,
  "round": 1,
  "max_rounds": 15,
  "subject_id": 1,
  "completion_options": []
}
```

字段说明：

- `profile`: 当前最新画像快照
- `next_question`: 下一轮建议追问；如果画像已完成，通常为 `null`
- `is_complete`: 画像采集是否已完成
- `saved`: 当前画像是否已写入数据库
- `round`: 当前轮次
- `max_rounds`: 最大轮次
- `subject_id`: 当前学科 id
- `completion_options`: 当 `is_complete=true` 时，当前固定返回 `["continue_chat", "next_step"]`

### 9.3 profile 完成时的前端处理建议

- 当 `complete.meta.is_complete = true` 时，表示当前画像采集阶段已经完成
- 此时后端不会再继续追问新的画像问题
- 前端可以基于 `completion_options` 给用户展示两个动作：
  - `continue_chat`：继续聊天
  - `next_step`：直接进入下一步

### 9.4 plan agent 专有字段

`plan` agent 用于根据当前对话、画像和知识星图生成一条结构化学习计划。

模式判断规则：

- 当前用户消息的 `meta.selected_plan_ids` 存在且非空：进入编辑模式
- 当前用户消息的 `meta.selected_plan_ids` 不存在或为空：进入新建模式
- `scene` 等其他 `meta` 字段只是补充场景上下文，不参与编辑/新建判断

#### 9.4.1 plan 过程事件

- `start`
- `chunk`
- `end`

plan 当前不推送 thinking，也不向前端暴露 tool_call/tool_result。

#### 9.4.2 plan complete.meta

```json
{
  "agent": "plan",
  "plan": {
    "id": 12,
    "subject_id": 1,
    "conversation_id": 88,
    "target_agent": "practice",
    "difficulty": "medium",
    "memory": {
      "summary": "先通过练习巩固当前薄弱点。",
      "reason": "画像已基本完整，且知识星图显示二叉树、递归掌握度较低。",
      "next_step": "进入练习 agent，先做一轮围绕薄弱点的题目。",
      "focus_nodes": ["二叉树", "递归"],
      "profile_complete": true,
      "subject_code": "data_structure",
      "subject_display": "数据结构"
    },
    "create_time": "2026-06-08T00:20:00Z",
    "success_time": null,
    "state": "pending"
  },
  "saved": true,
  "subject_id": 1
}
```

字段说明：

- `plan`: 本轮新生成并已保存的学习计划对象
- `plan.target_agent`: 推荐用户下一步进入的 agent
- `plan.difficulty`: 计划难度，固定为 `low | medium | high`
- `plan.memory`: 给后续 agent 或前端使用的计划上下文
- `saved`: 当前计划是否已写入数据库

#### 9.4.3 plan agent 完整 WS 示例

前端发送：

```json
{
  "type": "message",
  "content": "请根据我当前的画像和知识星图，帮我生成一份学习计划",
  "role": "user"
}
```

后端可能返回：

```json
{
  "type": "accepted",
  "conversation_id": 88,
  "user_message": {
    "id": 1001,
    "role": "user",
    "content": "请根据我当前的画像和知识星图，帮我生成一份学习计划",
    "created_at": "2026-06-08T00:30:00Z"
  },
  "ai_message_id": 1002,
  "ai_state": "generating"
}
```

```json
{
  "type": "start",
  "ai_message_id": 1002
}
```

```json
{
  "type": "chunk",
  "ai_message_id": 1002,
  "content": "我已经根据你当前的学习情况整理出一份学习计划，"
}
```

```json
{
  "type": "end",
  "ai_message_id": 1002
}
```

```json
{
  "type": "complete",
  "conversation_id": 88,
  "ai_message_id": 1002,
  "content": "我已经根据你当前的学习情况整理出一份学习计划，建议你先进入练习模式巩固二叉树和递归。",
  "meta": {
    "agent": "plan",
    "plan": {
      "id": 12,
      "subject_id": 1,
      "conversation_id": 88,
      "target_agent": "practice",
      "difficulty": "medium",
      "memory": {
        "summary": "先通过练习巩固当前薄弱点。",
        "reason": "画像已基本完整，且知识星图显示二叉树、递归掌握度较低。",
        "next_step": "进入练习 agent，先做一轮围绕薄弱点的题目。",
        "focus_nodes": ["二叉树", "递归"],
        "profile_complete": true,
        "subject_code": "data_structure",
        "subject_display": "数据结构"
      },
      "create_time": "2026-06-08T00:30:01Z",
      "success_time": null,
      "state": "pending"
    },
    "saved": true,
    "subject_id": 1
  }
}
```

前端建议：

- 用 `complete.meta.plan` 作为本轮计划结果的唯一可信来源
- 用 `plan.target_agent` 决定后续跳转到 `chat / profile / practice`
- 用 `plan.difficulty` 控制后续页面默认难度展示
- 如需编辑已有计划，请在发送消息时通过 `meta.selected_plan_ids` 显式传入选中的计划 ID 列表
- 如未传 `meta.selected_plan_ids`，后端会默认理解为“新建计划”

## 10. 推荐前端接入流程

### 10.1 初始化

1. 登录获取 JWT
2. 创建会话或查询已有会话
3. 使用 `conversation_id` 建立 WebSocket 连接

### 10.2 建连后

前端依次处理：

1. `history`
2. `state`
3. 如果有 `resume`，恢复当前正在生成的消息

### 10.3 用户发送消息

1. 通过 WS 发送 `type=message`
2. 收到 `accepted`
3. 创建本轮“AI 正在生成”的占位 UI
4. 按事件流更新：
   - `start`
   - `tool_call`
   - `tool_result`
   - `thinking_start`
   - `thinking_chunk`
   - `thinking_end`
   - `chunk`
   - `end`
   - `complete`
   - `error`

## 11. 前端状态管理建议

建议前端按 `ai_message_id` 聚合一轮 AI 回复状态。

### 11.1 建议维护的字段

- `conversationId`
- `aiMessageId`
- `status`
  - `generating`
  - `complete`
  - `error`
- `content`
- `meta`
- `toolCalls`

### 11.2 toolCalls 建议结构

```json
[
  {
    "tool_call_id": "run_123",
    "tool_name": "get_knowledge_map",
    "tool_args": {
      "subject_code": "data_structure"
    },
    "tool_output": "...",
    "status": "done"
  }
]
```

## 12. 兼容性说明

- 当前主流程：发消息和收流都走 WebSocket
- 仍保留 HTTP 兼容消息入口：
  - `POST /api/conversations/<conversation_id>/messages/`
- 但前端新接入建议直接使用 WebSocket 统一流程

## 13. 常见问题

### 13.1 为什么建连后先收到 history / state？

这是为了让前端在刷新、重连、断线恢复时快速同步当前会话状态。

### 13.2 为什么 resume 不是增量？

因为 `resume` 的目标是断线恢复，它返回当前累计内容，方便前端直接恢复展示。

### 13.3 为什么 chunk 是增量？

因为流式生成阶段前端只需要 append 新内容，增量更高效。

### 13.4 为什么 chat 和 practice 有 tool_call/tool_result，profile 没有？

因为当前只对 chat / practice 的工具调用做了前端可视化；profile 的评估逻辑仍主要通过最终 `complete.meta` 暴露结果。

### 13.5 practice 和 chat 的区别是什么？

- chat 只使用只读工具查询数据，不直接更新知识星图
- practice 会在用户回答题目后直接调用更新工具，修改对应知识点掌握度

### 13.6 plan agent 的 complete 里为什么会带计划对象？

因为 plan agent 的目标就是“构建计划”本身，所以前端通常不需要再额外查一次接口，就可以直接从 `complete.meta.plan` 拿到本轮生成结果。
