import http from './http'
import { ENDPOINTS, OPENMAIC_API_VIDEO, getOpenmaicBaseUrl } from './endpoints'

// ============================================================
// 视频课程 HTTP 接口
//
//   后端流程:
//     1. POST /api/video-course/generate/         → 创建 Celery 任务, 返回 VideoCourseRecord
//     2. GET  /api/video-course/tasks/<task_id>/  → 合并响应: state + course + iframe_url
//     3. POST /api/video-course/<id>/progress/    → 上报观看进度, 影响知识图谱
//     4. GET  /api/video-courses/                 → 历史记录列表
//     5. GET  /api/video-courses/<id>/            → 详情
// ============================================================

export interface VideoSceneOutline {
  id: string
  type: 'slide'
  title: string
  description: string
  key_points: string[]
  order: number
  knowledge_node_id: string | null
}

export interface VideoCourseOutline {
  desc: string
  language_directive: string
  target_audience: string
  difficulty: 'easy' | 'medium' | 'hard'
  estimated_minutes: number
  course_intro: string
  course_summary: string
  learning_objectives: string[]
  prerequisites: string[]
  outlines: VideoSceneOutline[]
}

export interface VideoCourseRecord {
  id: number
  task_id: string
  subject_id: number
  subject_name: string
  subject_display: string
  topic: string
  extra_prompt: string
  knowledge_node_ids: string[]
  state: 'generating' | 'complete' | 'error' | string
  course: VideoCourseOutline
  video_uuid: string
  iframe_url: string
  error_message: string
  viewed_scene_ids: string[]
  last_scene_id: string
  watched_seconds: number
  completion_ratio: number
  completed: boolean
  scene_count: number
  viewed_scene_count: number
  created_at: string
  completed_at: string | null
  updated_at: string
  ttl_sec: number
}

export interface VideoProgressSummary {
  viewed_count: number
  total_count: number
  completion_ratio: number
  new_viewed_scene_ids: string[]
  knowledge_updates: Array<{
    scene_id: string
    node_id: string
    result?: unknown
    error?: string
  }>
}

// ─── 生成视频课程 ────────────────────────────────
interface StartVideoCourseOpts {
  subjectId: number
  topic: string
  extraPrompt?: string
  knowledgeNodeIds?: string[]
  /** 绑定到 LearningPlan, 生成时回填 plan.memory.items[].video_record_id */
  planId?: number
  /** PlanItem 的 id 字段, 与 planId 一起传才生效 */
  planNodeId?: string
}

export async function startVideoCourse(
  opts: StartVideoCourseOpts,
): Promise<{ data: VideoCourseRecord }> {
  return http.post(ENDPOINTS.VIDEO_COURSE_GENERATE, {
    subject_id: opts.subjectId,
    topic: opts.topic,
    extra_prompt: opts.extraPrompt ?? '',
    knowledge_node_ids: opts.knowledgeNodeIds ?? [],
    plan_id: opts.planId,
    plan_node_id: opts.planNodeId,
  })
}

export async function getVideoCourseTask(
  taskId: string,
): Promise<{ data: VideoCourseRecord }> {
  return http.get(ENDPOINTS.VIDEO_COURSE_TASK(taskId))
}

export async function getVideoCourse(
  recordId: number,
): Promise<{ data: VideoCourseRecord }> {
  return http.get(ENDPOINTS.VIDEO_COURSE_DETAIL(recordId))
}

export async function listVideoCourses(
  params: { subject?: number; state?: string; completed?: boolean } = {},
): Promise<{ data: { results: VideoCourseRecord[]; count: number } | VideoCourseRecord[] }> {
  return http.get(ENDPOINTS.VIDEO_COURSES, { params })
}

/** 通过 uuid 查找视频课程记录 */
export async function getVideoCourseByUuid(uuid: string): Promise<{ data: VideoCourseRecord }> {
  return http.get(ENDPOINTS.VIDEO_COURSE_BY_UUID(uuid))
}

/**
 * 前端回填 outlines 到后端。
 * PATCH /api/video-courses/<id>/outlines/
 *
 * 后端收到后自动生成简介+作业，响应中带 intro / homework。
 */
export async function patchOutlines(
  recordId: number,
  outlines: VideoSceneOutline[],
): Promise<{
  data: VideoCourseRecord & { intro?: Record<string, unknown>; homework?: Record<string, unknown>[] }
}> {
  return http.patch(ENDPOINTS.VIDEO_COURSE_OUTLINES(recordId), { outlines })
}

