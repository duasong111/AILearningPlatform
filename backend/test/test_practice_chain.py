"""
Practice Chain 功能测试脚本

测试内容：
1. Quiz chain 生成题目并存储到 Redis
2. Practice chain 从 Redis 读取题目并生成分析
3. 两种分析模式：with_answer 和 without_answer
4. 错误处理：题目不存在、索引越界等

运行方式：
    cd backend
    python test/test_practice_chain.py

日志输出：
    - 控制台实时输出
    - 文件保存：test/logs/test_practice_chain_YYYYMMDD_HHMMSS.log
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestLogger:
    """简单的测试日志记录器，同时输出到控制台和文件"""

    def __init__(self):
        self.log_file = None
        self.log_path = None

    def setup(self):
        """初始化日志文件"""
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_path = os.path.join(log_dir, f'test_practice_chain_{timestamp}.log')
        self.log_file = open(self.log_path, 'w', encoding='utf-8')

    def log(self, message: str):
        """输出日志到控制台和文件"""
        print(message)
        if self.log_file:
            self.log_file.write(message + '\n')
            self.log_file.flush()

    def close(self):
        """关闭日志文件"""
        if self.log_file:
            self.log_file.close()
            print(f"\n📝 测试日志已保存到: {self.log_path}")


# 全局日志记录器
logger = TestLogger()

# 设置 Django 测试环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.core.cache import cache
from langchain_core.messages import AIMessage

from llm.chains.practice_chain import (
    QuestionIndexError,
    QuizNotFoundError,
    analyze_quiz_question,
)
from llm.chains.quiz_chain import (
    QUIZ_TTL_SEC,
    quiz_result_key,
    quiz_state_key,
)
from llm.schemas.practice_schema import PracticeAnalysis
from llm.schemas.quiz_schema import QuizQuestion


def create_mock_quiz_question(index: int = 0) -> QuizQuestion:
    """创建一个模拟的 quiz 题目"""
    if index == 0:
        return QuizQuestion(
            question_type="choice",
            difficulty="medium",
            topic="数据结构",
            bloom_level="分析",
            title="单链表删除复杂度判断",
            knowledge_node_id="DS03",
            knowledge_node_name="链表",
            question_text="单链表中，删除第 i 个节点的时间复杂度是多少？",
            question_context="假设需要按常规流程先定位到待删除节点的前驱节点。",
            code_snippet=None,
            input_modes=["choice", "text", "image"],
            options=["A. O(1)", "B. O(log n)", "C. O(n)", "D. O(n²)"],
            correct_answer="C",
            explanation="删除第 i 个节点需要先找到第 i-1 个节点，这需要 O(n) 的时间遍历。删除操作本身是 O(1)，但总体时间复杂度为 O(n)。",
            approach="先把删除拆成“找到位置”和“执行删除”两个步骤，再分别分析复杂度。",
            hints=["删除前是否需要先找到前驱节点？", "链表能否像数组那样随机访问？"],
            steps=[
                {"text": "删除第 i 个节点前，需要先找到第 i-1 个节点。", "is_key": True},
                {"text": "单链表只能顺序遍历，因此查找前驱节点需要 O(n)。", "is_key": False},
                {"text": "修改指针本身是 O(1)，但整体复杂度仍由查找决定。", "is_key": False},
            ],
            knowledge=[
                {"title": "链表遍历", "description": "单链表只能从头顺序访问节点", "icon": None},
                {"title": "删除操作", "description": "删除通常需要先拿到待删节点前驱", "icon": None},
            ],
            deep_analysis="这道题容易把“删除动作本身”和“完成删除整件事”的复杂度混淆。真正的瓶颈在于定位节点位置，而不是改指针。",
            pitfalls=["把删除动作本身的 O(1) 误当成完整流程复杂度"],
            next_steps=["继续对比链表与数组的插入删除复杂度"],
        )
    elif index == 1:
        return QuizQuestion(
            question_type="short_answer",
            difficulty="hard",
            topic="数据结构",
            bloom_level="评价",
            title="BST 最坏情况与规避方式",
            knowledge_node_id="DS05",
            knowledge_node_name="树",
            question_text="请解释二叉搜索树（BST）在最坏情况下的时间复杂度，并说明如何避免这种情况。",
            question_context="请同时说明最坏情况出现的原因。",
            code_snippet=None,
            input_modes=["text", "image"],
            options=None,
            correct_answer="最坏情况下 BST 退化为链表，查找/插入/删除的时间复杂度为 O(n)。可以通过平衡二叉树（如 AVL 树、红黑树）来保证 O(log n) 的时间复杂度。",
            explanation="当插入的数据有序时，BST 会退化为链表。平衡二叉树通过旋转操作保持树的平衡。",
            approach="先想 BST 理想情况下为什么快，再反推最坏情况下树会退化成什么形状。",
            hints=["考虑插入序列已经有序时树会变成什么样", "树高变化会如何影响查找路径长度"],
            steps=[
                {"text": "BST 理想情况下高度接近 O(log n)。", "is_key": False},
                {"text": "若插入数据有序，BST 会退化成链表。", "is_key": True},
                {"text": "退化后查找、插入、删除都可能要走完整条链，因此是 O(n)。", "is_key": False},
            ],
            knowledge=[
                {"title": "二叉搜索树", "description": "满足左小右大的有序树结构", "icon": None},
                {"title": "平衡二叉树", "description": "通过旋转保持树高受控", "icon": None},
            ],
            deep_analysis="BST 的效率本质上依赖树高。一旦树高退化到 n，查找路径也会随之拉长，复杂度就退化为线性级别。",
            pitfalls=["忽略树高对复杂度的直接影响"],
            next_steps=["继续练习 AVL 树和红黑树的平衡策略"],
        )
    else:
        return QuizQuestion(
            question_type="choice",
            difficulty="easy",
            topic="数据结构",
            bloom_level="理解",
            title="数组随机访问复杂度",
            knowledge_node_id="DS01",
            knowledge_node_name="数组",
            question_text="数组的随机访问时间复杂度是？",
            question_context=None,
            code_snippet=None,
            input_modes=["choice", "text", "image"],
            options=["A. O(1)", "B. O(log n)", "C. O(n)", "D. O(n²)"],
            correct_answer="A",
            explanation="数组支持通过索引直接访问元素，时间复杂度为 O(1)。",
            approach="回忆数组是否支持通过索引直接定位元素。",
            hints=["连续存储让数组具备什么优势？"],
            steps=[
                {"text": "数组元素在内存中连续排列。", "is_key": False},
                {"text": "给定索引可直接算出目标地址，因此访问是 O(1)。", "is_key": True},
            ],
            knowledge=[
                {"title": "数组", "description": "支持随机访问的线性结构", "icon": None},
                {"title": "随机访问", "description": "无需遍历，直接定位目标位置", "icon": None},
            ],
            deep_analysis="数组的随机访问能力来自连续内存布局和固定偏移量计算。",
            pitfalls=["把随机访问和插入效率混为一谈"],
            next_steps=["继续练习数组与链表的复杂度比较"],
        )


def create_mock_analysis(mode: str) -> PracticeAnalysis:
    """创建一个模拟的 practice 分析结果"""
    if mode == "with_answer":
        return PracticeAnalysis(
            mode=mode,
            phase="post_submit",
            analysis="删除链表节点时，真正耗时的是先找到前驱节点，因此整体复杂度是 O(n)。",
            key_knowledge_points=["链表遍历", "删除操作", "时间复杂度分析"],
            difficulty_assessment="medium",
            approach=None,
            hints=[],
            knowledge=[
                {"title": "链表遍历", "description": "单链表定位节点需要顺序访问", "icon": None},
                {"title": "删除操作", "description": "删除前通常需要先拿到前驱节点", "icon": None},
            ],
            result={
                "verdict": "correct",
                "is_correct": True,
                "user_answer": "C",
                "correct_answer": "C",
                "summary": "你回答正确，关键在于把查找前驱和执行删除分开分析。",
            },
            steps=[
                {"text": "先定位到第 i-1 个节点。", "is_key": True},
                {"text": "单链表只能顺序遍历，因此查找是 O(n)。", "is_key": False},
                {"text": "修改指针删除节点本身是 O(1)。", "is_key": False},
            ],
            deep_analysis="这道题考查的是单链表删除操作的完整流程复杂度。删除动作本身虽然简单，但定位前驱节点的成本决定了总体复杂度。",
            pitfalls=["不要只看改指针这一步", "要把查找成本计入总复杂度"],
            next_steps=["继续练习链表插入与删除题", "对比数组删除的 O(n) 原因"],
        )
    else:
        return PracticeAnalysis(
            mode=mode,
            phase="pre_submit",
            analysis="先从树高变化入手，思考 BST 在最坏情况下为什么会退化，以及平衡机制如何控制复杂度。",
            key_knowledge_points=["二叉搜索树", "最坏情况分析", "平衡二叉树", "时间复杂度"],
            difficulty_assessment="hard",
            approach="先想 BST 为何理想情况下快，再反推什么情况下它会失去这种优势。",
            hints=["考虑插入序列有序时会发生什么", "树高如果接近 n，会带来什么复杂度后果"],
            knowledge=[
                {"title": "二叉搜索树", "description": "查找效率高度依赖树高", "icon": None},
                {"title": "平衡二叉树", "description": "通过结构调整控制树高", "icon": None},
            ],
            result=None,
            steps=[
                {"text": "先分析 BST 在平衡状态下的高度和查找路径长度。", "is_key": False},
                {"text": "再考虑有序插入导致的退化情况。", "is_key": True},
                {"text": "最后思考哪些平衡机制能避免退化。", "is_key": False},
            ],
            deep_analysis=None,
            pitfalls=["不要只回答最坏复杂度而忽略退化原因"],
            next_steps=["先自己写出最坏情况分析", "再复盘 AVL 和红黑树如何保持平衡"],
        )


def setup_mock_quiz_data(task_id: str, questions: list[QuizQuestion]):
    """在缓存中设置模拟的 quiz 数据"""
    cache.set(quiz_state_key(task_id), "complete", QUIZ_TTL_SEC)
    result = [q.model_dump() for q in questions]
    cache.set(quiz_result_key(task_id), json.dumps(result, ensure_ascii=False), QUIZ_TTL_SEC)


def mock_llm_response(mock_analysis: PracticeAnalysis):
    """创建一个模拟的 LLM 响应"""
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_analysis)
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


async def test_quiz_storage():
    """测试 1: Quiz 数据存储和读取"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 1: Quiz 数据存储和读取")
    logger.log("=" * 60)

    task_id = "test-quiz-001"
    questions = [
        create_mock_quiz_question(0),
        create_mock_quiz_question(1),
        create_mock_quiz_question(2),
    ]

    # 存储到缓存
    setup_mock_quiz_data(task_id, questions)

    # 验证状态
    state = cache.get(quiz_state_key(task_id))
    assert state == "complete", f"状态应为 complete，实际为 {state}"
    logger.log(f"✓ Quiz 状态正确: {state}")

    # 验证数据
    result_json = cache.get(quiz_result_key(task_id))
    assert result_json is not None, "Quiz 结果不应为空"
    result = json.loads(result_json)
    assert len(result) == 3, f"应有 3 道题，实际为 {len(result)}"
    logger.log(f"✓ Quiz 数据正确: {len(result)} 道题")

    # 验证题目内容
    first_q = result[0]
    assert first_q["question_type"] == "choice"
    assert first_q["knowledge_node_name"] == "链表"
    assert len(first_q["options"]) == 4
    logger.log(f"✓ 第一题内容正确: {first_q['knowledge_node_name']}")

    logger.log("\n✓ 测试 1 通过\n")


