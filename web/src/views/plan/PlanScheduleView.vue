<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { getSubjectDisplayName } from '@/api/subjects'
import { createConversation, listConversations } from '@/api/conversations'
import { useConvWS } from '@/composables/use_conv_ws'
import type { WSInboundEvent } from '@/types/chat'
import MarkdownContent from '@/components/MarkdownContent.vue'
import {
  listPlans,
  skipPlan,
  type LearningPlan,
  type PlanStepType,
} from '@/api/plan'
import { startAutoQuiz } from '@/api/quiz'

const mySubjects = useMySubjectsStore()
const router = useRouter()

/* ── Current subject ─────────────────────────────── */
const currentSubject = useCurrentSubjectStore()
const courseName = computed(() => getSubjectDisplayName(currentSubject.code))

// 当前 subject 对应的 MySubject.id (后端创建 conversation 需要 numeric pk)
const currentSubjectId = computed<number | null>(() => {
  const s = mySubjects.subjects.find((m) => m.name === currentSubject.code)
  return s?.id ?? null
})

/* ── Plan group: 一个节点 + 5 步 step plan ─────────── */
interface PlanGroup {
  node_id: string
  node_name: string
  node_type: string
  difficulty: number
  tag?: string
  steps: LearningPlan[]
}

const allPlans = ref<LearningPlan[]>([])

const planGroups = computed<PlanGroup[]>(() => {
  const map = new Map<string, PlanGroup>()
  for (const p of allPlans.value) {
    if (!map.has(p.node_id)) {
      map.set(p.node_id, {
        node_id: p.node_id,
        node_name: p.node_name,
        node_type: p.node_type,
        difficulty: p.difficulty,
        tag: p.memory?.tag,
        steps: [],
      })
    }
    map.get(p.node_id)!.steps.push(p)
  }
  // 每个 group 内 step 按 step_order 排序
  for (const g of map.values()) {
    g.steps.sort((a, b) => (a.memory?.step_order ?? 0) - (b.memory?.step_order ?? 0))
  }
  // 按第一个 step 的 expected_completion_time 排序（全局顺序）
  return [...map.values()].sort((a, b) => {
    const aTime = a.steps[0]?.expected_completion_time ?? ''
    const bTime = b.steps[0]?.expected_completion_time ?? ''
    return aTime.localeCompare(bTime)
  })
})

/* ── Kanban: 按周分组 ───────────────────────────── */
interface WeekColumn {
  key: string
  label: string       // e.g. "6/23 - 6/29"
  weekStart: Date
  weekEnd: Date
  isCurrent: boolean
  isPast: boolean
  plans: LearningPlan[]
  doneCount: number
  totalCount: number
}

function getWeekStart(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - d.getDay()) // 周日=0 作为一周开始
  return d
}

function getWeekEnd(start: Date): Date {
  const d = new Date(start)
  d.setDate(d.getDate() + 6)
  d.setHours(23, 59, 59, 999)
  return d
}

function formatWeekLabel(start: Date, end: Date): string {
  const s = `${start.getMonth() + 1}/${start.getDate()}`
  const e = `${end.getMonth() + 1}/${end.getDate()}`
  return `${s} - ${e}`
}

const weekColumns = computed<WeekColumn[]>(() => {
  const now = new Date()
  const currentWeekStart = getWeekStart(now)
  const columns: WeekColumn[] = []
  const colMap = new Map<string, WeekColumn>()

  for (const p of allPlans.value) {
    let weekStart: Date
    if (p.expected_completion_time) {
      weekStart = getWeekStart(new Date(p.expected_completion_time))
    } else {
      // 没有截止日期的放到当前周
      weekStart = currentWeekStart
    }
    const key = weekStart.toISOString().slice(0, 10)
    if (!colMap.has(key)) {
      const weekEnd = getWeekEnd(weekStart)
      colMap.set(key, {
        key,
        label: formatWeekLabel(weekStart, weekEnd),
        weekStart,
        weekEnd,
        isCurrent: key === currentWeekStart.toISOString().slice(0, 10),
        isPast: weekEnd < now,
        plans: [],
        doneCount: 0,
        totalCount: 0,
      })
    }
    const col = colMap.get(key)!
    col.plans.push(p)
    col.totalCount++
    if (p.state === 'success') col.doneCount++
  }

  // 排序：按 weekStart 升序
  columns.push(...colMap.values())
  columns.sort((a, b) => a.weekStart.getTime() - b.weekStart.getTime())
  return columns
})

/* ── 全局统计 ────────────────────────────────────── */
const totalSteps = computed(() => allPlans.value.length)
const doneSteps = computed(() => allPlans.value.filter(p => p.state === 'success').length)
const skippedSteps = computed(() => allPlans.value.filter(p => p.state === 'skipped').length)
const pendingSteps = computed(() => allPlans.value.filter(p => p.state === 'pending').length)
const progress = computed(() =>
  totalSteps.value === 0 ? 0 : Math.round((doneSteps.value / totalSteps.value) * 100)
)

const stepTypeDistribution = computed<Record<string, number>>(() => {
  const dist: Record<string, number> = {}
  for (const p of allPlans.value) {
    const t = p.memory?.step_type ?? 'reading'
    dist[t] = (dist[t] || 0) + 1
  }
  return dist
})

/* ── Step type UI config ─────────────────────────── */
interface TypeConfig {
  label: string
  icon: string
}

