"""私教老师主智能体 —— 基于 DeepAgents 编排多智能体群聊。"""

from deepagents import SubAgent, create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool

from ..prompts.chat_prompts import TUTOR_AGENT_SYSTEM_PROMPT


# ═══════════════════════════════════════════════════════════════
# 工具工厂 — 根据 user_id / subject 创建带用户隔离的工具
# ═══════════════════════════════════════════════════════════════


def _make_exam_tools(user_id: int):
    """创建测评相关工具（绑定用户 ID）。"""

    @tool
    def create_exam_tool(search_query: str, mcq_count: int = 5, qa_count: int = 2) -> str:
        """创建一份综合测评试卷。

        调用 Dify 题库生成工作流，生成选择题和问答题，并存入数据库。

        Args:
            search_query: 考察范围，如"数据结构"、"计算机网络"
            mcq_count: 选择题数量（默认5）
            qa_count: 问答题数量（默认2）

        Returns:
            创建结果描述字符串
        """
        from quiz.models import ExamSession

        from dify_workflow.quiz_generator import call_dify_workflow_quiz_generator

        try:
            result = call_dify_workflow_quiz_generator(
                mcq_count=mcq_count, qa_count=qa_count, search_query=search_query,
            )
            if result is None:
                return "测评生成失败：Dify 工作流返回空，请稍后重试"

            outputs = result.get("data", {}).get("outputs", {})
            mcqs = outputs.get("multiple_choice", [])
            essays = outputs.get("essay", [])

            session = ExamSession.objects.create(
                user_id=user_id,
                search_query=search_query,
                mcq_count=len(mcqs), qa_count=len(essays),
                multiple_choice=mcqs, essay=essays,
            )
            return (
                f"✅ 测评「{search_query}」已生成，共 {len(mcqs)} 道选择 + {len(essays)} 道问答。\n\n"
                f"点击下方卡片或[链接](/app/exam?session={session.id})开始答题。"
            )
        except Exception as e:
            return f"创建测评失败：{e}"

    @tool
    def get_exam_history_tool() -> str:
        """获取测评历史记录概览。返回最近的测评列表和得分情况。"""
        from quiz.models import ExamSession

        sessions = ExamSession.objects.filter(
            user_id=user_id, status="completed",
        ).order_by("-completed_at")[:5]
        if not sessions:
            return "暂无已完成的测评记录"

        lines = ["最近的测评记录："]
        for s in sessions:
            score = f"{s.mcq_score:.0%}" if s.mcq_score is not None else "未评分"
            lines.append(f"  - {s.search_query}（{score}，{s.completed_at.strftime('%m/%d')}）")
        return "\n".join(lines)

    return [create_exam_tool, get_exam_history_tool]


def _make_practice_quiz_tools(user_id: int, subject):
    """创建「3 道选择题快测」工具（绑定学科，用于对话气泡内嵌的轻量练习卡）。

    与 _make_exam_tools 的区别：
    - 不创建 ExamSession，不依赖 Dify 工作流
    - 直接调 llm/chains/quiz_chain.agenerate_quiz 生成轻量 QuizQuestion
    - 前端对话气泡中通过 sub_agent_start/end 协议渲染骨架屏与卡片
    - 本工具走 tutor 兜底调度（_build_dispatcher），不进入 DeepAgent task tool，
      所以用纯 async 函数 + 闭包列表即可，不需要 @tool 装饰器。

    Returns:
        (callable, quiz_questions): callable 是 async 函数，传入 dict 参数；
        quiz_questions 列表会在调用后被填充 QuizQuestion 序列化结果。
    """

    quiz_questions: list[dict] = []

    async def generate_practice_quiz_tool(
        search_query: str,
        mcq_count: int = 3,
        extra_prompt: str = "",
    ) -> str:
        """生成一份轻量的选择题练习（用于对话中快速检测）。"""
        from ..chains.quiz_chain import agenerate_quiz

        if not subject or not getattr(subject, "id", None):
            return "出题失败：当前对话未关联学科，无法确定题库范围"

        try:
            questions = await agenerate_quiz(
                subject_id=subject.id,
                extra_prompt=extra_prompt or search_query,
                count=mcq_count,
            )
        except Exception as exc:  # noqa: BLE001
            return f"出题失败：{exc}"

        # 只保留选择题（practice_quiz 子能力只出选择题）
        mcqs = [q for q in questions if getattr(q, "question_type", None) == "choice"]
        if not mcqs:
            return "出题失败：模型未生成任何选择题，请稍后重试"

        # 把题目序列化到外层闭包，调度层会读走推给前端
        quiz_questions.clear()
        quiz_questions.extend([q.model_dump() for q in mcqs])
        return (
            f"已生成「{search_query}」的 {len(mcqs)} 道选择题，下方可直接作答。"
        )

    return [generate_practice_quiz_tool], quiz_questions


