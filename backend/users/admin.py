from django.contrib import admin
from .models import User, UserProfile, Subject, KnowledgeNode, Conversation, Message


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'real_name', 'gender', 'age', 'occupation', 'city']
    search_fields = ['username', 'email', 'real_name']
    list_filter = ['gender', 'occupation']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'name', 'created_at']
    search_fields = ['user__email', 'name']
    list_filter = ['name']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'course', 'knowledge_base', 'cognitive_style', 'learning_goal_score', 'available_time', 'created_at']
    search_fields = ['subject__name', 'course']
    list_filter = ['course']


@admin.register(KnowledgeNode)
class KnowledgeNodeAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'node_id', 'name', 'mastery', 'created_at']
    search_fields = ['subject__name', 'name', 'node_id']
    list_filter = ['subject__name']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'title', 'agent', 'created_at', 'updated_at']
    search_fields = ['subject__name', 'title']
    list_filter = ['subject__name', 'agent']
    readonly_fields = ['agent_payload', 'handoff']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'content', 'created_at']
    search_fields = ['conversation__title', 'content']
    list_filter = ['role']
