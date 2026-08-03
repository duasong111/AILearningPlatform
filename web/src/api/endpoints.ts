// 请求路由控制 - 请规范使用

export const ENDPOINTS = {
  // === 用户认证 ===
  LOGIN: '/api/auth/login/', // 用户登录
  REGISTER: '/api/auth/register/', // 用户注册
  REFRESH: '/api/auth/refresh/', // 刷新 token

  // === 用户画像 ===
  PROFILE: '/api/profile/', // GET/PATCH ?subject=<code> // 构建用户画像
  PROFILE_COMPLETE: '/api/profile/complete/', // POST 标记画像完成

  // === 学科管理 ===
  SUBJECTS: '/api/subjects/', // GET 学科列表
  CONVERSATIONS: '/api/conversations/', // GET 列表; DELETE /<id>/
  MESSAGES: '/api/messages/', // GET ?conversation=<id> 拉历史 transcript
  SUBJECT_DeTAIL: (id: string) => `/api/subjects/${id}/`, // 获取学科详情

  // === Learning records ===
  RESOURCE_HISTORY: '/api/learning/resource-history/',
  EXERCISE_RECORDS: '/api/learning/exercises/',
  REPORTS: '/api/learning/reports/',
  STUDY_SESSIONS: '/api/learning/study-sessions/',
  STUDY_SESSION_ACCUMULATE: '/api/learning/study-sessions/accumulate/',
  STUDY_SESSION_SUMMARY: '/api/learning/study-sessions/summary/',
  STUDY_SESSION_TOTAL: '/api/learning/study-sessions/total/',
  STUDY_TIME_AGGREGATE: '/api/learning/study-time/',   // GET ?days=30 → { by_day, by_subject }

  // === 读书会话 (打开书事件) ====
  READING_SESSIONS: '/api/learning/reading-sessions/',         // GET 列表
  READING_SESSION_OPEN: '/api/learning/reading-sessions/open/',           // POST 打开书
  READING_SESSION_HEARTBEAT: '/api/learning/reading-sessions/heartbeat/', // POST 心跳
  READING_SESSION_CLOSE: '/api/learning/reading-sessions/close/',         // POST 关书
  BOOKS: '/api/learning/books/',                                   // GET 书列表 (mirror)

  // ==== 知识节点 ====
  KNOWLEDGE_NODES: '/api/knowledge-nodes/', // GET 列表; POST 新建
  KNOWLEDGE_NODE_DETAIL: (id: string) => `/api/knowledge-nodes/${id}/`, // GET 详情; PATCH 更新; DELETE 删除
  KNOWLEDGE_GRAPH: (code: string) => `/api/knowledge-graph/${code}/`, // GET 完整图谱拓扑 + mastery

  // === 学习计划 =====
  PLANS: '/api/plans/', // GET 列表 (?subject=code); POST 新建
  PLAN_DETAIL: (id: number | string) => `/api/plans/${id}/`, // GET/PATCH/DELETE 单个计划

  // === 题目与解析生成 ===

  QUIZ_GENERATE: '/api/quiz/generate/',
  QUIZ_AUTO_GENERATE: '/api/quiz/auto-generate/',
  QUIZ_TASK: (id: string) => `/api/quiz/tasks/${id}/`,          // GET 合并响应: state + questions + error_message
  QUIZ_ACTIVE_QUEUE: '/api/quiz/active-queue/',                 // GET ready+generating 队列
  QUIZ_MARK_ANSWERED: '/api/quiz/mark-answered/',               // POST 标记已答 (后端自动补题)
  PRACTICE_ANALYZE: '/api/practice/analyze/',
  PRACTICE_TASK: (id: string) => `/api/practice/tasks/${id}/`,  // GET 合并响应: state + analysis

  // === 历史记录 ===
  QUIZZES_LIST: '/api/quizzes/',                    // GET 出题列表 (?subject=&state=)
  PRACTICE_ANALYSES_LIST: '/api/practice-analyses/', // GET 解析列表 (?subject=&state=&quiz_generation=)

  // === 综合测评 (Dify 工作流生成题库) ===
  EXAM_SESSIONS: '/api/exam/sessions/',
  EXAM_SESSION: (id: number) => `/api/exam/sessions/${id}/`,
  EXAM_SESSION_SUBMIT: (id: number) => `/api/exam/sessions/${id}/submit/`,
  EXAM_HISTORY: '/api/exam/history/',

  // === 代码实践 ===
  PRACTICE_SESSION: (id: number) => `/api/practice/sessions/${id}/`,

  // === 视频课程 ===
 VIDEO_COURSES: '/api/video-courses/',                             // GET 列表
 VIDEO_COURSE_DETAIL: (id: number | string) => `/api/video-courses/${id}/`,  // GET 详情
 VIDEO_COURSE_GENERATE: '/api/video-course/generate/',             // POST 启动生成
 VIDEO_COURSE_TASK: (id: string) => `/api/video-course/tasks/${id}/`,         // GET 轮询状态
 VIDEO_COURSE_PROGRESS: (id: number | string) => `/api/video-course/${id}/progress/`, // POST 上报进度
VIDEO_COURSE_INTRO: (recordId: number | string) => `/api/video-courses/${recordId}/intro/`, // POST 生成简介+作业
  VIDEO_COURSE_BY_UUID: (uuid: string) => `/api/video-courses/by-uuid/${uuid}/`, // GET 通过 uuid 查找记录
  VIDEO_COURSE_OUTLINES: (recordId: number | string) => `/api/video-courses/${recordId}/outlines/`, // PATCH 回填 outlines
} as const

/**
 * 直接访问 OpenMAIC 服务端的辅助函数。
 *
 * 注意：这不是后端 API，而是前端直接轮询视频生成服务（由 VITE_OPENMAIC_URL 配置），
 * 用来在后端轮询还没拉到 scenes 时，兜底把 outline 推到前端。
 *
 * Vite 注入：import.meta.env.VITE_OPENMAIC_URL（完整 URL，含协议）
 */
export function getOpenmaicBaseUrl(): string {
  const raw = (import.meta.env.VITE_OPENMAIC_URL as string | undefined)?.trim()
  if (raw) return raw.replace(/\/+$/, '')
  return '<YOUR_OPENMAIC_HOST:PORT>'  // 请在 .env 中配置 VITE_OPENMAIC_URL
}

export const OPENMAIC_API_VIDEO = (uuid: string): string =>
  `${getOpenmaicBaseUrl()}/api/video/${uuid}`