async def test_practice_with_answer_correct():
    """测试 2: with_answer 模式 - 用户回答正确"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 2: with_answer 模式 - 用户回答正确")
    logger.log("=" * 60)

    # 准备 quiz 数据
    quiz_task_id = "test-quiz-002"
    questions = [create_mock_quiz_question(0)]
    setup_mock_quiz_data(quiz_task_id, questions)

    # Mock LLM
    mock_analysis = create_mock_analysis("with_answer")
    mock_llm = mock_llm_response(mock_analysis)

    with patch('llm.chains.practice_chain.build_llm', return_value=mock_llm):
        result = await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=0,
            mode="with_answer",
            user_answer="C",  # 正确答案
            subject_display="数据结构",
            subject_code="data_structure",
        )

    # 验证结果
    assert result.mode == "with_answer"
    assert "时间复杂度" in result.analysis
    assert result.result is not None and result.result.correct_answer == "C"
    assert len(result.key_knowledge_points) > 0
    logger.log(f"✓ 分析模式: {result.mode}")
    logger.log(f"✓ 分析长度: {len(result.analysis)} 字符")
    logger.log(f"✓ 知识点: {', '.join(result.key_knowledge_points)}")
    logger.log(f"✓ 难度评估: {result.difficulty_assessment}")

    logger.log("\n✓ 测试 2 通过\n")


async def test_practice_with_answer_wrong():
    """测试 3: with_answer 模式 - 用户回答错误"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 3: with_answer 模式 - 用户回答错误")
    logger.log("=" * 60)

    quiz_task_id = "test-quiz-003"
    questions = [create_mock_quiz_question(0)]
    setup_mock_quiz_data(quiz_task_id, questions)

    # 创建一个针对错误回答的分析
    mock_analysis = PracticeAnalysis(
        mode="with_answer",
        phase="post_submit",
        analysis="你把删除动作本身的 O(1) 和完整删除流程的 O(n) 混淆了。",
        key_knowledge_points=["链表遍历", "删除操作", "时间复杂度", "常见误区"],
        difficulty_assessment="medium",
        approach=None,
        hints=[],
        knowledge=[
            {"title": "链表遍历", "description": "定位前驱节点要顺序访问", "icon": None},
        ],
        result={
            "verdict": "wrong",
            "is_correct": False,
            "user_answer": "A",
            "correct_answer": "C",
            "summary": "你的选择是 A，正确答案是 C，因为查找前驱节点需要 O(n)。",
        },
        steps=[
            {"text": "先找到第 i-1 个节点。", "is_key": True},
            {"text": "顺序遍历找到前驱节点需要 O(n)。", "is_key": False},
            {"text": "修改指针删除节点本身是 O(1)。", "is_key": False},
        ],
        deep_analysis="常见误区在于只盯着改指针这一步，忽略了真正耗时的查找过程。",
        pitfalls=["混淆删除动作与完整删除流程"],
        next_steps=["复习链表操作复杂度", "对比数组和双向链表删除流程"],
    )
    mock_llm = mock_llm_response(mock_analysis)

    with patch('llm.chains.practice_chain.build_llm', return_value=mock_llm):
        result = await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=0,
            mode="with_answer",
            user_answer="A",  # 错误答案
            subject_display="数据结构",
            subject_code="data_structure",
        )

    assert result.result is not None and result.result.verdict == "wrong"
    assert result.result.user_answer == "A"
    assert "O(n)" in (result.deep_analysis or "") or "O(n)" in result.result.summary
    logger.log(f"✓ 错误分析正确识别了用户选择了 A")
    logger.log(f"✓ 分析了错误原因")
    logger.log(f"✓ 解释了正确答案")

    logger.log("\n✓ 测试 3 通过\n")


