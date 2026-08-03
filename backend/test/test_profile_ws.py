#!/usr/bin/env python3
"""
WebSocket 用户画像构建接口测试（LangChain agent + 工具）

Usage:
  python test/test_profile_ws.py                              # 默认：自动找 data_structure subject_id，单轮
  python test/test_profile_ws.py <subject_id>                # 指定 subject_id，单轮
  python test/test_profile_ws.py <subject_id> "<消息>"         # 指定 subject_id + 消息
  python test/test_profile_ws.py --multi <subject_id> <轮数>   # 多轮
  python test/test_profile_ws.py --tool <subject_id> "[消息]"  # 强制工具调用
"""
import asyncio
import json
import sys

import requests
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/profile/build/"
EMAIL = "test@example.com"
PASSWORD = "testpass123"


def login():
    resp = requests.post(f"{BASE_URL}/api/auth/login/", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code == 200:
        return resp.json()["access"]
    requests.post(f"{BASE_URL}/api/auth/register/", json={
        "username": "test_user", "email": EMAIL, "password": PASSWORD, "password_confirm": PASSWORD
    })
    resp = requests.post(f"{BASE_URL}/api/auth/login/", json={"email": EMAIL, "password": PASSWORD})
    return resp.json()["access"]


def get_subject_id(token, code: str = "data_structure") -> int:
    """取当前用户的 subject_id（不存在则创建）。"""
    headers = {"Authorization": f"Bearer {token}"}
    # 先看知识图谱里的 subject_id（也能间接推断：查 subject 列表）
    resp = requests.get(f"{BASE_URL}/api/subjects/", headers=headers)
    if resp.status_code == 200:
        # list() 接口返回预定义全表，不是用户的 —— 这里我们直接 POST 创建（get_or_create）
        pass
    # POST /api/subjects/ 内部 get_or_create，幂等
    resp = requests.post(f"{BASE_URL}/api/subjects/", headers=headers, json={"name": code})
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"create subject failed: {resp.status_code} {resp.text}")
    return resp.json()["id"]


async def _one_round(token: str, subject_id: int, message: str,
                     conversation_id: int | None = None,
                     label: str = "") -> tuple[int | None, dict]:
    """跑一轮。返回 (next_conversation_id, last_event_dict)。"""
    url = f"{WS_URL}?token={token}"
    if label:
        print(f"\n{'='*60}\n{label}\n{'='*60}\n", flush=True)
    print(f"消息: {message}\n", flush=True)

    payload = {"type": "message", "subject_id": subject_id, "message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    full_response = ""
    last = {}
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(payload))
        async for raw in ws:
            data = json.loads(raw)
            last = data
            t = data.get("type")

            if t == "start":
                cid = data.get("conversation_id")
                print(f"[开始] {data.get('message')} (conversation_id={cid}, subject_id={data.get('subject_id')})")
                print(f"轮次: {data.get('round')}/{data.get('max_rounds')}\n", flush=True)

            elif t == "chunk":
                content = data.get("content", "")
                full_response += content
                for ch in content:
                    print(ch, end="", flush=True)

            elif t == "tool_call":
                print(f"\n[🔧 工具调用] {data.get('name')}({json.dumps(data.get('args'), ensure_ascii=False)})", flush=True)

            elif t == "tool_result":
                out = data.get("output", "")
                if len(out) > 200:
                    out = out[:200] + "..."
                print(f"[📥 工具结果] {data.get('name')} → {out}", flush=True)

            elif t == "complete":
                print(f"\n\n[完成] 响应长度: {len(full_response)} 字符", flush=True)

            elif t == "question":
                print(f"\n{'='*60}")
                print(f"[下一问题] {data.get('question')}")
                print(f"{'='*60}", flush=True)
                return last.get("conversation_id") or conversation_id, data

            elif t == "saved":
                print(f"\n[画像已保存] is_complete={data.get('is_complete')}", flush=True)
                if data.get("profile"):
                    print(json.dumps(data["profile"], ensure_ascii=False, indent=2)[:500])
                return last.get("conversation_id") or conversation_id, data

            elif t == "error":
                print(f"\n✗ 错误: {data.get('message')}", flush=True)
                return conversation_id, data

    return conversation_id, last


async def single_round(token, subject_id, message):
    await _one_round(token, subject_id, message, label="[单轮测试]")


async def multi_round(token, subject_id, rounds, message):
    """多轮：每轮结束后取 next_question，自动接着回答。"""
    conversation_id = None
    current_msg = message
    for i in range(rounds):
        cid, last = await _one_round(token, subject_id, current_msg, conversation_id,
                                     label=f"[第 {i+1}/{rounds} 轮]")
        if cid:
            conversation_id = cid
        if last.get("type") in ("saved", "error"):
            return
        if not last.get("question"):
            return
        current_msg = (
            "我每周大约能花 10 小时学习，主要想通过面试拿到 offer。"
            "我已经有 C++ 基础，会数组和链表，但二叉树比较薄弱。"
        )
        print(f"\n[自动回答] {current_msg}", flush=True)
    print(f"\n{'='*60}\n✓ {rounds} 轮完成，conversation_id={conversation_id}\n{'='*60}")


async def tool_trigger(token, subject_id, message):
    """第一轮：直接要求 agent 读知识图谱并改分数，验证 tool_call/tool_result 事件。"""
    cid, last = await _one_round(token, subject_id, message, label="[Tool 触发测试]")
    if last.get("type") == "error":
        return
    print(f"\n{'='*60}\n✓ 工具触发测试完成 (conversation_id={cid})\n{'='*60}")


async def main():
    args = sys.argv[1:]
    token = login()
    print("✓ 登录成功")

    if not args:
        subject_id = get_subject_id(token, "data_structure")
        print(f"✓ subject_id = {subject_id} (data_structure)")
        await single_round(token, subject_id, "我想学数据结构，为了面试")
        return

    if args[0] == "--multi":
        subject_id = int(args[1])
        rounds = int(args[2])
        message = args[3] if len(args) > 3 else "我想学数据结构，为了面试"
        await multi_round(token, subject_id, rounds, message)
    elif args[0] == "--tool":
        subject_id = int(args[1])
        message = " ".join(args[2:]) or (
            "我已经会数组和链表了，请帮我把知识图谱里这两个节点的分调到 60，二叉树调到 20"
        )
        await tool_trigger(token, subject_id, message)
    else:
        subject_id = int(args[0])
        message = " ".join(args[1:]) if len(args) > 1 else "我想学数据结构，为了面试"
        await single_round(token, subject_id, message)


if __name__ == "__main__":
    asyncio.run(main())
