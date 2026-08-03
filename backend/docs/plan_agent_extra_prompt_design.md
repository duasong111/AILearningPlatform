# Plan Agent Extra Prompt 设计方案

## 设计原则

**Conversation 是通用对话模型，不应该为特定 agent 添加字段。**

所有 agent 特定的上下文信息都通过 `extra_prompt` 字段传递。

## 方案概述

### 前端传递 Plan IDs

前端在创建 plan 对话时，将选中的计划 ID 放在 `extra_prompt` 中：

```javascript
// 示例 1：标准格式
POST /api/conversations/
{
  "subject_id": 1,
  "agent": "plan",
  "title": "编辑学习计划",
  "extra_prompt": "用户选中的计划 ID: 1, 2, 3"
}

// 示例 2：JSON 格式
POST /api/conversations/
{
  "subject_id": 1,
  "agent": "plan",
  "title": "编辑学习计划",
  "extra_prompt": "plan_ids: [1, 2, 3]"
}

// 示例 3：自然语言
POST /api/conversations/
{
  "subject_id": 1,
  "agent": "plan",
  "title": "编辑学习计划",
  "extra_prompt": "请帮我编辑这几个计划，ID 是 5, 6, 7，把难度都改成 medium"
}
```

### 后端自动解析

`plan_agent.py` 中的 `extract_plan_ids_from_prompt()` 函数自动从 `extra_prompt` 中提取计划 ID。

## 支持的格式

`extract_plan_ids_from_prompt()` 支持以下格式：

| 格式 | 示例 | 提取结果 |
|------|------|----------|
| 中文标准 | `"用户选中的计划 ID: 1, 2, 3"` | `[1, 2, 3]` |
| 中文无空格 | `"用户选中的计划 ID: 1,2,3"` | `[1, 2, 3]` |
| 中文空格分隔 | `"用户选中的计划 ID: 1 2 3"` | `[1, 2, 3]` |
| 英文标准 | `"plan_ids: 1, 2, 3"` | `[1, 2, 3]` |
| JSON 数组 | `"plan_ids: [1, 2, 3]"` | `[1, 2, 3]` |
| selected_plan_ids | `"selected_plan_ids: 10, 20"` | `[10, 20]` |
| 纯数组 | `"[1, 2, 3]"` | `[1, 2, 3]` |
| 自然语言 | `"请帮我编辑计划，ID 是 5, 6, 7"` | `[5, 6, 7]` |
| 单个 ID | `"用户选中的计划 ID: 100"` | `[100]` |

## 工作流程

### 1. 前端创建对话

```javascript
const response = await fetch('/api/conversations/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    subject_id: 1,
    agent: 'plan',
    title: '编辑学习计划',
    extra_prompt: '用户选中的计划 ID: 1, 2, 3\n\n请把这些计划都改成高难度'
  })
});
```

### 2. 后端判断模式

`tasks.py` 中的 `_run_plan_agent_async()` 自动判断模式：

```python
# 从 extra_prompt 中提取计划 ID
plan_ids = extract_plan_ids_from_prompt(conversation.extra_prompt)
is_edit_mode = plan_ids is not None and len(plan_ids) > 0

if is_edit_mode:
    # 编辑模式：使用工具读写现有计划
    async for event in astream_plan_events(...):
        ...
else:
    # 生成模式：生成新计划
    plan = await build_learning_plan(...)
    ...
```

### 3. 构建系统提示词

`build_system_prompt()` 自动处理 extra_prompt：

```python
def build_system_prompt(subject_display, subject_code, extra_prompt=None):
    prompt = PLAN_EDIT_SYSTEM_PROMPT.format(...)
    
    if extra_prompt:
        # 检查是否包含计划 ID
        plan_ids = extract_plan_ids_from_prompt(extra_prompt)
        if plan_ids:
            # 添加编辑指令
            prompt += build_plan_edit_instructions(plan_ids)
        
        # 始终附加原始 extra_prompt
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    
    return prompt
```

### 4. Agent 调用工具

Agent 看到系统提示词中的计划 ID 后，会自动调用 `get_selected_plans` 工具获取详情：

```
系统提示词：
...
## 用户选中的计划

用户当前选中的计划 ID: 1, 2, 3

如需查看这些计划的详细内容，请使用 get_selected_plans 工具。
...

## 额外指令
用户选中的计划 ID: 1, 2, 3

请把这些计划都改成高难度
```

Agent 推理：
1. 看到计划 ID: 1, 2, 3
2. 调用 `get_selected_plans([1, 2, 3])` 获取详情
3. 对每个计划调用 `update_plan(id, difficulty='high')`
4. 回复用户："已将 3 个计划改为高难度"

## 两种模式对比

### 生成模式（无计划 ID）

```javascript
// 前端
{
  "agent": "plan",
  "extra_prompt": "帮我制定一个学习计划"  // 无计划 ID
}

// 后端
plan_ids = None
is_edit_mode = False
→ 调用 build_learning_plan() 生成新计划
→ 调用 astream_plan_reply() 流式回复
```

