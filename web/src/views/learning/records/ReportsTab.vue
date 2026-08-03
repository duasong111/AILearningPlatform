<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useReports } from './useReports'
import { formatWeekRange } from '@/utils/format'
import { exportReportPDF } from '@/api/learning'
import type { WeeklyReport } from '@/types/learning'

/**
 * 我的报告 Tab —— 周报卡片列表
 *   Export PDF 按钮调 exportReportPDF, 当前 stub 会抛 "PDF endpoint pending"
 *   View 走 catch -> toast 提示, 不静默
 */

const { items, loading, error, reload } = useReports()
const exportingIds = ref<Set<number>>(new Set())

async function handleExport(r: WeeklyReport): Promise<void> {
  if (exportingIds.value.has(r.id)) return
  exportingIds.value.add(r.id)
  exportingIds.value = new Set(exportingIds.value)
  try {
    await exportReportPDF(r.id)
    ElMessage({ message: '→ Downloaded', customClass: 'x-toast' })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Export failed'
    ElMessage({ message: `× ${msg}`, customClass: 'x-toast' })
  } finally {
    exportingIds.value.delete(r.id)
    exportingIds.value = new Set(exportingIds.value)
  }
}
</script>

<template>
  <div class="x-tab-panel">
    <!-- LOADING -->
    <div v-if="loading && items.length === 0" class="x-report-grid">
      <div v-for="i in 2" :key="i" class="x-report-card x-report-card-skel">
        <div class="x-skel x-skel-block-l"></div>
        <div class="x-skel x-skel-block-s"></div>
        <div class="x-skel x-skel-block-m"></div>
      </div>
    </div>

    <!-- ERROR -->
    <div v-else-if="error" class="x-state-error">
      <p class="x-state-msg">× {{ error }}</p>
      <button class="x-btn-link" @click="reload">Retry →</button>
    </div>

    <!-- EMPTY -->
    <div v-else-if="items.length === 0" class="x-state-empty">
      <p class="x-eyebrow x-eyebrow-mute">EMPTY</p>
      <p class="x-state-msg">No weekly reports yet.</p>
    </div>

    <!-- LIST -->
    <div v-else class="x-report-grid">
      <article v-for="r in items" :key="r.id" class="x-report-card">
        <header class="x-report-head">
          <p class="x-eyebrow x-eyebrow-mute">WEEK</p>
          <h3 class="x-report-title">{{ formatWeekRange(r.week_start, r.week_end) }}</h3>
          <span class="x-pill is-mute">{{ r.total_time_min }} min</span>
        </header>

        <p class="x-report-summary">{{ r.summary }}</p>

        <div class="x-report-cols">
          <div class="x-report-col">
            <p class="x-eyebrow x-eyebrow-mute">TOP NODES ↑</p>
            <ul class="x-node-list">
              <li v-for="n in r.top_nodes" :key="n">{{ n }}</li>
            </ul>
          </div>
          <div class="x-report-col">
            <p class="x-eyebrow x-eyebrow-mute">WEAK NODES ↓</p>
            <ul class="x-node-list x-node-list-weak">
              <li v-for="n in r.weak_nodes" :key="n">{{ n }}</li>
            </ul>
          </div>
        </div>

        <footer class="x-report-foot">
          <button
            class="x-btn-link"
            :disabled="exportingIds.has(r.id)"
            @click="handleExport(r)"
          >
            {{ exportingIds.has(r.id) ? 'Exporting…' : 'Export PDF →' }}
          </button>
        </footer>
      </article>
    </div>
  </div>
</template>

<style scoped>
@import './tab-shared.css';

.x-report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.x-report-card {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-report-card:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-report-card-skel {
  min-height: 220px;
}

.x-report-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.x-report-title {
  flex: 1;
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0;
}

.x-report-summary {
  font-size: 14px;
  color: var(--x-body);
  line-height: 1.55;
}

.x-report-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.x-report-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-node-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-node-list li {
  font-size: 13px;
  color: var(--x-body);
  padding: 4px 8px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
}
.x-node-list-weak li {
  background: var(--x-error-soft);
  color: var(--x-error);
}

.x-report-foot {
  border-top: 1px solid var(--x-hairline);
  padding-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.x-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}
.x-pill.is-mute {
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
}
</style>
