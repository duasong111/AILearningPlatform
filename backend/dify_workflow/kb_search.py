import ast
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
    host = os.environ.get("PROXY_HOST", "").strip()
    if not host:
        try:
            for line in Path("/etc/resolv.conf").read_text().splitlines():
                if line.startswith("nameserver"):
                    host = line.split()[1]
                    break
        except Exception:
            pass
    if not host:
        return None
    port = os.environ.get("PROXY_PORT", "7890")
    proxy = f"http://{host}:{port}"
    return {"http": proxy, "https": proxy}


_load_dotenv()


def call_dify_workflow_kb_search(query, user_id="user", input_var="query"):
    """
    调用 Dify 工作流,从知识库中检索 top 3 候选片段。

    参数:
        query:     用户的问题文本
        user_id:   终端用户标识(应用内唯一)
        input_var: 工作流 Start 节点定义的输入变量名,默认 "query"
                   按你工作流实际变量名调整(如 "question" / "q" 等)

    返回:
        成功: dict (整个 Dify 响应,outputs.* 中的字符串已自动解析)
        失败: None
    """
    api_url = "https://api.dify.ai/v1/workflows/run"
    api_key = os.environ["KB_SEARCH_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {input_var: query},
        "response_mode": "blocking",
        "user": user_id,
    }
    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=60,
            proxies=_get_proxy(),
        )
        if response.status_code != 200:
            return None
        result = response.json()
        # 把 outputs.* 中字符串形式的 list/dict 还原
        outputs = result.get("data", {}).get("outputs", {})
        for k, v in list(outputs.items()):
            if isinstance(v, str):
                try:
                    outputs[k] = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    pass
        return result
    except Exception:
        return None


if __name__ == "__main__":
    result = call_dify_workflow_kb_search("什么是进程")
    if result is None:
        print("调用失败")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
