<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMasteryStore } from '@/stores/mastery'
import { getCourseDisplayName, buildKnowledgeResources } from '@/api/mocks/courseDetail'
import { GRAPHS } from '@/api/mocks/knowledgeGraph'
import type { SubjectCode } from '@/types/learning'
import { IconEncyclopedia, IconChat, IconNotepad, IconCheck, IconArrow } from '@/components/icons'

/**
 * 知识点详情页 — 4 类学习资源
 *
 * 路由: /app/learning/course/:subjectCode/node/:nodeId
 *
 * 资源类型:
 *   - video    × 2  (原理/实例 系列)
 *   - ppt      × 1  (讲义)
 *   - encyclopedia × 1  (markdown 百科)
 *   - qa       × 1 (问答列表)
 */

const router = useRouter()
const route = useRoute()
const masteryStore = useMasteryStore()

const subjectCode = computed(() => route.params.subjectCode as SubjectCode)
const nodeId = computed(() => route.params.nodeId as string)
const courseName = computed(() => getCourseDisplayName(subjectCode.value))

// 节点信息
const graph = computed(() => GRAPHS[subjectCode.value])
const node = computed(() => graph.value.nodes.find((n) => n.id === nodeId.value))
const nodeName = computed(() => node.value?.name ?? `节点 ${nodeId.value}`)

// 模拟 mastery (用于显示"已掌握"等状态)
const mastery = computed(() => masteryStore.getNodeMastery(subjectCode.value, nodeId.value))

// 当前激活的 tab
const activeTab = ref<'video' | 'ppt' | 'encyclopedia' | 'qa'>('video')

// 资源数据
const resources = computed(() => buildKnowledgeResources(subjectCode.value, nodeId.value, (mastery.value ?? 0) >= 70))

