<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  createExamSession,
  fetchExamHistory,
  getExamSession,
  submitExamSession,
  type ExamSession,
  type McqQuestion,
  type EssayQuestion,
} from '@/api/exam'
import { useCurrentSubjectStore } from '@/stores/currentSubject'

// 类型守卫: MCQ 才有 options 字段, Essay 没有 —— 用 options 当 discriminator
function isMcq(q: McqQuestion | EssayQuestion): q is McqQuestion {
  return 'options' in q
}
import { getSubjectDisplayName } from '@/api/subjects'
import { listPlans, markPlanDone, type LearningPlan } from '@/api/plan'
import { IconSparkle, IconCheck, IconCross } from '@/components/icons'

type Phase = 'setup' | 'generating' | 'exam' | 'results'
const phase = ref<Phase>('setup')

const router = useRouter()
const route = useRoute()
const currentSubject = useCurrentSubjectStore()
const MCQ_OPTIONS = [0, 3, 5, 10] as const
const ESSAY_OPTIONS = [0, 1, 2, 3] as const

const searchQuery = ref('')
const mcqCount = ref<0 | 3 | 5 | 10>(5)
const qaCount = ref<0 | 1 | 2 | 3>(2)
const setupError = ref('')

/** 计划联动：从 PlanScheduleView "去执行"跳转时写入的 plan ID */
const linkedPlanId = ref<string | null>(null)
/** 待做试卷：从计划 API 获取的 exam 类型计划步骤 */
const pendingPlans = ref<LearningPlan[]>([])
const pendingLoading = ref(false)
/** 手动出题表单展开/收起 */
const showManualForm = ref(false)

onMounted(async () => {
  if (currentSubject.code) searchQuery.value = getSubjectDisplayName(currentSubject.code)

  // 计划联动：读取 plan_prompt 存入 linkedPlanPrompt，不自动生成
  const planPrompt = sessionStorage.getItem('aiteach.plan_prompt')
  if (planPrompt) {
    sessionStorage.removeItem('aiteach.plan_prompt')
    linkedPlanId.value = sessionStorage.getItem('aiteach.plan_id')
    if (linkedPlanId.value) sessionStorage.removeItem('aiteach.plan_id')
  }

  // 从链接跳转（如 /app/exam?session=19）加载已有试卷
  const sessionId = route.query.session
  if (sessionId) {
    const id = Number(sessionId)
    if (!Number.isNaN(id) && id > 0) {
      try {
        const { data } = await getExamSession(id)
        session.value = data
        if (data.status === 'completed') {
          phase.value = 'results'
        } else {
          mcqAnswers.value = { ...data.mcq_answers }
          essayAnswers.value = { ...data.essay_answers }
          phase.value = 'exam'
        }
        loadPendingPlans()
        loadHistory()
        return
      } catch { /* 加载失败则回退到 setup 页面 */ }
    }
  }

  loadPendingPlans()
  loadHistory()
})

/** 加载计划里的待做测评 */
async function loadPendingPlans() {
  if (!currentSubject.code) return
  pendingLoading.value = true
  try {
    const { data } = await listPlans(currentSubject.code, { step_type: 'exam' })
    // 过滤：排除已完成和已跳过的，只保留 pending / running / failed
    pendingPlans.value = data.filter(p => p.state !== 'success' && p.state !== 'skipped')
  } catch {
    pendingPlans.value = []
  } finally {
    pendingLoading.value = false
  }
}

/** 从待做计划卡片开始测评 */
async function startExamFromPlan(plan: LearningPlan) {
  const query = plan.memory?.step_desc?.trim() || plan.node_name
  if (!query) return
  searchQuery.value = query
  linkedPlanId.value = String(plan.id)
  setupError.value = ''
  generateError.value = ''
  phase.value = 'generating'
  try {
    const { data } = await createExamSession({ search_query: query, mcq_count: 5, qa_count: 2 })
    session.value = data
    mcqAnswers.value = {}
    essayAnswers.value = {}
    phase.value = 'exam'
    await nextTick()
    const paper = document.querySelector('.xe-paper-wrap')
    if (paper) paper.scrollTop = 0
  } catch (err: unknown) {
    generateError.value = err instanceof Error ? err.message : '题库生成失败，请稍后重试'
    phase.value = 'setup'
  }
}

const session = ref<ExamSession | null>(null)
const generateError = ref('')

async function handleStartExam() {
  const query = searchQuery.value.trim()
  if (!query) { setupError.value = '请输入考察范围关键词'; return }
  if (mcqCount.value + qaCount.value === 0) { setupError.value = '至少选一类题型'; return }
  setupError.value = ''
  generateError.value = ''
  phase.value = 'generating'
  try {
    const { data } = await createExamSession({ search_query: query, mcq_count: mcqCount.value, qa_count: qaCount.value })
    session.value = data
    mcqAnswers.value = {}
    essayAnswers.value = {}
    phase.value = 'exam'
    // 滚动到卷首
    await nextTick()
    const paper = document.querySelector('.xe-paper-wrap')
    if (paper) paper.scrollTop = 0
  } catch (err: unknown) {
    generateError.value = err instanceof Error ? err.message : '题库生成失败，请稍后重试'
    phase.value = 'setup'
  }
}

const mcqAnswers = ref<Record<string, string>>({})
const essayAnswers = ref<Record<string, string>>({})
const submitError = ref('')

type QuestionEntry = { type: 'mcq'; q: { id: number; question: string; options: Record<string, string>; answer: string }
  } | { type: 'essay'; q: { id: number; question: string } }

const allQuestions = computed<QuestionEntry[]>(() => {
  if (!session.value) return []
  return [
    ...session.value.multiple_choice.map((q): QuestionEntry => ({ type: 'mcq', q })),
    ...session.value.essay.map((q): QuestionEntry => ({ type: 'essay', q })),
  ]
})

const totalCount = computed(() => allQuestions.value.length)
const answeredCount = computed(() => {
  return allQuestions.value.filter(e => {
    const id = String(e.q.id)
    return e.type === 'mcq' ? !!mcqAnswers.value[id] : !!essayAnswers.value[id]?.trim()
  }).length
})
const progressPct = computed(() => totalCount.value > 0 ? Math.round(answeredCount.value / totalCount.value * 100) : 0)

/** 判断某题是否已作答 */
function isQuestionAnswered(e: QuestionEntry): boolean {
  const id = String(e.q.id)
  return e.type === 'mcq' ? !!mcqAnswers.value[id] : !!essayAnswers.value[id]?.trim()
}

// 分开的选择题列表（保持原始顺序，从 1 编号）
const mcqEntries = computed(() =>
  (session.value?.multiple_choice ?? []).map((q, i) => ({ q, num: i + 1 }))
)
const essayEntries = computed(() =>
  (session.value?.essay ?? []).map((q, i) => ({ q, num: i + 1 }))
)

const mcqDone = computed(() =>
  mcqEntries.value.filter(e => !!mcqAnswers.value[String(e.q.id)]).length
)
const essayDone = computed(() =>
  essayEntries.value.filter(e => !!essayAnswers.value[String(e.q.id)]?.trim()).length
)

function selectMcq(id: number, letter: string) { mcqAnswers.value[String(id)] = letter }

const submitting = ref(false)
const submitPhase = ref<'idle' | 'grading' | 'analyzing'>('idle')  // 交卷动画阶段

async function handleSubmit() {
  if (!session.value) return
  submitting.value = true
  submitPhase.value = 'grading'
  submitError.value = ''
  try {
    // 模拟评分阶段（短暂延迟做过渡）
    await new Promise(r => setTimeout(r, 600))
    submitPhase.value = 'analyzing'
    const { data } = await submitExamSession(session.value.id, { mcq_answers: mcqAnswers.value, essay_answers: essayAnswers.value })
    session.value = data
    submitPhase.value = 'idle'
    phase.value = 'results'
    loadHistory()
    loadPendingPlans() // 刷新待做列表
    // 关联了计划步骤 → 自动标记为完成
    if (linkedPlanId.value) {
      try { await markPlanDone(Number(linkedPlanId.value)) } catch { /* 静默 */ }
    }
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : '提交失败，请重试'
    submitPhase.value = 'idle'
  } finally {
    submitting.value = false
  }
}

