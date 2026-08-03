"""图文文档生成服务 —— 两阶段 LLM 生成（主题 → 大纲 → 带 SVG 图解的 HTML 文档）。

独立于 practice_generator.py，专门生成图文并茂的知识文档。
"""

import json
import logging
import re

from ..config import LLMProvider
from .llm_factory import build_llm

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Stage 1: 文档大纲生成 Prompt
# ═══════════════════════════════════════════════════════════════

OUTLINE_SYSTEM_PROMPT = """# 图文文档大纲生成器

你是一位专业的技术文档作者，擅长将知识点组织为图文并茂的学习文档。

## 核心任务

根据用户指定的主题，自动推断知识结构，生成一系列章节大纲。
每个章节需要指定适合的图解类型：

- **flowchart（流程图）**：步骤、流程、决策分支
- **mindmap（思维导图）**：知识结构、分类体系
- **comparison（对比图）**：两个概念的并排比较
- **timeline（时间线）**：发展历程、事件序列
- **architecture（架构图）**：系统结构、组件关系
- **data-structure（数据结构图）**：数组、链表、树、图等结构
- **process（步骤图）**：操作步骤、工序流程
- **tree（树形图）**：分层结构、继承关系

## 设计原则

- 每个章节 2-5 分钟阅读量
- 图文比例约 4:6（文字说明 40%，图解 60%）
- 图解要能直观传达核心概念
- 章节从浅入深，先概念后应用
- 根据用户需求的语言生成对应语言的内容

## 输出格式

返回单个 JSON 对象：

```json
{
  "languageDirective": "2-5 句描述文档语言和风格的指令",
  "title": "文档标题",
  "sections": [
    {
      "id": "sec_1",
      "title": "章节标题",
      "description": "本章要讲什么，1-2句",
      "keyPoints": ["要点1", "要点2", "要点3"],
      "diagramType": "flowchart",
      "diagramPrompt": "流程图的主题和关键元素描述"
    }
  ]
}
```

**重要**：整个响应必须是一个 JSON 对象，不要用 markdown 代码块包裹，不要添加额外说明。"""

OUTLINE_USER_PROMPT = """请根据以下主题生成图文文档大纲：

## 主题

{topic}

## 编程语言（如适用）

{language}

## 章节数量

{section_count} 个章节

## 输出要求

- 自动推断知识结构的难度和受众
- 每个章节选择合适的图解类型
- diagramPrompt 是对图解内容的简要描述，供 Stage 2 生成 SVG 时使用
- 输出完整的 JSON 对象"""

# ═══════════════════════════════════════════════════════════════
# Stage 2: 图文 HTML 生成 Prompt
# ═══════════════════════════════════════════════════════════════

ILLUSTRATED_SYSTEM_PROMPT = """# 图文文档章节生成器

生成一个自包含的 HTML 文档章节，包含文字讲解和精美的 SVG 图解。学生通过阅读文字 + 查看图解来理解知识点。

## 通用要求

1. **完整的 HTML5 文档结构**
2. **文字讲解**（正文段落，清晰易读）
3. **内嵌 SVG 图解**（直接写在 HTML 中，不使用外部资源）
4. **移动端响应式设计**

## 视觉风格（必须遵守）

- **宽屏布局**：内容最大宽度 1100px，margin: 0 auto，不要做成手机窄版
- **浅色主题**：白色/浅灰背景（#f8fafc, #ffffff）
- 标题使用深色（#1e293b），正文使用深灰（#334155, #475569）
- 强调色使用蓝色系（#3b82f6, #2563eb）
- SVG 图解使用柔和的配色（蓝色 #3b82f6、绿色 #10b981、橙色 #f59e0b、紫色 #8b5cf6）
- 卡片/面板使用白色背景 + 轻微阴影（box-shadow: 0 1px 3px rgba(0,0,0,0.08)）
- 圆角边框（border-radius: 12px），现代简洁风格
- 字体：系统默认中文字体栈（-apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif）

## 页面结构

```
┌──────────────────────────────────────┐
│  📖 章节标题                          │
│  ─────────────────────────────────── │
│  文字段落 1                          │
│                                      │
│  ┌──────────────────────────────┐    │
│  │     SVG 图解（居中显示）      │    │
│  │     流程图/思维导图/对比图    │    │
│  └──────────────────────────────┘    │
│                                      │
│  图1: 图解说明                       │
│  ─────────────────────────────────── │
│  文字段落 2（进一步讲解）             │
│                                      │
│  💡 关键要点（列表形式）              │
│  - 要点1                             │
│  - 要点2                             │
└──────────────────────────────────────┘
```

## SVG 图解设计要求

1. **尺寸**：宽度 900-1100px，高度自适应（300-600px）
2. **配色**：使用柔和的颜色，不要大红大绿
3. **文字**：SVG 内文字使用 14-16px，清晰可读
4. **箭头/连线**：使用 marker-end 定义箭头
5. **节点**：圆角矩形，带阴影或渐变
6. **间距**：节点之间保持足够间距，不拥挤
7. **动画**：可选轻微 hover 效果（CSS transition）

## 输出格式

只返回 HTML 文档，不要 markdown 代码块，不要解释。"""


