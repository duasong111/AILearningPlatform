<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMasteryStore } from '@/stores/mastery'
import { getCourseChapters, getCourseDisplayName, hasChaptersFor, buildKnowledgeResources } from '@/api/mocks/courseDetail'
import { GRAPHS } from '@/api/mocks/knowledgeGraph'
import type { SubjectCode } from '@/types/learning'
import { IconNotepad, IconEncyclopedia, IconChat, IconCheck, IconSparkle, IconChevron } from '@/components/icons'

/**
 * 课程详情页 — 左右分栏嵌入式
 *
 * ┌─────────────────┬──────────────────────────────┐
 *  │  HEADER │  (无 header, 只左侧有)      │
 *  ├─────────────────┼──────────────────────────────┤
 *  │  章节列表        │  知识点面板 (Tab 切换)       │
 *  │  (左侧, 滚动)   │  (右侧, 固定高度, 滚动)     │
 *  │ │  - 节点标题 + 状态           │
 *  │ - 展开/折叠 │  - 视频/PPT/百科/问答        │
 *  │  - 节点胶囊    │                              │
 *  └─────────────────┴──────────────────────────────┘
 */

const masteryStore = useMasteryStore()

const subjectCode = ref<SubjectCode>('data_structure')
const courseName = computed(() => getCourseDisplayName(subjectCode.value))
const hasChapters = computed(() => hasChaptersFor(subjectCode.value))
const chapters = computed(() => getCourseChapters(subjectCode.value))
const graph = computed(() => GRAPHS[subjectCode.value])

// 当前选中节点
const activeNodeId = ref<string | null>(null)
const activeNodeName = ref<string>('')
const activeNodeMastery = ref<number | null>(null)
const activeTab = ref<'video' | 'ppt' | 'encyclopedia' | 'qa'>('video')

// 展开的章节
const expandedChapters = ref<Set<string>>(new Set(['ch-basic']))

// ─── helpers ──────────────────────────────────────────────
function getNodeName(nodeId: string): string {
  return graph.value.nodes.find((n) => n.id === nodeId)?.name ?? `节点 ${nodeId}`
}
function getNodeMastery(nodeId: string): number | null {
  return masteryStore.getNodeMastery(subjectCode.value, nodeId)
}
function getChapterProgress(chapterId: string) {
  const ch = chapters.value.find((c) => c.id === chapterId)
  if (!ch) return { completed: 0, total: 0, percent: 0 }
  const total = ch.knowledge_node_ids.length
  if (total === 0) return { completed: 0, total: 0, percent: 0 }
  const completed = ch.knowledge_node_ids.filter((id) => (getNodeMastery(id) ?? 0) >= 70).length
  return { completed, total, percent: Math.round((completed / total) * 100) }
}
function getOverallProgress() {
  const allIds = chapters.value.flatMap((c) => c.knowledge_node_ids)
  const total = allIds.length
  if (total === 0) return { completed: 0, total: 0, percent: 0 }
  const completed = allIds.filter((id) => (getNodeMastery(id) ?? 0) >= 70).length
  return { completed, total, percent: Math.round((completed / total) * 100) }
}

const activeResources = computed(() => {
  if (!activeNodeId.value) return null
  return buildKnowledgeResources(subjectCode.value, activeNodeId.value, (activeNodeMastery.value ?? 0) >= 70)
})

// ─── 操作 ───────────────────────────────────────────────
function toggleChapter(chapterId: string) {
  if (expandedChapters.value.has(chapterId)) {
    expandedChapters.value.delete(chapterId)
  } else {
    expandedChapters.value.add(chapterId)
  }
  expandedChapters.value = new Set(expandedChapters.value)
}

function selectNode(nodeId: string) {
  if (activeNodeId.value === nodeId) {
    activeNodeId.value = null
    return
  }
  activeNodeId.value = nodeId
  activeNodeName.value = getNodeName(nodeId)
  activeNodeMastery.value = getNodeMastery(nodeId)
  activeTab.value = 'video'
}

function masteryDotColor(mastery: number | null): string {
  if (mastery === null) return 'var(--x-hairline)'
  if (mastery >= 80) return 'var(--x-primary)'
  if (mastery >= 50) return 'var(--x-accent)'
  if (mastery >= 30) return 'var(--x-warning)'
  return 'var(--x-body-mid)'
}

function masteryLabel(mastery: number | null): string {
  if (mastery === null) return '未学'
  if (mastery >= 80) return '已掌握'
  if (mastery >= 50) return '学习中'
  if (mastery >= 30) return '初学'
  return '刚接触'
}

function progressColor(percent: number): string {
  if (percent >= 80) return 'var(--x-primary)'
  if (percent >= 50) return 'var(--x-accent)'
  if (percent > 0) return 'var(--x-warning)'
  return 'var(--x-hairline)'
}

