<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMasteryStore } from '@/stores/mastery'
import { getKnowledgeGraph } from '@/api/learning'
import { getNodeBlurb } from '@/api/mocks/knowledgeGraph'
import { formatRelative } from '@/utils/format'
import type { KnowledgeGraph, SubjectCode } from '@/types/learning'
import { IconSparkle } from '@/components/icons'

/**
 * 知识星图 —— 3D WebGL 渲染的知识图谱可视化
 *
 *   渲染引擎: 3d-force-graph (Three.js + d3-force-3d)
 *   节点颜色: 按 mastery (0-100) 从灰 (#9ca3af) → 蓝 (#1d4ed8) 渐变
 *   节点大小: 按 difficulty 缩放 (4 + difficulty * 2.4)
 *   边颜色:   按 relation type 给 9 种颜色
 *   交互:     hover 浮窗, click 邻居高亮 + 相机飞入 + 详情抽屉
 *
 *   学科切换: 顶部 select, 默认取 mySubjects 第一个
 *   mastery:  后端 API 返回 + Pinia overlay (练习后实时更新)
 */

// ============================================================
// 类型
// ============================================================
interface GraphNode {
  id: string
  name: string
  type: string
  difficulty: number
  mastery: number
  x?: number
  y?: number
  z?: number
}

interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: string
}

// ============================================================
// Store & Router
// ============================================================
const currentSubject = useCurrentSubjectStore()
const masteryStore = useMasteryStore()
const router = useRouter()

// 从全局 store 读取当前学科
const currentCode = computed<SubjectCode>(() => currentSubject.code)

// ============================================================
// 图数据
// ============================================================
const graphData = ref<KnowledgeGraph | null>(null)
const loading = ref<boolean>(false)
const error = ref<string>('')

const isEmptyGraph = computed(
  () => !loading.value && !error.value && (graphData.value?.nodes.length ?? 0) === 0,
)

async function loadGraph(code: SubjectCode): Promise<void> {
  loading.value = true
  error.value = ''
  graphData.value = null
  try {
    const { data } = await getKnowledgeGraph(code)
    graphData.value = data
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Load failed'
  } finally {
    loading.value = false
  }
}

// ============================================================
// Mastery 计算 (overlay 优先)
// ============================================================
function resolveMastery(n: GraphNode): number {
  if (!currentCode.value) return n.mastery
  const overlay = masteryStore.getNodeMastery(currentCode.value, n.id)
  if (overlay !== null) return overlay
  return n.mastery
}

// ============================================================
// 3D Graph 实例
// ============================================================
const graphContainerRef = ref<HTMLElement | null>(null)
const labelsContainerRef = ref<HTMLElement | null>(null)
let graphInstance: ForceGraph3D<GraphNode, GraphLink> | null = null

// 交互状态
const hoveredNode = ref<GraphNode | null>(null)
const selectedNode = ref<GraphNode | null>(null)
let highlightNodes = new Set<GraphNode>()
let highlightLinks = new Set<GraphLink>()

// DOM 标签
let labelElements = new Map<string, HTMLElement>()
let labelRafId: number | null = null

// ============================================================
// 视觉映射 (ported from demo)
// ============================================================
const RELATION_COLORS: Record<string, string> = {
  contains: '#3b82f6',
  prerequisite: '#2563eb',
  used_in: '#60a5fa',
  used_by: '#93c5fd',
  implemented_by: '#bfdbfe',
  related_to: '#7dd3fc',
  implements: '#38bdf8',
  evaluates: '#1d4ed8',
  solves: '#0ea5e9',
}

function lerpMasteryColor(mastery: number): string {
  const t = Math.max(0, Math.min(100, mastery || 0)) / 100
  const r = Math.round(156 + (29 - 156) * t)
  const g = Math.round(163 + (78 - 163) * t)
  const b = Math.round(175 + (216 - 175) * t)
  return `rgb(${r},${g},${b})`
}

// ── 液体球节点 ──────────────────────────────────────
// 每个节点 = 玻璃外壳 + 内部液体（水位 = mastery）
// mastery 越高，液体越满
const liquidClipPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)

