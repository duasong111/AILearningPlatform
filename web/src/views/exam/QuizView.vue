<script setup lang="ts">
/**
 * AI 出题 (Quiz 模式) —— 批量出题 + 即时分析
 *
 *   跟 PracticeView (agent=practice WS 流) 的区别:
 *     - QuizView: 纯 HTTP 轮询, 一批题先全部出来, 然后逐题点选 + 看分析
 *     - PracticeView: WS 流式, 一题一题出, 边答边判
 *
 *   流程:
 *     1. 选学科 + 点"开始答题" → POST /api/quiz/generate/ → poll
 *     2. 拿到题组 → 渲染题干 + A/B/C/D 按钮
 *     3. 点选项 → POST /api/practice/analyze/ → poll
 *     4. 拿到 analysis → 右侧抽屉滑出, 显示 AI 讲解
 *     5. 切下一题 / 上一题 → 抽屉内容跟着换
 *
 *   状态机:
 *     idle        → 等用户点"开始答题"
 *     generating  → 调 /api/quiz/generate/ + poll
 *     answering   → 显示题组, 等用户点选项
 *     analyzing   → 调 /api/practice/analyze/ + poll
 *     done        → 全部题答完 (可选保留)
 *     error       → 出题或分析失败, 显示错误 + retry
 *
 *   不用 store: 整批题只在这个 view 内部用, 跟 PracticeView 一样用 local ref.
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { getSubjectDisplayName } from '@/api/subjects'
import {
  fetchPracticeAnalyses,
  fetchQuizHistory,
  isChoice,
  isShortAnswer,
  pollPracticeUntilDone,
  pollQuizUntilDone,
  startPracticeAnalyze,
  startQuizTask,
  type PracticeAnalysisItem,
  type PracticeResultPayload,
  type QuizHistoryItem,
  type StructuredQuestion,
} from '@/api/quiz'
import { formatRelative } from '@/utils/format'
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { SubjectCode } from '@/types/learning'
import {
  IconSparkle,
  IconCross,
  IconRetry,
  IconCheck,
  IconArrow,
  IconWarn,
} from '@/components/icons'

// ============================================================
// State (all local, no store)
// ============================================================
const mySubjects = useMySubjectsStore()

const selectedSubjectCode = ref<SubjectCode | ''>(
  (mySubjects.subjects[0]?.name as SubjectCode | undefined) ?? '',
)
const currentSubjectId = computed<number | null>(() => {
  const s = mySubjects.subjects.find((m) => m.name === selectedSubjectCode.value)
  return s?.id ?? null
})
const noSubject = computed(() => mySubjects.subjects.length === 0)

// ============================================================
// Dashboard 数据 —— 仅 phase==='idle' 视图消费, 跟答题流 state 解耦
//
//   接口:
//     GET /api/quizzes/           → QuizGenerationRecord[]  (出过的题, 含 state/subject/created_at)
//     GET /api/practice-analyses/ → PracticeAnalysisRecord[](答过题的解析)
//
//   设计稿里有 "平均分 / 最高分 / 5 维度能力雷达" 这些字段, 后端没存,
//   不造假数据, 概览页只展示能从真实记录里推导的 4 个指标 + 学科卡 + 历史 table.
// ============================================================
const quizRecords = ref<QuizHistoryItem[]>([])
const practiceRecords = ref<PracticeAnalysisItem[]>([])
const dashboardLoading = ref(false)
const dashboardError = ref('')

async function loadAssessmentData(): Promise<void> {
  dashboardLoading.value = true
  dashboardError.value = ''
  try {
    // 两条 list 并行拉, 减少首屏等待
    const [{ data: quizList }, { data: praList }] = await Promise.all([
      fetchQuizHistory(),
      fetchPracticeAnalyses(),
    ])
    // 后端 default ordering 是 -created_at, 这里再保险 sort 一次, 不依赖后端
    quizRecords.value = [...quizList].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
    practiceRecords.value = [...praList].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
  } catch (err) {
    dashboardError.value = err instanceof Error ? err.message : '加载评测数据失败'
  } finally {
    dashboardLoading.value = false
  }
}

// 4 个统计数字 —— 全部从真实 records 推导, 无 mock
const completedQuizCount = computed(
  () => quizRecords.value.filter((r) => r.state === 'complete').length,
)
const analyzedQuestionCount = computed(
  () => practiceRecords.value.filter((r) => r.state === 'complete').length,
)
const subjectsCoveredCount = computed(() => {
  const ids = new Set<number>()
  for (const r of quizRecords.value) {
    if (r.state === 'complete') ids.add(r.subject_id)
  }
  return ids.size
})
const lastAssessmentRelative = computed(() => {
  const latest = quizRecords.value.find((r) => r.state === 'complete')
  return latest ? formatRelative(latest.created_at) : '—'
})

// 可用评测卡 —— 每门已添加学科一张, 状态根据是否做过完成态 quiz 来定
interface SubjectCard {
  id: number
  name: string
  display_name: string
  status: 'available' | 'completed'  // 可参加 / 已完成
  doneCount: number                   // 已做过几组
  latestTaskId: string | null         // 最近一组 task_id, 可用于跳"重做最近"
}
const subjectCards = computed<SubjectCard[]>(() => {
  return mySubjects.subjects.map((s) => {
    const mine = quizRecords.value.filter(
      (r) => r.subject_id === s.id && r.state === 'complete',
    )
    return {
      id: s.id,
      name: s.name,
      display_name: s.display_name,
      status: mine.length > 0 ? 'completed' : 'available',
      doneCount: mine.length,
      latestTaskId: mine[0]?.task_id ?? null,
    }
  })
})

// 历史 table 行 —— 最近 8 条已完成 quiz, 用 actual_count + completion 时长展示
interface HistoryRow {
  id: number
  task_id: string
  subject_display: string
  count: number               // 题目数
  created_at: string          // ISO
  duration_min: number | null // completed_at - created_at, 分钟; null=进行中
}
const historyRows = computed<HistoryRow[]>(() => {
  return quizRecords.value
    .filter((r) => r.state === 'complete')
    .slice(0, 8)
    .map((r) => {
      const start = new Date(r.created_at).getTime()
      const end = r.completed_at ? new Date(r.completed_at).getTime() : 0
      const min = end > start ? Math.max(1, Math.round((end - start) / 60000)) : null
      return {
        id: r.id,
        task_id: r.task_id,
        subject_display: r.subject_display,
        count: r.actual_count,
        created_at: r.created_at,
        duration_min: min,
      }
    })
})

// 题数 → pill 配色档 (代替设计稿里"按分数分档"的方案, 因为后端没分数)
function countTier(n: number): 'high' | 'mid' | 'low' {
  if (n >= 10) return 'high'
  if (n >= 5) return 'mid'
  return 'low'
}

type Phase = 'idle' | 'generating' | 'answering' | 'analyzing' | 'done' | 'error'
const phase = ref<Phase>('idle')

const questions = ref<StructuredQuestion[]>([])
const currentIndex = ref(0)
const userAnswers = ref<Record<number, string>>({})    // question_index → user answer
const quizTaskId = ref<string | null>(null)
const currentAnalysis = ref<PracticeResultPayload | null>(null)
const analysisDrawerOpen = ref(false)

const startQuizError = ref<string>('')
const analysisError = ref<string>('')

const currentQuestion = computed<StructuredQuestion | null>(
  () => questions.value[currentIndex.value] ?? null,
)
const isCurrentAnswered = computed(
  () => currentIndex.value in userAnswers.value,
)
const answeredCount = computed(() => Object.keys(userAnswers.value).length)
const totalCount = computed(() => questions.value.length)
const progressLabel = computed(
  () => `${answeredCount.value} / ${totalCount.value}`,
)

// ============================================================
// Subject picker bootstrap — PracticeView 同样要 mounted 拉
// ============================================================
onMounted(() => {
  if (mySubjects.subjects.length === 0) {
    mySubjects.loadFromBackend()
  }
  // 异步拉评测记录, 不阻塞主流程, idle 视图自带 loading skeleton
  loadAssessmentData()
})

// ============================================================
// 生成配置 dialog —— 让用户选 题数 + 难度 再发起出题
//
//   传给后端的两个维度:
//     count        → /api/quiz/generate/ body.count   (后端 int, 直接转发给 task)
//     difficulty   → 后端没有专门字段, 翻译成自然语言塞 extra_prompt
//                    后端 LLM chain 会把 extra_prompt 拼进出题 prompt
// ============================================================
type QuizCount = 3 | 5 | 8
type QuizDifficulty = 'easy' | 'medium' | 'hard'

const generateConfig = ref<{ count: QuizCount; difficulty: QuizDifficulty }>({
  count: 5,
  difficulty: 'medium',
})
const generateDialogOpen = ref(false)

const QUIZ_COUNT_OPTIONS: QuizCount[] = [3, 5, 8]
const QUIZ_DIFFICULTY_OPTIONS: Array<{ value: QuizDifficulty; label: string; hint: string }> = [
  { value: 'easy',   label: '简单', hint: '巩固基础概念' },
  { value: 'medium', label: '中等', hint: '综合应用' },
  { value: 'hard',   label: '困难', hint: '深度思考与拓展' },
]

const DIFFICULTY_PROMPT_FRAGMENT: Record<QuizDifficulty, string> = {
  easy:   '请生成简单难度的题目, 偏向基础概念辨析与记忆。',
  medium: '请生成中等难度的题目, 侧重综合应用与场景分析。',
  hard:   '请生成困难难度的题目, 需要多步推理或跨知识点融合。',
}

/** 打开配置对话框. 可选传 card → 同步选中学科 */
function openGenerateDialog(card?: { name: string }): void {
  if (card) {
    selectedSubjectCode.value = card.name as SubjectCode
  }
  if (!currentSubjectId.value) {
    ElMessage({
      message: '× 请先在「我的课程」添加一门学科',
      customClass: 'x-toast',
    })
    return
  }
  // 不重置之前的配置, 让用户连续测试时保留偏好
  generateDialogOpen.value = true
}

