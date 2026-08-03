<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRef, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import MarkdownContent from '@/components/MarkdownContent.vue'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { getSubjectDisplayName } from '@/api/subjects'
import { createConversation } from '@/api/conversations'
import http from '@/api/http'
import { ENDPOINTS } from '@/api/endpoints'
import {
  IconTimer,
  IconNotepad,
  IconCross,
  IconBulb,
  IconCheck,
  IconNode,
  IconArrow,
  IconHourglass,
} from '@/components/icons'
import {
  getQuizTask,
  pollQuizUntilDone,
  startPracticeAnalyze,
  pollPracticeUntilDone,
  fetchPracticeAnalyses,
  fetchQuizHistory,
  isChoice,
  isShortAnswer,
  markQuizAnswered,
} from '@/api/quiz'
import type {
  StructuredQuestion,
  PracticeResultPayload,
  QuizHistoryItem,
} from '@/api/quiz'
import { useActiveQuizFeed } from './useActiveQuizFeed'

const props = defineProps<{ taskId?: string }>()
const router = useRouter()
const route = useRoute()
const currentSubject = useCurrentSubjectStore()
const mySubjects = useMySubjectsStore()

// ── Plan 插队模式: 从 URL query 里读 plan, 注入 ActiveQueue ──
const planIdFromQuery = computed<number | null>(() => {
  const raw = route.query.plan
  if (raw == null) return null
  const n = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(n) && n > 0 ? n : null
})
const isPlanMode = computed(() => planIdFromQuery.value != null)

// 题目对应 Subject 的 code (这里是 Subject.name, 不是 MySubject.id)
const subjectNameRef = computed(() => currentSubject.code || '')

// 后端 active-queue 数据源 (替代 useQuizQueue)
const feed = useActiveQuizFeed({
  subjectName: subjectNameRef,
  planId: planIdFromQuery,
})

// ── 当前批的 task 信息 ──
const currentTaskId = ref<string>(props.taskId ?? '')
const currentDbId = ref<number>(0)

// ── 历史记录弹窗 ──
const showHistory = ref(false)
const historyList = ref<QuizHistoryItem[]>([])
const historyLoading = ref(false)

async function loadHistoryList(): Promise<void> {
  historyLoading.value = true
  try {
    const { data } = await fetchQuizHistory({ state: 'complete' })
    historyList.value = data
  } catch {
    // silent
  } finally {
    historyLoading.value = false
  }
}

// ── State machine ──
type Phase = 'loading' | 'answering' | 'reviewing' | 'done' | 'error'
const phase = ref<Phase>('loading')
const isReviewing = computed(() => phase.value === 'reviewing')
const errorMsg = ref('')

// ── Questions ──
const questions = ref<StructuredQuestion[]>([])
// 每题归属: 同维度数组, idx 对齐 questions
const questionQuizDbIds = ref<number[]>([])
const questionQuizTaskIds = ref<string[]>([])
// 该题在其所属 batch 内的 index (用于提交分析时传给后端)
const questionBatchIndex = ref<number[]>([])
const currentIdx = ref(0)
const currentQ = computed(() => questions.value[currentIdx.value] ?? null)

// 替换 questions.value 时同时维护归属 mapping (用于历史回放/单 batch 加载)
function setQuestionsWithBatchInfo(
  qs: StructuredQuestion[],
  dbId: number,
  taskId: string,
): void {
  questions.value = qs
  questionQuizDbIds.value = qs.map(() => dbId)
  questionQuizTaskIds.value = qs.map(() => taskId)
  // 单 batch: batch 内 idx 就是 0..len-1
  questionBatchIndex.value = qs.map((_, i) => i)
  // B12: 同步刷新 currentDbId, 防止 meta 数组默认值与 currentDbId 不一致
  if (dbId) currentDbId.value = dbId
  if (taskId) currentTaskId.value = taskId
}

// ── Answers ──
interface AnswerEntry {
  userAnswer: string
  // null = 后端尚未判分 / 短答题未 AI 评 (B8/B9)
  isCorrect: boolean | null
  analyzing: boolean
  analysis: PracticeResultPayload | null
  analyzeError: string | null
  hintsUsed: number
  hints: string[]
  hintLoading: boolean
}
const answers = ref<Record<number, AnswerEntry>>({})

const answeredCount = computed(
  () => Object.values(answers.value).filter((a) => !a.analyzing).length,
)
const correctCount = computed(
  () => Object.values(answers.value).filter((a) => a.isCorrect === true).length,
)
const pendingCount = computed(
  // 短答题提交后等 AI 判分期间, 算 pending (不算对也不算错)
  () => Object.values(answers.value).filter((a) => a.userAnswer && a.isCorrect === null && !a.analyzing).length,
)
const correctPct = computed(() => {
  if (questions.value.length === 0) return 0
  return Math.round((correctCount.value / questions.value.length) * 100)
})
const allDone = computed(
  () => questions.value.length > 0 && answeredCount.value === questions.value.length,
)
const totalHintsUsed = computed(
  () => Object.values(answers.value).reduce((sum, a) => sum + a.hintsUsed, 0),
)

// ── 解析面板三态渲染 (B9: isCorrect 可能是 null, 必须三态化) ──
type VerdictState = 'correct' | 'wrong' | 'pending'

function verdictState(entry: AnswerEntry | undefined): VerdictState {
  if (!entry?.userAnswer) return 'pending'
  if (entry.isCorrect === true) return 'correct'
  if (entry.isCorrect === false) return 'wrong'
  return 'pending'
}

function verdictLabel(s: VerdictState): string {
  return s === 'correct' ? '回答正确' : s === 'wrong' ? '回答错误' : '等待判分'
}

function verdictBadgeClass(s: VerdictState): string {
  return s === 'correct'
    ? 'x-phase-badge--correct'
    : s === 'wrong'
      ? 'x-phase-badge--wrong'
      : 'x-phase-badge--pre'
}

const currentVerdict = computed<VerdictState>(() => verdictState(answers.value[currentIdx.value]))

// ── ActiveQueue: 把后端返回的 ready quizzes 扁平化成本地 questions ──
// ready items 按 (source asc, created_at asc) 顺序拼好; 同时为每道题记录
// 它所在 quiz 的 db id + batch 内 idx (提交判分时使用).
const flattened = computed(() => {
  const out: StructuredQuestion[] = []
  const dbIds: number[] = []
  const taskIds: string[] = []
  const batchIdx: number[] = []
  for (const q of feed.ready.value) {
    if (!q.questions) continue
    for (let i = 0; i < q.questions.length; i++) {
      // 跳过 batch 内已答完的题
      const progress = q.item_progress?.[String(i)]
      if (progress?.answered) continue
      const item = q.questions[i]
      if (!item) continue   // noUncheckedIndexedAccess: 数组访问可能 undefined
      out.push(item)
      dbIds.push(q.id)
      taskIds.push(q.task_id)
      batchIdx.push(i)
    }
  }
  return { out, dbIds, taskIds, batchIdx }
})

// 把后端拉来的 quiz 数据合并到本地 (不带 mutation, 仅 ref 同步)
function syncQuestionsFromFeed(): void {
  const { out, dbIds, taskIds, batchIdx } = flattened.value
  // 检查 dbIds 是否改变; 如果变了说明后端补题了, 全量刷新
  const sig = dbIds.join(',') + '|' + out.length
  if (sig === lastFeedSig.value) return
  lastFeedSig.value = sig
  questions.value = out
  questionQuizDbIds.value = dbIds
  questionQuizTaskIds.value = taskIds
  questionBatchIndex.value = batchIdx
  if (out.length > 0 && currentIdx.value >= out.length) {
    currentIdx.value = Math.max(0, out.length - 1)
  }
  // B10: 计时器只在 loading → answering 切换那一刻启动一次, 后续 watch 不会重启
  if (out.length > 0 && phase.value === 'loading') {
    enterAnswering()
  }
}
const lastFeedSig = ref('')

