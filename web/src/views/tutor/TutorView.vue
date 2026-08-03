<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { getSubjectDisplayName } from '@/api/subjects'
import { createConversation, deleteConversation, getConversation, listConversations, updateMessage } from '@/api/conversations'
import { useConvWS } from '@/composables/use_conv_ws'
import StreamingMarkdown from '@/components/StreamingMarkdown.vue'
import tutorAvatar from '@/assets/chat/teacher1.png'
import examAvatar from '@/assets/chat/chuti.png'
import videoAvatar from '@/assets/chat/shipin.png'
import practiceAvatar from '@/assets/chat/shijian.png'
import writerAvatar from '@/assets/chat/tuwen.png'
import type {
  ChatMessage, ChatMessageKind, PersistedConversationListItem, WSInboundEvent, SubAgentInfo,
} from '@/types/chat'

/** 子智能体信息映射（与 chat.d.ts 中的 SUB_AGENT_MAP 保持一致，但作为运行时常量） */
const SUB_AGENT_MAP: Record<string, SubAgentInfo> = {
  exam:           { type: 'exam',           name: '出题助手', icon: '📝' },
  practice_quiz:  { type: 'practice_quiz',  name: '出题助手', icon: '✏️' },
  video:          { type: 'video',          name: '视频助手', icon: '🎬' },
  doc_assistant:  { type: 'doc_assistant',  name: '实践助手', icon: '🖥️' },
  doc_writer:     { type: 'doc_writer',     name: '图文助手', icon: '📄' },
}

const mySubjects = useMySubjectsStore()
const currentSubject = useCurrentSubjectStore()
const route = useRoute()
const router = useRouter()

const currentSubjectId = computed<number | null>(() => {
  const code = currentSubject.code
  if (!code) return null
  const s = mySubjects.subjects.find((m) => m.name === code)
  return s?.id ?? null
})

const currentConvId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const composeText = ref('')
const sending = ref(false)
const inFlight = ref(false)

// 对话列表
const conversations = ref<PersistedConversationListItem[]>([])
const loadingConvs = ref(false)

async function loadConversations(): Promise<void> {
  if (!currentSubjectId.value) return
  loadingConvs.value = true
  try {
    const { data } = await listConversations({ agent: 'tutor', subject: currentSubjectId.value! })
    conversations.value = [...(data ?? [])].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
  } catch { /* 静默失败 */ }
  finally { loadingConvs.value = false }
}

async function switchConversation(id: number): Promise<void> {
  if (id === currentConvId.value) return
  // 断开当前 WS 并切换
  ws.close()
  currentConvId.value = id
  messages.value = []
  currentAIBubbleId.value = null
  currentAIServerId.value = null
  try {
    const { data } = await getConversation(id)
    messages.value = (data.messages ?? [])
      .map((m) => {
        const meta = (m.meta || {}) as Record<string, any>
        return {
          id: `srv-${m.id}`, serverId: m.id,
          kind: meta.sub_agent_type
            || (m.role === 'tool' ? 'tool' : (m.role as 'user' | 'assistant')),
          content: m.content,
          meta: meta,
          thinkingContent: meta.thinking_content || undefined,
          thinkingActive: false,
          pending: false,
          ts: m.created_at,
        }
      })
      .sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime())
    // 等待一小段时间确保旧的 WS 完全关闭
    await new Promise(resolve => setTimeout(resolve, 100))
    await ws.connect(id, 'tutor')
    await loadConversations() // 刷新列表排序
  } catch (err) {
    pushSystem(`× 加载对话失败: ${err instanceof Error ? err.message : 'unknown'}`)
    // 连接失败时重置状态
    currentConvId.value = null
    messages.value = []
  }
}

async function handleDeleteConversation(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？删除后不可恢复。', '删除对话', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
    })
  } catch { return }
  try {
    await deleteConversation(id)
    if (currentConvId.value === id) {
      // 删除的是当前对话 → 切换到第一个其他对话或新建
      const remaining = conversations.value.filter(c => c.id !== id)
      if (remaining.length > 0) {
        await switchConversation(remaining[0]!.id)
      } else {
        messages.value = []
        currentConvId.value = null
        currentAIBubbleId.value = null
        currentAIServerId.value = null
        await handleNewChat()
      }
    }
    await loadConversations()
  } catch (err) { ElMessage.error(`删除失败: ${err instanceof Error ? err.message : 'unknown'}`) }
}

const currentSubAgent = ref<string>('')
const agentStatuses = ref<Record<string, 'idle' | 'working'>>({
  tutor: 'idle', exam: 'idle', practice_quiz: 'idle', video: 'idle', doc_assistant: 'idle', doc_writer: 'idle',
})
const AGENT_LIST: Record<string, { icon: string; name: string; avatar?: string }> = {
  // 5 个 agent 都用真实头像 (assets/chat/ 下 5 张图), 不再显示 emoji
  tutor:          { icon: '', name: '私教老师', avatar: tutorAvatar },     // teacher1.png
  exam:           { icon: '', name: '出题助手', avatar: examAvatar },       // chuti.png
  practice_quiz:  { icon: '', name: '出题助手', avatar: examAvatar },       // 复用 chuti.png
  video:          { icon: '', name: '视频助手', avatar: videoAvatar },      // shipin.png
  doc_assistant:  { icon: '', name: '实践助手', avatar: practiceAvatar },   // shijian.png
  doc_writer:     { icon: '', name: '图文助手', avatar: writerAvatar },     // tuwen.png
}

// 当前选中的 agent —— 默认 tutor (私教), 点击切换
const selectedAgent = ref<keyof typeof AGENT_LIST>('tutor')
function selectAgent(type: keyof typeof AGENT_LIST): void {
  selectedAgent.value = type
}
const AGENT_COLORS: Record<string, string> = {
  tutor: '#1E5AE0', exam: '#7C3AED', practice_quiz: '#7C3AED', video: '#F59E0B', doc_assistant: '#10B981', doc_writer: '#8B5CF6',
}

const drawerOpen = ref<boolean>(true)
function toggleDrawer(): void { drawerOpen.value = !drawerOpen.value }