def _make_plan_tools(user_id: int, subject):
    """创建计划相关工具（绑定用户和学科）。"""

    @tool
    def query_plans_tool(subject_code: str = "") -> str:
        """查询当前学习计划概览。

        Args:
            subject_code: 学科代码（可选，默认查当前学科）

        Returns:
            计划列表和进度概览
        """
        from plan.models import LearningPlan

        filters = {"state__in": ["pending", "running"], "subject__user_id": user_id}
        if subject:
            filters["subject"] = subject
        plans = LearningPlan.objects.filter(**filters).order_by(
            "expected_completion_time"
        )[:10]
        if not plans:
            return "当前没有待执行的学习计划"

        lines = ["当前学习计划："]
        for p in plans:
            memory = p.memory or {}
            step_label = memory.get("step_label") or p.action_type
            lines.append(
                f"  - {p.node_name} · {step_label}"
                f"（{p.expected_minutes}min，截止 {p.expected_completion_time or '待定'}）"
            )
        return "\n".join(lines)

    return [query_plans_tool]


def _make_video_tools(subject):
    """创建视频相关工具（绑定学科上下文）。"""

    @tool
    def generate_video_tool(topic: str, extra_prompt: str = "") -> str:
        """搜索并推荐 B 站教学视频。

        根据用户提供的知识点主题，搜索哔哩哔哩上的
        相关教学视频，返回最匹配的视频供用户观看。

        Args:
            topic: 知识点主题，如"Java多线程"、"快速排序"
            extra_prompt: 额外筛选要求（可选）

        Returns:
            视频搜索结果描述和 bvid
        """
        try:
            from dify_workflow.bili_push import call_dify_workflow_resource

            # 方案 0: 搜索词拼接学科名，提高相关性
            subject_name = getattr(subject, "name", "") or ""
            search_query = f"{subject_name} {topic}" if subject_name else topic
            if extra_prompt:
                search_query = f"{search_query} {extra_prompt}"

            result = call_dify_workflow_resource(search_query)
            if result is None:
                return "视频搜索失败：Dify 工作流返回空，请稍后重试"

            videos = result.get("data", {}).get("outputs", {}).get("text", [])
            if not videos or not isinstance(videos, list):
                return f"未找到与「{topic}」相关的教学视频，请尝试更具体的关键词。"

            # 方案 1: 相关性过滤 — 标题必须包含用户指定的关键词
            keywords = topic.lower().split()
            filtered = []
            for v in videos:
                title = (v.get("title", "") or "").lower()
                # 至少匹配一个关键词
                if any(kw in title for kw in keywords):
                    filtered.append(v)

            # 如果过滤后为空，回退到全部结果（避免过于严格）
            if not filtered:
                filtered = videos

            # 按播放量排序取最佳
            filtered.sort(key=lambda v: v.get("play", 0) or 0, reverse=True)
            best = filtered[0]
            bvid = best.get("bvid", "")
            title = best.get("title", topic)
            duration = best.get("duration", "")
            pic = best.get("pic", "")
            author = best.get("author", "")
            play_count = best.get("play", 0)

            if not bvid:
                return f"视频搜索异常：未获取到视频 ID"

            return (
                f"✅ 已找到相关教学视频。\n\n"
                f"bvid:{bvid}\n"
                f"title:{title}\n"
                f"duration:{duration}\n"
                f"pic:{pic}\n"
                f"author:{author}\n"
                f"play:{play_count}"
            )
        except Exception as e:
            return f"视频搜索失败：{e}"

    return [generate_video_tool]


def _make_quiz_tools(user_id: int):
    """创建练习题相关工具（绑定用户 ID）。"""

    @tool
    def generate_quiz_tool(topic: str, count: int = 5) -> str:
        """生成练习题。

        Args:
            topic: 知识点主题
            count: 题目数量（默认5）

        Returns:
            出题结果
        """
        return (
            f"已为你生成 {count} 道关于「{topic}」的练习题。"
            f"请前往刷题页面开始练习。"
        )

    return [generate_quiz_tool]