// 集中处理 "进入答题态" 的副作用, 避免多处 watch 重复启动计时器
function enterAnswering(): void {
  phase.value = 'answering'
  startTime.value = Date.now()
  startTimer()
}

// 后端 feed 更新时同步到 questions
watch(
  () => feed.ready.value,
  () => {
    syncQuestionsFromFeed()
  },
  { immediate: true, deep: true },
)

// 加载指定 task 的题目
async function loadQuestionsFor(taskId: string): Promise<void> {
  errorMsg.value = ''
  try {
    const { data } = await getQuizTask(taskId)
    if (data.state === 'complete' && data.questions) {
      currentDbId.value = data.id
      setQuestionsWithBatchInfo(data.questions, data.id, taskId)
      enterAnswering()
    } else if (data.state === 'error') {
      errorMsg.value = data.error_message ?? '生成失败'
      phase.value = 'error'
    } else {
      // 生成中 → 轮询
      const result = await pollQuizUntilDone(taskId, (state) => {
        errorMsg.value = state
      })
      if (result.ok) {
        // B7: polling 期间合并响应可能不带 id, 再 fetch 一次拿最新 dbId
        let dbId = currentDbId.value
        if (!dbId) {
          try {
            const { data: fresh } = await getQuizTask(taskId)
            dbId = fresh?.id ?? 0
          } catch { /* 留 0, 由后续 catch 兜底 */ }
        }
        currentDbId.value = dbId
        setQuestionsWithBatchInfo(result.questions, dbId, taskId)
        enterAnswering()
      } else {
        errorMsg.value = result.error
        phase.value = 'error'
      }
    }
  } catch {
    errorMsg.value = '加载失败，请检查网络'
    phase.value = 'error'
  }
}

// ── Timer ──
const startTime = ref(Date.now())
const elapsed = ref(0)
let timerHandle: ReturnType<typeof setInterval> | null = null