const STEP_TYPE_CONFIG: Record<string, TypeConfig> = {
  reading: {
    label: '看书',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M1.5 2.5h4a1 1 0 011 1v7.5a.7.7 0 00-.7-.5h-4a.5.5 0 01-.5-.5V3a.5.5 0 01.5-.5zM11.5 2.5h-4a1 1 0 00-1 1v7.5a.7.7 0 01.7-.5h4a.5.5 0 00.5-.5V3a.5.5 0 00-.5-.5z" stroke="currentColor" stroke-width="1.3"/></svg>',
  },
  video: {
    label: '视频教学',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="1" y="2.5" width="7" height="8" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M8 5.5l3.5-2v6l-3.5-2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  },
  quiz: {
    label: '刷题',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M4.5 1v2.5M8.5 1v2.5M2.5 5h8M3 3.5h7a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5H3A1.5 1.5 0 011.5 11V5A1.5 1.5 0 013 3.5z" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><path d="M5 8l1.2 1.2L8.5 7" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  },
  qa: {
    label: '对话',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M2 2.5h6a1.5 1.5 0 011.5 1.5v3a1.5 1.5 0 01-1.5 1.5H5.5L3 10.5V8.5H2A.5.5 0 011.5 8V3A.5.5 0 012 2.5z" stroke="currentColor" stroke-width="1.3"/><circle cx="4.5" cy="5.5" r=".7" fill="currentColor"/><circle cx="6.5" cy="5.5" r=".7" fill="currentColor"/><circle cx="8.5" cy="5.5" r=".7" fill="currentColor"/></svg>',
  },
  chapter_quiz: {
    label: '章节测验',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><rect x="1.5" y="1" width="10" height="11" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M4 4h5M4 6.5h5M4 9h3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>',
  },
  exam: {
    label: '综合测评',
    icon: '<svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M3.5 1h6a1 1 0 011 1v9a1 1 0 01-1 1h-6a1 1 0 01-1-1V2a1 1 0 011-1z" stroke="currentColor" stroke-width="1.3"/><path d="M5 4.5h3M5 7h2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><circle cx="9" cy="9" r="1.5" fill="currentColor"/></svg>',
  },
}

const STEP_ROUTE: Record<string, string> = {
  reading: 'app-galaxy',
  video: 'app-video-detail',
  quiz: 'app-exercise',
  chapter_quiz: 'app-exercise',
  qa: 'app-dialog',
  exam: 'app-exam',
}

// 当从计划触发时，quiz/chapter_quiz 直接跳转答题页而非列表页
const STEP_DETAIL_ROUTE: Record<string, string> = {
  quiz: 'app-exercise-detail',
  chapter_quiz: 'app-exercise-detail',
}

const PLAN_PROMPT_KEY = 'aiteach.plan_prompt'

const generatingQuizForPlanId = ref<number | null>(null)

async function startStep(plan: LearningPlan): Promise<void> {
  const stepType = plan.memory?.step_type as PlanStepType | undefined
  if (!stepType) return
  const routeName = STEP_ROUTE[stepType]
  if (!routeName) return

  // 如果是刷题/章节测验类型的计划，自动出题
  if ((stepType === 'quiz' || stepType === 'chapter_quiz') && currentSubjectId.value && plan.state === 'pending') {
    generatingQuizForPlanId.value = plan.id
    try {
      const { data } = await startAutoQuiz({
        subjectId: currentSubjectId.value,
        nodeId: plan.node_id,
        nodeName: plan.node_name,
        planId: plan.id,
        extraPrompt: plan.memory?.step_desc as string || '',
      })
      // 存当前 plan_id 和 task_id 让练习页用
      sessionStorage.setItem('aiteach.plan_id', String(plan.id))
      sessionStorage.setItem('aiteach.quiz_task_id', data.task_id)
      generatingQuizForPlanId.value = null
      router.push({ name: 'app-exercise-detail', params: { taskId: data.task_id }, query: { plan_id: plan.id } })
      return
    } catch {
      generatingQuizForPlanId.value = null
      // fallback: 直接跳转，让练习页自己处理
    }
  }

  // 存 plan 的 step_desc 给目标页用
  if (plan.memory?.step_desc) {
    sessionStorage.setItem(PLAN_PROMPT_KEY, plan.memory.step_desc)
  }
  // 存当前 plan_id 让目标页关联
  sessionStorage.setItem('aiteach.plan_id', String(plan.id))
  router.push({ name: routeName })
}

/* ── Status display ──────────────────────────────── */
const STATE_LABEL: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  success: '已完成',
  failed: '已失败',
  skipped: '已跳过',
}

function stateClass(state: string): string {
  return `step-state step-state-${state}`
}

/* ── Group done progress ─────────────────────────── */
function groupProgress(g: PlanGroup): { done: number; total: number; pct: number } {
  const total = g.steps.length
  const done = g.steps.filter(s => s.state === 'success').length
  const pct = total === 0 ? 0 : Math.round((done / total) * 100)
  return { done, total, pct }
}

/* ── Chat types ──────────────────────────────────── */
interface ChatMessage {
  role: 'ai' | 'user'
  text: string
  modification?: string[]
  streaming?: boolean
}

/* ── Reactive state ──────────────────────────────── */
const loading = ref(true)
const error = ref('')
const planConvId = ref<number | null>(null)

// ── 选中（给 AI 看的 plan_ids 集合） ─────────────────
const selectedPlanIds = ref<Set<number>>(new Set())
function toggleSelectPlan(id: number): void {
  const s = new Set(selectedPlanIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedPlanIds.value = s
}
function clearSelection(): void {
  selectedPlanIds.value = new Set()
}
const selectedPlans = computed(() =>
  allPlans.value.filter(p => selectedPlanIds.value.has(p.id))
)

/* ── 建议预览状态 ─────────────────────────────────── */
interface SuggestedPlan {
  target_agent?: string
  plan_difficulty?: string
  node_id?: string
  node_name?: string
  step_type?: string
  state?: string
  [key: string]: any
}
const suggestedPlans = ref<SuggestedPlan[]>([])

const conversation = ref<ChatMessage[]>([])

const streamingAiIdx = ref(-1)
const currentAiServerId = ref<number | null>(null)

/* ── Computed ────────────────────────────────────── */
const inputText = ref('')
const isTyping = ref(false)
const messagesRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)
const wsStatus = ref<string>('idle')

/* ── WebSocket ───────────────────────────────────── */
const ws = useConvWS({
  onEvent: handleWSEvent,
  onClose: (info) => {
    if (!info.clean) {
      // eslint-disable-next-line no-console
      console.warn('[plan-ws] close:', info.code, info.reason)
    }
    wsStatus.value = 'closed'
    isTyping.value = false
  },
})

