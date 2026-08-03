from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegisterView, UserLoginView, UserProfileView,
    SubjectViewSet, ConversationViewSet, MessageViewSet,
    KnowledgeNodeViewSet, ConversationMessageCreateView,
    KnowledgeGraphView, ProfileCompleteView,
)

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
# 知识节点只读（写入只能由 LangChain agent 工具完成）
router.register(r'knowledge-nodes', KnowledgeNodeViewSet, basename='knowledge-node')

urlpatterns = [
    path('auth/register/', UserRegisterView.as_view(), name='auth-register'),
    path('auth/login/', UserLoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/complete/', ProfileCompleteView.as_view(), name='profile-complete'),
    # 学科 / 会话 / 消息 / 知识节点接口
    path('', include(router.urls)),
    # 对话内发消息（HTTP 兼容入口；主推荐流程改为会话 WS）
    path('conversations/<int:conversation_id>/messages/',
         ConversationMessageCreateView.as_view(),
         name='conversation-message-create'),
    # 知识图谱完整拓扑 + mastery（星图 3D 渲染用）
    path('knowledge-graph/<str:subject_code>/',
         KnowledgeGraphView.as_view(),
         name='knowledge-graph'),
    # 流式接口统一使用 ws/conversations/<id>/ 收发对话
]