function makeLiquidSphere(node: GraphNode): THREE.Group {
  const mastery = resolveMastery(node)
  const t = Math.max(0, Math.min(100, mastery)) / 100
  const radius = 0.5 // 基础半径，nodeVal 控制整体大小

  const group = new THREE.Group()

  // 玻璃外壳
  const shellGeo = new THREE.SphereGeometry(radius, 32, 32)
  const shellMat = new THREE.MeshPhysicalMaterial({
    color: 0x93c5fd,
    transparent: true,
    opacity: 0.5,
    roughness: 0.1,
    metalness: 0,
    transmission: 0.4,
    thickness: 0.9,
    clearcoat: 1,
    clearcoatRoughness: 0.1,
  })
  const shell = new THREE.Mesh(shellGeo, shellMat)
  group.add(shell)

  // 液体：半径略小，用 clipping plane 裁掉水位以上部分
  const liquidRadius = radius * 0.88
  const liquidGeo = new THREE.SphereGeometry(liquidRadius, 32, 32)
  const liquidColor = new THREE.Color(lerpMasteryColor(mastery))
  const liquidMat = new THREE.MeshPhysicalMaterial({
    color: liquidColor,
    transparent: true,
    opacity: 0.85,
    roughness: 0.2,
    metalness: 0,
    transmission: 0.3,
    side: THREE.DoubleSide,
    clippingPlanes: [liquidClipPlane],
    clipShadows: true,
  })
  const liquid = new THREE.Mesh(liquidGeo, liquidMat)

  // 水位高度：mastery=0 时在底部，mastery=100 时满
  // 球心在原点，液体球也居中，但通过 clip plane 只保留 y <= waterLevel 的部分
  // waterLevel 从 -liquidRadius (空) 到 +liquidRadius (满)
  const waterLevel = -liquidRadius + t * (2 * liquidRadius)
  // clipping plane: normal=(0,1,0), constant=-waterLevel → 保留 y <= waterLevel
  // THREE.Plane 的 constant 是平面方程 ax+by+cz+d=0 中的 d，plane 法线 (0,1,0)
  // 点 y=waterLevel 在平面上 → d = -waterLevel
  // 但 clipping 行为：保留 normal 指向的那一侧（即 y > waterLevel）？不，three.js clip 保留与 normal 反向的一侧
  // 实际：clippingPlanes 裁掉 normal 正方向那侧，保留 y <= waterLevel
  // 所以 normal=(0,1,0) 裁掉上方，保留下方 → 正确
  liquidMat.clippingPlanes = [new THREE.Plane(new THREE.Vector3(0, 1, 0), -waterLevel)]

  group.add(liquid)

  // 液面顶部加一个小圆盘高亮，让水位线更明显
  if (t > 0.02 && t < 0.98) {
    const surfaceRadius = Math.sqrt(liquidRadius * liquidRadius - waterLevel * waterLevel) * 0.95
    if (surfaceRadius > 0.01) {
      const surfaceGeo = new THREE.CircleGeometry(surfaceRadius, 32)
      const surfaceMat = new THREE.MeshBasicMaterial({
        color: liquidColor,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      })
      const surface = new THREE.Mesh(surfaceGeo, surfaceMat)
      surface.rotation.x = -Math.PI / 2
      surface.position.y = waterLevel + 0.003
      group.add(surface)
    }
  }

  // 高亮态：加外发光环
  if (highlightNodes.size > 0 && highlightNodes.has(node)) {
    const ringGeo = new THREE.RingGeometry(radius * 1.15, radius * 1.3, 32)
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x3b82f6,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide,
    })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.lookAt(0, 0, 0) // 面向相机方向（近似）
    group.add(ring)
  }

  return group
}

// 缓存节点对象，避免每帧重建
const nodeObjectCache = new Map<string, THREE.Group>()

