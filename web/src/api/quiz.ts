import http from './http'
import { ENDPOINTS } from './endpoints'
import type {
  QuestionType,
  StructuredQuestion,
  StructuredQuestionBatch,
} from '@/types/chat'

// ============================================================
// 题目生成 / 判分 HTTP 接口
//
//   后端流程:
//     1. POST /api/quiz/generate/        → 创建 Celery 任务, 返回 { task_id, ... }
//     2. GET  /api/quiz/tasks/<task_id>/ → 合并响应: state + questions (complete时) + error_message
//     3. POST /api/practice/analyze/     → 创建解析任务, 返回 { task_id, ... }
//     4. GET  /api/practice/tasks/<task_id>/ → 合并响应: state + analysis (complete时)
//
//   历史记录:
//     GET /api/quizzes/                  → 出题列表 (?subject=&state=)
//     GET /api/practice-analyses/        → 解析列表 (?subject=&state=&quiz_generation=)
// ============================================================

interface StartQuizOpts {
  subjectId: number       // MySubject.id
  count?: number          // 题数, 不传让后端决定
  extraPrompt?: string
}

// ─── 出题 ──────────────────────────────────────────────
export async function startQuizTask(
  opts: StartQuizOpts,
): Promise<{ data: { task_id: string } & Record<string, unknown> }> {
  return http.post(ENDPOINTS.QUIZ_GENERATE, {
    subject_id: opts.subjectId,
    count: opts.count,
    extra_prompt: opts.extraPrompt ?? '',
  })
}

// ─── 自动出题（按知识点 + 薄弱点） ─────────────────────────────
interface AutoQuizOpts {
  subjectId: number
  nodeId?: string
  nodeName?: string
  planId?: number
  count?: number
  extraPrompt?: string
}

export async function startAutoQuiz(
  opts: AutoQuizOpts,
): Promise<{ data: { task_id: string } & Record<string, unknown> }> {
  return http.post(ENDPOINTS.QUIZ_AUTO_GENERATE, {
    subject_id: opts.subjectId,
    node_id: opts.nodeId ?? '',
    node_name: opts.nodeName ?? '',
    plan_id: opts.planId,
    count: opts.count,
    extra_prompt: opts.extraPrompt ?? '',
  })
}

// GET /api/quiz/tasks/<task_id>/ — 合并响应: state + questions + error_message
export interface QuizTaskResponse {
  id: number
  task_id: string
  subject_id: number
  subject_name: string
  subject_display: string
  extra_prompt: string
  requested_count: number | null
  actual_count: number
  state: 'generating' | 'complete' | 'error' | string
  questions?: StructuredQuestionBatch  // state=complete 时存在
  error_message?: string               // state=error 时存在
  created_at: string
  completed_at: string | null
  ttl_sec: number
}

export async function getQuizTask(
  taskId: string,
): Promise<{ data: QuizTaskResponse }> {
  return http.get(ENDPOINTS.QUIZ_TASK(taskId))
}

// ─── 判分 (run_practice_analysis_task) ──────────────────────
interface AnalyzeOpts {
  quizTaskId: string
  questionIndex: number                                // 0-based, 出题 batch 的第几题
  userAnswer: string                                   // 用户选的答案 (A/B/C/D or 自由文本)
  mode?: 'with_answer' | 'without_answer'              // 后端两种模式, 默认 with_answer
  subjectDisplay?: string
  subjectCode?: string
}

export async function startPracticeAnalyze(
  opts: AnalyzeOpts,
): Promise<{ data: { task_id: string } }> {
  return http.post(ENDPOINTS.PRACTICE_ANALYZE, {
    quiz_task_id: opts.quizTaskId,
    question_index: opts.questionIndex,
    user_answer: opts.userAnswer,
    mode: opts.mode ?? 'with_answer',
    subject_display: opts.subjectDisplay,
    subject_code: opts.subjectCode,
  })
}