const totalMcq = computed(() => session.value?.multiple_choice.length ?? 0)
const correctMcq = computed(() => session.value?.mcq_correct ?? 0)
const mcqPct = computed(() => totalMcq.value > 0 ? Math.round(correctMcq.value / totalMcq.value * 100) : 0)

function mcqResultClass(q: { id: number; answer: string }): 'correct' | 'wrong' | 'unanswered' {
  const ans = session.value?.mcq_answers[String(q.id)] ?? ''
  if (!ans) return 'unanswered'
  return ans.toUpperCase() === q.answer.toUpperCase() ? 'correct' : 'wrong'
}

/** 获取某道问答题的 AI 评分 */
function getEssayScore(qId: number) {
  return session.value?.analysis?.essay_scores?.find(s => s.id === qId) ?? null
}

/** 获取某道选择题的 AI 错题诊断 */
function getMcqDiag(qId: number) {
  return session.value?.analysis?.mcq_diagnostics?.find(d => d.id === qId) ?? null
}

const history = ref<ExamSession[]>([])
/** 仅已完成的试卷 */
const completedExams = computed(() => history.value.filter(h => h.status === 'completed'))
async function loadHistory() {
  try { const { data } = await fetchExamHistory(); history.value = data } catch { /* 静默 */ }
}