function nodeThreeObject(node: GraphNode): THREE.Group {
  // mastery 变化或高亮变化时需要重建
  const key = `${node.id}:${resolveMastery(node)}:${highlightNodes.has(node)}`
  const cached = nodeObjectCache.get(key)
  if (cached) return cached

  // 清理同 id 旧缓存
  for (const [k] of nodeObjectCache) {
    if (k.startsWith(`${node.id}:`)) nodeObjectCache.delete(k)
  }

  const obj = makeLiquidSphere(node)
  // 按节点大小缩放：nodeVal 是 6~16，球体基础半径 0.5
  const scale = nodeSize(node) * 0.6
  obj.scale.setScalar(scale)
  nodeObjectCache.set(key, obj)
  return obj
}

function nodeSize(node: GraphNode): number {
  return 4 + (node.difficulty || 1) * 2.4
}

function linkColor(link: GraphLink): string {
  const base = RELATION_COLORS[link.type] ?? '#93c5fd'
  if (highlightLinks.size > 0) {
    return highlightLinks.has(link) ? base : 'rgba(147,197,253,0.10)'
  }
  return base
}

function linkOpacity(link: GraphLink): number {
  if (highlightLinks.size > 0) {
    return highlightLinks.has(link) ? 0.92 : 0.08
  }
  return 0.48
}

function linkWidth(link: GraphLink): number {
  return highlightLinks.has(link) ? 1.5 : 0.5
}

function linkParticles(link: GraphLink): number {
  return highlightLinks.has(link) ? 3 : 0
}

// ============================================================
// 高亮逻辑
// ============================================================
function getLinkNodeId(endpoint: string | GraphNode): string {
  return typeof endpoint === 'object' ? endpoint.id : endpoint
}

function setHighlight(node: GraphNode): void {
  highlightNodes = new Set([node])
  highlightLinks = new Set()
  const data = graphInstance?.graphData() as { nodes: GraphNode[]; links: GraphLink[] } | undefined
  if (!data) return
  for (const link of data.links) {
    const sId = getLinkNodeId(link.source)
    const tId = getLinkNodeId(link.target)
    if (sId === node.id || tId === node.id) {
      highlightLinks.add(link)
      const other = data.nodes.find((n) => n.id === (sId === node.id ? tId : sId))
      if (other) highlightNodes.add(other)
    }
  }
  refreshAccessors()
}

function clearHighlight(): void {
  highlightNodes = new Set()
  highlightLinks = new Set()
  refreshAccessors()
}

function refreshAccessors(): void {
  if (!graphInstance) return
  // 清空缓存让 nodeThreeObject 重建（高亮态变化需要重建节点对象）
  nodeObjectCache.clear()
  // 3d-force-graph 的 nodeThreeObject() 在类型定义里只有 setter 重载 (require 1 arg),
  // 但运行时可以当 getter 调用. 这里 cast any 强制通过编译, 效果: 把当前 setter
  // 重新赋值一遍, 触发节点重建.
  const inst = graphInstance as any
  if (typeof inst.nodeThreeObject === 'function' && inst.nodeThreeObject.length === 0) {
    inst.nodeThreeObject(inst.nodeThreeObject())
  }
  inst.linkColor(inst.linkColor())
  inst.linkWidth(inst.linkWidth())
  inst.linkOpacity(inst.linkOpacity())
  inst.linkDirectionalParticles(inst.linkDirectionalParticles())
}

// ============================================================
// DOM 标签覆盖层
// ============================================================
function rebuildLabels(): void {
  const container = labelsContainerRef.value
  if (!container) return
  container.innerHTML = ''
  labelElements.clear()
  const data = graphInstance?.graphData() as { nodes: GraphNode[] } | undefined
  if (!data) return
  for (const node of data.nodes) {
    const el = document.createElement('div')
    el.className = 'node-label'
    el.textContent = node.name
    container.appendChild(el)
    labelElements.set(node.id, el)
  }
  scheduleLabelUpdates()
}

