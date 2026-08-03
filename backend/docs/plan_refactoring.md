# Plan Agent 重构总结

## 重构目标

将 plan agent 拆分为三个独立组件，实现职责分离和更好的可复用性。

## 新架构

```
llm/
├── common.py              # 公共工具函数（避免循环导入）
├── chains/
│   └── plan_chain.py      # 计划生成核心逻辑
├── tools/
│   └── plan_tools.py      # 5 个 CRUD 工具
└── agents/
    └── plan_agent.py      # 对话编排 + 流式输出
```

### 1. `llm/common.py` - 公共工具函数

**职责**：提供被多个模块共用的工具函数，避免循环导入

**主要函数**：
- `extract_json()` - 从 LLM 输出提取 JSON
- `format_history()` - 格式化对话历史
- `dumps_profile()` - 序列化用户画像
- `profile_is_complete()` - 判断画像是否完整
- `current_round_from_history()` - 计算对话轮次

**为什么单独创建**：
- 之前这些函数在 `agents/profile_common.py` 和 `agents/profile_evaluator_agent.py`
- 当 `plan_chain.py` 导入它们时，会触发 `agents/__init__.py` 加载
- `agents/__init__.py` 导入 `plan_agent`，而 `plan_agent` 又导入 `plan_chain` → 循环导入
- 将公共函数移到 `llm/common.py` 打破循环

### 2. `llm/chains/plan_chain.py` - 计划生成核心逻辑

**职责**：根据用户画像和知识星图生成学习计划

**主要函数**：
```python
async def build_learning_plan(
    *,
    subject_display: str,
    subject_code: str,
    history_messages: list[BaseMessage],
    profile_summary: dict,
    knowledge_map: list[dict],
) -> dict:
    """生成个性化的学习计划"""
```

**特点**：
- 纯逻辑，不包含对话编排
- 可被 plan_agent、plan_tool、其他 chain 复用
- 包含 fallback 机制（LLM 失败时使用规则生成）

**返回格式**：
```json
{
  "target_agent": "practice",
  "difficulty": "medium",
  "state": "pending",
  "memory": {
    "summary": "...",
    "reason": "...",
    "next_step": "...",
    "focus_nodes": ["链表", "二叉树"],
    "profile_complete": true
  }
}
```

### 3. `llm/tools/plan_tools.py` - 5 个 CRUD 工具

**职责**：提供计划的增删改查操作，供 agent 在对话中调用

**工具列表**：

#### `get_selected_plans`
```python
@tool
def get_selected_plans(
    plan_ids: list[int],
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """获取用户选中的计划详情"""
```
**用途**：当 agent 需要了解现有计划的具体内容时调用

#### `update_plan`
```python
@tool
def update_plan(
    plan_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
    target_agent: str | None = None,
    difficulty: str | None = None,
    memory: dict | None = None,
    state: str | None = None,
) -> str:
    """更新现有计划"""
```
**用途**：修改现有计划的任何字段

#### `create_plan`
```python
@tool
def create_plan(
    target_agent: str,
    difficulty: str,
    memory: dict,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """创建新计划"""
```
**用途**：当用户要求添加新计划时调用

#### `delete_plan`
```python
@tool
def delete_plan(
    plan_id: int,
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> str:
    """删除计划"""
```
**用途**：当用户明确要求删除某个计划时调用

#### `list_user_plans`
```python
@tool
def list_user_plans(
    config: Annotated[RunnableConfig, InjectedToolArg],
    state: str | None = None,
    limit: int = 10,
) -> str:
    """列出用户的所有计划"""
```
**用途**：当用户问"我有哪些计划"时调用

### 4. `llm/agents/plan_agent.py` - 对话编排

**职责**：流式输出对话，调用工具读写计划

**主要函数**：

#### `astream_plan_events` - 编辑模式
```python
async def astream_plan_events(
    *,
    subject_display: str,
    subject_code: str,
    user_id: int,
    history_messages: list[BaseMessage],
    selected_plan_ids: list[int] | None = None,
    extra_prompt: str | None = None,
) -> AsyncIterator[PlanAgentEvent]:
    """流式输出 Plan Agent 事件（带工具调用）"""
```

#### `astream_plan_reply` - 生成模式
```python
async def astream_plan_reply(
    *,
    subject_display: str,
    history_messages: list[BaseMessage],
    plan: dict,
    extra_prompt: str | None = None,
) -> AsyncIterator[str]:
    """流式输出计划回复（用于生成新计划后的回复）"""
```

## 两种运行模式

### 模式 1：生成模式（Generate Mode）

**触发条件**：`conversation.selected_plan_ids` 为空

