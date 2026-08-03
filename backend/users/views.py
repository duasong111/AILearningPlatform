from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from django.http import Http404
from asgiref.sync import sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, UserProfile, Subject, KnowledgeNode, Conversation, Message
from .serializers import UserSerializer, UserRegisterSerializer, UserProfileSerializer, SubjectSerializer, ConversationSerializer, ConversationListSerializer, MessageSerializer, KnowledgeNodeSerializer


def _normalize_message_meta(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return None


def _normalize_object_field(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return None


def _normalize_string_list(value, *, field_name: str):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f'{field_name} must be an array')
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _normalize_int_list(value, *, field_name: str):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f'{field_name} must be an array')
    normalized: list[int] = []
    for item in value:
        try:
            normalized.append(int(item))
        except (TypeError, ValueError):
            raise ValueError(f'{field_name} must contain integers only')
    return list(dict.fromkeys(normalized))


def _normalize_agent_payload(agent: str, payload: dict):
    normalized = dict(payload)

    if agent == Conversation.AGENT_PLAN:
        selected_plan_ids = _normalize_int_list(normalized.get('selected_plan_ids'), field_name='selected_plan_ids')
        mode = normalized.get('mode')
        if mode is None:
            mode = 'edit' if selected_plan_ids else 'generate'
        if mode not in {'generate', 'edit'}:
            raise ValueError('plan agent_payload.mode must be generate or edit')
        normalized['mode'] = mode
        normalized['selected_plan_ids'] = selected_plan_ids
        return normalized

    if agent == Conversation.AGENT_PRACTICE:
        mode = normalized.get('mode')
        if mode is not None and mode not in {'free', 'plan_driven'}:
            raise ValueError('practice agent_payload.mode must be free or plan_driven')
        if normalized.get('plan_id') is not None:
            try:
                normalized['plan_id'] = int(normalized['plan_id'])
            except (TypeError, ValueError):
                raise ValueError('practice agent_payload.plan_id must be an integer')
            normalized.setdefault('mode', 'plan_driven')
        if normalized.get('difficulty') is not None and normalized['difficulty'] not in {'low', 'medium', 'high'}:
            raise ValueError('practice agent_payload.difficulty must be low, medium or high')
        normalized['focus_nodes'] = _normalize_string_list(normalized.get('focus_nodes'), field_name='focus_nodes')
        if normalized.get('question_count') is not None:
            try:
                normalized['question_count'] = int(normalized['question_count'])
            except (TypeError, ValueError):
                raise ValueError('practice agent_payload.question_count must be an integer')
        return normalized

    if agent == Conversation.AGENT_PROFILE:
        mode = normalized.get('mode')
        if mode is not None and mode not in {'collect_profile', 'refine_profile'}:
            raise ValueError('profile agent_payload.mode must be collect_profile or refine_profile')
        normalized['missing_dimensions'] = _normalize_string_list(
            normalized.get('missing_dimensions'),
            field_name='missing_dimensions',
        )
        return normalized

    if agent == Conversation.AGENT_CHAT:
        if normalized.get('scene') is not None:
            normalized['scene'] = str(normalized['scene']).strip()
        if normalized.get('goal') is not None:
            normalized['goal'] = str(normalized['goal']).strip()
        return normalized

    return normalized


def _normalize_handoff(value, *, expected_agent: str):
    handoff = _normalize_object_field(value)
    if handoff is None:
        return None
    normalized = dict(handoff)
    next_agent = normalized.get('next_agent')
    if next_agent is not None and next_agent not in {
        Conversation.AGENT_CHAT,
        Conversation.AGENT_PROFILE,
        Conversation.AGENT_PRACTICE,
        Conversation.AGENT_PLAN,
        Conversation.AGENT_VIDEO,
        Conversation.AGENT_TUTOR,
    }:
        raise ValueError('handoff.next_agent is invalid')
    if next_agent and next_agent != expected_agent:
        raise ValueError('handoff.next_agent must match conversation agent')
    payload = _normalize_object_field(normalized.get('payload'))
    if payload is None:
        raise ValueError('handoff.payload must be an object')
    normalized['payload'] = payload or {}
    if normalized.get('from_agent') is not None:
        normalized['from_agent'] = str(normalized['from_agent']).strip()
    extra_prompt = normalized.get('extra_prompt')
    normalized['extra_prompt'] = str(extra_prompt).strip() if extra_prompt is not None else None
    return normalized


