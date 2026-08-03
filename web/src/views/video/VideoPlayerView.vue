<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMySubjectsStore } from '@/stores/mySubjects'
import {
  getVideoCourse,
  getVideoCourseTask,
  reportVideoProgress,
  type VideoCourseRecord,
  type VideoSceneOutline,
  type VideoCourseOutline,
  fetchOpenmaicOutlines,
  patchOutlines,
} from '@/api/video'
import { createConversation, getConversation } from '@/api/conversations'
import { useConvWS } from '@/composables/use_conv_ws'
import StreamingMarkdown from '@/components/StreamingMarkdown.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import {
  IconArrow,
  IconChat,
  IconNotepad,
  IconBulb,
  IconCheck,
  IconPin,
  IconPause,
  IconPlus,
  IconRetry,
  IconTimer,
  IconVideo,
  IconHourglass,
} from '@/components/icons'
import type {
  ChatMessage,
  WSInboundEvent,
} from '@/types/chat'

const route = useRoute()
const router = useRouter()
const currentSubject = useCurrentSubjectStore()
const mySubjects = useMySubjectsStore()

const videoUuid = computed(() => {
  const v = route.params.id
  const result = Array.isArray(v) ? v[0] : (v as string) || ''
  return result || undefined
})

// 是否有选中的视频（即路由上有 uuid）
const hasSelected = computed<boolean>(() => !!videoUuid.value)

// ─── 左侧：视频列表 ────────────────────────────────
// 从 VideoCourseView 移植的逻辑
import { startVideoCourse } from '@/api/video'
import { listPlans, type LearningPlan } from '@/api/plan'

interface VideoEntry {
  plan: LearningPlan
  videoRecordId: number | null
  videoUuid: string | null
  videoState: 'generating' | 'complete' | 'error' | null
}

const entries = ref<VideoEntry[]>([])
const listLoading = ref(false)
const generating = ref<number | null>(null)
const listError = ref<string>('')

const subjectId = computed<number | null>(() => {
  const s = mySubjects.subjects.find((m) => m.name === currentSubject.code)
  return s?.id ?? null
})

async function loadEntries(): Promise<void> {
  if (!subjectId.value) {
    entries.value = []
    return
  }
  listLoading.value = true
  listError.value = ''
  try {
    const { data } = await listPlans(currentSubject.code)
    const plans = Array.isArray(data) ? data : (data as { results: LearningPlan[] }).results ?? []
    const out: VideoEntry[] = []
    for (const plan of plans) {
      if (plan.memory?.step_type !== 'video') continue
      const mem = plan.memory as {
        video_record_id?: number
        video_uuid?: string
        video_state?: string
      }
      out.push({
        plan,
        videoRecordId: mem.video_record_id ?? null,
        videoUuid: mem.video_uuid ?? null,
        videoState: (mem.video_state as VideoEntry['videoState']) ?? null,
      })
    }
    out.sort((a, b) => {
      const aT = a.plan.expected_completion_time ?? ''
      const bT = b.plan.expected_completion_time ?? ''
      return aT.localeCompare(bT)
    })
    entries.value = out
  } catch (e: unknown) {
    listError.value = (e as Error).message || '加载失败'
    entries.value = []
  } finally {
    listLoading.value = false
  }
}

async function onPick(entry: VideoEntry): Promise<void> {
  if (entry.videoRecordId) {
    router.push({ name: 'app-video-detail', params: { id: String(entry.videoRecordId) } })
    return
  }
  if (!subjectId.value) {
    ElMessage({ message: 'x 缺少学科信息', customClass: 'x-toast' })
    return
  }
  if (generating.value !== null) return
  generating.value = entry.plan.id
  try {
    const { data } = await startVideoCourse({
      subjectId: subjectId.value,
      topic: entry.plan.node_name,
      extraPrompt: (entry.plan.memory as { step_desc?: string } | undefined)?.step_desc ?? '',
      planId: entry.plan.id,
      planNodeId: String(entry.plan.id),
    })
    entry.videoRecordId = data.id
    entry.videoState = data.state as VideoEntry['videoState']
    entry.videoUuid = data.video_uuid
    router.push({ name: 'app-video-detail', params: { id: String(data.id) } })
  } catch (e: unknown) {
    ElMessage({
      message: 'x 启动失败: ' + ((e as Error).message || '未知错误'),
      customClass: 'x-toast',
    })
  } finally {
    generating.value = null
  }
}

function statusOf(entry: VideoEntry): { text: string; tone: 'ready' | 'generating' | 'error' | 'pending' } {
  if (!entry.videoRecordId) return { text: '未生成', tone: 'pending' }
  if (entry.videoState === 'complete') return { text: '可观看', tone: 'ready' }
  if (entry.videoState === 'error') return { text: '生成失败', tone: 'error' }
  return { text: '生成中', tone: 'generating' }
}

// 当前选中的条目高亮
const selectedPlanId = computed<number | null>(() => {
  if (!record.value) return null
  // 从 entries 反查匹配的记录
  const found = entries.value.find(
    (e) => e.videoRecordId === record.value!.id || e.videoUuid === videoUuid.value,
  )
  return found?.plan.id ?? null
})

// ─── 选中视频的收看记录 ───
const record = ref<VideoCourseRecord | null>(null)
const detailError = ref<string>('')
const loading = ref(true)
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)
const openmaicPollTimer = ref<ReturnType<typeof setInterval> | null>(null)

