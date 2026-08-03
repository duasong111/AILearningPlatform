import http from './http'
import { ENDPOINTS } from './endpoints'
import * as recordMocks from './mocks/learningRecords'
import * as reportMocks from './mocks/reports'
import type {
  ExerciseRecord,
  KnowledgeGraph,
  ResourceHistoryItem,
  RichWeeklyReport,
  SubjectCode,
  WeeklyReport,
} from '@/types/learning'

// ============================================================
// 学习时长记录 (StudySession)
//   前端每 1 分钟调一次 accumulateStudyTime, 后端按天/类型聚合
// ============================================================

export type StudyActivityType = 'chat' | 'reading' | 'video' | 'quiz' | 'exam'

export interface StudySession {
  id: number
  user: number
  subject: number
  subject_name: string
  activity_type: StudyActivityType
  date: string
  duration_minutes: number
  created_at: string
  updated_at: string
}

export interface StudySessionSummary {
  date: string
  activity_type: StudyActivityType
  total_minutes: number
}

export interface StudySessionTotal {
  total_minutes: number
  by_type: Record<string, number>
}

export interface StudySessionFilters {
  subject?: string
  activity_type?: StudyActivityType
  start?: string
  end?: string
}

/** POST /api/learning/study-sessions/accumulate/ — 累加学习时长 (前端每分钟调一次) */
export function accumulateStudyTime(payload: {
  subject: string
  activity_type: StudyActivityType
  minutes?: number
}): Promise<{ data: StudySession }> {
  return http.post(ENDPOINTS.STUDY_SESSION_ACCUMULATE, payload)
}

/** GET /api/learning/study-sessions/ — 查询学习记录 (支持时间筛选) */
export function listStudySessions(filters?: StudySessionFilters): Promise<{ data: StudySession[] }> {
  return http.get(ENDPOINTS.STUDY_SESSIONS, { params: filters })
}

/** GET /api/learning/study-sessions/summary/ — 按天聚合 */
export function getStudySessionSummary(filters?: StudySessionFilters): Promise<{ data: StudySessionSummary[] }> {
  return http.get(ENDPOINTS.STUDY_SESSION_SUMMARY, { params: filters })
}

/** GET /api/learning/study-sessions/total/ — 总时长 (按类型分) */
export function getStudySessionTotal(filters?: StudySessionFilters): Promise<{ data: StudySessionTotal }> {
  return http.get(ENDPOINTS.STUDY_SESSION_TOTAL, { params: filters })
}

// ------------------------------------------------------------
// 学习时间双维度聚合 —— 给 /app/home 看板用
//   GET /api/learning/study-time/?days=30
//   返回 { by_day: [{date, minutes}], by_subject: [{code, minutes}] }
// ------------------------------------------------------------
export interface StudyTimeByDay    { date: string; minutes: number }
export interface StudyTimeBySubject { code: string;  minutes: number }
export interface StudyTimeAggregate {
  by_day:     StudyTimeByDay[]
  by_subject: StudyTimeBySubject[]
}

export function getStudyTime(days = 30): Promise<{ data: StudyTimeAggregate }> {
  return http.get(ENDPOINTS.STUDY_TIME_AGGREGATE, { params: { days } })
}

export function listResourceHistory(): Promise<{
  data: { items: ResourceHistoryItem[] }
}> {
  // 后端聚合: GET /api/learning/resource-history/
  // 目前后端先返空 list, 等"打开书/视频上报"接通后即可填数据
  return http.get<{ items: ResourceHistoryItem[] }>(ENDPOINTS.RESOURCE_HISTORY)
}

// ------------------------------------------------------------
// 学习记录 - 习题记录 (真数据接口)
// ------------------------------------------------------------
export function listExerciseRecords(): Promise<{
  data: { items: ExerciseRecord[]; total: number }
}> {
  // 后端聚合: GET /api/learning/exercises/
  // 内部聚合 quiz_practiceanalysisrecord + quiz_examsession
  return http.get<{ items: ExerciseRecord[]; total: number }>(ENDPOINTS.EXERCISE_RECORDS)
}

