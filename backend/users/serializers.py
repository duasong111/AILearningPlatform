from rest_framework import serializers
from django.core.cache import cache

from llm.state_keys import conv_ai_state, conv_current_ai_msg
from .models import User, UserProfile, Subject, KnowledgeNode, Conversation, Message


class SubjectSerializer(serializers.ModelSerializer):
    """学科序列化器"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'display_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_display_name(self, obj):
        return obj.get_display_name()


class UserSerializer(serializers.ModelSerializer):
    """用户基本信息序列化器"""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'avatar', 'real_name',
            'gender', 'age', 'occupation', 'city', 'bio',
            'learning_goal', 'interest_tags'
        ]
        read_only_fields = ['id', 'email']


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """用户画像序列化器"""
    subject = SubjectSerializer(read_only=True)
    is_complete = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            'id', 'subject', 'course', 'knowledge_base', 'cognitive_style',
            'learning_goal_score', 'available_time', 'common_mistakes',
            'interest_direction', 'created_at', 'updated_at', 'is_complete',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_complete']

    def get_is_complete(self, obj) -> bool:
        """画像完整度：前端 onboarding 流程依赖此字段判断是否可进入主页。"""
        from llm.common import profile_is_complete
        return profile_is_complete({
            "learning_goal": {
                "goal": getattr(obj, "course", None),
                "priority": int(obj.learning_goal_score or 0),
            },
            "knowledge_base": {
                "level": int(obj.knowledge_base or 0),
                "strong_areas": [],
                "weak_areas": list(obj.common_mistakes or []),
                "recommended_courses": [obj.course] if obj.course else [],
            },
            "cognitive_style": {
                "description": "",
                "score": int(obj.cognitive_style or 0),
            },
            "available_time": int(obj.available_time or 0),
            "interest_direction": list(obj.interest_direction or []),
        })


class MessageSerializer(serializers.ModelSerializer):
    """对话消息序列化器"""

    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'meta', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """对话会话序列化器（详情）"""
    messages = MessageSerializer(many=True, read_only=True)
    subject_id = serializers.IntegerField(write_only=True, source='subject.id')
    # 从 Redis 读出的瞬时态字段
    ai_state = serializers.SerializerMethodField()
    current_ai_message_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'subject_id', 'title', 'agent', 'extra_prompt', 'agent_payload', 'handoff', 'messages',
            'ai_state', 'current_ai_message_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_ai_state(self, obj):
        return cache.get(conv_ai_state(obj.id), "idle")

    def get_current_ai_message_id(self, obj):
        return cache.get(conv_current_ai_msg(obj.id))


class ConversationListSerializer(serializers.ModelSerializer):
    """对话会话列表序列化器（不带消息）"""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_display = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    # 从 Redis 读出的瞬时态字段
    ai_state = serializers.SerializerMethodField()
    current_ai_message_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'agent', 'extra_prompt', 'agent_payload', 'handoff',
            'subject_name', 'subject_display', 'message_count',
            'ai_state', 'current_ai_message_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subject_display(self, obj):
        return obj.subject.get_display_name()

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_ai_state(self, obj):
        return cache.get(conv_ai_state(obj.id), "idle")

    def get_current_ai_message_id(self, obj):
        return cache.get(conv_current_ai_msg(obj.id))


class KnowledgeNodeSerializer(serializers.ModelSerializer):
    """知识节点只读序列化器 —— 节点只能由 agent 工具修改，
    客户端只能 GET。"""
    subject_id = serializers.IntegerField(source='subject.id', read_only=True)
    evidence_count = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeNode
        fields = ['id', 'subject_id', 'node_id', 'name', 'mastery', 'evidence_count', 'created_at', 'updated_at']
        read_only_fields = fields  # 整张表只读

    def get_evidence_count(self, obj):
        return len(obj.evidence_log or [])
