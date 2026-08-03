#!/usr/bin/env python3
"""
交互式 terminal 对话脚本 —— 直接在终端和 LangChain agent 对话。

走 WS /ws/profile/build/，完整事件流：
  - 自然语言逐 token 流式输出（打字机效果）
  - 工具调用：get_knowledge_map / assess_and_update_knowledge_score
  - 工具结果
  - 15 轮上限 / is_complete 触发自动保存画像

用法:
  python test/test_interactive.py                          # 默认 data_structure
  python test/test_interactive.py <subject_id>             # 指定学科 id
  python test/test_interactive.py <subject_id> "<开场白>"   # 指定开场白
"""
from __future__ import annotations

import asyncio
import json
import sys

import requests
import websockets

# 强制 UTF-8 输出（Windows GBK 终端会炸 emoji / 中文符号）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/profile/build/"
EMAIL = "test@example.com"
PASSWORD = "testpass123"
MAX_ROUNDS = 15

# ANSI 颜色
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
MAGENTA = "\033[35m"
GRAY = "\033[90m"


def _login() -> str:
    resp = requests.post(f"{BASE_URL}/api/auth/login/",
                         json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"{RED}✗ 登录失败: HTTP {resp.status_code} {resp.text}{RESET}")
        sys.exit(1)
    return resp.json()["access"]


def _get_or_create_subject(token: str, code: str = "data_structure") -> int:
    resp = requests.post(f"{BASE_URL}/api/subjects/", headers=_auth(token), json={"name": code})
    if resp.status_code not in (200, 201):
        print(f"{RED}✗ 创建学科失败: HTTP {resp.status_code} {resp.text}{RESET}")
        sys.exit(1)
    return resp.json()["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _one_round(ws, subject_id: int, message: str, conversation_id: int | None) -> tuple[int | None, dict, bool]:
    """跑一轮：发消息 → 收事件 → 返 (cid, last_event, is_complete)。"""
    payload = {"type": "message", "subject_id": subject_id, "message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    await ws.send(json.dumps(payload))

    cid = None
    last = {}
    full_text = ""
    round_num = 0
    profile = {}
    next_q = None
    is_complete = False
    got_error = False

    try:
        async for raw in ws:
            d = json.loads(raw)
            last = d
            t = d.get("type")

            if t == "start":
                cid = d.get("conversation_id")
                round_num = d.get("round", 0)
                print(f"\n{BOLD}{CYAN}━━━ 第 {round_num}/{d.get('max_rounds', MAX_ROUNDS)} 轮 ━━━{RESET}")
                print(f"{GRAY}conversation_id={cid}  subject_id={d.get('subject_id')}{RESET}\n")

            elif t == "chunk":
                content = d.get("content", "")
                full_text += content
                sys.stdout.write(content)
                sys.stdout.flush()

            elif t == "tool_call":
                args_str = json.dumps(d.get("args", {}), ensure_ascii=False)
                print(f"\n{MAGENTA}🔧 {BOLD}{d.get('name')}{RESET}{MAGENTA}({args_str[:80]}){RESET}", flush=True)

            elif t == "tool_result":
                out = str(d.get("output", ""))
                if len(out) > 200:
                    out = out[:200] + "..."
                print(f"   {GREEN}↳ {d.get('name')} →{RESET} {GRAY}{out}{RESET}", flush=True)

            elif t == "complete":
                print(f"\n\n{GRAY}── 完成 ({len(full_text)} 字符) ──{RESET}", flush=True)

            elif t == "question":
                next_q = d.get("question")
                profile = d.get("profile", {})

            elif t == "saved":
                is_complete = d.get("is_complete", False)
                profile = d.get("profile", {})
                print(f"\n{BOLD}{GREEN}✓ 画像已保存 (is_complete={is_complete}){RESET}")
                if profile:
                    _print_profile_summary(profile)

            elif t == "error":
                print(f"\n{RED}✗ 错误: {d.get('message')}{RESET}", flush=True)
                got_error = True
                break
    except websockets.exceptions.ConnectionClosed:
        if not got_error:
            print(f"\n{RED}✗ 连接被关闭{RESET}")

    return cid, last, is_complete


def _print_profile_summary(profile: dict):
    print(f"{GRAY}{'─'*50}{RESET}")
    print(f"{BOLD}当前画像:{RESET}")
    if profile.get("learning_goal"):
        lg = profile["learning_goal"]
        print(f"  🎯 目标: {lg.get('goal', '?')}  优先级={lg.get('priority', '?')}")
    if profile.get("knowledge_base"):
        kb = profile["knowledge_base"]
        print(f"  📚 知识: level={kb.get('level', '?')}  强项={kb.get('strong_areas', [])}  弱项={kb.get('weak_areas', [])}")
    if profile.get("cognitive_style"):
        cs = profile["cognitive_style"]
        print(f"  🧠 风格: {cs.get('style_type', '?')}  score={cs.get('score', '?')}")
    if profile.get("available_time") is not None:
        print(f"  ⏰ 可用时间: {profile['available_time']} 小时/周")
    if profile.get("interest_direction"):
        print(f"  ❤️  兴趣: {profile['interest_direction']}")
    if profile.get("course"):
        print(f"  📖 推荐课程: {profile['course']}")
    print(f"{GRAY}{'─'*50}{RESET}")


async def interactive_loop(token: str, subject_id: int, opener: str | None):
    """主循环：连 WS，stdin 读消息，回事件流。"""
    conversation_id: int | None = None
    round_count = 0

    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║   AiTeach · 交互式画像构建（WS agent）        ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════╝{RESET}")
    print(f"{GRAY}subject_id={subject_id}  /  输入 'exit' 或 Ctrl+C 退出{RESET}\n")

    async with websockets.connect(f"{WS_URL}?token={token}") as ws:
        # 开场白（可选）：让 agent 先抛一个问题
        if opener:
            print(f"{BOLD}[开场白] 你:{RESET} {opener}\n")
            conversation_id, last, is_complete = await _one_round(ws, subject_id, opener, conversation_id)
            round_count += 1
            if last.get("type") == "error":
                return

        while True:
            try:
                line = input(f"\n{BOLD}{YELLOW}你 ❯{RESET} ")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{GRAY}Bye.{RESET}")
                return

            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q", ":q"):
                print(f"{GRAY}Bye.{RESET}")
                return

            print(f"{BOLD}[你] {line}{RESET}\n", flush=True)
            conversation_id, last, is_complete = await _one_round(ws, subject_id, line, conversation_id)
            round_count += 1

            if is_complete:
                print(f"\n{GREEN}已达 is_complete=true，对话自然结束。{RESET}")
                return

            if round_count >= MAX_ROUNDS:
                print(f"\n{YELLOW}已达 {MAX_ROUNDS} 轮上限。{RESET}")
                return

            # 自动把 agent 的问题复述出来
            next_q = last.get("question")
            if next_q:
                print(f"\n{CYAN}💬 agent 问:{RESET} {next_q}")


def main():
    args = sys.argv[1:]
    token = _login()
    print(f"{GREEN}✓ 登录成功{RESET}")

    if not args:
        subject_id = _get_or_create_subject(token, "data_structure")
        opener = "我想学数据结构"
    else:
        subject_id = int(args[0])
        opener = args[1] if len(args) > 1 else "你好"

    print(f"{GREEN}✓ subject_id={subject_id}{RESET}\n")

    try:
        asyncio.run(interactive_loop(token, subject_id, opener))
    except KeyboardInterrupt:
        print(f"\n{GRAY}Interrupted.{RESET}")


if __name__ == "__main__":
    main()