function formatTime(ms: number): string {
  const sec = Math.floor(ms / 1000)
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// ── Input state (for the current question) ──
const selectedOption = ref<string>('')
const shortAnswerText = ref('')

// Reset input when navigating between questions
watch(currentIdx, () => {
  const entry = answers.value[currentIdx.value]
  if (entry) {
    selectedOption.value = entry.userAnswer
    shortAnswerText.value = entry.userAnswer
  } else {
    selectedOption.value = ''
    shortAnswerText.value = ''
  }
})

// ── Load questions (for a given taskId, supports history replay) ──
async function loadQuestions(): Promise<void> {
  if (!props.taskId) return
  currentTaskId.value = props.taskId
  phase.value = 'loading'
  errorMsg.value = ''
  try {
    const { data } = await getQuizTask(props.taskId)
    if (data.state === 'complete' && data.questions) {
      currentDbId.value = data.id
      setQuestionsWithBatchInfo(data.questions, data.id, props.taskId)
      await tryLoadHistory(data.id)
    } else if (data.state === 'error') {
      errorMsg.value = data.error_message ?? '生成失败'
      phase.value = 'error'
    } else {
      // Still generating → poll
      const result = await pollQuizUntilDone(props.taskId, (state) => {
        errorMsg.value = state
      })
      if (result.ok) {
        // B7: polling 期间合并响应可能不带 id, 再 fetch 一次拿最新 dbId
        let dbId = data?.id ?? currentDbId.value
        if (!dbId) {
          try {
            const { data: fresh } = await getQuizTask(props.taskId)
            dbId = fresh?.id ?? 0
          } catch { /* 留 0, 兜底由 submitAnswer 阻断 */ }
        }
        currentDbId.value = dbId
        setQuestionsWithBatchInfo(result.questions, dbId, props.taskId)
        enterAnswering()
      } else {
        errorMsg.value = result.error
        phase.value = 'error'
      }
    }
  } catch {
    errorMsg.value = '加载失败，请检查网络'
    phase.value = 'error'
  }
}

async function tryLoadHistory(dbId: number): Promise<void> {
  try {
    const { data: analyses } = await fetchPracticeAnalyses({
      quiz_generation: String(dbId),
      state: 'complete',
    })
    if (analyses.length > 0) {
      for (const a of analyses) {
        const analysis = a.analysis as unknown as PracticeResultPayload | null
        // B5: 这里 a.question_index 是后端 batch 内 idx, 单 batch 模式下恰好 == currentIdx
        // 一旦未来支持多 batch 合并回放, 必须改成全局 idx, 否则 UI 错位
        answers.value[a.question_index] = {
          userAnswer: a.user_answer ?? '',
          // B9: 以分析返回的 is_correct 作为唯一可信源, 没有 analysis 就 null
          isCorrect: analysis?.result?.is_correct ?? null,
          analyzing: false,
          analysis,
          analyzeError: null,
          hintsUsed: 0,
          hints: [],
          hintLoading: false,
        }
      }
      phase.value = 'reviewing'
      return
    }
  } catch {
    // 历史解析加载失败 — 降级为重新答题
  }
  enterAnswering()
}

function startTimer(): void {
  if (timerHandle) clearInterval(timerHandle)
  timerHandle = setInterval(() => {
    elapsed.value = Date.now() - startTime.value
  }, 1000)
}

// 进入 ready 后从 loading 切到 answering
watch(
  () => questions.value.length,
  (n, prev) => {
    if (n > 0 && prev === 0 && phase.value === 'loading') {
      enterAnswering()
    }
  },
)

onMounted(async () => {
  if (props.taskId) {
    // 历史回放入口 - 不走 feed, 老路径
    await loadQuestions()
    return
  }
  // B3: 无限流模式重置上一次的 currentDbId / currentTaskId, 防止残值污染
  currentDbId.value = 0
  currentTaskId.value = ''
  phase.value = 'loading'
  errorMsg.value = isPlanMode.value ? 'AI 正在出计划相关题目…' : 'AI 正在出题…'
  // B11: 等 currentSubject 就绪后再起 feed (避免发空请求被 useActiveQuizFeed 静默丢弃)
  if (!currentSubject.code) {
    await Promise.race([
      new Promise<void>((r) => setTimeout(r, 2000)),
      new Promise<void>((r) => {
        const stop = watch(
          () => currentSubject.code,
          (v) => { if (v) { stop(); r() } },
          { immediate: true },
        )
      }),
    ])
  }
  // 后端会根据当前未答 pool 自动补题; 我们只需拉一次
  feed.start()
  // 阶段性 phase 切到 answering 由 syncQuestionsFromFeed 内部 watch + phase guard
  // 这里不再单独判断.
})
onBeforeUnmount(() => {
  if (timerHandle) clearInterval(timerHandle)
  // B16: 显式释放 feed, 配合 onScopeDispose 形成双保险
  feed.dispose()
})

// ── Helpers ──
function letterFor(idx: number): string {
  return String.fromCharCode('A'.charCodeAt(0) + idx)
}

function difficultyLabel(d: string): string {
  return d === 'easy' ? '简单' : d === 'hard' ? '困难' : '中等'
}

function difficultyClass(d: string): string {
  return d === 'easy' ? 'diff-easy' : d === 'hard' ? 'diff-hard' : 'diff-med'
}

// ── Navigation ──
function goPrev(): void {
  if (currentIdx.value > 0) currentIdx.value--
}

function goNext(): void {
  if (currentIdx.value < questions.value.length - 1) currentIdx.value++
}

function goTo(idx: number): void {
  currentIdx.value = idx
}

// 提交答案 ──
async function submitAnswer(): Promise<void> {
  const q = currentQ.value
  if (!q) return

  const idx = currentIdx.value
  if (answers.value[idx] && !answers.value[idx].analyzing) return // already answered

  const userAnswer = isChoice(q) ? selectedOption.value : shortAnswerText.value.trim()
  if (!userAnswer) return

  // B8: 短答题不在前端做字符串判分, isCorrect 留 null 等后端 AI 判定
  const isCorrect = isShortAnswer(q)
    ? null
    : userAnswer === q.correct_answer.trim()

  // B2: 兜底要求 dbId/taskId 必须有有效值, 否则阻断提交并报错
  const dbId = questionQuizDbIds.value[idx]
  const taskId = questionQuizTaskIds.value[idx]
  if (!dbId || !taskId) {
    console.error('[submitAnswer] missing batch meta', {
      idx,
      dbId,
      taskId,
      dbIds: questionQuizDbIds.value,
      taskIds: questionQuizTaskIds.value,
    })
    return
  }

  // 找到当前题所属的 batch (队列模式下题目来自多个 batch)
  // 取该题真实的 task id (优先用 feed 里的, fallback 到 route prop)
  const quizTaskId = questionQuizTaskIds.value[idx] || props.taskId
  const batchIdx = questionBatchIndex.value[idx] ?? idx

  answers.value[idx] = {
    userAnswer,
    isCorrect,
    analyzing: true,
    analysis: null,
    analyzeError: null,
    hintsUsed: answers.value[idx]?.hintsUsed ?? 0,
    hints: answers.value[idx]?.hints ?? [],
    hintLoading: false,
  }

  // Trigger AI analysis
  try {
    if (!quizTaskId) throw new Error('缺少 quiz task ID')
    const { data: start } = await startPracticeAnalyze({
      quizTaskId,
      questionIndex: batchIdx,
      userAnswer,
      mode: 'with_answer',
      subjectDisplay: getSubjectDisplayName(currentSubject.code),
      subjectCode: currentSubject.code,
    })

    const result = await pollPracticeUntilDone(start.task_id)
    const entry = answers.value[idx]
    if (!entry) return

    if (result.ok) {
      entry.analysis = result.analysis
      // B9: 以分析返回的 is_correct 作为唯一可信源
      const aiCorrect = result.analysis.result?.is_correct
      if (typeof aiCorrect === 'boolean') {
        entry.isCorrect = aiCorrect
      }
      entry.analyzing = false
    } else {
      entry.analyzeError = result.error
      entry.analyzing = false
    }
  } catch (e) {
    const entry = answers.value[idx]
    if (entry) {
      // 别把真错误吞了, 把 err.message 透出去, 用户能看到具体原因
      // (例: "缺少 quiz task ID" / "Network Error" / "Request failed with status code 500")
      const msg = e instanceof Error ? e.message : String(e)
      entry.analyzeError = `解析失败: ${msg}`
      entry.analyzing = false
    }
    console.error('[startPracticeAnalyze] failed', e)
  }

  // 记录已答题: 后端会去标 is_active=false 并自动补下一个 quiz
  // 短答题用 null 让后端按真实判分写库
  try {
    await markQuizAnswered({
      quiz_id: dbId,
      question_index: batchIdx,
      correct: isCorrect,
    })
} catch (e) {
    // 不阻塞 UI: 本地推进, 但上报方便排查
    console.error('[markQuizAnswered] failed', e)
  }
  // 让下一题立刻出现: 既有的已答题会被后端补题后清掉, force refresh
  await feed.refresh()
  // 自动跳到下一题 (B1: 之前这里只在越界时回退, 不会前进)
  const len = questions.value.length
  if (len === 0) {
    // feed 把所有题都收缩掉了 → 等待 4s 轮询补题
    phase.value = 'loading'
    errorMsg.value = isPlanMode.value ? 'AI 正在出计划相关题目…' : 'AI 正在出题…'
    return
  }
  if (currentIdx.value < len - 1) {
    currentIdx.value++
  } else {
    // 当前已是最后一题 → 保持在末尾, 等 feed 收缩后 watch 会再次触发
    currentIdx.value = len - 1
  }
}

// ── Hints (pre-submission) ──
async function requestHint(): Promise<void> {
  const idx = currentIdx.value
  const entry = answers.value[idx]
  if (entry?.hintLoading) return

  if (!answers.value[idx]) {
    answers.value[idx] = {
      userAnswer: '',
      isCorrect: false,
      analyzing: false,
      analysis: null,
      analyzeError: null,
      hintsUsed: 0,
      hints: [],
      hintLoading: true,
    }
  } else {
    answers.value[idx].hintLoading = true
  }

  try {
    // B2: 与 submitAnswer 一致的兜底, 防止 batch meta 缺失时发空任务
    const quizTaskId = questionQuizTaskIds.value[idx] ?? props.taskId ?? ''
    const batchIdx = questionBatchIndex.value[idx] ?? idx
    if (!quizTaskId) {
      console.error('[requestHint] missing batch meta', { idx })
      return
    }
    const { data: start } = await startPracticeAnalyze({
      quizTaskId,
      questionIndex: batchIdx,
      userAnswer: '',
      mode: 'without_answer',
      subjectDisplay: getSubjectDisplayName(currentSubject.code),
      subjectCode: currentSubject.code,
    })

    const result = await pollPracticeUntilDone(start.task_id)
    const e = answers.value[idx]
    if (!e) return

    if (result.ok && result.analysis.hints) {
      // B4: 后端一次返回多条 hint 时一次性推入 (去重), 不再每点一次只加一条 → 节省 Celery 调用
      const existing = new Set(e.hints)
      let added = 0
      for (const h of result.analysis.hints) {
        if (!existing.has(h)) {
          e.hints.push(h)
          added++
        }
      }
      e.hintsUsed += added
    }
  } catch {
    // silent
  } finally {
    if (answers.value[idx]) {
      answers.value[idx].hintLoading = false
    }
  }
}

function goBack(): void {
  router.push({ name: 'app-plan' })
}

function switchToHistory(taskId: string): void {
  showHistory.value = false
  currentTaskId.value = taskId
  // B3: 重置 currentDbId, 后续 loadQuestionsFor 完成时会再赋值
  currentDbId.value = 0
  questions.value = []
  answers.value = {}
  currentIdx.value = 0
  phase.value = 'loading'
  elapsed.value = 0
  if (timerHandle) clearInterval(timerHandle)
  loadQuestionsFor(taskId)
}

function relativeTime(isoStr: string): string {
  const now = Date.now()
  const then = new Date(isoStr).getTime()
  const diff = now - then
  const min = Math.floor(diff / 60_000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  return `${day} 天前`
}

// ── 去聊一聊 ──
async function goToChat(): Promise<void> {
  const q = currentQ.value
  if (!q) return

  // 获取当前学科 ID
  const subjectId = mySubjects.subjects.find((m) => m.name === currentSubject.code)?.id
  if (!subjectId) {
    console.error('[goToChat] 缺少学科 ID')
    return
  }

  // 构建题目数据（用于 meta，让 TutorView 渲染为出题助手卡片样式）
  const answerEntry = answers.value[currentIdx.value]
  const userAnswer = answerEntry?.userAnswer || null

  const questionData = {
    question_text: q.question_text,
    options: q.options || [],
    correct_answer: q.correct_answer,
    explanation: q.explanation,
    knowledge_points: [] as string[],
    user_answer: userAnswer,
  }

  try {
    // 创建对话（不带 extra_prompt）
    const { data } = await createConversation({
      subject_id: subjectId,
      title: `刷题答疑 - ${questionData.question_text.slice(0, 20)}...`,
      agent: 'tutor',
    })

    // 发送用户消息，用 practice_quiz 类型的 meta 渲染题目卡片
    await http.post(ENDPOINTS.MESSAGES, {
      conversation_id: data.id,
      content: '这道题不太理解，请帮我详细解析一下知识点和解题思路。',
      role: 'user',
      meta: {
        sub_agent_type: 'practice_quiz',
        questions: [questionData],
      },
    })

    // 跳转到对话页面
    router.push({ name: 'app-dialog', query: { conv: data.id } })
  } catch (err) {
    console.error('[goToChat] 创建对话失败', err)
  }
}
</script>

<template>
  <div class="x-exercise-detail">
    <!-- ── Top bar ───────────────────────────────────── -->
    <header class="x-detail-topbar">
      <button class="x-back-btn" @click="goBack">
        <span class="x-back-arrow" style="display:inline-flex;transform:scaleX(-1)"><IconArrow :size="13" /></span>
      </button>

      <div class="x-topbar-right">
        <button class="x-history-btn" @click="loadHistoryList(); showHistory = !showHistory" title="答题记录">
          <span class="x-history-icon" style="display:inline-flex"><IconNotepad :size="14" /></span>
        </button>
      </div>
    </header>

    <!-- 历史记录弹窗 -->
    <Transition name="xp-modal">
      <div v-if="showHistory" class="x-history-overlay" @click.self="showHistory = false">
        <div class="x-history-dropdown">
          <header class="x-history-head">
            <span class="x-history-title">答题记录</span>
            <button class="x-history-close" @click="showHistory = false">×</button>
          </header>
          <div class="x-history-body">
            <div v-if="historyLoading" class="x-history-loading">
              <div class="x-loading-spinner x-loading-spinner--sm" />
            </div>
            <div v-else-if="historyList.length === 0" class="x-history-empty">暂无记录</div>
            <div v-else class="x-history-list">
              <button
                v-for="item in historyList"
                :key="item.id"
                class="x-history-item"
                @click="switchToHistory(item.task_id)"
              >
                <div class="x-history-item-top">
                  <span class="x-history-item-count">{{ item.actual_count || item.requested_count }}</span>
                  <span class="x-history-item-label">题</span>
                  <span class="x-history-item-subject">{{ item.subject_display }}</span>
                </div>
                <div class="x-history-item-time">{{ relativeTime(item.created_at) }}</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── 历史记录弹窗 ── -->

    <!-- ── Loading state ─────────────────────────────── -->
    <div v-if="phase === 'loading'" class="x-loading-state">
      <div class="x-loading-spinner" />
      <p class="x-loading-text">AI 正在生成题目…</p>
      <p class="x-loading-sub">{{ errorMsg || '请稍候' }}</p>
    </div>

    <!-- ── Error state ───────────────────────────────── -->
    <div v-else-if="phase === 'error'" class="x-error-state">
      <div class="x-error-icon"><IconCross :size="22" /></div>
      <p class="x-error-text">{{ errorMsg || '加载失败' }}</p>
      <button class="x-retry-btn" @click="loadQuestions">重试</button>
      <button class="x-back-link" @click="goBack">返回刷题</button>
    </div>

    <!-- ── Main content (answering / done) ───────────── -->
    <div v-else class="x-detail-main">
      <!-- Left: Question area -->
      <div class="x-q-panel">
        <div v-if="currentQ" class="x-q-panel-scroll">
          <!-- Question header -->
          <div class="x-q-head">
            <div class="x-q-head-left">
              <div class="x-q-tags">
                <span class="x-tag" :class="difficultyClass(currentQ.difficulty)">
                  {{ difficultyLabel(currentQ.difficulty) }}
                </span>
                <span v-if="currentQ.knowledge_node_name" class="x-tag x-tag-bloom">
                  {{ currentQ.knowledge_node_name }}
                </span>
              </div>
            </div>
            <div class="x-q-nav">
              <button :disabled="currentIdx === 0" @click="goPrev">‹</button>
              <button :disabled="currentIdx === questions.length - 1" @click="goNext">›</button>
            </div>
          </div>

          <!-- (无限流模式: 不显示进度条) -->

          <!-- Question text -->
          <div class="x-q-body">
            <h2 class="x-q-title">{{ currentQ.question_text }}</h2>

            <!-- Image (if any) -->
            <img
              v-if="currentQ.image_base64"
              :src="currentQ.image_base64"
              class="x-q-image"
              alt="题目图片"
            />

            <!-- Choice options -->
            <div v-if="isChoice(currentQ) && currentQ.options" class="x-choices">
              <button
                v-for="(opt, oi) in currentQ.options"
                :key="oi"
                class="x-choice"
                :class="{
                  'is-selected': selectedOption === letterFor(oi),
                  'is-correct': answers[currentIdx]?.userAnswer && letterFor(oi) === currentQ.correct_answer,
                  'is-wrong': answers[currentIdx]?.userAnswer === letterFor(oi) && letterFor(oi) !== currentQ.correct_answer,
                  'is-disabled': !!answers[currentIdx]?.userAnswer,
                }"
                :disabled="!!answers[currentIdx]?.userAnswer"
                @click="selectedOption = letterFor(oi)"
              >
                <span class="x-choice-letter">{{ letterFor(oi) }}</span>
                <span class="x-choice-text">{{ opt }}</span>
              </button>
            </div>

            <!-- Short answer -->
            <div v-else-if="isShortAnswer(currentQ)" class="x-short-answer">
              <textarea
                v-model="shortAnswerText"
                class="x-text-area"
                :disabled="!!answers[currentIdx]?.userAnswer"
                placeholder="在此输入你的答案…"
                rows="5"
              />
              <div v-if="answers[currentIdx]?.userAnswer" class="x-answer-display">
                <span class="x-answer-label">你的答案：</span>
                {{ answers[currentIdx]!.userAnswer }}
              </div>
            </div>
          </div>
        </div>

        <!-- Action bar -->
        <div v-if="currentQ" class="x-action-bar">
          <div class="x-action-left">
            <button
              v-if="!answers[currentIdx]?.userAnswer"
              class="x-btn-hint"
              :disabled="answers[currentIdx]?.hintLoading"
              @click="requestHint"
            >
              <span class="x-hint-icon" style="display:inline-flex"><IconBulb :size="14" /></span>
              {{ answers[currentIdx]?.hintLoading ? '获取中…' : '要提示' }}
              <span v-if="answers[currentIdx]?.hintsUsed" class="x-hint-badge">
                {{ answers[currentIdx]!.hintsUsed }}
              </span>
            </button>
          </div>
          <div class="x-action-right">
            <button
              v-if="currentIdx > 0"
              class="x-btn-secondary"
              @click="goPrev"
            >
              上一题
            </button>
            <button
              v-if="!answers[currentIdx]?.userAnswer"
              class="x-btn-primary"
              :disabled="isChoice(currentQ) ? !selectedOption : !shortAnswerText.trim()"
              @click="submitAnswer"
            >
              提交答案
            </button>
            <button
              v-else-if="currentIdx < questions.length - 1"
              class="x-btn-primary"
              @click="goNext"
            >
              下一题
            </button>
          </div>
        </div>
      </div>

      <!-- Right: Analysis panel -->
      <div class="x-analysis-panel">
        <template v-if="currentQ">
          <!-- Pre-submission -->
          <template v-if="!answers[currentIdx]?.userAnswer">
            <div class="x-phase-head">
              <span class="x-phase-badge x-phase-badge--pre">答题中</span>
              <h3 class="x-phase-title">提交答案后查看详细解析</h3>
              <p class="x-phase-sub">
                先尝试自己解答，提交后 AI 将给出个性化分析
              </p>
            </div>
            <div class="x-analysis-scroll">
              <!-- 去聊一聊按钮 -->
              <div class="x-chat-action">
                <button class="x-btn-chat" @click="goToChat">
                  去聊一聊
                </button>
              </div>
              <!-- Hints (if requested) -->
              <div v-if="answers[currentIdx]?.hints?.length" class="x-a-section">
                <div class="x-a-section-title">渐进提示</div>
                <div
                  v-for="(hint, hi) in answers[currentIdx]!.hints"
                  :key="hi"
                  class="x-hint-card"
                >
                  <div class="x-hint-head">
                    <span class="x-hint-num">{{ hi + 1 }}</span>
                    <span class="x-hint-label">提示 {{ hi + 1 }}</span>
                  </div>
                  <p class="x-hint-text">{{ hint }}</p>
                </div>
              </div>

              <!-- Knowledge preview -->
              <div v-if="currentQ.knowledge_node_name" class="x-a-section">
                <div class="x-a-section-title">涉及知识点</div>
                <div class="x-k-item">
                  <span class="x-k-icon" style="display:inline-flex;align-items:center;justify-content:center"><IconNode :size="14" /></span>
                  <div class="x-k-body">
                    <div class="x-k-name">{{ currentQ.knowledge_node_name }}</div>
                    <div class="x-k-desc">本题考察的核心知识点</div>
                  </div>
                </div>
              </div>

              <!-- Static explanation (from question data) -->
              <div v-if="currentQ.explanation" class="x-a-section">
                <div class="x-a-section-title">参考讲解</div>
                <div class="x-approach-card">
                  <MarkdownContent :text="currentQ.explanation" />
                </div>
              </div>
            </div>
          </template>

          <!-- Post-submission: Analyzing (骨架屏, 结构镜像最终结果) -->
          <template v-else-if="answers[currentIdx]?.analyzing">
            <div class="x-phase-head">
              <span class="x-phase-badge x-phase-badge--pre">
                <span style="display:inline-flex;align-items:center;gap:4px">
                  <IconHourglass :size="11" />
                  分析中
                </span>
              </span>
              <h3 class="x-phase-title">AI 正在生成解析…</h3>
            </div>
            <div class="x-analysis-scroll x-analyzing">
              <!-- 镜像 verdict banner 的位置 -->
              <div class="x-result-banner is-pending x-skel-banner">
                <div class="x-result-icon x-skel x-skel-circle" />
                <div class="x-result-body">
                  <div class="x-skel x-skel-line x-skel-w60" />
                  <div class="x-skel x-skel-line x-skel-w40" />
                </div>
              </div>

              <!-- 解析正文 -->
              <div class="x-a-section">
                <div class="x-a-section-title x-skel x-skel-line x-skel-w30" />
                <div class="x-skel x-skel-block" />
                <div class="x-skel x-skel-block" style="width: 92%" />
                <div class="x-skel x-skel-block" style="width: 78%" />
              </div>

              <!-- 解题步骤 (骨架 3 行) -->
              <div class="x-a-section">
                <div class="x-a-section-title x-skel x-skel-line x-skel-w30" />
                <ol class="x-steps x-skel-steps">
                  <li v-for="n in 3" :key="n">
                    <span class="x-skel x-skel-line x-skel-w90" />
                  </li>
                </ol>
              </div>

              <!-- 关键知识点 -->
              <div class="x-a-section">
                <div class="x-a-section-title x-skel x-skel-line x-skel-w30" />
                <ul class="x-kp-list x-skel-list">
                  <li v-for="n in 3" :key="n">
                    <span class="x-skel x-skel-line x-skel-w70" />
                  </li>
                </ul>
              </div>

              <!-- 详细讲解 -->
              <div class="x-a-section">
                <div class="x-a-section-title x-skel x-skel-line x-skel-w30" />
                <div class="x-skel x-skel-block" />
                <div class="x-skel x-skel-block" style="width: 88%" />
              </div>
            </div>
          </template>

          <!-- Post-submission: Analysis result -->
          <template v-else-if="answers[currentIdx]?.analysis">
            <div class="x-phase-head">
              <span
                class="x-phase-badge"
                :class="verdictBadgeClass(currentVerdict)"
              >
                <span style="display:inline-flex;align-items:center;gap:4px">
                  <component
                    :is="currentVerdict === 'correct' ? IconCheck : currentVerdict === 'wrong' ? IconCross : IconHourglass"
                    :size="11"
                  />
                  {{ verdictLabel(currentVerdict) }}
                </span>
              </span>
              <h3 class="x-phase-title">
                {{ answers[currentIdx]!.analysis!.result?.summary || '解析' }}
              </h3>
            </div>

            <div class="x-analysis-scroll">
              <!-- 去聊一聊按钮 -->
              <div class="x-chat-action">
                <button class="x-btn-chat" @click="goToChat">
                  去聊一聊
                </button>
              </div>
              <!-- Result banner -->
              <div
                class="x-result-banner"
                :class="currentVerdict === 'correct' ? 'is-correct' : currentVerdict === 'wrong' ? 'is-wrong' : 'is-pending'"
              >
                <div class="x-result-icon">
                  <component
                    :is="currentVerdict === 'correct' ? IconCheck : currentVerdict === 'wrong' ? IconCross : IconHourglass"
                    :size="20"
                  />
                </div>
                <div class="x-result-body">
                  <div class="x-result-verdict">
                    {{ verdictLabel(currentVerdict) }}
                  </div>
                  <div v-if="currentVerdict === 'wrong' && currentQ?.correct_answer" class="x-result-correct">
                    正确答案：{{ currentQ!.correct_answer }}
                  </div>
                </div>
              </div>

              <!-- Analysis text -->
              <div v-if="answers[currentIdx]!.analysis!.analysis" class="x-a-section">
                <div class="x-a-section-title">解析</div>
                <MarkdownContent :text="answers[currentIdx]!.analysis!.analysis" />
              </div>

              <!-- Steps -->
              <div v-if="answers[currentIdx]!.analysis!.steps?.length" class="x-a-section">
                <div class="x-a-section-title">解题步骤</div>
                <ol class="x-steps">
                  <li
                    v-for="(step, si) in answers[currentIdx]!.analysis!.steps"
                    :key="si"
                    :class="{ 'is-key': step.is_key }"
                  >
                    <MarkdownContent :text="step.text" />
                  </li>
                </ol>
              </div>

              <!-- Key knowledge points -->
              <div v-if="answers[currentIdx]!.analysis!.key_knowledge_points?.length" class="x-a-section">
                <div class="x-a-section-title">关键知识点</div>
                <ul class="x-kp-list">
                  <li v-for="(kp, ki) in answers[currentIdx]!.analysis!.key_knowledge_points" :key="ki">
                    {{ kp }}
                  </li>
                </ul>
              </div>

              <!-- Deep analysis -->
              <div v-if="answers[currentIdx]!.analysis!.deep_analysis" class="x-a-section">
                <div class="x-a-section-title">详细讲解</div>
                <MarkdownContent :text="answers[currentIdx]!.analysis!.deep_analysis!" />
              </div>

              <!-- Pitfalls -->
              <div v-if="answers[currentIdx]!.analysis!.pitfalls?.length" class="x-a-section">
                <div class="x-a-section-title">常见误区</div>
                <ul class="x-pitfall-list">
                  <li v-for="(p, pi) in answers[currentIdx]!.analysis!.pitfalls" :key="pi">
                    {{ p }}
                  </li>
                </ul>
              </div>

              <!-- Next steps -->
              <div v-if="answers[currentIdx]!.analysis!.next_steps?.length" class="x-a-section">
                <div class="x-a-section-title">推荐学习</div>
                <ul class="x-next-list">
                  <li v-for="(ns, ni) in answers[currentIdx]!.analysis!.next_steps" :key="ni">
                    {{ ns }}
                  </li>
                </ul>
              </div>

              <!-- Knowledge cards -->
              <div v-if="answers[currentIdx]!.analysis!.knowledge?.length" class="x-a-section">
                <div class="x-a-section-title">知识点卡片</div>
                <div
                  v-for="(k, ki) in answers[currentIdx]!.analysis!.knowledge"
                  :key="ki"
                  class="x-k-item"
                >
                  <span class="x-k-icon" style="display:inline-flex;align-items:center;justify-content:center"><IconNode :size="14" /></span>
                  <div class="x-k-body">
                    <div class="x-k-name">{{ k.title }}</div>
                    <div class="x-k-desc">{{ k.description }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- Post-submission: Analysis error -->
          <template v-else-if="answers[currentIdx]?.analyzeError">
            <div class="x-phase-head">
              <span class="x-phase-badge x-phase-badge--wrong">解析失败</span>
              <h3 class="x-phase-title">{{ answers[currentIdx]!.analyzeError }}</h3>
            </div>
          </template>

          <!-- Fallback -->
          <template v-else>
            <div class="x-phase-head">
              <span class="x-phase-badge x-phase-badge--pre">等待中</span>
              <h3 class="x-phase-title">提交答案后查看解析</h3>
            </div>
          </template>
        </template>

        <!-- Empty state when no question -->
        <div v-else class="x-analysis-empty">
          <p>选择一道题目查看解析</p>
        </div>
      </div>
    </div>

    <!-- ── 当前批答完 → 自动出下一批 ── -->
    <transition name="x-fade">
      <div v-if="phase === 'done'" class="x-done-bar">
        <span>本组完成，正在出下一组…</span>
        <div class="x-loading-spinner x-loading-spinner--sm" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.x-exercise-detail {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 64px); /* minus AppShell topbar */
  background: var(--x-canvas);
}

/* ── Top bar ───────────────────────────────────────── */
.x-detail-topbar {
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 48px;
  border-bottom: 1px solid var(--x-hairline);
  background: var(--x-canvas);
  gap: 16px;
  flex-shrink: 0;
}

.x-back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: transparent;
  font-size: 13px;
  font-family: inherit;
  color: var(--x-body-mid);
  cursor: pointer;
  transition: all 0.15s;
}