function handleWSEvent(ev: WSInboundEvent): void {
  switch (ev.type) {
    case 'history': {
      const msgs = ev.messages ?? []
      const loaded: ChatMessage[] = []
      for (const m of msgs) {
        if (m.role === 'user') {
          loaded.push({ role: 'user', text: m.content })
        } else if (m.role === 'assistant' && m.content) {
          loaded.push({ role: 'ai', text: m.content })
        }
      }
      if (loaded.length > 0) {
        conversation.value = loaded
      }
      scrollMessages()
      break
    }
    case 'state': {
      wsStatus.value = ev.ai_state ?? 'idle'
      break
    }
    case 'resume': {
      if (streamingAiIdx.value < 0) {
        conversation.value.push({ role: 'ai', text: ev.content, streaming: true })
        streamingAiIdx.value = conversation.value.length - 1
      } else {
        conversation.value[streamingAiIdx.value]!.text = ev.content
      }
      currentAiServerId.value = ev.ai_message_id
      isTyping.value = false
      scrollMessages()
      break
    }
    case 'accepted': {
      currentAiServerId.value = ev.ai_message_id
      if (ev.ai_state === 'generating' || ev.ai_state === 'idle') {
        isTyping.value = true
      }
      break
    }
    case 'chunk': {
      isTyping.value = false
      if (streamingAiIdx.value < 0) {
        conversation.value.push({ role: 'ai', text: ev.content, streaming: true })
        streamingAiIdx.value = conversation.value.length - 1
      } else {
        conversation.value[streamingAiIdx.value]!.text += ev.content
      }
      scrollMessages()
      break
    }
    case 'complete': {
      isTyping.value = false
      if (streamingAiIdx.value >= 0) {
        const msg = conversation.value[streamingAiIdx.value]!
        msg.text = ev.content
        msg.streaming = false
      } else {
        conversation.value.push({ role: 'ai', text: ev.content })
      }
      streamingAiIdx.value = -1
      currentAiServerId.value = null
      scrollMessages()
      // preview 模式返回建议
      const meta = ev.meta as Record<string, unknown> | undefined
      if (meta?.mode === 'preview' && Array.isArray(meta.suggested_plans)) {
        suggestedPlans.value = meta.suggested_plans as SuggestedPlan[]
      } else {
        suggestedPlans.value = []
        // 真实编辑模式：刷新 plan 数据
        refreshPlanData()
      }
      break
    }
    case 'tool_call': {
      // eslint-disable-next-line no-console
      console.log('[plan-ws] tool_call:', ev.tool_name, ev.tool_args)
      break
    }
    case 'tool_result': {
      // eslint-disable-next-line no-console
      console.log('[plan-ws] tool_result:', ev.tool_name, ev.tool_output)
      break
    }
    case 'error': {
      isTyping.value = false
      streamingAiIdx.value = -1
      conversation.value.push({
        role: 'ai',
        text: `⚠ 出现错误：${ev.message}`,
      })
      scrollMessages()
      break
    }
  }
}

/* ── Load plan from backend ──────────────────────── */
async function loadPlan(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const { data: plans } = await listPlans(currentSubject.code)
    allPlans.value = plans

    if (plans.length === 0) {
      conversation.value = [
        {
          role: 'ai',
          text: `「${courseName.value}」暂无学习计划。请先在"我的课程"完成用户画像，画像完成后系统会自动为每个知识点 × 5 个步骤（看书 / 视频 / 刷题 / 对话 / 章节测验）创建计划。`,
        },
      ]
    } else {
      conversation.value = [
        {
          role: 'ai',
          text: `已为「${courseName.value}」加载 ${planGroups.value.length} 个知识节点、共 ${totalSteps.value} 个学习步骤（已完成 ${doneSteps.value} / 跳过 ${skippedSteps.value} / 待执行 ${pendingSteps.value}）。你可以针对单个步骤或选中多个步骤后让 AI 帮你调整。`,
        },
      ]
    }

    await connectPlanConversation()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '加载计划失败'
    conversation.value = [
      { role: 'ai', text: '加载计划时出错，请刷新页面重试。' },
    ]
  } finally {
    loading.value = false
    scrollMessages()
  }
}

/* ── Connect plan conversation WS ────────────────── */
async function connectPlanConversation(): Promise<void> {
  const subjectId = currentSubjectId.value
  if (!subjectId) {
    wsStatus.value = 'idle'
    return
  }

  try {
    const { data: convs } = await listConversations({
      agent: 'plan',
      subject: subjectId,
    })

    let convId: number | null = null
    if (convs.length > 0) {
      convId = convs[0]!.id
    } else {
      const { data: newConv } = await createConversation({
        subject_id: subjectId,
        title: `${courseName.value} 计划对话`,
        agent: 'plan',
      })
      convId = newConv.id
    }

    planConvId.value = convId
    wsStatus.value = 'connecting'
    await ws.connect(convId)
    wsStatus.value = 'open'
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[plan] connect WS failed:', err)
    wsStatus.value = 'error'
  }
}

/* ── Refresh plan data after AI modifications ────── */
async function refreshPlanData(): Promise<void> {
  try {
    const { data: plans } = await listPlans(currentSubject.code)
    allPlans.value = plans
  } catch {
    // 静默失败
  }
}

/* ── Step action: skip ────────────────── */
async function skipStep(plan: LearningPlan): Promise<void> {
  if (plan.state === 'skipped' || plan.state === 'success') return
  try {
    const { data: updated } = await skipPlan(plan.id, {})
    const idx = allPlans.value.findIndex(p => p.id === plan.id)
    if (idx >= 0) allPlans.value[idx] = updated
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[plan] skipStep failed:', err)
  }
}