async def test_practice_without_answer():
    """测试 4: without_answer 模式 - 引导式分析"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 4: without_answer 模式 - 引导式分析")
    logger.log("=" * 60)

    quiz_task_id = "test-quiz-004"
    questions = [create_mock_quiz_question(1)]  # 简答题
    setup_mock_quiz_data(quiz_task_id, questions)

    mock_analysis = create_mock_analysis("without_answer")
    mock_llm = mock_llm_response(mock_analysis)

    with patch('llm.chains.practice_chain.build_llm', return_value=mock_llm):
        result = await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=0,
            mode="without_answer",
            user_answer=None,
            subject_display="数据结构",
            subject_code="data_structure",
        )

    assert result.mode == "without_answer"
    assert "思路" in result.analysis or "引导" in result.analysis
    # 不应该直接给出答案
    assert result.result is None
    assert result.deep_analysis is None
    logger.log(f"✓ 分析模式: {result.mode}")
    logger.log(f"✓ 提供了引导式分析")
    logger.log(f"✓ 没有直接给出答案")
    logger.log(f"✓ 知识点: {', '.join(result.key_knowledge_points)}")

    logger.log("\n✓ 测试 4 通过\n")


async def test_error_quiz_not_found():
    """测试 5: 错误处理 - Quiz 数据不存在"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 5: 错误处理 - Quiz 数据不存在")
    logger.log("=" * 60)

    try:
        await analyze_quiz_question(
            quiz_task_id="non-existent-task",
            question_index=0,
            mode="with_answer",
        )
        assert False, "应该抛出 QuizNotFoundError"
    except QuizNotFoundError as e:
        logger.log(f"✓ 正确抛出 QuizNotFoundError: {e}")

    logger.log("\n✓ 测试 5 通过\n")