function stopPoll() {
  if (pollTimer.value !== null) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

function stopOpenmaicPoll() {
  if (openmaicPollTimer.value !== null) {
    clearInterval(openmaicPollTimer.value)
    openmaicPollTimer.value = null
  }
}

/**
 * 把 OpenMAIC 的 scenes 灌进本地 record.course.outlines（深合并，按 id 去重，按 order 稳定排序）。
 */
function mergeOutlinesIntoRecord(outlines: VideoSceneOutline[]): boolean {
  if (!record.value) return false
  const existing = record.value.course
  const current: VideoSceneOutline[] = ((existing as { outlines?: VideoSceneOutline[] } | null | undefined)?.outlines) ?? []
  const byId = new Map<string, VideoSceneOutline>()
  for (const s of current) byId.set(s.id, s)
  let added = false
  for (const s of outlines) {
    const prev = byId.get(s.id)
    if (!prev) {
      added = true
      byId.set(s.id, s)
      continue
    }
    if ((s.title && !prev.title) || (s.description && !prev.description)) {
      byId.set(s.id, { ...prev, ...s })
      added = true
    }
  }
  if (!added && current.length === byId.size) return false
  const merged = Array.from(byId.values()).sort((a, b) => a.order - b.order)
  ;(record.value.course as { outlines?: VideoSceneOutline[] }).outlines = merged
  record.value = { ...record.value, course: { ...(record.value.course as VideoCourseOutline), outlines: merged } }
  return true
}

function startPollingOutlines(): void {
  stopOpenmaicPoll()
  if (!record.value?.video_uuid) return
  if (orderedScenes.value.length > 0) return
  const uuid = record.value.video_uuid
  const recordId = record.value.id
  let attempts = 0
  const MAX_ATTEMPTS = 150

  const tick = async (): Promise<void> => {
    attempts += 1
    if (orderedScenes.value.length > 0) {
      stopOpenmaicPoll()
      return
    }
    try {
      const { data: backend } = await getVideoCourse(recordId)
      const backendOutlines = ((backend.course as { outlines?: VideoSceneOutline[] } | null | undefined)?.outlines) ?? []
      if (backendOutlines.length > 0) {
        mergeOutlinesIntoRecord(backendOutlines)
        stopOpenmaicPoll()
        return
      }
    } catch { /* ignore */ }

    try {
      const openmaicOutlines = await fetchOpenmaicOutlines(uuid)
      if (openmaicOutlines && openmaicOutlines.length > 0) {
        mergeOutlinesIntoRecord(openmaicOutlines)
        try { await patchOutlines(recordId, openmaicOutlines) } catch { /* ignore */ }
        stopOpenmaicPoll()
        return
      }
    } catch { /* ignore */ }

    if (attempts >= MAX_ATTEMPTS) stopOpenmaicPoll()
  }

  void tick()
  openmaicPollTimer.value = setInterval(() => { void tick() }, 2000) as unknown as ReturnType<typeof setInterval>
}

async function loadDetail(idStr: string): Promise<void> {
  loading.value = true
  detailError.value = ''
  stopPoll()
  stopOpenmaicPoll()
  try {
    const id = Number(idStr)
    if (!Number.isFinite(id) || id <= 0) {
      detailError.value = '无效的视频课程标识'
      loading.value = false
      return
    }
    const { data } = await getVideoCourse(id)
    record.value = data

    // 处理 generating 状态的轮询
    if (data.state === 'generating') {
      // 有 task_id：轮询任务状态
      if (data.task_id) {
        pollTimer.value = setInterval(async () => {
          try {
            const { data: pollData } = await getVideoCourseTask(data.task_id)
            if (pollData.state === 'complete' || pollData.state === 'error') {
              record.value = pollData
              stopPoll()
              try {
                const { data: detail } = await getVideoCourse(data.id)
                record.value = detail
              } catch { /* ignore */ }
              startPollingOutlines()
            }
          } catch { /* ignore */ }
        }, 2000)
      } else {
        // 无 task_id：直接轮询 record 本身（后端可能直接更新 state）
        pollTimer.value = setInterval(async () => {
          try {
            const { data: pollData } = await getVideoCourse(id)
            if (pollData.state !== 'generating') {
              record.value = pollData
              stopPoll()
              startPollingOutlines()
            }
          } catch { /* ignore */ }
        }, 3000)
      }
    } else if (data.state === 'complete') {
      startPollingOutlines()
    }
  } catch (e: unknown) {
    detailError.value = (e as Error).message || '加载失败'
  } finally {
    loading.value = false
  }
}

// ─── 章节大纲 ───
const scenes = computed<VideoSceneOutline[]>(() => record.value?.course?.outlines ?? [])
const totalScenes = computed<number>(() => scenes.value.length)
const viewedSceneIds = ref<Set<string>>(new Set())
const currentSceneIndex = ref<number>(-1)
const watchedSeconds = ref<number>(0)
const completed = ref<boolean>(false)

const overallProgress = computed<number>(() => {
  if (totalScenes.value === 0) return 0
  return Math.round((viewedSceneIds.value.size / totalScenes.value) * 100)
})

const orderedScenes = computed<VideoSceneOutline[]>(() =>
  [...scenes.value].sort((a, b) => a.order - b.order),
)
const currentScene = computed<VideoSceneOutline | null>(() =>
  currentSceneIndex.value >= 0 ? orderedScenes.value[currentSceneIndex.value] ?? null : null,
)

function selectScene(index: number): void {
  if (index < 0 || index >= totalScenes.value) return
  currentSceneIndex.value = index
  const scene = orderedScenes.value[index]
  if (scene) markSceneViewed(scene.id)
}

function prevScene(): void {
  if (currentSceneIndex.value > 0) selectScene(currentSceneIndex.value - 1)
}
function nextScene(): void {
  if (currentSceneIndex.value < totalScenes.value - 1) selectScene(currentSceneIndex.value + 1)
}

// ─── 进度上报 ───
let lastReportAt = 0
let lastReportSceneId = ''
async function flushProgress(force = false): Promise<void> {
  if (!record.value) return
  const now = Date.now()
  if (!force && now - lastReportAt < 5_000) return
  const currentSceneId = currentScene.value?.id ?? ''
  if (!force && currentSceneId === lastReportSceneId) return
  lastReportAt = now
  lastReportSceneId = currentSceneId
  try {
    await reportVideoProgress({
      recordId: record.value.id,
      viewedSceneIds: Array.from(viewedSceneIds.value),
      lastSceneId: currentSceneId || null,
      watchedSeconds: Math.floor(watchedSeconds.value),
      completed: completed.value,
    })
  } catch { /* quiet */ }
}

function markSceneViewed(sceneId: string): void {
  viewedSceneIds.value = new Set([...viewedSceneIds.value, sceneId])
  if (viewedSceneIds.value.size >= totalScenes.value) {
    completed.value = true
    void flushProgress(true)
  } else {
    void flushProgress(false)
  }
}

// ─── iframe postMessage 监听 ───
const iframeRef = ref<HTMLIFrameElement | null>(null)

interface VideoProgressPayload {
  currentIndex: number; totalPages: number; isPlaying: boolean
  phase: string; title: string; timestamp: number
}
interface VideoSceneChangePayload {
  sceneId: string; currentIndex: number; title: string; timestamp: number
}

function handlePlayerMessage(event: MessageEvent): void {
  if (!record.value) return
  const data = event.data as Record<string, unknown> | null
  if (!data || typeof data !== 'object') return
  const type = (data as { type?: string }).type
  if (!type) return

  if (type === 'video-progress') {
    const payload = data.payload as VideoProgressPayload
    if (payload?.phase === 'ready' || payload?.phase === 'slides') {}
  } else if (type === 'video-scene-change') {
    const payload = data.payload as VideoSceneChangePayload
    if (payload?.sceneId) {
      ensureOutlineForScene(payload.sceneId, payload.title, typeof payload.currentIndex === 'number' ? payload.currentIndex : undefined)
      const idx = orderedScenes.value.findIndex((s) => s.id === payload.sceneId)
      if (idx >= 0) { currentSceneIndex.value = idx; markSceneViewed(payload.sceneId) }
      else if (typeof payload.currentIndex === 'number') { currentSceneIndex.value = payload.currentIndex; markSceneViewed(payload.sceneId) }
    }
  } else if (type === 'video-complete') {
    completed.value = true; void flushProgress(true)
  } else if (type === 'openmaic/scene' || type === 'openmaic/scene_change') {
    const sceneId = (data as { sceneId?: string }).sceneId
    const order = (data as { order?: number }).order
    const title = (data as { title?: string }).title
    if (typeof sceneId === 'string') {
      ensureOutlineForScene(sceneId, title, typeof order === 'number' ? order - 1 : undefined)
      const idx = orderedScenes.value.findIndex((s) => s.id === sceneId)
      if (idx >= 0) { currentSceneIndex.value = idx; markSceneViewed(sceneId) }
      else if (typeof order === 'number') { currentSceneIndex.value = order - 1; markSceneViewed(sceneId) }
    }
  } else if (type === 'openmaic/ended') {
    completed.value = true; void flushProgress(true)
  }
}

function ensureOutlineForScene(sceneId: string, title?: string, idxHint?: number): void {
  if (!record.value) return
  const sceneList: VideoSceneOutline[] = ((record.value.course as { outlines?: VideoSceneOutline[] } | null | undefined)?.outlines) ?? []
  if (sceneList.some((s) => s.id === sceneId)) {
    if (title) {
      const tgt = sceneList.find((s) => s.id === sceneId)
      if (tgt && !tgt.title) {
        tgt.title = title
        record.value = { ...record.value, course: { ...(record.value.course as VideoCourseOutline), outlines: sceneList.slice().sort((a, b) => a.order - b.order) } }
      }
    }
    return
  }
  const order = typeof idxHint === 'number' ? idxHint + 1 : sceneList.length + 1
  const outline: VideoSceneOutline = { id: sceneId, type: 'slide', title: title ?? '加载中…', description: '', key_points: [], order, knowledge_node_id: null }
  const next = [...sceneList, outline].sort((a, b) => a.order - b.order)
  record.value = { ...record.value, course: { ...(record.value.course as VideoCourseOutline), outlines: next } }
}

function sendToVideo(data: Record<string, unknown>): void {
  iframeRef.value?.contentWindow?.postMessage(data, '*')
}
function controlPlay(): void { sendToVideo({ type: 'video-control', action: 'play' }) }
function controlPause(): void { sendToVideo({ type: 'video-control', action: 'pause' }) }
function controlToggleSpeed(): void { sendToVideo({ type: 'video-control', action: 'toggleSpeed' }) }
function controlQuery(): void { sendToVideo({ type: 'video-query' }) }

let watchTimer: number | null = null
function startWatchTimer(): void {
  if (watchTimer !== null) return
  const start = Date.now() - watchedSeconds.value * 1000
  watchTimer = window.setInterval(() => { watchedSeconds.value = Math.floor((Date.now() - start) / 1000) }, 1000) as unknown as number
}
function stopWatchTimer(): void {
  if (watchTimer !== null) { window.clearInterval(watchTimer); watchTimer = null }
}

// ─── 中间：内容 tabs ───
type ContentTab = 'outline' | 'intro' | 'notes' | 'homework' | 'discuss'
const contentTab = ref<ContentTab>('outline')

const introData = computed(() => (record.value?.course as Record<string, unknown>)?.intro_data as Record<string, unknown> | null ?? null)
const homeworkData = computed(() => (record.value?.course as Record<string, unknown>)?.homework_data as Array<Record<string, unknown>> | null ?? null)

// ─── 右侧：智能体面板 ───
type AgentTab = 'notes' | 'chat' | 'mindmap'
const agentTab = ref<AgentTab>('chat')

// ─── 笔记 ───
interface CourseNote { id: string; sceneId: string | null; text: string; createdAt: number; source?: 'manual' | 'selection' }
const notes = ref<CourseNote[]>([])
function loadNotes(): void {
  if (!record.value) return
  const raw = localStorage.getItem(`video-course-notes:${record.value.id}`)
  if (raw) { try { notes.value = JSON.parse(raw) as CourseNote[] } catch { notes.value = [] } }
}
function saveNotes(): void {
  if (!record.value) return
  localStorage.setItem(`video-course-notes:${record.value.id}`, JSON.stringify(notes.value))
}
const noteDraft = ref<string>('')
function addNote(): void {
  if (!noteDraft.value.trim() || !record.value) return
  notes.value.unshift({ id: `n-${Date.now()}`, sceneId: currentScene.value?.id ?? null, text: noteDraft.value.trim(), createdAt: Date.now() })
  noteDraft.value = ''; saveNotes()
}

// ── 划词添加笔记 ──
const selectedText = ref<string>('')
const selectionAnchor = ref<{ top: number; left: number } | null>(null)
const selectionTargetSceneId = ref<string | null>(null)

function handleSelection(event: MouseEvent | FocusEvent): void {
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed) {
    selectedText.value = ''
    selectionAnchor.value = null
    return
  }
  const text = sel.toString().trim()
  if (!text || text.length < 2) {
    selectedText.value = ''
    selectionAnchor.value = null
    return
  }
  selectedText.value = text

  // 计算选区位置（浮动按钮锚点）
  const range = sel.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  const chatScroll = document.querySelector('.vp-chat-scroll')
  if (!chatScroll) return
  const scrollRect = chatScroll.getBoundingClientRect()
  selectionAnchor.value = {
    top: rect.top - scrollRect.top + chatScroll.scrollTop - 40,
    left: rect.left - scrollRect.left + rect.width / 2 - 40,
  }
  // 记录选中文本所属消息的场景
  const target = event.target as HTMLElement
  const msgEl = target.closest('[data-scene-id]') as HTMLElement | null
  selectionTargetSceneId.value = msgEl?.dataset.sceneId ?? currentScene.value?.id ?? null
}

