// ============================================================
// 学习域类型 —— 字段全 snake_case, 与未来 DRF 序列化器对齐
//   (本轮三个 Tab 用 mock 数据, 后端接入后无需改 view)
// ============================================================

// 与 backend/users/models.py:34-42 的 Subject.SUBJECT_CHOICES 严格对齐
export type SubjectCode =
  | 'data_structure'
  | 'cybersecurity'
  | 'iot'
  | 'electrical_automation'
  | 'mechanical_design'
  | 'advanced_math'
  | 'artificial_intelligence'

// ============================================================
// 学习记录 - 资源历史
// ============================================================
export interface ResourceHistoryItem {
  id: number
  timestamp: string                                  // ISO
  resource_name: string
  type: 'video' | 'article' | 'pdf' | 'interactive'
  duration_min: number
  subject: SubjectCode
}

// ============================================================
// 学习记录 - 习题记录
// ============================================================
export interface ExerciseRecord {
  id: number
  timestamp: string
  question: string
  answer: string
  correct: boolean
  knowledge_node: string                             // 知识点中文名, e.g. "二叉搜索树"
  subject: SubjectCode
}

// ============================================================
// 学习记录 - 周报
// ============================================================
export interface WeeklyReport {
  id: number
  week_start: string                                 // ISO date
  week_end: string
  summary: string
  top_nodes: string[]                                // 表现好的 3 个节点
  weak_nodes: string[]                               // 薄弱的 3 个节点
  total_time_min: number
}

// ============================================================
// 富周报 —— ReportsView 用的可视化全字段
//   后端目前只返 lean WeeklyReport; 这个富版块前端 mock 拼出来演示,
//   后端补全端到端时, 把 fetchRichReports 换成真 http.get 即可, 类型不变.
// ============================================================
export interface ReportSubjectSlice {
  subject: SubjectCode
  minutes: number
}
export interface ReportMasteryNode {
  name: string
  subject: SubjectCode
  mastery: number                                     // 0-100
}
export interface ReportDailyCorrectness {
  day: string                                         // "6/8"
  correct: number
  wrong: number
}

export interface RichWeeklyReport {
  id: number
  week_start: string
  week_end: string

  // 总览
  total_minutes: number
  total_questions: number
  total_correct: number
  subjects_studied: SubjectCode[]
  nodes_mastered_count: number                       // mastery >= 70
  summary: string

  // 可视化数据
  daily_minutes: number[]                             // 7 个, 对应 week_start..week_end
  subject_distribution: ReportSubjectSlice[]
  mastery_distribution: number[]                      // 5 个, 区间 [0-20, 20-40, 40-60, 60-80, 80-100]
  daily_correctness: ReportDailyCorrectness[]

  top_nodes: ReportMasteryNode[]                      // TOP 5
  weak_nodes: ReportMasteryNode[]                     // BOTTOM 5
}

// ============================================================
// 知识图谱 - 节点 / 边 / 整图
//   对齐 backend/users/knowledge_map.py 的静态字典结构
// ============================================================
export interface KnowledgeNode {
  id: string                                         // 短 id, e.g. "ds_array"
  name: string                                       // 显示名
  type: string                                       // "concept" | "structure" | "algorithm" | ...
  difficulty: number                                 // 1-5
  mastery?: number                                   // 0-100, 来自 KnowledgeNode.mastery (后端字段)
}

export interface KnowledgeRelation {
  source: string                                     // 源节点 id
  target: string                                     // 目标节点 id
  type: string                                       // "prerequisite" | "used_in" | "contains" | ...
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[]
  relations: KnowledgeRelation[]
}

// ============================================================
// 课程详情 (CourseDetailView) —— 章节 + 知识点
//   章节目前是 frontend-only 抽象, 把 GRAPHS[code] 里的节点按 type 分组
//   (后端没有 Chapter model, 后续接 KnowledgeChapter 的话改 type 即可)
// ============================================================
export interface Chapter {
  id: string
  name: string
  description: string
  order: number
  knowledge_node_ids: string[]            // 该章包含的节点 id (对应 KnowledgeNode.id 字符串)
}

// ============================================================
// 知识点详情 (KnowledgePointView) —— 4 个 tab 的资源
// ============================================================
export interface VideoResource {
  type: 'video'
  title: string
  duration: string                        // "12:34"
  source: string                          // "B站" / "学堂在线" / "YouTube"
  thumbnail_hue?: number                  // 0-360, 用 hsl 生成缩略图背景色
}
export interface PPTResource {
  type: 'ppt'
  title: string
  page_count: number
  file_size?: string                      // "2.3 MB"
}
export interface EncyclopediaResource {
  type: 'encyclopedia'
  content: string                         // markdown
}
export interface QAItem {
  id: string
  question: string
  answer_count: number
  has_accepted_answer: boolean
  asker: string
  time_ago: string                        // "2 days ago"
}
export interface QAResource {
  type: 'qa'
  items: QAItem[]
}

export type KnowledgeResource =
  | VideoResource
  | PPTResource
  | EncyclopediaResource
  | QAResource