def _make_doc_assistant_tools(user_id: int):
    """创建实践助手相关工具（绑定用户 ID）。"""

    @tool
    def create_doc_tool(topic: str, language: str = "zh-CN", scene_count: int = 3) -> str:
        """生成交互式教学课件，包含多个场景的完整 HTML 课程内容。

        根据用户指定的主题，自动生成包含题目描述、交互式 HTML 页面的
        完整课件，可直接在对话中查看和交互。

        Args:
            topic: 课件主题，如"二叉树遍历"、"快速排序原理"
            language: 输出语言（zh-CN / en），默认中文
            scene_count: 场景数量（默认3）

        Returns:
            创建结果描述和会话 ID
        """
        from quiz.models import PracticeSession

        from .practice_generator import generate_practice_outlines, generate_scene_html

        try:
            # Stage 1: 生成大纲
            result = generate_practice_outlines(topic, language, scene_count)
            outlines = result.get("outlines", [])
            language_directive = result.get("languageDirective", "")

            # Stage 2: 逐个场景生成 HTML
            scenes = []
            for i, outline in enumerate(outlines):
                try:
                    scene = generate_scene_html(outline, language_directive)
                    scenes.append({
                        "title": outline.get("title", f"场景 {i + 1}"),
                        "html": scene["html"],
                        "widgetType": scene.get("widgetType", "code"),
                        "widgetConfig": scene.get("widgetConfig"),
                    })
                except Exception as e:
                    scenes.append({
                        "title": outline.get("title", f"场景 {i + 1}"),
                        "html": (
                            f"<html><body style='font-family:sans-serif;padding:2rem;"
                            f"color:#dc2626;'><h2>⚠️ 场景生成失败</h2><p>{e}</p></body></html>"
                        ),
                        "widgetType": "code",
                        "widgetConfig": None,
                    })

            session = PracticeSession.objects.create(
                user_id=user_id,
                search_query=topic,
                language=language,
                scene_count=len(scenes),
                outlines=outlines,
                scenes=scenes,
                status=PracticeSession.STATUS_READY,
            )
            return (
                f"✅ 课件「{topic}」已生成，共 {len(scenes)} 个场景。\n\n"
                f"session_id:{session.id}"
            )
        except Exception as e:
            return f"创建课件失败：{e}"

    return [create_doc_tool]


def _make_doc_writer_tools(user_id: int):
    """创建图文助手相关工具（绑定用户 ID）。"""

    @tool
    def create_doc_writer_tool(topic: str, language: str = "zh-CN", section_count: int = 4) -> str:
        """生成图文并茂的学习文档，每个章节带有 SVG 图解（流程图、思维导图、对比图等）。

        根据用户指定的主题，自动生成包含文字讲解和内嵌 SVG 图解的
        完整文档，可直接在对话中查看。

        Args:
            topic: 文档主题，如"TCP三次握手"、"快速排序原理"
            language: 输出语言（zh-CN / en），默认中文
            section_count: 章节数量（默认4）

        Returns:
            创建结果描述和会话 ID
        """
        from quiz.models import PracticeSession

        from .doc_writer import generate_doc_outlines, generate_section_html

        try:
            result = generate_doc_outlines(topic, language, section_count)
            title = result.get("title", topic)
            sections_outline = result.get("sections", [])
            language_directive = result.get("languageDirective", "")

            sections = []
            for i, sect in enumerate(sections_outline):
                try:
                    html_result = generate_section_html(sect, language_directive)
                    sections.append({
                        "title": html_result.get("title", f"章节 {i + 1}"),
                        "html": html_result["html"],
                    })
                except Exception as e:
                    sections.append({
                        "title": sect.get("title", f"章节 {i + 1}"),
                        "html": (
                            f"<html><body style='font-family:sans-serif;padding:2rem;"
                            f"color:#dc2626;'><h2>⚠️ 章节生成失败</h2><p>{e}</p></body></html>"
                        ),
                    })

            session = PracticeSession.objects.create(
                user_id=user_id,
                search_query=title,
                language=language,
                scene_count=len(sections),
                outlines=sections_outline,
                scenes=sections,
                status=PracticeSession.STATUS_READY,
            )
            return (
                f"✅ 图文文档「{title}」已生成，共 {len(sections)} 个章节。\n\n"
                f"session_id:{session.id}"
            )
        except Exception as e:
            return f"创建文档失败：{e}"

    return [create_doc_writer_tool]


# ═══════════════════════════════════════════════════════════════
# 子智能体配置
# ═══════════════════════════════════════════════════════════════


