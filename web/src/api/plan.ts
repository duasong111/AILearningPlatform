// 计划相关 API
import http from './http'
import type { SubjectCode } from '@/types/learning'
import { ENDPOINTS } from './endpoints'
import { listMySubjects } from './subjects'

// ── 类型定义 ─────────────────────────────────────────

export type PlanState = 'pending' | 'running' | 'success' | 'failed' | 'skipped'
export type PlanTargetAgent = 'chat' | 'profile' | 'practice' | 'plan' | 'video'
export type PlanActionType = 'study' | 'practice' | 'chat' | 'video'
export type PlanStepType = 'reading' | 'video' | 'quiz' | 'qa' | 'chapter_quiz' | 'exam'
export type PlanDifficulty = 'low' | 'medium' | 'high'

// memory 字段的轻量类型（plan_node step metadata）
export interface PlanMemory {
  step_label?: string
  step_type?: PlanStepType
  step_order?: number
  step_desc?: string
  summary?: string
  tag?: string
  skip_reason?: string
  skipped_at?: string
  [key: string]: any
}

// PlanItem: 来自计划节点的数据结构 (用于视频课等场景)
export interface PlanItem {
  type: string
  name: string
  desc?: string
  tag?: string
  /** PlanItem 唯一 id (后端在生成计划时给每个 item 分配) */
  id?: string
  /** 绑定到 VideoCourseRecord.id (生成时由后端回填) */
  video_record_id?: number
  /** OpenMAIC 业务 uuid (生成完成后由后端回填) */
  video_uuid?: string
  /** 'generating' | 'complete' | 'error' */
  video_state?: string
}

// 后端 LearningPlan 模型
//   一条 plan = 一个 (节点 × 步骤) 的完整执行记录
//   包含 节点信息、步骤信息、状态、时间
export interface LearningPlan {
  id: number
  subject_id: number
  conversation_id: number | null
  subject_name?: string
  subject_display?: string
  target_agent: PlanTargetAgent
  // ── 节点信息 ──
  node_id: string
  node_name: string
  node_type: string
  order: number
  // ── 步骤信息 ──
  action_type: PlanActionType
  difficulty: number  // 节点难度 1-5
  // ── 整体难度 ──
  plan_difficulty: PlanDifficulty
  // ── 记忆/元数据 ──
  memory: PlanMemory
  // ── 状态 ──
  state: PlanState
  completed: boolean
  // ── 时间 ──
  expected_minutes: number
  expected_completion_time: string | null
  actual_completion_time: string | null
  create_time: string
  success_time: string | null
  updated_at: string
}

// ── 列表查询参数 ─────────────────────────────────────

export interface PlanListFilters {
  node_name?: string
  step_type?: PlanStepType
  state?: PlanState
  target_agent?: PlanTargetAgent
  action_type?: PlanActionType
  tag?: string
}

// ── API 函数 ─────────────────────────────────────────

// GET /api/plans/?subject=<id> — 获取当前课程的计划列表
//   后端 subject filter 按 Subject.id（数字）过滤，不是 code
//   接受 SubjectCode，内部先查 /api/subjects/mine/ 拿到 id
export async function listPlans(
  subjectCode: SubjectCode,
  filters?: PlanListFilters,
): Promise<{ data: LearningPlan[] }> {
  const { data: mySubjects } = await listMySubjects()
  const subj = mySubjects.find((s) => s.name === subjectCode)
  if (!subj) {
    return { data: [] }
  }
  const { data } = await http.get<LearningPlan[]>(ENDPOINTS.PLANS, {
    params: { subject: subj.id, ...filters },
  })
  return { data: Array.isArray(data) ? data : [] }
}

// GET /api/plans/<id>/ — 单个 plan 详情
export async function getPlan(id: number): Promise<{ data: LearningPlan }> {
  const { data } = await http.get<LearningPlan>(ENDPOINTS.PLAN_DETAIL(id))
  return { data }
}

// POST /api/plans/ — 创建一个新的 plan
export async function createPlan(payload: {
  subject_name: string
  target_agent: PlanTargetAgent
  plan_difficulty?: PlanDifficulty
  node_id?: string
  node_name?: string
  node_type?: string
  action_type?: PlanActionType
  difficulty?: number
  expected_minutes?: number
  memory?: PlanMemory
  state?: PlanState
}): Promise<{ data: LearningPlan }> {
  const { data } = await http.post<LearningPlan>(ENDPOINTS.PLANS, payload)
  return { data }
}

// PATCH /api/plans/<id>/ — 更新 plan
export async function updatePlan(
  id: number,
  payload: {
    state?: PlanState
    plan_difficulty?: PlanDifficulty
    memory?: PlanMemory
  },
): Promise<{ data: LearningPlan }> {
  const { data } = await http.patch<LearningPlan>(ENDPOINTS.PLAN_DETAIL(id), payload)
  return { data }
}

// DELETE /api/plans/<id>/ — 删除 plan
export async function deletePlan(id: number): Promise<void> {
  await http.delete(ENDPOINTS.PLAN_DETAIL(id))
}

// POST /api/plans/<id>/complete/ — 标记 plan 为完成
//   可选 body: { actual_completion_time: "ISO 8601" }
export async function markPlanDone(
  id: number,
  body?: { actual_completion_time?: string },
): Promise<{ data: LearningPlan }> {
  const { data } = await http.post<LearningPlan>(`${ENDPOINTS.PLAN_DETAIL(id)}complete/`, body || {})
  return { data }
}

// POST /api/plans/<id>/skip/ — 标记 plan 为跳过
//   可选 body: { reason: "..." }
export async function skipPlan(
  id: number,
  body?: { reason?: string },
): Promise<{ data: LearningPlan }> {
  const { data } = await http.post<LearningPlan>(`${ENDPOINTS.PLAN_DETAIL(id)}skip/`, body || {})
  return { data }
}

export default {
  listPlans,
  getPlan,
  createPlan,
  updatePlan,
  deletePlan,
  markPlanDone,
  skipPlan,
}
