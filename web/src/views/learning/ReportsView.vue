<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchRichReports } from '@/api/mocks/reports'   // 本视图走 mock, 其它视图仍走真后端
import { getSubjectDisplayName } from '@/api/subjects'
import type { RichWeeklyReport } from '@/types/learning'
import { IconSparkle, IconHourglass } from '@/components/icons'

/**
 * 学习报告
 *
 *   Layout (沿用 x-* 令牌 + 比例, 跟 PracticeView 同源风格):
 *     ┌─ 1200 max-width 居中 ─┐
 *     │  header                │  标题 + 状态
 *     ├ 280 ┬─ 1fr ─────────┤
 *     │ 列表 │ 详情            │  左 280px 报告列表 + 右 flex 详情
 *     └─────┴─────────────┘
 *
 *   图表全部手画 SVG (不引 chart 库), 用 x-* 颜色, 跟其它视图统一视觉.
 */

const reports = ref<RichWeeklyReport[]>([])
const selectedId = ref<number | null>(null)
const loading = ref<boolean>(false)
const error = ref<string>('')

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await fetchRichReports()
    reports.value = data
    if (data.length > 0 && data[0]) selectedId.value = data[0].id
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Load failed'
  } finally {
    loading.value = false
  }
})

// 选中当前报告
const current = computed<RichWeeklyReport | null>(
  () => reports.value.find((r) => r.id === selectedId.value) ?? null,
)

function selectReport(id: number): void {
  selectedId.value = id
}

// 比例计算 helpers
const accuracy = computed<number>(() => {
  const c = current.value
  if (!c || c.total_questions === 0) return 0
  return Math.round((c.total_correct / c.total_questions) * 100)
})

// 颜色池 (跟 base.css 对齐)
const PALETTE = ['#1E5AE0', '#10B981', '#F59E0B', '#7C3AED', '#0EA5E9', '#EC4899', '#94A3B8']
function sliceColor(idx: number, total: number): string {
  if (total === 0) return PALETTE[0]!
  return PALETTE[idx % PALETTE.length]!
}

function formatWeekLabel(r: RichWeeklyReport): string {
  return `${r.week_start.slice(5)} → ${r.week_end.slice(5)}`
}

function formatDateLong(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
}

// ============================================================
// 1) 每日时长 柱图
// ============================================================
const DAILY_BAR_W = 36
const DAILY_BAR_GAP = 12
const DAILY_BAR_MAX_H = 160
function dailyBarChart(r: RichWeeklyReport): { x: number; y: number; h: number; label: string; mins: number; color: string }[] {
  const max = Math.max(1, ...r.daily_minutes)
  return r.daily_minutes.map((m, i) => {
    const h = Math.max(2, (m / max) * DAILY_BAR_MAX_H)
    return {
      x: i * (DAILY_BAR_W + DAILY_BAR_GAP) + DAILY_BAR_GAP,
      y: DAILY_BAR_MAX_H - h,
      h,
      label: r.daily_correctness[i]?.day ?? `${i}`,
      mins: m,
      color: i === 6 ? PALETTE[2]! : PALETTE[0]!,   // 最后一天用琥珀色高亮
    }
  })
}

// ============================================================
// 2) 学科时间分布 donut
// ============================================================
const DONUT_R = 70
const DONUT_C = 2 * Math.PI * DONUT_R
const DONUT_W = 28
function donutSegments(r: RichWeeklyReport): {
  subject: string; minutes: number; pct: number; color: string
  dashOffset: number; dashArray: string
}[] {
  const total = r.subject_distribution.reduce((acc, s) => acc + s.minutes, 0) || 1
  let offset = 0
  return r.subject_distribution.map((s, i) => {
    const pct = s.minutes / total
    const dash = pct * DONUT_C
    const seg = {
      subject: s.subject,
      minutes: s.minutes,
      pct: Math.round(pct * 100),
      color: sliceColor(i, r.subject_distribution.length),
      dashOffset: -offset,
      dashArray: `${dash} ${DONUT_C - dash}`,
    }
    offset += dash
    return seg
  })
}