/** 用户在对话框点 "开始测验" → 关弹窗 + 触发实际出题 */
function confirmGenerate(): void {
  generateDialogOpen.value = false
  handleStartQuiz()
}

// ============================================================
// Action: 开始答题 (handler 签名不变, 内部读 generateConfig)
// ============================================================
async function handleStartQuiz(): Promise<void> {
  if (!currentSubjectId.value) {
    ElMessage({ message: '× 请先在「我的课程」添加一门学科', customClass: 'x-toast' })
    return
  }
  phase.value = 'generating'
  startQuizError.value = ''
  questions.value = []
  currentIndex.value = 0
  userAnswers.value = {}
  currentAnalysis.value = null
  analysisDrawerOpen.value = false

  try {
    const { count, difficulty } = generateConfig.value
    const { data: startRes } = await startQuizTask({
      subjectId: currentSubjectId.value,
      count,
      // 把难度翻译成自然语言塞进 extra_prompt, 后端 LLM chain 会拼到出题 prompt
      extraPrompt: DIFFICULTY_PROMPT_FRAGMENT[difficulty],
    })
    quizTaskId.value = startRes.task_id
    const result = await pollQuizUntilDone(startRes.task_id, (s) => {
      // 进度回调 (目前后端只有 generating/complete/error 三态, 不展开)
      if (s === 'generating') phase.value = 'generating'
    })
    if (!result.ok) {
      startQuizError.value = result.error
      phase.value = 'error'
      return
    }
    questions.value = result.questions
    phase.value = result.questions.length > 0 ? 'answering' : 'done'
  } catch (err) {
    startQuizError.value = err instanceof Error ? err.message : '出题失败'
    phase.value = 'error'
  }
}

// ============================================================
// Action: 点选项 → 调 analyze
// ============================================================
async function handleOptionClick(letter: string): Promise<void> {
  if (phase.value !== 'answering') return
  const q = currentQuestion.value
  if (!q || !quizTaskId.value || !currentSubjectId.value) return
  if (isCurrentAnswered.value) return                          // 已答过, 锁住

  const subject = mySubjects.subjects.find(
    (s) => s.id === currentSubjectId.value,
  )
  const subjectDisplay = subject?.display_name ?? '未知学科'
  const subjectCode = subject?.name ?? 'unknown'

  userAnswers.value[currentIndex.value] = letter
  phase.value = 'analyzing'
  analysisError.value = ''
  analysisDrawerOpen.value = true
  currentAnalysis.value = null

  try {
    const { data: startRes } = await startPracticeAnalyze({
      quizTaskId: quizTaskId.value,
      questionIndex: currentIndex.value,
      userAnswer: letter,
      subjectDisplay,
      subjectCode,
    })
    const r = await pollPracticeUntilDone(startRes.task_id)
    if (!r.ok) {
      analysisError.value = r.error
      currentAnalysis.value = null
      phase.value = 'answering'
      return
    }
    currentAnalysis.value = r.analysis
    phase.value = 'answering'                                // 恢复, 可以切下一题
  } catch (err) {
    analysisError.value = err instanceof Error ? err.message : '分析失败'
    currentAnalysis.value = null
    phase.value = 'answering'
  }
}

