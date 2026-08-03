<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import { useRoute } from 'vue-router'
import LearningStatsOverview from './LearningStatsOverview.vue'
import ActionPickerDialog from './ActionPickerDialog.vue'
import ResourceHistoryTab from './records/ResourceHistoryTab.vue'
import ExerciseRecordsTab from './records/ExerciseRecordsTab.vue'
import ReportsTab from './records/ReportsTab.vue'
import type { ResourceHistoryItem, ExerciseRecord } from '@/types/learning'

/**
 * 学习记录 —— 三个 Tab 的 tabbed view
 *
 *   Tab 状态写在 URL ?tab= 里, 而不是本地 ref —— 这样:
 *     1) 浏览器后退能回到上一个 Tab
 *     2) /app/learning/records?tab=reports 是可分享 deep link
 *     3) 进入页面时如果没带 tab, 默认走 'history'
 *
 *   keep-alive 包裹 3 个 panel: 保留切换前的滚动位置与展开/答案状态.
 *   每个 panel 内部的 useXxx() 在第一次 mount 时 fetch, 之后 alive 不重 fetch.
 *   想强刷的话, Tab 组件自己暴露了 reload() (用于 Retry 按钮).
 *
 *   跨 tab 共享的"去哪儿"弹窗 (ActionPickerDialog):
 *     资源/答题 行被点击 → 调 provide 的 openPicker(item) → 这里打开 dialog
 *     dialog 关闭或跳转都 reset state.
 */

const route = useRoute()

// 允许的 Tab key —— 收到非法值时 fallback 到 'history'
type TabKey = 'history' | 'exercises' | 'reports'
const TABS: { key: TabKey; label: string; comp: unknown }[] = [
  { key: 'history',   label: '资源历史', comp: ResourceHistoryTab  },
  { key: 'exercises', label: '习题记录', comp: ExerciseRecordsTab  },
  { key: 'reports',   label: '我的报告', comp: ReportsTab          },
]

const activeKey = computed<TabKey>(() => {
  const raw = route.query.tab
  if (raw === 'exercises' || raw === 'reports' || raw === 'history') return raw
  return 'history'
})

const activeComponent = computed(
  () => TABS.find((t) => t.key === activeKey.value)?.comp ?? ResourceHistoryTab,
)

// ============================================================
// Picker dialog 状态 —— 跨 tab 共享, 由父级渲染, 子 tab 用 provide
// 调 openPicker({ kind, data }) 触发, 选目的地跳转后 close
// ============================================================
type PickerItem =
  | { kind: 'resource'; data: ResourceHistoryItem }
  | { kind: 'exercise'; data: ExerciseRecord }

const pickerOpen  = ref(false)
const pickerItem  = ref<PickerItem | null>(null)

function openPicker(item: PickerItem): void {
  pickerItem.value = item
  pickerOpen.value = true
}
function closePicker(): void {
  pickerOpen.value = false
  // 让 leave 动画走完再清 item, 否则 dialog 内容"瞬间消失"很突兀
  setTimeout(() => { pickerItem.value = null }, 200)
}

// inject key (typed), 子 tab 用同样的 key 拿
provide('openPicker', openPicker)
</script>

<template>
  <div class="x-records">
    <header class="x-records-head">
      <p class="x-eyebrow x-eyebrow-mute">LEARNING ⏤ RECORDS</p>
      <h1 class="x-records-title">学习记录</h1>
      <p class="x-records-subtitle">
        看过的资源、做过的题、每周给你的报告 —— 你的学习时光留痕。
      </p>
    </header>

    <!-- 总览区: 跨 3 tab 共享的可视化 (4 数字 + 学科分布 + 7 天热力 + 薄弱节点)
         不在 <keep-alive> 内, 每次进页面都重新 mount, 数字与 chart 都反映最新数据 -->
    <LearningStatsOverview />

    <!-- TABS -->
    <nav class="x-tabs" aria-label="Records tabs">
      <router-link
        v-for="t in TABS"
        :key="t.key"
        class="x-tab"
        :class="{ 'is-active': activeKey === t.key }"
        :to="{ query: { ...route.query, tab: t.key } }"
        replace
      >
        {{ t.label }}
      </router-link>
    </nav>

    <!-- PANEL -->
    <div class="x-records-panel">
      <transition name="x-tab-fade" mode="out-in">
        <!--
          注意: 不要在 <component> 上加 :key="activeKey"!
          keep-alive 靠组件身份判断缓存: 加 key 会让 Vue 把它当成"新组件"
          → 切回去时重新 mount → 数据重新 fetch → 整个面板闪烁.
          去掉 key, 切 tab 时 Vue 只切换 :is, keep-alive 复用缓存实例.
        -->
        <keep-alive>
          <component :is="activeComponent" />
        </keep-alive>
      </transition>
    </div>

    <!-- 跨 tab 共享的"去哪儿"弹窗 —— 由各 tab 的行 click 触发 -->
    <ActionPickerDialog
      v-model:open="pickerOpen"
      :item="pickerItem"
      @update:open="closePicker"
    />
  </div>
</template>

<style scoped>
.x-records {
  padding: 32px 40px 48px;
  /* max-width: var(--x-container); */
  margin: 0 auto;
}

/* === HEAD === */
.x-records-head {
  margin-bottom: 24px;
}
.x-records-title {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 8px 0 6px;
}
.x-records-subtitle {
  font-size: 14px;
  color: var(--x-body);
  margin: 0;
}

/* === TABS === */
.x-tabs {
  display: flex;
  gap: 4px;
  justify-content: center;     /* tabs 居中 */
  border-bottom: 1px solid var(--x-hairline);
  margin-bottom: 16px;
}
.x-tab {
  padding: 10px 18px;          /* 加点 padding, 居中后更舒展 */
  font-family: var(--x-font-display);
  font-size: 13px;
  color: var(--x-body-mid);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;        /* overlap the underline */
  transition: color 0.18s, border-color 0.18s, background 0.18s;
  border-radius: 6px 6px 0 0;
}
.x-tab:hover {
  color: var(--x-ink);
  background: var(--x-canvas-soft);
}
.x-tab.is-active {
  color: var(--x-primary);
  border-bottom-color: var(--x-primary);
  font-weight: 500;
}

/* === 切换过渡: 旧面板淡出 → 新面板淡入 (mode="out-in" 避免重叠) === */
.x-tab-fade-enter-active,
.x-tab-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.x-tab-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.x-tab-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* === PANEL === */
.x-records-panel {
  padding-top: 8px;
}

/* === primitives === */
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute {
  color: var(--x-body-mid);
}

@media (max-width: 768px) {
  .x-records {
    padding: 24px 16px 40px;
  }
  .x-records-title {
    font-size: 22px;
  }
}
</style>