function updateLabels(): void {
  if (!graphInstance) {
    labelRafId = null
    return
  }
  const data = graphInstance.graphData() as { nodes: GraphNode[] }
  labelElements.forEach((el, nodeId) => {
    const node = data.nodes.find((n) => n.id === nodeId)
    if (!node || !Number.isFinite(node.x) || !Number.isFinite(node.y) || !Number.isFinite(node.z)) {
      el.style.display = 'none'
      return
    }
    const coords = graphInstance!.graph2ScreenCoords(node.x!, node.y!, node.z!)
    if (!coords || !Number.isFinite(coords.x) || !Number.isFinite(coords.y)) {
      el.style.display = 'none'
      return
    }
    el.style.display = 'block'
    el.style.left = `${coords.x}px`
    el.style.top = `${coords.y + 8 + (node.difficulty || 1) * 2}px`
    el.style.opacity = highlightNodes.size > 0 && !highlightNodes.has(node) ? '0.35' : '0.96'
    el.style.zIndex = highlightNodes.has(node) ? '3' : '1'
  })
  labelRafId = requestAnimationFrame(updateLabels)
}

function scheduleLabelUpdates(): void {
  if (labelRafId !== null) return
  labelRafId = requestAnimationFrame(updateLabels)
}

// ============================================================
// 数据装载
// ============================================================
function buildPayload(g: KnowledgeGraph): { nodes: GraphNode[]; links: GraphLink[] } {
  return {
    nodes: g.nodes.map((n) => ({
      id: n.id,
      name: n.name,
      type: n.type,
      difficulty: n.difficulty,
      mastery: n.mastery ?? 0,
    })),
    links: g.relations.map((r) => ({
      source: r.source,
      target: r.target,
      type: r.type,
    })),
  }
}

async function feedData(): Promise<void> {
  if (!graphData.value) return
  // 等 v-show 让 canvas 可见后再初始化/更新, 保证 Three.js 有正确尺寸
  await nextTick()
  if (!graphInstance && graphContainerRef.value) {
    initGraph(graphContainerRef.value)
  }
  if (!graphInstance) return
  graphInstance
    .width(graphContainerRef.value!.clientWidth)
    .height(graphContainerRef.value!.clientHeight)
  graphInstance.graphData(buildPayload(graphData.value))
  rebuildLabels()
  setTimeout(() => graphInstance?.zoomToFit(1200, 80), 300)
}

// ============================================================
// 交互处理
// ============================================================
function handleNodeClick(node: GraphNode): void {
  setHighlight(node)
  selectedNode.value = selectedNode.value?.id === node.id ? null : node
  // Camera fly-to
  if (graphInstance && node.x != null && node.y != null && node.z != null) {
    const distance = 160
    const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1)
    graphInstance.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node as any,
      1000,
    )
  }
}

function handleNodeHover(node: GraphNode | null): void {
  hoveredNode.value = node
}

function handleBackgroundClick(): void {
  clearHighlight()
  selectedNode.value = null
}

// ============================================================
// 详情抽屉
// ============================================================
// ESC 关闭
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && selectedNode.value) {
    selectedNode.value = null
  }
}

function closeDrawer(): void {
  selectedNode.value = null
}

// 节点简介
const selectedBlurb = computed<string>(() => {
  const n = selectedNode.value
  if (!n) return ''
  return getNodeBlurb(n.id, n.name, n.type, n.difficulty)
})

// mastery 详情
const selectedMasteryMeta = computed<{
  mastery: number | null
  updatedAt: number | null
  hasOverlay: boolean
}>(() => {
  const n = selectedNode.value
  if (!n) return { mastery: null, updatedAt: null, hasOverlay: false }
  if (!currentCode.value) return { mastery: n.mastery ?? null, updatedAt: null, hasOverlay: false }
  const bucket = masteryStore.masteryMap[currentCode.value]
  const overlay = bucket?.[n.id]
  if (overlay) {
    return { mastery: overlay.mastery, updatedAt: overlay.updated_at, hasOverlay: true }
  }
  return { mastery: n.mastery ?? null, updatedAt: null, hasOverlay: false }
})

// 关系分组
interface ConnGroup {
  key: string
  label: string
  hint: string
  items: GraphNode[]
}