// 短答题自由文本提交
const freeTextInput = ref('')
async function handleFreeFormSubmit(): Promise<void> {
  const text = freeTextInput.value.trim()
  if (!text) {
    ElMessage({ message: '× 请先输入答案', customClass: 'x-toast' })
    return
  }
  freeTextInput.value = ''
  await handleOptionClick(text)                              // 复用同一条分析通道
}

// ============================================================
// Action: 切换题目
// ============================================================
function handlePrev(): void {
  if (currentIndex.value > 0) {
    currentIndex.value--
    currentAnalysis.value = null
    analysisError.value = ''
  }
}
function handleNext(): void {
  if (currentIndex.value < questions.value.length - 1) {
    currentIndex.value++
    currentAnalysis.value = null
    analysisError.value = ''
  }
}

function closeAnalysisDrawer(): void {
  analysisDrawerOpen.value = false
}
</script>

<template>
  <div class="x-quiz">
    <!-- HEADER -->
    <header class="x-quiz-head">
      <div class="x-quiz-head-left">
        <p class="x-eyebrow x-eyebrow-mute">LEARNING ⏤ ASSESSMENT</p>
        <h1 class="x-quiz-title">评测系统</h1>
        <p class="x-quiz-sub">
          能力评估 · 章节测验 · 综合认证 —— 按学科出题, 即时给讲解与归档。
        </p>
      </div>
      <div class="x-quiz-head-right">
        <select
          v-if="!noSubject"
          v-model="selectedSubjectCode"
          class="x-subject-pick"
          :disabled="phase === 'generating' || phase === 'analyzing'"
        >
          <option
            v-for="s in mySubjects.subjects"
            :key="s.id"
            :value="s.name"
          >{{ s.display_name }}</option>
        </select>
        <button
          class="x-btn x-btn-primary"
          :disabled="noSubject || phase === 'generating' || phase === 'analyzing'"
          @click="openGenerateDialog()"
        >
          {{ phase === 'generating' ? '出题中…' : '开始答题' }}
        </button>
        <span v-if="phase === 'answering' || phase === 'analyzing'" class="x-status is-ok">
          进度 {{ progressLabel }}
        </span>
        <span v-else-if="phase === 'generating'" class="x-status is-busy">生成中…</span>
        <span v-else-if="phase === 'error'" class="x-status is-error">出错了</span>
      </div>
    </header>

    <!-- BODY -->
    <div class="x-quiz-body">
      <!-- empty: 还没选课 -->
      <div v-if="noSubject" class="x-quiz-empty">
        <p class="x-quiz-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-primary)"><IconSparkle :size="40" /></p>
        <p class="x-quiz-empty-title">还没选课</p>
        <p class="x-quiz-empty-hint">先去「我的课程」添加一门学科, 才能出题。</p>
      </div>

      <!-- error: 出题失败 -->
      <div v-else-if="phase === 'error' && startQuizError" class="x-quiz-empty">
        <p class="x-quiz-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-error, oklch(58% 0.20 25))"><IconCross :size="36" /></p>
        <p class="x-quiz-empty-title">出题失败</p>
        <p class="x-quiz-empty-hint">{{ startQuizError }}</p>
        <button class="x-btn x-btn-outline-sm" @click="handleStartQuiz"><span style="display:inline-flex;align-items:center;gap:6px"><IconRetry :size="12" /> 重试</span></button>
      </div>

      <!-- idle: 评测中心 dashboard
           原本只是个"准备好就出题"空状态, 现在改成参考设计稿 10-assessment.html 的
           评测概览页 —— 统计 + 可用评测 + 历史记录 三块, 全部用真实后端数据 -->
      <div v-else-if="phase === 'idle'" class="x-dash">
        <!-- 加载/错误状态 (不阻塞 layout, 给个轻量提示) -->
        <div v-if="dashboardLoading" class="x-dash-loading">
          <span class="x-dash-spinner"></span>
          <span>加载评测数据…</span>
        </div>
        <div v-else-if="dashboardError" class="x-dash-error">
          <span style="display:inline-flex;align-items:center;gap:6px">
            <IconCross :size="12" />
            {{ dashboardError }}
          </span>
          <button class="x-btn x-btn-outline-sm" @click="loadAssessmentData"><span style="display:inline-flex;align-items:center;gap:6px"><IconRetry :size="12" /> 重试</span></button>
        </div>

        <!-- 评测统计 (4 数字) -->
        <section class="x-dash-stats">
          <div class="x-stat-card">
            <p class="x-eyebrow x-eyebrow-mute">已完成评测</p>
            <p class="x-stat-num">{{ completedQuizCount }}</p>
            <p class="x-stat-hint">出题任务 (state=complete)</p>
          </div>
          <div class="x-stat-card">
            <p class="x-eyebrow x-eyebrow-mute">答题分析</p>
            <p class="x-stat-num x-stat-num-primary">{{ analyzedQuestionCount }}</p>
            <p class="x-stat-hint">已生成解析的题数</p>
          </div>
          <div class="x-stat-card">
            <p class="x-eyebrow x-eyebrow-mute">覆盖学科</p>
            <p class="x-stat-num x-stat-num-secondary">{{ subjectsCoveredCount }}</p>
            <p class="x-stat-hint">/ {{ mySubjects.subjects.length }} 已添加</p>
          </div>
          <div class="x-stat-card">
            <p class="x-eyebrow x-eyebrow-mute">最近评测</p>
            <p class="x-stat-num x-stat-num-text">{{ lastAssessmentRelative }}</p>
            <p class="x-stat-hint">距上次出题</p>
          </div>
        </section>

        <!-- 可用评测 (按已添加学科, 每门一卡) -->
        <section class="x-dash-section">
          <header class="x-dash-section-head">
            <h2 class="x-dash-section-title">可用评测</h2>
            <span class="x-dash-section-sub">
              选学科 → 点「开始答题」即可生成一组题
            </span>
          </header>

          <div v-if="subjectCards.length === 0" class="x-dash-empty-card">
            还没添加任何学科, 去「我的课程」加一门再回来。
          </div>

          <div v-else class="x-dash-cards">
            <article
              v-for="card in subjectCards"
              :key="card.id"
              class="x-exam-card"
              :class="{ 'is-active': card.name === selectedSubjectCode }"
              @click="selectedSubjectCode = card.name as SubjectCode"
            >
              <header class="x-exam-status">
                <span class="x-exam-dot" :class="`is-${card.status}`"></span>
                <span class="x-exam-status-text" :class="`is-${card.status}`">
                  {{ card.status === 'completed' ? '已完成' : '可参加' }}
                </span>
              </header>

              <h3 class="x-exam-title">{{ card.display_name }}</h3>

              <div class="x-exam-meta">
                <span v-if="card.doneCount > 0">
                  已完成 {{ card.doneCount }} 组
                </span>
                <span v-else>暂无记录, 开始第一组</span>
              </div>

              <footer class="x-exam-cta">
                <button
                  class="x-btn x-btn-primary x-btn-sm"
                  :disabled="phase !== 'idle'"
                  @click.stop="openGenerateDialog(card)"
                >
                  {{ card.status === 'completed' ? '再来一组' : '开始测验' }}
                </button>
              </footer>
            </article>
          </div>
        </section>

        <!-- 评测记录 (最近 8 条已完成 quiz) -->
        <section class="x-dash-section">
          <header class="x-dash-section-head">
            <h2 class="x-dash-section-title">评测记录</h2>
            <span class="x-dash-section-sub">最近 {{ historyRows.length }} 条</span>
          </header>

          <div v-if="historyRows.length === 0" class="x-dash-empty-card">
            还没有评测记录, 完成一组测验后会出现在这里。
          </div>

          <table v-else class="x-dash-table">
            <thead>
              <tr>
                <th>学科</th>
                <th>题数</th>
                <th>日期</th>
                <th>用时</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in historyRows" :key="row.id">
                <td>{{ row.subject_display }}</td>
                <td>
                  <span class="x-count-pill" :class="`is-${countTier(row.count)}`">
                    {{ row.count }} 题
                  </span>
                </td>
                <td class="x-dash-cell-mute">{{ formatRelative(row.created_at) }}</td>
                <td class="x-dash-cell-mute">
                  {{ row.duration_min !== null ? `${row.duration_min} 分钟` : '—' }}
                </td>
                <td class="x-dash-cell-action">
                  <code class="x-dash-task-id">{{ row.task_id.slice(0, 8) }}</code>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <!-- 答题中 -->
      <div v-else class="x-quiz-grid">
        <!-- LEFT: 进度 -->
        <aside class="x-quiz-progress">
          <p class="x-eyebrow x-eyebrow-mute">PROGRESS</p>
          <p class="x-quiz-progress-big">{{ progressLabel }}</p>
          <ul class="x-quiz-progress-list">
            <li
              v-for="(q, i) in questions"
              :key="i"
              :class="{
                'is-current': i === currentIndex,
                'is-done': i in userAnswers,
              }"
              @click="currentIndex = i"
            >
              <span class="x-quiz-progress-num">{{ i + 1 }}</span>
              <span class="x-quiz-progress-name">
                {{ q.knowledge_node_name }}
                <small>{{ q.difficulty }}</small>
              </span>
            </li>
          </ul>
        </aside>

        <!-- MIDDLE: 当前题 -->
        <main class="x-quiz-main">
          <div v-if="currentQuestion" class="x-quiz-card">
            <p class="x-eyebrow">
              Q{{ currentIndex + 1 }} · {{ currentQuestion.difficulty }} ·
              {{ currentQuestion.knowledge_node_name }}
            </p>
            <p class="x-quiz-stem">{{ currentQuestion.question_text }}</p>

            <!-- 选择题 -->
            <div v-if="isChoice(currentQuestion)" class="x-quiz-options">
              <button
                v-for="opt in (currentQuestion.options ?? [])"
                :key="opt"
                class="x-quiz-opt"
                :class="{
                  'is-selected': userAnswers[currentIndex] === opt,
                  'is-correct': userAnswers[currentIndex] && currentQuestion.correct_answer && opt.startsWith(currentQuestion.correct_answer + '.'),
                  'is-locked': isCurrentAnswered,
                }"
                :disabled="isCurrentAnswered"
                @click="handleOptionClick(opt)"
              >
                {{ opt }}
              </button>
            </div>

            <!-- 短答题 -->
            <div v-else-if="isShortAnswer(currentQuestion)" class="x-quiz-freeform">
              <textarea
                v-model="freeTextInput"
                class="x-input"
                rows="4"
                placeholder="输入你的答案…"
                :disabled="isCurrentAnswered"
              />
              <button
                class="x-btn x-btn-primary"
                :disabled="isCurrentAnswered"
                @click="handleFreeFormSubmit"
              >提交</button>
            </div>

            <!-- 翻页 -->
            <div class="x-quiz-nav">
              <button
                class="x-btn x-btn-outline-sm"
                :disabled="currentIndex === 0"
                @click="handlePrev"
              ><span style="display:inline-flex;align-items:center;gap:6px"><span style="display:inline-flex;transform:scaleX(-1)"><IconArrow :size="11" /></span> 上一题</span></button>
              <span class="x-quiz-nav-pos">{{ currentIndex + 1 }} / {{ questions.length }}</span>
              <button
                class="x-btn x-btn-outline-sm"
                :disabled="currentIndex >= questions.length - 1"
                @click="handleNext"
              ><span style="display:inline-flex;align-items:center;gap:6px">下一题 <IconArrow :size="11" /></span></button>
            </div>

            <!-- 标准答案 (答完才显示) -->
            <details v-if="isCurrentAnswered" class="x-quiz-answers">
              <summary>查看标准答案</summary>
              <p><strong>正确答案：</strong>{{ currentQuestion.correct_answer }}</p>
              <p><strong>解析：</strong>{{ currentQuestion.explanation }}</p>
            </details>
          </div>
        </main>
      </div>
    </div>

    <!-- 右侧分析抽屉 -->
    <aside
      class="x-quiz-drawer"
      :class="{ 'is-open': analysisDrawerOpen }"
    >
      <button
        v-if="analysisDrawerOpen"
        class="x-quiz-drawer-close"
        @click="closeAnalysisDrawer"
      ><span style="display:inline-flex;align-items:center;gap:6px"><IconCross :size="11" /> 关闭</span></button>

      <p v-if="!currentAnalysis && !analysisError" class="x-quiz-drawer-hint">
        点左侧题目的选项后, AI 分析会出现在这里
      </p>

      <div v-else-if="analysisError" class="x-quiz-drawer-error">
        <p class="x-eyebrow x-eyebrow-mute">ANALYSIS FAILED</p>
        <p>{{ analysisError }}</p>
      </div>

      <div v-else-if="currentAnalysis" class="x-quiz-drawer-content">
        <p class="x-eyebrow x-eyebrow-mute">
          AI 分析 · {{ currentAnalysis.difficulty_assessment }} · 阶段 {{ currentAnalysis.phase }}
        </p>

        <!-- 判分结果条 -->
        <div
          v-if="currentAnalysis.result"
          class="x-quiz-verdict"
          :class="{
            'is-correct': currentAnalysis.result.is_correct,
            'is-wrong':   !currentAnalysis.result.is_correct,
          }"
        >
          <span class="x-quiz-verdict-mark" style="display:inline-flex;align-items:center;justify-content:center">
            <component :is="currentAnalysis.result.is_correct ? IconCheck : IconCross" :size="18" />
          </span>
          <span class="x-quiz-verdict-text">
            {{ currentAnalysis.result.summary }}
          </span>
        </div>

        <div class="x-quiz-drawer-analysis">
          <MarkdownContent :text="currentAnalysis.analysis" />
        </div>

        <!-- 解题步骤 -->
        <div v-if="currentAnalysis.steps && currentAnalysis.steps.length > 0" class="x-quiz-steps">
          <p class="x-eyebrow x-eyebrow-mute">解题步骤</p>
          <ol class="x-quiz-steps-list">
            <li
              v-for="(s, i) in currentAnalysis.steps"
              :key="i"
              class="x-quiz-step"
              :class="{ 'is-key': s.is_key }"
            >
              <span class="x-quiz-step-num">{{ i + 1 }}</span>
              <span class="x-quiz-step-text">{{ s.text }}</span>
              <span v-if="s.is_key" class="x-quiz-step-tag">关键</span>
            </li>
          </ol>
        </div>

        <!-- 误区 -->
        <div v-if="currentAnalysis.pitfalls && currentAnalysis.pitfalls.length > 0" class="x-quiz-pitfalls">
          <p class="x-eyebrow x-eyebrow-mute">常见误区</p>
          <ul class="x-quiz-pitfalls-list">
            <li v-for="(p, i) in currentAnalysis.pitfalls" :key="i"><span style="display:inline-flex;align-items:center;margin-right:4px;color:var(--x-accent-amber, oklch(70% 0.15 80))"><IconWarn :size="12" /></span>{{ p }}</li>
          </ul>
        </div>

        <!-- 知识点 -->
        <div v-if="currentAnalysis.knowledge && currentAnalysis.knowledge.length > 0" class="x-quiz-knowledge">
          <p class="x-eyebrow x-eyebrow-mute">关键知识点</p>
          <ul class="x-quiz-knowledge-list">
            <li v-for="(k, i) in currentAnalysis.knowledge" :key="i" class="x-quiz-knowledge-card">
              <p class="x-quiz-knowledge-title">{{ k.title }}</p>
              <p class="x-quiz-knowledge-desc">{{ k.description }}</p>
            </li>
          </ul>
        </div>

        <!-- 下一步 -->
        <div v-if="currentAnalysis.next_steps && currentAnalysis.next_steps.length > 0" class="x-quiz-next">
          <p class="x-eyebrow x-eyebrow-mute">接下来</p>
          <ol class="x-quiz-next-list">
            <li v-for="(s, i) in currentAnalysis.next_steps" :key="i">
              <span class="x-quiz-next-num">{{ i + 1 }}.</span>
              <span class="x-quiz-next-text">{{ s }}</span>
            </li>
          </ol>
        </div>

        <!-- 旧 key_points (兼容) -->
        <div v-if="currentAnalysis.key_knowledge_points.length > 0" class="x-quiz-drawer-points">
          <p class="x-eyebrow x-eyebrow-mute">标签</p>
          <ul>
            <li v-for="p in currentAnalysis.key_knowledge_points" :key="p">{{ p }}</li>
          </ul>
        </div>
      </div>
    </aside>
  </div>

  <!-- ============================================================
       配置 Dialog —— 用户开始出题前选 题数 + 难度
       teleport 到 body 避免被父级 overflow / transform 限制
       ============================================================ -->
  <teleport to="body">
    <transition name="x-modal-fade">
      <div
        v-if="generateDialogOpen"
        class="x-modal-backdrop"
        @click.self="generateDialogOpen = false"
      >
        <div class="x-modal" role="dialog" aria-modal="true" aria-labelledby="quiz-modal-title">
          <header class="x-modal-head">
            <h3 id="quiz-modal-title" class="x-modal-title">配置评测</h3>
            <button
              class="x-modal-close"
              aria-label="关闭"
              @click="generateDialogOpen = false"
            ><IconCross :size="14" /></button>
          </header>

          <div class="x-modal-body">
            <p class="x-modal-desc">
              根据你已选学科 + 学习画像 (掌握度/弱点) 自动出题。
              下面两个维度告诉 AI 你想要的题怎么生成。
            </p>

            <!-- 学科 (只展示, 不可选 —— 在外面 picker 改) -->
            <div class="x-modal-field">
              <p class="x-modal-label">学科</p>
              <p class="x-modal-value">
                {{ getSubjectDisplayName(selectedSubjectCode) || '—' }}
              </p>
            </div>

            <!-- 题目数量 -->
            <div class="x-modal-field">
              <p class="x-modal-label">题目数量</p>
              <div class="x-modal-segments">
                <button
                  v-for="n in QUIZ_COUNT_OPTIONS"
                  :key="n"
                  type="button"
                  class="x-segment"
                  :class="{ 'is-active': generateConfig.count === n }"
                  @click="generateConfig.count = n"
                >
                  {{ n }} 题
                </button>
              </div>
            </div>

            <!-- 难度 -->
            <div class="x-modal-field">
              <p class="x-modal-label">难度</p>
              <div class="x-modal-segments">
                <button
                  v-for="d in QUIZ_DIFFICULTY_OPTIONS"
                  :key="d.value"
                  type="button"
                  class="x-segment x-segment-stacked"
                  :class="{ 'is-active': generateConfig.difficulty === d.value }"
                  @click="generateConfig.difficulty = d.value"
                >
                  <span class="x-segment-title">{{ d.label }}</span>
                  <span class="x-segment-hint">{{ d.hint }}</span>
                </button>
              </div>
            </div>
          </div>

          <footer class="x-modal-foot">
            <button
              class="x-btn x-btn-outline-sm"
              @click="generateDialogOpen = false"
            >取消</button>
            <button
              class="x-btn x-btn-primary"
              @click="confirmGenerate"
            ><span style="display:inline-flex;align-items:center;gap:6px">开始测验 <IconArrow :size="12" /></span></button>
          </footer>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