function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3 class="xd-h3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="xd-h2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="xd-h1">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="xd-li">$1</li>')
    .replace(/`([^`]+)`/g, '<code class="xd-code">$1</code>')
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre class="xd-pre"><code>$1</code></pre>')
    .replace(/\n\n/g, '<br>')
    .replace(/^> (.+)$/gm, '<blockquote class="xd-bq">$1</blockquote>')
}

const tabs = [
  { key: 'video',        label: '视频',  icon: 'play' },
  { key: 'ppt',          label: 'PPT',  icon: 'ppt' },
  { key: 'encyclopedia', label: '百科',  icon: 'ency' },
  { key: 'qa',           label: '问答',  icon: 'chat' },
] as const
</script>

<template>
  <div class="x-view">

    <!-- ══左侧栏: Header + 章节列表 ══════════════════════ -->
    <aside class="x-left">
      <header class="x-lhd">
        <p class="x-eyebrow">学习进度</p>
        <h1 class="x-title">{{ courseName }}</h1>
        <div class="x-ov">
          <div class="x-ov-track">
            <div
              class="x-ov-fill"
              :style="{
                width: getOverallProgress().percent + '%',
                background: progressColor(getOverallProgress().percent),
              }"
            ></div>
          </div>
          <span class="x-ov-num">{{ getOverallProgress().completed }}/{{ getOverallProgress().total }}</span>
        </div>
      </header>

      <div class="x-chapters">
        <section
          v-for="ch in chapters"
          :key="ch.id"
          class="x-ch"
          :class="{ 'is-open': expandedChapters.has(ch.id) }"
        >
          <!-- 章节行 -->
          <button class="x-ch-row" @click="toggleChapter(ch.id)">
            <span class="x-ch-n">{{ ch.order + 1 }}</span>
            <span class="x-ch-name">{{ ch.name }}</span>
            <div class="x-ch-bar">
              <div
                class="x-ch-fill"
                :style="{
                  width: getChapterProgress(ch.id).percent + '%',
                  background: progressColor(getChapterProgress(ch.id).percent),
                }"
              ></div>
            </div>
            <span class="x-ch-pct">{{ getChapterProgress(ch.id).percent }}%</span>
            <span class="x-ch-arrow" :class="{ 'is-open': expandedChapters.has(ch.id) }">
              <IconChevron :size="12" />
            </span>
          </button>

          <!-- 节点列表 -->
          <div class="x-nodes" v-if="expandedChapters.has(ch.id)">
            <button
              v-for="nid in ch.knowledge_node_ids"
              :key="nid"
              class="x-node"
              :class="{
                'is-active': activeNodeId === nid,
                'is-done': (getNodeMastery(nid) ?? 0) >= 80,
              }"
              @click="selectNode(nid)"
            >
              <span
                class="x-node-dot"
                :style="{ background: masteryDotColor(getNodeMastery(nid)) }"
              ></span>
              <span class="x-node-name">{{ getNodeName(nid) }}</span>
            </button>
          </div>
        </section>
      </div>
    </aside>

    <!-- ══ 右侧栏: 知识点面板 ═════════════════════════════ -->
    <main class="x-right">
      <div v-if="activeNodeId" class="x-panel">
        <!-- 面板头部 -->
        <div class="x-ph">
          <div class="x-ph-left">
            <span
              class="x-ph-dot"
              :style="{ background: masteryDotColor(activeNodeMastery) }"
            ></span>
            <span class="x-ph-name">{{ activeNodeName }}</span>
            <span
              class="x-ph-badge"
              :class="{ 'is-done': (activeNodeMastery ?? 0) >= 80 }"
            >
              {{ (activeNodeMastery ?? 0) >= 80 ? '已掌握' : '学习中' }}
            </span>
          </div>
       </div>

        <!-- Tab 栏 -->
        <div class="x-ptabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="x-ptab"
            :class="{ 'is-active': activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            <span class="x-ptab-icon">
              <IconNotepad v-if="tab.icon === 'ppt'" :size="12" />
              <IconEncyclopedia v-else-if="tab.icon === 'ency'" :size="12" />
              <IconChat v-else-if="tab.icon === 'chat'" :size="12" />
              <svg v-else width="10" height="10" viewBox="0 0 24 24" aria-hidden="true" style="margin-left:1px"><path d="M8 5 L19 12 L8 19 Z" fill="currentColor" /></svg>
            </span>
            {{ tab.label }}
          </button>
        </div>

        <!-- 内容 -->
        <div class="x-pbody">

          <!-- 视频 -->
          <div v-if="activeTab === 'video' && activeResources" class="x-videos">
            <div
              v-for="(vid, idx) in activeResources.videos"
              :key="idx"
              class="x-vid"
            >
              <div
                class="x-vid-thumb"
                :style="{
                  background: `hsl(${(activeNodeName.charCodeAt(0) * 37 + idx * 97) % 360}, 55%, 42%)`,
                }"
              >
                <span class="x-vid-play">▶</span>
                <span class="x-vid-dur">{{ vid.duration }}</span>
              </div>
              <div class="x-vid-info">
                <p class="x-vid-title">{{ vid.title }}</p>
                <p class="x-vid-src">{{ vid.source }}</p>
              </div>
            </div>
          </div>

          <!-- PPT -->
          <div v-if="activeTab === 'ppt' && activeResources" class="x-ppt">
            <div class="x-ppt-row">
              <span class="x-ppt-icon"><IconNotepad :size="28" /></span>
              <div class="x-ppt-info">
                <p class="x-ppt-title">{{ activeResources.ppts[0]?.title }}</p>
                <p class="x-ppt-meta">
                  {{ activeResources.ppts[0]?.page_count }} 页
                  <span v-if="activeResources.ppts[0]?.file_size"> · {{ activeResources.ppts[0]?.file_size }}</span>
                </p>
              </div>
              <button class="x-btn x-btn-outline x-btn-sm">下载</button>
            </div>
          </div>

          <!-- 百科 -->
          <div v-if="activeTab === 'encyclopedia' && activeResources" class="x-ency">
            <div class="x-md" v-html="renderMarkdown(activeResources.encyclopedia.content)"></div>
          </div>

          <!-- 问答 -->
          <div v-if="activeTab === 'qa' && activeResources" class="x-qas">
            <div
              v-for="item in activeResources.qa.items"
              :key="item.id"
              class="x-qa"
            >
              <p class="x-qa-q">{{ item.question }}</p>
              <div class="x-qa-ft">
                <span>{{ item.asker }}</span>
                <span>{{ item.time_ago }}</span>
                <span
                  class="x-qa-badge"
                  :class="{ 'ok': item.has_accepted_answer }"
                >
                  <span v-if="item.has_accepted_answer" style="display:inline-flex;align-items:center;gap:3px"><IconCheck :size="11" />已解决</span>
                  <span v-else>{{ item.answer_count }} 回答</span>
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="x-empty">
        <span class="x-empty-icon"><IconSparkle :size="40" /></span>
        <p class="x-empty-tip">从左侧选择一个知识点开始学习</p>
      </div>
    </main>

  </div>
</template>

<style scoped>
/* ── 左右分栏布局══════════════════════════════════════ */
.x-view {
  display: flex;
  gap: 16px;
  padding: 20px 28px 60px;
  /* max-width: var(--x-container); */
  /* margin: 0 auto; */
  height: calc(100vh - 80px);
  align-items: flex-start;
}

/* ── 左侧栏 ═════════════════════════════════════════════ */
.x-left {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
  padding-right: 4px;
}

/* 左侧 Header */
.x-lhd {
  padding: 14px 16px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--x-body-mid);
}
.x-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.x-ov {
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-ov-track {
  flex: 1;
  height: 5px;
  background: var(--x-hairline);
  border-radius: 99px;
  overflow: hidden;
}
.x-ov-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.4s ease;
}
.x-ov-num {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
}

/* 章节列表 */
.x-chapters {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-ch {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  overflow: hidden;
}
.x-ch.is-open { border-color: var(--x-hairline-strong); }

/* 章节行 */
.x-ch-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}
.x-ch-row:hover { background: var(--x-canvas-soft); }

.x-ch-n {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--x-primary);
  color: var(--x-on-primary);
  font-family: var(--x-font-mono);
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.x-ch-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  min-width: 70px;
}
.x-ch-bar {
  flex: 1;
  height: 4px;
  background: var(--x-hairline);
  border-radius: 99px;
  overflow: hidden;
}
.x-ch-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.3s ease;
}
.x-ch-pct {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body-mid);
  min-width: 28px;
  text-align: right;
}
.x-ch-arrow {
  font-size: 9px;
  color: var(--x-body-mid);
  flex-shrink: 0;
}

/* 节点列表 */
.x-nodes {
  border-top: 1px solid var(--x-hairline);
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 8px 10px;
  background: var(--x-canvas-soft);
}
.x-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 99px;
  cursor: pointer;
  font-size: 13px;
  color: var(--x-ink);
  transition: border-color 0.1s, background 0.1s;
}
.x-node:hover { border-color: var(--x-hairline-strong); }
.x-node.is-active {
  background: var(--x-primary-soft);
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.x-node-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 0.2s;
}
.x-node-name { white-space: nowrap; }

/* ── 右侧栏 ═════════════════════════════════════════════ */
.x-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  overflow-y: auto;
}

/* 面板 */
.x-panel {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline-strong);
  border-radius: var(--x-rounded-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 面板头部 */
.x-ph {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: var(--x-canvas-soft);
  border-bottom: 1px solid var(--x-hairline);
}
.x-ph-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.x-ph-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  transition: background 0.2s;
}
.x-ph-name {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--x-ink);
}
.x-ph-badge {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 99px;
  background: var(--x-hairline);
  color: var(--x-body-mid);
  transition: background 0.2s;
}
.x-ph-badge.is-done {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}

/* Tab 栏 */
.x-ptabs {
  display: flex;
  gap: 4px;
  padding: 12px 20px 0;
  border-bottom: 1px solid var(--x-hairline);
}
.x-ptab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 15px;
  color: var(--x-body-mid);
  margin-bottom: -1px;
  transition: color 0.1s, border-color 0.1s;
}
.x-ptab:hover { color: var(--x-ink); }
.x-ptab.is-active {
  color: var(--x-primary);
  border-bottom-color: var(--x-primary);
}

/* 内容区 */
.x-pbody {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

/* 视频 */
.x-videos {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.x-vid {
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.15s;
}
.x-vid:hover { border-color: var(--x-hairline-strong); transform: translateY(-2px); }
.x-vid-thumb {
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.x-vid-play { font-size: 28px; color: rgba(255,255,255,0.9); }
.x-vid-dur {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: rgba(255,255,255,0.9);
  background: rgba(0,0,0,0.4);
  padding: 2px 7px;
  border-radius: 4px;
}
.x-vid-info { padding: 12px 14px; }
.x-vid-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.x-vid-src { font-size: 12px; color: var(--x-body-mid); margin: 0; }

/* PPT */
.x-ppt-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
}
.x-ppt-icon { color: var(--x-primary); display: inline-flex; }
.x-ppt-info { flex: 1; }
.x-ppt-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 4px;
}
.x-ppt-meta { font-size: 13px; color: var(--x-body-mid); margin: 0; }

/* 百科 */
.x-md {
  font-size: 15px;
  line-height: 1.8;
  color: var(--x-ink);
}
:deep(.xd-h1) { font-size: 22px; font-weight: 600; margin: 18px 0 10px; }
:deep(.xd-h2) { font-size: 18px; font-weight: 600; margin: 16px 0 8px; }
:deep(.xd-h3) { font-size: 16px; font-weight: 600; margin: 14px 0 6px; }
:deep(.xd-li) { margin: 4px 0; list-style: disc; margin-left: 20px; }
:deep(.xd-code) {
  font-family: var(--x-font-mono);
  font-size: 14px;
  background: var(--x-canvas-soft);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--x-accent);
}
:deep(.xd-pre) {
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
  padding: 14px;
  overflow-x: auto;
  margin: 12px 0;
}
:deep(.xd-pre code) { font-family: var(--x-font-mono); font-size: 14px; }
:deep(.xd-bq) {
  border-left: 3px solid var(--x-primary);
  padding-left: 16px;
  color: var(--x-body-mid);
  margin: 14px 0;
}

/* 问答 */
.x-qas { display: flex; flex-direction: column; gap: 12px; }
.x-qa {
  padding: 14px 18px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.1s;
}
.x-qa:hover { border-color: var(--x-hairline-strong); }
.x-qa-q {
  font-size: 15px;
  color: var(--x-ink);
  line-height: 1.6;
  margin: 0;
}
.x-qa-ft {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--x-body-mid);
}
.x-qa-badge {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--x-hairline);
  font-size: 12px;
}
.x-qa-badge.ok {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}

/* ── 空状态 ══════════════════════════════════════════════ */
.x-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 300px;
}
.x-empty-icon {
  font-size: 44px;
  color: var(--x-hairline-strong);
}
.x-empty-tip {
  font-size: 15px;
  color: var(--x-body-mid);
  margin: 0;
}

/* ── BUTTONS ══════════════════════════════════════════════ */
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.1s;
  white-space: nowrap;
}
.x-btn:active:not(:disabled) { transform: scale(0.97); }
.x-btn-outline {
  background: transparent;
  color: var(--x-ink);
  border: 1px solid var(--x-hairline);
  padding: 8px 16px;
}
.x-btn-outline:hover:not(:disabled) {
  background: var(--x-canvas);
  border-color: var(--x-hairline-strong);
}
.x-btn-sm { padding: 6px 14px; font-size: 13px; }

/* ── RESPONSIVE ══════════════════════════════════════════ */
@media (max-width: 768px) {
  .x-view {
    flex-direction: column;
    padding: 12px 12px 40px;
    height: auto;
  }
  .x-left {
    width: 100%;
    max-height: 40vh;
  }
  .x-right { height: auto; }
}
</style>