# 包装 simplejwt 让它能在 async view 里跑
class AsyncJWTAuthentication(JWTAuthentication):
    async def authenticate(self, request):
        return await sync_to_async(super().authenticate)(request)

# MiMo 等兼容 API 将内容放在 reasoning_content 字段而非 content 字段
# 此补丁让 LangChain 的 ChatOpenAI 能正确处理 thinking 阶段
def _patch_reasoning_content():
    try:
        from langchain_openai.chat_models.base import _convert_delta_to_message_chunk
        from typing import Mapping, Any, cast
        from langchain_core.messages import BaseMessageChunk, AIMessageChunk, HumanMessageChunk, SystemMessageChunk, FunctionMessageChunk, ToolMessageChunk, ChatMessageChunk
        from langchain_core.messages.tool import tool_call_chunk

        _original = _convert_delta_to_message_chunk

        def _patched_convert_delta_to_message_chunk(
            _dict: Mapping[str, Any], default_class: type[BaseMessageChunk]
        ) -> BaseMessageChunk:
            id_ = _dict.get('id')
            role = cast(str, _dict.get('role'))
            content = _dict.get('content')
            reasoning = _dict.get('reasoning_content')

            # MiMo sends reasoning_content during thinking, content during actual response
            if content is None and reasoning:
                content = ''
            else:
                content = cast(str, content or '')
            additional_kwargs = {}
            if _dict.get('function_call'):
                function_call = dict(_dict['function_call'])
                if 'name' in function_call and function_call['name'] is None:
                    function_call['name'] = ''
                additional_kwargs['function_call'] = function_call
            tool_call_chunks = []
            if raw_tool_calls := _dict.get('tool_calls'):
                try:
                    tool_call_chunks = [
                        tool_call_chunk(
                            name=rtc['function'].get('name'),
                            args=rtc['function'].get('arguments'),
                            id=rtc.get('id'),
                            index=rtc['index'],
                        )
                        for rtc in raw_tool_calls
                    ]
                except KeyError:
                    pass

            if role == 'user' or default_class == HumanMessageChunk:
                return HumanMessageChunk(content=content, id=id_)
            if role == 'assistant' or default_class == AIMessageChunk:
                return AIMessageChunk(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    id=id_,
                    tool_call_chunks=tool_call_chunks,
                )
            if role in ('system', 'developer') or default_class == SystemMessageChunk:
                if role == 'developer':
                    additional_kwargs = {'__openai_role__': 'developer'}
                else:
                    additional_kwargs = {}
                return SystemMessageChunk(
                    content=content, id=id_, additional_kwargs=additional_kwargs
                )
            if role == 'function' or default_class == FunctionMessageChunk:
                return FunctionMessageChunk(content=content, name=_dict['name'], id=id_)
            if role == 'tool' or default_class == ToolMessageChunk:
                return ToolMessageChunk(
                    content=content, tool_call_id=_dict['tool_call_id'], id=id_
                )
            if role or default_class == ChatMessageChunk:
                return ChatMessageChunk(content=content, role=role, id=id_)
            return default_class(content=content, id=id_)

        import langchain_openai.chat_models.base
        langchain_openai.chat_models.base._convert_delta_to_message_chunk = _patched_convert_delta_to_message_chunk
    except Exception:
        pass

_patch_reasoning_content()


class UserRegisterView(APIView):
    """用户注册"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '注册成功',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """用户登录"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': '请提供邮箱和密码'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': '用户不存在'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(password):
            return Response(
                {'error': '密码错误'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        })