/* ============================================================
   容器 + 头部 (复制 PracticeView 风格, 各自一份避免跨 scope 依赖)
   ============================================================ */
.x-quiz {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  color: var(--x-ink);
  display: flex;
  flex-direction: column;
}
.x-quiz-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 28px 40px 18px;
  border-bottom: 1px solid var(--x-hairline);
  /* max-width: var(--x-container); */
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  gap: 24px;
}
.x-quiz-head-left { flex: 1; min-width: 0; }
.x-quiz-head-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.x-quiz-title {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 600;
  margin: 4px 0 4px;
  color: var(--x-ink);
}
.x-quiz-sub {
  font-size: 12px;
  color: var(--x-body-mid);
  margin: 0;
  max-width: 540px;
  line-height: 1.6;
}
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--x-primary);
  margin: 0;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

/* ============================================================
   按钮 / 状态 (复制 PracticeView)
   ============================================================ */
.x-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--x-rounded-sm);
  font-size: 13px;
  font-family: var(--x-font-ui);
  cursor: pointer;
  border: 1px solid transparent;
  background: transparent;
  color: var(--x-ink);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.x-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-color: var(--x-primary);
}
.x-btn-primary:not(:disabled):hover { filter: brightness(0.93); }
.x-btn-outline-sm {
  padding: 6px 12px;
  font-size: 12px;
  border-color: var(--x-hairline-strong);
}
.x-btn-outline-sm:not(:disabled):hover { background: var(--x-canvas-soft); }