# ═══════════════════════════════════════════════════════════════
# 公开 API
# ═══════════════════════════════════════════════════════════════


def generate_doc_outlines(topic: str, language: str = "zh-CN", section_count: int = 4) -> dict:
    """Stage 1: 从主题生成文档大纲。

    Args:
        topic: 文档主题（如"TCP三次握手"）
        language: 输出语言
        section_count: 期望的章节数量

    Returns:
        {"languageDirective": str, "title": str, "sections": [...]}
    """
    llm = build_llm(streaming=False, provider=LLMProvider.MINIMAX)
    user_prompt = OUTLINE_USER_PROMPT.format(
        topic=topic,
        language=language,
        section_count=section_count,
    )
    response = llm.invoke([
        {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])
    text = response.content if hasattr(response, "content") else str(response)
    parsed = _parse_json_response(text)
    if not parsed or not parsed.get("sections"):
        raise ValueError(f"大纲生成失败：LLM 返回格式不正确，原文: {text[:300]}")
    return parsed


def generate_section_html(section: dict, language_directive: str = "") -> dict:
    """Stage 2: 从章节大纲生成带 SVG 图解的 HTML。

    Args:
        section: 章节大纲字典（含 title, description, keyPoints, diagramType, diagramPrompt）
        language_directive: Stage 1 返回的语言指令

    Returns:
        {"html": str, "title": str}
    """
    llm = build_llm(streaming=False, provider=LLMProvider.MINIMAX)
    key_points = "\n".join(section.get("keyPoints", []))
    diagram_type = section.get("diagramType", "flowchart")
    diagram_prompt = section.get("diagramPrompt", section.get("title", ""))

    user_prompt = f"""请为以下文档章节生成完整的 HTML 页面：

## 章节信息
- 标题: {section.get("title", "")}
- 描述: {section.get("description", "")}
- 图解类型: {diagram_type}
- 图解主题: {diagram_prompt}
- 核心要点:
{key_points}

## 语言要求
{language_directive or "使用中文生成内容。"}

## 视觉风格要求
- 宽屏布局：内容最大宽度 1100px
- 浅色主题：白色/浅灰背景，深色文字
- 蓝色系强调色 (#3b82f6)
- SVG 图解要精美、清晰、色彩柔和
- 现代简洁风格，圆角卡片

## 输出要求
返回完整的 HTML 文档（从 <!DOCTYPE html> 开始到 </html> 结束），不要 markdown 代码块，不要解释。"""

    response = llm.invoke([
        {"role": "system", "content": ILLUSTRATED_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ])
    text = response.content if hasattr(response, "content") else str(response)
    html = _extract_html(text)
    if not html:
        raise ValueError(f"章节「{section.get('title', '')}」HTML 提取失败")
    return {"html": html, "title": section.get("title", "")}


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _parse_json_response(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON。"""
    cleaned = text.strip()
    # 剥离推理模型的  CCS...标记
    think_end = cleaned.rfind("<｜end▁of▁thinking｜>")
    if think_end != -1:
        cleaned = cleaned[think_end + len("<｜end▁of▁thinking｜>"):].strip()
    # 尝试提取 markdown 代码块
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)```", cleaned, re.DOTALL)
    if md_match:
        cleaned = md_match.group(1).strip()
    elif cleaned.startswith("```"):
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
