<script setup lang="ts">
import { inject } from 'vue'
import { useResourceHistory } from './useResourceHistory'
import { formatRelative } from '@/utils/format'
import { getSubjectDisplayName } from '@/api/subjects'
import type { ResourceHistoryItem } from '@/types/learning'
import { IconCross, IconRetry, IconArrow, IconGrid, IconNotepad, IconQuote, IconHourglass } from '@/components/icons'

/**
 * 资源历史 Tab —— 用户看过的视频/文章/PDF/交互式课件
 *   数据: mock (api/learning.ts → api/mocks/learningRecords.ts)
 *
 *   行 click → 调父级 provide 的 openPicker, 弹 "去哪儿" modal.
 *   父级没 provide 时 (独立运行/测试), 安全降级为无操作.
 */

const { items, loading, error, reload } = useResourceHistory()

// 父级 LearningRecordsView provide 的 picker 触发器
type PickerItem = { kind: 'resource'; data: ResourceHistoryItem }
const openPicker = inject<(item: PickerItem) => void>('openPicker')

function handleClick(r: ResourceHistoryItem): void {
  if (!openPicker) return
  openPicker({ kind: 'resource', data: r })
}

// type icon —— 不引图标库
const TYPE_GLYPH: Record<string, string> = {
  video:       '▶',
  article:     '☰',
  pdf:         '◰',
  interactive: '◐',
}
const TYPE_ICON: Record<string, typeof IconGrid> = {
  video:       IconHourglass,
  article:     IconNotepad,
  pdf:         IconQuote,
  interactive: IconGrid,
}
const TYPE_LABEL: Record<string, string> = {
  video:       'VIDEO',
  article:     'ARTICLE',
  pdf:         'PDF',
  interactive: 'INTERACTIVE',
}
</script>

<template>
  <div class="x-tab-panel">
    <!-- LOADING -->
    <div v-if="loading && items.length === 0" class="x-list">
      <div v-for="i in 4" :key="i" class="x-list-row x-list-row-skel">
        <div class="x-skel x-skel-time"></div>
        <div class="x-skel x-skel-main"></div>
        <div class="x-skel x-skel-meta"></div>
      </div>
    </div>

    <!-- ERROR -->
    <div v-else-if="error" class="x-state-error">
      <p class="x-state-msg"><span style="display:inline-flex;align-items:center;gap:6px"><IconCross :size="11" /> {{ error }}</span></p>
      <button class="x-btn-link" @click="reload"><span style="display:inline-flex;align-items:center;gap:6px"><IconRetry :size="11" /> Retry</span></button>
    </div>

    <!-- EMPTY -->
    <div v-else-if="items.length === 0" class="x-state-empty">
      <p class="x-eyebrow x-eyebrow-mute">EMPTY</p>
      <p class="x-state-msg">No resource history yet.</p>
    </div>

    <!-- LIST -->
    <div v-else class="x-list">
      <div
        v-for="r in items"
        :key="r.id"
        class="x-list-row is-clickable"
        role="button"
        tabindex="0"
        @click="handleClick(r)"
        @keydown.enter="handleClick(r)"
        @keydown.space.prevent="handleClick(r)"
      >
        <div class="x-list-time">{{ formatRelative(r.timestamp) }}</div>
        <div class="x-list-main">
          <p class="x-list-title">
            <span class="x-list-glyph" style="display:inline-flex;align-items:center;color:var(--x-primary)"><component :is="TYPE_ICON[r.type] ?? IconNotepad" :size="13" /></span>
            {{ r.resource_name }}
          </p>
          <p class="x-eyebrow x-eyebrow-mute">
            {{ TYPE_LABEL[r.type] }} ⏤ {{ getSubjectDisplayName(r.subject) }}
          </p>
        </div>
        <div class="x-list-meta">{{ r.duration_min }}m</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './tab-shared.css';
</style>