/** 人性化相对时间 */
function relativeDate(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小时前`
  const day = Math.floor(hr / 24)
  if (day < 7) return `${day} 天前`
  const wk = Math.floor(day / 7)
  if (wk < 4) return `${wk} 周前`
  return `${Math.floor(day / 30)} 个月前`
}

function viewHistorySession(h: ExamSession) {
  session.value = h
  if (h.status === 'completed') {
    phase.value = 'results'
  } else {
    mcqAnswers.value = { ...h.mcq_answers }
    essayAnswers.value = { ...h.essay_answers }
    phase.value = 'exam'
  }
}

function restartExam() { session.value = null; linkedPlanId.value = null; phase.value = 'setup'; loadPendingPlans() }

// ────── 试卷分页 ──────
const MCQ_PER_SHEET = 6   // 每张纸 6 道选择（左 3 + 右 3）
const ESSAY_PER_SHEET = 4 // 每张纸 4 道问答（左 2 + 右 2）

interface SheetItem { q: import('@/api/exam').McqQuestion | import('@/api/exam').EssayQuestion; num: number }

interface Sheet {
  type: 'mcq' | 'essay'
  pageNum: number
  totalPages: number
  left: SheetItem[]
  right: SheetItem[]
}

const sheets = computed<Sheet[]>(() => {
  const mcqs = session.value?.multiple_choice ?? []
  const essays = session.value?.essay ?? []
  const result: Sheet[] = []

  // 选择题分页
  for (let i = 0; i < mcqs.length; i += MCQ_PER_SHEET) {
    const chunk = mcqs.slice(i, i + MCQ_PER_SHEET)
    const mid = Math.ceil(chunk.length / 2)
    result.push({
      type: 'mcq',
      left: chunk.slice(0, mid).map((q, j) => ({ q, num: i + j + 1 })),
      right: chunk.slice(mid).map((q, j) => ({ q, num: i + mid + j + 1 })),
      pageNum: 0,
      totalPages: 0,
    })
  }

  // 问答题分页
  const essayBase = mcqs.length
  for (let i = 0; i < essays.length; i += ESSAY_PER_SHEET) {
    const chunk = essays.slice(i, i + ESSAY_PER_SHEET)
    const mid = Math.ceil(chunk.length / 2)
    result.push({
      type: 'essay',
      left: chunk.slice(0, mid).map((q, j) => ({ q, num: essayBase + i + j + 1 })),
      right: chunk.slice(mid).map((q, j) => ({ q, num: essayBase + i + mid + j + 1 })),
      pageNum: 0,
      totalPages: 0,
    })
  }

  result.forEach((s, i) => { s.pageNum = i + 1; s.totalPages = result.length })
  return result
})
</script>

<template>
  <div :class="['xe-root', { 'xe-embed': route.query.embed === '1' }]">

    <!-- ══════════════════════════════════════
         SETUP
    ══════════════════════════════════════ -->
    <div v-if="phase === 'setup'" class="xe-dash xe-fade-in">

      <!-- 顶部标题 + 手动出题按钮 -->
      <div class="xe-dash-head">
        <div>
          <p class="xe-eyebrow">ASSESSMENT · 综合测评</p>
          <h1 class="xe-dash-title">{{ getSubjectDisplayName(currentSubject.code) || '综合测评' }}</h1>
        </div>
        <button class="xe-dash-cta" @click="showManualForm = !showManualForm">
          <template v-if="showManualForm">收起</template>
          <template v-else><IconSparkle :size="14" /> 手动出题</template>
        </button>
      </div>

      <!-- 手动出题浮层 -->
      <div v-if="showManualForm" class="xe-manual xe-fade-in">
        <div class="xe-manual-card">
          <div class="xe-field">
            <label class="xe-label">考察范围</label>
            <input v-model="searchQuery" class="xe-input" type="text" placeholder="如：数据结构、计算机网络、深度学习" />
            <p class="xe-hint">多个知识点以逗号或顿号分隔</p>
          </div>
          <div class="xe-manual-row">
            <div class="xe-field">
              <label class="xe-label">选择题</label>
              <div class="xe-segs">
                <button v-for="n in MCQ_OPTIONS" :key="n" type="button"
                  class="xe-seg" :class="{ 'is-on': mcqCount === n }"
                  @click="mcqCount = n">{{ n === 0 ? '不出' : `${n} 题` }}</button>
              </div>
            </div>
            <div class="xe-field">
              <label class="xe-label">问答题</label>
              <div class="xe-segs">
                <button v-for="n in ESSAY_OPTIONS" :key="n" type="button"
                  class="xe-seg" :class="{ 'is-on': qaCount === n }"
                  @click="qaCount = n">{{ n === 0 ? '不出' : `${n} 题` }}</button>
              </div>
            </div>
          </div>
          <button class="xe-cta" @click="handleStartExam">
            <IconSparkle :size="15" />
            开始测评
          </button>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="setupError || generateError" class="xe-err-banner">
        {{ setupError || generateError }}
      </div>

      <!-- 待做试卷 -->
      <section class="xe-dash-section">
        <h2 class="xe-dash-section-title">待做试卷</h2>
        <div v-if="pendingLoading" class="xe-dash-empty">加载中…</div>
        <div v-else-if="pendingPlans.length === 0" class="xe-dash-empty">
          <p class="xe-dash-empty-text">暂无待做试卷</p>
          <button class="xe-dash-empty-link" @click="router.push({ name: 'app-plan' })">
            去学习计划中制定测评计划 →
          </button>
        </div>
        <div v-else class="xe-card-grid">
          <div
            v-for="plan in pendingPlans"
            :key="plan.id"
            class="xe-pcard"
            role="button"
            tabindex="0"
            @click="startExamFromPlan(plan)"
            @keydown.enter="startExamFromPlan(plan)"
          >
            <div class="xe-pcard-top">
              <span class="xe-pcard-type">📋 综合测评</span>
              <span v-if="plan.difficulty" class="xe-pcard-diff">难度 {{ plan.difficulty }}</span>
            </div>
            <p class="xe-pcard-topic">{{ plan.memory?.step_desc || plan.node_name }}</p>
            <div class="xe-pcard-meta">
              <span class="xe-pcard-node">{{ plan.node_name }}</span>
              <span class="xe-pcard-time">{{ plan.expected_minutes }}min</span>
            </div>
            <button class="xe-pcard-btn">开始测评</button>
          </div>
        </div>
      </section>

      <!-- 已完成试卷 -->
      <section class="xe-dash-section">
        <h2 class="xe-dash-section-title">已完成试卷</h2>
        <div v-if="completedExams.length === 0" class="xe-dash-empty">
          <p class="xe-dash-empty-text">尚未完成任何测评</p>
        </div>
        <div v-else class="xe-card-grid">
          <div
            v-for="h in completedExams"
            :key="h.id"
            class="xe-dcard"
            role="button"
            tabindex="0"
            @click="viewHistorySession(h)"
            @keydown.enter="viewHistorySession(h)"
          >
            <div class="xe-dcard-top">
              <span class="xe-dcard-pct" :class="(h.mcq_score ?? 0) >= 0.8 ? 'is-high' : (h.mcq_score ?? 0) >= 0.6 ? 'is-mid' : 'is-low'">
                {{ h.mcq_score !== null ? Math.round(h.mcq_score * 100) + '%' : '—' }}
              </span>
              <span class="xe-dcard-tag">{{ h.mcq_count }}选 {{ h.qa_count }}答</span>
            </div>
            <p class="xe-dcard-topic">{{ h.search_query }}</p>
            <div class="xe-dcard-meta">
              <span class="xe-dcard-date">{{ relativeDate(h.completed_at || h.created_at) }}</span>
              <span class="xe-dcard-arrow">查看 →</span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ══════════════════════════════════════
         GENERATING
    ══════════════════════════════════════ -->
    <div v-else-if="phase === 'generating'" class="xe-generating xe-fade-in">
      <div class="xe-gen-ring">
        <div class="xe-gen-ring-track"></div>
        <div class="xe-gen-ring-fill"></div>
        <div class="xe-gen-inner">
          <IconSparkle :size="24" />
        </div>
      </div>
      <p class="xe-gen-title">正在生成题库</p>
      <p class="xe-gen-sub">「{{ searchQuery }}」· 约需 15–60 秒</p>
    </div>

    <!-- ══════════════════════════════════════
         EXAM — 试卷模式
    ══════════════════════════════════════ -->
    <div v-else-if="phase === 'exam' && session" class="xe-exam xe-fade-in">
      <!-- 答题进度浮窗 -->
      <aside class="xe-prog-float">
        <!-- 选择题 -->
        <div v-if="mcqEntries.length > 0" class="xe-pf-block">
          <div class="xe-pf-head">
            <span class="xe-pf-label">选择题</span>
            <span class="xe-pf-tally">{{ mcqDone }}<span class="xe-pf-tally-sep">/</span>{{ mcqEntries.length }}</span>
          </div>
          <div class="xe-pf-grid">
            <div
              v-for="e in mcqEntries"
              :key="'pf-m-' + e.q.id"
              class="xe-pf-cell"
              :class="{ 'is-done': !!mcqAnswers[String(e.q.id)] }"
              :title="`选择题 #${e.num}${mcqAnswers[String(e.q.id)] ? ' ✓ 已答' : ' ✗ 未答'}`"
            >
              <span class="xe-pf-cell-num">{{ e.num }}</span>
            </div>
          </div>
        </div>
        <!-- 分界线 -->
        <div v-if="mcqEntries.length > 0 && essayEntries.length > 0" class="xe-pf-divider"></div>
        <!-- 问答题 -->
        <div v-if="essayEntries.length > 0" class="xe-pf-block">
          <div class="xe-pf-head">
            <span class="xe-pf-label">问答题</span>
            <span class="xe-pf-tally">{{ essayDone }}<span class="xe-pf-tally-sep">/</span>{{ essayEntries.length }}</span>
          </div>
          <div class="xe-pf-grid">
            <div
              v-for="e in essayEntries"
              :key="'pf-e-' + e.q.id"
              class="xe-pf-cell"
              :class="{ 'is-done': !!essayAnswers[String(e.q.id)]?.trim() }"
              :title="`问答题 #${e.num}${essayAnswers[String(e.q.id)]?.trim() ? ' ✓ 已答' : ' ✗ 未答'}`"
            >
              <span class="xe-pf-cell-num">{{ e.num }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 顶栏 -->
      <div class="xe-topbar">
        <div class="xe-topbar-left">
          <span class="xe-topbar-subject">{{ session.search_query }}</span>
          <div class="xe-topbar-progress">
            <div class="xe-progress-track">
              <div class="xe-progress-fill" :style="{ width: progressPct + '%' }"></div>
            </div>
            <span class="xe-progress-label">{{ answeredCount }}/{{ totalCount }}</span>
          </div>
        </div>
        <button class="xe-submit-btn" :disabled="submitting" @click="handleSubmit">
          <template v-if="submitPhase === 'grading'">正在批改…</template>
          <template v-else-if="submitPhase === 'analyzing'">智能体分析中…</template>
          <template v-else>交卷</template>
        </button>
      </div>

      <!-- 试卷滚动区域 -->
      <div class="xe-paper-wrap">

        <!-- 每张试卷 -->
        <article v-for="(sheet, si) in sheets" :key="si" class="xe-paper">

          <!-- 卷头 -->
          <header class="xe-paper-head">
            <div class="xe-paper-head-left">
              <span class="xe-paper-head-subject">{{ session.search_query }}</span>
              <span v-if="sheet.type === 'mcq'" class="xe-paper-head-type">选择题</span>
              <span v-else class="xe-paper-head-type">问答题</span>
            </div>
            <div class="xe-paper-head-right">
              <h1 class="xe-paper-title">综合测评试卷</h1>
              <span class="xe-paper-page-num">第 {{ sheet.pageNum }} 页 / 共 {{ sheet.totalPages }} 页</span>
            </div>
          </header>

          <!-- 对开正文 -->
          <div class="xe-paper-spread">

            <!-- 左页 -->
            <div class="xe-paper-page xe-paper-page--left">
              <!-- 选择题 -->
              <template v-if="sheet.type === 'mcq'">
                <div v-for="item in sheet.left" :key="'mcq-' + item.q.id"
                  class="xe-paper-q"
                  :class="{ 'is-answered': !!mcqAnswers[String(item.q.id)] }">
                  <div class="xe-paper-q-num">{{ item.num }}.</div>
                  <div class="xe-paper-q-body">
                    <p class="xe-paper-q-stem">{{ item.q.question }}</p>
                    <div class="xe-paper-opts">
                      <button v-for="letter in (['A','B','C','D'] as const)" :key="letter"
                        class="xe-paper-opt"
                        :class="{ 'is-sel': mcqAnswers[String(item.q.id)] === letter }"
                        @click="selectMcq(item.q.id, letter)">
                        <span class="xe-paper-opt-letter">{{ letter }}.</span>
                        <span class="xe-paper-opt-text">{{ isMcq(item.q) ? item.q.options[letter] : '' }}</span>
                        <span v-if="mcqAnswers[String(item.q.id)] === letter" class="xe-paper-opt-mark">
                          <IconCheck :size="13" />
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </template>
              <!-- 问答题 -->
              <template v-else>
                <div v-for="item in sheet.left" :key="'essay-' + item.q.id"
                  class="xe-paper-q"
                  :class="{ 'is-answered': !!essayAnswers[String(item.q.id)]?.trim() }">
                  <div class="xe-paper-q-num">{{ item.num }}.</div>
                  <div class="xe-paper-q-body">
                    <p class="xe-paper-q-stem">{{ item.q.question }}</p>
                    <textarea v-model="essayAnswers[String(item.q.id)]"
                      class="xe-paper-textarea" rows="5" placeholder="在此作答…" />
                  </div>
                </div>
              </template>
            </div>

            <!-- 中缝 -->
            <div class="xe-paper-gutter">
              <div class="xe-paper-gutter-line"></div>
            </div>

            <!-- 右页 -->
            <div class="xe-paper-page xe-paper-page--right">
              <template v-if="sheet.type === 'mcq'">
                <div v-for="item in sheet.right" :key="'mcq-' + item.q.id"
                  class="xe-paper-q"
                  :class="{ 'is-answered': !!mcqAnswers[String(item.q.id)] }">
                  <div class="xe-paper-q-num">{{ item.num }}.</div>
                  <div class="xe-paper-q-body">
                    <p class="xe-paper-q-stem">{{ item.q.question }}</p>
                    <div class="xe-paper-opts">
                      <button v-for="letter in (['A','B','C','D'] as const)" :key="letter"
                        class="xe-paper-opt"
                        :class="{ 'is-sel': mcqAnswers[String(item.q.id)] === letter }"
                        @click="selectMcq(item.q.id, letter)">
                        <span class="xe-paper-opt-letter">{{ letter }}.</span>
                        <span class="xe-paper-opt-text">{{ isMcq(item.q) ? item.q.options[letter] : '' }}</span>
                        <span v-if="mcqAnswers[String(item.q.id)] === letter" class="xe-paper-opt-mark">
                          <IconCheck :size="13" />
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else>
                <div v-for="item in sheet.right" :key="'essay-' + item.q.id"
                  class="xe-paper-q"
                  :class="{ 'is-answered': !!essayAnswers[String(item.q.id)]?.trim() }">
                  <div class="xe-paper-q-num">{{ item.num }}.</div>
                  <div class="xe-paper-q-body">
                    <p class="xe-paper-q-stem">{{ item.q.question }}</p>
                    <textarea v-model="essayAnswers[String(item.q.id)]"
                      class="xe-paper-textarea" rows="5" placeholder="在此作答…" />
                  </div>
                </div>
              </template>
            </div>
          </div>
        </article>

        <!-- 卷尾：交卷（最后一页之后） -->
        <div class="xe-paper-foot">
          <p v-if="submitError" class="xe-err">{{ submitError }}</p>
          <div class="xe-paper-foot-row">
            <p class="xe-paper-foot-hint">
              <template v-if="answeredCount === totalCount">✓ 全部作答完毕，可以交卷</template>
              <template v-else>还有 {{ totalCount - answeredCount }} 题未作答</template>
            </p>
            <button class="xe-submit-btn" :disabled="submitting" @click="handleSubmit">
              <template v-if="submitPhase === 'grading'">正在批改…</template>
              <template v-else-if="submitPhase === 'analyzing'">智能体分析中…</template>
              <template v-else>交卷</template>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════
         RESULTS
    ══════════════════════════════════════ -->
    <div v-else-if="phase === 'results' && session" class="xe-results xe-fade-in">
      <!-- 成绩英雄区 -->
      <div class="xe-score-hero">
        <div class="xe-score-ring-wrap">
          <div class="xe-score-ring" :style="{ '--pct': mcqPct }">
            <div class="xe-score-ring-hole">
              <span class="xe-score-val">{{ mcqPct }}</span>
              <span class="xe-score-unit">%</span>
            </div>
          </div>
        </div>
        <div class="xe-score-text">
          <p class="xe-eyebrow">选择题得分</p>
          <p class="xe-score-headline">
            {{ correctMcq }} / {{ totalMcq }}<span class="xe-score-sub"> 题正确</span>
          </p>
          <p class="xe-score-range">{{ session.search_query }}</p>
          <button class="xe-restart" @click="restartExam">再测一次</button>
        </div>
      </div>

      <div class="xe-review-wrap">
        <!-- 选择题解析 -->
        <section v-if="session.multiple_choice.length > 0" class="xe-section">
          <h2 class="xe-section-title">选择题解析</h2>
          <div class="xe-review-list">
            <div v-for="(q, i) in session.multiple_choice" :key="q.id"
              class="xe-review-card" :class="`is-${mcqResultClass(q)}`">
              <div class="xe-rc-head">
                <span class="xe-rc-index">{{ i + 1 }}</span>
                <span class="xe-rc-verdict" :class="`is-${mcqResultClass(q)}`">
                  <IconCheck v-if="mcqResultClass(q) === 'correct'" :size="11" />
                  <IconCross v-else-if="mcqResultClass(q) === 'wrong'" :size="11" />
                  {{ mcqResultClass(q) === 'correct' ? '正确' : mcqResultClass(q) === 'wrong' ? '错误' : '未作答' }}
                </span>
              </div>
              <p class="xe-rc-stem">{{ q.question }}</p>
              <div class="xe-rc-opts">
                <div v-for="letter in (['A','B','C','D'] as const)" :key="letter"
                  class="xe-rc-opt"
                  :class="{
                    'is-ans': letter.toUpperCase() === q.answer.toUpperCase(),
                    'is-usr': session!.mcq_answers[String(q.id)]?.toUpperCase() === letter.toUpperCase()
                      && letter.toUpperCase() !== q.answer.toUpperCase(),
                  }">
                  <span class="xe-rc-letter">{{ letter }}</span>
                  <span>{{ q.options[letter] }}</span>
                </div>
              </div>
              <!-- Dify 题目解析 -->
              <div class="xe-rc-explain">
                <span class="xe-rc-explain-tag">解析</span>
                {{ q.explanation }}
              </div>
              <!-- AI 错因诊断（仅错题） -->
              <div v-if="getMcqDiag(q.id)" class="xe-rc-diag">
                <div class="xe-rc-diag-head">
                  <span class="xe-rc-explain-tag" style="color: var(--x-accent-amber-deep)">AI 诊断</span>
                </div>
                <div class="xe-rc-diag-row">
                  <span class="xe-rc-diag-badge is-wrong">{{ getMcqDiag(q.id)!.user_pick }}</span>
                  <span class="xe-rc-diag-arrow">→</span>
                  <span class="xe-rc-diag-badge is-corr">{{ getMcqDiag(q.id)!.correct }}</span>
                </div>
                <p class="xe-rc-diag-why">{{ getMcqDiag(q.id)!.why_wrong }}</p>
              </div>
            </div>
          </div>
        </section>

        <!-- 问答题参考答案（含 AI 评分） -->
        <section v-if="session.essay.length > 0" class="xe-section">
          <h2 class="xe-section-title">问答题参考答案</h2>
          <div class="xe-essay-list">
            <div v-for="(q, i) in session.essay" :key="q.id" class="xe-essay-card">
              <div class="xe-essay-q">
                <span class="xe-essay-idx">{{ i + 1 }}</span>
                <p class="xe-essay-stem">{{ q.question }}</p>
                <!-- AI 评分徽章 -->
                <span v-if="getEssayScore(q.id)" class="xe-essay-score-badge"
                  :class="getEssayScore(q.id)!.score >= 75 ? 'is-high' : getEssayScore(q.id)!.score >= 50 ? 'is-mid' : 'is-low'">
                  {{ getEssayScore(q.id)!.score }} 分
                </span>
              </div>
              <div class="xe-essay-cols">
                <div class="xe-essay-col">
                  <p class="xe-col-label">你的作答</p>
                  <p class="xe-col-body" :class="{ 'is-empty': !session!.essay_answers[String(q.id)] }">
                    {{ session!.essay_answers[String(q.id)] || '（未作答）' }}
                  </p>
                </div>
                <div class="xe-essay-col is-ref">
                  <p class="xe-col-label">参考答案</p>
                  <p class="xe-col-body">{{ q.answer }}</p>
                  <ul v-if="q.scoring_points.length" class="xe-points">
                    <li v-for="(pt, pi) in q.scoring_points" :key="pi">{{ pt }}</li>
                  </ul>
                </div>
              </div>
              <!-- AI 反馈 -->
              <div v-if="getEssayScore(q.id)" class="xe-essay-feedback">
                <span class="xe-essay-feedback-tag">AI 点评</span>
                {{ getEssayScore(q.id)!.feedback }}
              </div>
            </div>
          </div>
        </section>

        <!-- ═════════════ AI 综合评估 ═════════════ -->
        <section v-if="session.analysis?.overall" class="xe-section">
          <h2 class="xe-section-title xe-section-title--ai">
            <IconSparkle :size="15" />
            AI 综合评估
          </h2>

          <!-- 问答题评分总览 -->
          <div v-if="session.analysis.essay_scores?.length" class="xe-analysis-block">
            <div class="xe-essay-score-grid">
              <div v-for="es in session.analysis.essay_scores" :key="'es-' + es.id" class="xe-essay-score-chip"
                :class="es.score >= 75 ? 'is-high' : es.score >= 50 ? 'is-mid' : 'is-low'">
                <span class="xe-essay-score-chip-num">问答 #{{ es.id }}</span>
                <span class="xe-essay-score-chip-val">{{ es.score }}</span>
                <span class="xe-essay-score-chip-unit">分</span>
              </div>
            </div>
          </div>

          <!-- 整体评估 -->
          <div class="xe-overall">
            <p class="xe-overall-summary">{{ session.analysis.overall.summary }}</p>

            <div class="xe-overall-grid">
              <div class="xe-overall-col">
                <h4 class="xe-overall-label xe-overall-label--good">✓ 优势</h4>
                <ul class="xe-overall-list">
                  <li v-for="(s, si) in session.analysis.overall.strengths" :key="'str-' + si">{{ s }}</li>
                </ul>
              </div>
              <div class="xe-overall-col">
                <h4 class="xe-overall-label xe-overall-label--warn">⚠ 薄弱点</h4>
                <ul class="xe-overall-list">
                  <li v-for="(w, wi) in session.analysis.overall.weaknesses" :key="'wk-' + wi">{{ w }}</li>
                </ul>
              </div>
            </div>

            <div class="xe-overall-recos">
              <h4 class="xe-overall-label">📋 学习建议</h4>
              <ol class="xe-overall-reco-list">
                <li v-for="(r, ri) in session.analysis.overall.recommendations" :key="'rec-' + ri">{{ r }}</li>
              </ol>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 提交分析遮罩——根级，不受页面滚动影响 -->
    <div v-if="submitting" class="xe-submit-overlay">
      <div class="xe-submit-dialog">
        <div class="xe-submit-spinner">
          <div class="xe-submit-spinner-ring"></div>
          <svg class="xe-submit-spinner-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-2.135-4.27a1 1 0 0 1 1.342-1.342l4.27 2.135A2 2 0 0 0 13.364 10L18 5.636"/>
            <path d="M5.636 18 10 13.364"/>
          </svg>
        </div>
        <p class="xe-submit-dialog-title">
          <template v-if="submitPhase === 'grading'">正在批改选择题…</template>
          <template v-else-if="submitPhase === 'analyzing'">AI 智能体正在分析你的作答</template>
        </p>
        <p class="xe-submit-dialog-sub">
          <template v-if="submitPhase === 'grading'">核对答案中，请稍候</template>
          <template v-else-if="submitPhase === 'analyzing'">正在逐题诊断错因、评估问答质量、生成学习建议…</template>
        </p>
        <div class="xe-submit-dots">
          <span class="xe-submit-dot" :class="{ 'is-active': submitPhase === 'grading' || submitPhase === 'analyzing' }"></span>
          <span class="xe-submit-dot" :class="{ 'is-active': submitPhase === 'analyzing' }"></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
   入场动画
   ============================================================ */
@keyframes xe-fadein {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.xe-fade-in { animation: xe-fadein 0.28s cubic-bezier(0.2, 0, 0, 1) both; }

/* ============================================================
   根容器
   ============================================================ */
.xe-root {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  color: var(--x-ink);
  display: flex;
  flex-direction: column;
}

/* 公共 eyebrow */
.xe-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--x-body-mid);
  margin: 0;
}