// ── 实践助手场景播放器状态 ──
const docFullscreen = ref<{ msgId: string; scenes: Array<{ title: string; html: string }>; sceneIdx: number; examSessionId?: number } | null>(null)
const docFsRef = ref<HTMLElement | null>(null)
function openDocFullscreen(msgId: string, scenes: Array<{ title: string; html: string }>, sceneIdx: number): void {
  docFullscreen.value = { msgId, scenes, sceneIdx }
  void nextTick().then(() => { docFsRef.value?.requestFullscreen?.().catch(() => {}) })
}
function closeDocFullscreen(): void {
  document.fullscreenElement && document.exitFullscreen?.().catch(() => {})
  docFullscreen.value = null
}
function onFullscreenChange(): void { if (!document.fullscreenElement) docFullscreen.value = null }
const docSceneIndex = ref<Record<string, number>>({})
const docBlobUrls = ref<Record<string, string>>({})
function getDocSceneIdx(msgId: string): number { return docSceneIndex.value[msgId] ?? 0 }
function setDocSceneIdx(msgId: string, idx: number, total: number): void {
  const clamped = Math.max(0, Math.min(idx, total - 1))
  docSceneIndex.value = { ...docSceneIndex.value, [msgId]: clamped }
}
function getDocBlobUrl(msgId: string, scenes: Array<{ html: string }>): string {
  const idx = getDocSceneIdx(msgId)
  const scene = scenes[idx]
  if (!scene?.html) return ''
  // 清理旧 blob URL
  const oldUrl = docBlobUrls.value[msgId]
  if (oldUrl) URL.revokeObjectURL(oldUrl)
  const blob = new Blob([scene.html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  docBlobUrls.value = { ...docBlobUrls.value, [msgId]: url }
  return url
}

const currentAIBubbleId = ref<string | null>(null)
const currentAIServerId = ref<number | null>(null)
const scrollerRef = ref<HTMLElement | null>(null)

function uid(): string { return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}` }
function nowIso(): string { return new Date().toISOString() }
function fmtTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60_000) return '刚刚'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)} 小时前`
  return `${d.getMonth() + 1}/${d.getDate()}`
}
function pushSystem(text: string): void {
  messages.value.push({ id: uid(), kind: 'system', content: text, pending: false, ts: nowIso() })
}

const STALL_TIMEOUT_MS = 100_000
let stallTimer: number | null = null
const lastStallMessageId = ref<string | null>(null)
const lastSentText = ref<string>('')
const STALL_HINT = ['⏱ AI 100s 未响应。', '请确认 Celery worker 已启动：cd backend && celery -A config worker -l info', '启动后点「重试」。'].join('\n')
function armStallWatchdog(): void {
  clearStallWatchdog()
  stallTimer = window.setTimeout(() => {
    const id = uid()
    messages.value.push({ id, kind: 'system', content: STALL_HINT, pending: false, ts: nowIso() })
    lastStallMessageId.value = id; stallTimer = null
  }, STALL_TIMEOUT_MS)
}
function clearStallWatchdog(): void { if (stallTimer !== null) { window.clearTimeout(stallTimer); stallTimer = null } }

function ensureAIBubble(serverId: number): ChatMessage {
  // 如果 serverId 变了，说明是新的 AI 回复，先把上一个气泡关掉
  if (currentAIServerId.value && currentAIServerId.value !== serverId) {
    finalizeAIBubble()
  }
  if (currentAIServerId.value === serverId && currentAIBubbleId.value) {
    const cur = messages.value.find((m) => m.id === currentAIBubbleId.value)
    if (cur) return cur
  }
  const existing = messages.value.find((m) => m.serverId === serverId && m.kind === 'assistant')
  if (existing) { currentAIBubbleId.value = existing.id; currentAIServerId.value = serverId; existing.pending = true; return existing }
  const bubble: ChatMessage = { id: uid(), serverId, kind: 'assistant', content: '', pending: true, ts: nowIso() }
  messages.value.push(bubble); currentAIBubbleId.value = bubble.id; currentAIServerId.value = serverId
  return bubble
}
function finalizeAIBubble(): void {
  if (!currentAIBubbleId.value) return
  const cur = messages.value.find((m) => m.id === currentAIBubbleId.value)
  if (cur) cur.pending = false
  currentAIBubbleId.value = null; currentAIServerId.value = null
}

function handleWSEvent(ev: WSInboundEvent): void {
  switch (ev.type) {
    case 'history': {
      if (!ev.messages || !Array.isArray(ev.messages)) break
      const fromServer = ev.messages
        .map<ChatMessage>((m) => {
          const meta = (m.meta || {}) as Record<string, any>
          return {
            id: `srv-${m.id}`, serverId: m.id,
            kind: meta.sub_agent_type
              || (m.role === 'tool' ? 'tool' : (m.role as 'user' | 'assistant')),
            content: m.content,
            meta: meta,
            thinkingContent: meta.thinking_content || undefined,
            thinkingActive: false,
            pending: false,
            ts: m.created_at,
          }
        })
      const serverIds = new Set(fromServer.map((m) => m.serverId))
      const localOnly = messages.value.filter((m) => !m.serverId || !serverIds.has(m.serverId))
      messages.value = [...fromServer, ...localOnly]; scrollToBottom()
      break
    }
    case 'state':
      // 只有当确实在等待 AI 回复时才响应 generating 状态
      // 避免页面刷新后 Redis 残留的旧 generating 状态导致光标闪烁
      if (ev.ai_state === 'generating' && ev.current_ai_message_id && inFlight.value) {
        ensureAIBubble(ev.current_ai_message_id); agentStatuses.value['tutor'] = 'working'
      } else if (ev.ai_state === 'idle') {
        finalizeAIBubble(); sending.value = false; inFlight.value = false; agentStatuses.value['tutor'] = 'idle'
        for (const k of Object.keys(agentStatuses.value)) { if (k !== 'tutor') agentStatuses.value[k] = 'idle' }
      }
      break
    case 'resume': {
      // 只在确实等待回复时才恢复流式内容，避免刷新后旧状态覆盖已保存的消息
      if (!inFlight.value) break
      clearStallWatchdog(); const b = ensureAIBubble(ev.ai_message_id); b.content = ev.content; b.pending = true; scrollToBottom(); break
    }
    case 'accepted':
      if (ev.user_message) {
        const lu = [...messages.value].reverse().find((m) => m.kind === 'user' && !m.serverId)
        if (lu) { lu.serverId = ev.user_message.id; lu.content = ev.user_message.content }
        else messages.value.push({ id: `srv-${ev.user_message.id}`, serverId: ev.user_message.id, kind: 'user', content: ev.user_message.content, pending: false, ts: ev.user_message.created_at })
      }
      if (ev.ai_message_id) { ensureAIBubble(ev.ai_message_id); armStallWatchdog() }
      scrollToBottom()
      break
    case 'thinking_chunk': {
      clearStallWatchdog()
      const b = ensureAIBubble(ev.ai_message_id)
      b.thinkingContent = (b.thinkingContent || '') + ev.content
      b.thinkingActive = true
      scrollToBottom()
      break
    }
    case 'chunk': {
      clearStallWatchdog()
      const b = ensureAIBubble(ev.ai_message_id)
      // 正文开始输出时，标记思考已结束
      if (b.thinkingActive) b.thinkingActive = false
      b.content += ev.content; scrollToBottom()
      break
    }
    case 'complete': {
      clearStallWatchdog(); const b = ensureAIBubble(ev.ai_message_id)
      b.content = ev.content; b.pending = false
      // 从 meta 恢复思考过程（断线重连场景）
      if ((ev as any).meta?.thinking_content) b.thinkingContent = (ev as any).meta.thinking_content
      b.thinkingActive = false
      finalizeAIBubble(); sending.value = false; inFlight.value = false
      agentStatuses.value['tutor'] = 'idle'
      for (const k of Object.keys(agentStatuses.value)) { if (k !== 'tutor') agentStatuses.value[k] = 'idle' }
      break
    }
    case 'end': {
      // LangGraph 流结束事件 —— 兜底复位所有状态
      finalizeAIBubble(); sending.value = false; inFlight.value = false
      agentStatuses.value['tutor'] = 'idle'
      for (const k of Object.keys(agentStatuses.value)) { if (k !== 'tutor') agentStatuses.value[k] = 'idle' }
      break
    }
    case 'sub_agent_start': {
      const info = SUB_AGENT_MAP[ev.sub_agent_type]
      if (info) {
        currentSubAgent.value = ev.sub_agent_type
        agentStatuses.value[ev.sub_agent_type] = 'working'

        // 所有 Agent：立刻插入骨架屏气泡，避免用户盲等。
        // 用稳定的临时 id，end 时按 id 找到它替换为真实内容。
        const startMeta = ((ev as any).meta || {}) as Record<string, any>
        messages.value.push({
          id: `sub-${ev.sub_agent_type}-${ev.ai_message_id}`,
          serverId: undefined,
          kind: ev.sub_agent_type as ChatMessageKind,
          content: '',
          meta: { generating: true, ...startMeta },
          pending: true,
          ts: new Date().toISOString(),
        })
        scrollToBottom()
      }
      break
    }
    case 'sub_agent_end': {
      const info = SUB_AGENT_MAP[ev.sub_agent_type]
      if (info) {
        agentStatuses.value[ev.sub_agent_type] = 'idle'
        const meta = ((ev as any).meta || {}) as Record<string, any>
        // 找到 start 时插的骨架屏气泡，把真实数据合并进去
        const skelId = `sub-${ev.sub_agent_type}-${ev.ai_message_id}`
        const skel = messages.value.find((m) => m.id === skelId)
        if (skel) {
          skel.serverId = ev.sub_message_id
          skel.meta = { ...(skel.meta || {}), ...meta, generating: false }
          skel.content = ev.content || ''
          skel.pending = false
        } else {
          // 兜底：万一 start 没抢到（比如刷新后从 history 进来），新建一个
          messages.value.push({
            id: skelId,
            serverId: ev.sub_message_id,
            kind: ev.sub_agent_type as ChatMessageKind,
            content: ev.content || '',
            meta,
            pending: false,
            ts: new Date().toISOString(),
          })
        }
      }
      currentSubAgent.value = ''
      break
    }
    case 'calibration_start': {
      // 在当前 AI 气泡里显示校准进度
      const bubble = messages.value.find((m) => m.serverId === ev.ai_message_id)
      if (bubble) {
        bubble.meta = { ...(bubble.meta || {}), calibrating: true }
      }
      break
    }
    case 'calibration_end': {
      const bubble = messages.value.find((m) => m.serverId === ev.ai_message_id)
      if (bubble) {
        const updatedNodes = (ev as any).updated_nodes || []
        const errorMsg = (ev as any).error
        bubble.meta = {
          ...(bubble.meta || {}),
          calibrating: false,
          calibrationResult: errorMsg
            ? { error: errorMsg }
            : { updated_count: ev.updated_count, updated_nodes: updatedNodes },
        }
      }
      break
    }
    case 'error': clearStallWatchdog(); finalizeAIBubble(); pushSystem(`× ${ev.message}`); sending.value = false; inFlight.value = false; break
  }
}

const ws = useConvWS({
  onEvent: handleWSEvent,
  onClose: (reason) => {
    console.log('[ws] onClose:', reason)
    clearStallWatchdog()
    sending.value = false
    inFlight.value = false
    // 如果是异常关闭，提示用户
    if (reason.code !== 1000 && reason.code !== 1005) {
      pushSystem(`⚠ WebSocket 断开 (${reason.code}): ${reason.reason}`)
    }
  },
})

async function handleNewChat(): Promise<void> {
  if (!currentSubjectId.value) return
  try {
    const code = currentSubject.code
    const pp = sessionStorage.getItem('aiteach.plan_prompt'); if (pp) sessionStorage.removeItem('aiteach.plan_prompt')
    const { data } = await createConversation({ subject_id: currentSubjectId.value, title: `${getSubjectDisplayName(code)} 对话`, agent: 'tutor', extra_prompt: pp || undefined })
    currentConvId.value = data.id; messages.value = []; currentAIBubbleId.value = null; currentAIServerId.value = null
    // 等待一小段时间确保状态清理完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await ws.connect(data.id, 'tutor')
    await loadConversations()
  } catch (err) {
    pushSystem(`× 创建对话失败: ${err instanceof Error ? err.message : 'unknown'}`)
    // 创建失败时重置状态
    currentConvId.value = null
    messages.value = []
  }
}

async function handleSend(): Promise<void> {
  const text = composeText.value.trim()
  if (!text || sending.value) return
  if (!currentConvId.value) { await handleNewChat(); if (!currentConvId.value) return }

  // 确保 WebSocket 已连接
  if (ws.status.value !== 'open') {
    try {
      console.log('[handleSend] WebSocket not open, connecting...', ws.status.value)
      await ws.connect(currentConvId.value!, 'tutor')
      console.log('[handleSend] WebSocket connected, status:', ws.status.value)
    } catch (err) {
      console.error('[handleSend] WebSocket connection failed:', err)
      pushSystem(`× WebSocket 连接失败: ${err instanceof Error ? err.message : 'unknown'}`)
      return
    }
  }

  const userMsg = { id: uid(), kind: 'user' as const, content: text, pending: true, failed: false, ts: nowIso() }
  messages.value.push(userMsg)
  composeText.value = ''
  lastSentText.value = text
  lastStallMessageId.value = null
  sending.value = true
  inFlight.value = true
  await scrollToBottom()

  console.log('[handleSend] Sending message via WebSocket:', { type: 'message', content: text, convId: currentConvId.value })
  const sendResult = ws.send({ type: 'message', content: text, role: 'user' })
  console.log('[handleSend] Send result:', sendResult, 'ws status:', ws.status.value)

  if (!sendResult) {
    userMsg.failed = true
    userMsg.pending = false
    sending.value = false
    inFlight.value = false
    pushSystem('× 发送失败: WebSocket 未连接')
    console.error('[handleSend] WebSocket send failed')
  } else {
    userMsg.pending = false
    console.log('[handleSend] Message sent successfully')
  }
}
function onComposeKey(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) { e.preventDefault(); handleSend() }
}
function handleRetrySend(): void { if (lastSentText.value) { composeText.value = lastSentText.value; handleSend() } }
async function scrollToBottom(): Promise<void> { await nextTick(); const el = scrollerRef.value; if (el) el.scrollTop = el.scrollHeight }

