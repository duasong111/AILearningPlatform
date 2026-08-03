"""Practice 分析结果的结构化 schema。"""
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


PracticeMode = Literal["with_answer", "without_answer"]
PracticePhase = Literal["pre_submit", "post_submit"]
Difficulty = Literal["easy", "medium", "hard"]
Verdict = Literal["correct", "wrong", "pending", "ungraded"]


class PracticeStep(BaseModel):
    """解析中的步骤项。"""

    text: str = Field(description="步骤文本")
    is_key: bool = Field(default=False, description="是否为关键步骤")


class PracticeKnowledgeCard(BaseModel):
    """解析中的知识卡片。"""

    title: str = Field(description="知识点名称")
    description: str = Field(description="知识点说明")
    icon: str | None = Field(default=None, description="可选图标字符，默认 null")


class PracticeResult(BaseModel):
    """答题结果摘要。"""

    verdict: Verdict = Field(description="答题结果：correct / wrong / pending / ungraded")
    is_correct: bool | None = Field(default=None, description="是否回答正确；未判分时为 null")
    user_answer: str | None = Field(default=None, description="用户答案，没有则为 null")
    correct_answer: str | None = Field(default=None, description="正确答案；答题前模式通常为 null")
    summary: str = Field(description="结果摘要，用于结果 banner 或顶部提示")


class PracticeAnalysis(BaseModel):
    """题目分析结果。"""

    @model_validator(mode="before")
    @classmethod
    def _strip_think_tags(cls, data):
        """LLM 输出中可能混有<think>...</think>思考标签，在 JSON 解析前去掉。"""
        if isinstance(data, str):
            data = re.sub(r"<think>[\s\S]*?</think>", "", data)
        return data

    mode: PracticeMode = Field(
        description="分析模式：with_answer（带答案分析）或 without_answer（无答案引导）",
    )
    phase: PracticePhase = Field(
        description="解析阶段：pre_submit（答题前）或 post_submit（答题后）",
    )
    analysis: str = Field(
        description="简要分析摘要，用于顶部概览；详细内容请看结构化字段",
    )
    key_knowledge_points: list[str] = Field(
        default_factory=list,
        description="题目涉及的核心知识点列表",
    )
    difficulty_assessment: Difficulty = Field(
        description="对题目难度的评估：easy / medium / hard",
    )
    approach: str | None = Field(
        default=None,
        description="答题前展示的建议思考方向；答题后可为空",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="渐进提示文本列表",
    )
    knowledge: list[PracticeKnowledgeCard] = Field(
        default_factory=list,
        description="关联知识预览或复习卡片列表",
    )
    result: PracticeResult | None = Field(
        default=None,
        description="答题结果摘要；答题前模式通常为 null",
    )
    steps: list[PracticeStep] = Field(
        default_factory=list,
        description="解题步骤列表",
    )
    deep_analysis: str | None = Field(
        default=None,
        description="深度解析文本；答题前模式可为空或简短提示",
    )
    pitfalls: list[str] = Field(
        default_factory=list,
        description="常见误区列表",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="下一步推荐练习或学习建议",
    )