const connectionGroups = computed<ConnGroup[]>(() => {
  const n = selectedNode.value
  if (!n || !graphInstance) return []
  const data = graphInstance.graphData() as { nodes: GraphNode[]; links: GraphLink[] }
  const id = n.id

  interface Buckets {
    prereq: Set<GraphNode>
    nextStep: Set<GraphNode>
    contains: Set<GraphNode>
    belongsTo: Set<GraphNode>
    apps: Set<GraphNode>
    uses: Set<GraphNode>
    usedBy: Set<GraphNode>
    related: Set<GraphNode>
  }

  const buckets: Buckets = {
    prereq: new Set(),
    nextStep: new Set(),
    contains: new Set(),
    belongsTo: new Set(),
    apps: new Set(),
    uses: new Set(),
    usedBy: new Set(),
    related: new Set(),
  }

  for (const link of data.links) {
    const sId = getLinkNodeId(link.source)
    const tId = getLinkNodeId(link.target)
    const out = sId === id
    const inn = tId === id
    if (!out && !inn) continue
    const otherId = out ? tId : sId
    const other = data.nodes.find((m) => m.id === otherId)
    if (!other) continue

    switch (link.type) {
      case 'prerequisite':
        if (out) buckets.prereq.add(other)
        else buckets.nextStep.add(other)
        break
      case 'contains':
        if (out) buckets.contains.add(other)
        else buckets.belongsTo.add(other)
        break
      case 'used_by':
      case 'solves':
        if (out) buckets.apps.add(other)
        else buckets.usedBy.add(other)
        break
      case 'used_in':
        if (out) buckets.uses.add(other)
        else buckets.usedBy.add(other)
        break
      case 'implements':
        if (out) buckets.apps.add(other)
        else buckets.usedBy.add(other)
        break
      case 'implemented_by':
        if (out) buckets.usedBy.add(other)
        else buckets.apps.add(other)
        break
      case 'evaluates':
        buckets.related.add(other)
        break
      case 'related_to':
      default:
        buckets.related.add(other)
        break
    }
  }

  const groups: ConnGroup[] = [
    { key: 'prereq', label: '前置依赖', hint: '建议先掌握', items: [...buckets.prereq] },
    { key: 'nextStep', label: '进阶方向', hint: '掌握本节点后可学', items: [...buckets.nextStep] },
    { key: 'belongsTo', label: '所属', hint: '更高层结构', items: [...buckets.belongsTo] },
    { key: 'contains', label: '包含', hint: '展开的子节点', items: [...buckets.contains] },
    { key: 'apps', label: '应用场景', hint: '实际工程中的用途', items: [...buckets.apps] },
    { key: 'uses', label: '使用了', hint: '依赖的其他知识', items: [...buckets.uses] },
    { key: 'usedBy', label: '被使用', hint: '哪些算法/结构用到本节点', items: [...buckets.usedBy] },
    { key: 'related', label: '相关', hint: '横向参考', items: [...buckets.related] },
  ]
  return groups.filter((g) => g.items.length > 0)
})

// AI 助教
function askAITutor(): void {
  const n = selectedNode.value
  if (!n) return
  router.push({
    path: '/app/dialog',
    query: { prefill: `请详细介绍一下「${n.name}」, 包括原理、应用场景和常见易错点。` },
  })
}

// 点击关系节点 → 切换选中 + 相机飞入
function selectRelated(node: GraphNode): void {
  const data = graphInstance?.graphData() as { nodes: GraphNode[] } | undefined
  const real = data?.nodes.find((m) => m.id === node.id)
  if (real) {
    selectedNode.value = real
    setHighlight(real)
    if (graphInstance && real.x != null && real.y != null && real.z != null) {
      const distRatio = 1 + 160 / Math.hypot(real.x || 1, real.y || 1, real.z || 1)
      graphInstance.cameraPosition(
        { x: (real.x || 0) * distRatio, y: (real.y || 0) * distRatio, z: (real.z || 0) * distRatio },
        real as any,
        1000,
      )
    }
  }
}