// ── 答题处理 ──
async function handleQuizAnswer(m: ChatMessage, questionIndex: number, answer: string): Promise<void> {
  if (!m.serverId || !m.meta?.questions) return
  const questions = [...(m.meta.questions || [])]
  if (!questions[questionIndex]) return

  // 本地先更新
  questions[questionIndex] = { ...questions[questionIndex], user_answer: answer }
  m.meta = { ...m.meta, questions }

  // 异步保存到后端
  try {
    await updateMessage(m.serverId, { meta: { ...m.meta } })
  } catch (err) {
    console.error('保存答案失败', err)
    ElMessage.error('答案保存失败，请稍后重试')
    // 回滚本地状态
    questions[questionIndex].user_answer = undefined
    m.meta = { ...m.meta, questions }
  }
}

const noSubject = computed(() => mySubjects.subjects.length === 0)

async function autoConnectTutor(): Promise<void> {
  if (noSubject.value) return
  try {
    // 如果 URL 中指定了对话 ID，直接打开该对话
    const convIdFromQuery = route.query.conv
    if (convIdFromQuery) {
      const id = Number(convIdFromQuery)
      if (Number.isFinite(id) && id > 0) {
        await loadConversations()
        await switchConversation(id)
        // 清除 URL 中的参数
        router.replace({ query: {} })
        return
      }
    }

    await loadConversations()
    if (conversations.value.length > 0) {
      const conv = conversations.value[0]!
      await switchConversation(conv.id)
      return
    }
    await handleNewChat()
  } catch (err) {
    console.error('autoConnectTutor error:', err)
    pushSystem(`× 加载对话失败: ${err instanceof Error ? err.message : 'unknown'}`)
    // 连接失败时重置状态
    currentConvId.value = null
    messages.value = []
  }
}
function onDocFsKey(e: KeyboardEvent): void { if (e.key === 'Escape' && docFullscreen.value) closeDocFullscreen() }
onMounted(async () => { await mySubjects.loadFromBackend(); await autoConnectTutor(); window.addEventListener('keydown', onDocFsKey); document.addEventListener('fullscreenchange', onFullscreenChange) })
onUnmounted(() => { window.removeEventListener('keydown', onDocFsKey); document.removeEventListener('fullscreenchange', onFullscreenChange) })

/**
 * 切学科时: 关旧 ws + 清消息 + 重新 autoConnect (拿新学科的 conv).
 *
 *   之前切学科 currentConvId 不变 → AI 拿旧学科的 system_prompt → 答错内容.
 *   这个 watch 是修复点 (对标 PlanScheduleView.vue:702 的同名 watch).
 */
watch(() => currentSubject.code, async () => {
  if (noSubject.value) return
  ws.close()
  currentConvId.value = null
  messages.value = []
  currentAIBubbleId.value = null
  currentAIServerId.value = null
  await autoConnectTutor()
})
</script>