// ============================================================
// 直接访问 OpenMAIC（前端兜底用，不走后端）
// ============================================================

/** OpenMAIC 返回的 scene 形状（与 OpenMAIC `app/api/video/[uuid]/route.ts` 一致）。 */
export interface OpenmaicScene {
  id: string
  type?: string
  title?: string
  description?: string
  desc?: string
  keyPoints?: string[]
  key_points?: string[]
  order?: number
  content?: unknown
  actions?: unknown[]
}

export interface OpenmaicVideoResponse {
  video?: {
    desc?: string
    scenes?: OpenmaicScene[]
    outlines?: OpenmaicScene[]
  }
  data?: {
    desc?: string
    scenes?: OpenmaicScene[]
    outlines?: OpenmaicScene[]
  }
  // 兼容 OpenMAIC 不同版本直接平铺
  desc?: string
  scenes?: OpenmaicScene[]
  outlines?: OpenmaicScene[]
}

/**
 * 前端直接 GET OpenMAIC 的 /api/video/<uuid>，返回规范化后的 outline 数组。
 *
 *   - 找不到 / 404 / uuid 不合规 → 返回 null（调用方继续等下一轮）
 *   - 命中 → 用 OpenMAIC 的 scenes 转成本地 VideoSceneOutline[] 形状
 *
 * 用于"后端轮询还没拉到 scenes" 时前端兜底轮询，2s 一次，最多 60s。
 */
export async function fetchOpenmaicOutlines(uuid: string): Promise<VideoSceneOutline[] | null> {
  const url = OPENMAIC_API_VIDEO(uuid)
  let resp: Response
  try {
    resp = await fetch(url, { method: 'GET', cache: 'no-store' })
  } catch {
    return null
  }
  if (resp.status !== 200) return null
  let body: OpenmaicVideoResponse
  try {
    body = (await resp.json()) as OpenmaicVideoResponse
  } catch {
    return null
  }
  // 兼容多种 payload 形状
  const video = (body.video ?? body.data ?? body) as {
    desc?: string
    scenes?: OpenmaicScene[]
    outlines?: OpenmaicScene[]
  }
  const scenes = video.scenes ?? video.outlines ?? []
  if (!scenes.length) return null
  return scenes.map((s, idx) => {
    const rawOrder = s.order
    let order: number
    if (typeof rawOrder === 'number' && Number.isFinite(rawOrder)) order = rawOrder
    else order = idx + 1
    return {
      id: s.id || `scene_${idx + 1}`,
      type: 'slide' as const,
      title: s.title ?? '',
      description: s.description ?? s.desc ?? '',
      key_points: s.keyPoints ?? s.key_points ?? [],
      order,
      knowledge_node_id: null,
    }
  })
}

/** 返回当前生效的 OpenMAIC base URL（UI 文案提示用）。 */
export function getOpenmaicUrl(): string {
  return getOpenmaicBaseUrl()
}

/** 获取视频课程简介和作业 */
export async function generateVideoIntro(recordId: number | string): Promise<{ intro: VideoIntroData; homework: VideoHomeworkItem[] }> {
  const resp = await http.post(ENDPOINTS.VIDEO_COURSE_INTRO(recordId))
  return resp.data
}

export interface VideoIntroData {
  summary: string
  why_learn: string
  key_concepts: string[]
  what_you_will_learn: string[]
}

export interface VideoHomeworkItem {
  id: string
  title: string
  description: string
  type: 'choice' | 'short_answer' | 'coding'
  difficulty: 'easy' | 'medium' | 'hard'
  answer_hint: string
}

// ─── 进度上报 ────────────────────────────────────
export interface ReportVideoProgressOpts {
  recordId: number
  viewedSceneIds: string[]
  lastSceneId?: string | null
  watchedSeconds: number
  completed?: boolean
}

export async function reportVideoProgress(
  opts: ReportVideoProgressOpts,
): Promise<{ data: VideoCourseRecord & { progress_summary: VideoProgressSummary } }> {
  return http.post(ENDPOINTS.VIDEO_COURSE_PROGRESS(opts.recordId), {
    viewed_scene_ids: opts.viewedSceneIds,
    last_scene_id: opts.lastSceneId ?? null,
    watched_seconds: opts.watchedSeconds,
    completed: opts.completed ?? false,
  })
}