/* ============================================================
   DASHBOARD — 测评首页
   ============================================================ */
.xe-dash {
  flex: 1;
  padding: 48px 48px 60px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 36px;
}

/* 顶部标题行 */
.xe-dash-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.xe-dash-title {
  font-family: var(--x-font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: var(--x-ink);
  margin: 4px 0 0;
}
.xe-dash-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline-strong);
  border-radius: 10px;
  font-family: var(--x-font-ui);
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.xe-dash-cta:hover {
  background: var(--x-canvas-soft);
  border-color: var(--x-primary);
}

/* 手动出题浮层 */
.xe-manual {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 28px;
}
.xe-manual-card {
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.xe-manual-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

/* 错误横幅 */
.xe-err-banner {
  font-size: 13px;
  color: var(--x-error);
  padding: 10px 16px;
  background: var(--x-error-soft);
  border-radius: 8px;
  margin: 0;
}
.xe-err {
  font-size: 12px;
  color: var(--x-error);
  padding: 8px 12px;
  background: var(--x-error-soft);
  border-radius: 6px;
  margin: 0;
}

/* 分区 */
.xe-dash-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.xe-dash-section-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.xe-dash-empty {
  padding: 32px 20px;
  text-align: center;
  background: var(--x-canvas-soft);
  border: 1px dashed var(--x-hairline-strong);
  border-radius: 10px;
}
.xe-dash-empty-text {
  font-size: 14px;
  color: var(--x-body-mid);
  margin: 0 0 12px;
}
.xe-dash-empty-link {
  display: inline-block;
  font-size: 13px;
  color: var(--x-primary);
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: none;
}
.xe-dash-empty-link:hover { text-decoration: underline; }

/* 卡片网格 */
.xe-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

/* ── 待做试卷卡片 ── */
.xe-pcard {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}
.xe-pcard:hover {
  border-color: var(--x-primary);
  box-shadow: 0 4px 16px var(--x-blue-alpha-06);
  transform: translateY(-2px);
}
.xe-pcard-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.xe-pcard-type {
  font-size: 12px;
  font-weight: 500;
  color: var(--x-body-mid);
}
.xe-pcard-diff {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  background: var(--x-canvas-soft);
  padding: 2px 8px;
  border-radius: 999px;
}
.xe-pcard-topic {
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
  line-height: 1.4;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-pcard-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}
.xe-pcard-node {
  font-size: 12px;
  color: var(--x-body-mid);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.xe-pcard-time {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-mute);
  flex-shrink: 0;
}
.xe-pcard-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: none;
  border-radius: 8px;
  font-family: var(--x-font-ui);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s;
  align-self: flex-start;
}
.xe-pcard-btn:hover { filter: brightness(1.08); }