function addSelectionAsNote(): void {
  if (!selectedText.value.trim() || !record.value) return
  notes.value.unshift({
    id: `n-${Date.now()}`,
    sceneId: selectionTargetSceneId.value,
    text: selectedText.value.trim(),
    createdAt: Date.now(),
    source: 'selection',
  })
  saveNotes()
  selectedText.value = ''
  selectionAnchor.value = null
  window.getSelection()?.removeAllRanges()
}
function deleteNote(id: string): void { notes.value = notes.value.filter((n) => n.id !== id); saveNotes() }
function sceneTitle(sceneId: string | null): string {
  if (!sceneId) return '未关联场景'
  const s = orderedScenes.value.find((o) => o.id === sceneId)
  return s ? `#${s.order} ${s.title}` : sceneId.slice(0, 8)
}

// ─── AI 对话 ───
const conversationId = ref<number | null>(null)
const chatInput = ref('')
const chatMessages = ref<(ChatMessage & { kind: string; tmpId?: string })[]>([])
const chatWsState = ref<'closed' | 'connecting' | 'open' | 'error'>('closed')
const chatSuggestions = ['这节讲了什么？', '总结核心要点', '给我一个练习题']

function onChatEvent(ev: WSInboundEvent): void {
  if (ev.type === 'history') {
    chatMessages.value = (ev.messages ?? []).map((m) => ({
      id: String(m.id), kind: m.role, content: m.content, ts: m.created_at,
    }))
  } else if (ev.type === 'accepted') {
    chatMessages.value.push({ id: `tmp-${Date.now()}-user`, kind: 'user', content: ev.user_message.content, ts: ev.user_message.created_at })
  } else if (ev.type === 'chunk') {
    const aiIdStr = String(ev.ai_message_id)
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last && last.kind === 'assistant' && last.tmpId === aiIdStr) {
      last.content = (last.content ?? '') + ev.content
    } else {
      chatMessages.value.push({ id: aiIdStr, kind: 'assistant', content: ev.content, ts: new Date().toISOString(), tmpId: aiIdStr })
    }
    void nextTick(() => scrollChatToBottom())
  } else if (ev.type === 'complete') {
    const aiIdStr = String(ev.ai_message_id)
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last && last.tmpId === aiIdStr) { last.content = ev.content; delete last.tmpId }
    else { chatMessages.value.push({ id: aiIdStr, kind: 'assistant', content: ev.content, ts: new Date().toISOString() }) }
  } else if (ev.type === 'error') {
    ElMessage({ message: `× ${ev.message}`, customClass: 'x-toast' })
  }
}

