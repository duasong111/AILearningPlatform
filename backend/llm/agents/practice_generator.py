"""实践内容生成服务 —— 两阶段 LLM 生成（需求 → 大纲 → 交互 HTML 场景）。

从 resource/practice/src/services/scene-generator.js 移植为 Python。
"""

import json
import logging
import re

from ..config import LLMProvider
from .llm_factory import build_llm

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Stage 1: 大纲生成 Prompt
# ═══════════════════════════════════════════════════════════════

OUTLINE_SYSTEM_PROMPT = """# 交互场景大纲生成器

你是一位专业的课程内容设计师，擅长将用户需求转化为交互式学习场景大纲。

## 核心任务

根据用户的自由文本需求，自动推断课程细节，生成一系列交互场景大纲。
根据需求内容判断每个场景最适合的类型：

- **code（代码实践）**：数据结构、算法、编程练习等需要写代码验证的内容

## 设计原则

- 场景类型统一为 interactive
- 每个场景 1-3 分钟
- 代码实践应包含编程语言、题目描述、初始代码模板、测试用例
- 根据用户需求的语言生成对应语言的内容

## 输出格式

返回单个 JSON 对象，包含两个顶层键：

```json
{
  "languageDirective": "2-5 句描述课程语言行为的指令",
  "outlines": [
    {
      "id": "scene_1",
      "type": "interactive",
      "title": "场景标题",
      "description": "教学目的描述",
      "keyPoints": ["要点1", "要点2"],
      "order": 1,
      "widgetType": "code",
      "widgetOutline": {
        "code": {
          "language": "python",
          "task": "题目描述",
          "starterCode": "def solution():\\n    pass",
          "testCases": [
            {"input": "输入描述", "expected": "预期输出"}
          ]
        }
      }
    }
  ]
}
```

- widgetType 为 code
- widgetOutline 包含 code 对象，内含 language / task / starterCode / testCases
- testCases 至少提供 2 个，覆盖边界情况
- starterCode 提供函数签名和基础框架，不要给出完整实现

**重要**：整个响应必须是一个 JSON 对象，不要用 markdown 代码块包裹，不要添加额外说明。"""

OUTLINE_USER_PROMPT = """请根据以下课程需求生成交互场景大纲：

## 用户需求

{requirement}

## 编程语言

{language}

## 场景数量

{scene_count} 个场景

## 输出要求

- 自动推断课程主题、目标受众、难度
- 每个场景都是代码实践类型（code）
- 提供编程语言、题目描述、初始代码和测试用例
- 输出完整的 JSON 对象"""

# ═══════════════════════════════════════════════════════════════
# Stage 2: 代码实践 HTML 生成 Prompt
# ═══════════════════════════════════════════════════════════════

