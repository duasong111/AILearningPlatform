// ============================================================
// 学习报告 mock —— 富数据, 够 ReportsView 出多种可视化
//
//   每条周报带:
//     - 总览 (时长/题数/学科数/掌握节点数)
//     - 每日学习时长 (折线/柱图)
//     - 学科时间分布 (donut)
//     - 掌握度分布 (0-20, 20-40, ... 柱图)
//     - 每日对错趋势 (stacked bar)
//     - TOP 5 掌握最好 / BOTTOM 5 最薄弱 节点
//     - 自然语言 summary
//
//   跟 backend WeeklyReportSerializer 字段不完全一致
//   (那只是 summary + top/weak), 后端补全后端会回同结构, 调 listReports 即可
// ============================================================

import type { RichWeeklyReport, SubjectCode } from '@/types/learning'

// ─── helpers ──────────────────────────────────────────────
function dayLabels(weekStart: string, weekEnd: string): string[] {
  const start = new Date(weekStart)
  const end = new Date(weekEnd)
  const days: string[] = []
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    days.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return days
}

const MASTERY_RANGES: { range: string; lo: number; hi: number }[] = [
  { range: '0-20',   lo: 0,  hi: 20 },
  { range: '20-40',  lo: 20, hi: 40 },
  { range: '40-60',  lo: 40, hi: 60 },
  { range: '60-80',  lo: 60, hi: 80 },
  { range: '80-100', lo: 80, hi: 100 },
]

function randomDailyMinutes(seed: number, days: number): number[] {
  // 周末少一些, 工作日多一些 (5-7 倍更明显)
  const base: number[] = []
  for (let i = 0; i < days; i++) {
    const isWeekend = i === 5 || i === 6
    const v = isWeekend ? 12 + ((seed * 7 + i) % 18) : 32 + ((seed * 13 + i) % 28)
    base.push(v)
  }
  return base
}

function masteryHistogram(seed: number, nodes: { mastery: number }[]): number[] {
  // 实际: 统计 nodes 落在每个 mastery 区间
  const hist = [0, 0, 0, 0, 0]
  for (const n of nodes) {
    const idx = MASTERY_RANGES.findIndex((r) => n.mastery >= r.lo && n.mastery < r.hi)
    if (idx === -1 && n.mastery === 100) hist[4]!++
    else if (idx >= 0) hist[idx]!++
  }
  // 留一点点随机扰动
  for (let i = 0; i < hist.length; i++) hist[i] = hist[i]! + ((seed + i) % 3)
  return hist
}

// ─── 6 条周报 (手写, 不随机) ──────────────────────────────────

const r1: RichWeeklyReport = {
  id: 1,
  week_start: '2026-06-01',
  week_end: '2026-06-07',
  total_minutes: 248,
  total_questions: 47,
  total_correct: 34,
  subjects_studied: ['data_structure', 'advanced_math'],
  nodes_mastered_count: 3,
  summary: '本周主攻数据结构, 在动态规划与平衡树上花了大量时间。AI 出题侧正确率 72%, 高三周前提升约 12 个百分点。',
  daily_minutes: [42, 38, 55, 30, 41, 18, 24],
  subject_distribution: [
    { subject: 'data_structure', minutes: 168 },
    { subject: 'advanced_math',  minutes: 80 },
  ],
  mastery_distribution: [6, 9, 12, 7, 4],         // 总 38 节点
  daily_correctness: [
    { day: '6/1', correct: 5, wrong: 2 },
    { day: '6/2', correct: 6, wrong: 1 },
    { day: '6/3', correct: 7, wrong: 3 },
    { day: '6/4', correct: 3, wrong: 2 },
    { day: '6/5', correct: 6, wrong: 2 },
    { day: '6/6', correct: 2, wrong: 1 },
    { day: '6/7', correct: 5, wrong: 1 },
  ],
  top_nodes: [
    { name: '红黑树',         subject: 'data_structure', mastery: 82 },
    { name: '栈',              subject: 'data_structure', mastery: 78 },
    { name: 'DFS',              subject: 'data_structure', mastery: 75 },
    { name: '极限定义',         subject: 'advanced_math',  mastery: 73 },
    { name: '链表',              subject: 'data_structure', mastery: 70 },
  ],
  weak_nodes: [
    { name: 'AC自动机',       subject: 'data_structure', mastery: 18 },
    { name: 'Tarjan算法',     subject: 'data_structure', mastery: 22 },
    { name: '跳表',             subject: 'data_structure', mastery: 28 },
    { name: 'KMP算法',         subject: 'data_structure', mastery: 32 },
    { name: '回溯算法',         subject: 'data_structure', mastery: 35 },
  ],
}

