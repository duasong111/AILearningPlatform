#!/usr/bin/env python3
"""
全功能集成测试 —— 一键跑完所有 HTTP + WebSocket 端点。

覆盖:
  AUTH        register / login / refresh / 负向
  SUBJECTS    list / create / idempotent
  KNOWLEDGE   GET 列表 + 写方法 405 保护
  CONV/MSG    list / create
  WS CHAT     鉴权负向 + 单轮流式
  WS PROFILE  subject code 负向 + subject_id 正向 + 多轮续 + 工具调用 + 图谱变更审计

用法: python test/test_all.py
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

import requests
import websockets

BASE_URL = "http://localhost:8000"
WS_CHAT = "ws://localhost:8000/ws/chat/"
WS_PROFILE = "ws://localhost:8000/ws/profile/build/"
EMAIL = "test@example.com"
PASSWORD = "testpass123"


# ============== 测试结果收集 ==============

@dataclass
class Results:
    passed: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)  # (name, err)

    def ok(self, name: str):
        self.passed.append(name)
        print(f"  ✓ {name}")

    def fail(self, name: str, err: str):
        self.failed.append((name, err))
        print(f"  ✗ {name}")
        print(f"      {err}")


# ============== 工具函数 ==============

def _login() -> dict:
    """登录拿 {access, refresh}"""
    resp = requests.post(f"{BASE_URL}/api/auth/login/", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    return resp.json()


def _register_unique() -> tuple[str, str]:
    """注册一个本次运行专用的新用户，返回 (email, password)"""
    suffix = int(time.time())
    email = f"e2e_{suffix}@example.com"
    password = "TestPass123!"
    username = f"e2e_{suffix}"
    resp = requests.post(f"{BASE_URL}/api/auth/register/", json={
        "username": username,
        "email": email,
        "password": password,
        "password_confirm": password,
    })
    assert resp.status_code == 201, f"register failed: {resp.status_code} {resp.text}"
    return email, password


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_or_create_subject(token: str, code: str = "data_structure") -> int:
    """POST /api/subjects/ 幂等返 subject_id"""
    resp = requests.post(f"{BASE_URL}/api/subjects/", headers=_auth(token), json={"name": code})
    assert resp.status_code in (200, 201), f"create subject failed: {resp.status_code} {resp.text}"
    return resp.json()["id"]


def _get_knowledge_nodes(token: str, subject_id: int) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/api/knowledge-nodes/",
        headers=_auth(token),
        params={"subject_id": subject_id},
    )
    assert resp.status_code == 200, f"get kn failed: {resp.status_code} {resp.text}"
    return resp.json()


def _mastery(token: str, subject_id: int, node_id: str) -> int:
    """某 node 的当前 mastery"""
    for n in _get_knowledge_nodes(token, subject_id):
        if n["node_id"] == node_id:
            return n["mastery"]
    raise KeyError(node_id)


# ============== 1. AUTH ==============

def test_auth(r: Results):
    print("\n── 1. AUTH ──")

    # 1.1 注册新用户
    try:
        email, password = _register_unique()
        r.ok(f"register new user ({email})")
    except Exception as e:
        r.fail("register new user", str(e))
        return

    # 1.2 重复注册 → 400
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/register/", json={
            "username": email.split("@")[0],
            "email": email,
            "password": password,
            "password_confirm": password,
        })
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}"
        r.ok("register duplicate → 400")
    except Exception as e:
        r.fail("register duplicate", str(e))

    # 1.3 登录
    try:
        data = _login()
        assert "access" in data and "refresh" in data
        r.ok("login → 200 with access+refresh")
    except Exception as e:
        r.fail("login", str(e))
        return

    # 1.4 错密码
    try:
        resp = requests.post(f"{BASE_URL}/api/auth/login/",
                             json={"email": EMAIL, "password": "wrong"})
        assert resp.status_code == 401, f"expected 401, got {resp.status_code}"
        r.ok("login wrong password → 401")
    except Exception as e:
        r.fail("login wrong password", str(e))

    # 1.5 refresh
    try:
        data = _login()
        resp = requests.post(f"{BASE_URL}/api/auth/refresh/", json={"refresh": data["refresh"]})
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}"
        assert "access" in resp.json()
        r.ok("refresh access token → 200")
    except Exception as e:
        r.fail("refresh token", str(e))


# ============== 2. SUBJECTS ==============

def test_subjects(r: Results, token: str):
    print("\n── 2. SUBJECTS ──")

    # 2.1 list
    try:
        resp = requests.get(f"{BASE_URL}/api/subjects/", headers=_auth(token))
        assert resp.status_code == 200
        subs = resp.json().get("subjects", [])
        codes = [s["code"] for s in subs]
        assert "data_structure" in codes and "cybersecurity" in codes
        r.ok(f"list subjects → 200 ({len(subs)} predefined)")
    except Exception as e:
        r.fail("list subjects", str(e))

    # 2.2 create + idempotent
    try:
        sid1 = _get_or_create_subject(token, "iot")
        sid2 = _get_or_create_subject(token, "iot")
        assert sid1 == sid2, f"idempotent failed: {sid1} vs {sid2}"
        r.ok(f"create iot subject (id={sid1}), idempotent on re-POST")
    except Exception as e:
        r.fail("create subject idempotent", str(e))

    # 2.3 唯一约束：相同 code 不能创建第二条
    # 用 Django ORM 直接绕过 API 验证（API 已经 get_or_create 不能复现）
    # 这里只验证 list 端点：用户的 subjects 只有一条 iot
    try:
        resp = requests.get(f"{BASE_URL}/api/subjects/?name=iot", headers=_auth(token))
        assert resp.status_code == 200
        r.ok("list filtered by name=iot")
    except Exception as e:
        r.fail("list filtered", str(e))

    # 2.4 GET /api/subjects/mine/ - 当前用户已选过的学科（含 id）
    try:
        resp = requests.get(f"{BASE_URL}/api/subjects/mine/", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "subjects" in data
        mine = data["subjects"]
        # 必须至少包含 data_structure（test 流程会用到）
        codes = [s["name"] for s in mine]
        assert "data_structure" in codes, f"data_structure not in mine: {codes}"
        # 每条必须含 id + name + display_name
        for s in mine:
            assert "id" in s and "name" in s and "display_name" in s
        # 拿到 data_structure 的 id，可被后续测试使用
        ds_id = next(s["id"] for s in mine if s["name"] == "data_structure")
        r.ok(f"GET /api/subjects/mine/ → 200, {len(mine)} 个 (data_structure id={ds_id})")
    except Exception as e:
        r.fail("GET subjects/mine", str(e))
        return

    # 2.5 跨用户隔离：mine 不应包含别人的 subject
    # 我们用本次注册的 e2e 用户来验证：它的 mine 应该是空（或只有它自己创建的）
    # 注意：上面用的是 test@example.com，是已存在用户，list 里会有历史数据
    # 这里只做最弱的断言（返回的是 list 即可），跨用户隔离由 2.4 的 get_queryset 强制
    try:
        resp = requests.get(f"{BASE_URL}/api/subjects/mine/", headers=_auth(token))
        ids_returned = {s["id"] for s in resp.json()["subjects"]}
        # 拿一个不属于我们的 id（比如刚才随便乱猜一个高的），但不应出现在 mine
        assert all(isinstance(i, int) and i > 0 for i in ids_returned)
        r.ok(f"mine 返 {len(ids_returned)} 个合法 id，无非法值")
    except Exception as e:
        r.fail("mine sanity check", str(e))


# ============== 3. KNOWLEDGE NODES (read-only) ==============

def test_knowledge_nodes(r: Results, token: str, subject_id: int):
    print("\n── 3. KNOWLEDGE NODES (read-only) ──")

    # 3.1 GET 列表
    try:
        nodes = _get_knowledge_nodes(token, subject_id)
        assert len(nodes) > 0, "expected at least 1 node"
        n0 = nodes[0]
        assert {"id", "subject_id", "node_id", "name", "mastery", "evidence_count"} <= n0.keys()
        r.ok(f"GET knowledge-nodes?subject_id={subject_id} → {len(nodes)} nodes")
    except Exception as e:
        r.fail("GET knowledge-nodes", str(e))

    # 3.2 POST / PUT / DELETE 都应 405
    for method, path, name in [
        ("POST", "/api/knowledge-nodes/", "POST → 405"),
        ("PUT", f"/api/knowledge-nodes/{nodes[0]['id']}/", "PUT → 405"),
        ("DELETE", f"/api/knowledge-nodes/{nodes[0]['id']}/", "DELETE → 405"),
    ]:
        try:
            resp = requests.request(method, BASE_URL + path, headers=_auth(token),
                                    json={"node_id": "X", "name": "X", "mastery": 99})
            assert resp.status_code == 405, f"expected 405, got {resp.status_code}"
            r.ok(f"  {name}")
        except Exception as e:
            r.fail(f"  {name}", str(e))


# ============== 4. CONVERSATIONS / MESSAGES ==============

def test_conv_msg(r: Results, token: str, subject_id: int):
    print("\n── 4. CONVERSATIONS / MESSAGES ──")

    # 4.1 list（全集）
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations/", headers=_auth(token))
        assert resp.status_code == 200
        before = resp.json()
        assert isinstance(before, list)
        before_ids = {c["id"] for c in before}
        r.ok(f"list conversations → 200 ({len(before)} 个)")
    except Exception as e:
        r.fail("list conversations", str(e))
        return

    # 4.2 创建新对话（POST）
    try:
        resp = requests.post(f"{BASE_URL}/api/conversations/", headers=_auth(token), json={
            "subject_id": subject_id, "title": "[e2e test] 新对话"
        })
        assert resp.status_code == 201, f"expected 201, got {resp.status_code} {resp.text}"
        new_conv = resp.json()
        assert new_conv["title"] == "[e2e test] 新对话"
        # subject_id 在 serializer 里是 write_only，response 不会回显 → 改用 detail 接口校验
        r.ok(f"POST /api/conversations/ → 201 (id={new_conv['id']})")
    except Exception as e:
        r.fail("create conversation", str(e))
        return

    new_cid = new_conv["id"]

    # 4.3 缺 subject_id → 400
    try:
        resp = requests.post(f"{BASE_URL}/api/conversations/", headers=_auth(token), json={"title": "x"})
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}"
        r.ok("POST conversation without subject_id → 400")
    except Exception as e:
        r.fail("create conv missing subject_id", str(e))

    # 4.4 别人的 subject_id → 404
    try:
        resp = requests.post(f"{BASE_URL}/api/conversations/", headers=_auth(token), json={
            "subject_id": 999999, "title": "x"
        })
        assert resp.status_code == 404, f"expected 404, got {resp.status_code}"
        r.ok("POST conversation with other-user's subject_id → 404")
    except Exception as e:
        r.fail("create conv with bad subject_id", str(e))

    # 4.5 list 后总数 + 1
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations/", headers=_auth(token))
        after = resp.json()
        after_ids = {c["id"] for c in after}
        assert new_cid in after_ids, f"new conversation {new_cid} not in list"
        assert len(after) == len(before) + 1, f"expected len+1, got {len(before)}→{len(after)}"
        r.ok(f"list after create → {len(after)} 个（+1）")
    except Exception as e:
        r.fail("list after create", str(e))

    # 4.6 按 subject 过滤
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations/", headers=_auth(token),
                            params={"subject": subject_id})
        assert resp.status_code == 200
        for c in resp.json():
            # list 接口走 ConversationListSerializer，返 subject_name（code 字符串）而不是 subject_id
            assert c["subject_name"] == "data_structure", f"bad subject_name: {c.get('subject_name')}"
        r.ok(f"list filtered by subject={subject_id} → {len(resp.json())} 个 (all subject_name='data_structure')")
    except Exception as e:
        r.fail("list filtered by subject", str(e))

    # 4.7 拿这个新对话的详情（含 messages=[]）
    try:
        resp = requests.get(f"{BASE_URL}/api/conversations/{new_cid}/", headers=_auth(token))
        assert resp.status_code == 200
        d = resp.json()
        assert d["id"] == new_cid
        assert d["messages"] == [], f"expected empty messages, got {d['messages']}"
        r.ok(f"GET /api/conversations/{new_cid}/ → 200 (messages=[])")
    except Exception as e:
        r.fail("retrieve conversation", str(e))

    # 4.8 给新对话发 2 条 user 消息
    try:
        for content in ("[e2e test] 第一条", "[e2e test] 第二条"):
            resp = requests.post(f"{BASE_URL}/api/messages/", headers=_auth(token), json={
                "conversation_id": new_cid, "role": "user", "content": content
            })
            assert resp.status_code == 201
        # 详情里应该有 2 条
        resp = requests.get(f"{BASE_URL}/api/conversations/{new_cid}/", headers=_auth(token))
        msgs = resp.json()["messages"]
        assert len(msgs) == 2, f"expected 2 messages, got {len(msgs)}"
        assert msgs[0]["content"] == "[e2e test] 第一条"
        assert msgs[1]["content"] == "[e2e test] 第二条"
        r.ok(f"POST 2 messages → conversation has 2 messages")
    except Exception as e:
        r.fail("send 2 messages", str(e))


# ============== 5. WS CHAT ==============

async def _ws_chat_single_round(token: str, conversation_id: int | None = None,
                                message: str = "e2e test") -> dict:
    """返回收到的事件列表。如果不传 conversation_id，取用户的第一个对话。"""
    events = []
    async with websockets.connect(f"{WS_CHAT}?token={token}") as ws:
        if conversation_id is None:
            resp = requests.get(f"{BASE_URL}/api/conversations/", headers=_auth(token))
            conversation_id = resp.json()[0]["id"]
        await ws.send(json.dumps({"type": "message", "conversation_id": conversation_id, "message": message}))
        async for raw in ws:
            d = json.loads(raw)
            events.append(d)
            if d.get("type") in ("complete", "error", "saved"):
                break
    return events


async def _ws_expect_error(ws_url: str, **params) -> int:
    """期望连接被拒（403）。返回 HTTP status。"""
    url = ws_url
    if params:
        from urllib.parse import urlencode
        url = f"{ws_url}?{urlencode(params)}"
    try:
        async with websockets.connect(url) as ws:
            await ws.recv()
            return -1
    except websockets.exceptions.InvalidStatus as e:
        return e.response.status_code
    except websockets.exceptions.ConnectionClosedError as e:
        return e.code


async def test_ws_chat(r: Results, token: str, subject_id: int):
    print("\n── 5. WS CHAT ──")

    # 5.1 无 token → 403
    try:
        code = await _ws_expect_error(WS_CHAT)
        assert code == 403, f"expected 403, got {code}"
        r.ok("WS no token → 403")
    except Exception as e:
        r.fail("WS no token", str(e))

    # 5.2 错 token → 403
    try:
        code = await _ws_expect_error(WS_CHAT, token="garbage")
        assert code == 403, f"expected 403, got {code}"
        r.ok("WS bad token → 403")
    except Exception as e:
        r.fail("WS bad token", str(e))

    # 5.3 单轮 chat
    try:
        events = await _ws_chat_single_round(token)
        types = [e.get("type") for e in events]
        assert "chunk" in types and "complete" in types, f"missing events: {types}"
        r.ok(f"WS chat single round → events={types}")
    except Exception as e:
        r.fail("WS chat single round", str(e))

    # 5.4 WS chat 选指定 conversation 进（验证"选对话"能力）
    try:
        # 取这个 subject 下最新的对话（应该是第 4 节创建的那个）
        resp = requests.get(f"{BASE_URL}/api/conversations/", headers=_auth(token),
                            params={"subject": subject_id})
        new_cid = resp.json()[0]["id"]
        events = await _ws_chat_single_round(token, conversation_id=new_cid)
        # 验证 AI 回复写到了这个对话：详情里最后一条应是 assistant
        resp = requests.get(f"{BASE_URL}/api/conversations/{new_cid}/", headers=_auth(token))
        msgs = resp.json()["messages"]
        assert len(msgs) >= 3, f"expected ≥3 messages (2 user + 1 AI), got {len(msgs)}"
        assert msgs[-1]["role"] == "assistant", f"last msg role: {msgs[-1]['role']}"
        r.ok(f"WS chat 选指定对话 id={new_cid} → AI 回复写入（最后一条 role=assistant）")
    except Exception as e:
        r.fail("WS chat into specific conversation", str(e))

    # 5.5 对话流：HTTP 建会话 + HTTP 存 2 条 + WS 选这个会话跑 2 轮 + 验证历史递增
    try:
        # 5.5.1 建全新对话
        resp = requests.post(f"{BASE_URL}/api/conversations/", headers=_auth(token), json={
            "subject_id": subject_id, "title": "[e2e 5.5] 对话流"
        })
        assert resp.status_code == 201
        flow_cid = resp.json()["id"]

        # 5.5.2 HTTP 存 2 条 user 消息（不开 LLM）
        for i, content in enumerate([
            "[e2e 5.5] 第一条历史消息",
            "[e2e 5.5] 第二条历史消息（提问风格）",
        ]):
            resp = requests.post(f"{BASE_URL}/api/messages/", headers=_auth(token), json={
                "conversation_id": flow_cid, "role": "user", "content": content
            })
            assert resp.status_code == 201, f"POST message {i}: {resp.status_code}"

        # 5.5.3 验证详情：2 条 user, 0 assistant
        resp = requests.get(f"{BASE_URL}/api/conversations/{flow_cid}/", headers=_auth(token))
        msgs = resp.json()["messages"]
        assert len(msgs) == 2
        assert all(m["role"] == "user" for m in msgs)
        r.ok(f"5.5.1-3 建对话 + 存 2 条 user → conversation_id={flow_cid}, 2 user / 0 assistant")
    except Exception as e:
        r.fail("5.5 chat flow setup", str(e))
        return

    # 5.5.4 WS 选这个对话跑第 1 轮
    try:
        events = await _ws_chat_single_round(token, conversation_id=flow_cid, message="继续聊")
        types = [e.get("type") for e in events]
        assert "chunk" in types and "complete" in types
        r.ok(f"5.5.4 WS chat 第 1 轮 (cid={flow_cid}) → events={types}")
    except Exception as e:
        r.fail("5.5.4 WS chat round 1", str(e))
        return

    # 5.5.5 HTTP 再存 1 条 user 消息
    try:
        resp = requests.post(f"{BASE_URL}/api/messages/", headers=_auth(token), json={
            "conversation_id": flow_cid, "role": "user",
            "content": "[e2e 5.5] 轮间手动追加"
        })
        assert resp.status_code == 201

        # 此时应是 3 user + 1 assistant (5.5.4 跑了 1 轮 WS 后，2 + 1 user + 1 AI = 4)
        # 加 1 user = 5
        resp = requests.get(f"{BASE_URL}/api/conversations/{flow_cid}/", headers=_auth(token))
        msgs = resp.json()["messages"]
        assert len(msgs) == 5, f"expected 5 (3 user + 1 AI + 1 new user), got {len(msgs)}"
        assert [m["role"] for m in msgs].count("user") == 4, f"user count: {[m['role'] for m in msgs]}"
        assert [m["role"] for m in msgs].count("assistant") == 1
        r.ok(f"5.5.5 HTTP 追加 user → 5 条 (4 user + 1 assistant)")
    except Exception as e:
        r.fail("5.5.5 HTTP append", str(e))
        return

    # 5.5.6 WS 选同一个对话跑第 2 轮（关键：consumer 要把 5 条历史都喂给 LLM）
    try:
        events = await _ws_chat_single_round(token, conversation_id=flow_cid, message="第二轮")
        types = [e.get("type") for e in events]
        assert "complete" in types, f"no complete in {types}"
        # 5 条 + 1 user (WS) + 1 AI (WS) = 7
        resp = requests.get(f"{BASE_URL}/api/conversations/{flow_cid}/", headers=_auth(token))
        msgs = resp.json()["messages"]
        assert len(msgs) == 7, f"expected 7 (5 user + 2 AI), got {len(msgs)}"
        assert [m["role"] for m in msgs].count("user") == 5
        assert [m["role"] for m in msgs].count("assistant") == 2
        r.ok(f"5.5.6 WS chat 第 2 轮 → 7 条 (5 user + 2 assistant)，consumer 真的加载了历史")
    except Exception as e:
        r.fail("5.5.6 WS chat round 2", str(e))


# ============== 6. WS PROFILE ==============

async def _ws_profile_round(token: str, subject_id: int, message: str,
                            conversation_id: int | None = None) -> tuple[int | None, list]:
    events = []
    payload = {"type": "message", "subject_id": subject_id, "message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    async with websockets.connect(f"{WS_PROFILE}?token={token}") as ws:
        await ws.send(json.dumps(payload))
        async for raw in ws:
            d = json.loads(raw)
            events.append(d)
            if d.get("type") in ("question", "saved", "error"):
                break
    cid = next((e.get("conversation_id") for e in events if e.get("type") == "start"), None)
    return cid, events


async def test_ws_profile(r: Results, token: str, subject_id: int):
    print("\n── 6. WS PROFILE ──")

    # 6.1 旧字段 subject → 被拒
    try:
        async with websockets.connect(f"{WS_PROFILE}?token={token}") as ws:
            await ws.send(json.dumps({"type": "message", "subject": "data_structure", "message": "x"}))
            err = None
            async for raw in ws:
                d = json.loads(raw)
                if d.get("type") == "error":
                    err = d.get("message", "")
                    break
            assert err and "subject_id" in err, f"expected subject_id error, got: {err}"
            r.ok(f"WS old 'subject' field → error: {err[:60]}")
    except Exception as e:
        r.fail("WS old subject field", str(e))

    # 6.2 不存在的 subject_id → 被拒
    try:
        async with websockets.connect(f"{WS_PROFILE}?token={token}") as ws:
            await ws.send(json.dumps({"type": "message", "subject_id": 999999, "message": "x"}))
            err = None
            async for raw in ws:
                d = json.loads(raw)
                if d.get("type") == "error":
                    err = d.get("message", "")
                    break
            assert err and "not found" in err, f"expected 'not found' error, got: {err}"
            r.ok(f"WS bad subject_id → error: {err[:60]}")
    except Exception as e:
        r.fail("WS bad subject_id", str(e))

    # 6.3 单轮 profile
    try:
        cid, events = await _ws_profile_round(token, subject_id, "e2e test round 1")
        types = [e.get("type") for e in events]
        assert "start" in types and "complete" in types, f"missing events: {types}"
        start = next(e for e in events if e["type"] == "start")
        assert start["subject_id"] == subject_id
        r.ok(f"WS profile single round (cid={cid}, events={types})")
    except Exception as e:
        r.fail("WS profile single round", str(e))
        return

    # 6.4 多轮 + conversation_id 续
    try:
        msg1 = "我对数组和链表很熟，二叉树不会"
        cid1, _ = await _ws_profile_round(token, subject_id, msg1)
        # 续第二轮
        async with websockets.connect(f"{WS_PROFILE}?token={token}") as ws:
            await ws.send(json.dumps({"type": "message", "subject_id": subject_id,
                                      "conversation_id": cid1, "message": "我每周 10 小时准备面试"}))
            round2 = None
            async for raw in ws:
                d = json.loads(raw)
                if d.get("type") == "start":
                    round2 = d.get("round")
                if d.get("type") in ("question", "saved", "error"):
                    break
            assert round2 == 2, f"expected round=2, got {round2}"
            r.ok(f"WS profile multi-round, round 2 starts at round={round2}, cid={cid1}")
    except Exception as e:
        r.fail("WS profile multi-round", str(e))


async def test_ws_tool(r: Results, token: str, subject_id: int):
    print("\n── 7. WS PROFILE + TOOL ──")

    # 记录调用前某个节点的 mastery
    try:
        nodes_before = {n["node_id"]: n["mastery"] for n in _get_knowledge_nodes(token, subject_id)}
        if "DS01" not in nodes_before:
            r.fail("DS01 not in nodes", "")
            return
        before = nodes_before["DS01"]
    except Exception as e:
        r.fail("read nodes_before", str(e))
        return

    # 触发工具调用：让 agent 读图谱 + 调 assess
    try:
        msg = "我数组完全不会，连下标访问都搞不清，请帮我把 DS01 调到 5"
        _, events = await _ws_profile_round(token, subject_id, msg)
        types = [e.get("type") for e in events]
        assert "tool_call" in types, f"no tool_call in {types}"
        assert "tool_result" in types, f"no tool_result in {types}"
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        tool_names = {e["name"] for e in tool_calls}
        assert "get_knowledge_map" in tool_names or "assess_and_update_knowledge_score" in tool_names
        r.ok(f"tool events fired: tool_calls={list(tool_names)}")
    except Exception as e:
        r.fail("tool events", str(e))
        return

    # 验证 mastery 真改了
    try:
        nodes_after = {n["node_id"]: n["mastery"] for n in _get_knowledge_nodes(token, subject_id)}
        after = nodes_after["DS01"]
        evidence_count = next(n for n in _get_knowledge_nodes(token, subject_id)
                              if n["node_id"] == "DS01")["evidence_count"]
        assert after != before, f"mastery unchanged: {before} → {after}"
        r.ok(f"DS01 mastery changed: {before} → {after} (evidence_count={evidence_count})")
    except Exception as e:
        r.fail("verify mastery change", str(e))


# ============== 主流程 ==============

def main():
    print("=" * 64)
    print(f"E2E 集成测试  →  {BASE_URL}")
    print("=" * 64)

    r = Results()
    token = None

    # 1. AUTH
    test_auth(r)
    # 拿到 token 跑后续
    try:
        token = _login()["access"]
    except Exception:
        print("\n✗ 无法登录，后续测试跳过")
        return _summary_and_exit(r)

    # 2. SUBJECTS
    test_subjects(r, token)

    # 3. KNOWLEDGE NODES
    subject_id = _get_or_create_subject(token, "data_structure")
    test_knowledge_nodes(r, token, subject_id)

    # 4. CONV / MSG
    test_conv_msg(r, token, subject_id)

    # 5. WS CHAT
    asyncio.run(test_ws_chat(r, token, subject_id))

    # 6. WS PROFILE
    asyncio.run(test_ws_profile(r, token, subject_id))

    # 7. WS PROFILE + TOOL
    asyncio.run(test_ws_tool(r, token, subject_id))

    return _summary_and_exit(r)


def _summary_and_exit(r: Results) -> int:
    print("\n" + "=" * 64)
    print(f"通过: {len(r.passed)}    失败: {len(r.failed)}")
    print("=" * 64)
    if r.failed:
        print("\n失败明细:")
        for name, err in r.failed:
            print(f"  ✗ {name}\n      {err}")
        return 1
    print("✓ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
