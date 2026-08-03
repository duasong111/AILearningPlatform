# Extra Prompt 功能说明

## 概述

`extra_prompt` 是 Conversation 模型的新字段，允许用户在创建对话时注入额外的提示词指令，用于定制 Agent 的行为和风格。

## 功能特性

### 1. 模型层
- **字段**: `Conversation.extra_prompt` (TextField, nullable)
- **用途**: 存储用户自定义的额外指令
- **持久化**: 保存在数据库中，随对话一起存储

### 2. API 层
创建对话时可以通过 `extra_prompt` 字段传入自定义指令：

```bash
POST /api/conversations/
{
  "subject_id": 1,
  "title": "我的对话",
  "agent": "chat",
  "extra_prompt": "请用幽默风趣的语气回答，多使用比喻和例子"
}
```

### 3. Agent 层
所有 Agent 都支持 `extra_prompt` 注入：

#### Chat Agent
```python
def build_system_prompt(subject_display, subject_code, extra_prompt=None):
    prompt = CHAT_AGENT_SYSTEM_PROMPT.format(...)
    if extra_prompt:
        prompt += f"\n\n## 额外指令\n{extra_prompt}"
    return prompt
```

#### Profile Agent
```python
async def astream_profile_reply(..., extra_prompt=None):
    # extra_prompt 会注入到系统提示词末尾
```

#### Plan Agent
```python
async def astream_plan_reply(..., extra_prompt=None):
    # extra_prompt 会注入到系统提示词末尾
```

### 4. 任务层
Celery 任务会自动从 Conversation 模型读取 `extra_prompt` 并传递给 Agent：

```python
# llm/tasks.py
asyncio.run(
    _run_chat_agent_async(
        ...
        extra_prompt=conversation.extra_prompt,  # 自动传递
    )
)
```

## 使用示例

### 示例 1: 定制回答风格
```python
Conversation.objects.create(
    subject=subject,
    agent="chat",
    extra_prompt="你是一个耐心的老师，对每个问题都详细解释，多用例子说明"
)
```

### 示例 2: 定制专业程度
```python
Conversation.objects.create(
    subject=subject,
    agent="chat",
    extra_prompt="假设用户是资深工程师，回答要深入底层原理，不需要解释基础概念"
)
```

### 示例 3: 定制画像构建重点
```python
Conversation.objects.create(
    subject=subject,
    agent="profile",
    extra_prompt="重点关注用户的学习目标和时间安排，其他信息可以快速收集"
)
```

### 示例 4: 定制学习计划风格
```python
Conversation.objects.create(
    subject=subject,
    agent="plan",
    extra_prompt="生成保守稳妥的学习计划，不要安排太紧凑，多留复习时间"
)
```

## 系统提示词注入位置

`extra_prompt` 会追加到系统提示词的**末尾**，格式如下：

```
[原始系统提示词]

## 额外指令
[用户自定义的 extra_prompt]
```

这样可以确保：
1. 原始系统提示词的核心规则不受影响
2. 额外指令作为补充，优先级较高
3. LLM 会同时遵循原始规则和额外指令

## 技术实现

### 数据库迁移
```python
# users/migrations/0012_add_extra_prompt_to_conversation.py
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='conversation',
            name='extra_prompt',
            field=models.TextField(
                blank=True,
                help_text='注入到系统提示词中的额外指令，用于定制 agent 行为',
                null=True,
                verbose_name='额外提示词'
            ),
        ),
    ]
```

### 修改的文件
1. `users/models.py` - 添加 `extra_prompt` 字段
2. `users/serializers.py` - 序列化器支持该字段
3. `llm/agents/chat_agent.py` - Chat Agent 支持注入
4. `llm/agents/profile_conversation_agent.py` - Profile Agent 支持注入
5. `llm/agents/plan_agent.py` - Plan Agent 支持注入
6. `llm/tasks.py` - 任务层传递 `extra_prompt`

### 测试
运行测试验证功能：
```bash
python test/test_extra_prompt.py
```

测试覆盖：
- ✅ 数据库字段读写
- ✅ 序列化器支持
- ✅ 系统提示词注入
- ✅ 不同 Agent 类型支持

## 注意事项

1. **可选字段**: `extra_prompt` 是可选的，不传则为 `None`，不影响现有功能
2. **向后兼容**: 已有对话的 `extra_prompt` 为 `None`，行为不变
3. **指令冲突**: 如果 `extra_prompt` 与原始系统提示词冲突，LLM 会尝试平衡两者
4. **长度建议**: 建议 `extra_prompt` 控制在 500 字符以内，避免占用过多 context

## 未来扩展

可能的增强方向：
- 支持多个 `extra_prompt` 模板（预设常用指令）
- 支持在对话过程中动态修改 `extra_prompt`
- 支持按 Agent 类型限制可用的 `extra_prompt`
- 添加 `extra_prompt` 使用统计和分析
