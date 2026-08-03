# Practice Chain 测试说明

## 测试文件

`test/test_practice_chain.py` - Practice Chain 功能测试脚本

## 测试内容

该测试脚本验证了 Practice Chain 的完整功能，包括：

### 1. Quiz 数据存储和读取
- 验证 Quiz 数据正确存储到 Redis/Cache
- 验证状态和题目数据的完整性

### 2. with_answer 模式 - 用户回答正确
- 验证带答案分析模式
- 验证知识点提取
- 验证难度评估
- 验证答题后结构化字段（`result / steps / deep_analysis / pitfalls / next_steps`）

### 3. with_answer 模式 - 用户回答错误
- 验证错误答案的分析
- 验证错误原因的识别
- 验证正确答案的解释

### 4. without_answer 模式 - 引导式分析
- 验证无答案模式下的引导式分析
- 验证不会直接给出答案
- 验证知识点覆盖
- 验证答题前结构化字段（`approach / hints / knowledge / steps`）

### 5. 错误处理 - Quiz 数据不存在
- 验证 `QuizNotFoundError` 异常正确抛出

### 6. 错误处理 - 题目索引越界
- 验证 `QuestionIndexError` 异常正确抛出

### 7. 分析多道题中的特定题目
- 验证可以从多道题中选择特定题目进行分析

### 8. Practice 结果序列化和反序列化
- 验证 JSON 序列化/反序列化的正确性

## 日志输出

测试运行时会自动生成日志文件：
- **日志目录**: `test/logs/`
- **文件命名**: `test_practice_chain_YYYYMMDD_HHMMSS.log`
- **日志内容**: 完整的测试输出，包括每个测试的详细结果

示例：
```
📝 测试日志已保存到: /home/app/code/github/aiteach/backend/test/logs/test_practice_chain_20260609_082752.log
```

查看最新日志：
```bash
# 查看最新的日志文件
ls -t test/logs/ | head -1 | xargs -I {} less test/logs/{}

# 或者查看日志目录
ls -lh test/logs/
```

## 运行测试

### 前置条件

确保已安装所有依赖：
```bash
cd backend
pip install -r requirements.txt
```

### 运行测试

```bash
cd backend
python test/test_practice_chain.py
```

### 预期输出

```
============================================================
Practice Chain 功能测试
============================================================

============================================================
测试 1: Quiz 数据存储和读取
============================================================
✓ Quiz 状态正确: complete
✓ Quiz 数据正确: 3 道题
✓ 第一题内容正确: 链表

✓ 测试 1 通过

... (其他测试)

============================================================
测试结果: 8/8 通过
============================================================
```

## 测试原理

### Mock 策略

测试使用 `unittest.mock` 模拟 LLM 调用，不需要真实的 API 密钥：

1. **模拟 Quiz 数据**：直接在缓存中写入预设的题目数据
2. **模拟 LLM 响应**：使用预设的 `PracticeAnalysis` 对象作为 LLM 返回值
3. **使用 LocMemCache**：通过 `settings_test.py` 使用内存缓存，无需 Redis

### 测试数据

测试使用 3 种不同类型的题目：
- **选择题（中等难度）**：单链表删除操作的时间复杂度
- **简答题（高难度）**：二叉搜索树的最坏情况分析
- **选择题（简单）**：数组随机访问时间复杂度

当前 quiz/practice 强结构输出的重点字段包括：

- **QuizQuestion**：
  - `topic / bloom_level / title / question_text / question_context / code_snippet`
  - `input_modes / approach / hints / steps / knowledge / deep_analysis / pitfalls / next_steps`
- **PracticeAnalysis**：
  - `mode / phase / analysis / key_knowledge_points / difficulty_assessment`
  - `approach / hints / knowledge / result / steps / deep_analysis / pitfalls / next_steps`

## 测试覆盖的功能点

| 功能点 | 测试覆盖 |
|--------|----------|
| Quiz 数据存储 | ✓ |
| Quiz 数据读取 | ✓ |
| with_answer 模式 | ✓ |
| without_answer 模式 | ✓ |
| 用户回答正确 | ✓ |
| 用户回答错误 | ✓ |
| 错误处理 | ✓ |
| 多题选择 | ✓ |
| 序列化/反序列化 | ✓ |

## 扩展测试

如需添加更多测试，可以参考现有测试函数的结构：

```python
async def test_your_new_feature():
    """测试描述"""
    print("\n" + "=" * 60)
    print("测试 X: 你的新功能")
    print("=" * 60)
    
    # 准备数据
    quiz_task_id = "test-quiz-xxx"
    questions = [create_mock_quiz_question(0)]
    setup_mock_quiz_data(quiz_task_id, questions)
    
    # Mock LLM
    mock_analysis = create_mock_analysis("with_answer")
    mock_llm = mock_llm_response(mock_analysis)
    
    # 执行测试
    with patch('llm.chains.practice_chain.build_llm', return_value=mock_llm):
        result = await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=0,
            mode="with_answer",
        )
    
    # 验证结果
    assert result.mode == "with_answer"
    print(f"✓ 验证通过")
    
    print("\n✓ 测试 X 通过\n")
```

然后在 `main()` 函数的 `tests` 列表中添加新测试：

```python
tests = [
    test_quiz_storage,
    # ... 其他测试
    test_your_new_feature,  # 添加新测试
]
```

## 故障排除

### 问题：ModuleNotFoundError: No module named 'celery'

解决：
```bash
pip install celery
```

### 问题：ModuleNotFoundError: No module named 'channels'

解决：
```bash
pip install channels
```

### 问题：测试失败但错误信息不明确

解决：查看完整的错误堆栈
```bash
python test/test_practice_chain.py 2>&1
```

## 相关文件

- `llm/chains/practice_chain.py` - Practice Chain 核心逻辑
- `llm/chains/quiz_chain.py` - Quiz Chain 核心逻辑
- `llm/schemas/practice_schema.py` - Practice 结果 Schema
- `llm/tasks.py` - Celery 任务定义
- `config/settings_test.py` - 测试环境配置