### 编辑模式（有计划 ID）

```javascript
// 前端
{
  "agent": "plan",
  "extra_prompt": "用户选中的计划 ID: 1, 2, 3\n\n把难度改成 high"
}

// 后端
plan_ids = [1, 2, 3]
is_edit_mode = True
→ 调用 astream_plan_events()（带工具）
→ Agent 调用 get_selected_plans, update_plan 等工具
→ 流式回复工具调用过程和结果
```

## 优势

### 1. 模型通用性
- ✅ Conversation 模型保持通用，不需要为特定 agent 添加字段
- ✅ 所有 agent 都使用同一个 `extra_prompt` 字段
- ✅ 易于扩展：未来其他 agent 也可以在 extra_prompt 中传递特定信息

### 2. 灵活性
- ✅ 前端可以用任何格式传递计划 ID
- ✅ 支持自然语言："请帮我编辑计划，ID 是 5, 6, 7"
- ✅ 支持结构化格式："plan_ids: [1, 2, 3]"
- ✅ 可以同时传递其他指令："用户选中的计划 ID: 1, 2, 3\n\n把难度改成 high"

### 3. 简洁性
- ✅ 不需要额外的迁移（只保留 extra_prompt 字段）
- ✅ 不需要修改序列化器（extra_prompt 已经存在）
- ✅ 不需要修改前端 API（extra_prompt 已经支持）

## 代码变更总结

### 已删除
- ❌ `users/models.py`: `Conversation.selected_plan_ids` 字段
- ❌ `users/migrations/0013_add_selected_plan_ids_to_conversation.py`
- ❌ `users/serializers.py`: `selected_plan_ids` 从两个序列化器中移除

### 已添加/修改
- ✅ `llm/agents/plan_agent.py`: 
  - `extract_plan_ids_from_prompt()` - 从 extra_prompt 提取计划 ID
  - `build_plan_edit_instructions()` - 构建编辑指令
  - `build_system_prompt()` - 自动处理 extra_prompt 中的计划 ID
  - `astream_plan_events()` - 移除 `selected_plan_ids` 参数

- ✅ `llm/tasks.py`:
  - `_run_plan_agent_async()` - 从 extra_prompt 判断模式
  - 导入 `extract_plan_ids_from_prompt`

- ✅ `test/test_plan_ids_extraction.py`:
  - 13 个测试用例，覆盖所有支持的格式

## 测试验证

```bash
cd backend
python test/test_plan_ids_extraction.py
```

测试结果：
```
============================================================
测试结果: 13/13 通过
============================================================
✅ 中文格式，逗号分隔
✅ 中文格式，无空格
✅ 中文格式，空格分隔
✅ 英文格式，数组
✅ 英文格式，逗号
✅ selected_plan_ids 格式
✅ 纯数组格式
✅ 自然语言中包含
✅ 无计划 ID
✅ 空字符串
✅ None 值
✅ 单个 ID
✅ 多个 ID
```

## 使用示例

### 场景 1：批量修改计划

```javascript
// 前端：用户在前端选中 3 个计划，想把它们都改成高难度
const response = await fetch('/api/conversations/', {
  method: 'POST',
  body: JSON.stringify({
    subject_id: 1,
    agent: 'plan',
    title: '批量修改计划',
    extra_prompt: '用户选中的计划 ID: 1, 2, 3\n\n请把这些计划都改成高难度'
  })
});

// WebSocket 连接后
ws.send({ type: 'message', content: '开始修改' });

// Agent 会自动：
// 1. 调用 get_selected_plans([1, 2, 3])
// 2. 对每个计划调用 update_plan(id, difficulty='high')
// 3. 回复："已将 3 个计划改为高难度"
```

### 场景 2：混合指令

```javascript
// 前端：同时传递计划 ID 和其他指令
{
  "agent": "plan",
  "extra_prompt": "用户选中的计划 ID: 5, 6\n\n" +
                  "1. 把计划 5 改成 practice 类型\n" +
                  "2. 把计划 6 改成 high 难度\n" +
                  "3. 新建一个 profile 类型的计划"
}

// Agent 会按顺序执行这 3 个操作
```

### 场景 3：自然语言

```javascript
// 前端：用户用自然语言描述
{
  "agent": "plan",
  "extra_prompt": "我想编辑一下我的学习计划，ID 是 10, 11, 12，" +
                  "把它们的难度都降低一级，然后新建一个复习计划"
}

// Agent 能理解并执行
```

## 总结

通过 `extra_prompt` 传递计划 ID 的方案：
- ✅ 保持 Conversation 模型的通用性
- ✅ 灵活支持多种格式
- ✅ 代码简洁，无需额外迁移
- ✅ 易于扩展和维护

这是一个符合软件工程原则的优雅设计。