/* ── Scroll messages to bottom ───────────────────── */
function scrollMessages(): void {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

/* ── Auto-resize textarea ────────────────────────── */
function onInput(): void {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

/* ── Send message ────────────────────────────────── */
function sendMessage(): void {
  const text = inputText.value.trim()
  if (!text) return

  // meta：仅携带选中的 plan_ids 供后端判断编辑模式；
  // plan 详情由 agent 通过 get_plan_detail 工具按需查询。
  const meta: Record<string, unknown> = {}
  let contentToSend = text

  if (selectedPlans.value.length > 0) {
    meta.selected_plan_ids = selectedPlans.value.map(p => p.id)
    // 将选中的 plan 以 #plan_id 形式拼入 content，供 agent 识别并调用工具查询
    const planRefs = selectedPlans.value.map(p => `#${p.id}`).join(' ')
    contentToSend = `${text}\n\n关联计划: ${planRefs}`
  }

  const displayText = selectedPlans.value.length > 0
    ? `【选中 ${selectedPlans.value.length} 个步骤：${selectedPlans.value.map(p => `${p.node_name}·${p.memory?.step_label ?? ''} #${p.id}`).join('、')}】\n${text}`
    : text
  conversation.value.push({ role: 'user', text: displayText })

  inputText.value = ''
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  clearSelection()
  scrollMessages()

  if (ws.status.value === 'open' && planConvId.value) {
    isTyping.value = true
    ws.send({ type: 'message', content: contentToSend, meta })
  } else {
    isTyping.value = true
    setTimeout(() => {
      isTyping.value = false
      conversation.value.push({
        role: 'ai',
        text: `当前 AI 助手未连接后端。已选中 ${selectedPlans.value.length} 个步骤，进度：${doneSteps.value}/${totalSteps.value}（${progress.value}%）。`,
      })
      scrollMessages()
    }, 1000)
  }
}

/* ── Quick actions ───────────────────────────────── */
function askAI(): void {
  inputText.value = '请根据我当前的知识点掌握度，帮我整体优化这份学习计划'
  nextTick(() => inputRef.value?.focus())
  sendMessage()
}

/* ── Plan suggestions (preview mode) ────────────── */
interface PlanSuggestion {
  key: string
  label: string
  icon: string
  prompt: string
}

const PLAN_SUGGESTIONS: PlanSuggestion[] = [
  {
    key: 'weak-first',
    label: '薄弱知识点优先',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 1v8M3 11v2M7 1v5M7 8v5M11 1v2M11 5v8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="3" cy="10" r="1.5" fill="currentColor"/><circle cx="7" cy="7" r="1.5" fill="currentColor"/><circle cx="11" cy="4" r="1.5" fill="currentColor"/></svg>',
    prompt: '请根据最新的知识点掌握度，把掌握度最低的节点调整到学习计划的前面',
  },
  {
    key: 'skip-mastered',
    label: '跳过已掌握节点',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 7l3 3 7-7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    prompt: '请把掌握度已经达到 80 以上的节点标记为已完成或跳过',
  },
  {
    key: 'difficulty',
    label: '调整难度',
    icon: '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1v6M7 11v2M1 7h6M11 7h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="7" r="2.5" stroke="currentColor" stroke-width="1.5"/></svg>',
    prompt: '请根据我的整体水平，重新评估并调整学习计划的难度',
  },
]

function sendSuggestion(suggestion: PlanSuggestion): void {
  const meta: Record<string, unknown> = {
    preview: true,
    scene: 'plan_suggestion',
  }
  let contentToSend = suggestion.prompt
  if (selectedPlans.value.length > 0) {
    meta.selected_plan_ids = selectedPlans.value.map(p => p.id)
    const planRefs = selectedPlans.value.map(p => `#${p.id}`).join(' ')
    contentToSend = `${suggestion.prompt}\n\n关联计划: ${planRefs}`
  }

  conversation.value.push({ role: 'user', text: suggestion.label })

  if (ws.status.value === 'open' && planConvId.value) {
    isTyping.value = true
    ws.send({ type: 'message', content: contentToSend, meta })
  } else {
    isTyping.value = true
    setTimeout(() => {
      isTyping.value = false
      conversation.value.push({
        role: 'ai',
        text: '当前 AI 助手未连接后端，请确保后端服务运行中。',
      })
      scrollMessages()
    }, 1000)
  }
}

/* ── Accept/Reject AI suggestions ───────────────── */
async function applySuggestions(): Promise<void> {
  if (suggestedPlans.value.length === 0) return
  if (ws.status.value === 'open' && planConvId.value) {
    // 让 AI 真正应用这些变更
    isTyping.value = true
    ws.send({
      type: 'message',
      content: '请应用以上建议',
      meta: {
        apply: true,
        suggested_plans: suggestedPlans.value,
      },
    })
  } else {
    conversation.value.push({
      role: 'ai',
      text: '⚠ 当前 AI 助手未连接后端，无法应用建议。',
    })
  }
  suggestedPlans.value = []
  scrollMessages()
}

function dismissSuggestions(): void {
  suggestedPlans.value = []
  conversation.value.push({
    role: 'ai',
    text: '已忽略本次建议。',
  })
  scrollMessages()
}

/* ── Watch subject change → reload plan ──────────── */
watch(() => currentSubject.code, () => {
  ws.close()
  planConvId.value = null
  conversation.value = []
  streamingAiIdx.value = -1
  selectedPlanIds.value = new Set()
  suggestedPlans.value = []
  loadPlan()
})

onMounted(() => {
  loadPlan()
})
</script>

<template>
  <div class="plan-schedule">
    <!-- Loading -->
    <div v-if="loading" class="plan-loading">
      <div class="loading-spinner"></div>
      <span>加载计划中...</span>
    </div>

    <!-- Two-column layout -->
    <div v-else class="plan-body">
      <!-- Left: Kanban board -->
      <section class="plan-panel">
        <div class="detail-header">
          <div class="detail-header-top">
            <h2 class="detail-title">{{ courseName }} 学习路径</h2>
            <div class="detail-actions">
              <button class="btn-action primary" @click="askAI()">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 2v4l3 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5"/></svg>
                让 AI 优化计划
              </button>
            </div>
          </div>
          <div class="detail-meta">
            <div class="detail-meta-item">
              <span class="status-pill active">进行中</span>
            </div>
            <div class="detail-meta-item">完成 <strong>{{ doneSteps }}</strong> / {{ totalSteps }}</div>
            <div class="detail-meta-item">跳过 <strong>{{ skippedSteps }}</strong></div>
            <div class="detail-meta-item">待执行 <strong>{{ pendingSteps }}</strong></div>
            <div class="detail-meta-item">进度 <strong>{{ progress }}%</strong></div>
          </div>
          <div class="progress-bar">
            <div class="progress-bar-fill" :style="{ width: progress + '%' }"></div>
          </div>
        </div>

        <!-- Kanban board -->
        <div class="kanban-board">
          <div v-if="weekColumns.length === 0" class="empty-state">
            <p>暂无学习计划。请先完成用户画像。</p>
          </div>
          <div v-else class="kanban-columns">
            <div
              v-for="col in weekColumns"
              :key="col.key"
              class="kanban-col"
              :class="{ 'is-current': col.isCurrent, 'is-past': col.isPast }"
            >
              <!-- Column header -->
              <div class="kanban-col-header">
                <span v-if="col.isCurrent" class="kanban-week-tag current">本周</span>
                <span v-else-if="col.isPast" class="kanban-week-tag past">已过</span>
                <span class="kanban-col-label">{{ col.label }}</span>
                <span class="kanban-col-count">{{ col.doneCount }}/{{ col.totalCount }}</span>
              </div>
              <div class="kanban-col-progress">
                <div
                  class="kanban-col-progress-fill"
                  :style="{ width: (col.totalCount ? Math.round(col.doneCount / col.totalCount * 100) : 0) + '%' }"
                ></div>
              </div>

              <!-- Cards -->
              <div class="kanban-cards">
                <div
                  v-for="step in col.plans"
                  :key="step.id"
                  class="kanban-card"
                  :class="['state-' + step.state, { 'is-selected': selectedPlanIds.has(step.id) }]"
                >
                  <div class="kanban-card-top">
                    <div
                      class="step-check"
                      :class="{ checked: selectedPlanIds.has(step.id) }"
                      @click="toggleSelectPlan(step.id)"
                      :title="selectedPlanIds.has(step.id) ? '取消选中' : '选中加入对话'"
                    >
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2.5 6l2.5 2.5 4.5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </div>
                    <span
                      v-if="step.memory && STEP_TYPE_CONFIG[step.memory.step_type ?? '']"
                      class="type-badge"
                      :class="'type-' + (step.memory.step_type ?? '')"
                      v-html="STEP_TYPE_CONFIG[step.memory.step_type ?? '']!.icon"
                    ></span>
                    <span :class="stateClass(step.state)">{{ STATE_LABEL[step.state] ?? step.state }}</span>
                  </div>
                  <div class="kanban-card-node">{{ step.node_name }}</div>
                  <div class="kanban-card-title">{{ step.memory?.step_label ?? step.action_type }}</div>
                  <div v-if="step.memory?.step_desc" class="kanban-card-desc">{{ step.memory.step_desc }}</div>
                  <div class="kanban-card-meta">
                    <span class="kanban-meta-item">{{ step.expected_minutes }}min</span>
                    <span v-if="step.difficulty" class="kanban-meta-item">难度{{ step.difficulty }}</span>
                  </div>
                  <div v-if="step.memory && STEP_ROUTE[step.memory.step_type ?? ''] && step.state !== 'success' && step.state !== 'skipped'" class="kanban-card-actions">
                    <button
                      class="step-btn primary"
                      :disabled="generatingQuizForPlanId === step.id"
                      @click="startStep(step)"
                    >
                      <span v-if="generatingQuizForPlanId === step.id" class="xp-spinner" />
                      {{ generatingQuizForPlanId === step.id ? '出题中…' : '去执行' }}
                    </button>
                    <button v-if="step.state === 'pending'" class="step-btn ghost" @click="skipStep(step)">跳过</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Right: AI chat -->
      <aside class="ai-panel">
        <div class="ai-panel-header">
          <div class="ai-panel-dot" :class="{ 'is-offline': wsStatus !== 'open', 'is-connecting': wsStatus === 'connecting' }"></div>
          <span class="ai-panel-title">AI 规划助手</span>
          <span class="ai-panel-badge" :class="'is-' + wsStatus">{{ wsStatus === 'open' ? '在线' : wsStatus === 'connecting' ? '连接中' : '离线' }}</span>
        </div>

        <div class="ai-panel-guide">
          <p class="guide-text">
            <strong>如何使用 AI 规划助手？</strong><br>
            直接在下方输入指令，可以针对选中步骤或整体计划进行调整：
          </p>
          <ul class="guide-list">
            <li><span class="guide-chip">整体</span>「重新调整学习顺序」「把难度降低一档」</li>
            <li><span class="guide-chip">单步</span>先勾选卡片左上角方框选中，再「把这步改为视频」</li>
            <li><span class="guide-chip">批量</span>「把今天截止的步骤延后」</li>
          </ul>
        </div>

        <!-- 3 个快捷建议按钮 -->
        <div v-if="allPlans.length > 0 && suggestedPlans.length === 0" class="suggestion-bar">
          <div class="suggestion-bar-label">智能建议</div>
          <div class="suggestion-buttons">
            <button
              v-for="s in PLAN_SUGGESTIONS"
              :key="s.key"
              class="suggestion-btn"
              :disabled="isTyping"
              @click="sendSuggestion(s)"
            >
              <span class="suggestion-btn-icon" v-html="s.icon"></span>
              <span class="suggestion-btn-label">{{ s.label }}</span>
            </button>
          </div>
        </div>

        <!-- 建议预览面板 -->
        <div v-if="suggestedPlans.length > 0" class="suggestion-preview">
          <div class="suggestion-preview-header">
            <span class="suggestion-preview-title">调整方案预览 ({{ suggestedPlans.length }} 项)</span>
          </div>
          <div class="suggestion-diff-list">
            <div
              v-for="(s, i) in suggestedPlans.slice(0, 12)"
              :key="i"
              class="suggestion-diff-item"
            >
              <span class="diff-icon">·</span>
              <span class="diff-name">{{ s.node_name }} · {{ s.step_label ?? s.step_type }}</span>
              <span class="diff-detail">{{ s.state ?? s.plan_difficulty }}</span>
            </div>
            <div v-if="suggestedPlans.length > 12" class="suggestion-diff-item diff-more">
              还有 {{ suggestedPlans.length - 12 }} 项…
            </div>
          </div>
          <div class="suggestion-preview-actions">
            <button class="btn-apply" @click="applySuggestions">应用方案</button>
            <button class="btn-dismiss" @click="dismissSuggestions">忽略</button>
          </div>
        </div>

        <div class="ai-messages" ref="messagesRef">
          <template v-for="(m, idx) in conversation" :key="idx">
            <div class="msg" :class="m.role">
              <div class="msg-avatar">{{ m.role === 'user' ? '我' : 'AI' }}</div>
              <div class="msg-bubble">
                <MarkdownContent :text="m.text" />
              </div>
            </div>
          </template>

          <!-- Typing indicator -->
          <div v-if="isTyping" class="msg ai">
            <div class="msg-avatar">AI</div>
            <div class="msg-bubble">
              <span class="typing">●</span>
            </div>
          </div>
        </div>

        <!-- Selected plans bar -->
        <div v-if="selectedPlans.length > 0" class="selected-nodes-bar">
          <div class="selected-nodes-chips">
            <span
              v-for="p in selectedPlans"
              :key="p.id"
              class="selected-plan-chip"
              @click="toggleSelectPlan(p.id)"
            >
              {{ p.node_name }}·{{ p.memory?.step_label ?? p.action_type }}
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
            </span>
          </div>
          <button class="selected-nodes-clear" @click="clearSelection()">清空</button>
        </div>

        <div class="ai-input-area">
          <textarea
            class="ai-input"
            ref="inputRef"
            v-model="inputText"
            :placeholder="selectedPlans.length > 0 ? '针对选中的步骤，告诉 AI 你想怎么改…' : '输入修改指令，例如：「把第3个节点的难度调低」'"
            rows="1"
            @input="onInput"
            @keydown="onKeydown"
          ></textarea>
          <button
            class="btn-send"
            :disabled="!inputText.trim()"
            @click="sendMessage()"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M3 9l12-5-5 12-2-5-5-2z" fill="currentColor"/></svg>
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.plan-schedule {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 68px);
  min-height: 0;
  overflow: hidden;
}

/* ── Loading ─────────────────────────────────────── */
.plan-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex: 1;
  color: var(--x-body-mid);
  font-size: 14px;
}
.loading-spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--x-hairline);
  border-top-color: var(--x-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.xp-spinner {
  width: 12px; height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: var(--x-on-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
  vertical-align: -1px;
}

/* ── Main two-column layout ──────────────────────── */
.plan-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Left: plan detail ───────────────────────────── */
.plan-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.detail-header {
  padding: 24px 32px 20px;
  background: var(--x-canvas);
  flex-shrink: 0;
}
.detail-header-top {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 8px;
}
.detail-title {
  font: 700 22px/1.3 var(--x-font-display);
  letter-spacing: -0.025em;
  flex: 1;
  color: var(--x-ink);
}
.detail-desc {
  font: 13px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
  margin-bottom: 14px;
}
.detail-actions {
  display: flex;
  gap: 8px;
}
.btn-action {
  height: 36px;
  padding: 0 20px;
  border-radius: var(--x-rounded-pill);
  font: 500 13px/1 var(--x-font-display);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.12s, color 0.12s, transform 0.1s;
  white-space: nowrap;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-body);
}
.btn-action:hover {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}
.btn-action:active { transform: scale(0.98); }
.btn-action.primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.btn-action.primary:hover {
  background: var(--x-primary-hover);
  color: var(--x-on-primary);
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 20px;
  font: 13px/1 var(--x-font-display);
  color: var(--x-body-mid);
  flex-wrap: wrap;
}
.detail-meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.detail-meta-item strong {
  color: var(--x-ink);
  font-weight: 600;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font: 600 11px/1 var(--x-font-display);
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
  letter-spacing: 0.02em;
}
.status-pill::before {
  content: '';
  width: 6px; height: 6px;
  border-radius: 50%;
}
.status-pill.active {
  background: var(--x-success-soft);
  color: oklch(38% 0.12 155);
}
.status-pill.active::before { background: var(--x-success); }

.progress-bar {
  height: 4px;
  background: var(--x-canvas-mid);
  border-radius: var(--x-rounded-pill);
  overflow: hidden;
  margin-top: 14px;
}
.progress-bar-fill {
  height: 100%;
  background: var(--x-primary);
  border-radius: var(--x-rounded-pill);
  transition: width 0.4s ease;
}

.detail-types {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  flex-wrap: wrap;
}
.detail-types-label {
  font: 500 12px/1 var(--x-font-display);
  color: var(--x-body-mid);
  margin-right: 2px;
}
.type-count {
  font: 500 12px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  margin-right: 4px;
}

/* ── Type badges (复用) ──────────────────────────── */
.type-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font: 500 11.5px/1 var(--x-font-display);
  padding: 3px 10px;
  border-radius: var(--x-rounded-sm);
  letter-spacing: 0.01em;
  flex-shrink: 0;
}
.type-badge :deep(svg) { flex-shrink: 0; }
.type-badge.type-reading {
  background: oklch(95% 0.04 280);
  color: oklch(42% 0.12 280);
}
.type-badge.type-video {
  background: oklch(95% 0.04 25);
  color: oklch(42% 0.16 25);
}
.type-badge.type-quiz {
  background: oklch(95% 0.04 255);
  color: oklch(42% 0.14 255);
}
.type-badge.type-chapter_quiz {
  background: oklch(95% 0.04 320);
  color: oklch(42% 0.12 320);
}
.type-badge.type-exam {
  background: oklch(95% 0.04 200);
  color: oklch(42% 0.12 200);
}
.type-badge.type-qa {
  background: oklch(95% 0.04 155);
  color: oklch(38% 0.12 155);
}