.x-back-btn:hover {
  color: var(--x-primary);
  border-color: var(--x-primary);
  background: var(--x-primary-soft);
}

.x-back-arrow {
  font-size: 14px;
}

.x-topbar-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.x-topbar-progress {
  font-size: 13px;
  font-weight: 500;
  color: var(--x-body-mid);
}

.x-topbar-dots {
  display: flex;
  gap: 6px;
}

.x-topbar-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--x-hairline);
  cursor: pointer;
  transition: all 0.15s;
}

.x-topbar-dot.is-current {
  background: var(--x-primary);
  box-shadow: 0 0 0 3px oklch(56% 0.19 255 / 0.15);
}

.x-topbar-dot.is-correct {
  background: oklch(52% 0.15 155);
}

.x-topbar-dot.is-wrong {
  background: oklch(56% 0.20 25);
}

.x-topbar-review-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  letter-spacing: 0.02em;
}

.x-topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.x-history-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-body-mid);
  font: 500 12px/1 var(--x-font-display);
  padding: 6px 12px;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.x-history-btn:hover { background: var(--x-primary-soft); color: var(--x-primary); }

.x-topbar-timer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--x-font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  letter-spacing: 0.04em;
}

.x-timer-icon {
  font-size: 14px;
}

/* ── Loading / Error states ────────────────────────── */
.x-loading-state,
.x-error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--x-body-mid);
}

