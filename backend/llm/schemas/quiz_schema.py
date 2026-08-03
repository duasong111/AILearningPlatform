"""出题 chain 的结构化输出 schema。"""
from typing import Literal

from pydantic import BaseModel, Field


InputMode = Literal["choice", "text", "code", "image", "dragdrop"]
QuestionType = Literal["choice", "short_answer"]
Difficulty = Literal["easy", "medium", "hard"]


class QuizStep(BaseModel):
    """题目解析中的步骤项。"""

    text: str = Field(description="步骤文本")
    is_key: bool = Field(default=False, description="是否为关键步骤")


class QuizKnowledgeCard(BaseModel):
    """题目关联知识卡片。"""

    title: str = Field(description="知识点名称")
    description: str = Field(description="知识点说明")
    icon: str | None = Field(default=None, description="可选图标字符，默认 null")


class QuizQuestion(BaseModel):
    """单道题目。"""

    question_type: QuestionType = Field(
        description="题型：choice（选择题）或 short_answer（简答题）",
    )
    difficulty: Difficulty = Field(
        description="难度：easy / medium / hard",
    )
    topic: str = Field(description="题目的主题或所属模块，如 数据结构 / Python")
    bloom_level: str = Field(description="Bloom 层级，如 记忆 / 理解 / 应用 / 分析 / 评价 / 创造")
    title: str = Field(description="题目标题，供题目头部展示")
    question_text: str = Field(
        description="题目正文",
    )
    question_context: str | None = Field(
        default=None,
        description="题目的补充背景、说明或上下文，没有则为 null",
    )
    code_snippet: str | None = Field(
        default=None,
        description="题目附带的代码片段，没有则为 null",
    )
    input_modes: list[InputMode] = Field(
        default_factory=list,
        description="前端允许的作答方式列表，如 ['choice', 'text', 'image']",
    )
    knowledge_node_id: str = Field(
        default="",
        description="目标知识点的 node_id，如 DS01。LLM 偶发漏填，留空时由后端从 knowledge_map 兜底回填",
    )
    knowledge_node_name: str = Field(
        default="",
        description="目标知识点的名称，如 链表。LLM 偶发漏填，留空时由后端从 knowledge_map 兜底回填",
    )
    image_base64: str | None = Field(
        default=None,
        description="题目的附加图片 base64 内容，当前默认 null，后续题库适配时可填",
    )
    options: list[str] | None = Field(
        default=None,
        description="选择题的选项列表（通常 4 个），简答题为 null",
    )
    correct_answer: str = Field(
        description="正确答案。选择题填选项字母（如 A），简答题填参考答案",
    )
    explanation: str = Field(
        description="标准解析，解释为什么这个答案正确",
    )
    approach: str = Field(description="答题前展示的解题思路引导")
    hints: list[str] = Field(
        default_factory=list,
        description="渐进提示列表，建议 2-4 条",
    )
    steps: list[QuizStep] = Field(
        default_factory=list,
        description="答题后展示的解题步骤列表",
    )
    knowledge: list[QuizKnowledgeCard] = Field(
        default_factory=list,
        description="关联知识预览卡片列表",
    )
    deep_analysis: str = Field(description="答题后展示的深度解析")
    pitfalls: list[str] = Field(
        default_factory=list,
        description="常见误区列表，建议 2-4 条",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="推荐的下一步练习或学习建议，建议 2-4 条",
    )