const chatWS = useConvWS({ onEvent: onChatEvent, onClose: () => { chatWsState.value = 'closed' } })

async function ensureConversation(): Promise<void> {
  if (conversationId.value) return
  if (!subjectId.value) return

  try {
    // 创建新对话
    const { data } = await createConversation({
      subject_id: subjectId.value,
      title: `视频课对话 - ${record.value?.course?.desc?.slice(0, 20) ?? '未命名'}...`,
      agent: 'video',
    })
    conversationId.value = data.id
  } catch (err) {
    console.error('[ensureConversation] 创建对话失败', err)
    ElMessage({ message: '创建对话失败', customClass: 'x-toast' })
  }
}

async function connectChat(): Promise<void> {
  if (chatWsState.value === 'open' || chatWsState.value === 'connecting') return
  await ensureConversation()
  if (!conversationId.value) return
  try {
    chatWsState.value = 'connecting'
    await chatWS.connect(conversationId.value, 'video')
    chatWsState.value = 'open'
  } catch {
    chatWsState.value = 'error'
  }
}

async function sendChat(): Promise<void> {
  const txt = chatInput.value.trim()
  if (!txt) return
  let wsState = chatWsState.value
  if (wsState !== 'open') { await connectChat(); wsState = chatWsState.value; if (wsState !== 'open') return }
  const sceneCtx = currentScene.value
    ? `\n\n[系统提示] 当前正在观看第 ${currentScene.value.order} 节《${currentScene.value.title}》: ${currentScene.value.description}`
    : ''
  chatWS.send({ type: 'message', content: txt + sceneCtx, role: 'user' })
  chatInput.value = ''
}

const chatScrollRef = ref<HTMLDivElement | null>(null)
function scrollChatToBottom(): void {
  if (!chatScrollRef.value) return
  chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
}

// ─── 思维导图 ───
interface MindNode { id: string; label: string; children: MindNode[]; viewed?: boolean }
const mindTree = computed<MindNode>(() => ({
  id: 'root',
  label: record.value?.course?.desc ?? '视频课程',
  children: orderedScenes.value.map((s) => ({
    id: s.id,
    label: s.title,
    viewed: viewedSceneIds.value.has(s.id),
    children: [],
  })),
}))

// ─── 生命周期 ───
onMounted(() => {
  void loadEntries()
  window.addEventListener('message', handlePlayerMessage)
  if (videoUuid.value) {
    void loadDetail(videoUuid.value)
  } else {
    loading.value = false
  }
  startWatchTimer()
})

onBeforeUnmount(() => {
  stopPoll(); stopOpenmaicPoll(); stopWatchTimer()
  window.removeEventListener('message', handlePlayerMessage)
  if (record.value) void flushProgress(true)
  chatWS.close()
})

watch(() => route.params.id, async (v) => {
  if (v) {
    const n = Array.isArray(v) ? v[0] : (v as string)
    if (n) {
      conversationId.value = null
      chatMessages.value = []
      await loadDetail(n)
    }
  } else {
    // 没有 uuid：清空选中状态
    record.value = null
    loading.value = false
    viewedSceneIds.value = new Set()
    currentSceneIndex.value = -1
    watchedSeconds.value = 0
    completed.value = false
    stopPoll(); stopOpenmaicPoll()
    contentTab.value = 'outline'
  }
})
</script>