.x-loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--x-hairline);
  border-top-color: var(--x-primary);
  border-radius: 50%;
  animation: x-spin 0.7s linear infinite;
}

.x-loading-spinner--sm {
  width: 24px;
  height: 24px;
  border-width: 2px;
}

.x-loading-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--x-ink);
}

.x-loading-sub {
  font-size: 13px;
}

.x-error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: oklch(96% 0.04 25);
  color: oklch(50% 0.15 25);
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 700;
}

.x-error-text {
  font-size: 15px;
  color: var(--x-ink);
}

.x-retry-btn {
  padding: 8px 24px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--x-primary);
  cursor: pointer;
  transition: background 0.15s;
}

.x-retry-btn:hover {
  background: var(--x-primary-soft);
}

.x-back-link {
  padding: 6px 16px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-family: inherit;
  color: var(--x-body-mid);
  cursor: pointer;
  text-decoration: underline;
}

@keyframes x-spin {
  to { transform: rotate(360deg); }
}

/* ── 骨架屏 (分析中动画) ─────────────────────────────
   镜像最终结果的结构, 用 shimmer 渐变扫描, 让用户感觉在加载而非卡死
   ───────────────────────────────────────────────────── */
.x-skel {
  position: relative;
  display: block;
  background: oklch(94% 0.01 250);
  border-radius: 6px;
  overflow: hidden;
}