/* ── Plan group (节点) ───────────────────────────── */
.detail-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}
.detail-body::-webkit-scrollbar { width: 5px; }
.detail-body::-webkit-scrollbar-thumb { background: var(--x-hairline); border-radius: 4px; }

.empty-state {
  padding: 60px 20px;
  text-align: center;
  color: var(--x-body-mid);
  font-size: 14px;
}

/* ── Kanban board ────────────────────────────────── */
.kanban-board {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.kanban-columns {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  overflow-x: auto;
  overflow-y: hidden;
  align-items: flex-start;
}
.kanban-columns::-webkit-scrollbar { height: 6px; }
.kanban-columns::-webkit-scrollbar-thumb { background: var(--x-hairline); border-radius: 4px; }

.kanban-col {
  flex-shrink: 0;
  width: 280px;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas-soft);
  overflow: hidden;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.kanban-col:hover {
  box-shadow: var(--x-shadow-card-hover);
}
.kanban-col.is-current {
  background: var(--x-canvas-tint);
}
.kanban-col.is-past {
  opacity: 0.7;
}

.kanban-col-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 8px;
  flex-shrink: 0;
}
.kanban-week-tag {
  font: 600 10px/1 var(--x-font-display);
  padding: 3px 8px;
  border-radius: var(--x-rounded-pill);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.kanban-week-tag.current {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.kanban-week-tag.past {
  background: var(--x-hairline);
  color: var(--x-body-mid);
}
.kanban-col-label {
  font: 600 13px/1.3 var(--x-font-display);
  color: var(--x-ink);
  flex: 1;
}
.kanban-col-count {
  font: 600 12px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  background: var(--x-canvas);
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
}

.kanban-col-progress {
  height: 3px;
  background: var(--x-hairline);
  margin: 0 14px 10px;
  border-radius: 2px;
  flex-shrink: 0;
  overflow: hidden;
}
.kanban-col-progress-fill {
  height: 100%;
  background: var(--x-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.kanban-cards {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.kanban-cards::-webkit-scrollbar { width: 4px; }
.kanban-cards::-webkit-scrollbar-thumb { background: var(--x-hairline); border-radius: 4px; }

.kanban-card {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.kanban-card:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.kanban-card.is-selected {
  box-shadow: var(--x-shadow-card), 0 0 0 2px var(--x-primary);
}
.kanban-card.state-success { opacity: 0.6; }
.kanban-card.state-success .kanban-card-title { text-decoration: line-through; }
.kanban-card.state-skipped { opacity: 0.45; }
.kanban-card.state-skipped .kanban-card-title { text-decoration: line-through; }

.kanban-card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.kanban-card-node {
  font: 500 11px/1.3 var(--x-font-display);
  color: var(--x-body-mid);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.kanban-card-title {
  font: 600 13px/1.4 var(--x-font-display);
  color: var(--x-ink);
}
.kanban-card-desc {
  font: 12px/1.4 var(--x-font-display);
  color: var(--x-body-mid);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.kanban-card-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.kanban-meta-item {
  font: 500 10px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  background: var(--x-canvas-soft);
  padding: 3px 8px;
  border-radius: var(--x-rounded-sm);
}
.kanban-card-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.plan-group {
  margin-bottom: 22px;
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  overflow: hidden;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.plan-group:hover {
  box-shadow: var(--x-shadow-card-hover);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
  background: var(--x-canvas-soft);
}
.group-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.group-index {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
  font: 600 11px/22px var(--x-font-display);
  text-align: center;
  flex-shrink: 0;
}
.group-name {
  font: 600 15px/1.2 var(--x-font-display);
  color: var(--x-ink);
  flex-shrink: 0;
}
.group-tag {
  font: 500 11px/1 var(--x-font-mono);
  padding: 2px 8px;
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
  flex-shrink: 0;
}
.group-difficulty {
  font: 500 11px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  flex-shrink: 0;
}
.group-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.group-progress-text {
  font: 500 12px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  white-space: nowrap;
}
.group-progress-bar {
  width: 80px;
  height: 3px;
  background: var(--x-canvas-mid);
  border-radius: var(--x-rounded-pill);
  overflow: hidden;
}
.group-progress-bar-fill {
  height: 100%;
  background: var(--x-success);
  border-radius: var(--x-rounded-pill);
  transition: width 0.3s ease;
}

/* ── Step list ───────────────────────────────────── */
.step-list {
  display: flex;
  flex-direction: column;
}

.step-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  transition: background 0.15s;
  position: relative;
}
.step-card:last-child { }
.step-card:hover { background: var(--x-canvas-soft); }
.step-card.is-selected {
  background: var(--x-primary-soft);
  box-shadow: inset 3px 0 0 var(--x-primary);
}

/* 状态色 */
.step-card.state-success { opacity: 0.6; }
.step-card.state-success .step-title { text-decoration: line-through; }
.step-card.state-skipped { opacity: 0.5; }
.step-card.state-skipped .step-title { text-decoration: line-through; }

.step-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding-top: 1px;
}
.step-check {
  width: 20px; height: 20px;
  border: 2px solid var(--x-hairline-strong);
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.15s;
  flex-shrink: 0;
}
.step-check:hover { border-color: var(--x-primary); }
.step-check.checked {
  background: var(--x-primary);
  border-color: var(--x-primary);
}
.step-check svg { display: none; }
.step-check.checked svg { display: block; }
.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-card-body {
  flex: 1;
  min-width: 0;
}
.step-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.step-title {
  font: 600 13.5px/1.3 var(--x-font-display);
  color: var(--x-ink);
}
.step-desc {
  font: 12.5px/1.45 var(--x-font-display);
  color: var(--x-body-mid);
  margin-bottom: 6px;
}
.step-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font: 500 11.5px/1 var(--x-font-mono);
  color: var(--x-body-mid);
  flex-wrap: wrap;
}
.step-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.step-meta-item:not(:last-child)::after {
  content: '·';
  margin-left: 10px;
  color: var(--x-hairline-strong);
}

/* 状态徽章 */
.step-state {
  font: 600 10px/1 var(--x-font-display);
  padding: 2px 8px;
  border-radius: var(--x-rounded-pill);
  letter-spacing: 0.02em;
  white-space: nowrap;
  flex-shrink: 0;
}
.step-state-pending {
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
}
.step-state-running {
  background: oklch(95% 0.06 250);
  color: oklch(40% 0.14 250);
}
.step-state-success {
  background: var(--x-success-soft);
  color: oklch(38% 0.12 155);
}
.step-state-failed {
  background: oklch(95% 0.05 25);
  color: oklch(40% 0.18 25);
}
.step-state-skipped {
  background: oklch(95% 0.03 60);
  color: oklch(45% 0.05 60);
}

/* ── Step right actions ──────────────────────────── */
.step-card-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding-top: 1px;
}
.step-btn {
  height: 30px;
  padding: 0 14px;
  border-radius: var(--x-rounded-pill);
  font: 500 12px/1 var(--x-font-display);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: background 0.12s, color 0.12s, transform 0.1s;
  white-space: nowrap;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-body);
}
.step-btn:hover {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}
.step-btn:active { transform: scale(0.98); }
.step-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.step-btn.primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.step-btn.primary:hover { background: var(--x-primary-hover); }
.step-btn.ghost {
  background: transparent;
}

/* ── Right: AI chat panel ────────────────────────── */
.ai-panel {
  width: 440px;
  min-width: 440px;
  background: var(--x-canvas);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--x-shadow-card);
}
.ai-panel-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 24px;
  background: var(--x-canvas);
  position: relative;
}
.ai-panel-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--x-success);
  animation: pulse 2s infinite;
  position: absolute;
  left: 24px;
}
.ai-panel-dot.is-offline {
  background: var(--x-danger, oklch(60% 0.2 25));
  animation: none;
}
.ai-panel-dot.is-connecting {
  background: var(--x-warning, oklch(70% 0.15 80));
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.ai-panel-title {
  font: 600 20px/1 var(--x-font-display);
  color: var(--x-ink);
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}
.ai-panel-badge {
  font: 500 11px/1 var(--x-font-mono);
  letter-spacing: 0.4px;
  color: var(--x-body-mid);
  padding: 4px 10px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-pill);
  margin-left: auto;
}
.ai-panel-badge.is-open {
  color: var(--x-success);
  background: var(--x-success-soft);
}
.ai-panel-badge.is-connecting {
  color: var(--x-accent-amber-deep);
  background: var(--x-amber-alpha-08);
}
.ai-panel-badge.is-closed,
.ai-panel-badge.is-error {
  color: var(--x-error);
  background: var(--x-error-soft);
}