// GET /api/practice/tasks/<task_id>/ — 合并响应: state + analysis + error_message
export interface PracticeTaskResponse {
  task_id: string
  quiz_task_id?: string
  mode?: string
  persisted: boolean
  state: 'generating' | 'complete' | 'error' | string
  analysis?: PracticeResultPayload  // state=complete 时存在
  error_message?: string            // state=error 时存在
  ttl_sec: number
}

export async function getPracticeTask(
  taskId: string,
): Promise<{ data: PracticeTaskResponse }> {
  return http.get(ENDPOINTS.PRACTICE_TASK(taskId))
}

// ─── PracticeResultPayload (跟后端 practice_schema.py 对齐) ────────
//
//   完整字段:
//     mode                  必填 — "with_answer" / "without_answer"
//     phase                 必填 — e.g. "post_submit"
//     analysis             必填 — 摘要
//     key_knowledge_points  必填 — 3-5 个关键知识点
//     difficulty_assessment 必填 — 难度评估
//     result                可选 — 判分结果
//     steps                 可选 — 解题步骤
//     deep_analysis         可选 — 详细讲解
//     pitfalls              可选 — 常见误区
//     next_steps            可选 — 推荐后续学习
//     knowledge             可选 — 知识点 [{title, description}]
//     approach              可选 — only for without_answer 模式
//     hints                 可选 — only for without_answer 模式
export interface PracticeResultVerdict {
  verdict: 'correct' | 'wrong' | 'ungraded'
  is_correct: boolean
  user_answer: string
  correct_answer: string
  summary: string
}
export interface PracticeResultStep {
  text: string
  is_key: boolean
}
export interface PracticeResultKnowledge {
  title: string
  description: string
}
export interface PracticeResultPayload {
  mode: 'with_answer' | 'without_answer'
  phase: string
  analysis: string
  key_knowledge_points: string[]
  difficulty_assessment: 'easy' | 'medium' | 'hard'
  result?: PracticeResultVerdict
  steps?: PracticeResultStep[]
  deep_analysis?: string | null
  pitfalls?: string[]
  next_steps?: string[]
  knowledge?: PracticeResultKnowledge[]
  approach?: string | null
  hints?: string[]
}

// ─── 历史记录 ──────────────────────────────────────────
export interface QuizHistoryItem {
  id: number
  task_id: string
  subject_id: number
  subject_name: string
  subject_display: string
  extra_prompt: string
  requested_count: number | null
  actual_count: number
  node_id: string
  node_name: string
  plan_id: number | null
  state: string
  questions?: StructuredQuestionBatch
  error_message: string
  created_at: string
  completed_at: string | null
}

export async function fetchQuizHistory(params?: {
  subject?: string
  state?: string
}): Promise<{ data: QuizHistoryItem[] }> {
  return http.get(ENDPOINTS.QUIZZES_LIST, { params })
}

export interface PracticeAnalysisItem {
  id: number
  task_id: string
  quiz_task_id: string
  quiz_generation_id: number
  subject_id: number
  subject_name: string
  subject_display: string
  question_index: number
  mode: string
  user_answer: string
  state: string
  analysis: Record<string, unknown> | null
  error_message: string
  created_at: string
  completed_at: string | null
}

export async function fetchPracticeAnalyses(params?: {
  subject?: string
  state?: string
  quiz_generation?: string
}): Promise<{ data: PracticeAnalysisItem[] }> {
  return http.get(ENDPOINTS.PRACTICE_ANALYSES_LIST, { params })
}

// ============================================================
// 轮询 helper — 每隔 800ms 查一次, 直到 complete / error / 超时
//
//   POLL_TIMEOUT_MS=180s —— LLM 出 5 道题实测 30~90s, 偶发更慢（cybersecurity
//   等 token 量大的学科撞 90s 就报 timeout 放弃，但后端其实跑成功了）。
//   200s 给足余量。后端 record TTL 是 3600s，超过这个值再放弃也合理。
// ============================================================
const POLL_INTERVAL_MS = 800
const POLL_TIMEOUT_MS = 180_000