/* ── 已完成试卷卡片 ── */
.xe-dcard {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s;
}
.xe-dcard:hover {
  border-color: var(--x-primary);
  box-shadow: 0 4px 16px var(--x-blue-alpha-06);
  transform: translateY(-2px);
}
.xe-dcard-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.xe-dcard-pct {
  font-family: var(--x-font-display);
  font-size: 24px;
  font-weight: 700;
}
.xe-dcard-pct.is-high { color: var(--x-success); }
.xe-dcard-pct.is-mid  { color: var(--x-accent-amber-deep); }
.xe-dcard-pct.is-low  { color: var(--x-error); }
.xe-dcard-tag {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-mute);
  background: var(--x-canvas-soft);
  padding: 3px 10px;
  border-radius: 999px;
}
.xe-dcard-topic {
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
  line-height: 1.4;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-dcard-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.xe-dcard-date {
  font-size: 12px;
  color: var(--x-body-mid);
}
.xe-dcard-arrow {
  font-size: 12px;
  font-weight: 500;
  color: var(--x-primary);
}

/* 保留表单控件样式（手动出题复用） */
.xe-field { display: flex; flex-direction: column; gap: 8px; }
.xe-label {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--x-body-mid);
  margin: 0;
}
.xe-hint { font-size: 11px; color: var(--x-mute); margin: 0; }