<template>
  <div class="vp-shell" :class="{ 'is-idle': !hasSelected }">
    <!-- ═══ 左侧：视频列表 ═══ -->
    <aside class="vp-left">
      <header class="vp-left-header">
        <div class="vp-left-title-row">
          <IconVideo :size="16" />
          <h2 class="vp-left-title">视频课</h2>
        </div>
        <p class="vp-left-sub">
          来自学习计划
          <span v-if="entries.length" class="vp-left-count">{{ entries.length }}</span>
        </p>
      </header>

      <div v-if="listLoading" class="vp-list-loading">加载中…</div>
      <div v-else-if="listError" class="vp-list-empty">× {{ listError }}</div>
      <div v-else-if="entries.length === 0" class="vp-list-empty">
        当前学科没有视频课计划。<br />去「计划」页生成。
      </div>

      <ul v-else class="vp-list">
        <li v-for="e in entries" :key="e.plan.id">
          <button
            type="button"
            class="vp-list-item"
            :class="{
              'is-busy': generating === e.plan.id,
              'is-active': e.plan.id === selectedPlanId,
            }"
            :disabled="generating !== null"
            @click="onPick(e)"
          >
            <span class="vp-list-item-ico">
              <IconVideo :size="14" />
            </span>
            <span class="vp-list-item-body">
              <span class="vp-list-item-name">{{ e.plan.node_name }}</span>
              <span v-if="(e.plan.memory as { step_desc?: string } | undefined)?.step_desc" class="vp-list-item-desc">
                {{ (e.plan.memory as { step_desc?: string }).step_desc }}
              </span>
            </span>
            <span class="vp-list-item-state" :data-tone="statusOf(e).tone">
              <template v-if="statusOf(e).tone === 'ready'"><IconCheck :size="11" /> {{ statusOf(e).text }}</template>
              <template v-else-if="statusOf(e).tone === 'generating'"><IconHourglass :size="11" /> {{ statusOf(e).text }}</template>
              <template v-else-if="statusOf(e).tone === 'error'">× {{ statusOf(e).text }}</template>
              <template v-else><IconArrow :size="11" /> {{ statusOf(e).text }}</template>
            </span>
            <span v-if="generating === e.plan.id" class="vp-list-item-spinner" aria-label="生成中"></span>
          </button>
        </li>
      </ul>
    </aside>

    <!-- ═══ 中间：播放器/空状态 ═══ -->
    <main class="vp-main">
      <!-- 未选中 -> 空状态 -->
      <template v-if="!hasSelected">
        <div class="vp-empty">
          <div class="vp-empty-art"><IconVideo :size="40" /></div>
          <h3 class="vp-empty-title">从左侧选一段视频</h3>
          <p class="vp-empty-sub">点击左侧任意条目即可观看或生成视频课程</p>
        </div>
      </template>

      <!-- 已选中 -> 播放器 -->
      <template v-else>
        <!-- 顶部条 -->
        <div class="vp-main-topbar">
          <div class="vp-eyebrow">
            <span class="vp-chapter-label">
              CHAPTER {{ currentScene?.order ?? '—' }}
              <span class="vp-chapter-total"> / {{ totalScenes }}</span>
            </span>
            <h1 class="vp-chapter-title">{{ currentScene?.title ?? record?.course?.desc ?? '—' }}</h1>
          </div>
          <div class="vp-teacher">
            <span class="vp-teacher-avatar">🤖</span>
            <span>AI 教研 · {{ record?.subject_display ?? '—' }}</span>
          </div>
        </div>

        <!-- 视频播放器 -->
        <div class="vp-video-wrap">
          <div v-if="loading" class="vp-loading">加载中…</div>
          <div v-else-if="detailError" class="vp-error">× {{ detailError }}</div>
          <div v-else-if="record?.state === 'generating'" class="vp-state-msg">⏳ 正在生成课程大纲，请稍候…</div>
          <div v-else-if="record?.state === 'error'" class="vp-state-msg error">❌ 生成失败：{{ record.error_message }}</div>
          <iframe
            v-else-if="record?.iframe_url"
            ref="iframeRef"
            :src="record.iframe_url"
            class="vp-iframe"
            allow="autoplay; fullscreen; speech-synthesis"
            frameborder="0"
            allowfullscreen
          />
          <div v-if="record?.iframe_url" class="vp-video-foot">
            <div class="vp-video-controls">
              <button class="vp-ctrl-btn" title="播放" @click="controlPlay"><IconPlus :size="14" :rotated="45" /></button>
              <button class="vp-ctrl-btn" title="暂停" @click="controlPause"><IconPause :size="14" /></button>
              <button class="vp-ctrl-btn" title="切换倍速" @click="controlToggleSpeed"><IconTimer :size="14" /></button>
              <button class="vp-ctrl-btn" title="刷新进度" @click="controlQuery"><IconRetry :size="14" /></button>
            </div>
            <div class="vp-watched"><IconPin :size="12" /> 累计观看 {{ Math.floor(watchedSeconds / 60) }} 分 {{ watchedSeconds % 60 }} 秒</div>
            <a :href="record.iframe_url" target="_blank" class="vp-open-new">在新窗口打开 ↗</a>
          </div>
        </div>

        <!-- Tabs：大纲 / 简介 / 讲义 / 作业 / 讨论 -->
        <div class="vp-tabs">
          <button
            v-for="t in [
              { id: 'outline', label: '章节大纲' },
              { id: 'intro', label: '简介' },
              { id: 'notes', label: '讲义' },
              { id: 'homework', label: '作业' },
              { id: 'discuss', label: '讨论' },
            ]"
            :key="t.id"
            type="button"
            class="vp-tab"
            :class="{ 'is-active': contentTab === t.id }"
            @click="contentTab = t.id as ContentTab"
          >{{ t.label }}</button>
        </div>

        <!-- Tab body -->
        <div class="vp-tab-body">
          <!-- 章节大纲（原左侧章节列表移入此处） -->
          <div v-if="contentTab === 'outline'" class="vp-outline">
            <div class="vp-outline-header">
              <h3 class="vp-h3">课程大纲</h3>
              <div class="vp-outline-progress">
                <div class="vp-outline-progress-bar">
                  <div class="vp-outline-progress-fill" :style="{ width: overallProgress + '%' }"></div>
                </div>
                <span class="vp-outline-progress-label">{{ viewedSceneIds.size }} / {{ totalScenes }}</span>
              </div>
            </div>
            <ol class="vp-outline-list">
              <li
                v-for="(s, idx) in orderedScenes"
                :key="s.id"
                class="vp-outline-item"
                :class="{ 'is-active': idx === currentSceneIndex, 'is-viewed': viewedSceneIds.has(s.id) }"
                @click="selectScene(idx)"
              >
                <span class="vp-outline-num">{{ s.order }}</span>
                <div class="vp-outline-body">
                  <h4 class="vp-outline-title">{{ s.title }}</h4>
                  <p class="vp-outline-desc">{{ s.description }}</p>
                </div>
                <span class="vp-outline-dot" :class="{ viewed: viewedSceneIds.has(s.id), current: idx === currentSceneIndex }">
                  {{ viewedSceneIds.has(s.id) ? '✓' : '' }}
                </span>
              </li>
            </ol>
          </div>

          <!-- 简介 -->
          <div v-if="contentTab === 'intro'" class="vp-intro">
            <template v-if="introData">
              <h3 class="vp-h3">课程简介</h3>
              <p class="vp-intro-summary">{{ (introData as any).summary }}</p>
              <h3 class="vp-h3">为什么学</h3>
              <p class="vp-intro-why">{{ (introData as any).why_learn }}</p>
              <h3 class="vp-h3">核心概念</h3>
              <ul v-if="(introData as any).key_concepts?.length">
                <li v-for="(c, i) in (introData as any).key_concepts" :key="i">{{ c }}</li>
              </ul>
              <h3 class="vp-h3">学完你将能够</h3>
              <ul v-if="(introData as any).what_you_will_learn?.length">
                <li v-for="(g, i) in (introData as any).what_you_will_learn" :key="i">{{ g }}</li>
              </ul>
            </template>
            <template v-else><p class="vp-muted">课程简介由 AI 生成，暂无数据</p></template>
          </div>

          <!-- 讲义 -->
          <div v-if="contentTab === 'notes'" class="vp-lecture">
            <MarkdownContent
              v-if="currentScene"
              :content="`### ${currentScene.title}\n\n${currentScene.description}\n\n**核心要点:**\n\n${currentScene.key_points.map((k) => '- ' + k).join('\n')}`"
            />
            <p v-else class="vp-muted">请选择章节</p>
          </div>

          <!-- 作业 -->
          <div v-if="contentTab === 'homework'" class="vp-homework">
            <template v-if="homeworkData?.length">
              <h3 class="vp-h3">课后作业</h3>
              <div v-for="(hw, i) in homeworkData as Array<Record<string, unknown>>" :key="(hw as any).id || i" class="vp-homework-item">
                <div class="vp-homework-header">
                  <span class="vp-homework-num">{{ i + 1 }}</span>
                  <span class="vp-homework-tag" :class="'difficulty-' + (hw as any).difficulty">{{ (hw as any).difficulty === 'easy' ? '简单' : (hw as any).difficulty === 'medium' ? '中等' : '困难' }}</span>
                  <span class="vp-homework-type">{{ (hw as any).type === 'choice' ? '选择题' : (hw as any).type === 'short_answer' ? '简答题' : '编程题' }}</span>
                </div>
                <h4 class="vp-homework-title">{{ (hw as any).title }}</h4>
                <p class="vp-homework-desc">{{ (hw as any).description }}</p>
                <details class="vp-homework-hint"><summary>查看提示</summary><p>{{ (hw as any).answer_hint }}</p></details>
              </div>
            </template>
            <template v-else><p class="vp-muted">课后作业由 AI 生成，暂无数据</p></template>
          </div>

          <!-- 讨论 -->
          <div v-if="contentTab === 'discuss'" class="vp-discuss">
            <div class="vp-discuss-empty">
              <IconChat :size="20" />
              <p>想讨论？请在右侧 AI 对话面板发起</p>
            </div>
          </div>
        </div>

        <!-- 导航 -->
        <nav class="vp-nav">
          <button class="vp-nav-btn" :disabled="currentSceneIndex <= 0" @click="prevScene"><IconArrow :size="14" :rotated="180" /> 上一节</button>
          <div class="vp-nav-progress">
            <span>{{ (currentSceneIndex + 1) || 0 }} / {{ totalScenes }}</span>
            <div class="vp-nav-progress-bar"><div :style="{ width: ((currentSceneIndex + 1) / totalScenes) * 100 + '%' }"></div></div>
          </div>
          <button class="vp-nav-btn primary" :disabled="currentSceneIndex >= totalScenes - 1" @click="nextScene">下一节 <IconArrow :size="14" /></button>
        </nav>
      </template>
    </main>

    <!-- ═══ 右侧：智能体协作空间 ═══ -->
    <aside class="vp-right" :class="{ 'is-empty': !hasSelected }">
      <header class="vp-right-header">
        <div>
          <h3 class="vp-right-title"><IconBulb :size="16" /> 智能体协作空间</h3>
          <p class="vp-right-sub">2 个 Agent 在线 · 上下文跟随当前章节</p>
        </div>
        <span class="vp-right-status" :class="'ws-' + chatWsState">
          {{ chatWsState === 'open' ? '已连接' : chatWsState === 'connecting' ? '连接中' : '离线' }}
        </span>
      </header>

      <div class="vp-agent-tabs">
        <button type="button" class="vp-agent-tab" :class="{ 'is-active': agentTab === 'notes' }" @click="agentTab = 'notes'">
          <IconNotepad :size="14" /> 笔记 <span class="vp-agent-tab-count">{{ notes.length }}</span>
        </button>
        <button type="button" class="vp-agent-tab" :class="{ 'is-active': agentTab === 'chat' }" @click="agentTab = 'chat'">
          <IconChat :size="14" /> AI 对话
        </button>
        <button type="button" class="vp-agent-tab" :class="{ 'is-active': agentTab === 'mindmap' }" @click="agentTab = 'mindmap'">
          <IconBulb :size="14" /> 思维导图
        </button>
      </div>

      <div v-if="agentTab === 'notes'" class="vp-agent-body">
        <div class="vp-note-input">
          <textarea v-model="noteDraft" rows="2" placeholder="随时记录灵感… (Ctrl+Enter 添加)" @keydown.ctrl.enter.prevent="addNote" />
          <button class="vp-add-note" type="button" @click="addNote">+ 添加</button>
        </div>
        <ul class="vp-note-list">
          <li v-for="n in notes" :key="n.id" class="vp-note">
            <div class="vp-note-meta"><span class="vp-note-scene">{{ sceneTitle(n.sceneId) }}</span><button class="vp-note-del" type="button" @click="deleteNote(n.id)">删除</button></div>
            <div class="vp-note-text">{{ n.text }}</div>
          </li>
          <li v-if="!notes.length" class="vp-empty">还没有笔记</li>
        </ul>
      </div>

      <div v-else-if="agentTab === 'chat'" class="vp-agent-body vp-chat-body" @mouseup="handleSelection">
        <div ref="chatScrollRef" class="vp-chat-scroll">
          <div v-if="!chatMessages.length" class="vp-chat-empty">
            <p>基于当前章节上下文，问 AI 任何问题</p>
            <div class="vp-chat-suggestions">
              <button v-for="s in chatSuggestions" :key="s" type="button" class="vp-chat-suggestion" @click="chatInput = s; sendChat()">{{ s }}</button>
            </div>
          </div>
          <div v-for="(m, i) in chatMessages" :key="i" class="vp-msg" :class="'vp-msg-' + m.kind" :data-scene-id="currentScene?.id ?? ''">
            <div class="vp-msg-avatar">{{ m.kind === 'user' ? '🙂' : '🤖' }}</div>
            <div class="vp-msg-bubble">
              <StreamingMarkdown :text="m.content" :pending="m.kind !== 'user' && i === chatMessages.length - 1 && m.content.length > 0" />
            </div>
          </div>
          <!-- 划词浮动按钮 -->
          <button
            v-if="selectionAnchor && selectedText"
            class="vp-selection-fab"
            :style="{ top: selectionAnchor.top + 'px', left: selectionAnchor.left + 'px' }"
            type="button"
            @click="addSelectionAsNote"
          >
            ✏️ 添加到笔记
          </button>
        </div>
        <form class="vp-chat-input" @submit.prevent="sendChat">
          <input v-model="chatInput" placeholder="输入问题… (Enter 发送, Shift+Enter 换行)" :disabled="chatWsState === 'connecting'" />
          <button type="submit" :disabled="!chatInput.trim() || chatWsState !== 'open'">发送</button>
        </form>
      </div>

      <div v-else-if="agentTab === 'mindmap'" class="vp-agent-body vp-mindmap-body">
        <p class="vp-mindmap-hint">课程结构 · 已学 <strong>{{ viewedSceneIds.size }}</strong> / {{ totalScenes }}</p>
        <svg class="vp-mindmap-svg" viewBox="0 0 360 800" preserveAspectRatio="xMidYMid meet">
          <g class="vp-mindmap-root">
            <rect x="80" y="20" width="200" height="56" rx="12" fill="#0071e3" />
            <text x="180" y="48" text-anchor="middle" fill="#fff" font-size="13" font-weight="600">{{ mindTree.label.slice(0, 14) }}</text>
            <text x="180" y="65" text-anchor="middle" fill="rgba(255,255,255,.8)" font-size="10">{{ mindTree.children.length }} 个场景</text>
          </g>
          <g v-for="(c, i) in mindTree.children" :key="c.id">
            <path :d="`M180 76 L180 ${100 + i * 60} L${c.viewed ? 60 : 60} ${100 + i * 60} L${c.viewed ? 90 : 90} ${100 + i * 60 + 20}`" :stroke="c.viewed ? '#34c759' : '#d2d2d7'" stroke-width="1.5" fill="none" />
            <rect x="40" :y="100 + i * 60" width="280" height="40" rx="8" :fill="c.viewed ? '#e8f8ee' : '#f5f5f7'" :stroke="c.viewed ? '#34c759' : '#d2d2d7'" stroke-width="1" />
            <text x="180" :y="100 + i * 60 + 18" text-anchor="middle" font-size="10" fill="#6e6e73">SCENE {{ i + 1 }}</text>
            <text x="180" :y="100 + i * 60 + 32" text-anchor="middle" font-size="12" font-weight="500" fill="#1d1d1f">{{ c.label.slice(0, 16) }}</text>
            <text v-if="c.viewed" x="305" :y="100 + i * 60 + 24" text-anchor="middle" font-size="12" fill="#34c759">✓</text>
          </g>
        </svg>
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* ─── 整体壳 ─── */
.vp-shell {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr) 430px;
  height: calc(100vh - 64px);
  background: var(--x-canvas, #f5f5f7);
  font-family: var(--x-font-display, -apple-system, 'SF Pro Text', 'Helvetica Neue', sans-serif);
}
.vp-shell.is-idle {
  grid-template-columns: 330px 1fr 0;
}
.vp-shell.is-idle .vp-right {
  display: none;
}