// ============================================================
// 初始化 3D Graph
// ============================================================
function initGraph(element: HTMLElement): void {
  graphInstance = new ForceGraph3D<GraphNode, GraphLink>(element)
    .backgroundColor('#eef6ff')
    .nodeLabel((n: GraphNode) => `${n.name} | mastery: ${resolveMastery(n)}`)
    .nodeVal(nodeSize)
    .nodeThreeObject(nodeThreeObject)
    .nodeThreeObjectExtend(() => false)
    .linkColor(linkColor)
    .linkOpacity(linkOpacity)
    .linkWidth(linkWidth)
    .linkDirectionalParticles(linkParticles)
    .linkDirectionalParticleWidth(2.4)
    .onNodeClick(handleNodeClick)
    .onNodeHover(handleNodeHover)
    .onBackgroundClick(handleBackgroundClick)

  // 启用 WebGL local clipping（clippingPlanes 需要）
  // 3d-force-graph 的 renderer() 不在类型声明里, 通过 cast 拿到 Three.js renderer
  const renderer = (graphInstance as any).renderer?.()
  if (renderer) renderer.localClippingEnabled = true

  // Force tuning (from demo)
  const chargeForce = graphInstance!.d3Force('charge')
  if (chargeForce) chargeForce.strength(-190)
  const linkForce = graphInstance!.d3Force('link')
  if (linkForce) linkForce.distance((link: GraphLink) => (link.type === 'contains' ? 30 : 50))
}

function onResize(): void {
  if (graphInstance && graphContainerRef.value) {
    graphInstance
      .width(graphContainerRef.value.clientWidth)
      .height(graphContainerRef.value.clientHeight)
    scheduleLabelUpdates()
  }
}

// ============================================================
// Watchers
// ============================================================
// 学科切换 → 重新加载图数据
watch(currentCode, (code) => loadGraph(code))

// 数据加载后喂给 3D 引擎
watch(graphData, () => feedData())

// mastery overlay 实时更新 (练习后)
watch(() => masteryStore.masteryMap, () => {
  if (!graphInstance) return
  refreshAccessors()
}, { deep: true })

// ============================================================
// Lifecycle
// ============================================================
onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
  // 不在此处 initGraph — canvas 此时 v-show=none, 尺寸为 0
  // 由 feedData() 在数据到达 + canvas 可见后初始化
  loadGraph(currentCode.value)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  if (labelRafId !== null) {
    cancelAnimationFrame(labelRafId)
    labelRafId = null
  }
  if (graphInstance) {
    graphInstance._destructor()
    graphInstance = null
  }
})
</script>