async def test_error_question_index_out_of_range():
    """测试 6: 错误处理 - 题目索引越界"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 6: 错误处理 - 题目索引越界")
    logger.log("=" * 60)

    quiz_task_id = "test-quiz-006"
    questions = [create_mock_quiz_question(0)]
    setup_mock_quiz_data(quiz_task_id, questions)

    try:
        await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=5,  # 越界
            mode="with_answer",
        )
        assert False, "应该抛出 QuestionIndexError"
    except QuestionIndexError as e:
        logger.log(f"✓ 正确抛出 QuestionIndexError: {e}")

    logger.log("\n✓ 测试 6 通过\n")


async def test_multiple_questions():
    """测试 7: 分析多道题中的特定题目"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 7: 分析多道题中的特定题目")
    logger.log("=" * 60)

    quiz_task_id = "test-quiz-007"
    questions = [
        create_mock_quiz_question(0),
        create_mock_quiz_question(1),
        create_mock_quiz_question(2),
    ]
    setup_mock_quiz_data(quiz_task_id, questions)

    # 分析第二题（索引 1）
    mock_analysis = create_mock_analysis("without_answer")
    mock_llm = mock_llm_response(mock_analysis)

    with patch('llm.chains.practice_chain.build_llm', return_value=mock_llm):
        result = await analyze_quiz_question(
            quiz_task_id=quiz_task_id,
            question_index=1,  # 第二题
            mode="without_answer",
            subject_display="数据结构",
            subject_code="data_structure",
        )

    assert result.mode == "without_answer"
    logger.log(f"✓ 成功分析了第 2 题（索引 1）")
    logger.log(f"✓ 知识点包含: {result.key_knowledge_points[0]}")

    logger.log("\n✓ 测试 7 通过\n")


