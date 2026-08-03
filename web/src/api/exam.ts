import http from './http'
import { ENDPOINTS } from './endpoints'

// ────── 类型定义 ──────

export interface McqQuestion {
  id: number
  question: string
  options: { A: string; B: string; C: string; D: string }
  answer: string
  explanation: string
}

export interface EssayQuestion {
  id: number
  question: string
  answer: string
  scoring_points: string[]
}

export type ExamStatus = 'active' | 'completed'

/** AI 分析 —— 问答题评分 */
export interface EssayScore {
  id: number
  score: number
  feedback: string
}

/** AI 分析 —— 选择题错题诊断 */
export interface McqDiagnostic {
  id: number
  question: string
  user_pick: string
  correct: string
  why_wrong: string
}

/** AI 分析 —— 整体评估 */
export interface ExamOverall {
  summary: string
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
}

/** AI 分析完整结果 */
export interface ExamAnalysis {
  essay_scores: EssayScore[]
  mcq_diagnostics: McqDiagnostic[]
  overall: ExamOverall
}

export interface ExamSession {
  id: number
  search_query: string
  mcq_count: number
  qa_count: number
  status: ExamStatus
  multiple_choice: McqQuestion[]
  essay: EssayQuestion[]
  mcq_answers: Record<string, string>
  essay_answers: Record<string, string>
  mcq_score: number | null
  mcq_correct: number
  analysis: ExamAnalysis | null
  created_at: string
  completed_at: string | null
}

export interface CreateExamPayload {
  search_query: string
  mcq_count: number
  qa_count: number
}

export interface SubmitExamPayload {
  mcq_answers: Record<string, string>
  essay_answers: Record<string, string>
}

// ────── API 函数 ──────

export function createExamSession(payload: CreateExamPayload) {
  // Dify 工作流同步出题，最长可能需要 90s，单独放大 timeout
  return http.post<ExamSession>(ENDPOINTS.EXAM_SESSIONS, payload, { timeout: 150000 })
}

export function submitExamSession(id: number, payload: SubmitExamPayload) {
  // 交卷后会触发 AI 分析，可能耗时 20-40s，放大超时
  return http.post<ExamSession>(ENDPOINTS.EXAM_SESSION_SUBMIT(id), payload, { timeout: 120000 })
}

export function fetchExamHistory() {
  return http.get<ExamSession[]>(ENDPOINTS.EXAM_HISTORY)
}

export function getExamSession(id: number) {
  return http.get<ExamSession>(ENDPOINTS.EXAM_SESSION(id))
}