.xe-input {
  padding: 10px 14px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: 8px;
  background: var(--x-canvas);
  color: var(--x-ink);
  font-size: 14px;
  font-family: var(--x-font-ui);
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.xe-input:focus {
  outline: none;
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
}

/* 数量选择器（手动出题复用） */
.xe-segs {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: 10px;
}
.xe-seg {
  flex: 1;
  padding: 8px 10px;
  background: transparent;
  border: none;
  border-radius: 7px;
  font-family: var(--x-font-ui);
  font-size: 13px;
  font-weight: 500;
  color: var(--x-body-mid);
  cursor: pointer;
  transition: background 0.14s, color 0.14s, box-shadow 0.14s;
}
.xe-seg:hover:not(.is-on) { color: var(--x-ink); }
.xe-seg.is-on {
  background: var(--x-canvas);
  color: var(--x-primary);
  font-weight: 600;
  box-shadow: 0 1px 4px oklch(0% 0 0 / 0.08);
}

.xe-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 13px;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: none;
  border-radius: 10px;
  font-family: var(--x-font-ui);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s, transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 4px 14px var(--x-blue-alpha-30);
  align-self: flex-start;
}
.xe-cta:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px var(--x-blue-alpha-30);
}
.xe-cta:active { transform: translateY(0); }

/* ============================================================
   GENERATING
   ============================================================ */
.xe-generating {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 60px 24px;
}

.xe-gen-ring {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.xe-gen-ring-track {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid var(--x-hairline);
}
.xe-gen-ring-fill {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: var(--x-primary);
  border-right-color: var(--x-primary);
  animation: xe-spin 1s linear infinite;
}
@keyframes xe-spin { to { transform: rotate(360deg); } }
.xe-gen-inner {
  color: var(--x-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.xe-gen-title {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.xe-gen-sub {
  font-size: 14px;
  color: var(--x-body-mid);
  margin: -8px 0 0;
  text-align: center;
}

/* ============================================================
   EXAM — 试卷模式
   ============================================================ */
.xe-exam {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
}

/* 顶栏 */
.xe-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 32px;
  border-bottom: 1px solid var(--x-hairline);
  background: var(--x-canvas-card);
  flex-shrink: 0;
  gap: 24px;
  z-index: 2;
}
.xe-topbar-left {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
  min-width: 0;
}
.xe-topbar-subject {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}
.xe-topbar-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.xe-progress-track {
  flex: 1;
  height: 4px;
  background: var(--x-canvas-mid);
  border-radius: 2px;
  overflow: hidden;
  min-width: 60px;
  max-width: 200px;
}
.xe-progress-fill {
  height: 100%;
  background: var(--x-primary);
  border-radius: 2px;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.xe-progress-label {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
  white-space: nowrap;
}

.xe-submit-btn {
  padding: 8px 20px;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: none;
  border-radius: 8px;
  font-family: var(--x-font-ui);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  transition: filter 0.15s;
}
.xe-submit-btn:not(:disabled):hover { filter: brightness(1.08); }
.xe-submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* ────── 答题进度浮窗 ────── */
.xe-prog-float {
  position: fixed;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 50;
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 4px 20px oklch(0% 0 0 / 0.06);
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 130px;
  user-select: none;
}
.xe-pf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.xe-pf-label {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--x-body-mid);
}
.xe-pf-tally {
  font-family: var(--x-font-mono);
  font-size: 16px;
  font-weight: 700;
  color: var(--x-ink);
  line-height: 1;
}
.xe-pf-tally-sep {
  font-weight: 400;
  color: var(--x-mute);
  margin: 0 1px;
}
.xe-pf-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 5px;
}
.xe-pf-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  background: var(--x-canvas-mid);
  transition: background 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s;
  cursor: default;
}
.xe-pf-cell.is-done {
  background: var(--x-success);
  box-shadow: 0 1px 3px oklch(55% 0.18 155 / 0.22);
}
.xe-pf-cell-num {
  font-family: var(--x-font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--x-mute);
  line-height: 1;
  transition: color 0.25s;
}
.xe-pf-cell.is-done .xe-pf-cell-num {
  color: #fff;
}

.xe-pf-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.xe-pf-divider {
  height: 1px;
  background: var(--x-hairline);
  margin: 2px 0;
}

/* 试卷滚动容器 */
.xe-paper-wrap {
  flex: 1;
  overflow-y: auto;
  background:
    radial-gradient(ellipse at 50% 0%, var(--x-canvas-tint) 0%, transparent 60%),
    var(--x-canvas-mid);
  padding: 32px 28px 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 36px;
}

/* 每张试卷 */
.xe-paper {
  width: 100%;
  max-width: 1200px;
  min-height: calc(100vh - 180px);
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 4px;
  box-shadow:
    0 2px 12px oklch(0% 0 0 / 0.05),
    0 6px 24px oklch(0% 0 0 / 0.03);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

/* 卷头：左右分布 */
.xe-paper-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 28px 40px 20px;
  margin: 0 36px;
  border-bottom: 1.5px solid var(--x-ink);
}
@media (max-width: 700px) {
  .xe-paper-head { margin: 0 16px; padding: 20px 16px 16px; flex-direction: column; align-items: flex-start; gap: 8px; }
}
.xe-paper-head-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.xe-paper-head-subject {
  font-size: 13px;
  color: var(--x-body-mid);
}
.xe-paper-head-type {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--x-primary);
  background: var(--x-primary-soft);
  padding: 2px 10px;
  border-radius: 999px;
  align-self: flex-start;
}
.xe-paper-head-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.xe-paper-title {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 3px;
  color: var(--x-ink);
  margin: 0;
}
.xe-paper-page-num {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-mute);
  letter-spacing: 0.08em;
}

/* ═════════════ 对开双栏 ═════════════ */
.xe-paper-spread {
  display: grid;
  grid-template-columns: 1fr 0px 1fr;
  flex: 1;
}
@media (max-width: 780px) {
  .xe-paper-spread { grid-template-columns: 1fr; }
}

/* 左页 / 右页 */
.xe-paper-page {
  padding: 28px 32px 24px;
}
@media (max-width: 780px) {
  .xe-paper-page { padding: 16px 16px 16px; }
}
.xe-paper-page--left  { padding-right: 20px; }
.xe-paper-page--right { padding-left: 20px; }

/* 中缝 */
.xe-paper-gutter {
  position: relative;
  display: flex;
  justify-content: center;
  z-index: 1;
}
.xe-paper-gutter-line {
  width: 1px;
  background:
    linear-gradient(
      to bottom,
      transparent 0%,
      var(--x-hairline-strong) 6%,
      var(--x-hairline) 50%,
      var(--x-hairline-strong) 94%,
      transparent 100%
    );
}
@media (max-width: 780px) {
  .xe-paper-gutter { display: none; }
}

/* 每题行 */
.xe-paper-q {
  display: flex;
  gap: 10px;
  padding: 16px 0;
  border-bottom: 1px dashed var(--x-hairline);
}
.xe-paper-q:last-child { border-bottom: none; }
.xe-paper-q-num {
  font-family: var(--x-font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--x-body-mid);
  min-width: 26px;
  flex-shrink: 0;
  padding-top: 1px;
}
.xe-paper-q-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.xe-paper-q-stem {
  font-size: 14px;
  line-height: 1.7;
  color: var(--x-ink);
  margin: 0;
  font-weight: 400;
}

/* 选择题选项 */
.xe-paper-opts {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.xe-paper-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--x-hairline);
  border-radius: 6px;
  background: var(--x-canvas);
  cursor: pointer;
  text-align: left;
  width: 100%;
  font-family: var(--x-font-ui);
  font-size: 13px;
  color: var(--x-ink);
  line-height: 1.5;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.12s;
}
.xe-paper-opt:hover {
  border-color: var(--x-primary);
  box-shadow: 0 1px 4px var(--x-blue-alpha-06);
}
.xe-paper-opt.is-sel {
  background: var(--x-primary);
  border-color: var(--x-primary);
  color: var(--x-on-primary);
}
.xe-paper-opt-letter {
  font-family: var(--x-font-mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--x-body-mid);
  flex-shrink: 0;
  transition: color 0.15s;
}
.xe-paper-opt:hover .xe-paper-opt-letter { color: var(--x-primary); }
.xe-paper-opt.is-sel .xe-paper-opt-letter { color: var(--x-on-primary); opacity: 0.8; }
.xe-paper-opt-text { flex: 1; }
.xe-paper-opt-mark {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

/* 问答题文本框 */
.xe-paper-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: 6px;
  background: var(--x-canvas);
  color: var(--x-ink);
  font-family: var(--x-font-ui);
  font-size: 13px;
  line-height: 1.65;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
  min-height: 90px;
}
.xe-paper-textarea:focus {
  outline: none;
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
}
.xe-paper-textarea::placeholder { color: var(--x-mute); font-size: 12px; }

