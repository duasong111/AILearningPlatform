"""
认知评估 Agent：根聊天证据 + 历史分值，给出 -1.0..1.0 之间的"相对认知 delta"。

自适应跳变幅度 + 解析失败重试 1 次。

被 knowledge_tools.assess_and_update_knowledge_score 调用。
"""
import re
import time
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from llm.config import LLMProvider, get_llm_config

# 自适应跳变：根据 prev_score 决定本次最大允许跳变
# 起步低分时允许大幅跃升（快速校准），高分时收紧（防震荡）
ADAPTIVE_MAX_DELTA = [
    # (prev_score < threshold, max_delta)
    (30,  25),  # 0-29: 最多 ±25（新生知识，抓紧校准）
    (60,  20),  # 30-59: 最多 ±20（默认）
    (90,  15),  # 60-89: 最多 ±15（接近熟练，小步调）
    (101, 10),  # 90-100: 最多 ±10（高分，谨慎改）
]


def _adaptive_max_delta(prev_score: int) -> int:
    for threshold, delta in ADAPTIVE_MAX_DELTA:
        if prev_score < threshold:
            return delta
    return 10


ASSESSOR_SYSTEM = """你是"认知评估员"，专门根据用户对话证据，评估用户对某个知识点的**相对**认知水平变化。

## 输出规则
- 仅输出一个 -1.0 到 1.0 之间的浮点数
- 0.0 = 无变化；正数 = 认知提升；负数 = 认知退步或误解
- 1.0 / -1.0 是极值，仅当证据**非常**充分/反证时使用
- 0.1 ~ 0.3 范围最常见

## 评估依据
- 用户是否提到相关概念（提到 = 兴趣信号）
- 用户回答的准确性 / 自信度
- 用户对细节的把握（举一反三 vs 死记硬背）
- 是否有概念混淆或误解
- 用户的提问深度

## 不要做的事
- 不要输出任何解释、标点、空格
- 不要输出范围之外的值
- 不要因为用户提到一次就大幅加分"""


def _build_llm(config):
    if config.provider == LLMProvider.MIMO:
        return ChatOpenAI(
            model=config.model_name,
            temperature=0.0,
            api_key=config.api_key,
            base_url=config.base_url,
            default_headers={"api-key": config.api_key},
            max_retries=1,
            extra_body={"thinking": {"type": "disabled"}},
        )
    if config.provider == LLMProvider.ANTHROPIC:
        return ChatAnthropic(
            model=config.model_name,
            temperature=0.0,
            api_key=config.api_key,
            base_url=config.base_url,
            max_retries=1,
        )
    return ChatOpenAI(
        model=config.model_name,
        temperature=0.0,
        api_key=config.api_key,
        base_url=config.base_url,
        max_retries=1,
    )


@dataclass
class AssessmentResult:
    new_score: int
    prev_score: int
    delta_norm: float          # [-1, 1]
    actual_delta: int          # 已经 clamp 过
    max_delta_used: int        # 自适应后本次上限
    rationale: str
    raw_outputs: list[str]     # 审计用：每次 LLM 的原始输出


def _call_llm_once(llm, node_name: str, prev_score: int, evidence: str) -> str:
    prompt = (
        f"知识点: {node_name}\n"
        f"当前分值: {prev_score}/100\n"
        f"对话证据: {evidence}\n\n"
        f"输出 -1.0 到 1.0 之间的浮点数（仅一个数字）："
    )
    msg = llm.invoke([
        SystemMessage(content=ASSESSOR_SYSTEM),
        HumanMessage(content=prompt),
    ])
    return (msg.content or "").strip()


def _parse_delta(raw: str) -> float | None:
    """宽容解析：抓第一个浮点数，钳到 [-1, 1]。无法解析返回 None（区别于 0.0）。"""
    m = re.search(r"-?\d*\.?\d+", raw)
    if not m:
        return None
    try:
        v = float(m.group())
    except ValueError:
        return None
    return max(-1.0, min(1.0, v))


class KnowledgeAssessor:
    """
    同步 LLM-based 评估器。features:
    - 自适应跳变：按 prev_score 选 max_delta
    - 解析失败重试 1 次
    - 仍失败 → new_score = prev_score（不写库），rationale 标注 parse_failed
    """

    def __init__(self):
        config = get_llm_config()
        self.llm = _build_llm(config)
        self.config = config

    def assess(self, *, node_name: str, prev_score: int, evidence: str) -> AssessmentResult:
        max_delta = _adaptive_max_delta(prev_score)
        raw_outputs: list[str] = []
        delta_norm: float | None = None

        # 最多调 2 次（首次 + 1 次重试）
        for attempt in range(2):
            raw = _call_llm_once(self.llm, node_name, prev_score, evidence)
            raw_outputs.append(raw)
            parsed = _parse_delta(raw)
            if parsed is not None:
                delta_norm = parsed
                break
            # parse 失败：重试前给个强 prompt 提示只输出数字
            if attempt == 0:
                evidence = evidence + " (重要：只输出一个 -1.0 到 1.0 的数字，不要任何其他内容)"

        if delta_norm is None:
            # 两次都失败：保守不动
            return AssessmentResult(
                new_score=prev_score,
                prev_score=prev_score,
                delta_norm=0.0,
                actual_delta=0,
                max_delta_used=max_delta,
                rationale=f"parse_failed after 2 attempts: raws={raw_outputs}",
                raw_outputs=raw_outputs,
            )

        proposed = round(delta_norm * max_delta)
        actual_delta = max(-max_delta, min(max_delta, proposed))
        new_score = max(0, min(100, prev_score + actual_delta))
        rationale = (
            f"attempt={len(raw_outputs)} "
            f"raw={raw_outputs[0]!r}→{delta_norm:+.2f} "
            f"×adaptive_max={max_delta}→{actual_delta:+d} "
            f"prev={prev_score}→new={new_score}"
        )
        return AssessmentResult(
            new_score=new_score,
            prev_score=prev_score,
            delta_norm=delta_norm,
            actual_delta=actual_delta,
            max_delta_used=max_delta,
            rationale=rationale,
            raw_outputs=raw_outputs,
        )


# 单例（懒加载）
_assessor: KnowledgeAssessor | None = None


def get_assessor() -> KnowledgeAssessor:
    global _assessor
    if _assessor is None:
        _assessor = KnowledgeAssessor()
    return _assessor
