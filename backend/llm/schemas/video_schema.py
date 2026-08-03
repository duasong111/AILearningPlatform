"""视频课程相关的结构化 schema。

- VideoCourse: LLM 生成一整门"视频课"的结构化大纲
- VideoScene:  大纲里的单个幻灯片场景（喂给 OpenMAIC /video 页面）
- VideoProgress: 前端上报观看进度的载荷
"""
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Difficulty = Literal["easy", "medium", "hard"]


class VideoScene(BaseModel):
    """单个幻灯片场景。"""

    id: str = Field(description="稳定 id，如 'scene_1'")
    type: Literal["slide"] = Field(default="slide", description="固定为 slide")
    title: str = Field(description="场景标题，≤20 字符")
    description: str = Field(description="1-2 句教学目的")
    key_points: list[str] = Field(description="3-5 条关键点")
    order: int = Field(description="播放顺序，从 1 开始")
    # 关联到知识图谱的 node_id（可空 —— 有些章节是引言/总结，不直接对应单一知识点）
    knowledge_node_id: str | None = Field(
        default=None,
        description="关联的知识点 node_id（如 'DS03'），若不直接对应单一知识点则填 null",
    )


class VideoCourse(BaseModel):
    """完整视频课程大纲（LLM 一次性结构化输出）。"""

    @model_validator(mode="before")
    @classmethod
    def _strip_think_tags(cls, data):
        if isinstance(data, str):
            data = re.sub(r"<think>[\s\S]*?</think>", "", data)
        return data

    desc: str = Field(description="课程短标题，会显示在播放器 UI 上")
    language_directive: str = Field(
        description="2-5 句语言指令（教学语言、术语处理、难度风格、受众）",
    )
    target_audience: str = Field(description="目标受众描述")
    difficulty: Difficulty = Field(description="整体难度")
    estimated_minutes: int = Field(description="预计时长（分钟）")
    course_intro: str = Field(description="开场白 2-3 句")
    course_summary: str = Field(description="结束语 2-3 句")
    learning_objectives: list[str] = Field(description="学习目标清单，3-5 条")
    prerequisites: list[str] = Field(
        default_factory=list, description="前置知识点列表",
    )
    outlines: list[VideoScene] = Field(description="8-14 个场景")


class VideoProgress(BaseModel):
    """前端上报的观看进度。"""

    video_course_id: int | None = Field(
        default=None,
        description="VideoCourseRecord.id（可空，方便纯 uuid 维度上报）",
    )
    video_uuid: str = Field(description="OpenMAIC 视频服务 uuid")
    viewed_scene_ids: list[str] = Field(
        description="已完整播放过的 scene id 列表（去重）",
    )
    last_scene_id: str | None = Field(
        default=None, description="最近一次播放到的 scene id",
    )
    watched_seconds: int = Field(
        default=0, description="累计观看时长（秒），用于评估'投入度'",
    )
    completed: bool = Field(
        default=False, description="是否完整看完（所有 scene 都已播放）",
    )