async def test_practice_result_serialization():
    """测试 8: Practice 结果序列化和反序列化"""
    logger.log("\n" + "=" * 60)
    logger.log("测试 8: Practice 结果序列化和反序列化")
    logger.log("=" * 60)

    analysis = create_mock_analysis("with_answer")

    # 序列化
    result_dict = analysis.model_dump()
    result_json = json.dumps(result_dict, ensure_ascii=False)
    logger.log(f"✓ 序列化成功，JSON 长度: {len(result_json)}")

    # 反序列化
    loaded_dict = json.loads(result_json)
    loaded_analysis = PracticeAnalysis(**loaded_dict)
    logger.log(f"✓ 反序列化成功")

    # 验证字段
    assert loaded_analysis.mode == analysis.mode
    assert loaded_analysis.analysis == analysis.analysis
    assert loaded_analysis.key_knowledge_points == analysis.key_knowledge_points
    assert loaded_analysis.difficulty_assessment == analysis.difficulty_assessment
    assert loaded_analysis.phase == analysis.phase
    logger.log(f"✓ 所有字段匹配")

    logger.log("\n✓ 测试 8 通过\n")


async def main():
    """运行所有测试"""
    logger.setup()

    logger.log("\n" + "=" * 60)
    logger.log("Practice Chain 功能测试")
    logger.log("=" * 60)

    tests = [
        test_quiz_storage,
        test_practice_with_answer_correct,
        test_practice_with_answer_wrong,
        test_practice_without_answer,
        test_error_quiz_not_found,
        test_error_question_index_out_of_range,
        test_multiple_questions,
        test_practice_result_serialization,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            failed += 1
            logger.log(f"\n✗ 测试失败: {test.__name__}")
            logger.log(f"  错误: {e}\n")
            import traceback
            logger.log(traceback.format_exc())

    logger.log("\n" + "=" * 60)
    logger.log(f"测试结果: {passed}/{len(tests)} 通过")
    if failed > 0:
        logger.log(f"失败: {failed}")
    logger.log("=" * 60 + "\n")

    logger.close()

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