.x-skel::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    oklch(98% 0.005 250 / 0.7) 50%,
    transparent 100%
  );
  animation: x-shimmer 1.4s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes x-shimmer {
  100% { transform: translateX(100%); }
}

.x-skel-line {
  height: 14px;
  margin: 8px 0;
}

.x-skel-w30 { width: 30%; }
.x-skel-w40 { width: 40%; }
.x-skel-w60 { width: 60%; }
.x-skel-w70 { width: 70%; }
.x-skel-w90 { width: 90%; }

.x-skel-block {
  height: 16px;
  width: 100%;
  margin: 10px 0;
}

.x-skel-circle {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}

.x-skel-banner {
  /* 沿用 is-pending 的底色, 再叠骨架 */
  position: relative;
}
.x-skel-banner .x-skel {
  background: oklch(90% 0.02 80);
}
.x-skel-banner .x-skel::after {
  background: linear-gradient(
    90deg,
    transparent 0%,
    oklch(96% 0.04 80 / 0.6) 50%,
    transparent 100%
  );
}

.x-skel-steps,
.x-skel-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.x-skel-steps li,
.x-skel-list li {
  margin: 10px 0;
}

/* 尊重用户的"减少动画"偏好 (系统级设置) */
@media (prefers-reduced-motion: reduce) {
  .x-skel::after {
    animation: none;
    opacity: 0.6;
  }
}

/* ── Main layout ───────────────────────────────────── */
.x-detail-main {
  flex: 1;
  width: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 460px;
  overflow: hidden;
}

/* ── Question panel (left) ─────────────────────────── */
.x-q-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.x-q-panel-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 32px 40px 24px;
}

.x-q-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.x-q-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.x-q-num {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--x-ink);
}

.x-q-total {
  font-size: 14px;
  color: var(--x-body-mid);
}

.x-q-tags {
  display: flex;
  gap: 8px;
  margin-left: 4px;
}

.x-tag {
  font-size: 11.5px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--x-hairline);
  color: var(--x-body-mid);
  background: var(--x-canvas);
}

.x-tag.diff-easy {
  color: oklch(42% 0.12 155);
  border-color: oklch(85% 0.06 155);
  background: oklch(96% 0.03 155);
}

.x-tag.diff-med {
  color: oklch(52% 0.12 80);
  border-color: oklch(85% 0.06 80);
  background: oklch(96% 0.03 80);
}

.x-tag.diff-hard {
  color: oklch(48% 0.14 25);
  border-color: oklch(85% 0.06 25);
  background: oklch(96% 0.03 25);
}

.x-tag-bloom {
  color: oklch(50% 0.10 300);
  border-color: oklch(88% 0.04 300);
  background: oklch(97% 0.02 300);
}

.x-q-nav {
  display: flex;
  gap: 6px;
}

.x-q-nav button {
  width: 34px;
  height: 34px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-body-mid);
  font-size: 16px;
  font-weight: 500;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.15s;
}

.x-q-nav button:hover:not(:disabled) {
  border-color: var(--x-primary);
  color: var(--x-primary);
}

.x-q-nav button:disabled {
  opacity: 0.3;
  cursor: default;
}

