#!/usr/bin/env python3
"""
测试 plan 选中 ID 通过消息 meta 传递的功能。
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from llm.tasks import _normalize_selected_plan_ids


def test_normalize_selected_plan_ids():
    """测试从消息 meta 中规范化 selected_plan_ids"""
    print("=" * 60)
    print("测试 _normalize_selected_plan_ids 函数")
    print("=" * 60)

    test_cases = [
        # (输入, 期望输出, 描述)
        ({"selected_plan_ids": [1, 2, 3]}, [1, 2, 3], "标准数组"),
        ({"selected_plan_ids": ["1", "2", "3"]}, [1, 2, 3], "字符串数字"),
        ({"selected_plan_ids": [1, "2", "x", 2]}, [1, 2], "过滤非法值并去重"),
        ({}, [], "无 selected_plan_ids"),
        ({"selected_plan_ids": "1,2,3"}, [], "非数组类型"),
        (None, [], "None 值"),
    ]

    passed = 0
    failed = 0

    for input_meta, expected, description in test_cases:
        result = _normalize_selected_plan_ids(input_meta)
        success = result == expected

        if success:
            passed += 1
            print(f"✅ {description}")
            print(f"   输入: {repr(input_meta)}")
            print(f"   输出: {result}")
        else:
            failed += 1
            print(f"❌ {description}")
            print(f"   输入: {repr(input_meta)}")
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
        print()

    print("=" * 60)
    print(f"测试结果: {passed}/{len(test_cases)} 通过")
    if failed > 0:
        print(f"失败: {failed}")
    print("=" * 60)

    return failed == 0


def test_build_system_prompt():
    """测试 build_system_prompt 是否正确处理 selected_plan_ids 和 extra_prompt"""
    from llm.agents.plan_agent import build_system_prompt

    print("\n" + "=" * 60)
    print("测试 build_system_prompt 函数")
    print("=" * 60)

    # 测试 1: 无 extra_prompt
    prompt1 = build_system_prompt("数据结构", "data_structure")
    assert "额外指令" not in prompt1
    assert "用户选中的计划" not in prompt1
    print("✅ 无 extra_prompt 时正常")

    # 测试 2: extra_prompt 无计划 ID
    prompt2 = build_system_prompt("数据结构", "data_structure", extra_prompt="请用简洁的语言回答")
    assert "额外指令" in prompt2
    assert "请用简洁的语言回答" in prompt2
    assert "用户选中的计划" not in prompt2
    print("✅ extra_prompt 无计划 ID 时只添加额外指令")

    # 测试 3: selected_plan_ids 触发编辑指令
    prompt3 = build_system_prompt("数据结构", "data_structure", selected_plan_ids=[1, 2, 3])
    assert "额外指令" not in prompt3
    assert "当前选中的计划 ID: 1, 2, 3" in prompt3
    assert "#1 #2 #3" in prompt3
    assert "get_plan_detail" in prompt3
    print("✅ selected_plan_ids 存在时添加编辑指令")

    print("=" * 60)
    print("build_system_prompt 测试通过")
    print("=" * 60)


if __name__ == "__main__":
    success1 = test_normalize_selected_plan_ids()
    test_build_system_prompt()

    if success1:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)
