import http from './http'
import { ENDPOINTS } from './endpoints'
import type {
  CreateConversationRequest,
  PersistedConversation,
  PersistedConversationListItem,
  PersistedMessage,
} from '@/types/chat'

// ============================================================
// 会话 / 消息 API —— 真后端 (backend ConversationViewSet / MessageViewSet)
//
// 2026-06 新约定:
//   GET    /api/conversations/                     列表 (ConversationListSerializer, 不带 messages)
//   GET    /api/conversations/<id>/                详情 (ConversationSerializer, 带 messages)
//   POST   /api/conversations/                     {subject_id, title?, agent?} 创建, 返详情
//   DELETE /api/conversations/<id>/                删
//   GET    /api/messages/?conversation=<id>        备用, 单独拉 transcript
//
// 注意: 与 WS 配合 — WS 连接前必须先 POST 拿到 conversation_id, URL 才知道连哪.
// ============================================================

export function listConversations(params?: {
  subject?: number             // backend filterset_fields=['subject','agent']
  agent?: string
}): Promise<{ data: PersistedConversationListItem[] }> {
  return http.get(ENDPOINTS.CONVERSATIONS, { params })
}

export function getConversation(id: number): Promise<{ data: PersistedConversation }> {
  return http.get(`${ENDPOINTS.CONVERSATIONS}${id}/`)
}

export function createConversation(
  payload: CreateConversationRequest,
): Promise<{ data: PersistedConversation }> {
  return http.post(ENDPOINTS.CONVERSATIONS, payload)
}

export function deleteConversation(id: number): Promise<{ data: void }> {
  return http.delete(`${ENDPOINTS.CONVERSATIONS}${id}/`)
}

// 备用: 单独按 conversation 拉消息列表
export function listMessages(conversationId: number): Promise<{
  data: PersistedMessage[]
}> {
  return http.get(ENDPOINTS.MESSAGES, { params: { conversation: conversationId } })
}

// 更新消息（用于保存用户答案）
export function updateMessage(
  messageId: number,
  payload: { meta?: Record<string, any> },
): Promise<{ data: PersistedMessage }> {
  return http.patch(`${ENDPOINTS.MESSAGES}${messageId}/`, payload)
}

export default {
  listConversations,
  getConversation,
  createConversation,
  deleteConversation,
  listMessages,
  updateMessage,
}
