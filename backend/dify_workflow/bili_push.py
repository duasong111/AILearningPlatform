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


def call_dify_workflow_resource(knowledgePoints, user_id="user"):
    """
    调用 Dify 工作流
    返回: dict (已自动把 outputs.text 的字符串形式的 list/dict 二次解析)
    失败: None
    """
    api_url = "https://api.dify.ai/v1/workflows/run"
    api_key = os.environ["BILI_PUSH_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": {"knowledgePoints": knowledgePoints},
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
            import logging
            logging.getLogger(__name__).error("bili_push HTTP %s: %s", response.status_code, response.text[:500])
            return None
        result = response.json()
        # 自动把 outputs.text 的 str 还原成 list/dict
        text_str = result.get("data", {}).get("outputs", {}).get("text", "")
        if isinstance(text_str, str):
            try:
                result["data"]["outputs"]["text"] = ast.literal_eval(text_str)
            except (ValueError, SyntaxError):
                pass
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("bili_push 异常: %s", e)
        return None


if __name__ == "__main__":
    result = call_dify_workflow_resource("java,css")
    if result is None:
        print("调用失败")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