/* 卷尾（所有纸张之后） */
.xe-paper-foot {
  width: 100%;
  max-width: 1200px;
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 8px;
  padding: 20px 40px;
  box-shadow: 0 2px 8px oklch(0% 0 0 / 0.04);
}
@media (max-width: 700px) {
  .xe-paper-foot { padding: 16px 20px; border-radius: 0; }
}
.xe-paper-foot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.xe-paper-foot-hint {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
}
.xe-paper-foot .xe-submit-btn {
  padding: 10px 28px;
  font-size: 14px;
}

/* ============================================================
   提交分析遮罩
   ============================================================ */
.xe-submit-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: oklch(0% 0 0 / 0.35);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: xe-fadein 0.2s ease both;
}
.xe-submit-dialog {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 16px;
  padding: 40px 48px;
  text-align: center;
  max-width: 380px;
  width: calc(100vw - 48px);
  box-shadow: 0 8px 40px oklch(0% 0 0 / 0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.xe-submit-spinner {
  position: relative;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}
.xe-submit-spinner-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid var(--x-hairline);
  border-top-color: var(--x-primary);
  animation: xe-spin 0.8s linear infinite;
}
.xe-submit-spinner-icon {
  position: relative;
  z-index: 1;
  color: var(--x-primary);
}
.xe-submit-dialog-title {
  font-family: var(--x-font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.xe-submit-dialog-sub {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: -8px 0 0;
  line-height: 1.6;
}
.xe-submit-dots {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.xe-submit-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--x-canvas-mid);
  transition: background 0.3s, transform 0.3s;
}
.xe-submit-dot.is-active {
  background: var(--x-primary);
  animation: xe-dot-pulse 0.8s ease-in-out infinite;
}
.xe-submit-dot:nth-child(2).is-active { animation-delay: 0.15s; }
@keyframes xe-dot-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.6); opacity: 0.4; }
}

/* ============================================================
   RESULTS
   ============================================================ */
.xe-results { display: flex; flex-direction: column; }

/* 成绩英雄 */
.xe-score-hero {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 40px 48px;
  background: linear-gradient(135deg, var(--x-canvas-tint) 0%, var(--x-canvas-soft) 100%);
  border-bottom: 1px solid var(--x-hairline);
}
@media (max-width: 600px) {
  .xe-score-hero { flex-direction: column; align-items: flex-start; padding: 28px 24px; gap: 24px; }
}

.xe-score-ring-wrap { flex-shrink: 0; }
.xe-score-ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: conic-gradient(
    var(--x-primary) calc(var(--pct) * 1%),
    var(--x-canvas-mid) 0%
  );
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.xe-score-ring-hole {
  width: 86px;
  height: 86px;
  border-radius: 50%;
  background: var(--x-canvas);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}
.xe-score-hero .xe-score-ring-hole { background: var(--x-canvas-tint); }
.xe-score-val {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--x-primary);
  line-height: 1;
}
.xe-score-unit {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
}

.xe-score-text { display: flex; flex-direction: column; gap: 8px; }
.xe-score-headline {
  font-family: var(--x-font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.5px;
  color: var(--x-ink);
  margin: 4px 0 0;
  line-height: 1.1;
}
.xe-score-sub { font-size: 16px; font-weight: 400; color: var(--x-body-mid); }
.xe-score-range { font-size: 13px; color: var(--x-body-mid); margin: 0; font-style: italic; }
.xe-restart {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 7px 16px;
  border: 1px solid var(--x-hairline-strong);
  border-radius: 8px;
  background: var(--x-canvas);
  color: var(--x-ink);
  font-family: var(--x-font-ui);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.14s, border-color 0.14s;
  align-self: flex-start;
}
.xe-restart:hover { background: var(--x-canvas-soft); border-color: var(--x-primary); }

/* 解析区域 */
.xe-review-wrap { padding: 36px 48px 64px; }
@media (max-width: 680px) { .xe-review-wrap { padding: 24px 20px 48px; } }

.xe-section { margin-bottom: 44px; }
.xe-section-title {
  font-family: var(--x-font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0 0 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--x-hairline);
}

/* 选择题解析列表 */
.xe-review-list { display: flex; flex-direction: column; gap: 16px; }
.xe-review-card {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-left-width: 3px;
}
.xe-review-card.is-correct   { border-left-color: var(--x-success); }
.xe-review-card.is-wrong      { border-left-color: var(--x-error); }
.xe-review-card.is-unanswered { border-left-color: var(--x-mute); }

.xe-rc-head { display: flex; align-items: center; gap: 10px; }
.xe-rc-index {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--x-canvas-mid);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--x-font-mono); font-size: 11px; color: var(--x-body-mid); flex-shrink: 0;
}
.xe-rc-verdict {
  font-family: var(--x-font-mono); font-size: 11px; letter-spacing: 0.05em;
  padding: 2px 10px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 4px;
}
.xe-rc-verdict.is-correct   { background: var(--x-success-soft); color: var(--x-success); }
.xe-rc-verdict.is-wrong      { background: var(--x-error-soft);   color: var(--x-error); }
.xe-rc-verdict.is-unanswered { background: var(--x-canvas-mid);   color: var(--x-mute); }

.xe-rc-stem { font-size: 14px; line-height: 1.65; color: var(--x-ink); margin: 0; }

.xe-rc-opts { display: flex; flex-direction: column; gap: 5px; }
.xe-rc-opt {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 12px; border-radius: 7px;
  font-size: 13px; color: var(--x-body); line-height: 1.5;
  background: var(--x-canvas-soft);
}
.xe-rc-opt.is-ans { background: var(--x-success-soft); color: var(--x-success); font-weight: 500; }
.xe-rc-opt.is-usr { background: var(--x-error-soft);   color: var(--x-error); text-decoration: line-through; }
.xe-rc-letter { font-family: var(--x-font-mono); font-size: 11px; flex-shrink: 0; width: 14px; opacity: 0.6; }

.xe-rc-explain {
  font-size: 13px; line-height: 1.65; color: var(--x-body);
  padding: 10px 14px; background: var(--x-canvas-soft);
  border-radius: 7px; border-left: 2px solid var(--x-primary-soft);
}
.xe-rc-explain-tag {
  font-family: var(--x-font-mono); font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--x-primary); margin-right: 6px; font-style: normal;
}

/* AI 错因诊断（嵌入选择题卡片内） */
.xe-rc-diag {
  margin-top: 4px;
  padding: 10px 14px;
  background: var(--x-canvas-tint);
  border-radius: 7px;
  border: 1px dashed var(--x-accent-amber);
}
.xe-rc-diag-head {
  margin-bottom: 6px;
}
.xe-rc-diag-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}
.xe-rc-diag-badge {
  font-family: var(--x-font-mono);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}
.xe-rc-diag-badge.is-wrong { background: var(--x-error-soft); color: var(--x-error); }
.xe-rc-diag-badge.is-corr  { background: var(--x-success-soft); color: var(--x-success); }
.xe-rc-diag-arrow { color: var(--x-mute); }
.xe-rc-diag-why {
  font-size: 12px;
  line-height: 1.6;
  color: var(--x-body);
  margin: 0;
}

