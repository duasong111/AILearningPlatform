// ============================================================
// 知识图谱 mocks —— 静态字典 + 节点简介
//
//   星图 (GalaxyView) 已迁移到后端 API, 但 CourseDetailView /
//   KnowledgePointView 仍用这里的 GRAPHS 做本地渲染.
//   后端补 GET /api/knowledge-graph/<subject>/ 后, 这两个页面也应 swap.
// ============================================================

import type { KnowledgeGraph, SubjectCode } from '@/types/learning'

// 1:1 移植自 backend/users/knowledge_map.py (data_structure_map)
const data_structure: KnowledgeGraph = {
  nodes: [
    { id: '2',  name: '数组',         type: 'structure',   difficulty: 1 },
    { id: '3',  name: '链表',         type: 'structure',   difficulty: 1 },
    { id: '4',  name: '栈',           type: 'structure',   difficulty: 1 },
    { id: '5',  name: '队列',         type: 'structure',   difficulty: 1 },
    { id: '6',  name: '哈希表',       type: 'structure',   difficulty: 2 },
    { id: '7',  name: '堆',           type: 'structure',   difficulty: 2 },
    { id: '8',  name: '树',           type: 'structure',   difficulty: 1 },
    { id: '9',  name: '二叉树',       type: 'structure',   difficulty: 1 },
    { id: '10', name: '二叉搜索树',   type: 'structure',   difficulty: 2 },
    { id: '11', name: 'AVL树',        type: 'structure',   difficulty: 3 },
    { id: '12', name: '红黑树',       type: 'structure',   difficulty: 4 },
    { id: '13', name: 'Trie树',       type: 'structure',   difficulty: 3 },
    { id: '14', name: 'B树',          type: 'structure',   difficulty: 4 },
    { id: '15', name: 'B+树',         type: 'structure',   difficulty: 4 },
    { id: '16', name: '图',           type: 'structure',   difficulty: 2 },
    { id: '17', name: 'DFS',          type: 'algorithm',   difficulty: 2 },
    { id: '18', name: 'BFS',          type: 'algorithm',   difficulty: 2 },
    { id: '19', name: 'Dijkstra',     type: 'algorithm',   difficulty: 4 },
    { id: '20', name: '拓扑排序',     type: 'algorithm',   difficulty: 3 },
    { id: '21', name: '优先队列',     type: 'concept',     difficulty: 2 },
    { id: '22', name: '回溯算法',     type: 'concept',     difficulty: 4 },
    { id: '23', name: '动态规划',     type: 'concept',     difficulty: 5 },
    { id: '24', name: '时间复杂度',   type: 'concept',     difficulty: 1 },
    { id: '25', name: '空间复杂度',   type: 'concept',     difficulty: 1 },
    { id: '26', name: 'TreeMap',      type: 'application', difficulty: 3 },
    { id: '27', name: '数据库索引',   type: 'application', difficulty: 3 },
    { id: '28', name: '搜索引擎',     type: 'application', difficulty: 3 },
    { id: '29', name: '缓存系统',     type: 'application', difficulty: 3 },
    { id: '30', name: '最短路径问题', type: 'application', difficulty: 3 },
    { id: '31', name: 'KMP算法',      type: 'algorithm',   difficulty: 3 },
    { id: '32', name: 'AC自动机',     type: 'algorithm',   difficulty: 5 },
    { id: '33', name: '字符串哈希',   type: 'algorithm',   difficulty: 2 },
    { id: '34', name: '归并排序',     type: 'algorithm',   difficulty: 2 },
    { id: '35', name: '快速排序',     type: 'algorithm',   difficulty: 2 },
    { id: '36', name: '堆排序',       type: 'algorithm',   difficulty: 2 },
    { id: '37', name: '计数排序',     type: 'algorithm',   difficulty: 2 },
    { id: '38', name: '桶排序',       type: 'algorithm',   difficulty: 2 },
    { id: '39', name: '基数排序',     type: 'algorithm',   difficulty: 3 },
    { id: '40', name: '排序稳定性',   type: 'concept',     difficulty: 2 },
    { id: '41', name: '内部排序',     type: 'concept',     difficulty: 1 },
    { id: '42', name: '外部排序',     type: 'concept',     difficulty: 3 },
    { id: '43', name: '并查集',       type: 'structure',   difficulty: 3 },
    { id: '44', name: '线段树',       type: 'structure',   difficulty: 4 },
    { id: '45', name: '树状数组',     type: 'structure',   difficulty: 4 },
    { id: '46', name: '跳表',         type: 'structure',   difficulty: 3 },
    { id: '47', name: '布隆过滤器',   type: 'structure',   difficulty: 3 },
    { id: '48', name: 'Floyd算法',    type: 'algorithm',   difficulty: 3 },
    { id: '49', name: 'Prim算法',     type: 'algorithm',   difficulty: 3 },
    { id: '50', name: 'Kruskal算法',  type: 'algorithm',   difficulty: 3 },
    { id: '51', name: 'Tarjan算法',   type: 'algorithm',   difficulty: 5 },
    { id: '52', name: '最大流',       type: 'algorithm',   difficulty: 5 },
    { id: '53', name: '递归与分治',   type: 'concept',     difficulty: 2 },
    { id: '54', name: '贪心算法',     type: 'concept',     difficulty: 3 },
  ],
  relations: [
    { source: '8',  target: '9',  type: 'contains' },
    { source: '9',  target: '10', type: 'contains' },
    { source: '10', target: '11', type: 'contains' },
    { source: '10', target: '12', type: 'contains' },
    { source: '8',  target: '13', type: 'contains' },
    { source: '8',  target: '14', type: 'contains' },
    { source: '14', target: '15', type: 'contains' },
    { source: '17', target: '16', type: 'used_in' },
    { source: '17', target: '8',  type: 'used_in' },
    { source: '17', target: '22', type: 'related_to' },
    { source: '18', target: '16', type: 'used_in' },
    { source: '18', target: '8',  type: 'used_in' },
    { source: '19', target: '16', type: 'used_in' },
    { source: '19', target: '30', type: 'solves' },
    { source: '20', target: '16', type: 'used_in' },
    { source: '7',  target: '21', type: 'implements' },
    { source: '21', target: '7',  type: 'implemented_by' },
    { source: '12', target: '26', type: 'used_by' },
    { source: '15', target: '27', type: 'used_by' },
    { source: '13', target: '28', type: 'used_by' },
    { source: '6',  target: '29', type: 'used_by' },
    { source: '10', target: '9',  type: 'prerequisite' },
    { source: '11', target: '10', type: 'prerequisite' },
    { source: '12', target: '10', type: 'prerequisite' },
    { source: '15', target: '14', type: 'prerequisite' },
    { source: '17', target: '18', type: 'related_to' },
    { source: '17', target: '19', type: 'prerequisite' },
    { source: '18', target: '19', type: 'prerequisite' },
    { source: '24', target: '2',  type: 'evaluates' },
    { source: '24', target: '3',  type: 'evaluates' },
    { source: '24', target: '6',  type: 'evaluates' },
    { source: '24', target: '7',  type: 'evaluates' },
    { source: '25', target: '2',  type: 'evaluates' },
    { source: '25', target: '3',  type: 'evaluates' },
    { source: '25', target: '16', type: 'evaluates' },
    { source: '31', target: '3',  type: 'used_in' },
    { source: '32', target: '3',  type: 'used_in' },
    { source: '32', target: '13', type: 'used_in' },
    { source: '33', target: '6',  type: 'used_in' },
    { source: '34', target: '53', type: 'prerequisite' },
    { source: '35', target: '53', type: 'prerequisite' },
    { source: '35', target: '54', type: 'prerequisite' },
    { source: '36', target: '7',  type: 'used_in' },
    { source: '37', target: '41', type: 'implements' },
    { source: '38', target: '41', type: 'implements' },
    { source: '39', target: '41', type: 'implements' },
    { source: '42', target: '37', type: 'prerequisite' },
    { source: '42', target: '38', type: 'prerequisite' },
    { source: '40', target: '34', type: 'evaluates' },
    { source: '40', target: '35', type: 'evaluates' },
    { source: '40', target: '36', type: 'evaluates' },
    { source: '43', target: '16', type: 'used_in' },
    { source: '44', target: '8',  type: 'used_in' },
    { source: '44', target: '16', type: 'used_in' },
    { source: '45', target: '8',  type: 'used_in' },
    { source: '45', target: '44', type: 'related_to' },
    { source: '46', target: '5',  type: 'implements' },
    { source: '47', target: '6',  type: 'related_to' },
    { source: '48', target: '16', type: 'used_in' },
    { source: '48', target: '19', type: 'related_to' },
    { source: '49', target: '16', type: 'used_in' },
    { source: '49', target: '50', type: 'related_to' },
    { source: '50', target: '43', type: 'used_in' },
    { source: '50', target: '16', type: 'used_in' },
    { source: '51', target: '16', type: 'used_in' },
    { source: '51', target: '17', type: 'prerequisite' },
    { source: '52', target: '16', type: 'used_in' },
    { source: '52', target: '43', type: 'used_in' },
    { source: '53', target: '17', type: 'used_in' },
    { source: '53', target: '22', type: 'used_in' },
    { source: '53', target: '23', type: 'used_in' },
    { source: '54', target: '49', type: 'used_in' },
    { source: '54', target: '50', type: 'used_in' },
  ],
}