def _make_sub_agent_configs(model: BaseChatModel, user_id: int, subject) -> list[SubAgent]:
    """构建所有子智能体配置（绑定用户和学科上下文）。"""

    video_tools = _make_video_tools(subject)
    doc_assistant_tools = _make_doc_assistant_tools(user_id)
    doc_writer_tools = _make_doc_writer_tools(user_id)

    video_sub: SubAgent = {
        "name": "video",
        "description": (
            "视频助手 —— 当用户想要观看教学视频、搜索B站课程时使用。"
            "主动使用场景：用户说「视频」「讲解」「看课程」「有没有XX的教学视频」「找视频」"
        ),
        "system_prompt": (
            "你是视频助手，负责为用户搜索和推荐 B 站教学视频。\n\n"
            "你的职责：\n"
            "1. 根据用户指定的知识点搜索 B 站相关教学视频\n\n"
            "可用工具：\n"
            "- generate_video_tool: 搜索视频，参数 topic（知识点主题）\n\n"
            "⚠️ 关键规则：\n"
            "搜索视频后，工具会返回视频信息和 bvid 号。\n"
            "你**只负责**原样返回工具结果，不要改写字段名，不要整理成推荐列表。\n"
            "**绝对不能**自己编造视频内容或链接。\n"
            "务必保留 `bvid:`、`title:`、`duration:`、`pic:` 这些字段行，方便前端解析并内嵌播放器。\n"
            "视频会直接嵌入对话中播放——那才是完整的体验。\n"
            "你输出结果之后任务就完成了，不需要再做任何事。回答简洁。"
        ),
        "model": model,
        "tools": video_tools,
    }

    doc_assistant_sub: SubAgent = {
        "name": "doc_assistant",
        "description": (
            "实践助手 —— 当用户想要生成交互式课件、代码实践、仿真实验、教学场景时使用。"
            "主动使用场景：用户说「生成课件」「教程」「代码实践」「仿真」「教学场景」「演示」"
        ),
        "system_prompt": (
            "你是实践助手，负责为用户生成交互式教学课件。\n\n"
            "你的职责：\n"
            "1. 根据用户指定的主题生成完整的交互式课件（默认 3 个场景）\n\n"
            "可用工具：\n"
            "- create_doc_tool: 生成课件，参数 topic（主题）、"
            "language（输出语言，默认 zh-CN）、scene_count（场景数，默认3）\n\n"
            "⚠️ 关键规则：\n"
            "创建课件后，工具会返回完整的交互式 HTML 课件内容。\n"
            "你**只负责**把这个课件内容原样返回给用户。\n"
            "**绝对不能**自己编写课件内容或总结工具的输出。\n"
            "课件会直接在对话中渲染显示——那才是完整的体验。\n"
            "你输出课件之后任务就完成了，不需要再做任何事。回答简洁。"
        ),
        "model": model,
        "tools": doc_assistant_tools,
    }

    doc_writer_sub: SubAgent = {
        "name": "doc_writer",
        "description": (
            "图文助手 —— 当用户想要生成图文并茂的学习文档、带图解的知识讲解时使用。"
            "主动使用场景：用户说「图解」「图示」「流程图」「思维导图」「图文」「知识文档」「可视化讲解」"
        ),
        "system_prompt": (
            "你是图文助手，负责为用户生成图文并茂的学习文档。\n\n"
            "你的职责：\n"
            "1. 根据用户指定的主题生成带 SVG 图解的知识文档（默认 1 个章节）\n\n"
            "可用工具：\n"
            "- create_doc_writer_tool: 生成图文文档，参数 topic（主题）、"
            "language（输出语言，默认 zh-CN）、section_count（章节数，默认1）\n\n"
            "⚠️ 关键规则：\n"
            "创建文档后，工具会返回完整的 HTML 文档内容（含 SVG 图解）。\n"
            "你**只负责**把文档内容原样返回给用户。\n"
            "**绝对不能**自己编写文档或总结工具的输出。\n"
            "文档会直接在对话中渲染显示——那才是完整的体验。\n"
            "你输出文档之后任务就完成了，不需要再做任何事。回答简洁。"
        ),
        "model": model,
        "tools": doc_writer_tools,
    }

    # 测评/出卷类需求不再通过 DeepAgent 的 exam 子智能体调度，
    # 统一交给 llm/tasks.py 里的出题分发逻辑处理。
    return [video_sub, doc_assistant_sub, doc_writer_sub]


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════


def create_tutor_agent(model: BaseChatModel, user_id: int, subject=None):
    """创建私教老师主智能体。

    Args:
        model: LLM 模型实例（如 ChatOpenAI）
        user_id: 当前用户 ID，用于工具的数据隔离
        subject: 当前学科对象，用于工具的数据过滤

    Returns:
        CompiledStateGraph（支持 astream_events 流式输出）
    """
    subagents = _make_sub_agent_configs(model, user_id, subject)

    return create_deep_agent(
        model=model,
        tools=[],
        subagents=subagents,
        system_prompt=TUTOR_AGENT_SYSTEM_PROMPT,
    )
