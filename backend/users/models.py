from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """自定义用户模型"""
    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    ]

    email = models.EmailField('邮箱', unique=True)
    avatar = models.ImageField('头像', upload_to='avatars/', null=True, blank=True)
    real_name = models.CharField('真实姓名', max_length=100, null=True, blank=True)
    gender = models.CharField('性别', max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    age = models.PositiveIntegerField('年龄', null=True, blank=True)
    occupation = models.CharField('职业', max_length=100, null=True, blank=True)
    city = models.CharField('城市', max_length=100, null=True, blank=True)
    bio = models.TextField('自我介绍', null=True, blank=True)
    learning_goal = models.TextField('学习目标', null=True, blank=True)
    interest_tags = models.JSONField('兴趣标签', default=list, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'


class Subject(models.Model):
    """学科模型"""
    SUBJECT_CHOICES = [
        ('data_structure', '数据结构'),
        ('cybersecurity', '网络安全'),
        ('iot', '物联网技术'),
        ('electrical_automation', 'Python 编程'),
        ('mechanical_design', '操作系统'),
        ('advanced_math', '软件工程'),
        ('artificial_intelligence', '人工智能'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField('学科名称', max_length=100, choices=SUBJECT_CHOICES)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '学科'
        verbose_name_plural = '学科'
        unique_together = ['user', 'name']

    def __str__(self):
        return f'{self.user.email} - {self.name}'

    def get_display_name(self):
        return dict(self.SUBJECT_CHOICES).get(self.name, self.name)


class UserProfile(models.Model):
    """用户画像模型（属于某个学科）"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='profile', null=True)
    course = models.CharField('课程', max_length=200, null=True, blank=True)
    knowledge_base = models.PositiveIntegerField('知识基础', default=0)
    cognitive_style = models.PositiveIntegerField('认知风格', default=0)
    learning_goal_score = models.PositiveIntegerField('学习目标', default=0)
    available_time = models.PositiveIntegerField('可用时间', default=0)
    common_mistakes = models.JSONField('易错知识点', default=list, blank=True)
    interest_direction = models.JSONField('兴趣方向', default=list, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '用户画像'
        verbose_name_plural = '用户画像'

    def __str__(self):
        return f'{self.subject.name} - Profile'

    def to_dict(self):
        """导出字典格式"""
        return {
            'id': self.id,
            'subject': self.subject.name if self.subject else None,
            'course': self.course,
            'knowledge_base': self.knowledge_base,
            'cognitive_style': self.cognitive_style,
            'learning_goal_score': self.learning_goal_score,
            'available_time': self.available_time,
            'common_mistakes': self.common_mistakes or [],
            'interest_direction': self.interest_direction or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_from_dict(self, data):
        """从字典更新"""
        if 'course' in data:
            self.course = data['course']
        if 'knowledge_base' in data:
            self.knowledge_base = data['knowledge_base']
        if 'cognitive_style' in data:
            self.cognitive_style = data['cognitive_style']
        if 'learning_goal_score' in data:
            self.learning_goal_score = data['learning_goal_score']
        if 'available_time' in data:
            self.available_time = data['available_time']
        if 'common_mistakes' in data:
            self.common_mistakes = data['common_mistakes']
        if 'interest_direction' in data:
            self.interest_direction = data['interest_direction']


class KnowledgeNode(models.Model):
    """知识点模型（属于某个学科的某个节点）"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='knowledge_nodes')
    node_id = models.CharField('知识点ID', max_length=10)  # 对应 knowledge_map 中的 id
    name = models.CharField('知识点名称', max_length=100)
    mastery = models.PositiveIntegerField('掌握程度', default=0)  # 0-100
    evidence_log = models.JSONField(
        '评估证据历史',
        default=list,
        blank=True,
        help_text='每条 {round, evidence, prev, new, delta_norm, actual_delta, rationale, ts}',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知识点'
        verbose_name_plural = '知识点'
        unique_together = ['subject', 'node_id']

    def __str__(self):
        return f'{self.subject.name} - {self.name}'


class Conversation(models.Model):
    """对话会话模型"""
    AGENT_CHAT = "chat"
    AGENT_PROFILE = "profile"
    AGENT_PRACTICE = "practice"
    AGENT_PLAN = "plan"
    AGENT_VIDEO = "video"
    AGENT_TUTOR = "tutor"
    AGENT_CHOICES = [
        (AGENT_CHAT, "聊天助手"),
        (AGENT_PROFILE, "画像构建"),
        (AGENT_PRACTICE, "练习出题"),
        (AGENT_PLAN, "学习计划"),
        (AGENT_VIDEO, "视频学习"),
        (AGENT_TUTOR, "AI 私教（多智能体）"),
    ]
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField('对话标题', max_length=200, default='新对话')
    agent = models.CharField(
        'agent 类型', max_length=20, choices=AGENT_CHOICES, default=AGENT_CHAT,
        help_text='决定这个对话走哪个 agent：chat=普通聊天，profile=画像构建，practice=练习出题，plan=学习计划协调，video=视频学习（统一走 WS）',
    )
    extra_prompt = models.TextField(
        '额外提示词', null=True, blank=True,
        help_text='注入到系统提示词中的额外指令，用于定制 agent 行为',
    )
    agent_payload = models.JSONField(
        'agent 配置',
        default=dict,
        blank=True,
        help_text='当前 agent 的结构化配置，不同 agent 使用不同字段',
    )
    handoff = models.JSONField(
        'agent 交接信息',
        default=dict,
        blank=True,
        help_text='上一个 agent 交接给当前会话的结构化信息',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.subject.name} - {self.title}'


class Message(models.Model):
    """对话消息模型（含 LangChain tool 消息支持）"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', 'AI助手'),
        ('tool', '工具返回'),
    ]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES)
    content = models.TextField('消息内容')
    meta = models.JSONField('附加元信息', default=dict, blank=True)
    tool_call_id = models.CharField('工具调用 ID', max_length=64, null=True, blank=True)
    tool_calls = models.JSONField('LLM 决策的工具调用', default=list, blank=True)
    tool_name = models.CharField('工具名', max_length=64, null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '对话消息'
        verbose_name_plural = '对话消息'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.content[:50]}...'