// markdown 渲染 (简易处理 — 保留标题/列表, 转换代码块)
function renderMarkdown(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3 class="x-md-h3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="x-md-h2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="x-md-h1">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li class="x-md-li">$1</li>')
    .replace(/(<li.*<\/li>)/gs, '<ul class="x-md-ul">$1</ul>')
    .replace(/`([^`]+)`/g, '<code class="x-md-code">$1</code>')
    .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre class="x-md-pre"><code>$1</code></pre>')
    .replace(/\| (.+) \|/g, (match) => {
      const cells = match.split('|').filter(Boolean).map((c: string) => c.trim())
      const row = cells.map((c: string) => `<td class="x-md-td">${c}</td>`).join('')
      return `<tr class="x-md-tr">${row}</tr>`
    })
    .replace(/(<tr.*<\/tr>)/gs, '<table class="x-md-table">$1</table>')
    .replace(/\n\n/g, '<br>')
    .replace(/^> (.+)$/gm, '<blockquote class="x-md-blockquote">$1</blockquote>')
}

// 视频缩略图背景色
function videoHue(idx: number): number {
  return (nodeName.value.charCodeAt(0) * 37 + idx * 97) % 360
}

// tab 列表
const tabs = [
  { key: 'video',         label: '视频教学',  icon: 'play' },
  { key: 'ppt',           label: 'PPT讲义',  icon: 'ppt' },
  { key: 'encyclopedia',  label: '知识百科',  icon: 'ency' },
  { key: 'qa',            label: '问答',      icon: 'chat' },
] as const
</script>

<template>
  <div class="x-kp">
    <!-- HEADER -->
    <header class="x-kp-head">
      <button class="x-back-btn" @click="router.back()">
        <span style="display:inline-flex;align-items:center;gap:6px;transform:scaleX(-1)"><IconArrow :size="13" /></span>返回
      </button>
      <div class="x-head-body">
        <p class="x-eyebrow x-eyebrow-mute">{{ courseName }}</p>
        <h1 class="x-title">{{ nodeName }}</h1>
        <div class="x-kp-meta">
          <span
            class="x-mastery-badge"
            :style="{ background: mastery !== null && mastery >= 70 ? 'var(--x-primary)' : 'var(--x-hairline)' }"
          >
            {{ mastery !== null && mastery >= 70 ? '已掌握' : '学习中' }}
          </span>
          <span class="x-kp-type">{{ node?.type ?? 'concept' }}</span>
        </div>
      </div>
    </header>

    <!-- TABS -->
    <div class="x-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="x-tab"
        :class="{ 'is-active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span class="x-tab-icon">
          <IconNotepad v-if="tab.icon === 'ppt'" :size="13" />
          <IconEncyclopedia v-else-if="tab.icon === 'ency'" :size="13" />
          <IconChat v-else-if="tab.icon === 'chat'" :size="13" />
          <svg v-else width="11" height="11" viewBox="0 0 24 24" aria-hidden="true" style="margin-left:2px">
            <path d="M8 5 L19 12 L8 19 Z" fill="currentColor" />
          </svg>
        </span>
        {{ tab.label }}
      </button>
    </div>

    <!-- VIDEO TAB -->
    <div v-if="activeTab === 'video'" class="x-tab-content">
      <div class="x-video-grid">
        <div
          v-for="(vid, idx) in resources.videos"
          :key="idx"
          class="x-video-card"
        >
          <div
            class="x-video-thumb"
            :style="{
              background: `hsl(${videoHue(idx)}, 60%, 45%)`,
            }"
          >
            <span class="x-video-play">▶</span>
            <span class="x-video-duration">{{ vid.duration }}</span>
          </div>
          <div class="x-video-info">
            <h3 class="x-video-title">{{ vid.title }}</h3>
            <p class="x-video-source">{{ vid.source }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- PPT TAB -->
    <div v-if="activeTab === 'ppt'" class="x-tab-content">
      <div class="x-ppt-card">
        <div class="x-ppt-icon"><IconNotepad :size="32" /></div>
        <div class="x-ppt-info">
          <h3 class="x-ppt-title">{{ resources.ppts[0]?.title }}</h3>
          <p class="x-ppt-meta">
            {{ resources.ppts[0]?.page_count }} 页
            <span v-if="resources.ppts[0]?.file_size"> · {{ resources.ppts[0]?.file_size }}</span>
          </p>
        </div>
        <button class="x-btn x-btn-primary x-btn-sm">下载讲义</button>
      </div>
    </div>

    <!-- ENCYCLOPEDIA TAB -->
    <div v-if="activeTab === 'encyclopedia'" class="x-tab-content">
      <div class="x-ency">
        <div
          class="x-md-body"
          v-html="renderMarkdown(resources.encyclopedia.content)"
        ></div>
      </div>
    </div>

    <!-- QA TAB -->
    <div v-if="activeTab === 'qa'" class="x-tab-content">
      <div class="x-qa-list">
        <article
          v-for="item in resources.qa.items"
          :key="item.id"
          class="x-qa-item"
        >
          <div class="x-qa-q">{{ item.question }}</div>
          <div class="x-qa-footer">
            <span class="x-qa-asker">{{ item.asker }}</span>
            <span class="x-qa-time">{{ item.time_ago }}</span>
            <span
              class="x-qa-badge"
              :class="{ 'is-answered': item.has_accepted_answer }"
            >
              <span v-if="item.has_accepted_answer" style="display:inline-flex;align-items:center;gap:3px"><IconCheck :size="11" />已解决</span>
              <span v-else>{{ item.answer_count }} 回答</span>
            </span>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<style scoped>
.x-kp {
  padding: 32px 40px 48px;
  max-width: var(--x-container);
  margin: 0 auto;
}

/* === HEADER === */
.x-kp-head {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}
.x-back-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 13px;
  color: var(--x-body-mid);
  padding: 0;
  text-align: left;
  transition: color 0.12s;
}
.x-back-btn:hover { color: var(--x-ink); }
.x-head-body {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-title {
  font-family: var(--x-font-display);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: var(--x-ink);
  margin: 0;
}
.x-kp-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-mastery-badge {
  font-size: 11px;
  font-family: var(--x-font-mono);
  padding: 2px 8px;
  border-radius: 99px;
  color: white;
  transition: background 0.2s;
}
.x-kp-type {
  font-size: 12px;
  color: var(--x-body-mid);
}

/* === TABS === */
.x-tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--x-hairline);
  margin-bottom: 24px;
}
.x-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 14px;
  color: var(--x-body-mid);
  transition: color 0.12s, border-color 0.12s;
  margin-bottom: -1px;
}
.x-tab:hover { color: var(--x-ink); }
.x-tab.is-active {
  color: var(--x-primary);
  border-bottom-color: var(--x-primary);
}
.x-tab-icon { display: inline-flex; align-items: center; }

/* === TAB CONTENT === */
.x-tab-content {
  animation: x-fade-in 0.15s ease;
}
@keyframes x-fade-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* VIDEO */
.x-video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.x-video-card {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  overflow: hidden;
  transition: border-color 0.12s, transform 0.12s;
  cursor: pointer;
}
.x-video-card:hover {
  border-color: var(--x-hairline-strong);
  transform: translateY(-2px);
}
.x-video-thumb {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.x-video-play {
  font-size: 32px;
  color: rgba(255,255,255,0.9);
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.x-video-duration {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: rgba(255,255,255,0.9);
  background: rgba(0,0,0,0.4);
  padding: 2px 6px;
  border-radius: 4px;
}
.x-video-info { padding: 12px 16px; }
.x-video-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 4px;
}
.x-video-source {
  font-size: 12px;
  color: var(--x-body-mid);
  margin: 0;
}

/* PPT */
.x-ppt-card {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.x-ppt-icon { color: var(--x-primary); display: inline-flex; }
.x-ppt-info { flex: 1; }
.x-ppt-title {
  font-family: var(--x-font-display);
  font-size: 16px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 4px;
}
.x-ppt-meta {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
}

/* ENCYCLOPEDIA */
.x-ency {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 32px;
}
.x-md-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--x-ink);
}
:deep(.x-md-h1) { font-size: 20px; font-weight: 600; margin: 24px 0 12px; }
:deep(.x-md-h2) { font-size: 17px; font-weight: 600; margin: 20px 0 10px; }
:deep(.x-md-h3) { font-size: 15px; font-weight: 600; margin: 16px 0 8px; }
:deep(.x-md-ul) { padding-left: 20px; margin: 8px 0; }
:deep(.x-md-li) { margin: 4px 0; list-style: disc; }
:deep(.x-md-code) {
  font-family: var(--x-font-mono);
  font-size: 13px;
  background: var(--x-canvas-soft);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--x-accent);
}
:deep(.x-md-pre) {
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}
:deep(.x-md-pre code) {
  font-family: var(--x-font-mono);
  font-size: 13px;
  color: var(--x-ink);
}
:deep(.x-md-table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
  font-size: 13px;
}
:deep(.x-md-tr) { border-bottom: 1px solid var(--x-hairline); }
:deep(.x-md-td) { padding: 8px 12px; }
:deep(.x-md-blockquote) {
  border-left: 3px solid var(--x-primary);
  padding-left: 16px;
  color: var(--x-body-mid);
  margin: 16px 0;
}

/* QA */
.x-qa-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.x-qa-item {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color 0.12s;
}
.x-qa-item:hover { border-color: var(--x-hairline-strong); }
.x-qa-q {
  font-size: 14px;
  color: var(--x-ink);
  line-height: 1.6;
}
.x-qa-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--x-body-mid);
}
.x-qa-badge {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 99px;
  background: var(--x-canvas-soft);
  font-size: 11px;
}
.x-qa-badge.is-answered {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}

/* BUTTONS */
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.1s;
  white-space: nowrap;
}
.x-btn:active:not(:disabled) { transform: scale(0.98); }
.x-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: 1px solid var(--x-primary);
  padding: 9px 18px;
}
.x-btn-primary:hover:not(:disabled) {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
}
.x-btn-sm { padding: 6px 14px; font-size: 12px; }

/* UTILS */
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

@media (max-width: 768px) {
  .x-kp { padding: 24px 16px 40px; }
  .x-tabs { overflow-x: auto; }
  .x-video-grid { grid-template-columns: 1fr; }
}
</style>