.ai-panel-guide {
  padding: 12px 20px;
  background: var(--x-canvas-soft);
  flex-shrink: 0;
}
.guide-text {
  font: 12px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
  margin: 0 0 6px;
}
.guide-text strong {
  color: var(--x-ink);
}
.guide-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.guide-list li {
  font: 12px/1.4 var(--x-font-display);
  color: var(--x-body-mid);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.guide-chip {
  display: inline-flex;
  align-items: center;
  font: 600 11px/1 var(--x-font-display);
  padding: 2px 8px;
  border-radius: var(--x-rounded-sm);
  background: var(--x-ai-soft);
  color: var(--x-ai);
  flex-shrink: 0;
  white-space: nowrap;
}

.suggestion-bar {
  padding: 12px 20px;
  flex-shrink: 0;
}
.suggestion-bar-label {
  font: 600 11px/1 var(--x-font-display);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--x-body-mid);
  margin-bottom: 8px;
}
.suggestion-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.suggestion-btn {
  flex: 1;
  min-width: 110px;
  height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: var(--x-rounded-pill);
  background: var(--x-canvas-soft);
  color: var(--x-body);
  font: 500 12px/1 var(--x-font-display);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.12s, color 0.12s, transform 0.1s;
}
.suggestion-btn:hover {
  color: var(--x-primary);
  background: var(--x-primary-soft);
}
.suggestion-btn:active { transform: scale(0.98); }
.suggestion-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.suggestion-btn-icon { display: inline-flex; }