// ------------------------------------------------------------
// 学习记录 - 周报 (精简版, 仍走 mock —— 后端没实现精简 shape)
// ------------------------------------------------------------
export function listReports(): Promise<{
  data: { items: WeeklyReport[] }
}> {
  // TODO: replace with http.get<{items: WeeklyReport[]}>(ENDPOINTS.REPORTS)
  return recordMocks.fetchReports()
}

// ------------------------------------------------------------
// 知识图谱 - 按学科加载 (后端: GET /api/knowledge-graph/<code>/)
// ------------------------------------------------------------
export async function getKnowledgeGraph(code: SubjectCode): Promise<{ data: KnowledgeGraph }> {
  const { data } = await http.get<KnowledgeGraph>(ENDPOINTS.KNOWLEDGE_GRAPH(code))
  return { data }
}

// ------------------------------------------------------------
// PDF 导出 - 周报 (stub)
//   后端落地后这里 POST /api/learning/reports/<id>/export/ 返 blob, 触发下载.
// ------------------------------------------------------------
export async function exportReportPDF(_reportId: number): Promise<{ data: Blob }> {
  // TODO: replace with http.post<Blob>(`${ENDPOINTS.REPORTS}${_reportId}/export/`, null, { responseType: 'blob' })
  await new Promise<void>((r) => setTimeout(r, 200))
  // 显式抛错让 view 走 catch -> toast "TODO" 提示
  throw new Error('PDF export endpoint pending — backend not yet implemented')
}

// ------------------------------------------------------------
// 富周报 (ReportsView 专用) —— 真数据接口
//   后端 GET /api/learning/reports/                                  → RichWeeklyReport[]
//   后端 GET /api/learning/reports/<id>/  (id = 周一距 epoch 天数) → 单条 RichWeeklyReport
// ------------------------------------------------------------
export function listRichReports(): Promise<{ data: RichWeeklyReport[] }> {
  return http.get<RichWeeklyReport[]>(ENDPOINTS.REPORTS)
}

export function getRichReport(id: number): Promise<{ data: RichWeeklyReport | null }> {
  return http.get<RichWeeklyReport>(`${ENDPOINTS.REPORTS}${id}/`)
}

// ------------------------------------------------------------
// 读书会话 (打开书事件上报) —— 后端落 BookReadingSession 表
// ------------------------------------------------------------
export interface BookReadingSession {
  id: number
  book_id: number
  book_title: string
  subject: string
  opened_at: string
  last_heartbeat_at: string | null
  closed_at: string | null
  duration_min: number
  status: 'open' | 'closed'
}

/** POST /api/learning/reading-sessions/open/ —— 用户点开书时调. bookCode 是 BOOKS_CONFIG[].id */
export function openReadingSession(
  bookCode: string,
): Promise<{ data: BookReadingSession }> {
  return http.post<BookReadingSession>(ENDPOINTS.READING_SESSION_OPEN, { book_code: bookCode })
}

/** POST /api/learning/reading-sessions/heartbeat/ —— 周期心跳累加 duration_min */
export function heartbeatReadingSession(
  readingSessionId: number,
): Promise<{ data: BookReadingSession }> {
  return http.post<BookReadingSession>(ENDPOINTS.READING_SESSION_HEARTBEAT, {
    reading_session_id: readingSessionId,
  })
}

/** POST /api/learning/reading-sessions/close/ —— 关书 (留待 UI 接入 onUnmount) */
export function closeReadingSession(
  readingSessionId: number,
): Promise<{ data: BookReadingSession }> {
  return http.post<BookReadingSession>(ENDPOINTS.READING_SESSION_CLOSE, {
    reading_session_id: readingSessionId,
  })
}

export default {
  accumulateStudyTime,
  listStudySessions,
  getStudySessionSummary,
  getStudySessionTotal,
  listResourceHistory,
  listExerciseRecords,
  listReports,
  listRichReports,
  getRichReport,
  getKnowledgeGraph,
  exportReportPDF,
}