class UserProfileView(RetrieveUpdateAPIView):
    """用户画像获取/更新"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """获取用户画像 - 优先通过 subject_id，其次 subject(code)，否则取用户第一个 subject"""
        subject_id = self.request.query_params.get('subject_id')
        subject_code = self.request.query_params.get('subject')
        if subject_id:
            subject = Subject.objects.filter(user=self.request.user, id=subject_id).first()
        elif subject_code:
            subject = Subject.objects.filter(user=self.request.user, name=subject_code).first()
        else:
            subject = Subject.objects.filter(user=self.request.user).first()

        if not subject:
            raise Http404("用户还没有创建任何学科，请先创建学科")

        profile, _ = UserProfile.objects.get_or_create(subject=subject)
        return profile


class ProfileCompleteView(APIView):
    """POST /api/profile/complete/ - 标记画像完成并返回最新 profile"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subject_code = request.data.get('subject')
        if not subject_code:
            return Response({'error': 'subject is required'}, status=400)

        subject = Subject.objects.filter(user=request.user, name=subject_code).first()
        if not subject:
            raise Http404("学科不存在")

        profile, _ = UserProfile.objects.get_or_create(subject=subject)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


# ============== 学科接口 ==============

class SubjectViewSet(viewsets.ModelViewSet):
    """学科 ViewSet - 增删改查"""
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']

    def get_queryset(self):
        return Subject.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """GET /api/subjects/ - 返回预定义学科列表（用于前端"选学科" UI）"""
        subjects = [{'code': code, 'name': name} for code, name in Subject.SUBJECT_CHOICES]
        return Response({'subjects': subjects})

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        """GET /api/subjects/mine/ - 当前用户已选过的学科列表（含 id、display_name）。

        与 GET /api/subjects/ 区别：本接口返 Subject 序列化器（带 id），
        客户端拿这里的 id 就可以直接喂给 WS /api/conversations/ POST、
        以及对话创建接口等下游流程。
        """
        qs = self.get_queryset().order_by('id')
        serializer = SubjectSerializer(qs, many=True)
        return Response({'subjects': serializer.data})

    def create(self, request, *args, **kwargs):
        """POST /api/subjects/ - 创建用户学科（只能选择预定义学科）"""
        name = request.data.get('name')
        if not name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        valid_subjects = [choice[0] for choice in Subject.SUBJECT_CHOICES]
        if name not in valid_subjects:
            return Response({'error': f'Invalid subject. Must be one of: {valid_subjects}'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查课程是否已存在
        existing = Subject.objects.filter(user=request.user, name=name).first()
        if existing:
            return Response(
                {'error': '该课程已存在，不能重复创建', 'subject': SubjectSerializer(existing).data},
                status=status.HTTP_409_CONFLICT
            )

        subject = Subject.objects.create(user=request.user, name=name)

        # 初始化知识点
        self._initialize_knowledge_nodes(subject, name)

        return Response(
            SubjectSerializer(subject).data,
            status=status.HTTP_201_CREATED
        )

    def _initialize_knowledge_nodes(self, subject, subject_name):
        """根据学科名称初始化知识点"""
        from .knowledge_map import (
            data_structure_map, cybersecurity_map, iot_map,
            electrical_automation_map, mechanical_design_map,
            advanced_math_map, artificial_intelligence_map
        )

        knowledge_maps = {
            'data_structure': data_structure_map,
            'cybersecurity': cybersecurity_map,
            'iot': iot_map,
            'electrical_automation': electrical_automation_map,
            'mechanical_design': mechanical_design_map,
            'advanced_math': advanced_math_map,
            'artificial_intelligence': artificial_intelligence_map,
        }

        km = knowledge_maps.get(subject_name)
        if not km:
            return

        nodes_to_create = []
        for node in km['nodes']:
            nodes_to_create.append(KnowledgeNode(
                subject=subject,
                node_id=node['id'],
                name=node['name'],
                mastery=0
            ))

        if nodes_to_create:
            KnowledgeNode.objects.bulk_create(nodes_to_create)


# ============== 对话接口 ==============

class ConversationViewSet(viewsets.ModelViewSet):
    """对话会话 ViewSet"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['subject', 'agent']

    def get_queryset(self):
        return Conversation.objects.filter(subject__user=self.request.user)

    def list(self, request, *args, **kwargs):
        """GET /api/conversations/ - 返回对话会话列表，支持按 subject/agent 过滤"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ConversationListSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """POST /api/conversations/ - 创建新对话会话"""
        subject_id = request.data.get('subject_id')
        title = request.data.get('title', '新对话')
        agent = request.data.get('agent', Conversation.AGENT_CHAT)
        extra_prompt = request.data.get('extra_prompt')
        agent_payload = _normalize_object_field(request.data.get('agent_payload'))
        handoff = _normalize_object_field(request.data.get('handoff'))

        if not subject_id:
            return Response({'error': 'subject_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if agent not in {
            Conversation.AGENT_CHAT,
            Conversation.AGENT_PROFILE,
            Conversation.AGENT_PRACTICE,
            Conversation.AGENT_PLAN,
            Conversation.AGENT_VIDEO,
            Conversation.AGENT_TUTOR,
        }:
            return Response({'error': 'invalid agent'}, status=status.HTTP_400_BAD_REQUEST)
        if agent_payload is None:
            return Response({'error': 'agent_payload must be an object'}, status=status.HTTP_400_BAD_REQUEST)
        if handoff is None:
            return Response({'error': 'handoff must be an object'}, status=status.HTTP_400_BAD_REQUEST)

        subject = Subject.objects.filter(user=request.user, id=subject_id).first()
        if not subject:
            return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            normalized_handoff = _normalize_handoff(handoff, expected_agent=agent) or {}
            if not agent_payload and normalized_handoff.get('payload'):
                agent_payload = normalized_handoff['payload']
            normalized_agent_payload = _normalize_agent_payload(agent, agent_payload or {})
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if extra_prompt is None and normalized_handoff.get('extra_prompt'):
            extra_prompt = normalized_handoff['extra_prompt']
        if extra_prompt is not None:
            extra_prompt = str(extra_prompt).strip() or None

        conversation = Conversation.objects.create(
            subject=subject,
            title=title,
            agent=agent,
            extra_prompt=extra_prompt,
            agent_payload=normalized_agent_payload,
            handoff=normalized_handoff,
        )

        result = ConversationSerializer(conversation).data

        # Profile 对话：创建后自动触发 AI 开场白
        # Tutor 对话带 extra_prompt：也触发 AI 先根据上下文回复
        if agent == Conversation.AGENT_PROFILE or (agent == Conversation.AGENT_TUTOR and extra_prompt):
            from llm.runtime import mark_generating
            from llm.tasks import run_conversation_agent_task

            ai_msg = Message.objects.create(
                conversation=conversation, role='assistant', content='', meta={},
            )
            mark_generating(ai_msg.id, conversation.id)
            run_conversation_agent_task.delay(
                conversation_id=conversation.id,
                ai_message_id=ai_msg.id,
                user_message_id=0,
                agent_type=agent,
            )
            result['ai_message_id'] = ai_msg.id
            result['ai_state'] = 'generating'

        return Response(result, status=status.HTTP_201_CREATED)


class MessageViewSet(viewsets.ModelViewSet):
    """对话消息 ViewSet"""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch']

    def get_queryset(self):
        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            return Message.objects.filter(
                conversation__subject__user=self.request.user,
                conversation_id=conversation_id
            )
        return Message.objects.none()

    def perform_update(self, serializer):
        """PATCH /api/messages/{id}/ - 更新消息（用于保存用户答案等）。

        只允许更新自己对话里的消息。
        """
        # 权限校验：确保消息属于当前用户的对话
        message = self.get_object()
        if message.conversation.subject.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("无权修改此消息")
        serializer.save()

    def create(self, request, *args, **kwargs):
        """POST /api/messages/ - 发送消息（保留旧 API 路径，内部走新流程）

        同步 view：写 user msg + AI 占位消息，随后投递 Celery 任务。
        实际业务逻辑全在 _create_message_and_maybe_chat_sync。
        """
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content')
        role = request.data.get('role', 'user')
        meta = _normalize_message_meta(request.data.get('meta'))

        if not conversation_id or not content:
            return Response({'error': 'conversation_id and content are required'}, status=status.HTTP_400_BAD_REQUEST)
        if meta is None:
            return Response({'error': 'meta must be an object'}, status=status.HTTP_400_BAD_REQUEST)

        user_msg, ai_msg_id, ai_state = _create_message_and_maybe_chat_sync(
            user=request.user,
            conversation_id=conversation_id,
            content=content,
            role=role,
            meta=meta,
        )
        if user_msg is None:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        if ai_msg_id is not None:
            return Response({
                "user_message": MessageSerializer(user_msg).data,
                "ai_message_id": ai_msg_id,
                "ai_state": ai_state,
            }, status=status.HTTP_201_CREATED)
        return Response(MessageSerializer(user_msg).data, status=status.HTTP_201_CREATED)


class KnowledgeNodeViewSet(viewsets.ReadOnlyModelViewSet):
    """知识节点只读视图。

    ⚠️ 节点只能由 LangChain agent 通过 `assess_and_update_knowledge_score` /
    `get_knowledge_map` 工具修改；用户（包括管理员）不允许通过 HTTP 写入。
    """
    serializer_class = KnowledgeNodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = KnowledgeNode.objects.filter(subject__user=self.request.user)
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs.order_by('node_id')


class KnowledgeGraphView(APIView):
    """GET /api/knowledge-graph/<subject_code>/

    返回指定学科的完整知识图谱拓扑（来自 knowledge_map.py 静态字典）
    并合并用户在该学科下每个节点的 mastery 数据。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_code: str):
        from .knowledge_map import (
            data_structure_map, cybersecurity_map, iot_map,
            electrical_automation_map, mechanical_design_map,
            advanced_math_map, artificial_intelligence_map,
        )

        KNOWLEDGE_MAPS = {
            'data_structure': data_structure_map,
            'cybersecurity': cybersecurity_map,
            'iot': iot_map,
            'electrical_automation': electrical_automation_map,
            'mechanical_design': mechanical_design_map,
            'advanced_math': advanced_math_map,
            'artificial_intelligence': artificial_intelligence_map,
        }

        km = KNOWLEDGE_MAPS.get(subject_code)
        if not km:
            return Response(
                {'error': f'Unknown subject: {subject_code}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 深拷贝节点和关系，避免修改模块级字典
        nodes = [dict(n) for n in km['nodes']]
        relations = [dict(r) for r in km['relations']]

        # 合并用户的 mastery 数据（如果用户已添加该学科）
        try:
            subject = Subject.objects.get(user=request.user, name=subject_code)
            mastery_lookup = {
                kn.node_id: kn.mastery
                for kn in KnowledgeNode.objects.filter(subject=subject)
            }
            for node in nodes:
                node['mastery'] = mastery_lookup.get(node['id'], 0)
        except Subject.DoesNotExist:
            for node in nodes:
                node['mastery'] = 0

        return Response({'nodes': nodes, 'relations': relations})


# ============== 自由函数：写 user msg + 触发 chat task（两个 view 共享） ==============


def _create_message_and_maybe_chat_sync(*, user, conversation_id: int, content: str, role: str = "user", meta: dict | None = None):
    """同步版：写 user message + AI 占位消息 + 投递 Celery agent 任务。

    Returns:
        (user_msg, ai_msg_id_or_None, ai_state_or_None)
        - chat/profile/practice agent 触发：(user_msg, ai_msg_id, "generating")
        - 非 user：(user_msg, None, None)
        - conversation 不存在：(None, None, None)
    """
    from llm.runtime import mark_generating
    from llm.tasks import run_conversation_agent_task

    try:
        conversation = Conversation.objects.select_related('subject').get(
            id=conversation_id, subject__user=user,
        )
    except Conversation.DoesNotExist:
        return None, None, None

    # Plan Agent 对话不持久化消息，但 Celery 任务仍执行（计划变更写入 DB）
    if conversation.agent == Conversation.AGENT_PLAN:
        # 不写 user message，直接投递 Celery 任务
        # 但需要把 meta.selected_plan_ids 和用户消息内容合并到 conversation.agent_payload 中供 Celery task 读取
        ai_msg_id = None
        mark_generating(ai_msg_id, conversation.id)

        # 合并 selected_plan_ids 和用户消息到 agent_payload
        payload = dict(conversation.agent_payload or {})
        if isinstance(meta, dict) and "selected_plan_ids" in meta:
            payload["selected_plan_ids"] = meta["selected_plan_ids"]
        # 保存用户消息内容供 Celery task 恢复
        if content:
            payload["user_content"] = content
        conversation.agent_payload = payload
        conversation.save(update_fields=["agent_payload", "updated_at"])

        run_conversation_agent_task.delay(
            conversation_id=conversation.id,
            ai_message_id=ai_msg_id,
            user_message_id=None,
            agent_type=conversation.agent,
        )
        return None, ai_msg_id, "generating"

    # 写 user message
    user_msg = Message.objects.create(
        conversation=conversation, role=role, content=content, meta=meta or {},
    )
    conversation.save()  # 刷新 updated_at

    # 仅 user role + 已注册 agent 触发 LLM 任务
    if role != 'user' or conversation.agent not in {
        Conversation.AGENT_CHAT,
        Conversation.AGENT_PROFILE,
        Conversation.AGENT_PRACTICE,
        Conversation.AGENT_VIDEO,
        Conversation.AGENT_TUTOR,
    }:
        return user_msg, None, None

    # 同步建 AI 占位
    ai_msg = Message.objects.create(
        conversation=conversation, role='assistant', content='', meta={},
    )

    # 先写入 Redis 初始态，避免前端订阅过快时读不到消息状态。
    mark_generating(ai_msg.id, conversation.id)
    run_conversation_agent_task.delay(
        conversation_id=conversation.id,
        ai_message_id=ai_msg.id,
        user_message_id=user_msg.id,
        agent_type=conversation.agent,
    )

    return user_msg, ai_msg.id, "generating"


# ============== 新对话流：POST /api/conversations/<id>/messages/ ==============


class ConversationMessageCreateView(APIView):
    """POST /api/conversations/<conversation_id>/messages/

    HTTP 兼容入口（聊天 / 画像统一走这里）：
    - URL 自带 conversation_id（body 不用传）
    - 同步 view：写 user msg + AI 占位消息 + 投递 Celery 任务
    """
    # 留空 → DRF 用 settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']
    #       即 simplejwt JWTAuthentication
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id: int):
        content = (request.data.get("content") or "").strip()
        role = request.data.get("role", "user")
        meta = _normalize_message_meta(request.data.get("meta"))
        # Plan agent 不要求 content（对话不持久化，只做计划调整）
        try:
            conversation = Conversation.objects.select_related('subject').get(
                id=conversation_id, subject__user=request.user,
            )
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        is_plan_agent = conversation.agent == Conversation.AGENT_PLAN
        if not is_plan_agent and not content:
            return Response({"error": "content is required"}, status=status.HTTP_400_BAD_REQUEST)
        if meta is None:
            return Response({"error": "meta must be an object"}, status=status.HTTP_400_BAD_REQUEST)

        user_msg, ai_msg_id, ai_state = _create_message_and_maybe_chat_sync(
            user=request.user,
            conversation_id=conversation_id,
            content=content,
            role=role,
            meta=meta,
        )
        # Plan agent 返回 (None, None, "generating")
        if is_plan_agent:
            return Response({
                "user_message": None,
                "ai_message_id": None,
                "ai_state": ai_state,
            }, status=status.HTTP_201_CREATED)
        if user_msg is None:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        if ai_msg_id is not None:
            return Response({
                "user_message": MessageSerializer(user_msg).data,
                "ai_message_id": ai_msg_id,
                "ai_state": ai_state,
            }, status=status.HTTP_201_CREATED)
        return Response(MessageSerializer(user_msg).data, status=status.HTTP_201_CREATED)
