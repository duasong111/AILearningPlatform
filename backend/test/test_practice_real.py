#!/usr/bin/env python3
"""
Practice Chain 真实数据测试

使用真实数据库 + 真实 LLM 调用，端到端验证：
1. Quiz Chain 生成真实题目
2. Practice Chain 分析题目（with_answer / without_answer）
3. 结果保存到 Redis 并可读取

运行：
    cd backend
    python test/test_practice_real.py
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from asgiref.sync import sync_to_async
from django.core.cache import cache

from llm.chains.practice_chain import analyze_quiz_question
from llm.chains.quiz_chain import (
    QUIZ_TTL_SEC,
    agenerate_quiz,
    quiz_result_key,
    quiz_state_key,
)

# 包装同步 DB 操作为 async
async def async_cache_set(key, value, timeout):
    await sync_to_async(cache.set)(key, value, timeout)

async def async_cache_get(key):
    return await sync_to_async(cache.get)(key)


class Logger:
    def __init__(self):
        self.log_file = None
        self.log_path = None

    def setup(self):
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_path = os.path.join(log_dir, f'test_practice_real_{ts}.log')
        self.log_file = open(self.log_path, 'w', encoding='utf-8')

    def log(self, msg=''):
        print(msg)
        if self.log_file:
            self.log_file.write(msg + '\n')
            self.log_file.flush()

    def close(self):
        if self.log_file:
            self.log_file.close()
            print(f"\n📝 日志已保存: {self.log_path}")


log = Logger()


async def store_quiz_in_cache(task_id: str, questions: list) -> None:
    """将题目存入缓存，模拟 quiz task 完成后的状态。"""
    result = [q.model_dump() for q in questions]
    await async_cache_set(quiz_state_key(task_id), "complete", QUIZ_TTL_SEC)
    await async_cache_set(quiz_result_key(task_id), json.dumps(result, ensure_ascii=False), QUIZ_TTL_SEC)


async def step1_generate_quiz(subject_id: int) -> tuple[str, list]:
    """Step 1: 调用 Quiz Chain 生成真实题目"""
    log.log("\n" + "=" * 70)
    log.log("Step 1: Quiz Chain 生成真实题目")
    log.log("=" * 70)

    log.log(f"\n📚 subject_id = {subject_id}")
    log.log("⏳ 正在调用 LLM 生成题目（约 15-30 秒）...")

    questions = await agenerate_quiz(
        subject_id=subject_id,
        extra_prompt="侧重基础概念，难度适中",
        count=3,
    )

    quiz_task_id = str(uuid.uuid4())[:8]
    await store_quiz_in_cache(quiz_task_id, questions)

    log.log(f"\n✅ 生成 {len(questions)} 道题目，quiz_task_id = {quiz_task_id}")

    for i, q in enumerate(questions):
        log.log(f"\n{'─' * 50}")
        log.log(f"题目 {i + 1} [{q.question_type}] [{q.difficulty}]")
        log.log(f"知识点: {q.knowledge_node_name} ({q.knowledge_node_id})")
        log.log(f"题目: {q.question_text}")
        if q.options:
            for opt in q.options:
                log.log(f"  {opt}")
        log.log(f"正确答案: {q.correct_answer}")
        log.log(f"解析: {q.explanation}")

    return quiz_task_id, questions


async def step2_analysis_with_answer(quiz_task_id: str, questions: list) -> None:
    """Step 2: with_answer 模式 - 模拟用户回答错误"""
    log.log("\n" + "=" * 70)
    log.log("Step 2: Practice Chain — with_answer 模式（模拟用户答错）")
    log.log("=" * 70)

    # 选第一道题，故意给一个错误答案
    q = questions[0]
    if q.question_type == "choice" and q.options:
        # 选一个不是正确答案的选项
        wrong_answer = q.options[0] if q.correct_answer not in q.options[0] else q.options[1]
    else:
        wrong_answer = "我不太确定，可能是 O(1)？"

    log.log(f"\n📝 题目: {q.question_text}")
    log.log(f"🙋 用户回答: {wrong_answer}")
    log.log(f"✅ 正确答案: {q.correct_answer}")
    log.log("⏳ 正在调用 LLM 分析（约 10-20 秒）...")

    result = await analyze_quiz_question(
        quiz_task_id=quiz_task_id,
        question_index=0,
        mode="with_answer",
        user_answer=wrong_answer,
        subject_display="数据结构",
        subject_code="data_structure",
    )

    log.log(f"\n{'─' * 50}")
    log.log("📊 分析结果")
    log.log(f"{'─' * 50}")
    log.log(f"模式: {result.mode}")
    log.log(f"难度评估: {result.difficulty_assessment}")
    log.log(f"知识点: {', '.join(result.key_knowledge_points)}")
    log.log(f"\n💬 分析内容:\n")
    log.log(result.analysis)


async def step3_analysis_without_answer(quiz_task_id: str, questions: list) -> None:
    """Step 3: without_answer 模式 - 引导式分析"""
    log.log("\n" + "=" * 70)
    log.log("Step 3: Practice Chain — without_answer 模式（引导式分析）")
    log.log("=" * 70)

    # 选第二道题（如果有的话）
    idx = min(1, len(questions) - 1)
    q = questions[idx]

    log.log(f"\n📝 题目: {q.question_text}")
    if q.options:
        for opt in q.options:
            log.log(f"  {opt}")
    log.log("（不告诉用户答案）")
    log.log("⏳ 正在调用 LLM 生成引导分析（约 10-20 秒）...")

    result = await analyze_quiz_question(
        quiz_task_id=quiz_task_id,
        question_index=idx,
        mode="without_answer",
        user_answer=None,
        subject_display="数据结构",
        subject_code="data_structure",
    )

    log.log(f"\n{'─' * 50}")
    log.log("📊 引导分析结果")
    log.log(f"{'─' * 50}")
    log.log(f"模式: {result.mode}")
    log.log(f"难度评估: {result.difficulty_assessment}")
    log.log(f"知识点: {', '.join(result.key_knowledge_points)}")
    log.log(f"\n💬 引导内容:\n")
    log.log(result.analysis)


async def step4_analysis_correct_answer(quiz_task_id: str, questions: list) -> None:
    """Step 4: with_answer 模式 - 模拟用户回答正确"""
    log.log("\n" + "=" * 70)
    log.log("Step 4: Practice Chain — with_answer 模式（模拟用户答对）")
    log.log("=" * 70)

    # 选最后一道题
    idx = len(questions) - 1
    q = questions[idx]
    correct_answer = q.correct_answer

    log.log(f"\n📝 题目: {q.question_text}")
    log.log(f"🙋 用户回答: {correct_answer}（正确）")
    log.log("⏳ 正在调用 LLM 分析（约 10-20 秒）...")

    result = await analyze_quiz_question(
        quiz_task_id=quiz_task_id,
        question_index=idx,
        mode="with_answer",
        user_answer=correct_answer,
        subject_display="数据结构",
        subject_code="data_structure",
    )

    log.log(f"\n{'─' * 50}")
    log.log("📊 分析结果")
    log.log(f"{'─' * 50}")
    log.log(f"模式: {result.mode}")
    log.log(f"难度评估: {result.difficulty_assessment}")
    log.log(f"知识点: {', '.join(result.key_knowledge_points)}")
    log.log(f"\n💬 分析内容:\n")
    log.log(result.analysis)


async def main():
    log.setup()

    log.log("\n" + "=" * 70)
    log.log("Practice Chain 真实数据端到端测试")
    log.log("=" * 70)

    SUBJECT_ID = 2  # duasong 的数据结构，53 个知识点

    try:
        # Step 1: 生成题目
        quiz_task_id, questions = await step1_generate_quiz(SUBJECT_ID)

        # Step 2: with_answer + 用户答错
        await step2_analysis_with_answer(quiz_task_id, questions)

        # Step 3: without_answer 引导式分析
        await step3_analysis_without_answer(quiz_task_id, questions)

        # Step 4: with_answer + 用户答对
        await step4_analysis_correct_answer(quiz_task_id, questions)

        log.log("\n" + "=" * 70)
        log.log("✅ 全部测试完成")
        log.log("=" * 70)

    except Exception as e:
        log.log(f"\n❌ 测试失败: {e}")
        import traceback
        log.log(traceback.format_exc())

    log.close()


if __name__ == "__main__":
    asyncio.run(main())