<template>
  <div class="x-tutor">
    <!-- 左侧：对话列表 -->
    <aside class="x-side x-side--convs" :class="{ 'is-folded': !drawerOpen }">
      <div v-if="drawerOpen" class="x-side-inner">
        <div class="x-conv-hd">
          <span class="x-side-ttl">对话列表</span>
          <button class="x-new-btn" @click="handleNewChat" :disabled="sending">+ 新建</button>
        </div>
        <div class="x-conv-list">
          <div v-if="conversations.length === 0 && !loadingConvs" class="x-conv-empty">暂无对话</div>
          <div
            v-for="conv in conversations" :key="conv.id"
            class="x-conv-item" :class="{ 'is-active': conv.id === currentConvId }"
            @click="switchConversation(conv.id)"
          >
            <div class="x-conv-info">
              <span class="x-conv-title">{{ conv.title }}</span>
              <span class="x-conv-meta">{{ conv.message_count }} 条消息 · {{ fmtTime(conv.updated_at) }}</span>
            </div>
            <button class="x-conv-del" @click.stop="handleDeleteConversation(conv.id)" title="删除对话">×</button>
          </div>
        </div>
      </div>
      <button v-if="drawerOpen" class="x-side-fold" @click="toggleDrawer">◀</button>
      <button v-else class="x-side-fold x-side-fold--exp" @click="toggleDrawer">▶</button>
    </aside>

    <!-- 中间：聊天区 -->
    <section class="x-chat">
      <div v-if="noSubject" class="x-empty">
        <span class="x-empty-ico">📚</span>
        <p class="x-empty-ttl">还没有选课</p>
        <p class="x-empty-sub">在「我的课程」中添加学科后开始</p>
        <router-link class="x-btn" to="/app/plan">去添加 →</router-link>
      </div>

      <div v-else ref="scrollerRef" class="x-msgs">
        <div v-if="messages.length === 0 && currentConvId" class="x-empty">
          <div class="x-empty-squad">
            <span v-for="(info, type) in AGENT_LIST" :key="type" class="x-empty-sq">
              <img v-if="info.avatar" :src="info.avatar" :alt="info.name" class="x-empty-sq-img" />
              <template v-else>{{ info.icon }}</template>
            </span>
          </div>
          <p class="x-empty-ttl">智能体团队已就绪</p>
          <p class="x-empty-sub">说出你的学习需求，我会调度团队为你服务</p>
        </div>

        <template v-for="m in messages" :key="m.id">
          <div v-if="m.kind === 'user'" class="x-msg x-msg--user">
            <div class="x-msg-bub">{{ m.content }}</div>
            <span class="x-msg-time">{{ fmtTime(m.ts) }}</span>
          </div>
          <div v-else-if="m.kind === 'assistant' && (m.content || m.pending)" class="x-msg x-msg--tutor">
            <div class="x-msg-hd"><span class="x-msg-ico">🧑‍🏫</span><span class="x-msg-who">私教老师</span></div>
            <div class="x-msg-bub">
              <details v-if="m.thinkingContent" class="x-thinking" :open="m.thinkingActive">
                <summary class="x-thinking-summary">
                  {{ m.thinkingActive ? '思考中…' : '思考过程' }}
                </summary>
                <div class="x-thinking-body">{{ m.thinkingContent }}</div>
              </details>
              <template v-if="m.content">
                <StreamingMarkdown :text="m.content" :pending="m.pending" />
              </template>
              <span v-else-if="!m.thinkingContent" class="x-wait">思考中…</span>
              <!-- 知识图谱校准状态 -->
              <div v-if="m.meta?.calibrating" class="x-calibration">
                <span class="x-calibration-spinner">⟳</span>
                <span class="x-calibration-text">正在校准知识图谱…</span>
              </div>
              <div v-else-if="m.meta?.calibrationResult" class="x-calibration-result">
                <template v-if="m.meta.calibrationResult.error">
                  <span class="x-calibration-error">✗ 校准失败：{{ m.meta.calibrationResult.error }}</span>
                </template>
                <template v-else>
                  <span class="x-calibration-success">✓ 知识图谱校准完成</span>
                  <span v-if="m.meta.calibrationResult.updated_count > 0" class="x-calibration-detail">
                    更新了 {{ m.meta.calibrationResult.updated_count }} 个知识点：
                    <span v-for="(node, ni) in m.meta.calibrationResult.updated_nodes" :key="ni" class="x-calibration-node">
                      {{ node.name }}
                    </span>
                  </span>
                </template>
              </div>
            </div>
            <span class="x-msg-time">{{ fmtTime(m.ts) }}</span>
          </div>
          <div v-else-if="AGENT_LIST[m.kind]" class="x-msg x-msg--sub" :class="{ 'x-msg--wide': m.kind === 'doc_assistant' || m.kind === 'doc_writer' || m.kind === 'exam' }">
            <div class="x-msg-hd">
              <span class="x-msg-dot" :style="{ background: AGENT_COLORS[m.kind] }"></span>
              <span class="x-msg-ico">
                <img v-if="AGENT_LIST[m.kind]?.avatar" :src="AGENT_LIST[m.kind]?.avatar" :alt="AGENT_LIST[m.kind]?.name" class="x-msg-ico-img" />
                <template v-else>{{ AGENT_LIST[m.kind]?.icon }}</template>
              </span>
              <span class="x-msg-who">{{ AGENT_LIST[m.kind]?.name }}</span>
            </div>
            <div class="x-msg-bub">
              <!-- 测评助手：内嵌试卷 -->
              <div
                v-if="m.kind === 'exam' && m.meta?.generating"
                class="x-doc-player x-doc-player--skel"
              >
                <div class="x-doc-nav">
                  <span class="x-doc-nav-title">正在生成测评试卷…</span>
                </div>
                <div class="x-doc-skel">
                  <div class="x-skel-banner"></div>
                  <div class="x-skel-row">
                    <div class="x-skel-circle"></div>
                    <div class="x-skel-block"></div>
                  </div>
                  <div class="x-skel-steps">
                    <div class="x-skel-line"></div>
                    <div class="x-skel-line x-skel-line--short"></div>
                  </div>
                </div>
              </div>
              <div
                v-else-if="m.kind === 'exam' && m.meta?.exam_card"
                class="x-doc-player"
              >
                <div class="x-doc-nav">
                  <span class="x-doc-nav-title">📋 {{ m.meta.exam_card.title || '测评试卷' }}</span>
                  <span class="x-doc-nav-count">🅰 {{ m.meta.exam_card.mcq_count }}题 · ✏️ {{ m.meta.exam_card.essay_count }}题</span>
                  <button
                    class="x-doc-nav-btn x-doc-fs-btn"
                    title="全屏答题"
                    @click.stop="docFullscreen = { msgId: m.id, scenes: [{ title: '测评试卷', html: '' }], sceneIdx: 0, examSessionId: m.meta.exam_card.session_id }"
                  >⛶</button>
                </div>
                <div class="x-doc-iframe-wrap" style="min-height:520px">
                  <iframe
                    :src="'/app/exam?session=' + m.meta.exam_card.session_id + '&embed=1'"
                    class="x-doc-iframe" style="height:560px"
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                  />
                </div>
              </div>
              <!-- 视频助手：B 站视频嵌入 -->
              <div
                v-if="m.kind === 'video' && m.meta?.generating"
                class="x-video-player x-video-player--skel"
              >
                <div class="x-video-top">
                  <span class="x-video-title">正在搜索教学视频…</span>
                </div>
                <div class="x-video-skel">
                  <div class="x-skel-banner"></div>
                  <div class="x-skel-row">
                    <div class="x-skel-circle"></div>
                    <div class="x-skel-block"></div>
                  </div>
                </div>
              </div>
              <div
                v-else-if="m.kind === 'video' && m.meta?.video"
                class="x-video-player"
              >
                <div class="x-video-top">
                  <span class="x-video-title">{{ m.meta.video.title || '教学视频' }}</span>
                  <span v-if="m.meta.video.duration" class="x-video-dur">{{ m.meta.video.duration }}</span>
                </div>
                <div class="x-video-wrap">
                  <iframe
                    :src="'https://player.bilibili.com/player.html?bvid=' + m.meta.video.bvid"
                    class="x-video-iframe"
                    allowfullscreen
                    sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
                  />
                </div>
              </div>
              <!-- 出题助手：选择题快测（含骨架屏） -->
              <div
                v-else-if="m.kind === 'practice_quiz'"
                class="x-quiz-player"
              >
                <div class="x-quiz-nav">
                  <span class="x-quiz-nav-title">📝 练习题</span>
                  <span class="x-quiz-nav-count">
                    <template v-if="m.meta?.generating">
                      正在出题…
                    </template>
                    <template v-else-if="m.meta?.quiz_status === 'error'">
                      ❌ 出题失败：{{ m.meta?.message || '请稍后重试' }}
                    </template>
                    <template v-else>
                      共 {{ (m.meta?.questions && m.meta.questions.length) || 0 }} 题
                    </template>
                  </span>
                </div>

                <!-- 骨架屏：生成中 -->
                <div
                  v-if="m.meta?.generating"
                  class="x-quiz-list"
                >
                  <div
                    v-for="n in 3"
                    :key="`skel-${n}`"
                    class="x-quiz-item x-quiz-item--skel"
                  >
                    <div class="x-quiz-skel-bar x-quiz-skel-bar--lg"></div>
                    <div class="x-quiz-skel-bar x-quiz-skel-bar--md"></div>
                    <div class="x-quiz-skel-row">
                      <div class="x-quiz-skel-bar x-quiz-skel-opt"></div>
                      <div class="x-quiz-skel-bar x-quiz-skel-opt"></div>
                    </div>
                    <div class="x-quiz-skel-row">
                      <div class="x-quiz-skel-bar x-quiz-skel-opt"></div>
                      <div class="x-quiz-skel-bar x-quiz-skel-opt"></div>
                    </div>
                  </div>
                </div>

                <!-- 真实题目 -->
                <div v-else class="x-quiz-list">
                  <div
                    v-for="(q, qi) in (m.meta?.questions || [])"
                    :key="qi"
                    class="x-quiz-item"
                  >
                    <div class="x-quiz-q">
                      <span class="x-quiz-idx">{{ Number(qi) + 1 }}.</span>
                      <span class="x-quiz-qtext">{{ q.question_text || q.title }}</span>
                      <span v-if="q.difficulty" class="x-quiz-tag" :class="`x-quiz-tag--${q.difficulty}`">
                        {{ { easy: '简单', medium: '中等', hard: '困难' }[q.difficulty as 'easy' | 'medium' | 'hard'] || q.difficulty }}
                      </span>
                      <!-- 答题状态 -->
                      <span v-if="q.user_answer" class="x-quiz-status" :class="{ 'is-correct': q.user_answer === q.correct_answer }">
                        {{ q.user_answer === q.correct_answer ? '✓ 正确' : '✗ 错误' }}
                      </span>
                    </div>
                    <div class="x-quiz-opts">
                      <label
                        v-for="(opt, oi) in (q.options || [])"
                        :key="oi"
                        class="x-quiz-opt"
                        :class="{
                          'is-selected': q.user_answer === String.fromCharCode(65 + Number(oi)),
                          'is-correct': q.correct_answer === String.fromCharCode(65 + Number(oi)),
                          'is-wrong': q.user_answer === String.fromCharCode(65 + Number(oi)) && q.user_answer !== q.correct_answer
                        }"
                      >
                        <input
                          type="radio"
                          :name="`quiz-${m.id}-${qi}`"
                          :value="String.fromCharCode(65 + Number(oi))"
                          :disabled="!!q.user_answer"
                          @change="handleQuizAnswer(m, Number(qi), String.fromCharCode(65 + Number(oi)))"
                        />
                        <span class="x-quiz-opt-letter">{{ String.fromCharCode(65 + Number(oi)) }}</span>
                        <span class="x-quiz-opt-text">{{ opt }}</span>
                      </label>
                    </div>
                    <details v-if="q.explanation" class="x-quiz-expl" :open="q.user_answer && q.user_answer !== q.correct_answer">
                      <summary>💡 查看解析</summary>
                      <div class="x-quiz-expl-body">
                        <p><strong>答案：</strong>{{ q.correct_answer }}</p>
                        <p>{{ q.explanation }}</p>
                      </div>
                    </details>
                  </div>
                </div>
              </div>
              <!-- 实践助手 / 图文助手：骨架屏 -->
              <div
                v-else-if="(m.kind === 'doc_assistant' || m.kind === 'doc_writer') && m.meta?.generating"
                class="x-doc-player x-doc-player--skel"
              >
                <div class="x-doc-nav">
                  <span class="x-doc-nav-title">{{ m.kind === 'doc_assistant' ? '正在生成实践场景…' : '正在生成图文内容…' }}</span>
                </div>
                <div class="x-doc-skel">
                  <div class="x-skel-banner"></div>
                  <div class="x-skel-row">
                    <div class="x-skel-circle"></div>
                    <div class="x-skel-block"></div>
                  </div>
                  <div class="x-skel-steps">
                    <div class="x-skel-line"></div>
                    <div class="x-skel-line x-skel-line--short"></div>
                    <div class="x-skel-line"></div>
                  </div>
                </div>
              </div>
              <!-- 实践助手 / 图文助手：内嵌课件播放器 -->
              <div
                v-else-if="(m.kind === 'doc_assistant' || m.kind === 'doc_writer') && m.meta?.doc_scenes"
                class="x-doc-player"
              >
                <div class="x-doc-nav">
                  <button
                    class="x-doc-nav-btn"
                    :disabled="getDocSceneIdx(m.id) === 0"
                    @click.stop="setDocSceneIdx(m.id, getDocSceneIdx(m.id) - 1, m.meta.doc_scenes.scenes.length)"
                  >◀</button>
                  <span class="x-doc-nav-title">
                    {{ m.meta.doc_scenes.scenes[getDocSceneIdx(m.id)]?.title || '' }}
                  </span>
                  <span class="x-doc-nav-count">{{ getDocSceneIdx(m.id) + 1 }} / {{ m.meta.doc_scenes.scenes.length }}</span>
                  <button
                    class="x-doc-nav-btn"
                    :disabled="getDocSceneIdx(m.id) >= m.meta.doc_scenes.scenes.length - 1"
                    @click.stop="setDocSceneIdx(m.id, getDocSceneIdx(m.id) + 1, m.meta.doc_scenes.scenes.length)"
                  >▶</button>
                  <button
                    class="x-doc-nav-btn x-doc-fs-btn"
                    title="全屏查看"
                    @click.stop="openDocFullscreen(m.id, m.meta.doc_scenes.scenes, getDocSceneIdx(m.id))"
                  >⛶</button>
                </div>
                <!-- 进度条 -->
                <div class="x-doc-progress">
                  <div class="x-doc-progress-fill" :style="{ width: ((getDocSceneIdx(m.id) + 1) / m.meta.doc_scenes.scenes.length * 100) + '%' }"></div>
                </div>
                <!-- 场景缩略导航 -->
                <div class="x-doc-thumbs" v-if="m.meta.doc_scenes.scenes.length > 1">
                  <button
                    v-for="(s, i) in m.meta.doc_scenes.scenes"
                    :key="i"
                    class="x-doc-thumb"
                    :class="{ 'is-active': i === getDocSceneIdx(String(m.id)) }"
                    @click.stop="setDocSceneIdx(String(m.id), Number(i), m.meta.doc_scenes.scenes.length as number)"
                  >
                    <span class="x-doc-thumb-n">{{ Number(i) + 1 }}</span>
                    <span class="x-doc-thumb-t">{{ s.title }}</span>
                  </button>
                </div>
                <div class="x-doc-iframe-wrap">
                  <iframe
                    v-if="m.meta.doc_scenes.scenes[getDocSceneIdx(m.id)]?.html"
                    :srcdoc="m.meta.doc_scenes.scenes[getDocSceneIdx(m.id)].html"
                    class="x-doc-iframe"
                    sandbox="allow-scripts allow-forms allow-popups"
                    loading="lazy"
                  />
                </div>
              </div>
              <!-- 普通文本内容 -->
              <StreamingMarkdown v-else :text="m.content" :pending="false" />
            </div>
            <span class="x-msg-time">{{ fmtTime(m.ts) }}</span>
          </div>
          <div v-else class="x-sys" :class="{ 'is-actionable': lastStallMessageId === m.id }">
            <span class="x-sys-txt">{{ m.content }}</span>
            <button v-if="lastStallMessageId === m.id" class="x-sys-act" @click="handleRetrySend">重试</button>
          </div>
        </template>
      </div>

      <div v-if="!noSubject" class="x-cmp">
        <div class="x-cmp-bar">
          <input v-model="composeText" class="x-cmp-inp" placeholder="输入你的学习需求…" @keydown="onComposeKey" :disabled="sending" />
          <button class="x-cmp-send" :class="{ 'is-ok': composeText.trim() && !sending }" :disabled="!composeText.trim() || sending" @click="handleSend">↑</button>
        </div>
      </div>
    </section>

    <!-- 右侧：私教团队 -->
    <aside class="x-side x-side--agents">
      <div class="x-side-inner">
        <p class="x-side-ttl">私教团队</p>
        <div class="x-side-list">
          <div v-for="(info, type) in AGENT_LIST" :key="type" class="x-agent"
            :class="{ 'is-live': agentStatuses[type] === 'working', 'is-selected': selectedAgent === type }"
            role="button" tabindex="0"
            @click="selectAgent(type as keyof typeof AGENT_LIST)"
            @keydown.enter="selectAgent(type as keyof typeof AGENT_LIST)"
            @keydown.space.prevent="selectAgent(type as keyof typeof AGENT_LIST)">
            <!-- 彩色点: 选中 → 显 agent 主题色; 工作中 → 绿点脉动; 默认 → 灰 -->
            <span class="x-agent-dot"
              :class="{
                'is-on': agentStatuses[type] === 'working',
                'is-selected': selectedAgent === type,
              }"
              :style="selectedAgent === type && agentStatuses[type] !== 'working'
                ? { background: AGENT_COLORS[type] }
                : {}"></span>
            <span class="x-agent-ico">
              <img v-if="info.avatar" :src="info.avatar" :alt="info.name" class="x-agent-ico-img" />
              <template v-else>{{ info.icon }}</template>
            </span>
            <div class="x-agent-txt">
              <span class="x-agent-name">{{ info.name }}</span>
              <span class="x-agent-st">{{ agentStatuses[type] === 'working' ? '工作中…' : '在线' }}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 全屏：课件 / 试卷 -->
    <div v-if="docFullscreen" ref="docFsRef" class="x-doc-fs-overlay">
      <div class="x-doc-fs-bar">
        <template v-if="docFullscreen.examSessionId">
          <span class="x-doc-fs-title">📋 测评试卷</span>
        </template>
        <template v-else>
          <button class="x-doc-nav-btn x-doc-fs-nav" :disabled="docFullscreen.sceneIdx === 0"
            @click.stop="docFullscreen.sceneIdx = Math.max(0, docFullscreen.sceneIdx - 1)">◀</button>
          <span class="x-doc-fs-title">{{ docFullscreen.scenes[docFullscreen.sceneIdx]?.title || '' }}</span>
          <span class="x-doc-nav-count x-doc-fs-count">{{ docFullscreen.sceneIdx + 1 }} / {{ docFullscreen.scenes.length }}</span>
          <button class="x-doc-nav-btn x-doc-fs-nav" :disabled="docFullscreen.sceneIdx >= docFullscreen.scenes.length - 1"
            @click.stop="docFullscreen.sceneIdx = Math.min(docFullscreen.scenes.length - 1, docFullscreen.sceneIdx + 1)">▶</button>
        </template>
        <button class="x-doc-fs-close" @click="closeDocFullscreen" title="退出全屏 (Esc)">✕</button>
      </div>
      <div class="x-doc-fs-frame">
        <iframe v-if="docFullscreen.examSessionId"
          :src="'/app/exam?session=' + docFullscreen.examSessionId"
          class="x-doc-fs-iframe" sandbox="allow-scripts allow-same-origin allow-forms allow-popups" />
        <iframe v-else-if="docFullscreen.scenes[docFullscreen.sceneIdx]?.html"
          :srcdoc="docFullscreen.scenes[docFullscreen.sceneIdx]?.html ?? ''"
          class="x-doc-fs-iframe" sandbox="allow-scripts allow-forms allow-popups" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.x-tutor { position: fixed; inset: 68px 0 0 0; display: flex; background: #F2F2F7; font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', var(--x-font-ui), sans-serif; }

/* 侧边栏通用 */
.x-side { width: 220px; flex-shrink: 0; display: flex; flex-direction: column; padding: 20px 12px; background: rgba(255,255,255,0.68); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px); transition: width 0.3s ease; }
.x-side--convs { border-right: 0.5px solid rgba(0,0,0,0.08); }
.x-side--agents { border-left: 0.5px solid rgba(0,0,0,0.08); }
.x-side.is-folded { width: 44px; padding: 20px 8px; align-items: center; }
.x-side-inner { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.x-side-ttl { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #8E8E93; margin: 0; }
.x-side-fold { background: none; border: none; color: #8E8E93; cursor: pointer; font-size: 11px; padding: 6px; border-radius: 8px; align-self: flex-end; margin-top: auto; }
.x-side-fold:hover { color: #1C1C1E; background: rgba(0,0,0,0.04); }
.x-side-fold--exp { align-self: center; margin-top: 0; }

/* 对话列表 */
.x-conv-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.x-new-btn { background: none; border: none; color: #1E5AE0; cursor: pointer; font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.x-new-btn:hover { background: rgba(30,90,224,0.08); }
.x-new-btn:disabled { opacity: 0.4; cursor: default; }
.x-conv-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.x-conv-empty { font-size: 13px; color: #8E8E93; padding: 12px 8px; text-align: center; }
.x-conv-item { display: flex; align-items: center; gap: 6px; padding: 10px 10px; border-radius: 10px; cursor: pointer; transition: background 0.15s; }
.x-conv-item:hover { background: rgba(0,0,0,0.04); }
.x-conv-item.is-active { background: rgba(30,90,224,0.08); }
.x-conv-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.x-conv-title { font-size: 13px; font-weight: 500; color: #1C1C1E; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.x-conv-item.is-active .x-conv-title { color: #1E5AE0; }
.x-conv-meta { font-size: 11px; color: #8E8E93; }
.x-conv-del { flex-shrink: 0; width: 20px; height: 20px; border: none; background: none; color: #C7C7CC; cursor: pointer; font-size: 14px; border-radius: 50%; display: flex; align-items: center; justify-content: center; opacity: 0; transition: all 0.15s; }
.x-conv-item:hover .x-conv-del { opacity: 1; }
.x-conv-del:hover { color: #FF3B30; background: rgba(255,59,48,0.08); }

/* 私教团队 */
.x-side-list { display: flex; flex-direction: column; gap: 2px; margin-top: 10px; }
.x-agent { display: flex; align-items: center; gap: 10px; padding: 10px 10px; border-radius: 12px; transition: background 0.2s; cursor: pointer; }
.x-agent:hover { background: var(--x-canvas-soft); }
.x-agent.is-selected { background: var(--x-primary-soft); }
.x-agent.is-live.is-selected { /* 工作中 + 选中: 在 --x-primary-soft 之上再叠一层 */ box-shadow: inset 0 0 0 1px var(--x-primary); }
.x-agent:hover { background: rgba(0,0,0,0.04); }
.x-agent.is-live { background: rgba(30,90,224,0.06); }
.x-agent-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; transition: background 0.3s, transform 0.3s; }
.x-agent-dot.is-on { background: #34C759; animation: x-pulse 1.5s ease-in-out infinite; }
@keyframes x-pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.6)} }
.x-agent-ico { font-size: 18px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center; }
.x-agent-ico-img { width: 24px; height: 24px; border-radius: 50%; object-fit: cover; }
.x-agent-txt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.x-agent-name { font-size: 14px; font-weight: 500; color: #1C1C1E; }
.x-agent-st { font-size: 11px; color: #8E8E93; }
.x-agent.is-live .x-agent-st { color: #1E5AE0; }

.x-chat { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.x-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 48px 24px; text-align: center; }
.x-empty-ico { font-size: 44px; margin-bottom: 4px; }
.x-empty-squad { display: flex; gap: 14px; margin-bottom: 8px; }
.x-empty-sq { font-size: 28px; opacity: 0.5; display: inline-flex; align-items: center; justify-content: center; }
.x-empty-sq-img { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; opacity: 1; }
.x-empty-ttl { font-size: 22px; font-weight: 700; color: #1C1C1E; margin: 0; letter-spacing: -0.01em; }
.x-empty-sub { font-size: 15px; color: #8E8E93; margin: 0; line-height: 1.5; }
.x-btn { display: inline-flex; align-items: center; gap: 4px; padding: 12px 24px; background: #1E5AE0; color: #fff; border-radius: 14px; text-decoration: none; font-size: 15px; font-weight: 600; margin-top: 8px; }

.x-msgs { flex: 1; overflow-y: auto; padding: 24px 40px; display: flex; flex-direction: column; gap: 24px; }
.x-msg { display: flex; flex-direction: column; max-width: 70%; animation: x-up 0.3s ease both; }
.x-msg--wide { max-width: 92%; width: 92%; }
@keyframes x-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.x-msg--user { align-self: flex-end; align-items: flex-end; }
.x-msg--tutor, .x-msg--sub { align-self: flex-start; }
.x-msg-hd { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; padding: 0 6px; }
.x-msg-ico { font-size: 14px; display: inline-flex; align-items: center; justify-content: center; }
.x-msg-ico-img { width: 22px; height: 22px; border-radius: 50%; object-fit: cover; }
.x-msg-who { font-size: 12px; font-weight: 600; color: #8E8E93; }
.x-msg-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.x-msg-bub { padding: 12px 18px; border-radius: 18px; font-size: 15px; line-height: 1.6; word-wrap: break-word; overflow-wrap: break-word; }
.x-msg--user .x-msg-bub { background: #1E5AE0; color: #fff; border-radius: 18px 18px 4px 18px; }
.x-msg--tutor .x-msg-bub { background: #fff; color: #1C1C1E; border-radius: 18px 18px 18px 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
/* Agent 消息不显示气泡，内容直接展示 */
.x-msg--sub .x-msg-bub { background: transparent; color: #1C1C1E; border-radius: 0; box-shadow: none; padding: 0 6px; }
.x-msg-time { font-size: 11px; color: #8E8E93; padding: 2px 6px 0; }
.x-wait { color: #8E8E93; font-size: 14px; animation: x-fade 1.5s ease-in-out infinite; }
@keyframes x-fade { 0%,100%{opacity:0.4} 50%{opacity:1} }
.x-msg-bub :deep(p) { margin: 0 0 8px; }
.x-msg-bub :deep(p:last-child) { margin-bottom: 0; }
.x-msg-bub :deep(ul), .x-msg-bub :deep(ol) { margin: 6px 0; padding-left: 20px; }
.x-msg-bub :deep(li) { margin-bottom: 4px; }

/* 思考过程折叠区 */
.x-thinking { margin-bottom: 10px; border-radius: 8px; background: #F9F9FB; border: 1px solid #E5E5EA; overflow: hidden; }
.x-thinking-summary { padding: 6px 12px; font-size: 12px; color: #8E8E93; cursor: pointer; user-select: none; }
.x-thinking-summary::marker { font-size: 10px; color: #8E8E93; }
.x-thinking-body { padding: 0 12px 10px; font-size: 13px; color: #6E6E73; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }

.x-sys { align-self: center; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #8E8E93; padding: 2px 0; }
.x-sys-txt { font-weight: 400; }
.x-sys.is-actionable { color: #FF3B30; }
.x-sys-act { background: none; border: none; color: #1E5AE0; cursor: pointer; font-size: 12px; font-weight: 500; }
.x-sys-act:hover { text-decoration: underline; }

.x-cmp { padding: 12px 24px 24px; flex-shrink: 0; }
.x-cmp-bar { display: flex; align-items: center; gap: 8px; background: #fff; border-radius: 22px; padding: 6px 6px 6px 18px; box-shadow: 0 2px 12px rgba(0,0,0,0.06), 0 0 0 0.5px rgba(0,0,0,0.04); }
.x-cmp-inp { flex: 1; border: none; background: none; outline: none; font-family: inherit; font-size: 15px; color: #1C1C1E; padding: 8px 0; line-height: 1.4; }
.x-cmp-inp::placeholder { color: #C7C7CC; }
.x-cmp-send { width: 32px; height: 32px; border-radius: 50%; border: none; background: #C7C7CC; color: #fff; font-size: 16px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s, transform 0.15s; flex-shrink: 0; }
.x-cmp-send.is-ok { background: #1E5AE0; }
.x-cmp-send:disabled { opacity: 0.5; cursor: default; }
.x-cmp-send:not(:disabled):active { transform: scale(0.92); }

/* 测评试卷卡片 */
.x-exam-card {
  background: #fff;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  padding: 16px 18px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.x-exam-card:hover {
  border-color: rgba(0,0,0,0.12);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.x-exam-card:active { transform: scale(0.985); }
.x-exam-card-top {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.x-exam-card-icon { font-size: 20px; }
.x-exam-card-title {
  font-size: 15px; font-weight: 600; color: #1C1C1E;
}
.x-exam-card-info {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding-left: 28px;
}
.x-exam-card-stat { font-size: 12px; color: #8E8E93; }
.x-exam-card-sep { color: #C7C7CC; font-size: 11px; }
.x-exam-card-act {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; font-weight: 600; color: #fff;
  padding: 6px 16px; background: #1E5AE0;
  border-radius: 8px; transition: background 0.15s;
}
.x-exam-card:hover .x-exam-card-act { background: #1A4FC9; }

/* 视频助手 —— B 站视频嵌入 */
.x-video-player {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px; overflow: hidden;
  background: #fff; margin-top: 4px;
}
.x-video-top {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.x-video-title {
  flex: 1; font-size: 13px; font-weight: 600; color: #1C1C1E;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.x-video-dur {
  font-size: 12px; color: #8E8E93; white-space: nowrap;
}
.x-video-wrap {
  position: relative; padding-top: 56.25%; /* 16:9 */
}
.x-video-iframe {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  border: none;
}

/* 出题助手 —— 3 道选择题快测 */
.x-quiz-player {
  border: 1px solid rgba(124, 58, 237, 0.18);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 12px rgba(124, 58, 237, 0.06);
}
.x-quiz-nav {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  border-bottom: 1px solid rgba(124, 58, 237, 0.12);
}
.x-quiz-nav-title { flex: 1; font-size: 13px; font-weight: 600; color: #5B21B6; }
.x-quiz-nav-count { font-size: 12px; color: #7C3AED; white-space: nowrap; }
.x-quiz-list { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 12px; }
.x-quiz-item {
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 12px 14px;
  background: #fafafa;
  transition: all 0.2s;
}
.x-quiz-item:hover { border-color: #c4b5fd; background: #fff; }
.x-quiz-q { display: flex; align-items: flex-start; gap: 6px; margin-bottom: 10px; line-height: 1.55; }
.x-quiz-idx { font-weight: 700; color: #7C3AED; flex-shrink: 0; }
.x-quiz-qtext { flex: 1; font-size: 14px; color: #1C1C1E; }
.x-quiz-tag {
  font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; flex-shrink: 0;
}
.x-quiz-tag--easy { background: #dcfce7; color: #15803d; }
.x-quiz-tag--medium { background: #fef3c7; color: #b45309; }
.x-quiz-tag--hard { background: #fee2e2; color: #b91c1c; }
.x-quiz-opts { display: flex; flex-direction: column; gap: 6px; }
.x-quiz-opt {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  background: #fff; cursor: pointer; font-size: 13px;
  color: #1e293b; transition: all 0.15s;
}
.x-quiz-opt:hover { border-color: #7C3AED; background: #f5f3ff; }
.x-quiz-opt.is-selected { border-color: #7C3AED; background: #f5f3ff; }
.x-quiz-opt.is-correct { border-color: #16a34a; background: #f0fdf4; }
.x-quiz-opt.is-wrong { border-color: #dc2626; background: #fef2f2; }
.x-quiz-opt input[type="radio"] { margin: 0; accent-color: #7C3AED; }
.x-quiz-opt input[type="radio"]:disabled { opacity: 0.5; }
.x-quiz-opt-letter {
  font-weight: 700; color: #7C3AED; flex-shrink: 0; min-width: 14px;
}
.x-quiz-opt.is-correct .x-quiz-opt-letter { color: #16a34a; }
.x-quiz-opt.is-wrong .x-quiz-opt-letter { color: #dc2626; }
.x-quiz-opt-text { flex: 1; }
.x-quiz-status { font-size: 12px; font-weight: 600; margin-left: 8px; padding: 2px 8px; border-radius: 10px; }
.x-quiz-status.is-correct { background: #dcfce7; color: #15803d; }
.x-quiz-status:not(.is-correct) { background: #fee2e2; color: #b91c1c; }
.x-quiz-expl { margin-top: 10px; font-size: 13px; }
.x-quiz-expl summary {
  cursor: pointer; color: #7C3AED; font-weight: 500; user-select: none;
  padding: 4px 0;
}
.x-quiz-expl-body { padding: 8px 12px; background: #f8fafc; border-radius: 6px; margin-top: 6px; color: #475569; line-height: 1.6; }
.x-quiz-expl-body p { margin: 4px 0; }

/* 出题助手 —— 骨架屏 */
.x-quiz-item--skel { padding: 14px; }
.x-quiz-skel-bar {
  height: 12px; border-radius: 6px;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  animation: x-quiz-skel 1.4s ease-in-out infinite;
  margin-bottom: 10px;
}
.x-quiz-skel-bar--lg { width: 70%; height: 14px; }
.x-quiz-skel-bar--md { width: 85%; }
.x-quiz-skel-bar--opt { flex: 1; height: 32px; margin-bottom: 0; border-radius: 8px; }
.x-quiz-skel-row { display: flex; gap: 8px; margin-bottom: 8px; }
.x-quiz-skel-row:last-child { margin-bottom: 0; }
@keyframes x-quiz-skel {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 知识图谱校准 */
.x-calibration {
  display: flex; align-items: center; gap: 8px;
  margin-top: 8px; padding: 8px 12px;
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  border-radius: 8px; font-size: 13px;
}
.x-calibration-spinner {
  font-size: 16px; color: #0284c7;
  animation: x-spin 1s linear infinite;
}
@keyframes x-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.x-calibration-text { color: #0369a1; font-weight: 500; }
.x-calibration-result {
  margin-top: 8px; padding: 8px 12px;
  background: #f8fafc; border-radius: 8px; font-size: 13px;
}
.x-calibration-success { color: #059669; font-weight: 500; }
.x-calibration-error { color: #dc2626; }
.x-calibration-detail { color: #475569; margin-left: 4px; }
.x-calibration-node {
  display: inline-block;
  margin: 0 4px; padding: 2px 8px;
  background: #dbeafe; color: #1e40af;
  border-radius: 6px; font-size: 12px;
}

/* 实践助手 —— 内嵌课件播放器 */
.x-doc-player {
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  margin: 4px -18px -12px;
}
.x-doc-player--skel { margin: 0; }
.x-doc-skel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.x-skel-banner {
  height: 120px;
  border-radius: 8px;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  animation: x-quiz-skel 1.4s ease-in-out infinite;
}
.x-skel-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.x-skel-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  animation: x-quiz-skel 1.4s ease-in-out infinite;
}
.x-skel-block {
  flex: 1;
  height: 16px;
  border-radius: 6px;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  animation: x-quiz-skel 1.4s ease-in-out infinite;
}
.x-skel-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.x-skel-line {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, #f1f5f9 0%, #e2e8f0 50%, #f1f5f9 100%);
  background-size: 200% 100%;
  animation: x-quiz-skel 1.4s ease-in-out infinite;
}
.x-skel-line--short { width: 60%; }

/* 视频助手骨架屏 */
.x-video-player--skel .x-video-skel {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.x-video-player--skel .x-skel-banner {
  height: 180px;
}

.x-doc-nav {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.x-doc-nav-btn {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(0,0,0,0.1); border-radius: 8px;
  background: #fff; cursor: pointer;
  font-size: 12px; color: #475569; transition: all 0.15s;
}
.x-doc-nav-btn:disabled { opacity: 0.35; cursor: default; }
.x-doc-nav-btn:not(:disabled):hover { background: #f1f5f9; border-color: rgba(0,0,0,0.2); }
.x-doc-nav-title {
  flex: 1; font-size: 13px; font-weight: 600; color: #1C1C1E;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.x-doc-nav-count {
  font-size: 12px; color: #8E8E93; white-space: nowrap;
}
.x-doc-iframe-wrap {
  width: 100%; min-height: 480px;
  overflow: hidden;
}
.x-doc-iframe {
  width: 100%; height: 560px;
  border: none; display: block;
}
.x-doc-fs-btn {
  font-size: 14px; line-height: 1;
}
/* 进度条 */
.x-doc-progress {
  height: 2px; background: #e2e8f0; overflow: hidden;
}
.x-doc-progress-fill {
  height: 100%; background: #3b82f6;
  transition: width 0.3s ease;
}
/* 缩略导航条 */
.x-doc-thumbs {
  display: flex; gap: 4px;
  padding: 6px 14px;
  background: #fff;
  overflow-x: auto;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.x-doc-thumb {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  background: transparent; border: 1px solid transparent;
  border-radius: 6px; cursor: pointer;
  white-space: nowrap; font-size: 12px; color: #94a3b8;
  transition: all 0.15s; flex-shrink: 0;
}
.x-doc-thumb:hover { background: #f1f5f9; color: #64748b; }
.x-doc-thumb.is-active {
  background: #eff6ff; border-color: #3b82f6; color: #2563eb;
}
.x-doc-thumb-n { font-weight: 700; font-size: 11px; }
.x-doc-thumb-t {
  max-width: 120px; overflow: hidden; text-overflow: ellipsis;
}

/* 全屏查看遮罩 */
.x-doc-fs-overlay {
  position: fixed; inset: 0; z-index: 9999;
  background: #000;
  display: flex; flex-direction: column;
  animation: x-fs-in 0.2s ease;
}
@keyframes x-fs-in { from { opacity: 0; } to { opacity: 1; } }
.x-doc-fs-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px;
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(12px);
  flex-shrink: 0;
}
.x-doc-fs-title {
  flex: 1; font-size: 15px; font-weight: 600; color: #fff;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.x-doc-fs-close {
  width: 36px; height: 36px; margin-left: 8px;
  display: flex; align-items: center; justify-content: center;
  border: none; border-radius: 10px;
  background: rgba(255,255,255,0.12); color: #fff;
  font-size: 18px; cursor: pointer; transition: background 0.15s;
}
.x-doc-fs-nav {
  background: rgba(255,255,255,0.1) !important;
  border-color: rgba(255,255,255,0.15) !important;
  color: #fff !important;
}
.x-doc-fs-nav:not(:disabled):hover { background: rgba(255,255,255,0.22) !important; }
.x-doc-fs-nav:disabled { opacity: 0.25; }
.x-doc-fs-count { font-size: 12px; color: rgba(255,255,255,0.5); white-space: nowrap; }
.x-doc-fs-close:hover { background: rgba(255,255,255,0.25); }
.x-doc-fs-frame {
  flex: 1; min-height: 0; padding: 8px 20px 20px;
}
.x-doc-fs-iframe {
  width: 100%; height: 100%;
  border: none; border-radius: 12px;
  background: #fff;
}
</style>