/* Progress dots */
.x-progress {
  display: flex;
  gap: 6px;
  margin-bottom: 28px;
}

.x-progress-dot {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--x-hairline);
  transition: background 0.2s;
}

.x-progress-dot.is-done {
  background: oklch(52% 0.15 155);
}

.x-progress-dot.is-current {
  background: var(--x-primary);
}

/* Question body */
.x-q-body {
  margin-bottom: 28px;
}

.x-q-title {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--x-ink);
  margin-bottom: 16px;
  letter-spacing: -0.01em;
}

.x-q-image {
  max-width: 100%;
  border-radius: var(--x-rounded-md);
  margin: 12px 0;
}

/* Choice cards */
.x-choices {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
}

.x-choice {
  display: flex;
  gap: 14px;
  padding: 14px 18px;
  border: 1.5px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
  font-family: inherit;
  width: 100%;
}

.x-choice:hover:not(.is-disabled) {
  border-color: oklch(80% 0.02 250);
}

.x-choice.is-selected {
  border-color: var(--x-primary);
  background: var(--x-primary-soft);
}

.x-choice.is-correct {
  border-color: oklch(52% 0.15 155);
  background: oklch(96% 0.04 155);
}

.x-choice.is-wrong {
  border-color: oklch(56% 0.20 25);
  background: oklch(96% 0.04 25);
}

.x-choice.is-disabled {
  cursor: default;
}

.x-choice-letter {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1.5px solid var(--x-hairline);
  display: grid;
  place-items: center;
  font-family: var(--x-font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--x-body-mid);
  flex-shrink: 0;
  transition: all 0.15s;
}

.x-choice.is-selected .x-choice-letter {
  border-color: var(--x-primary);
  color: var(--x-primary);
  background: oklch(92% 0.04 255);
}

.x-choice.is-correct .x-choice-letter {
  border-color: oklch(52% 0.15 155);
  color: oklch(42% 0.12 155);
  background: oklch(92% 0.06 155);
}

.x-choice.is-wrong .x-choice-letter {
  border-color: oklch(56% 0.20 25);
  color: oklch(48% 0.14 25);
  background: oklch(92% 0.06 25);
}

.x-choice-text {
  font-size: 15px;
  line-height: 1.5;
  color: var(--x-ink);
  flex: 1;
}

/* Short answer */
.x-text-area {
  width: 100%;
  min-height: 120px;
  padding: 14px 18px;
  border: 1.5px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  font-size: 15px;
  font-family: inherit;
  line-height: 1.65;
  color: var(--x-ink);
  resize: vertical;
  transition: border-color 0.15s;
  outline: none;
  margin-bottom: 16px;
}

.x-text-area:focus {
  border-color: var(--x-primary);
}

.x-text-area::placeholder {
  color: oklch(68% 0.01 250);
}

.x-text-area:disabled {
  opacity: 0.5;
}

.x-answer-display {
  font-size: 14px;
  line-height: 1.6;
  color: var(--x-ink);
  padding: 12px 16px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
}

.x-answer-label {
  font-weight: 600;
  color: var(--x-body-mid);
  font-size: 12px;
}

/* Action bar */
.x-action-bar {
  padding: 14px 48px;
  border-top: 1px solid var(--x-hairline);
  background: var(--x-canvas);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.x-action-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.x-action-right {
  display: flex;
  gap: 8px;
}

.x-btn-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-body-mid);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}

.x-btn-hint:hover:not(:disabled) {
  border-color: oklch(68% 0.14 80);
  color: oklch(50% 0.12 80);
}

.x-btn-hint:disabled {
  opacity: 0.4;
  cursor: default;
}

.x-hint-icon {
  font-size: 14px;
}

.x-hint-badge {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: oklch(68% 0.14 80);
  color: white;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 700;
}

.x-btn-primary {
  padding: 10px 28px;
  background: var(--x-primary);
  color: white;
  border: none;
  border-radius: var(--x-rounded-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}

.x-btn-primary:hover:not(:disabled) {
  filter: brightness(1.08);
}

.x-btn-primary:disabled {
  opacity: 0.4;
  cursor: default;
  filter: none;
}

.x-btn-primary--lg {
  padding: 14px 40px;
  font-size: 16px;
}

.x-btn-ghost {
  padding: 10px 20px;
  border: none;
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-soft);
  color: var(--x-body);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.x-btn-ghost:hover { background: var(--x-primary-soft); color: var(--x-primary); }

.x-btn-chat {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 24px;
  background: var(--x-primary);
  color: white;
  border: none;
  border-radius: var(--x-rounded-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}

.x-btn-chat:hover:not(:disabled) {
  filter: brightness(1.08);
}

.x-btn-chat:disabled {
  opacity: 0.4;
  cursor: default;
}

.x-chat-action {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.x-btn-secondary {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 20px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-ink);
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.15s;
}

.x-btn-secondary:hover {
  border-color: oklch(80% 0.02 250);
}

/* ── Analysis panel (right) ────────────────────────── */
.x-analysis-panel {
  display: flex;
  flex-direction: column;
  background: var(--x-canvas);
  border-left: 1px solid var(--x-hairline);
  overflow: hidden;
}

.x-phase-head {
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--x-hairline);
  flex-shrink: 0;
}

.x-phase-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  border-radius: 999px;
  font-family: var(--x-font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.x-phase-badge--pre {
  background: var(--x-primary-soft);
  color: var(--x-primary);
  border: 1px solid oklch(88% 0.04 255);
}

.x-phase-badge--correct {
  background: oklch(96% 0.04 155);
  color: oklch(38% 0.12 155);
  border: 1px solid oklch(82% 0.06 155);
}

.x-phase-badge--wrong {
  background: oklch(96% 0.04 25);
  color: oklch(42% 0.16 25);
  border: 1px solid oklch(82% 0.06 25);
}

.x-phase-title {
  font-family: var(--x-font-display);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--x-ink);
  margin-top: 12px;
}

.x-phase-sub {
  font-size: 13px;
  line-height: 1.5;
  color: var(--x-body-mid);
  margin-top: 4px;
}

.x-analysis-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.x-analyzing {
  display: flex;
  flex-direction: column;
  /* 骨架用 flex-start 让占位条左对齐, 与最终结果布局一致 */
  align-items: stretch;
  gap: 4px;
  color: var(--x-body-mid);
  font-size: 14px;
}

.x-analysis-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--x-body-mid);
  font-size: 14px;
}

/* Analysis sections */
.x-a-section {
  margin-bottom: 20px;
}

.x-a-section-title {
  font-family: var(--x-font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--x-body-mid);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.x-a-section-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--x-hairline);
}

/* Result banner */
.x-result-banner {
  padding: 20px;
  border-radius: var(--x-rounded-md);
  margin-bottom: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.x-result-banner.is-correct {
  background: oklch(96% 0.04 155);
  border: 1.5px solid oklch(82% 0.06 155);
}

.x-result-banner.is-wrong {
  background: oklch(96% 0.04 25);
  border: 1.5px solid oklch(82% 0.06 25);
}

.x-result-banner.is-pending {
  background: oklch(96% 0.04 80);
  border: 1.5px solid oklch(82% 0.06 80);
}

.x-result-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-size: 20px;
  font-weight: 700;
  color: white;
}

.x-result-banner.is-correct .x-result-icon {
  background: oklch(52% 0.15 155);
}

.x-result-banner.is-wrong .x-result-icon {
  background: oklch(56% 0.20 25);
}

.x-result-banner.is-pending .x-result-icon {
  background: oklch(56% 0.10 80);
  color: white;
}

.x-result-verdict {
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
}

.x-result-correct {
  font-size: 13px;
  color: var(--x-body-mid);
  margin-top: 4px;
}

