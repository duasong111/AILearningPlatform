// ============================================================
// 课程详情 mock —— 章节 + 每节点的 4 类学习资源
//
//   数据源: GRAPHS[code] 给节点, 我们前端按 type 分组做成 8 章节.
//   资源 (视频/PPT/百科/问答) 全部 factory 动态拼, 不维护 53 套死数据.
//
//   当前覆盖完整: data_structure (其他学科 fallback 到通用 4 章, 节点列表为空).
// ============================================================

import { GRAPHS } from './knowledgeGraph'
import type {
  Chapter,
  EncyclopediaResource,
  KnowledgeResource,
  PPTResource,
  QAResource,
  SubjectCode,
  VideoResource,
} from '@/types/learning'

// ─── 章节映射 (data_structure 专用) ─────────────────────
const DS_CHAPTERS: { id: string; name: string; description: string; nodeIds: string[] }[] = [
  {
    id: 'ch-basic',
    name: '基础结构',
    description: '数组 / 链表 / 栈 / 队列 — 一切数据结构的起点',
    nodeIds: ['2', '3', '4', '5'],
  },
  {
    id: 'ch-hash-heap',
    name: '哈希与堆',
    description: '平均 O(1) 查找 + 优先级调度',
    nodeIds: ['6', '7', '21'],
  },
  {
    id: 'ch-tree',
    name: '树',
    description: '从二叉树到 B+ 树 — 8 个变体一锅端',
    nodeIds: ['8', '9', '10', '11', '12', '13', '14', '15'],
  },
  {
    id: 'ch-graph',
    name: '图与图算法',
    description: 'DFS / BFS / 最短路 / 最小生成树 / 最大流',
    nodeIds: ['16', '17', '18', '19', '20', '48', '49', '50', '51', '52'],
  },
  {
    id: 'ch-sort',
    name: '排序',
    description: '9 种排序 + 稳定性 / 内部 / 外部变体',
    nodeIds: ['34', '35', '36', '37', '38', '39', '40', '41', '42'],
  },
  {
    id: 'ch-string',
    name: '字符串',
    description: 'KMP / AC 自动机 / 字符串哈希',
    nodeIds: ['31', '32', '33'],
  },
  {
    id: 'ch-paradigm',
    name: '复杂度与算法范式',
    description: '大 O 分析 / 递归分治 / 回溯 / 动态规划 / 贪心',
    nodeIds: ['24', '25', '53', '22', '23', '54'],
  },
  {
    id: 'ch-advanced',
    name: '高级结构与现实应用',
    description: '并查集 / 线段树 / 跳表 / 布隆 + 4 大应用',
    nodeIds: ['43', '44', '45', '46', '47', '26', '27', '28', '29', '30'],
  },
]

// 通用 fallback 章节 (其他学科用 — 4 章, 节点空)
const GENERIC_CHAPTERS = [
  { id: 'g-intro',    name: '概论',         description: '学科背景 / 概念 / 适用场景', nodeIds: [] as string[] },
  { id: 'g-basic',    name: '基础',         description: '核心定义 / 入门例题',         nodeIds: [] as string[] },
  { id: 'g-mid',      name: '进阶',         description: '变体 / 复杂度 / 优化',         nodeIds: [] as string[] },
  { id: 'g-apply',    name: '实战',         description: '工程应用 / 常见坑',             nodeIds: [] as string[] },
]

// ─── 资源 factory (单节点 → 4 类资源) ───────────────────────
function buildVideoResource(nodeName: string, idx: number): VideoResource {
  const variants = [
    { suffix: '原理',  source: '学堂在线', duration: '12:34' },
    { suffix: '实例',  source: 'B站',     duration: '8:21'  },
    { suffix: '应用',  source: '慕课网',   duration: '15:07' },
  ]
  const v = variants[idx % variants.length]!
  return {
    type: 'video',
    title: `${nodeName} ${v.suffix}`,
    duration: v.duration,
    source: v.source,
    thumbnail_hue: (nodeName.charCodeAt(0) * 17) % 360,
  }
}

function buildPPTResource(nodeName: string, pageCount: number): PPTResource {
  return {
    type: 'ppt',
    title: `《${nodeName}》讲义`,
    page_count: pageCount,
    file_size: `${(pageCount * 0.15).toFixed(1)} MB`,
  }
}