CODE_SYSTEM_PROMPT = """# 代码实践 Widget 内容生成器

生成一个自包含的 HTML 代码练习页面。学生在这个页面中阅读题目、编写代码、验证结果。

## 通用要求

1. **完整的 HTML5 文档结构**
2. **内嵌 Widget 配置** 在 `<script type="application/json" id="widget-config">` 标签中
3. **代码编辑器**（使用 textarea，等宽字体，带行号提示）
4. **测试用例展示**（输入 / 预期输出）
5. **运行/提交按钮**
6. **结果反馈区域**（通过 / 不通过）
7. **宽屏优先布局**：内容区最大宽度 1100px，充分利用可用空间，不要做成窄窄的手机版面

## 视觉风格（必须遵守）

- **浅色主题**：背景使用白色或浅灰色 (#f8fafc, #f1f5f9)
- 文字颜色使用深色 (#1e293b, #475569)
- 强调色使用蓝色系 (#3b82f6, #2563eb)
- 通过绿色 (#16a34a) 显示正确，红色 (#dc2626) 显示错误
- 卡片/面板使用白色背景 + 轻微阴影
- 代码区域使用深色背景 (#1e293b)，浅色文字 (#e2e8f0)，等宽字体
- 圆角边框，现代简洁风格

## 页面结构

```
┌──────────────────────────────┐
│  📝 题目描述                  │
│  详细的任务说明和背景          │
├──────────────────────────────┤
│  语言标签: Python 3           │
├──────────────────────────────┤
│  ┌────────────────────────┐  │
│  │ 1  def solution():    │  │  ← 代码编辑区
│  │ 2      pass           │  │    深色背景
│  │ 3                     │  │    等宽字体
│  └────────────────────────┘  │
│  [ 运行测试 ]  [ 重置 ]       │
├──────────────────────────────┤
│  测试结果:                    │
│  ✅ 用例1: 通过               │
│  ❌ 用例2: 输入=[1,2] 预期=3  │
├──────────────────────────────┤
│  💡 提示 (可折叠)             │
└──────────────────────────────┘
```

## Widget 配置 Schema

```json
{
  "type": "code",
  "language": "python",
  "task": "实现一个函数，返回两个数的和",
  "testCases": [
    { "input": "a=1, b=2", "expected": "3" },
    { "input": "a=-1, b=1", "expected": "0" }
  ]
}
```

## 交互逻辑

1. 页面加载时，代码编辑区填入初始代码模板
2. 点击「运行测试」时：
   - 对 JavaScript：使用 try/catch + new Function() 执行代码，捕获输出并与预期比较
   - 对 Python/Java/C++：展示预期输出，提示学生自行验证
   - 将代码内容通过 postMessage 发送给父窗口
3. 测试结果用颜色区分（绿色通过 / 红色失败）
4. 提供「显示提示」按钮，点击展开解题思路（初始隐藏）

## postMessage 监听器（必须包含）

```javascript
window.addEventListener('message', function(event) {
  const { type, state } = event.data;
  if (type === 'SET_WIDGET_STATE' && state) {
    if (state.code && document.getElementById('code-editor')) {
      document.getElementById('code-editor').value = state.code;
    }
  }
});

// 提交时向父窗口发送消息
function notifyParent(result) {
  window.parent.postMessage({
    type: 'CODE_SUBMIT',
    code: document.getElementById('code-editor').value,
    language: '{language}',
    result: result,
  }, '*');
}
```

## 关键设计要求

1. **代码编辑器**：textarea 元素，等宽字体 'Fira Code', 'Consolas', monospace，字号 14px，行高 1.6
2. **行号**：使用 CSS counter 或 JS 动态生成行号（左侧灰色数字）
3. **代码高亮**：不需要语法高亮库，使用等宽字体即可（textarea 原生不支持高亮）
4. **按钮状态**：运行中时按钮禁用并显示"运行中…"
5. **触摸友好**：按钮最小 44x44px
6. **测试用例展示**：每个用例用卡片样式，清晰显示输入、预期输出、实际结果
7. **提示区域**：使用 details/summary 标签实现折叠

## 输出格式

只返回 HTML 文档，不要 markdown 代码块，不要解释。"""


# ═══════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════


