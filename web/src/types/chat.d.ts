// ============================================================
// 聊天 / 对话 类型 —— 2026-06 对齐新后端
//   - 后端: ConversationStreamConsumer (users/consumers.py) + ConversationViewSet
//   - WS URL: /ws/conversations/<id>/?token=<jwt>
//   - 创建会话: 必须先 POST /api/conversations/ {subject_id, title?, agent?}
//     然后才能 WS 连接到 <id>
// ============================================================

// ----- 持久层 (HTTP) -----

export type MessageRole = 'user' | 'assistant' | 'tool'
export type ConvAgent = 'chat' | 'profile' | 'practice' | 'plan' | 'video' | 'tutor'
export type AIState = 'idle' | 'generating' | 'complete' | string   // 也可能是 "error:<reason>"

export interface PersistedMessage {
  id: number
  role: MessageRole
  content: string
  meta?: Record<string, unknown>
  created_at: string
}

// GET /api/conversations/  —— ConversationListSerializer
//   字段更轻 (无 messages), 多了 subject_name / message_count / ai_state
export interface PersistedConversationListItem {
  id: number
  title: string
  agent: ConvAgent
  subject_name: string             // subject code, e.g. "data_structure"
  subject_display: string          // 显示名, e.g. "数据结构"
  message_count: number
  ai_state: AIState
  current_ai_message_id: number | null
  created_at: string
  updated_at: string
}

// GET /api/conversations/<id>/  —— ConversationSerializer
//   含 messages[], 用于打开某个会话恢复 transcript
export interface PersistedConversation {
  id: number
  title: string
  agent: ConvAgent
  messages: PersistedMessage[]
  ai_state: AIState
  current_ai_message_id: number | null
  created_at: string
  updated_at: string
}

// POST /api/conversations/  body —— 由 ConversationViewSet.create 验证
export interface CreateConversationRequest {
  subject_id: number               // 必填, MySubject.id
  title?: string                   // 默认 "新对话"
  agent?: ConvAgent                // 默认 "chat"
  extra_prompt?: string            // 可选, 注入系统提示词的"额外指令"段落
}

// ----- WebSocket 协议 (新) -----
//
// 入站 (C → S):
//   {type:"message", content:"...", role:"user"}
// 出站 (S → C):
//   history    — connect 后立刻回最近 6 条 transcript
//   state      — 当前 AI 状态 (idle / generating / complete / error)
//   resume     — 如果重连时 AI 还在生成, 把累计的 partial 内容一次性吐过来
//   accepted   — server 收到 user message, 返回 user_message + ai_message_id
//   chunk      — 增量 token (会带 ai_message_id 标识属于哪一条 AI 消息)
//   complete   — AI 完成 (带 meta: tokens/duration/model 等)
//   error      — 异常

export interface WSOutboundMessage {
  type: 'message'
  content: string
  role?: 'user'                    // 默认 user, 其它角色不开放给前端
  meta?: Record<string, unknown>   // 额外上下文（selected_plan_ids / preview / apply 等）
}

export interface WSEventHistory {
  type: 'history'
  conversation_id: number
  messages: PersistedMessage[]
}
export interface WSEventState {
  type: 'state'
  conversation_id: number
  ai_state: AIState
  current_ai_message_id: number | null
}
export interface WSEventResume {
  type: 'resume'
  conversation_id: number
  ai_message_id: number
  content: string                  // 一次性给到目前累计的所有内容
}
export interface WSEventAccepted {
  type: 'accepted'
  conversation_id: number
  user_message: PersistedMessage
  ai_message_id: number | null
  ai_state: AIState
}
export interface WSEventChunk {
  type: 'chunk'
  conversation_id: number
  ai_message_id: number
  content: string                  // 增量
}
export interface WSEventComplete {
  type: 'complete'
  conversation_id: number
  ai_message_id: number
  content: string                  // 完整内容
  meta?: Record<string, unknown>   // tokens / duration / model 等
}
export interface WSEventError {
  type: 'error'
  conversation_id?: number
  ai_message_id?: number
  message: string
}

// ----- LangChain agent tool 事件 -----
//   backend Celery task 在 agent 调工具时把这两个事件发出来.
//   chat agent 一般不调工具; practice agent 会调 get_knowledge_map / assess_and_update_knowledge_score.

export interface WSEventToolCall {
  type: 'tool_call'
  ai_message_id?: number
  tool_name: string
  tool_args?: Record<string, unknown> | string | null
  tool_call_id?: string
}

export interface WSEventToolResult {
  type: 'tool_result'
  ai_message_id?: number
  tool_name: string
  tool_output: string                                // 工具返回的字符串 (有时是 JSON 字符串)
  tool_call_id?: string
}