.suggestion-preview {
  padding: 12px 20px;
  background: var(--x-canvas-soft);
  flex-shrink: 0;
  max-height: 200px;
  overflow-y: auto;
}
.suggestion-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.suggestion-preview-title {
  font: 600 12px/1 var(--x-font-display);
  color: var(--x-ink);
}
.suggestion-diff-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 8px;
}
.suggestion-diff-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font: 12px/1.4 var(--x-font-display);
  color: var(--x-body-mid);
}
.suggestion-diff-item.diff-more {
  font-style: italic;
  color: var(--x-body-mid);
  opacity: 0.7;
}
.diff-icon {
  width: 12px;
  text-align: center;
  color: var(--x-body-mid);
  flex-shrink: 0;
}
.diff-name {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.diff-detail {
  font: 500 11px/1 var(--x-font-mono);
  color: var(--x-primary);
  flex-shrink: 0;
}
.suggestion-preview-actions {
  display: flex;
  gap: 6px;
}
.btn-apply {
  flex: 1;
  height: 34px;
  border: none;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-radius: var(--x-rounded-pill);
  font: 500 12px/1 var(--x-font-display);
  cursor: pointer;
  transition: background 0.12s, transform 0.1s;
}
.btn-apply:hover { background: var(--x-primary-hover); }
.btn-apply:active { transform: scale(0.98); }
.btn-dismiss {
  height: 34px;
  padding: 0 16px;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-body);
  border-radius: var(--x-rounded-pill);
  font: 500 12px/1 var(--x-font-display);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.btn-dismiss:hover {
  color: var(--x-primary);
  background: var(--x-primary-soft);
}

.ai-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 24px 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
}
.ai-messages::-webkit-scrollbar { width: 4px; }
.ai-messages::-webkit-scrollbar-thumb { background: var(--x-hairline); border-radius: 4px; }