/* ─── 左：视频列表 ─── */
.vp-left {
  border-right: 1px solid var(--x-hairline, #e5e5ea);
  background: #fff;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden; /* 防止滚动穿透 */
}
.vp-left-header {
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--x-hairline, #e5e5ea);
}
.vp-left-title-row {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--x-primary, #0071e3);
}
.vp-left-title {
  font: 600 18px/1.3;
  color: var(--x-fg, #1d1d1f);
  margin: 0;
}
.vp-left-sub {
  font: 400 12px/1.6;
  color: #6e6e73;
  margin: 8px 0 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.vp-left-count {
  font: 500 11px/1;
  background: rgba(0,113,227,0.08);
  color: var(--x-primary, #0071e3);
  padding: 4px 10px;
  border-radius: 999px;
}
.vp-list-loading,
.vp-list-empty {
  padding: 32px 16px;
  font: 400 13px/1.6;
  color: #6e6e73;
  text-align: center;
}
.vp-list {
  list-style: none;
  padding: 8px 12px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px; /* 增加卡片间距 */
  overflow-y: auto;
  flex: 1;
  overscroll-behavior: contain; /* 防止滚动穿透 */
}
.vp-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid transparent;
  border-left: 3px solid transparent;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: inherit;
  transition: background 0.15s, border-color 0.15s, transform 0.1s, box-shadow 0.15s;
}
.vp-list-item:hover:not(:disabled) {
  background: #fff;
  border-color: var(--x-hairline, #e5e5ea);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.vp-list-item.is-active {
  background: #fff;
  border-left-color: var(--x-primary, #0071e3);
  box-shadow: 0 2px 12px rgba(0,113,227,0.12);
}
.vp-list-item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.vp-list-item.is-busy {
  background: rgba(0,113,227,0.08);
  border-color: var(--x-primary, #0071e3);
}
.vp-list-item-ico {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(0,113,227,0.08);
  color: var(--x-primary, #0071e3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.vp-list-item.is-busy .vp-list-item-ico {
  background: var(--x-primary, #0071e3);
  color: #fff;
}
.vp-list-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vp-list-item-name {
  font: 600 13px/1.5;
  color: var(--x-fg, #1d1d1f);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.vp-list-item-desc {
  font: 400 11px/1.5;
  color: #6e6e73;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.vp-list-item-state {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 500 11px/1;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}
.vp-list-item-state[data-tone='ready'] { background: rgba(52,199,89,0.12); color: #34c759; }
.vp-list-item-state[data-tone='generating'] { background: rgba(255,149,0,0.12); color: #ff9500; }
.vp-list-item-state[data-tone='error'] { background: rgba(255,59,48,0.12); color: #ff3b30; }
.vp-list-item-state[data-tone='pending'] { background: #f5f5f7; color: #8e8e93; }
.vp-list-item-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0,113,227,0.2);
  border-top-color: var(--x-primary, #0071e3);
  border-radius: 50%;
  animation: vp-spin 0.6s linear infinite;
}
@keyframes vp-spin { to { transform: rotate(360deg); } }

/* ─── 中间：播放器/空状态 ─── */
.vp-main {
  padding: 18px 24px 24px;
  overflow-y: auto;
  min-width: 0;
  overscroll-behavior: contain; /* 防止滚动穿透 */
}
.vp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  color: #6e6e73;
}
.vp-empty-art {
  margin-bottom: 16px;
  opacity: 0.3;
}
.vp-empty-title {
  font: 600 18px/1.3;
  color: var(--x-fg, #1d1d1f);
  margin: 0 0 6px;
}
.vp-empty-sub {
  font-size: 13px;
  color: #6e6e73;
  margin: 0;
}

.vp-main-topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 16px;
}
.vp-eyebrow { min-width: 0; }
.vp-chapter-label {
  font: 600 11px/1;
  color: var(--x-primary, #0071e3);
  letter-spacing: 0.06em;
}
.vp-chapter-total { color: #6e6e73; font-weight: 400; }
.vp-chapter-title {
  font: 600 22px/1.3;
  color: var(--x-fg, #1d1d1f);
  margin: 4px 0 0;
}
.vp-teacher {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border-radius: 999px;
  border: 1px solid var(--x-hairline, #e5e5ea);
  font-size: 12px;
  color: var(--x-fg, #1d1d1f);
  white-space: nowrap;
}
.vp-teacher-avatar {
  width: 24px; height: 24px;
  background: linear-gradient(135deg, #6e6e73, #1d1d1f);
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vp-video-wrap {
  position: relative;
  background: #000;
  border-radius: 14px;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  margin-bottom: 8px;
}
.vp-iframe { width: 100%; height: 100%; display: block; }
.vp-loading, .vp-error, .vp-state-msg {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 14px;
}
.vp-error, .vp-state-msg.error { background: rgba(0,0,0,0.7); }
.vp-state-msg { background: rgba(0,0,0,0.5); }
.vp-video-foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 10px; background: rgba(0,0,0,0.6); color: #fff; font-size: 11px; gap: 8px;
}
.vp-video-controls { display: flex; gap: 4px; }
.vp-ctrl-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px;
  border: 1px solid rgba(255,255,255,0.2); border-radius: 6px;
  background: rgba(255,255,255,0.08); color: #fff; cursor: pointer; transition: background 0.15s;
}
.vp-ctrl-btn:hover { background: rgba(255,255,255,0.18); }
.vp-watched { display: inline-flex; align-items: center; gap: 4px; }
.vp-open-new { color: rgba(255,255,255,0.7); text-decoration: none; }
.vp-open-new:hover { color: #fff; text-decoration: underline; }

/* ─── Tabs ─── */
.vp-tabs {
  display: flex;
  gap: 20px;
  border-bottom: 1px solid var(--x-hairline, #e5e5ea);
  margin: 16px 0 12px;
  overflow-x: auto;
}
.vp-tab {
  background: none; border: none;
  padding: 8px 0 10px;
  font: 500 13px/1;
  color: #6e6e73;
  cursor: pointer;
  position: relative;
  white-space: nowrap;
}
.vp-tab:hover { color: var(--x-fg, #1d1d1f); }
.vp-tab.is-active { color: var(--x-fg, #1d1d1f); }
.vp-tab.is-active::after {
  content: ''; position: absolute; bottom: -1px; left: 0; right: 0;
  height: 2px; background: var(--x-primary, #0071e3);
}

.vp-tab-body {
  min-height: 200px;
  background: #fff;
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.vp-h3 { font: 600 14px/1; color: var(--x-fg, #1d1d1f); margin: 0 0 8px; }
.vp-h3:not(:first-child) { margin-top: 16px; }
.vp-tab-body p { font-size: 13px; line-height: 1.7; color: #424245; margin: 0 0 8px; }
.vp-tab-body ul { padding-left: 20px; margin: 0; }
.vp-tab-body li { font-size: 13px; line-height: 1.7; color: #424245; }
.vp-muted { color: #a1a1a6 !important; }

/* ─── 章节大纲 (tab 内) ─── */
.vp-outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.vp-outline-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}
.vp-outline-progress-bar {
  width: 80px;
  height: 4px;
  background: #f5f5f7;
  border-radius: 999px;
  overflow: hidden;
}
.vp-outline-progress-fill {
  height: 100%;
  background: var(--x-primary, #0071e3);
  transition: width 0.3s;
}
.vp-outline-progress-label {
  font: 500 11px/1;
  color: #6e6e73;
}
.vp-outline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vp-outline-item {
  display: grid;
  grid-template-columns: 28px 1fr 20px;
  gap: 8px;
  align-items: start;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;
}
.vp-outline-item:hover { background: rgba(0,113,227,0.04); }
.vp-outline-item.is-active { background: rgba(0,113,227,0.06); }
.vp-outline-num {
  font: 600 11px/1;
  color: var(--x-primary, #0071e3);
  background: rgba(0,113,227,0.08);
  width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 999px;
  margin-top: 2px;
}
.vp-outline-title {
  font: 500 13px/1.4;
  color: var(--x-fg, #1d1d1f);
  margin: 0 0 2px;
}
.vp-outline-desc {
  font-size: 11px;
  color: #6e6e73;
  margin: 0;
  line-height: 1.4;
}
.vp-outline-dot {
  width: 8px; height: 8px;
  border-radius: 999px;
  background: #d2d2d7;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  margin-top: 6px;
}
.vp-outline-dot.current {
  background: var(--x-primary, #0071e3);
  box-shadow: 0 0 0 3px rgba(0,113,227,0.18);
}
.vp-outline-dot.viewed {
  background: #34c759;
  color: #fff;
}

/* ─── 讨论 ─── */
.vp-discuss-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 32px 0; color: #6e6e73; font-size: 13px;
}

/* ─── 导航 ─── */
.vp-nav {
  display: grid; grid-template-columns: 1fr 2fr 1fr; align-items: center;
  gap: 12px; padding: 14px 18px;
  background: #fff; border-radius: 14px;
  border: 1px solid var(--x-hairline, #e5e5ea);
}
.vp-nav-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: none; border: 1px solid var(--x-hairline, #e5e5ea);
  border-radius: 999px; padding: 8px 14px;
  font: 500 13px/1; color: var(--x-fg, #1d1d1f);
  cursor: pointer; justify-self: start;
}
.vp-nav-btn.primary {
  background: var(--x-primary, #0071e3); color: #fff; border-color: var(--x-primary, #0071e3);
  justify-self: end;
}
.vp-nav-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.vp-nav-progress {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  font: 500 12px/1; color: #6e6e73;
}
.vp-nav-progress-bar {
  width: 100%; height: 3px; background: #f5f5f7; border-radius: 999px; overflow: hidden;
}
.vp-nav-progress-bar > div { height: 100%; background: var(--x-primary, #0071e3); transition: width 0.3s; }

/* ─── 右：智能体 ─── */
.vp-right {
  border-left: 1px solid var(--x-hairline, #e5e5ea);
  background: #fff;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.vp-right.is-empty {
  opacity: 0.5;
}
.vp-right-header {
  padding: 14px 18px 12px;
  border-bottom: 1px solid var(--x-hairline, #e5e5ea);
  display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;
}
.vp-right-title {
  display: inline-flex; align-items: center; gap: 6px;
  font: 600 14px/1; color: var(--x-fg, #1d1d1f); margin: 0;
}
.vp-right-sub { font-size: 11px; color: #6e6e73; margin: 4px 0 0; }
.vp-right-status {
  font: 500 10px/1; padding: 3px 8px; border-radius: 999px;
  background: #f5f5f7; color: #6e6e73;
}
.vp-right-status.ws-open { background: #e8f8ee; color: #1f7a3a; }
.vp-right-status.ws-connecting { background: #fff4d6; color: #8b6a00; }
.vp-right-status.ws-error { background: #fde7e7; color: #b3261e; }

.vp-agent-tabs {
  display: flex; gap: 4px; padding: 8px 12px 0;
  border-bottom: 1px solid var(--x-hairline, #e5e5ea);
}
.vp-agent-tab {
  display: inline-flex; align-items: center; gap: 4px;
  background: none; border: none; padding: 10px 10px;
  font: 500 12px/1; color: #6e6e73; cursor: pointer;
  position: relative; border-radius: 8px 8px 0 0;
}
.vp-agent-tab:hover { color: var(--x-fg, #1d1d1f); }
.vp-agent-tab.is-active { color: var(--x-fg, #1d1d1f); background: #f5f5f7; }
.vp-agent-tab-count {
  background: var(--x-primary, #0071e3);
  color: #fff; font-size: 10px; padding: 1px 5px; border-radius: 999px;
  line-height: 1.3;
}
.vp-agent-body {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column;
  overscroll-behavior: contain; /* 防止滚动穿透 */
}
.vp-note-input {
  padding: 12px; border-bottom: 1px solid var(--x-hairline, #e5e5ea);
  display: flex; gap: 8px; align-items: flex-end;
}
.vp-note-input textarea {
  flex: 1; resize: none; border: 1px solid var(--x-hairline, #e5e5ea);
  border-radius: 8px; padding: 8px 10px; font: 400 12px/1.4; outline: none;
}
.vp-add-note {
  background: var(--x-primary, #0071e3); color: #fff;
  border: none; border-radius: 8px; padding: 8px 12px;
  font: 500 12px/1; cursor: pointer; white-space: nowrap;
}
.vp-note-list { list-style: none; margin: 0; padding: 8px 12px; display: flex; flex-direction: column; gap: 8px; }
.vp-note { padding: 8px 10px; background: #f5f5f7; border-radius: 8px; }
.vp-note-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.vp-note-scene { font-size: 10px; color: #6e6e73; }
.vp-note-del { background: none; border: none; font-size: 10px; color: #ff3b30; cursor: pointer; padding: 0; }
.vp-note-text { font-size: 12px; line-height: 1.5; color: var(--x-fg, #1d1d1f); white-space: pre-wrap; word-break: break-word; }
.vp-empty { text-align: center; padding: 24px; color: #6e6e73; font-size: 12px; }

.vp-chat-body { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.vp-chat-scroll {
  flex: 1 1 0; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px;
  overscroll-behavior: contain;
  min-height: 0;
}
.vp-chat-empty { text-align: center; padding: 20px 0; }
.vp-chat-empty p { font-size: 12px; color: #6e6e73; margin-bottom: 12px; }
.vp-chat-suggestions { display: flex; flex-direction: column; gap: 6px; }
.vp-chat-suggestion {
  background: #f5f5f7; border: 1px solid var(--x-hairline, #e5e5ea);
  border-radius: 8px; padding: 8px 12px; font: 400 12px/1; color: var(--x-fg, #1d1d1f);
  cursor: pointer; text-align: left;
}
.vp-chat-suggestion:hover { background: rgba(0,113,227,0.06); border-color: var(--x-primary, #0071e3); }
.vp-msg { display: flex; gap: 8px; align-items: flex-start; }
.vp-msg-user { flex-direction: row-reverse; }
.vp-msg-avatar { font-size: 20px; line-height: 1; flex-shrink: 0; }
.vp-msg-bubble {
  max-width: 80%; padding: 8px 12px; border-radius: 12px;
  font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
}
.vp-chat-input {
  flex-shrink: 0; display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--x-hairline, #e5e5ea);
  background: #fff;
}
.vp-chat-input input {
  flex: 1; padding: 8px 12px; border: 1px solid var(--x-hairline, #e5e5ea);
  border-radius: 8px; font-size: 12px; outline: none;
}
.vp-chat-input input:focus { border-color: var(--x-primary, #0071e3); }
.vp-chat-input button {
  padding: 8px 16px; background: var(--x-primary, #0071e3); color: #fff;
  border: none; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer;
}
.vp-chat-input button:disabled { opacity: 0.5; cursor: default; }

/* 划词浮动按钮 */
.vp-selection-fab {
  position: absolute; z-index: 100;
  padding: 6px 12px; border: none; border-radius: 6px;
  background: var(--x-primary, #0071e3); color: #fff;
  font-size: 12px; font-weight: 500; cursor: pointer;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transition: all 0.15s;
}
.vp-selection-fab:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}
</style>