const EMPTY: KnowledgeGraph = { nodes: [], relations: [] }

export const GRAPHS: Record<SubjectCode, KnowledgeGraph> = {
  data_structure,
  cybersecurity:           EMPTY,
  iot:                     EMPTY,
  electrical_automation:   EMPTY,
  mechanical_design:       EMPTY,
  advanced_math:           EMPTY,
  artificial_intelligence: EMPTY,
}

// key = node.id (data_structure 用 string id "2"~"54")
export const NODE_BLURBS: Record<string, string> = {
  '2':  '数组是连续内存中存放同类型元素的线性结构。随机访问 O(1), 中间插入/删除 O(n)。是几乎所有高级数据结构的底层载体。',
  '3':  '链表用指针把零散内存中的节点串起来。访问慢 O(n) 但增删快 O(1) — 当你不知道前一个节点时除外。常见变体: 单向 / 双向 / 循环。',
  '6':  '哈希表通过 hash(key) 把元素散布到桶中, 平均 O(1) 完成增删查。冲突解决两大流派: 链地址法 (拉链) 与开放寻址法 (探测)。',
  '8':  '树是层次结构的统称, 每个节点有 0~N 个子节点。从二叉树 / BST 到 B+ / Trie, 几乎所有"快速查找"问题最终都化归到某种树。',
  '12': '红黑树是一种自平衡 BST, 通过 5 条颜色规则把树高度卡在 2·log₂(n+1) 之内。Java TreeMap、C++ std::map、Linux 调度器都在用它。',
  '16': '图由节点 (vertex) 与边 (edge) 组成, 是表达「关系」最通用的结构。无向 / 有向、带权 / 不带权、稀疏 / 稠密 — 选择对应的存储 (邻接表 vs 邻接矩阵) 是图算法的第一步。',
  '23': '动态规划: 把大问题拆成会重复出现的子问题, 用表 (或滚动数组) 缓存解, 避免指数级爆炸。核心三件事: 状态定义 / 转移方程 / 边界条件。',
  '24': '时间复杂度: 算法消耗时间随输入规模 n 增长的渐进行为, 用大 O 表示。常见量级: O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2ⁿ)。',
}

// 类型对应的中文描述
const TYPE_LABEL: Record<string, string> = {
  structure:   '数据结构',
  algorithm:   '算法',
  concept:     '核心概念',
  application: '应用场景',
}

function buildFallbackBlurb(name: string, type: string, difficulty: number): string {
  const cn = TYPE_LABEL[type] ?? '知识点'
  const diffWord =
    difficulty >= 4 ? '进阶, 需要扎实的基础' :
    difficulty >= 3 ? '中等难度, 建议先掌握前置依赖' :
    difficulty >= 2 ? '入门偏中等, 多做练习' :
    '基础, 适合作为起点'
  return `${name} 是${cn}领域的重要${cn === '数据结构' ? '一员' : '一项'}, 难度等级 ${difficulty}/5 — ${diffWord}。详细原理可在 AI 助教中深入了解。`
}

export function getNodeBlurb(
  id: string,
  name: string,
  type: string,
  difficulty: number,
): string {
  return NODE_BLURBS[id] ?? buildFallbackBlurb(name, type, difficulty)
}
