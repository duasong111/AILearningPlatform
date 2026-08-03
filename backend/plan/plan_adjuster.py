"""LLM 驱动的学习计划重排序。

规则层 (plan_templates.build_personalized_plan_spec) 已经完成了步骤筛选和时间压缩,
本模块负责最后一步: 根据用户画像对知识点学习顺序进行优化调整。

调整维度:
  - 兴趣优先: interest_direction 匹配的节点适当提前
  - 薄弱优先: common_mistakes 中的节点适当提前
  - 难度递进: 简单在前, 复杂在后 (但兴趣/薄弱可打破)

调用方式 (async):
    specs = build_personalized_plan_spec(subject_code, profile_summary)
    specs = await adjust_plan_order(specs, profile_summary, subject_display)
"""

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from llm.agents.llm_factory import build_llm
from llm.common import extract_json

logger = logging.getLogger(__name__)


PLAN_ADJUSTER_SYSTEM_PROMPT = """你是学习计划排序专家。请根据用户画像对知识点学习顺序进行优化调整。

## 排序规则

1. **尊重依赖关系**: 被依赖的知识点必须在前 (如"链表"在"栈"之前、"树"在"二叉树"之前)
2. **兴趣优先**: 用户兴趣方向相关的知识点适当提前, 提升学习动力
3. **薄弱优先**: 薄弱知识点适当提前, 便于尽早攻克
4. **难度递进**: 简单知识点在前, 复杂在后 (但兴趣/薄弱可打破此规则)

## 输出格式

输出一个 JSON 对象, 包含重新排序后的知识点名称列表:
```json
{"order": ["知识点A", "知识点B", ...]}
```

注意: 列表必须包含输入的所有知识点, 不能遗漏或新增, 不能修改名称。"""


def _group_specs_by_node(specs: list[dict]) -> list[dict]:
    """提取去重后的节点列表 (保留首次出现的 spec 中的节点信息)。"""
    seen = set()
    nodes = []
    for spec in specs:
        name = spec["node_name"]
        if name not in seen:
            seen.add(name)
            nodes.append({
                "node_name": name,
                "difficulty": spec["difficulty"],
                "node_type": spec["node_type"],
            })
    return nodes


def _format_nodes_for_prompt(nodes: list[dict]) -> str:
    """格式化节点列表供 LLM 阅读。"""
    lines = []
    for i, n in enumerate(nodes, 1):
        lines.append(f"{i}. {n['node_name']} (难度{n['difficulty']}, 类型{n['node_type']})")
    return "\n".join(lines)


def _format_profile_for_prompt(profile_summary: dict) -> str:
    """格式化画像摘要供 LLM 阅读。"""
    kb = profile_summary.get("knowledge_base") or {}
    lg = profile_summary.get("learning_goal") or {}
    weak = kb.get("weak_areas") or []
    interests = profile_summary.get("interest_direction") or []

    return (
        f"- 学习目标: {lg.get('goal') or '未指定'}\n"
        f"- 知识基础: {kb.get('level', 0)}/100\n"
        f"- 兴趣方向: {', '.join(interests) if interests else '未指定'}\n"
        f"- 薄弱知识点: {', '.join(weak) if weak else '无'}"
    )


def _reorder_specs(specs: list[dict], ordered_names: list[str]) -> list[dict]:
    """按 ordered_names 顺序重排 specs, 每个节点内的步骤保持原 step_order。"""
    name_to_specs: dict[str, list[dict]] = {}
    for spec in specs:
        name_to_specs.setdefault(spec["node_name"], []).append(spec)

    # 每个节点内部按 step_order 排序
    for name in name_to_specs:
        name_to_specs[name].sort(key=lambda s: s.get("step_order", 0))

    result = []
    for name in ordered_names:
        if name in name_to_specs:
            result.extend(name_to_specs[name])
    # 兜底: LLM 遗漏的节点追加到末尾
    for name, node_specs in name_to_specs.items():
        if name not in ordered_names:
            result.extend(node_specs)
    return result


async def adjust_plan_order(
    specs: list[dict],
    profile_summary: dict,
    subject_display: str,
) -> list[dict]:
    """调用 LLM 根据画像重排 plan specs 的节点顺序。

    Args:
        specs: build_personalized_plan_spec 的输出
        profile_summary: 用户画像摘要 dict
        subject_display: 学科中文名 (如 "数据结构")

    Returns:
        重排后的 specs 列表, 节点顺序优化, 步骤内容不变
    """
    if not specs:
        return specs

    nodes = _group_specs_by_node(specs)
    if len(nodes) <= 1:
        return specs

    user_prompt = (
        f"学科: {subject_display}\n\n"
        f"## 用户画像\n{_format_profile_for_prompt(profile_summary)}\n\n"
        f"## 知识点列表 (当前顺序, 已按依赖拓扑排序)\n{_format_nodes_for_prompt(nodes)}\n\n"
        f"请根据用户画像重新排序这些知识点。"
    )

    try:
        llm = build_llm(streaming=False, temperature=0.1)
        response = await llm.ainvoke([
            SystemMessage(content=PLAN_ADJUSTER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        text = response.content if isinstance(response.content, str) else str(response.content)
        parsed = json.loads(extract_json(text))
        ordered_names = parsed.get("order", [])

        if not isinstance(ordered_names, list) or len(ordered_names) != len(nodes):
            logger.warning(
                "adjust_plan_order: LLM 返回节点数不匹配 (got %s, expected %s), 跳过重排",
                len(ordered_names) if isinstance(ordered_names, list) else 0,
                len(nodes),
            )
            return specs

        reordered = _reorder_specs(specs, ordered_names)
        logger.info(
            "adjust_plan_order: reordered %s nodes for subject=%s",
            len(nodes), subject_display,
        )
        return reordered
    except Exception:  # noqa: BLE001
        logger.exception("adjust_plan_order failed, keeping original order")
        return specs
