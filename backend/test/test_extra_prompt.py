#!/usr/bin/env python3
"""
测试 extra_prompt 功能

验证 Conversation.extra_prompt 字段能够正确注入到 agent 系统提示词中
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from users.models import Conversation, Subject, User


def test_extra_prompt_field():
    """测试 extra_prompt 字段"""
    print("=" * 60)
    print("测试 extra_prompt 字段")
    print("=" * 60)

    # 获取一个用户和学科
    user = User.objects.first()
    if not user:
        print("❌ 没有找到用户")
        return False

    subject = Subject.objects.filter(user=user).first()
    if not subject:
        print("❌ 没有找到学科")
        return False

    print(f"\n✅ 使用用户: {user.username}")
    print(f"✅ 使用学科: {subject.name}")

    # 测试 1: 创建不带 extra_prompt 的对话
    conv1 = Conversation.objects.create(
        subject=subject,
        title="测试对话 1",
        agent=Conversation.AGENT_CHAT,
    )
    print(f"\n✅ 创建对话 1 (无 extra_prompt)")
    print(f"   ID: {conv1.id}")
    print(f"   extra_prompt: {repr(conv1.extra_prompt)}")
    assert conv1.extra_prompt is None, "extra_prompt 应该是 None"

    # 测试 2: 创建带 extra_prompt 的对话
    extra_prompt = "请用幽默风趣的语气回答，多使用比喻和例子"
    conv2 = Conversation.objects.create(
        subject=subject,
        title="测试对话 2",
        agent=Conversation.AGENT_CHAT,
        extra_prompt=extra_prompt,
    )
    print(f"\n✅ 创建对话 2 (带 extra_prompt)")
    print(f"   ID: {conv2.id}")
    print(f"   extra_prompt: {repr(conv2.extra_prompt)}")
    assert conv2.extra_prompt == extra_prompt, "extra_prompt 应该匹配"

    # 测试 3: 更新 extra_prompt
    new_prompt = "你是一个严格的技术面试官，问题要深入底层原理"
    conv1.extra_prompt = new_prompt
    conv1.save()
    print(f"\n✅ 更新对话 1 的 extra_prompt")
    print(f"   新值: {repr(conv1.extra_prompt)}")

    # 重新从数据库读取验证
    conv1_reloaded = Conversation.objects.get(id=conv1.id)
    assert conv1_reloaded.extra_prompt == new_prompt, "extra_prompt 应该持久化"
    print(f"✅ 验证 extra_prompt 已持久化")

    # 测试 4: 测试不同 agent 类型
    conv3 = Conversation.objects.create(
        subject=subject,
        title="测试对话 3 (Profile)",
        agent=Conversation.AGENT_PROFILE,
        extra_prompt="重点关注用户的学习目标和时间安排",
    )
    print(f"\n✅ 创建 Profile 对话 (带 extra_prompt)")
    print(f"   ID: {conv3.id}")
    print(f"   agent: {conv3.agent}")
    print(f"   extra_prompt: {repr(conv3.extra_prompt)}")

    # 测试 5: 序列化测试
    from users.serializers import ConversationSerializer
    serializer = ConversationSerializer(conv2)
    data = serializer.data
    print(f"\n✅ 序列化对话 2")
    print(f"   包含 extra_prompt: {'extra_prompt' in data}")
    print(f"   extra_prompt 值: {repr(data.get('extra_prompt'))}")
    assert 'extra_prompt' in data, "序列化结果应该包含 extra_prompt"
    assert data['extra_prompt'] == extra_prompt, "序列化值应该匹配"

    # 清理测试数据
    conv1.delete()
    conv2.delete()
    conv3.delete()
    print(f"\n✅ 清理测试数据")

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


def test_system_prompt_injection():
    """测试 extra_prompt 注入到系统提示词"""
    print("\n" + "=" * 60)
    print("测试系统提示词注入")
    print("=" * 60)

    from llm.agents.chat_agent import build_system_prompt

    # 测试 1: 无 extra_prompt
    prompt1 = build_system_prompt("数据结构", "data_structure")
    print(f"\n✅ 生成系统提示词 (无 extra_prompt)")
    print(f"   长度: {len(prompt1)} 字符")
    print(f"   包含 '额外指令': {'额外指令' in prompt1}")
    assert "额外指令" not in prompt1, "不应该包含额外指令"

    # 测试 2: 有 extra_prompt
    extra = "请用幽默风趣的语气回答"
    prompt2 = build_system_prompt("数据结构", "data_structure", extra)
    print(f"\n✅ 生成系统提示词 (带 extra_prompt)")
    print(f"   长度: {len(prompt2)} 字符")
    print(f"   包含 '额外指令': {'额外指令' in prompt2}")
    print(f"   包含 extra_prompt: {extra in prompt2}")
    assert "额外指令" in prompt2, "应该包含额外指令"
    assert extra in prompt2, "应该包含 extra_prompt 内容"

    # 测试 3: 显示提示词末尾
    print(f"\n✅ 系统提示词末尾 (最后 100 字符):")
    print(f"   ...{prompt2[-100:]}")

    print("\n" + "=" * 60)
    print("✅ 系统提示词注入测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success1 = test_extra_prompt_field()
        success2 = test_system_prompt_injection()

        if success1 and success2:
            print("\n🎉 所有测试通过！extra_prompt 功能正常工作")
            sys.exit(0)
        else:
            print("\n❌ 部分测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