const r2: RichWeeklyReport = {
  id: 2,
  week_start: '2026-05-25',
  week_end: '2026-05-31',
  total_minutes: 196,
  total_questions: 38,
  total_correct: 24,
  subjects_studied: ['data_structure', 'iot'],
  nodes_mastered_count: 2,
  summary: '本周在巩固高数微积分与 IoT 协议, MQTT 章节已完成。下周建议补一下信号量与互斥锁, 那里还相对薄弱。',
  daily_minutes: [35, 28, 41, 22, 33, 15, 22],
  subject_distribution: [
    { subject: 'data_structure', minutes: 110 },
    { subject: 'iot',            minutes: 86 },
  ],
  mastery_distribution: [5, 8, 11, 8, 4],
  daily_correctness: [
    { day: '5/25', correct: 4, wrong: 2 },
    { day: '5/26', correct: 3, wrong: 3 },
    { day: '5/27', correct: 5, wrong: 2 },
    { day: '5/28', correct: 2, wrong: 2 },
    { day: '5/29', correct: 4, wrong: 1 },
    { day: '5/30', correct: 2, wrong: 2 },
    { day: '5/31', correct: 4, wrong: 2 },
  ],
  top_nodes: [
    { name: 'MQTT协议',     subject: 'iot',             mastery: 76 },
    { name: '链表',          subject: 'data_structure',  mastery: 70 },
    { name: '栈',           subject: 'data_structure',  mastery: 68 },
    { name: '二叉搜索树',   subject: 'data_structure',  mastery: 65 },
    { name: '传感器接口',    subject: 'iot',             mastery: 62 },
  ],
  weak_nodes: [
    { name: '并查集',       subject: 'data_structure',  mastery: 25 },
    { name: '树状数组',     subject: 'data_structure',  mastery: 30 },
    { name: '线程同步',     subject: 'iot',             mastery: 32 },
    { name: '线段树',       subject: 'data_structure',  mastery: 36 },
    { name: '消息队列',     subject: 'iot',             mastery: 40 },
  ],
}

const r3: RichWeeklyReport = {
  id: 3,
  week_start: '2026-05-18',
  week_end: '2026-05-24',
  total_minutes: 132,
  total_questions: 24,
  total_correct: 16,
  subjects_studied: ['data_structure'],
  nodes_mastered_count: 1,
  summary: '入门周, 完成账户初始化与第一门学科选择, 开始接触数据结构基础。节奏还在建立。',
  daily_minutes: [18, 12, 22, 25, 18, 10, 27],
  subject_distribution: [
    { subject: 'data_structure', minutes: 132 },
  ],
  mastery_distribution: [4, 6, 5, 2, 1],
  daily_correctness: [
    { day: '5/18', correct: 2, wrong: 1 },
    { day: '5/19', correct: 1, wrong: 2 },
    { day: '5/20', correct: 3, wrong: 1 },
    { day: '5/21', correct: 3, wrong: 1 },
    { day: '5/22', correct: 2, wrong: 2 },
    { day: '5/23', correct: 1, wrong: 1 },
    { day: '5/24', correct: 4, wrong: 0 },
  ],
  top_nodes: [
    { name: '数组',     subject: 'data_structure', mastery: 72 },
    { name: '链表',     subject: 'data_structure', mastery: 65 },
    { name: '栈',       subject: 'data_structure', mastery: 60 },
    { name: '队列',     subject: 'data_structure', mastery: 55 },
    { name: '树',       subject: 'data_structure', mastery: 52 },
  ],
  weak_nodes: [
    { name: '红黑树',   subject: 'data_structure', mastery: 8 },
    { name: 'B树',     subject: 'data_structure', mastery: 10 },
    { name: 'DFS',     subject: 'data_structure', mastery: 15 },
    { name: 'Dijkstra', subject: 'data_structure', mastery: 18 },
    { name: '动态规划', subject: 'data_structure', mastery: 22 },
  ],
}

const r4: RichWeeklyReport = {
  id: 4,
  week_start: '2026-06-08',
  week_end: '2026-06-14',
  total_minutes: 312,
  total_questions: 64,
  total_correct: 51,
  subjects_studied: ['data_structure', 'cybersecurity', 'advanced_math'],
  nodes_mastered_count: 4,
  summary: '本周跨三门学科拓展: 数据结构推进到高级算法, 网络安全开始入门(对称加密、哈希), 高数复习了级数与微分方程。',
  daily_minutes: [55, 60, 42, 48, 36, 30, 41],
  subject_distribution: [
    { subject: 'data_structure', minutes: 160 },
    { subject: 'cybersecurity',  minutes: 88 },
    { subject: 'advanced_math',  minutes: 64 },
  ],
  mastery_distribution: [3, 7, 14, 12, 8],
  daily_correctness: [
    { day: '6/8',  correct: 8, wrong: 2 },
    { day: '6/9',  correct: 9, wrong: 1 },
    { day: '6/10', correct: 6, wrong: 3 },
    { day: '6/11', correct: 7, wrong: 2 },
    { day: '6/12', correct: 5, wrong: 3 },
    { day: '6/13', correct: 7, wrong: 2 },
    { day: '6/14', correct: 9, wrong: 1 },
  ],
  top_nodes: [
    { name: '红黑树',         subject: 'data_structure',  mastery: 88 },
    { name: '对称加密',       subject: 'cybersecurity',   mastery: 82 },
    { name: '哈希函数',       subject: 'cybersecurity',   mastery: 80 },
    { name: 'DFS',             subject: 'data_structure',  mastery: 78 },
    { name: '微分中值定理',   subject: 'advanced_math',   mastery: 75 },
  ],
  weak_nodes: [
    { name: 'AC自动机',       subject: 'data_structure',  mastery: 22 },
    { name: 'TLS握手',         subject: 'cybersecurity',   mastery: 28 },
    { name: '跳表',             subject: 'data_structure',  mastery: 32 },
    { name: '级数收敛判别',     subject: 'advanced_math',   mastery: 36 },
    { name: '回溯算法',         subject: 'data_structure',  mastery: 40 },
  ],
}