// ============================================================
// 3) 掌握度分布 柱图
// ============================================================
const MASTERY_BAR_W = 36
const MASTERY_BAR_GAP = 14
const MASTERY_BAR_MAX_H = 130
const MASTERY_RANGES = ['0-20', '20-40', '40-60', '60-80', '80-100']
const MASTERY_RANGE_COLORS = ['#FEE2E2', '#FCD34D', '#DBE7FF', '#93C5FD', '#1E5AE0']
function masteryBars(r: RichWeeklyReport): { x: number; y: number; h: number; count: number; label: string; color: string }[] {
  const max = Math.max(1, ...r.mastery_distribution)
  return r.mastery_distribution.map((c, i) => {
    const h = Math.max(2, (c / max) * MASTERY_BAR_MAX_H)
    return {
      x: i * (MASTERY_BAR_W + MASTERY_BAR_GAP) + MASTERY_BAR_GAP,
      y: MASTERY_BAR_MAX_H - h,
      h,
      count: c,
      label: MASTERY_RANGES[i]!,
      color: MASTERY_RANGE_COLORS[i]!,
    }
  })
}

// ============================================================
// 4) 每日对错 stacked bar
// ============================================================
const STK_BAR_W = 36
const STK_BAR_GAP = 12
const STK_BAR_MAX_H = 130
function stackedBars(r: RichWeeklyReport): { x: number; yCorrect: number; yWrong: number; hCorrect: number; hWrong: number; day: string }[] {
  const max = Math.max(1, ...r.daily_correctness.map((d) => d.correct + d.wrong))
  return r.daily_correctness.map((d, i) => {
    const total = d.correct + d.wrong
    const hTotal = Math.max(2, (total / max) * STK_BAR_MAX_H)
    const hCorrect = total > 0 ? (d.correct / total) * hTotal : 0
    const hWrong = total > 0 ? (d.wrong / total) * hTotal : 0
    return {
      x: i * (STK_BAR_W + STK_BAR_GAP) + STK_BAR_GAP,
      yCorrect: STK_BAR_MAX_H - hTotal,
      yWrong: STK_BAR_MAX_H - hCorrect,
      hCorrect,
      hWrong,
      day: d.day,
    }
  })
}

// 监听选中变化时无需重置任何东西, computed 自带反应
watch(current, () => { /* placeholder for future */ })
</script>

