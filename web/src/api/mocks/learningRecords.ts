// ============================================================
// 学习记录 mocks —— 资源历史 / 习题记录 / 周报
//
// SWAP TARGET: 后端补上对应接口后, 在 api/learning.ts 一行换成真请求即可.
//   - 这里直接返 {data: {items: [...]}} 拟 axios 形状
//   - setTimeout 250ms 拟真实网络延迟, 让 view 的 loading 态走一遍
//
// 数据原则:
//   - 时间戳全部硬编码 ISO (~过去 3 周内), 保持页面间一致;
//     不用 Date.now() 是为了避免每次刷新都换一组 "x hours ago"
//   - subject / knowledge_node 字段引用真实学科/概念, 后端接入后零摩擦
// ============================================================

import type {
  ExerciseRecord,
  ResourceHistoryItem,
  WeeklyReport,
} from '@/types/learning'

const LATENCY_MS = 250
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

// ------------------------------------------------------------
// 资源历史 —— 用户看过的视频/文章/PDF/交互式课件
// ------------------------------------------------------------
const MOCK_RESOURCE_HISTORY: ResourceHistoryItem[] = [
  {
    id: 101,
    timestamp: '2026-06-06T14:32:00+08:00',
    resource_name: '红黑树原理详解',
    type: 'video',
    duration_min: 28,
    subject: 'data_structure',
  },
  {
    id: 102,
    timestamp: '2026-06-06T10:08:00+08:00',
    resource_name: 'TCP 三次握手与四次挥手',
    type: 'article',
    duration_min: 12,
    subject: 'cybersecurity',
  },
  {
    id: 103,
    timestamp: '2026-06-05T20:45:00+08:00',
    resource_name: '动态规划入门 - 背包问题',
    type: 'interactive',
    duration_min: 45,
    subject: 'data_structure',
  },
  {
    id: 104,
    timestamp: '2026-06-04T16:20:00+08:00',
    resource_name: '神经网络反向传播推导',
    type: 'pdf',
    duration_min: 35,
    subject: 'artificial_intelligence',
  },
  {
    id: 105,
    timestamp: '2026-06-03T09:15:00+08:00',
    resource_name: '哈希表冲突解决方案对比',
    type: 'video',
    duration_min: 22,
    subject: 'data_structure',
  },
  {
    id: 106,
    timestamp: '2026-06-01T22:10:00+08:00',
    resource_name: 'MQTT 协议在 IoT 中的应用',
    type: 'article',
    duration_min: 18,
    subject: 'iot',
  },
  {
    id: 107,
    timestamp: '2026-05-29T15:00:00+08:00',
    resource_name: '微分中值定理证明',
    type: 'pdf',
    duration_min: 40,
    subject: 'advanced_math',
  },
]

// ------------------------------------------------------------
// 习题记录 —— 题目 + 用户答案 + 是否正确 + 涉及知识点
// ------------------------------------------------------------
const MOCK_EXERCISE_RECORDS: ExerciseRecord[] = [
  {
    id: 201,
    timestamp: '2026-06-06T15:10:00+08:00',
    question: '红黑树最坏情况下查找的时间复杂度是?',
    answer: 'O(log n)',
    correct: true,
    knowledge_node: '红黑树',
    subject: 'data_structure',
  },
  {
    id: 202,
    timestamp: '2026-06-06T15:14:00+08:00',
    question: 'AVL 树与红黑树相比, 哪个插入更快?',
    answer: 'AVL 树',
    correct: false,
    knowledge_node: '平衡二叉树',
    subject: 'data_structure',
  },
  {
    id: 203,
    timestamp: '2026-06-05T21:30:00+08:00',
    question: '0-1 背包问题的状态转移方程是?',
    answer: 'dp[i][j] = max(dp[i-1][j], dp[i-1][j-w[i]] + v[i])',
    correct: true,
    knowledge_node: '动态规划',
    subject: 'data_structure',
  },
  {
    id: 204,
    timestamp: '2026-06-04T17:00:00+08:00',
    question: 'ReLU 激活函数在 x<0 时的导数是?',
    answer: '0',
    correct: true,
    knowledge_node: '激活函数',
    subject: 'artificial_intelligence',
  },
  {
    id: 205,
    timestamp: '2026-06-03T10:00:00+08:00',
    question: '开放寻址法的探测序列有哪几种?',
    answer: '只有线性探测',
    correct: false,
    knowledge_node: '哈希表',
    subject: 'data_structure',
  },
]

// ------------------------------------------------------------
// 周报 —— 每周自动汇总
// ------------------------------------------------------------
const MOCK_REPORTS: WeeklyReport[] = [
  {
    id: 301,
    week_start: '2026-06-01',
    week_end: '2026-06-07',
    summary:
      '本周主攻数据结构, 在动态规划与平衡树上花了大量时间。AI 方向新增 1 篇深度学习论文阅读, 节奏不错。',
    top_nodes: ['红黑树', '动态规划', 'ReLU'],
    weak_nodes: ['哈希冲突', 'AVL 旋转', '梯度消失'],
    total_time_min: 248,
  },
  {
    id: 302,
    week_start: '2026-05-25',
    week_end: '2026-05-31',
    summary:
      '主要在巩固高数微积分与 IoT 协议, MQTT 章节已完成。建议下周补一下信号量与互斥锁。',
    top_nodes: ['微分中值定理', 'MQTT', '链表'],
    weak_nodes: ['信号量', '互斥锁', '极限定义'],
    total_time_min: 196,
  },
  {
    id: 303,
    week_start: '2026-05-18',
    week_end: '2026-05-24',
    summary:
      '入门周, 完成账户初始化与第一门学科选择, 开始接触数据结构基础。',
    top_nodes: ['数组', '链表', '栈'],
    weak_nodes: ['递归思想', '复杂度分析', '指针'],
    total_time_min: 132,
  },
]

// ============================================================
// 公共 fetch 函数 —— 形状与 axios 一致
// ============================================================
export async function fetchResourceHistory(): Promise<{
  data: { items: ResourceHistoryItem[] }
}> {
  await sleep(LATENCY_MS)
  return { data: { items: MOCK_RESOURCE_HISTORY } }
}

export async function fetchExerciseRecords(): Promise<{
  data: { items: ExerciseRecord[] }
}> {
  await sleep(LATENCY_MS)
  return { data: { items: MOCK_EXERCISE_RECORDS } }
}

export async function fetchReports(): Promise<{
  data: { items: WeeklyReport[] }
}> {
  await sleep(LATENCY_MS)
  return { data: { items: MOCK_REPORTS } }
}