def generate_practice_outlines(requirement: str, language: str = "python", scene_count: int = 3) -> dict:
    """Stage 1: 从用户需求生成场景大纲。

    Args:
        requirement: 用户需求文本（如"二叉树遍历"）
        language: 编程语言
        scene_count: 期望的场景数量

    Returns:
        {"languageDirective": str, "outlines": [...]}
    """
    llm = build_llm(streaming=False, provider=LLMProvider.MINIMAX)
    user_prompt = OUTLINE_USER_PROMPT.format(
        requirement=requirement,
        language=language,
        scene_count=scene_count,
    )
    response = llm.invoke([
        {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])
    text = response.content if hasattr(response, "content") else str(response)
    parsed = _parse_json_response(text)
    if not parsed or not parsed.get("outlines"):
        raise ValueError(f"大纲生成失败：LLM 返回格式不正确，原文: {text[:300]}")
    return parsed


def generate_scene_html(outline: dict, language_directive: str = "") -> dict:
    """Stage 2: 从场景大纲生成代码实践 HTML。

    Args:
        outline: 场景大纲字典（含 title, description, keyPoints, widgetOutline 等）
        language_directive: Stage 1 返回的语言指令

    Returns:
        {"html": str, "widgetType": "code", "widgetConfig": dict|null}
    """
    llm = build_llm(streaming=False, provider=LLMProvider.MINIMAX)
    code_outline = (outline.get("widgetOutline") or {}).get("code") or {}
    language = code_outline.get("language", "python")
    task = code_outline.get("task") or outline.get("description", "")
    starter_code = code_outline.get("starterCode", "")
    test_cases = code_outline.get("testCases", [])
    key_points = "\n".join(outline.get("keyPoints", []))

    user_prompt = f"""请为以下代码实践场景生成完整的 HTML 页面：

## 场景信息
- 标题: {outline.get("title", "")}
- 描述: {outline.get("description", "")}
- Widget 类型: code
- 编程语言: {language}
- 核心要点:
{key_points}

## 代码大纲
- 题目: {task}
- 初始代码:
```{language}
{starter_code}
```
- 测试用例:
{json.dumps(test_cases, ensure_ascii=False, indent=2)}

## 语言要求
{language_directive or "使用与需求文本相同的语言生成内容。"}

## 视觉风格要求
- 宽屏布局：内容最大宽度 1100px，margin: 0 auto，不要做成手机窄版
- 浅色主题：白色/浅灰背景，深色文字
- 蓝色系强调色 (#3b82f6)
- 代码区深色背景 (#1e293b)，浅色等宽文字
- 通过绿色 (#16a34a)，失败红色 (#dc2626)
- 现代简洁风格，圆角卡片

## 输出要求
返回完整的 HTML 文档（从 <!DOCTYPE html> 开始到 </html> 结束），不要 markdown 代码块。
注意：浏览器无法直接执行 Python 代码。展示测试用例和预期输出，引导学生自行对比验证。同时通过 postMessage 将代码发送给父窗口。"""

    response = llm.invoke([
        {"role": "system", "content": CODE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])
    text = response.content if hasattr(response, "content") else str(response)
    html = _extract_html(text)
    if not html:
        raise ValueError(f"场景「{outline.get('title', '')}」HTML 提取失败")
    widget_config = _extract_widget_config(html)
    return {"html": html, "widgetType": "code", "widgetConfig": widget_config}


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _parse_json_response(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON。"""
    cleaned = text.strip()
    # 剥离推理模型的 <think>...</think> 标记
    think_end = cleaned.rfind("<｜end▁of▁thinking｜>")
    if think_end != -1:
        cleaned = cleaned[think_end + len("<｜end▁of▁thinking｜>"):].strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def _extract_html(text: str) -> str | None:
    """从 LLM 响应中提取 HTML 文档，过滤掉模型输出的前言/后语。"""
    cleaned = text.strip()
    # 1. 尝试提取 markdown 代码块中的内容
    md_match = re.search(r"```(?:html)?\s*\n?(.*?)```", cleaned, re.DOTALL)
    if md_match:
        cleaned = md_match.group(1).strip()
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:html)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    # 2. 从 <!DOCTYPE 或 <html 标签开始提取
    doc_start = cleaned.find("<!DOCTYPE")
    doc_end = cleaned.rfind("</html>")
    if doc_start != -1 and doc_end != -1:
        return cleaned[doc_start:doc_end + 7]
    html_start = cleaned.find("<html")
    if html_start != -1:
        html_end = cleaned.rfind("</html>")
        if html_end != -1:
            return cleaned[html_start:html_end + 7]
    # 3. 兜底：从 <body 或 <script 开始截取，去掉前言
    body_start = cleaned.find("<body")
    script_start = cleaned.find("<script")
    if body_start != -1 or script_start != -1:
        start = body_start if body_start != -1 else script_start
        if script_start != -1 and (body_start == -1 or script_start < body_start):
            start = script_start
        return cleaned[start:]
    return None


def _extract_widget_config(html: str) -> dict | None:
    """从 HTML 中提取 widget 配置。"""
    match = re.search(
        r'<script type="application/json" id="widget-config">([\s\S]*?)</script>',
        html,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None