.x-subject-pick {
  padding: 6px 10px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-ink);
  font-size: 13px;
  font-family: var(--x-font-ui);
  min-width: 140px;
}
.x-status {
  font-size: 11px;
  padding: 4px 8px;
  border-radius: var(--x-rounded-sm);
  font-family: var(--x-font-mono);
}
.x-status.is-ok { background: rgba(0, 160, 0, 0.08); color: #2c8a2c; }
.x-status.is-busy { background: rgba(255, 165, 0, 0.1); color: #b07a1a; }
.x-status.is-error { background: rgba(220, 50, 50, 0.08); color: #c13030; }

/* ============================================================
   BODY
   ============================================================ */
.x-quiz-body {
  flex: 1;
  padding: 24px 40px 48px;
  /* max-width: var(--x-container); */
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* 空白态 / 错误态 */
.x-quiz-empty {
  text-align: center;
  padding: 80px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  border: 1px dashed var(--x-hairline-strong);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas-soft);
}
.x-quiz-mark {
  font-size: 40px;
  color: var(--x-primary);
  margin-bottom: 8px;
}
.x-quiz-empty-title {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.x-quiz-empty-hint {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0 0 8px;
}

/* 2 栏 grid: 进度 + 当前题 (跟 PracticeView 一致, 右侧用 fixed drawer) */
.x-quiz-grid {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  align-items: start;
}
@media (max-width: 1024px) {
  .x-quiz-grid { grid-template-columns: 1fr; }
}

/* ============================================================
   DASHBOARD —— phase='idle' 视图 (评测中心)
   按设计稿 10-assessment.html, 复用 x-* token, 不引新色
   ============================================================ */
.x-dash {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 4px 0 8px;
}

/* 加载/错误条 —— 顶部细 hint, 不阻塞 layout */
.x-dash-loading,
.x-dash-error {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--x-body-mid);
  padding: 8px 12px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: 8px;
}
.x-dash-error {
  color: var(--x-error, oklch(58% 0.20 25));
}
.x-dash-spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--x-hairline);
  border-top-color: var(--x-primary);
  animation: x-dash-spin 0.8s linear infinite;
}
@keyframes x-dash-spin { to { transform: rotate(360deg); } }

/* === 4 数字统计 === */
.x-dash-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.x-stat-card {
  padding: 20px 24px;
  background: var(--x-canvas);
  border-radius: 12px;
  box-shadow: var(--x-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-stat-card:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-stat-num {
  font-family: var(--x-font-display);
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: var(--x-ink);
  letter-spacing: -0.4px;
  font-variant-numeric: tabular-nums;
  margin: 4px 0 0;
}
/* 用主色突出 "答题分析" 数字 (核心指标) */
.x-stat-num-primary { color: var(--x-primary); }
/* 用绿色突出 "覆盖学科" (进度类指标) */
.x-stat-num-secondary { color: oklch(55% 0.18 142); }
/* 文本类指标 (最近评测时间) 字号小一档, 因为是 "3 分钟前" 这种文字 */
.x-stat-num-text { font-size: 20px; font-weight: 600; }
.x-stat-hint {
  font-size: 11px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.4px;
  color: var(--x-body-mid);
  margin: 0;
}

/* === 区块标题 === */
.x-dash-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.x-dash-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 4px;
}
.x-dash-section-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
  letter-spacing: -0.2px;
}
.x-dash-section-sub {
  font-size: 12px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.4px;
  color: var(--x-body-mid);
}

.x-dash-empty-card {
  padding: 32px 24px;
  text-align: center;
  font-size: 13px;
  color: var(--x-body-mid);
  background: var(--x-canvas-soft);
  border: 1px dashed var(--x-hairline);
  border-radius: 10px;
}

/* === 可用评测卡片 grid === */
.x-dash-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.x-exam-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
  background: var(--x-canvas-card);
  border-radius: 12px;
  box-shadow: var(--x-shadow-card);
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-exam-card:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-exam-card.is-active {
  box-shadow: var(--x-shadow-card-hover),
              0 0 0 3px oklch(52% 0.18 255 / 0.18);
  transform: translateY(-2px);
}

.x-exam-status {
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-exam-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--x-hairline);
}
.x-exam-dot.is-available { background: oklch(62% 0.14 168); }   /* 绿 */
.x-exam-dot.is-completed { background: var(--x-primary); }      /* 蓝 */

