"""一次性生成 plan/baseline_plans.py（静态快照）。

用法（在 backend 目录）:
    python plan/_gen_baseline.py

无需 Django settings，直接读 users/knowledge_map.py 即可，
但通过 setup Django 保证 llm.chains.plan_chain 的导入链不断。
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from llm.chains.plan_chain import (
    SUBJECT_KNOWLEDGE_MAP,
    build_baseline_plan_items,
)

out_path = os.path.join(os.path.dirname(__file__), "baseline_plans.py")

lines = [
    '"""基础学习计划静态快照（自动生成，请勿手改）。',
    "",
    "由 _gen_baseline.py 一次性生成于 %s。",
    "",
    "结构:",
    "    BASELINE_PLANS = {",
    '        "data_structure": [',
    '            {"node_id": "2", "node_name": "数组", "node_type": "structure",',
    '             "difficulty": 1, "expected_minutes": 30},',
    "            ...",
    "        ],",
    "        ...",
    "    }",
    "",
    "顺序规则:",
    "  - 按 prerequisite 拓扑排序，依赖在前",
    "  - 同层按 (difficulty, name, id) 稳定排序",
    "  - difficulty 1-5 线性映射 expected_minutes = 30 * difficulty",
    "",
    "运行时由 plan_chain.create_baseline_plan 直接查表，不再动态计算。",
    '"""',
    "",
    "",
    "BASELINE_PLANS = {",
]

for code, attr in SUBJECT_KNOWLEDGE_MAP.items():
    items = build_baseline_plan_items(subject_code=code)
    lines.append(f'    "{code}": [')
    for it in items:
        # Use repr to handle Chinese characters safely
        lines.append(
            f'        {{"node_id": {it["node_id"]!r}, '
            f'"node_name": {it["node_name"]!r}, '
            f'"node_type": {it["node_type"]!r}, '
            f'"difficulty": {it["difficulty"]}, '
            f'"expected_minutes": {it["expected_minutes"]}}},'
        )
    lines.append("    ],")
lines.append("}")
lines.append("")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"wrote {out_path}")
print(f"subjects: {len(SUBJECT_KNOWLEDGE_MAP)}")
total = sum(len(v) for v in [
    build_baseline_plan_items(subject_code=c) for c in SUBJECT_KNOWLEDGE_MAP
])
print(f"total items: {total}")