**流程**：
```
用户: "帮我制定一个学习计划"
  ↓
_run_plan_agent_async()
  ↓
build_learning_plan()  ← 调用 plan_chain
  ↓
_create_learning_plan()  ← 保存到数据库
  ↓
astream_plan_reply()  ← 流式输出回复
  ↓
WebSocket 推送给用户
```

**特点**：
- 一次性生成计划
- 不需要工具调用
- 快速响应

### 模式 2：编辑模式（Edit Mode）

**触发条件**：`conversation.selected_plan_ids` 非空（如 `[1, 2, 3]`）

**流程**：
```
用户选中计划 ID=1,2,3
  ↓
创建对话，selected_plan_ids=[1,2,3]
  ↓
用户: "把那个练习计划改成高难度"
  ↓
astream_plan_events()  ← 带工具的 agent
  ↓
LLM 推理: "需要先查看计划详情"
  ↓
调用 get_selected_plans([1,2,3])
  ↓
工具返回计划详情
  ↓
LLM 推理: "ID=1 是练习计划，改成 high"
  ↓
调用 update_plan(1, difficulty='high')
  ↓
工具返回 "OK: 计划 1 已更新"
  ↓
LLM 流式回复: "已将练习计划改为高难度"
```

**特点**：
- 多轮对话
- Agent 自主决定调用哪些工具
- 工具调用记录在 message.tool_calls 中
- 可以批量操作多个计划

## 数据模型变更

### Conversation 模型新增字段

```python
# users/models.py
class Conversation(models.Model):
    # ... 其他字段 ...
    selected_plan_ids = models.JSONField(
        '选中的计划 ID 列表', 
        default=list, 
        blank=True,
        help_text='用户选中的计划 ID 列表，用于 plan agent 编辑现有计划',
    )
```

**用途**：前端在创建 plan 对话时传入用户选中的计划 ID

**API 示例**：
```json
POST /api/conversations/
{
  "subject_id": 1,
  "agent": "plan",
  "title": "编辑学习计划",
  "selected_plan_ids": [1, 2, 3]
}
```

### 迁移文件

- `users/migrations/0013_add_selected_plan_ids_to_conversation.py`

## 提示词设计

### `plan_prompts.py` 包含三套提示词

#### 1. `PLAN_BUILDER_SYSTEM_PROMPT`
- 用于 `build_learning_plan()`（plan_chain）
- 指导 LLM 生成结构化计划
- 输出 JSON 格式

#### 2. `PLAN_EDIT_SYSTEM_PROMPT`
- 用于 `astream_plan_events()`（plan_agent 编辑模式）
- 指导 agent 如何调用工具
- 包含工具使用指南和注意事项

#### 3. `PLAN_REPLY_SYSTEM_PROMPT`
- 用于 `astream_plan_reply()`（plan_agent 生成模式）
- 指导如何用自然语言解释计划
- 输出简洁、可执行的建议

## 任务层集成

### `llm/tasks.py` - `_run_plan_agent_async`

```python
async def _run_plan_agent_async(*, conversation, current_user, ai_message_id: int, history_rows) -> None:
    # 判断模式
    selected_plan_ids = conversation.selected_plan_ids or []
    is_edit_mode = len(selected_plan_ids) > 0

    if is_edit_mode:
        # 编辑模式：使用 astream_plan_events（带工具）
        async for event in astream_plan_events(
            subject_display=...,
            subject_code=...,
            user_id=...,
            history_messages=...,
            selected_plan_ids=selected_plan_ids,
            extra_prompt=conversation.extra_prompt,
        ):
            # 处理事件流
            if event.type == "chunk":
                # 流式输出文本
            elif event.type == "tool_call":
                # 推送工具调用事件
            elif event.type == "tool_result":
                # 推送工具结果事件
    else:
        # 生成模式：生成新计划 + 流式回复
        plan_payload = await build_learning_plan(...)
        saved_plan = await _create_learning_plan(...)
        async for token in astream_plan_reply(...):
            # 流式输出文本
```

## 前端使用示例

### 场景 1：生成新计划

```javascript
// 创建对话（不传 selected_plan_ids）
const response = await fetch('/api/conversations/', {
  method: 'POST',
  body: JSON.stringify({
    subject_id: 1,
    agent: 'plan',
    title: '制定学习计划'
  })
});

// 连接 WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/conversation/${conversationId}/`);

// 发送消息
ws.send(JSON.stringify({
  type: 'message',
  content: '帮我制定一个学习计划'
}));

// 接收流式回复
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    console.log(data.content);  // "根据你的画像，建议..."
  }
};
```

### 场景 2：编辑现有计划

```javascript
// 用户在前端选中计划 ID=1,2,3
const selectedPlanIds = [1, 2, 3];