function buildEncyclopediaResource(nodeName: string): EncyclopediaResource {
  return {
    type: 'encyclopedia',
    content: [
      `# ${nodeName}`,
      ``,
      `## 定义`,
      `${nodeName} 是计算机科学里的核心概念之一, 在算法/系统/工程多个层面都有应用。`,
      ``,
      `## 核心原理`,
      `本节我们用伪代码 + 例子带你看清 ${nodeName} 的工作方式, 以及它在数据流中的位置。`,
      ``,
      `### 关键步骤`,
      `1. 初始化结构 (根据具体实现)`,
      `2. 处理数据插入 / 查询 / 删除`,
      `3. 保证不变量 (平衡 / 唯一性 / 优先级 等) 始终成立`,
      ``,
      `## 复杂度`,
      `| 操作 | 平均 | 最坏 |`,
      `|------|------|------|`,
      `| 插入 | O(1) ~ O(log n) | O(n) |`,
      `| 查询 | O(1) ~ O(log n) | O(n) |`,
      `| 删除 | O(1) ~ O(log n) | O(n) |`,
      ``,
      `## 示例`,
      `下面是一段示意代码, 展示 ${nodeName} 在真实程序中的样子:`,
      ``,
      '```python',
      `# ${nodeName} 的伪代码示例`,
      `def demo_${nodeName.replace(/\s+/g, '_').toLowerCase()}():`,
      `    data = init_${nodeName}()`,
      `    data.add(1)`,
      `    return data.size()`,
      '```',
      ``,
      `## 常见误区`,
      `- 把平均复杂度和最坏复杂度混为一谈`,
      `- 忽略常数因子的实际影响`,
      `- 在不需要 ${nodeName} 的场景强行使用`,
      ``,
      `> 想要更深入的探讨, 看上面的视频系列 + 做完"问答"区的题。`,
    ].join('\n'),
  }
}

function buildQAResource(nodeName: string, hasMastery: boolean): QAResource {
  return {
    type: 'qa',
    items: [
      {
        id: `q1-${nodeName}`,
        question: `${nodeName} 和它的"近亲"在工程里怎么选? 边界在哪?`,
        answer_count: hasMastery ? 3 : 1,
        has_accepted_answer: hasMastery,
        asker: '小李',
        time_ago: '2 days ago',
      },
      {
        id: `q2-${nodeName}`,
        question: `初学者最容易在 ${nodeName} 上踩什么坑? 怎么避?`,
        answer_count: 0,
        has_accepted_answer: false,
        asker: '匿名',
        time_ago: '5h ago',
      },
      {
        id: `q3-${nodeName}`,
        question: `在刷题网站上, ${nodeName} 这类题的"标准解"通常长什么样?`,
        answer_count: 7,
        has_accepted_answer: true,
        asker: '王老师',
        time_ago: '3 weeks ago',
      },
    ],
  }
}

// ─── 资源组装 ─────────────────────────────────────────
export function buildKnowledgeResources(
  subjectCode: SubjectCode,
  nodeId: string,
  hasMastery: boolean,
): {
  videos: VideoResource[]
  ppts: PPTResource[]
  encyclopedia: EncyclopediaResource
  qa: QAResource
} {
  const node = GRAPHS[subjectCode]?.nodes.find((n) => n.id === nodeId)
  const nodeName = node?.name ?? `Node ${nodeId}`
  return {
    videos: [
      buildVideoResource(nodeName, 0),
      buildVideoResource(nodeName, 1),
    ],
    ppts: [
      buildPPTResource(nodeName, 12 + (nodeId.charCodeAt(0) % 8)),    // 12-19 页
    ],
    encyclopedia: buildEncyclopediaResource(nodeName),
    qa: buildQAResource(nodeName, hasMastery),
  }
}

// ─── 章节获取 ─────────────────────────────────────────
export function getCourseChapters(subjectCode: SubjectCode): Chapter[] {
  if (subjectCode === 'data_structure') {
    return DS_CHAPTERS.map((c, i) => ({
      id: c.id,
      name: c.name,
      description: c.description,
      order: i,
      knowledge_node_ids: c.nodeIds,
    }))
  }
  return GENERIC_CHAPTERS.map((c, i) => ({
    id: c.id,
    name: c.name,
    description: c.description,
    order: i,
    knowledge_node_ids: [],
  }))
}

/** 章节的"显示学科名" (给面包屑用) */
export function getCourseDisplayName(subjectCode: SubjectCode): string {
  const map: Record<SubjectCode, string> = {
    data_structure: '数据结构',
    cybersecurity: '网络安全',
    iot: '物联网技术',
    electrical_automation: 'Python 编程',
    mechanical_design: '操作系统',
    advanced_math: '软件工程',
    artificial_intelligence: '人工智能',
  }
  return map[subjectCode] ?? subjectCode
}

/** 学科是不是"有真实章节" (用于显"数据准备中"空态) */
export function hasChaptersFor(subjectCode: SubjectCode): boolean {
  return subjectCode === 'data_structure'
}

// 兼容 (让上层 import 顺手)
export { GRAPHS }