<template>
  <div class="x-rep">
    <!-- ============================================================
         HEADER
         ============================================================ -->
    <header class="x-rep-head">
      <div>
        <p class="x-eyebrow x-eyebrow-mute">LEARNING ⏤ REPORTS</p>
        <h1 class="x-rep-title">学习报告</h1>
        <p class="x-rep-sub">每周自动汇总你的学习时长、答题情况、掌握度变化。点左侧切周, 右侧看详情。</p>
      </div>
      <div class="x-rep-head-right">
        <span v-if="!loading && !error" class="x-rep-count">
          共 <strong>{{ reports.length }}</strong> 份周报
        </span>
        <span v-else-if="loading" class="x-rep-status">LOADING…</span>
        <span v-else class="x-rep-status is-error">× {{ error }}</span>
      </div>
    </header>

    <!-- ============================================================
         BODY 2-pane
         ============================================================ -->
    <div class="x-rep-body">
      <!-- LEFT: 报告列表 -->
      <aside class="x-rep-list">
        <header class="x-list-head">
          <p class="x-eyebrow x-eyebrow-mute">WEEKS</p>
        </header>
        <ol v-if="reports.length" class="x-list-items">
          <li
            v-for="r in reports"
            :key="r.id"
            class="x-list-item"
            :class="{ 'is-active': r.id === selectedId }"
            @click="selectReport(r.id)"
          >
            <div class="x-list-week">
              <span class="x-list-eyebrow">WEEK</span>
              <span class="x-list-date">{{ formatWeekLabel(r) }}</span>
            </div>
            <div class="x-list-stat">
              <div class="x-list-stat-mini">
                <span class="x-list-stat-num">{{ r.total_minutes }}</span>
                <span class="x-list-stat-lbl">min</span>
              </div>
              <div class="x-list-stat-mini">
                <span class="x-list-stat-num">{{ r.total_correct }}/{{ r.total_questions }}</span>
                <span class="x-list-stat-lbl">答对</span>
              </div>
            </div>
          </li>
        </ol>
        <p v-else-if="!loading" class="x-list-empty">暂无报告</p>
      </aside>

      <!-- RIGHT: 详情 -->
      <main class="x-rep-detail">
        <div v-if="!current && !loading" class="x-rep-empty">
          <p class="x-rep-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-primary)"><IconSparkle :size="40" /></p>
          <p class="x-rep-empty-title">选一份周报开始看</p>
          <p class="x-rep-empty-hint">左侧会列出最近的周报, 选一份显详情。</p>
        </div>

        <div v-else-if="!current" class="x-rep-empty">
          <p class="x-rep-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-primary)"><IconHourglass :size="40" /></p>
          <p class="x-rep-empty-title">加载中…</p>
        </div>

        <div v-else class="x-rep-content">
          <!-- 顶部: 周范围 + AI 摘要 -->
          <header class="x-r-head">
            <p class="x-eyebrow x-eyebrow-mute">WEEKLY REPORT</p>
            <h2 class="x-r-title">
              {{ formatDateLong(current.week_start) }} — {{ formatDateLong(current.week_end) }}
            </h2>
            <p class="x-r-summary">{{ current.summary }}</p>
          </header>

          <!-- 总览卡组 -->
          <section class="x-r-cards">
            <div class="x-r-card">
              <p class="x-eyebrow x-eyebrow-mute">总学习时长</p>
              <p class="x-r-card-num">{{ current.total_minutes }}<span class="x-r-card-unit"> min</span></p>
              <p class="x-r-card-foot">日均 {{ Math.round(current.total_minutes / 7) }} min</p>
            </div>
            <div class="x-r-card">
              <p class="x-eyebrow x-eyebrow-mute">答题</p>
              <p class="x-r-card-num">
                {{ current.total_correct }}<span class="x-r-card-sep">/</span>{{ current.total_questions }}
              </p>
              <p class="x-r-card-foot">正确率 {{ accuracy }}%</p>
            </div>
            <div class="x-r-card">
              <p class="x-eyebrow x-eyebrow-mute">涉及学科</p>
              <p class="x-r-card-num">{{ current.subjects_studied.length }}</p>
              <p class="x-r-card-foot">
                {{ current.subjects_studied.map((s) => getSubjectDisplayName(s)).join(' / ') || '—' }}
              </p>
            </div>
            <div class="x-r-card">
              <p class="x-eyebrow x-eyebrow-mute">掌握节点</p>
              <p class="x-r-card-num">
                {{ current.nodes_mastered_count }}<span class="x-r-card-unit"> ≥70</span>
              </p>
              <p class="x-r-card-foot">本周边界</p>
            </div>
          </section>

          <!-- 每日时长 + 每日对错 (两柱图并排) -->
          <section class="x-r-charts-row">
            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">每日学习时长 (min)</p>
                <p class="x-r-block-sub">最后一天琥珀高亮</p>
              </header>
              <svg
                :viewBox="`0 0 ${7 * (DAILY_BAR_W + DAILY_BAR_GAP)} ${DAILY_BAR_MAX_H + 36}`"
                class="x-r-svg"
                role="img"
                aria-label="每日学习时长柱图"
              >
                <line
                  :x1="0" :x2="7 * (DAILY_BAR_W + DAILY_BAR_GAP)"
                  :y1="DAILY_BAR_MAX_H" :y2="DAILY_BAR_MAX_H"
                  class="x-r-axis"
                />
                <g v-for="b in dailyBarChart(current)" :key="b.label">
                  <rect
                    :x="b.x" :y="b.y" :width="DAILY_BAR_W" :height="b.h"
                    :fill="b.color"
                    rx="3"
                  />
                  <text
                    :x="b.x + DAILY_BAR_W / 2"
                    :y="DAILY_BAR_MAX_H + 14"
                    class="x-r-axis-label"
                    text-anchor="middle"
                  >{{ b.label }}</text>
                  <text
                    :x="b.x + DAILY_BAR_W / 2"
                    :y="b.y - 4"
                    class="x-r-bar-num"
                    text-anchor="middle"
                  >{{ b.mins }}</text>
                </g>
              </svg>
            </div>

            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">每日答题 (✓/✗ 堆叠)</p>
                <p class="x-r-block-sub">绿=对, 红=错</p>
              </header>
              <svg
                :viewBox="`0 0 ${7 * (STK_BAR_W + STK_BAR_GAP)} ${STK_BAR_MAX_H + 36}`"
                class="x-r-svg"
                role="img"
                aria-label="每日答题对错堆叠柱图"
              >
                <line
                  :x1="0" :x2="7 * (STK_BAR_W + STK_BAR_GAP)"
                  :y1="STK_BAR_MAX_H" :y2="STK_BAR_MAX_H"
                  class="x-r-axis"
                />
                <g v-for="b in stackedBars(current)" :key="b.day">
                  <!-- 错误柱子：底部圆角 -->
                  <path
                    :d="`M${b.x},${b.yWrong} L${b.x + STK_BAR_W},${b.yWrong} L${b.x + STK_BAR_W},${b.yWrong + b.hWrong - 3} Q${b.x + STK_BAR_W},${b.yWrong + b.hWrong} ${b.x + STK_BAR_W - 3},${b.yWrong + b.hWrong} L${b.x + 3},${b.yWrong + b.hWrong} Q${b.x},${b.yWrong + b.hWrong} ${b.x},${b.yWrong + b.hWrong - 3} Z`"
                    fill="#DC2626"
                  />
                  <!-- 正确柱子：顶部圆角 -->
                  <path
                    :d="`M${b.x},${b.yCorrect + 3} Q${b.x},${b.yCorrect} ${b.x + 3},${b.yCorrect} L${b.x + STK_BAR_W - 3},${b.yCorrect} Q${b.x + STK_BAR_W},${b.yCorrect} ${b.x + STK_BAR_W},${b.yCorrect + 3} L${b.x + STK_BAR_W},${b.yCorrect + b.hCorrect} L${b.x},${b.yCorrect + b.hCorrect} Z`"
                    fill="#10B981"
                  />
                  <text
                    :x="b.x + STK_BAR_W / 2"
                    :y="STK_BAR_MAX_H + 14"
                    class="x-r-axis-label"
                    text-anchor="middle"
                  >{{ b.day }}</text>
                </g>
              </svg>
            </div>
          </section>

          <!-- 学科 donut + 掌握度柱图 -->
          <section class="x-r-charts-row">
            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">学科时间分布</p>
                <p class="x-r-block-sub">donut 图 + 右侧图例</p>
              </header>
              <div class="x-r-donut-wrap">
                <svg
                  :viewBox="`0 0 ${(DONUT_R + DONUT_W) * 2} ${(DONUT_R + DONUT_W) * 2}`"
                  class="x-r-donut-svg"
                  role="img"
                  aria-label="学科时间分布"
                >
                  <g
                    :transform="`translate(${DONUT_R + DONUT_W}, ${DONUT_R + DONUT_W}) rotate(-90)`"
                  >
                    <circle
                      :r="DONUT_R"
                      fill="none"
                      stroke="var(--x-canvas-mid)"
                      :stroke-width="DONUT_W"
                    />
                    <circle
                      v-for="(s, i) in donutSegments(current)"
                      :key="s.subject"
                      :r="DONUT_R"
                      fill="none"
                      :stroke="s.color"
                      :stroke-width="DONUT_W"
                      :stroke-dasharray="s.dashArray"
                      :stroke-dashoffset="s.dashOffset"
                    >
                      <title>{{ getSubjectDisplayName(s.subject) }} · {{ s.minutes }}min · {{ s.pct }}%</title>
                    </circle>
                    <text
                      y="6"
                      text-anchor="middle"
                      class="x-r-donut-num"
                    >{{ current.total_minutes }}</text>
                    <text
                      y="22"
                      text-anchor="middle"
                    class="x-r-donut-lbl"
                    >总 min</text>
                  </g>
                </svg>
                <ul v-if="current.subject_distribution.length" class="x-r-legend">
                  <li
                    v-for="(s, i) in donutSegments(current)"
                    :key="s.subject"
                    class="x-r-legend-item"
                  >
                    <span class="x-r-legend-swatch" :style="{ background: s.color }"></span>
                    <span class="x-r-legend-name">{{ getSubjectDisplayName(s.subject) }}</span>
                    <span class="x-r-legend-val">{{ s.minutes }}<span class="x-r-legend-unit">m</span></span>
                    <span class="x-r-legend-pct">{{ s.pct }}%</span>
                  </li>
                </ul>
                <p v-else class="x-r-legend-empty">本周未记录到学科时间</p>
              </div>
            </div>

            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">掌握度分布</p>
                <p class="x-r-block-sub">按 mastery 区间分组的节点数</p>
              </header>
              <svg
                :viewBox="`0 0 ${5 * (MASTERY_BAR_W + MASTERY_BAR_GAP)} ${MASTERY_BAR_MAX_H + 36}`"
                class="x-r-svg"
                role="img"
                aria-label="掌握度分布柱图"
              >
                <line
                  :x1="0" :x2="5 * (MASTERY_BAR_W + MASTERY_BAR_GAP)"
                  :y1="MASTERY_BAR_MAX_H" :y2="MASTERY_BAR_MAX_H"
                  class="x-r-axis"
                />
                <g v-for="b in masteryBars(current)" :key="b.label">
                  <rect
                    :x="b.x" :y="b.y" :width="MASTERY_BAR_W" :height="b.h"
                    :fill="b.color"
                    rx="3"
                  />
                  <text
                    :x="b.x + MASTERY_BAR_W / 2"
                    :y="MASTERY_BAR_MAX_H + 14"
                    class="x-r-axis-label"
                    text-anchor="middle"
                  >{{ b.label }}</text>
                  <text
                    :x="b.x + MASTERY_BAR_W / 2"
                    :y="b.y - 4"
                    class="x-r-bar-num"
                    text-anchor="middle"
                  >{{ b.count }}</text>
                </g>
              </svg>
            </div>
          </section>

          <!-- TOP 5 + WEAK 5 (双列表) -->
          <section class="x-r-nodes">
            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">TOP 5 · 掌握最好</p>
              </header>
              <ol v-if="current.top_nodes.length" class="x-r-node-list">
                <li
                  v-for="(n, i) in current.top_nodes"
                  :key="n.name"
                  class="x-r-node-item is-good"
                >
                  <span class="x-r-node-rank">{{ i + 1 }}</span>
                  <span class="x-r-node-name">{{ n.name }}</span>
                  <span class="x-r-node-sub">{{ getSubjectDisplayName(n.subject) }}</span>
                  <div class="x-r-node-bar">
                    <div
                      class="x-r-node-bar-fill is-good"
                      :style="{ width: n.mastery + '%' }"
                    ></div>
                    <span class="x-r-node-bar-text">{{ n.mastery }}</span>
                  </div>
                </li>
              </ol>
              <p v-else class="x-r-empty-mini">暂无数据</p>
            </div>

            <div class="x-r-block">
              <header class="x-r-block-head">
                <p class="x-eyebrow x-eyebrow-mute">BOTTOM 5 · 最薄弱</p>
              </header>
              <ol v-if="current.weak_nodes.length" class="x-r-node-list">
                <li
                  v-for="(n, i) in current.weak_nodes"
                  :key="n.name"
                  class="x-r-node-item is-weak"
                >
                  <span class="x-r-node-rank">{{ i + 1 }}</span>
                  <span class="x-r-node-name">{{ n.name }}</span>
                  <span class="x-r-node-sub">{{ getSubjectDisplayName(n.subject) }}</span>
                  <div class="x-r-node-bar">
                    <div
                      class="x-r-node-bar-fill is-weak"
                      :style="{ width: n.mastery + '%' }"
                    ></div>
                    <span class="x-r-node-bar-text">{{ n.mastery }}</span>
                  </div>
                </li>
              </ol>
              <p v-else class="x-r-empty-mini">暂无数据</p>
            </div>
          </section>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
   ROOT + HEADER  (跟其它内部页一致)
   ============================================================ */
