import json
import os
from pathlib import Path

import requests


def _load_dotenv():
    p = Path(__file__).resolve().parent / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _get_proxy() -> dict | None:
    """获取代理配置 — 仅在 PROXY_HOST 显式环境变量设了才用代理.

    历史版本会从 /etc/resolv.conf 读 nameserver 当 PROXY_HOST, 这在
    WSL2 里 work (nameserver = 宿主机 IP), 但在 macOS 上会读到家用
    路由器 IP (如 192.168.18.1) + 默认 7890 端口, 而 7890 根本没服务,
    造成 Dify 调用 ConnectTimeout → 前端看到 502.

    修复: 只信任显式 PROXY_HOST, 不再 magic-parse resolv.conf.
    WSL2 用户需要在 .env 设 PROXY_HOST=<host_ip> PROXY_PORT=<port>.
    macOS 正常网络下, 直接连 api.dify.ai, 不走代理.
    """
    host = os.environ.get("PROXY_HOST", "").strip()
    if not host:
        return None
    port = os.environ.get("PROXY_PORT", "7890")
    proxy = f"http://{host}:{port}"
    return {"http": proxy, "https": proxy}


_load_dotenv()


def call_dify_workflow_quiz_generator(
    mcq_count: int,
    qa_count: int,
    search_query: str,
    user_id: str = "user",
):
    """
    调用 Dify 题库生成工作流，生成选择题和问答题。

    参数:
        mcq_count:    选择题数量
        qa_count:     问答题数量
        search_query: 考察范围关键词（如"数据结构"、"计算机网络"、"深度学习"等）
        user_id:      终端用户标识

    返回:
        成功: dict（完整 Dify 响应，outputs 已原始保留）
        失败: None
    """
    api_url = "https://api.dify.ai/v1/workflows/run"
    api_key = os.environ["QUIZ_GENERATOR_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {
            "mcq_count": mcq_count,
            "qa_count": qa_count,
            "search_query": search_query,
        },
        "response_mode": "blocking",
        "user": user_id,
    }
    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=120,
            proxies=_get_proxy(),
        )
        if response.status_code != 200:
            print(f"[quiz_generator] HTTP {response.status_code}: {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"[quiz_generator] 请求异常: {e}")
        return None


if __name__ == "__main__":
    result = call_dify_workflow_quiz_generator(
        mcq_count=3,
        qa_count=2,
        search_query="数据结构",
    )
    if result is None:
        print("调用失败")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