// ----- Agent 生命周期 + 模型 thinking (2026-06 加) -----
//   thinking_* 是模型原生思考过程 (Claude / OpenAI o-series 等),
//   用于前端显"AI 正在思考…" indicator; 内容可能含模型内部推理, 通常不直接显示给用户.

export interface WSEventStart {
  type: 'start'
  conversation_id: number
  ai_message_id: number
}
export interface WSEventEnd {
  type: 'end'
  conversation_id: number
  ai_message_id: number
}
export interface WSEventThinkingStart {
  type: 'thinking_start'
  conversation_id: number
  ai_message_id: number
}
export interface WSEventThinkingChunk {
  type: 'thinking_chunk'
  conversation_id: number
  ai_message_id: number
  content: string
}
export interface WSEventThinkingEnd {
  type: 'thinking_end'
  conversation_id: number
  ai_message_id: number
}
export interface WSEventSubAgentStart {
  type: 'sub_agent_start'
  sub_agent_type: string
  ai_message_id: number
}
export interface WSEventSubAgentEnd {
  type: 'sub_agent_end'
  sub_agent_type: string
  content?: string
  ai_message_id: number
  sub_message_id?: number
  meta?: Record<string, unknown>
}

// 校准事件
export interface WSEventCalibrationStart {
  type: 'calibration_start'
  ai_message_id: number
  total_messages: number
}
export interface WSEventCalibrationEnd {
  type: 'calibration_end'
  ai_message_id: number
  updated_count: number
  updated_nodes?: Array<{ name: string; node_id: string; result: string }>
  error?: string
}

export type WSInboundEvent =
  | WSEventHistory
  | WSEventState
  | WSEventResume
  | WSEventAccepted
  | WSEventStart
  | WSEventEnd
  | WSEventChunk
  | WSEventComplete
  | WSEventError
  | WSEventToolCall
  | WSEventToolResult
  | WSEventThinkingStart
  | WSEventThinkingChunk
  | WSEventThinkingEnd
  | WSEventSubAgentStart
  | WSEventSubAgentEnd
  | WSEventCalibrationStart
  | WSEventCalibrationEnd
  | WSEventSubAgentEnd
  | WSEventThinkingStart
  | WSEventThinkingChunk
  | WSEventThinkingEnd

// ----- 结构化题目 (2026-06) -----
//   后端 quiz chain (llm/chains/quiz_chain.py) 的输出形状.
//   通过 Celery 任务 run_quiz_generation_task 生成, 存到 Redis,
//   前端通过 HTTP 接口 (startQuizTask / getQuizResult) 拿.

export type QuestionType = 'choice' | 'short_answer' | 'true_false'
export type DifficultyLevel = 'easy' | 'medium' | 'hard'

export interface StructuredQuestion {
  question_type: QuestionType
  difficulty: DifficultyLevel
  knowledge_node_id: string
  knowledge_node_name: string
  question_text: string
  image_base64?: string | null
  options: string[] | null                            // null for short_answer / true_false
  correct_answer: string                              // 'A'/'B'/'C'/'D' for choice; 自由文本 for short_answer
  explanation: string                                 // AI 讲解 (静态, 嵌在题目里)
}

export type StructuredQuestionBatch = StructuredQuestion[]

// ----- Quiz 任务 (HTTP) -----
//   后端 run_quiz_generation_task / run_practice_analysis_task 走 Celery,
//   通过 HTTP 接口查询状态和拉结果.

export type QuizTaskState = 'generating' | 'complete' | 'error' | string
export interface QuizTaskStatus {
  task_id: string
  state: QuizTaskState
  result?: StructuredQuestionBatch
  message?: string
}

// ----- UI 内存模型 -----

export type ChatMessageKind = 'user' | 'assistant' | 'tool' | 'system' | string

export interface ChatMessage {
  id: string
  serverId?: number
  kind: ChatMessageKind
  content: string
  meta?: Record<string, any>
  thinkingContent?: string
  thinkingActive?: boolean
  toolName?: string
  pending?: boolean
  ts: string
  tmpId?: string
  subAgentType?: string
  failed?: boolean
}

// 子智能体信息
export interface SubAgentInfo { type: string; name: string; icon: string }
export const SUB_AGENT_MAP: Record<string, SubAgentInfo> = {
  exam:          { type: 'exam',          name: '出题助手', icon: '📝' },
  video:         { type: 'video',         name: '视频助手', icon: '🎬' },
  doc_assistant: { type: 'doc_assistant', name: '实践助手', icon: '🖥️' },
  doc_writer:    { type: 'doc_writer',    name: '图文助手', icon: '📄' },
}