.x-rep {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  color: var(--x-ink);
  display: flex;
  flex-direction: column;
}
.x-rep-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 32px 40px 24px;
  border-bottom: 1px solid var(--x-hairline);
  /* max-width: var(--x-container); */
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}
.x-rep-title {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 8px 0 6px;
}
.x-rep-sub {
  font-size: 13px;
  color: var(--x-body);
  margin: 0;
  max-width: 640px;
  line-height: 1.55;
}
.x-rep-head-right {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
  flex-shrink: 0;
}
.x-rep-count strong { color: var(--x-ink); font-weight: 600; }
.x-rep-status.is-error { color: var(--x-error); }

/* ============================================================
   BODY 2-pane
   ============================================================ */
.x-rep-body {
  flex: 1;
  padding: 24px 40px 48px;
  /* max-width: var(--x-container); */
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 1024px) {
  .x-rep-body { grid-template-columns: 240px 1fr; }
}
@media (max-width: 768px) {
  .x-rep-body { grid-template-columns: 1fr; }
  .x-rep-list { position: static; }
}

/* ============================================================
   LEFT  LIST
   ============================================================ */
.x-rep-list {
  position: sticky;
  top: 80px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
  padding: 16px;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-rep-list:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-list-head {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--x-hairline);
  margin-bottom: 8px;
}
.x-list-items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-list-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.12s, border-color 0.12s;
}
.x-list-item:hover { background: var(--x-canvas-mid); }
.x-list-item.is-active {
  background: var(--x-canvas);
  border-color: var(--x-primary);
}
.x-list-week {
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-list-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--x-body-mid);
  text-transform: uppercase;
}
.x-list-date {
  font-family: var(--x-font-display);
  font-size: 13px;
  color: var(--x-ink);
  font-weight: 500;
}
.x-list-item.is-active .x-list-date { color: var(--x-primary); }
.x-list-stat {
  display: flex;
  gap: 14px;
}
.x-list-stat-mini {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--x-font-mono);
}
.x-list-stat-num {
  font-size: 13px;
  color: var(--x-ink);
  font-weight: 600;
}
.x-list-stat-lbl {
  font-size: 10px;
  color: var(--x-body-mid);
  letter-spacing: 0.4px;
}
.x-list-empty {
  font-size: 12px;
  color: var(--x-body-mid);
  text-align: center;
  padding: 12px 4px;
  margin: 0;
}