<template>
  <div class="x-galaxy">
    <!-- LOADING -->
    <div v-if="loading" class="x-state">
      <p class="x-eyebrow x-eyebrow-mute">LOADING</p>
      <p class="x-state-msg">正在排列星图…</p>
    </div>

    <!-- ERROR -->
    <div v-else-if="error" class="x-state x-state-error">
      <p class="x-eyebrow x-eyebrow-mute">ERROR</p>
      <p class="x-state-msg">× {{ error }}</p>
      <button class="x-btn-link" @click="loadGraph(currentCode)">Retry →</button>
    </div>

    <!-- EMPTY -->
    <div v-else-if="isEmptyGraph" class="x-state">
      <p class="x-eyebrow x-eyebrow-mute">EMPTY</p>
      <p class="x-state-msg">该学科暂无知识图数据。</p>
      <p class="x-state-hint">请先在「学科管理」中添加该学科。</p>
    </div>

    <!-- 3D WebGL canvas (fullscreen) -->
    <div
      v-show="!loading && !error && !isEmptyGraph"
      ref="graphContainerRef"
      class="x-graph-3d"
    />

    <!-- DOM label overlay -->
    <div
      v-show="!loading && !error && !isEmptyGraph"
      ref="labelsContainerRef"
      class="x-labels"
    />

    <!-- HOVER CARD -->
    <transition name="x-fade">
      <aside v-if="hoveredNode" class="x-hover-card">
        <p class="x-eyebrow x-eyebrow-mute">{{ hoveredNode.type.toUpperCase() }}</p>
        <h3 class="x-hover-name">{{ hoveredNode.name }}</h3>
        <div class="x-hover-row">
          <span class="x-eyebrow x-eyebrow-mute">DIFFICULTY</span>
          <span class="x-hover-dots">
            <span v-for="i in 5" :key="i" class="x-dot" :class="{ on: i <= hoveredNode.difficulty }"></span>
          </span>
        </div>
        <div class="x-hover-row">
          <span class="x-eyebrow x-eyebrow-mute">MASTERY</span>
          <span class="x-mono">{{ resolveMastery(hoveredNode) }}/100</span>
        </div>
      </aside>
    </transition>

    <!-- DETAIL DRAWER -->
    <transition name="x-drawer">
      <aside
        v-if="selectedNode"
        class="x-drawer"
        role="dialog"
        :aria-label="`${selectedNode.name} details`"
      >
        <header class="x-drawer-head">
          <button class="x-drawer-close" @click="closeDrawer" aria-label="Close">×</button>
          <p class="x-eyebrow x-eyebrow-mute">{{ selectedNode.type.toUpperCase() }}</p>
          <h2 class="x-drawer-title">{{ selectedNode.name }}</h2>
          <div class="x-drawer-meta">
            <div class="x-meta-cell">
              <span class="x-eyebrow x-eyebrow-mute">DIFFICULTY</span>
              <span class="x-hover-dots">
                <span
                  v-for="i in 5"
                  :key="i"
                  class="x-dot"
                  :class="{ on: i <= selectedNode.difficulty }"
                ></span>
              </span>
            </div>
            <div v-if="selectedMasteryMeta.mastery !== null" class="x-meta-cell x-meta-cell-rich">
              <span class="x-eyebrow x-eyebrow-mute">MASTERY</span>
              <span class="x-mono">
                {{ selectedMasteryMeta.mastery }}/100
                <span v-if="selectedMasteryMeta.hasOverlay" class="x-overlay-dot" title="从练习出题会话更新" style="display:inline-flex;align-items:center;vertical-align:-2px;color:var(--x-primary)"><IconSparkle :size="9" /></span>
              </span>
              <span
                v-if="selectedMasteryMeta.hasOverlay && selectedMasteryMeta.updatedAt"
                class="x-meta-time"
              >{{ formatRelative(new Date(selectedMasteryMeta.updatedAt).toISOString()) }}</span>
            </div>
          </div>
        </header>

        <div class="x-drawer-body">
          <section class="x-drawer-section">
            <p class="x-eyebrow x-eyebrow-mute">ABOUT</p>
            <p class="x-drawer-blurb">{{ selectedBlurb }}</p>
          </section>

          <section
            v-for="g in connectionGroups"
            :key="g.key"
            class="x-drawer-section"
          >
            <header class="x-conn-head">
              <p class="x-eyebrow x-eyebrow-mute">{{ g.label }}</p>
              <span class="x-conn-hint">— {{ g.hint }}</span>
            </header>
            <ul class="x-conn-list">
              <li v-for="rel in g.items" :key="rel.id">
                <button type="button" class="x-conn-chip" @click="selectRelated(rel)">
                  <span class="x-conn-chip-name">{{ rel.name }}</span>
                  <span class="x-conn-chip-meta">{{ rel.type }} · d{{ rel.difficulty }}</span>
                </button>
              </li>
            </ul>
          </section>

          <section v-if="connectionGroups.length === 0" class="x-drawer-section">
            <p class="x-conn-empty">该节点暂无关联节点 (孤立)。</p>
          </section>
        </div>

        <footer class="x-drawer-foot">
          <button class="x-btn x-btn-primary" @click="askAITutor">
            找 AI 助教详聊 →
          </button>
        </footer>
      </aside>
    </transition>
  </div>
</template>

<style scoped>
.x-galaxy {
  position: relative;
  width: 100%;
  height: calc(100vh - 64px);
  overflow: hidden;
}

.x-graph-3d {
  position: absolute;
  inset: 0;
  touch-action: none;
}

.x-labels {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  overflow: hidden;
}

:deep(.node-label) {
  position: absolute;
  transform: translate(-50%, 14px);
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
  color: #184c84;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(114, 169, 234, 0.42);
  border-radius: 999px;
  padding: 3px 7px;
  box-shadow: 0 4px 14px rgba(92, 140, 197, 0.18);
  backdrop-filter: blur(4px);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.7);
}