/* 问答题卡 */
.xe-essay-list { display: flex; flex-direction: column; gap: 20px; }
.xe-essay-card {
  background: var(--x-canvas-card); border: 1px solid var(--x-hairline);
  border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 16px;
}
.xe-essay-q { display: flex; align-items: flex-start; gap: 14px; }
.xe-essay-idx {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--x-canvas-mid);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--x-font-mono); font-size: 11px; color: var(--x-body-mid); flex-shrink: 0; margin-top: 2px;
}
.xe-essay-stem { font-size: 15px; line-height: 1.65; color: var(--x-ink); margin: 0; }
.xe-essay-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 640px) { .xe-essay-cols { grid-template-columns: 1fr; } }
.xe-essay-col {
  padding: 14px; border-radius: 8px;
  background: var(--x-canvas-soft); border: 1px solid var(--x-hairline);
  display: flex; flex-direction: column; gap: 6px;
}
.xe-essay-col.is-ref { background: var(--x-success-soft); border-color: rgba(16,185,129,0.2); }
.xe-col-label {
  font-family: var(--x-font-mono); font-size: 10px; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--x-body-mid); margin: 0;
}
.xe-essay-col.is-ref .xe-col-label { color: var(--x-success); }
.xe-col-body { font-size: 13px; line-height: 1.65; color: var(--x-ink); margin: 0; white-space: pre-wrap; }
.xe-col-body.is-empty { color: var(--x-mute); font-style: italic; }
.xe-points {
  padding-left: 18px; margin: 4px 0 0;
  display: flex; flex-direction: column; gap: 3px;
  font-size: 12px; color: var(--x-success); line-height: 1.5;
}

/* ============================================================
   AI 智能分析
   ============================================================ */
.xe-section-title--ai {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--x-primary);
}

/* 问答题 AI 评分徽章 */
.xe-essay-score-badge {
  flex-shrink: 0;
  margin-left: auto;
  font-family: var(--x-font-mono);
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
}
.xe-essay-score-badge.is-high { background: var(--x-success-soft); color: var(--x-success); }
.xe-essay-score-badge.is-mid  { background: var(--x-accent-amber); color: #92400e; }
.xe-essay-score-badge.is-low  { background: var(--x-error-soft); color: var(--x-error); }

/* 问答题 AI 反馈 */
.xe-essay-feedback {
  font-size: 13px;
  line-height: 1.65;
  color: var(--x-body);
  padding: 10px 14px;
  background: var(--x-canvas-soft);
  border-radius: 7px;
  border-left: 2px solid var(--x-primary-soft);
}
.xe-essay-feedback-tag {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--x-primary);
  margin-right: 6px;
}

/* 分析块 */
.xe-analysis-block { margin-bottom: 32px; }
.xe-analysis-block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--x-hairline);
}

/* 错题诊断卡片 */
.xe-diag-card {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-left: 3px solid var(--x-error);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 10px;
}
.xe-diag-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}
.xe-diag-idx {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-error);
  background: var(--x-error-soft);
  padding: 2px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}
.xe-diag-q { font-size: 14px; line-height: 1.55; color: var(--x-ink); }
.xe-diag-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  font-size: 13px;
}
.xe-diag-label { color: var(--x-body-mid); min-width: 56px; flex-shrink: 0; }
.xe-diag-val {
  font-family: var(--x-font-mono);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.xe-diag-val.is-wrong { background: var(--x-error-soft); color: var(--x-error); }
.xe-diag-val.is-corr  { background: var(--x-success-soft); color: var(--x-success); }
.xe-diag-why {
  font-size: 13px;
  line-height: 1.65;
  color: var(--x-body);
  padding: 10px 12px;
  background: var(--x-canvas-soft);
  border-radius: 6px;
  margin: 8px 0 0;
}

/* 问答题评分总览 */
.xe-essay-score-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.xe-essay-score-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  font-family: var(--x-font-mono);
}
.xe-essay-score-chip.is-high { background: var(--x-success-soft); }
.xe-essay-score-chip.is-mid  { background: var(--x-canvas-soft); border: 1px solid var(--x-accent-amber); }
.xe-essay-score-chip.is-low  { background: var(--x-error-soft); }
.xe-essay-score-chip-num { font-size: 11px; color: var(--x-body-mid); }
.xe-essay-score-chip-val { font-size: 18px; font-weight: 700; color: var(--x-ink); }
.xe-essay-score-chip-unit { font-size: 11px; color: var(--x-body-mid); }

/* 整体评估 */
.xe-overall {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: 12px;
  padding: 24px;
}
.xe-overall-summary {
  font-size: 14px;
  line-height: 1.75;
  color: var(--x-ink);
  margin: 0 0 24px;
  padding: 14px 18px;
  background: var(--x-canvas-soft);
  border-radius: 8px;
  border-left: 3px solid var(--x-primary);
}
.xe-overall-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
@media (max-width: 600px) { .xe-overall-grid { grid-template-columns: 1fr; } }
.xe-overall-label {
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 10px;
}
.xe-overall-label--good { color: var(--x-success); }
.xe-overall-label--warn { color: var(--x-accent-amber-deep); }
.xe-overall-list {
  padding-left: 18px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--x-body);
}
.xe-overall-recos {
  padding-top: 20px;
  border-top: 1px solid var(--x-hairline);
}
.xe-overall-reco-list {
  padding-left: 20px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--x-body);
}

/* ══════════════ 嵌入模式（对话气泡内，独立风格） ══════════════ */
.xe-embed {
  background: #f0f4ff !important;
  --x-primary: #6366f1 !important;
  --x-on-primary: #fff !important;
}
.xe-embed .xe-exam { padding: 0 !important; }
.xe-embed .xe-paper-wrap {
  padding: 0 !important; background: transparent !important;
  display: flex; flex-direction: column; gap: 12px;
}
.xe-embed .xe-paper {
  margin: 0 !important; border-radius: 14px !important;
  background: #fff !important;
  box-shadow: 0 2px 8px rgba(99,102,241,0.08) !important;
  border: 1px solid rgba(99,102,241,0.06) !important;
}
.xe-embed .xe-paper-head {
  margin: 0 !important; padding: 16px 18px 12px !important;
  border-bottom: 1px solid #eef2ff !important;
  flex-direction: row !important; align-items: center !important; gap: 10px !important;
}
.xe-embed .xe-paper-head-subject { font-size: 12px !important; color: #6366f1 !important; background: #eef2ff; padding: 2px 10px; border-radius: 20px; }
.xe-embed .xe-paper-head-type { font-size: 12px !important; color: #8b8bf0 !important; }
.xe-embed .xe-paper-title { font-size: 15px !important; color: #1e1b4b !important; }
.xe-embed .xe-paper-page-num { display: none !important; }
.xe-embed .xe-paper-spread { grid-template-columns: 1fr !important; }
.xe-embed .xe-paper-page { padding: 16px 18px !important; }
.xe-embed .xe-paper-gutter { display: none !important; }
.xe-embed .xe-paper-q-stem { font-size: 14px !important; color: #1e1b4b !important; font-weight: 500 !important; }
.xe-embed .xe-paper-opts { gap: 6px !important; }
.xe-embed .xe-paper-opt {
  padding: 10px 14px !important; font-size: 13px !important;
  border: 1.5px solid #e0e7ff !important; border-radius: 10px !important;
  background: #fafbff !important; transition: all 0.15s !important;
}
.xe-embed .xe-paper-opt:hover { border-color: #818cf8 !important; background: #eef2ff !important; }
.xe-embed .xe-paper-opt.is-sel {
  border-color: #6366f1 !important; background: #eef2ff !important;
  color: #4338ca !important; font-weight: 500 !important;
}
.xe-embed .xe-paper-textarea {
  font-size: 13px !important; min-height: 60px !important;
  border: 1.5px solid #e0e7ff !important; border-radius: 10px !important;
  background: #fafbff !important;
}
.xe-embed .xe-paper-textarea:focus { border-color: #6366f1 !important; }
.xe-embed .xe-paper-foot {
  padding: 14px 18px !important; border-top: 1px solid #eef2ff !important;
  background: #fafbff !important;
}
.xe-embed .xe-submit-btn {
  padding: 10px 24px !important; font-size: 14px !important;
  background: #6366f1 !important; border-radius: 10px !important;
}
.xe-embed .xe-submit-btn:hover { background: #4f46e5 !important; }
.xe-embed .xe-float-bar { display: none !important; }
.xe-embed .xe-paper-foot-hint { font-size: 12px !important; color: #8b8bf0 !important; }
</style>