/* ============================================================
   RIGHT  DETAIL
   ============================================================ */
.x-rep-detail {
  min-height: 460px;
  min-width: 0;
}
.x-rep-empty {
  text-align: center;
  padding: 80px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: var(--x-canvas-soft);
  border: 1px dashed var(--x-hairline-strong);
  border-radius: var(--x-rounded-md);
}
.x-rep-mark {
  font-size: 36px;
  color: var(--x-primary);
}
.x-rep-empty-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  color: var(--x-ink);
  margin: 0;
}
.x-rep-empty-hint {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
}

.x-rep-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── 顶部 head ── */
.x-r-head {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 24px 28px;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-r-head:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-r-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 6px 0 10px;
}
.x-r-summary {
  font-size: 13px;
  color: var(--x-body);
  line-height: 1.65;
  margin: 0;
  max-width: 720px;
}

/* ── 总览卡组 ── */
.x-r-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 1200px) { .x-r-cards { grid-template-columns: repeat(2, 1fr); } }
.x-r-card {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-r-card:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-r-card-num {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  color: var(--x-ink);
  line-height: 1.1;
  margin: 6px 0 4px;
}
.x-r-card-unit, .x-r-card-sep {
  font-size: 14px;
  color: var(--x-body-mid);
  font-weight: 400;
  margin-left: 4px;
}
.x-r-card-foot {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  margin: 0;
}

/* ── 图表 row ── */
.x-r-charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 1024px) { .x-r-charts-row { grid-template-columns: 1fr; } }
.x-r-block {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 20px 22px;
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.x-r-block:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.x-r-block-head {
  margin-bottom: 16px;
}
.x-r-block-sub {
  font-size: 11px;
  color: var(--x-body-mid);
  margin: 4px 0 0;
}

.x-r-svg {
  width: 100%;
  height: auto;
  display: block;
}
.x-r-axis {
  stroke: var(--x-hairline);
  stroke-width: 1;
}
.x-r-axis-label {
  font-family: var(--x-font-mono);
  font-size: 9px;
  fill: var(--x-body-mid);
}
.x-r-bar-num {
  font-family: var(--x-font-mono);
  font-size: 9px;
  fill: var(--x-body);
}

/* ── donut ── */
.x-r-donut-wrap {
  display: flex;
  align-items: center;
  gap: 16px;
}
.x-r-donut-svg {
  width: 160px;
  height: 160px;
  flex-shrink: 0;
}
.x-r-donut-num {
  font-family: var(--x-font-display);
  font-size: 24px;
  font-weight: 600;
  fill: var(--x-ink);
}
.x-r-donut-lbl {
  font-family: var(--x-font-mono);
  font-size: 9px;
  fill: var(--x-body-mid);
  letter-spacing: 1px;
}
.x-r-legend {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-r-legend-item {
  display: grid;
  grid-template-columns: 12px 1fr auto auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--x-ink);
}
.x-r-legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.x-r-legend-name { color: var(--x-body); }
.x-r-legend-val {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-ink);
  font-weight: 600;
}
.x-r-legend-unit {
  color: var(--x-body-mid);
  margin-left: 1px;
  font-weight: 400;
}
.x-r-legend-pct {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body-mid);
  min-width: 32px;
  text-align: right;
}
.x-r-legend-empty {
  font-size: 12px;
  color: var(--x-body-mid);
  margin: 0;
}

