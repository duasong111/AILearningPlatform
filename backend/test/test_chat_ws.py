#!/usr/bin/env python3
"""
WebSocket 聊天接口测试 (打字机效果)
用法: python test/test_chat_ws.py [消息内容]
"""
import asyncio
import json
import sys

import requests
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/chat/"
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


def get_or_create_conversation(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/conversations/", headers=headers)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]
    resp = requests.post(f"{BASE_URL}/api/subjects/", headers=headers, json={"name": "data_structure"})
    subject_id = resp.json()["id"]
    resp = requests.post(f"{BASE_URL}/api/conversations/", headers=headers, json={"subject_id": subject_id, "title": "测试对话"})
    return resp.json()["id"]


async def test_chat(token, conversation_id, message):
    url = f"{WS_URL}?token={token}"
    print(f"\n{'='*60}")
    print(f"消息: {message}")
    print(f"{'='*60}\n", flush=True)

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "type": "message",
            "conversation_id": conversation_id,
            "message": message,
        }))

        full_response = ""
        async for raw in ws:
            data = json.loads(raw)
            ev_type = data.get("type")
            if ev_type == "user_message":
                pass
            elif ev_type == "chunk":
                content = data.get("content", "")
                full_response += content
                for char in content:
                    print(char, end="", flush=True)
            elif ev_type == "complete":
                print(f"\n\n{'='*60}")
                print(f"✓ 完成 | 长度: {len(full_response)} 字符")
                return True
            elif ev_type == "error":
                print(f"\n✗ 错误: {data.get('message')}")
                return False
    return True


async def test_auth_fail():
    """无 token 应被拒。Channels 在 connect() 里 close() 而未 accept() 时，
    会在 HTTP 握手阶段返 403 (被 websockets 库抛 InvalidStatus)。"""
    print("\n[负向] 无 token 连接 ...")
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.recv()
            print("✗ 居然连上了，期望被拒绝")
            return False
    except websockets.exceptions.InvalidStatus as e:
        print(f"✓ 握手被拒: {e}")
        return True
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✓ 被 close 拒绝 (code={e.code})")
        return True


async def test_bad_token():
    """错 token 应被拒。"""
    print("\n[负向] 错 token 连接 ...")
    try:
        async with websockets.connect(f"{WS_URL}?token=garbage") as ws:
            await ws.recv()
            print("✗ 居然连上了，期望被拒绝")
            return False
    except websockets.exceptions.InvalidStatus as e:
        print(f"✓ 握手被拒: {e}")
        return True
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"✓ 被 close 拒绝 (code={e.code})")
        return True


async def main():
    message = sys.argv[1] if len(sys.argv) > 1 else "尽可能详细给我解释什么是栈"
    token = login()
    print("✓ 登录成功")

    conv_id = get_or_create_conversation(token)
    print(f"✓ 对话 ID: {conv_id}")

    await test_auth_fail()
    await test_bad_token()
    await test_chat(token, conv_id, message)


if __name__ == "__main__":
    asyncio.run(main())