interface PollQuizOk {
  ok: true
  questions: StructuredQuestionBatch
}
interface PollQuizErr {
  ok: false
  error: string
}

export async function pollQuizUntilDone(
  taskId: string,
  onProgress?: (state: string) => void,
  abortSignal?: AbortSignal,
): Promise<PollQuizOk | PollQuizErr> {
  const start = Date.now()
  let notFoundStreak = 0
  while (Date.now() - start < POLL_TIMEOUT_MS) {
    if (abortSignal?.aborted) {
      return { ok: false, error: 'aborted' }
    }
    try {
      const { data } = await getQuizTask(taskId)
      // 后端 404 时 axios throw, 这里进不到. 仅当 response 成功 (2xx) 但缺 fields 时
      if (!data || (!data.state && data.error_message)) {
        return { ok: false, error: data.error_message ?? 'empty response' }
      }
      onProgress?.(data.state)
      if (data.state === 'complete' && data.questions) {
        return { ok: true, questions: data.questions }
      }
      if (data.state === 'error') {
        return { ok: false, error: data.error_message ?? '生成失败' }
      }
      notFoundStreak = 0
    } catch (err: any) {
      // 网络抖动 / 404 / 5xx 都会到这里
      const status = err?.response?.status
      if (status === 404) {
        // task id 已失效 (被清或从未存在) - 不要 retry 到天荒地老, 直接退出
        return { ok: false, error: 'not_found' }
      }
      // 其它错误: 短窗口内多次失败放弃, 减少无效请求
      notFoundStreak++
      if (notFoundStreak >= 5) {
        return { ok: false, error: 'repeated_failure' }
      }
    }
    if (abortSignal?.aborted) {
      return { ok: false, error: 'aborted' }
    }
    await new Promise<void>((r) => setTimeout(r, POLL_INTERVAL_MS))
  }
  return { ok: false, error: 'timeout' }
}

// ─── practice analyze 轮询 ──────────────────────────────────
interface PollPracticeOk {
  ok: true
  analysis: PracticeResultPayload
}
interface PollPracticeErr {
  ok: false
  error: string
}

export async function pollPracticeUntilDone(
  taskId: string,
  onProgress?: (state: string) => void,
  abortSignal?: AbortSignal,
): Promise<PollPracticeOk | PollPracticeErr> {
  const start = Date.now()
  while (Date.now() - start < POLL_TIMEOUT_MS) {
    if (abortSignal?.aborted) {
      return { ok: false, error: 'aborted' }
    }
    try {
      const { data } = await getPracticeTask(taskId)
      onProgress?.(data.state)
      if (data.state === 'complete' && data.analysis) {
        return { ok: true, analysis: data.analysis }
      }
      if (data.state === 'error') {
        return { ok: false, error: data.error_message ?? '解析失败' }
      }
    } catch {
      // 单次轮询失败 (网络抖动) → 重试下一次
    }
    if (abortSignal?.aborted) {
      return { ok: false, error: 'aborted' }
    }
    await new Promise<void>((r) => setTimeout(r, POLL_INTERVAL_MS))
  }
  return { ok: false, error: 'timeout' }
}

// ─── 类型守卫 ──────────────────────────────────────────
export function isChoice(q: StructuredQuestion): boolean {
  return q.question_type === 'choice' || q.question_type === 'true_false'
}
export function isShortAnswer(q: StructuredQuestion): boolean {
  return q.question_type === 'short_answer'
}

// ─── Active queue + mark-answered (后端驱动刷题) ──
export async function markQuizAnswered(payload: {
  quiz_id: number
  question_index: number
  correct: boolean | null
}): Promise<void> {
  await http.post(ENDPOINTS.QUIZ_MARK_ANSWERED, payload)
}

export type {
  QuestionType,
  StructuredQuestion,
  StructuredQuestionBatch,
}