// 创建对话（传入 selected_plan_ids）
const response = await fetch('/api/conversations/', {
  method: 'POST',
  body: JSON.stringify({
    subject_id: 1,
    agent: 'plan',
    title: '编辑学习计划',
    selected_plan_ids: selectedPlanIds
  })
});

// 连接 WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/conversation/${conversationId}/`);

// 发送编辑请求
ws.send(JSON.stringify({
  type: 'message',
  content: '把那个练习计划改成高难度，再加一个新的画像计划'
}));

// 接收事件流
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'tool_call') {
    console.log(`调用工具: ${data.tool_name}`, data.tool_args);
    // 调用工具: get_selected_plans {plan_ids: [1, 2, 3]}
    // 调用工具: update_plan {plan_id: 1, difficulty: 'high'}
    // 调用工具: create_plan {target_agent: 'profile', ...}
  }
  
  if (data.type === 'tool_result') {
    console.log(`工具结果: ${data.tool_name}`, data.tool_output);
    // 工具结果: get_selected_plans [{id: 1, ...}, ...]
    // 工具结果: update_plan "OK: 计划 1 已更新"
    // 工具结果: create_plan "OK: 新计划已创建，ID=4"
  }
  
  if (data.type === 'chunk') {
    console.log(data.content);
    // "好的，我已经：
    //  1. 将计划 1 的难度从 medium 改为 high
    //  2. 新建了一个画像构建计划（ID=4）..."
  }
};
```

## 架构优势

| 维度 | 重构前 | 重构后 |
|------|--------|--------|
| **职责清晰** | plan_agent.py 混杂生成和回复逻辑 | Chain 负责生成，Agent 负责对话 |
| **复用性** | Plan 逻辑只能在 plan agent 中使用 | Chain 可被多个地方调用 |
| **灵活性** | 只能生成新计划 | 支持生成和编辑两种模式 |
| **可测试性** | 难以单独测试计划生成逻辑 | Chain 可以独立单元测试 |
| **工具调用** | 无工具支持 | 5 个 CRUD 工具，agent 自主调用 |
| **批量操作** | 不支持 | 一次对话可以修改多个计划 |

## 关键设计决策

### 1. 为什么创建 `llm/common.py`？

**问题**：循环导入
- `plan_chain.py` 需要 `profile_common` 和 `profile_evaluator_agent` 中的工具函数
- 这些函数在 `agents/` 目录下
- 导入它们会触发 `agents/__init__.py` 加载
- `agents/__init__.py` 导入 `plan_agent`
- `plan_agent` 导入 `plan_chain` → 循环

**解决方案**：
- 将公共函数移到 `llm/common.py`
- `plan_chain.py` 从 `llm.common` 导入
- 不触发 `agents/__init__.py` 加载

### 2. 为什么让 agent 通过 ID 获取计划数据？

**问题**：extra_prompt 应该包含完整计划数据还是只包含 ID？

**方案 A**：包含完整计划数据
```python
extra_prompt = """
## 计划 ID=1
- 目标: practice
- 难度: medium
...
"""
```

**方案 B**：只包含 ID（采用）
```python
extra_prompt = "用户当前选中的计划 ID: 1, 2, 3"
```

**选择方案 B 的原因**：
- ✅ Token 效率高（100-200 字符 vs 1000+ 字符）
- ✅ 数据实时（工具调用时实时查询）
- ✅ 符合 Tool 设计理念（Agent 自主决定何时获取数据）

### 3. 为什么有两种模式？

**生成模式**：
- 用户："帮我制定一个学习计划"
- 不需要查看/修改现有计划
- 快速生成新计划

**编辑模式**：
- 用户："把那个练习计划改成高难度"
- 需要查看现有计划内容
- 需要工具调用来修改

**好处**：
- 根据场景选择最合适的模式
- 生成模式更快（不需要工具调用）
- 编辑模式更灵活（可以批量操作）

## 总结

这次重构实现了：

1. ✅ **职责分离**：Chain（生成）、Tools（CRUD）、Agent（对话）各司其职
2. ✅ **避免循环导入**：创建 `llm/common.py` 存放公共函数
3. ✅ **两种模式**：生成模式（快速）和编辑模式（灵活）
4. ✅ **工具支持**：5 个 CRUD 工具，agent 自主调用
5. ✅ **数据模型**：Conversation 新增 `selected_plan_ids` 字段
6. ✅ **任务层集成**：`_run_plan_agent_async` 自动判断模式

架构更清晰、更灵活、更易维护！