/* Approach card */
.x-approach-card {
  padding: 16px;
  border: 1px solid oklch(88% 0.04 255);
  border-radius: var(--x-rounded-md);
  background: oklch(98% 0.008 255);
}

/* Hint cards */
.x-hint-card {
  padding: 14px 16px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  margin-bottom: 8px;
}

.x-hint-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.x-hint-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: oklch(97% 0.04 80);
  color: oklch(45% 0.12 80);
  display: grid;
  place-items: center;
  font-family: var(--x-font-mono);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.x-hint-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--x-body-mid);
}

.x-hint-text {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--x-ink);
  padding-left: 30px;
}

/* Knowledge items */
.x-k-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  margin-bottom: 6px;
  transition: border-color 0.15s;
}

.x-k-item:hover {
  border-color: oklch(85% 0.03 250);
}

.x-k-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: oklch(96% 0.008 250);
  display: grid;
  place-items: center;
  font-size: 14px;
  flex-shrink: 0;
  color: var(--x-primary);
}

.x-k-body {
  flex: 1;
}

.x-k-name {
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 600;
  color: var(--x-ink);
}

.x-k-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--x-body-mid);
  margin-top: 3px;
}

/* Steps */
.x-steps {
  padding-left: 24px;
  margin: 0;
}

.x-steps li {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.x-steps li.is-key {
  font-weight: 600;
}

/* Lists */
.x-kp-list,
.x-pitfall-list,
.x-next-list {
  padding-left: 20px;
  margin: 0;
}

.x-kp-list li,
.x-pitfall-list li,
.x-next-list li {
  margin-bottom: 6px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--x-ink);
}

/* ── Summary overlay ───────────────────────────────── */
/* ── Review bar (历史答题顶部紧凑统计条 —— 替代原来底部的大卡片) ── */
.x-review-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 24px;
  height: 52px;
  background: var(--x-canvas-soft);
  border-bottom: 1px solid var(--x-hairline);
}

.x-review-bar-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--x-font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--x-primary);
  padding: 5px 12px;
  border: 1px solid oklch(88% 0.04 255);
  background: var(--x-primary-soft);
  border-radius: 999px;
  flex-shrink: 0;
}

.x-review-bar-mark {
  font-size: 13px;
}

.x-review-bar-stats {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--x-font-display);
  flex-shrink: 0;
}

.x-review-bar-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--x-ink);
  line-height: 1;
}

.x-review-bar-sep {
  font-size: 14px;
  color: var(--x-body-mid);
  line-height: 1;
}

.x-review-bar-total {
  font-size: 14px;
  color: var(--x-body-mid);
  line-height: 1;
}

.x-review-bar-word {
  font-size: 12px;
  color: var(--x-body-mid);
  margin-left: 6px;
}

.x-review-bar-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.x-review-bar-track {
  flex: 1;
  max-width: 220px;
  height: 6px;
  border-radius: 3px;
  background: var(--x-hairline);
  overflow: hidden;
}

.x-review-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: oklch(52% 0.15 155);
  transition: width 0.3s ease;
}

.x-review-bar-pct {
  font-family: var(--x-font-mono);
  font-size: 13px;
  font-weight: 600;
  color: oklch(52% 0.15 155);
}

.x-review-bar-back {
  flex-shrink: 0;
  padding: 7px 16px;
  font-size: 13px;
}

.x-summary-overlay {
  position: fixed;
  inset: 0;
  background: oklch(0% 0 0 / 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.x-summary-card {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-lg);
  padding: 40px 48px;
  width: 480px;
  max-width: 90vw;
  box-shadow: 0 24px 64px oklch(0% 0 0 / 0.2);
}

.x-summary-head {
  text-align: center;
  margin-bottom: 32px;
}

.x-summary-head h2 {
  font-family: var(--x-font-display);
  font-size: 24px;
  font-weight: 700;
  color: var(--x-ink);
}

.x-summary-head p {
  font-size: 14px;
  color: var(--x-body-mid);
  margin-top: 4px;
}

.x-summary-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 24px;
}

.x-stat {
  text-align: center;
}

.x-stat-value {
  display: block;
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--x-ink);
}

.x-stat-label {
  font-size: 12px;
  color: var(--x-body-mid);
  margin-top: 4px;
}

.x-summary-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}

.x-summary-bar-track {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--x-hairline);
  overflow: hidden;
}

.x-summary-bar-fill {
  height: 100%;
  border-radius: 4px;
  background: oklch(52% 0.15 155);
  transition: width 0.4s ease;
}

.x-summary-pct {
  font-family: var(--x-font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  min-width: 40px;
  text-align: right;
}

.x-summary-actions {
  display: flex;
  justify-content: center;
}

/* ── Transitions ───────────────────────────────────── */
.x-fade-enter-active,
.x-fade-leave-active {
  transition: opacity 0.2s;
}

.x-fade-enter-from,
.x-fade-leave-to {
  opacity: 0;
}

/* ── Responsive ────────────────────────────────────── */
@media (max-width: 1024px) {
  .x-detail-main {
    grid-template-columns: 1fr;
  }

  .x-analysis-panel {
    border-left: none;
    border-top: 1px solid var(--x-hairline);
    max-height: 400px;
  }

  .x-q-panel-scroll {
    padding: 24px 24px 16px;
  }

  .x-action-bar {
    padding: 12px 24px;
  }
}

/* ── Done bar (当前批答完自动出下一批) ── */
.x-done-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: var(--x-canvas);
  border-radius: var(--x-rounded-pill);
  box-shadow: var(--x-shadow-modal);
  font: 14px/1 var(--x-font-display);
  color: var(--x-body-mid);
  z-index: 50;
}
.x-done-bar .x-loading-spinner { width: 14px; height: 14px; }

@media (max-width: 768px) {
  .x-detail-topbar {
    padding: 0 16px;
  }

  .x-q-panel-scroll {
    padding: 16px;
  }

  .x-action-bar {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .x-analysis-scroll {
    padding: 16px;
  }
}

/* ── 历史记录弹窗 ── */
.x-history-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  justify-content: flex-end;
  background: transparent;
}
.x-history-dropdown {
  margin-top: 52px;
  margin-right: 16px;
  width: 320px;
  max-height: calc(100vh - 80px);
  background: var(--x-canvas);
  border-radius: var(--x-rounded-lg);
  box-shadow: var(--x-shadow-modal);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.x-history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  flex-shrink: 0;
}
.x-history-title {
  font: 600 14px/1 var(--x-font-display);
  color: var(--x-ink);
}
.x-history-close {
  width: 28px; height: 28px;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-body-mid);
  font-size: 18px;
  line-height: 1;
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
}
.x-history-close:hover { background: var(--x-error-soft); color: var(--x-error); }
.x-history-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 12px;
}
.x-history-loading {
  display: flex;
  justify-content: center;
  padding: 32px 0;
}
.x-history-empty {
  text-align: center;
  padding: 32px 0;
  font: 13px/1 var(--x-font-display);
  color: var(--x-body-mid);
}
.x-history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-history-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: none;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: background 0.12s;
  width: 100%;
}
.x-history-item:hover { background: var(--x-canvas-mid); }
.x-history-item-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.x-history-item-count {
  font: 600 15px/1 var(--x-font-mono);
  color: var(--x-primary);
}
.x-history-item-label {
  font: 500 12px/1 var(--x-font-display);
  color: var(--x-body-mid);
}
.x-history-item-subject {
  font: 500 12px/1 var(--x-font-display);
  color: var(--x-body);
  margin-left: auto;
}
.x-history-item-time {
  font: 500 11px/1 var(--x-font-mono);
  color: var(--x-body-mid);
}

.xp-modal-enter-active, .xp-modal-leave-active {
  transition: opacity 0.15s ease;
}
.xp-modal-enter-from, .xp-modal-leave-to {
  opacity: 0;
}
</style>