/* === STATE === */
.x-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--x-body-mid);
}
.x-state-error .x-state-msg { color: var(--x-error); font-family: var(--x-font-mono); }
.x-state-msg { font-size: 14px; margin: 0; }
.x-state-hint {
  font-size: 12px;
  color: var(--x-mute);
  margin: 0;
}
.x-btn-link {
  background: transparent;
  border: 0;
  color: var(--x-primary);
  cursor: pointer;
  font-family: var(--x-font-mono);
  font-size: 12px;
  letter-spacing: 0.8px;
  padding: 6px 12px;
  border-radius: var(--x-rounded-pill);
}
.x-btn-link:hover { background: var(--x-primary-soft); }

/* === HOVER CARD === */
.x-hover-card {
  position: absolute;
  top: 16px;
  right: 16px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  padding: 12px 16px;
  min-width: 200px;
  box-shadow: var(--x-shadow-popover);
  z-index: 5;
}
.x-hover-name {
  font-family: var(--x-font-display);
  font-size: 16px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 6px 0 8px;
}
.x-hover-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 6px;
}
.x-hover-dots {
  display: inline-flex;
  gap: 3px;
}
.x-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--x-hairline);
}
.x-dot.on { background: var(--x-primary); }
.x-mono { font-family: var(--x-font-mono); font-size: 12px; color: var(--x-ink); }

/* === fade === */
.x-fade-enter-active,
.x-fade-leave-active {
  transition: opacity 0.12s;
}
.x-fade-enter-from,
.x-fade-leave-to { opacity: 0; }

.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

/* ============================================================
   DETAIL DRAWER
   ============================================================ */
.x-drawer {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 360px;
  max-width: 92%;
  background: var(--x-canvas);
  border-left: 1px solid var(--x-hairline);
  display: flex;
  flex-direction: column;
  z-index: 6;
  box-shadow: -8px 0 24px rgba(15, 23, 42, 0.06);
}

.x-drawer-head {
  position: relative;
  flex-shrink: 0;
  padding: 18px 20px 14px 20px;
  border-bottom: 1px solid var(--x-hairline);
}
.x-drawer-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 0;
  background: transparent;
  color: var(--x-body-mid);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.x-drawer-close:hover {
  background: var(--x-canvas-mid);
  color: var(--x-ink);
}
.x-drawer-title {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 6px 0 12px;
  letter-spacing: -0.2px;
}

.x-drawer-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.x-meta-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-meta-cell-rich .x-mono {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--x-ink);
}
.x-overlay-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--x-accent-amber);
}
.x-meta-time {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 0.4px;
  color: var(--x-mute);
  margin-top: 2px;
}

.x-drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px 16px;
}
.x-drawer-section {
  padding: 14px 0;
  border-bottom: 1px solid var(--x-hairline);
}
.x-drawer-section:last-child { border-bottom: 0; }

.x-drawer-blurb {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--x-body);
  line-height: 1.65;
}

/* === connection groups === */
.x-conn-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}
.x-conn-hint {
  font-size: 11px;
  color: var(--x-mute);
}
.x-conn-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.x-conn-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 12px;
  color: var(--x-ink);
  transition: background 0.12s, border-color 0.12s, transform 0.1s;
}
.x-conn-chip:hover {
  background: var(--x-primary-soft);
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.x-conn-chip:active { transform: scale(0.97); }
.x-conn-chip-name { font-weight: 500; }
.x-conn-chip-meta {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body-mid);
}
.x-conn-chip:hover .x-conn-chip-meta { color: var(--x-primary); }

.x-conn-empty {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
}

.x-drawer-foot {
  flex-shrink: 0;
  border-top: 1px solid var(--x-hairline);
  padding: 14px 20px;
}
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.1s;
}
.x-btn:active:not(:disabled) { transform: scale(0.98); }
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: 1px solid var(--x-primary);
  padding: 10px 18px;
}
.x-btn-primary:hover:not(:disabled) {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
}

/* drawer slide-in animation */
.x-drawer-enter-active,
.x-drawer-leave-active {
  transition: transform 0.22s cubic-bezier(0.2, 0.7, 0.2, 1), opacity 0.18s;
}
.x-drawer-enter-from,
.x-drawer-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .x-drawer-enter-active,
  .x-drawer-leave-active {
    transition: opacity 0.15s;
    transform: none;
  }
}

@media (max-width: 768px) {
  .x-drawer { width: 100%; }
}
</style>