.x-exam-status-text {
  font-size: 11px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.6px;
  font-weight: 600;
  text-transform: uppercase;
}
.x-exam-status-text.is-available { color: oklch(55% 0.14 168); }
.x-exam-status-text.is-completed { color: var(--x-primary); }

.x-exam-title {
  font-family: var(--x-font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
  letter-spacing: -0.2px;
}
.x-exam-meta {
  font-size: 12px;
  color: var(--x-body-mid);
  flex: 1;
}
.x-exam-cta {
  margin-top: 8px;
}
.x-exam-cta .x-btn {
  width: 100%;
}

/* btn-sm 跟原 .x-btn-primary 风格保持一致, 只是 padding/字号小一档 */
.x-btn-sm {
  font-size: 13px;
  padding: 8px 14px;
}

/* === 评测记录 table === */
.x-dash-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  overflow: hidden;
}
.x-dash-table th {
  text-align: left;
  font-family: var(--x-font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.6px;
  color: var(--x-body-mid);
  text-transform: uppercase;
  padding: 12px 16px;
  border-bottom: 1px solid var(--x-hairline);
  background: var(--x-canvas-soft);
}
.x-dash-table td {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--x-ink);
  border-bottom: 1px solid var(--x-hairline);
}
.x-dash-table tbody tr:last-child td { border-bottom: 0; }
.x-dash-table tbody tr:hover td { background: var(--x-canvas-soft); }
.x-dash-cell-mute { color: var(--x-body-mid); }
.x-dash-cell-action { text-align: right; }
.x-dash-task-id {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  padding: 2px 6px;
  background: var(--x-canvas-soft);
  border-radius: 4px;
}