.msg {
  display: flex;
  gap: 10px;
  max-width: 80%;
}
.msg.user { align-self: flex-end; flex-direction: row-reverse; }
.msg-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font: 600 10px/1 var(--x-font-display);
  flex-shrink: 0;
}
.msg.ai .msg-avatar {
  background: var(--x-canvas-mid);
  color: var(--x-primary);
}
.msg.user .msg-avatar {
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
}
.msg-bubble {
  padding: 10px 14px;
  border-radius: var(--x-rounded-md);
  font: 14px/1.5 var(--x-font-display);
  word-wrap: break-word;
  min-width: 60px;
}
.msg.ai .msg-bubble {
  background: var(--x-canvas);
  color: var(--x-ink);
  box-shadow: var(--x-shadow-card);
}
.msg.user .msg-bubble {
  background: var(--x-primary);
  color: var(--x-on-primary);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}
.msg-text { white-space: pre-wrap; }
.msg-bubble :deep(.x-md) { font-size: 13px; }
.msg.user .msg-bubble :deep(.x-md) { color: var(--x-on-primary); }
.msg.user .msg-bubble :deep(.x-md code) { background: rgba(255,255,255,0.2); color: var(--x-on-primary); }

.typing { display: inline-block; color: var(--x-primary); animation: x-typing 1s steps(2) infinite; margin-left: 2px; }
@keyframes x-typing {
  50% { opacity: 0.2; }
}

.selected-nodes-bar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 20px;
  background: var(--x-primary-soft);
  flex-shrink: 0;
}
.selected-nodes-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.selected-plan-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 500 11px/1 var(--x-font-display);
  padding: 4px 10px;
  border-radius: var(--x-rounded-pill);
  background: var(--x-primary-soft);
  color: var(--x-primary);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  white-space: nowrap;
}
.selected-plan-chip:hover {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.selected-plan-chip svg { flex-shrink: 0; opacity: 0.6; }
.selected-plan-chip:hover svg { opacity: 1; }
.selected-nodes-clear {
  border: none;
  background: transparent;
  color: var(--x-primary);
  font: 500 12px/1 var(--x-font-display);
  cursor: pointer;
  padding: 4px 0;
  margin-left: auto;
  flex-shrink: 0;
  margin-left: auto;
}
.selected-nodes-clear:hover { text-decoration: underline; }

.ai-input-area {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 14px 24px 32px;
  background: var(--x-canvas);
}
.ai-input {
  flex: 1;
  min-width: 0;
  resize: none;
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 14px 16px;
  font-family: var(--x-font-display);
  font-size: 14.5px;
  line-height: 1.55;
  color: var(--x-ink);
  outline: none;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease;
  min-height: 64px;
  max-height: 120px;
  border: none;
}
.ai-input:focus {
  box-shadow: var(--x-shadow-card-hover),
              0 0 0 3px oklch(52% 0.18 255 / 0.18);
}
.ai-input::placeholder { color: var(--x-body-mid); }

.btn-send {
  flex-shrink: 0;
  align-self: flex-end;
  height: 44px;
  padding: 0 18px;
  border: none;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-radius: var(--x-rounded-pill);
  font: 500 13px/1 var(--x-font-display);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.12s, transform 0.1s;
}
.btn-send:hover:not(:disabled) { background: var(--x-primary-hover); }
.btn-send:active:not(:disabled) { transform: scale(0.98); }
.btn-send:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
