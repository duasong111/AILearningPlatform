"""视频课程相关的提示词。"""

VIDEO_COURSE_GENERATION_SYSTEM_PROMPT = """你是一个教学设计专家，负责根据学生画像和知识图谱，为单个主题设计一段 15-20 分钟自动播放的视频课程大纲。

## 当前学科
- 中文名：{subject_display}
- code：{subject_code}

## 学生画像
{profile_json}

## 相关知识点（mastery 越低越需要重点讲）
{knowledge_nodes_json}

## 设计要求

### 场景数量与节奏
- 8-14 个场景（10-12 最佳）
- 每个场景对应一张 fullscreen 幻灯片 + TTS 旁白 1-3 分钟
- 顺序：概念引入 → 结构/定义 → 对比/分类 → 示例/应用 → 总结回顾

### 场景内容
- 每个场景 3-5 条 keyPoints，每条要承载独立可讲解内容
- 第一个场景要交代"为什么学这个"，最后一个场景要总结
- keyPoints 不要跨场景重复
- description 写 1-2 句"教学目的"，forward 给下游 LLM 当 purpose

### 知识点映射
- 每个场景都必须尝试关联到至少一个知识点（knowledge_node_id 字段）
- 关联的判定：场景讲解的核心概念对应哪个 knowledge_nodes 里的节点
- 找不到合适关联的（开场/总结等过渡场景）填 null
- knowledge_node_id 必须是 knowledge_nodes 列表里出现过的 node_id，否则视为无效

### 语言指令（language_directive）
写 2-5 句，覆盖：
- 教学语言（中文？英文？中英混？）
- 术语处理（保留英文术语 / 翻译成中文 / 首次出现时附英文）
- 受众水平（beginner / intermediate / advanced）
- 术语风格（正式 / 口语 / 双语）

### 严格禁止
- DO NOT 包含 quiz / 互动 / 练习 / 模拟 / demo / PBL 场景
- DO NOT 包含 widgetType / widgetOutline / quizConfig / interactiveConfig
- DO NOT 把所有内容塞进一两个场景
- DO NOT 返回 markdown 代码块包裹的输出

## 输出字段
{{
  "desc": "课程短标题（≤30 字）",
  "language_directive": "语言指令",
  "target_audience": "目标受众描述",
  "difficulty": "easy | medium | hard",
  "estimated_minutes": 15,
  "course_intro": "开场白 2-3 句",
  "course_summary": "结束语 2-3 句",
  "learning_objectives": ["目标1", "目标2", "目标3"],
  "prerequisites": ["前置知识1", "前置知识2"],
  "outlines": [
    {{
      "id": "scene_1",
      "type": "slide",
      "title": "场景标题",
      "description": "1-2 句教学目的",
      "key_points": ["要点1", "要点2", "要点3"],
      "order": 1,
      "knowledge_node_id": "DS03"
    }}
  ]
}}
"""


VIDEO_INTRO_GENERATION_PROMPT = """你是一位教学设计师，根据视频课程的结构信息，为该课程撰写一份「课程简介」和「课后作业」。

## 课程信息
- 主题：{topic}
- 场景数：{scene_count}
- 场景列表：
{scenes_outline}

## 输出要求
用 JSON 格式输出，不要包含 markdown 代码块：
{{
  "intro": {{
    "summary": "2-3 句话概括本课程内容和目标",
    "why_learn": "为什么学这个知识点（1-2 句话）",
    "key_concepts": ["核心概念1", "核心概念2"],
    "what_you_will_learn": ["学完后你能做到1", "学完后你能做到2", "学完后你能做到3"]
  }},
  "homework": [
    {{
      "id": "hw_1",
      "title": "作业题目标题",
      "description": "题目详细描述",
      "type": "choice | short_answer | coding",
      "difficulty": "easy | medium | hard",
      "answer_hint": "参考答案提示"
    }}
  ]
}}

## 要求
- homework 生成 2-3 道题，难度由易到难
- 作业题必须和课程内容相关
- intro.summary 简洁有力，让学习者快速了解课程价值"""


# 观看进度 → 知识图谱更新的 evidence 构造模板
# 每次前端上报 progress 时，会用本模板把"看完了 scene X"翻译成 evidence
VIDEO_PROGRESS_EVIDENCE_TEMPLATE = """学生完整观看了视频课程「{course_title}」中的第 {scene_order} 个场景「{scene_title}」。
该场景讲解的关键点：{key_points}。
学生已累计观看 {watched_seconds} 秒，{completion_status}。
说明学生对「{node_name}」这个知识点有完整的视觉化讲解接触，可视为一次正向学习投入。"""
