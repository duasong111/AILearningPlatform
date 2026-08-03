<script setup lang="ts">
import { inject, ref } from 'vue'
import { useExerciseRecords } from './useExerciseRecords'
import { formatRelative } from '@/utils/format'
import { getSubjectDisplayName } from '@/api/subjects'
import type { ExerciseRecord } from '@/types/learning'
import { IconCross, IconRetry, IconChevron, IconCheck, IconArrow } from '@/components/icons'

/**
 * 习题记录 Tab —— 题目 + 用户答案 + 是否正确
 *   - 卡片整体 click → 弹 "去哪儿" modal (走父级 provide 的 openPicker)
 *   - 答案展开独立: 卡片右下方 "▸ 答案" 按钮, 不冒泡到卡片
 *   - Correct / Wrong 用 success / error 色调的 pill
 */

const { items, loading, error, reload } = useExerciseRecords()
const expandedIds = ref<Set<number>>(new Set())

function toggle(id: number): void {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id)
  } else {
    expandedIds.value.add(id)
  }
  // ref<Set> 没法响应 .add/.delete, 手动触发
  expandedIds.value = new Set(expandedIds.value)
}

// 父级 LearningRecordsView provide 的 picker 触发器
type PickerItem = { kind: 'exercise'; data: ExerciseRecord }
const openPicker = inject<(item: PickerItem) => void>('openPicker')

function handleClick(r: ExerciseRecord): void {
  if (!openPicker) return
  openPicker({ kind: 'exercise', data: r })
}
</script>

<template>
  <div class="x-tab-panel">
    <!-- LOADING -->
    <div v-if="loading && items.length === 0" class="x-list">
      <div v-for="i in 3" :key="i" class="x-list-row x-list-row-skel">
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
      <p class="x-state-msg">No exercise records yet.</p>
    </div>

    <!-- LIST -->
    <div v-else class="x-list">
      <div
        v-for="r in items"
        :key="r.id"
        class="x-list-row x-list-row-clickable"
        role="button"
        tabindex="0"
        @click="handleClick(r)"
        @keydown.enter="handleClick(r)"
        @keydown.space.prevent="handleClick(r)"
      >
        <div class="x-list-time">{{ formatRelative(r.timestamp) }}</div>
        <div class="x-list-main">
          <p class="x-list-title">{{ r.question }}</p>
          <p class="x-eyebrow x-eyebrow-mute">
            {{ r.knowledge_node }} ⏤ {{ getSubjectDisplayName(r.subject) }}
          </p>
          <transition name="x-fade">
            <div v-if="expandedIds.has(r.id)" class="x-answer">
              <span class="x-eyebrow x-eyebrow-mute">ANSWER ⏤</span>
              <span class="x-answer-text">{{ r.answer }}</span>
            </div>
          </transition>
        </div>
        <div class="x-list-meta">
          <span
            class="x-pill"
            :class="r.correct ? 'is-success' : 'is-error'"
          >{{ r.correct ? 'Correct' : 'Wrong' }}</span>
          <!-- 答案展开按钮: stopPropagation 阻止冒泡到卡片的"打开 picker" -->
          <button
            class="x-answer-toggle"
            type="button"
            @click.stop="toggle(r.id)"
            :aria-expanded="expandedIds.has(r.id)"
          ><span style="display:inline-flex;align-items:center;gap:6px"><span :style="{ display:'inline-flex', transform: expandedIds.has(r.id) ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.15s' }"><IconChevron :size="10" /></span> {{ expandedIds.has(r.id) ? '收起' : '答案' }}</span></button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './tab-shared.css';

.x-list-row-btn {
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--x-hairline);
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  transition: background 0.12s;
}
.x-list-row-btn:hover {
  background: var(--x-canvas-soft);
}

.x-answer {
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--x-canvas-mid);
  border-radius: var(--x-rounded-sm);
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-ink);
}
.x-answer-text { margin-left: 6px; }

.x-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.x-pill.is-success {
  background: var(--x-success-soft);
  color: var(--x-success);
}
.x-pill.is-error {
  background: var(--x-error-soft);
  color: var(--x-error);
}

.x-fade-enter-active,
.x-fade-leave-active {
  transition: opacity 0.15s;
}
.x-fade-enter-from,
.x-fade-leave-to {
  opacity: 0;
}
</style>