/* === 题数分档 pill (代替设计稿"分数 pill", 因后端没分数) === */
.x-count-pill {
  display: inline-flex;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-family: var(--x-font-mono);
  font-weight: 600;
  letter-spacing: 0.4px;
}
.x-count-pill.is-high {
  background: oklch(94% 0.04 142);
  color: oklch(45% 0.14 142);
}
.x-count-pill.is-mid {
  background: oklch(96% 0.04 80);
  color: oklch(45% 0.12 80);
}
.x-count-pill.is-low {
  background: var(--x-canvas-soft);
  color: var(--x-body-mid);
}

/* ============================================================
   MODAL —— 出题前配置 (题数 + 难度)
   teleport 到 body 后, scoped 仍然生效 (Vue 编译时给所有元素打 data-v-xxx)
   ============================================================ */
.x-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: oklch(0% 0 0 / 0.45);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.x-modal {
  width: 100%;
  max-width: 460px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 16px;
  box-shadow: 0 24px 60px oklch(0% 0 0 / 0.12);
  display: flex;
  flex-direction: column;
}

.x-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--x-hairline);
}
.x-modal-title {
  font-family: var(--x-font-display);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: var(--x-ink);
  margin: 0;
}
.x-modal-close {
  background: transparent;
  border: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 22px;
  line-height: 1;
  color: var(--x-body-mid);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.x-modal-close:hover {
  background: var(--x-canvas-soft);
  color: var(--x-ink);
}

.x-modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.x-modal-desc {
  font-size: 13px;
  line-height: 1.6;
  color: var(--x-body);
  margin: 0;
  padding: 12px 14px;
  background: var(--x-canvas-soft);
  border-radius: 8px;
  border-left: 3px solid var(--x-primary);
}

.x-modal-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-modal-label {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: var(--x-body-mid);
  margin: 0;
}
.x-modal-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
  padding: 8px 12px;
  background: var(--x-canvas-soft);
  border-radius: 8px;
}

/* === Segment control (题数 / 难度) === */
.x-modal-segments {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: 10px;
}
.x-segment {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: 0;
  border-radius: 7px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--x-body-mid);
  cursor: pointer;
  transition: background 0.15s, color 0.15s, box-shadow 0.15s;
}
.x-segment:hover:not(.is-active) {
  color: var(--x-ink);
}
.x-segment.is-active {
  background: var(--x-canvas);
  color: var(--x-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px oklch(0% 0 0 / 0.08);
}

/* 难度 segment 内含双行 (标题+ hint), 改成 vertical stack */
.x-segment-stacked {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
}
.x-segment-title {
  font-size: 13px;
  font-weight: 600;
}
.x-segment-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
}
.x-segment-stacked.is-active .x-segment-hint {
  color: var(--x-body);
}

.x-modal-foot {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid var(--x-hairline);
  background: var(--x-canvas-soft);
}