/* ── 节点列表 ── */
.x-r-nodes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 1024px) { .x-r-nodes { grid-template-columns: 1fr; } }
.x-r-node-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-r-node-item {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
}
.x-r-node-rank {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  text-align: center;
}
.x-r-node-item.is-good .x-r-node-rank { color: var(--x-success); }
.x-r-node-item.is-weak .x-r-node-rank { color: var(--x-error); }
.x-r-node-name {
  font-family: var(--x-font-display);
  font-size: 13px;
  color: var(--x-ink);
  font-weight: 500;
  grid-column: 2;
  grid-row: 1;
}
.x-r-node-sub {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body-mid);
  letter-spacing: 0.4px;
  grid-column: 2;
  grid-row: 2;
}
.x-r-node-bar {
  position: relative;
  width: 120px;
  height: 6px;
  background: var(--x-canvas-mid);
  border-radius: 3px;
  overflow: hidden;
  grid-column: 3;
  grid-row: 1 / 3;
  align-self: center;
}
.x-r-node-bar-fill {
  position: absolute;
  inset: 0;
  border-radius: 3px;
  transition: width 0.2s;
}
.x-r-node-bar-fill.is-good { background: var(--x-success); }
.x-r-node-bar-fill.is-weak { background: var(--x-error); }
.x-r-node-bar-text {
  position: absolute;
  right: 0;
  top: -16px;
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body);
}
.x-r-empty-mini {
  font-size: 12px;
  color: var(--x-body-mid);
  margin: 0;
  text-align: center;
  padding: 16px 0;
}

/* ============================================================
   PRIMITIVES (跟其它视图同源, 各自一份避免跨 scope 依赖)
   ============================================================ */
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

@media (max-width: 768px) {
  .x-rep-head { flex-direction: column; align-items: stretch; padding: 24px 16px; }
  .x-rep-body { padding: 16px; }
  .x-r-head, .x-r-block, .x-r-card { padding: 16px; }
}
</style>