const r5: RichWeeklyReport = {
  id: 5,
  week_start: '2026-05-11',
  week_end: '2026-05-17',
  total_minutes: 96,
  total_questions: 18,
  total_correct: 11,
  subjects_studied: ['data_structure'],
  nodes_mastered_count: 0,
  summary: '低强度恢复周。完成了上一周落下的几道基础题, 把数组/链表的边角 case 重温了一遍。',
  daily_minutes: [0, 18, 20, 0, 22, 16, 20],
  subject_distribution: [
    { subject: 'data_structure', minutes: 96 },
  ],
  mastery_distribution: [3, 5, 4, 1, 0],
  daily_correctness: [
    { day: '5/11', correct: 0, wrong: 0 },
    { day: '5/12', correct: 3, wrong: 2 },
    { day: '5/13', correct: 3, wrong: 1 },
    { day: '5/14', correct: 0, wrong: 0 },
    { day: '5/15', correct: 4, wrong: 1 },
    { day: '5/16', correct: 2, wrong: 1 },
    { day: '5/17', correct: 3, wrong: 1 },
  ],
  top_nodes: [
    { name: '数组', subject: 'data_structure', mastery: 65 },
    { name: '链表', subject: 'data_structure', mastery: 60 },
    { name: '栈',   subject: 'data_structure', mastery: 56 },
    { name: '队列', subject: 'data_structure', mastery: 50 },
    { name: '树',   subject: 'data_structure', mastery: 48 },
  ],
  weak_nodes: [
    { name: 'AVL树', subject: 'data_structure', mastery: 5 },
    { name: 'KMP算法', subject: 'data_structure', mastery: 8 },
    { name: '拓扑排序', subject: 'data_structure', mastery: 10 },
    { name: '红黑树', subject: 'data_structure', mastery: 12 },
    { name: '哈希冲突', subject: 'data_structure', mastery: 15 },
  ],
}

const r6: RichWeeklyReport = {
  id: 6,
  week_start: '2026-05-04',
  week_end: '2026-05-10',
  total_minutes: 0,
  total_questions: 0,
  total_correct: 0,
  subjects_studied: [],
  nodes_mastered_count: 0,
  summary: '本周未开始学习。',
  daily_minutes: [0, 0, 0, 0, 0, 0, 0],
  subject_distribution: [],
  mastery_distribution: [0, 0, 0, 0, 0],
  daily_correctness: [
    { day: '5/4', correct: 0, wrong: 0 },
    { day: '5/5', correct: 0, wrong: 0 },
    { day: '5/6', correct: 0, wrong: 0 },
    { day: '5/7', correct: 0, wrong: 0 },
    { day: '5/8', correct: 0, wrong: 0 },
    { day: '5/9', correct: 0, wrong: 0 },
    { day: '5/10', correct: 0, wrong: 0 },
  ],
  top_nodes: [],
  weak_nodes: [],
}

const MOCK_RICH_REPORTS: RichWeeklyReport[] = [r4, r1, r2, r5, r3, r6]  // 最新在前

// 备用: 给一些代码会显式引到的"day labels"
void dayLabels

// 兼容旧 WeeklyReportSerializer (api/learning.ts 的 listReports 还在用)
import type { WeeklyReport } from '@/types/learning'
const MOCK_LEAN_REPORTS: WeeklyReport[] = MOCK_RICH_REPORTS.map((r) => ({
  id: r.id,
  week_start: r.week_start,
  week_end: r.week_end,
  summary: r.summary,
  top_nodes: r.top_nodes.map((n) => n.name),
  weak_nodes: r.weak_nodes.map((n) => n.name),
  total_time_min: r.total_minutes,
}))

export async function fetchRichReports(): Promise<{ data: RichWeeklyReport[] }> {
  await new Promise<void>((r) => setTimeout(r, 220))
  return { data: MOCK_RICH_REPORTS }
}

export async function fetchRichReport(id: number): Promise<{ data: RichWeeklyReport | null }> {
  await new Promise<void>((r) => setTimeout(r, 180))
  return { data: MOCK_RICH_REPORTS.find((r) => r.id === id) ?? null }
}

export { MOCK_RICH_REPORTS, MOCK_LEAN_REPORTS, MASTERY_RANGES }