/* === Modal 进出过渡 === */
.x-modal-fade-enter-active,
.x-modal-fade-leave-active {
  transition: opacity 0.15s ease;
}
.x-modal-fade-enter-from,
.x-modal-fade-leave-to {
  opacity: 0;
}
.x-modal-fade-enter-active .x-modal,
.x-modal-fade-leave-active .x-modal {
  transition: transform 0.18s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.x-modal-fade-enter-from .x-modal {
  transform: translateY(8px) scale(0.98);
}
.x-modal-fade-leave-to .x-modal {
  transform: translateY(4px) scale(0.99);
}

/* === 响应式 === */
@media (max-width: 1024px) {
  .x-dash-stats { grid-template-columns: repeat(2, 1fr); }
  .x-dash-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .x-dash-stats,
  .x-dash-cards { grid-template-columns: 1fr; }
  .x-stat-num { font-size: 26px; }
  .x-dash-table th,
  .x-dash-table td { padding: 10px 12px; font-size: 12px; }
}

/* LEFT 进度 */
.x-quiz-progress {
  position: sticky;
  top: 80px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.x-quiz-progress-big {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 600;
  margin: 0;
  color: var(--x-ink);
}
.x-quiz-progress-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-quiz-progress-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  font-size: 12px;
  color: var(--x-body-mid);
  transition: background 0.12s;
}
.x-quiz-progress-list li:hover { background: rgba(0, 0, 0, 0.04); }
.x-quiz-progress-list li.is-current {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.x-quiz-progress-list li.is-done { color: var(--x-ink); }
.x-quiz-progress-num {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-family: var(--x-font-mono);
  flex-shrink: 0;
}
.x-quiz-progress-list li.is-done .x-quiz-progress-num { background: var(--x-primary); color: var(--x-on-primary); }
.x-quiz-progress-list li.is-current .x-quiz-progress-num { background: rgba(255, 255, 255, 0.2); }
.x-quiz-progress-name { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.x-quiz-progress-name small { font-size: 10px; opacity: 0.7; }

/* MIDDLE 当前题卡片 */
.x-quiz-main { min-width: 0; }
.x-quiz-card {
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
  padding: 24px;
  box-shadow: var(--x-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.x-quiz-stem {
  font-size: 16px;
  line-height: 1.7;
  color: var(--x-ink);
  margin: 0;
  white-space: pre-wrap;
}

/* 选项 */
.x-quiz-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-quiz-opt {
  text-align: left;
  padding: 12px 14px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-ink);
  font-size: 14px;
  line-height: 1.6;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s;
  font-family: var(--x-font-ui);
}
.x-quiz-opt:not(:disabled):hover { background: var(--x-canvas-soft); border-color: var(--x-primary); }
.x-quiz-opt.is-selected { background: var(--x-primary); color: var(--x-on-primary); border-color: var(--x-primary); }
.x-quiz-opt.is-correct { background: rgba(0, 160, 0, 0.12); border-color: #2c8a2c; color: #2c8a2c; }
.x-quiz-opt.is-correct.is-selected { background: #2c8a2c; color: white; }
.x-quiz-opt.is-locked:not(.is-selected):not(.is-correct) { opacity: 0.6; }

/* 短答题 */
.x-quiz-freeform {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.x-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas);
  color: var(--x-ink);
  font-size: 14px;
  font-family: var(--x-font-ui);
  resize: vertical;
}

/* 翻页 */
.x-quiz-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--x-hairline);
}
.x-quiz-nav-pos {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
}

/* 标准答案 (details) */
.x-quiz-answers {
  font-size: 13px;
  color: var(--x-body-mid);
  border-top: 1px dashed var(--x-hairline);
  padding-top: 12px;
}
.x-quiz-answers summary {
  cursor: pointer;
  color: var(--x-primary);
  font-weight: 500;
}
.x-quiz-answers p { margin: 8px 0 0; line-height: 1.6; }

/* ============================================================
   RIGHT 分析抽屉 (fixed-position drawer, 跟 PracticeView 一致)
   ============================================================ */
.x-quiz-drawer {
  position: fixed;
  top: 56px;
  right: 0;
  bottom: 0;
  width: 380px;
  background: var(--x-canvas-soft);
  border-left: 1px solid var(--x-hairline);
  transform: translateX(100%);
  transition: transform 0.25s ease;
  z-index: 50;
  padding: 24px 20px;
  box-sizing: border-box;
  overflow-y: auto;
}
.x-quiz-drawer.is-open { transform: translateX(0); }
.x-quiz-drawer-close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: transparent;
  border: 0;
  font-size: 14px;
  color: var(--x-body-mid);
  cursor: pointer;
  padding: 4px 8px;
}
.x-quiz-drawer-close:hover { color: var(--x-ink); }
.x-quiz-drawer-hint {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 40px 0;
  text-align: center;
  line-height: 1.6;
}
.x-quiz-drawer-error {
  font-size: 13px;
  color: #c13030;
  line-height: 1.6;
}
.x-quiz-drawer-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.x-quiz-drawer-analysis {
  font-size: 14px;
  line-height: 1.7;
  color: var(--x-ink);
}
.x-quiz-drawer-points ul {
  margin: 8px 0 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--x-ink);
  line-height: 1.7;
}

/* ── 判分结果条 ── */
.x-quiz-verdict {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--x-rounded-sm);
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 500;
}
.x-quiz-verdict.is-correct { background: var(--x-success-soft); color: var(--x-success); }
.x-quiz-verdict.is-wrong   { background: var(--x-error-soft);   color: var(--x-error); }
.x-quiz-verdict-mark {
  font-size: 18px;
  font-weight: 700;
  flex-shrink: 0;
}

/* ── 解题步骤 ── */
.x-quiz-steps {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--x-hairline);
}
.x-quiz-steps p { margin: 0 0 8px; }
.x-quiz-steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-quiz-step {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-soft);
  font-size: 13px;
  color: var(--x-ink);
  line-height: 1.55;
}
.x-quiz-step.is-key {
  background: var(--x-primary-soft);
}
.x-quiz-step-num {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  text-align: center;
  padding-top: 2px;
}
.x-quiz-step.is-key .x-quiz-step-num { color: var(--x-primary); }
.x-quiz-step-text { color: inherit; }
.x-quiz-step-tag {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  padding: 1px 6px;
  background: var(--x-canvas);
  border: 1px solid var(--x-primary);
  color: var(--x-primary);
  border-radius: var(--x-rounded-pill);
  align-self: center;
}

/* ── 误区 / 接下来 ── */
.x-quiz-pitfalls,
.x-quiz-next {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--x-hairline);
}
.x-quiz-pitfalls p,
.x-quiz-next p { margin: 0 0 6px; }
.x-quiz-pitfalls-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.x-quiz-pitfalls-list li {
  position: relative;
  padding: 4px 0 4px 18px;
  font-size: 13px;
  color: var(--x-body);
  line-height: 1.6;
}
.x-quiz-pitfalls-list li::before {
  content: '';
  display: none;
}
.x-quiz-next-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-quiz-next-list li {
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: var(--x-body);
  line-height: 1.6;
}
.x-quiz-next-num {
  color: var(--x-primary);
  font-family: var(--x-font-mono);
  font-size: 12px;
  flex-shrink: 0;
}

/* ── 知识点卡片 ── */
.x-quiz-knowledge {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--x-hairline);
}
.x-quiz-knowledge p { margin: 0 0 6px; }
.x-quiz-knowledge-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-quiz-knowledge-card {
  padding: 10px 12px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
  border-left: 2px solid var(--x-primary);
}
.x-quiz-knowledge-title {
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 4px;
}
.x-quiz-knowledge-desc {
  font-size: 12px;
  color: var(--x-body);
  line-height: 1.55;
  margin: 0;
}
</style>
