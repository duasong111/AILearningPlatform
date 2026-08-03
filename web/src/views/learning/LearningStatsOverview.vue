<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { SUBJECT_CHOICES } from '@/api/subjects'
import { useResourceHistory } from './records/useResourceHistory'
import { useExerciseRecords } from './records/useExerciseRecords'
import { useReports } from './records/useReports'
import { useStudyTime } from './records/useStudyTime'

/**
 * 学习记录 —— 总览区 (跨 3 tab 共享)
 *
 *   数据源: 3 个 useXxx() composable (跟 tab 用同一个 mock endpoint)
 *   视觉: 4 数字卡 + ECharts calendar 26 周活动热力
 *   ECharts 自己负责: 日历布局 / 4 档分阶颜色 / tooltip / 自适应
 *
 *   品牌色 (硬编码进 ECharts option, 不走 CSS 变量):
 *     - 0   → #F1F4F9  (canvas-soft, 灰底)
 *     - 1-3 → #DBE7FF  (primary-soft, 浅蓝)
 *     - 4-7 → #7FA0F4  (浅一档 primary)
 *     - 8+  → #1E5AE0  (primary, 实色)
 */

const { items: resources } = useResourceHistory()
const { items: exercises } = useExerciseRecords()
const { items: reports }   = useReports()
const { byDay: studyByDay, bySubject: studyBySubject } = useStudyTime(30)

// ============================================================
// 4 数字总览
// ============================================================
const totalResources = computed(() => resources.value.length)
const totalExercises = computed(() => exercises.value.length)
const totalMinutes = computed(() =>
  resources.value.reduce((sum, r) => sum + r.duration_min, 0),
)
const accuracyPct = computed(() => {
  if (exercises.value.length === 0) return null   // 0 答题时显示 — 而不是 NaN
  const correct = exercises.value.filter((e) => e.correct).length
  return Math.round((correct / exercises.value.length) * 100)
})

// ============================================================
// ECharts calendar 热力
//   把 resources + exercises + reports 折成 [date, count] 对
//   喂给 ECharts, 颜色和阈值在 option.visualMap.pieces 里定
// ============================================================
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

// 当年 (e.g. '2026'), ECharts calendar 范围参数
const currentYear = String(new Date().getFullYear())

// ============================================================
// 下方两个小图: 计划完成柱状图 + 星图综合评价热力
//   数据先 mock, 后期接真实 endpoint 替换即可
// ============================================================

// ── 柱状图: 最近 7 天每天完成的计划数 ──
const planCompletionData = computed(() => [
  { day: '周一', count: 4 },
  { day: '周二', count: 6 },
  { day: '周三', count: 3 },
  { day: '周四', count: 7 },
  { day: '周五', count: 5 },
  { day: '周六', count: 8 },
  { day: '周日', count: 6 },
])

// ── 雷达图: 7 学科综合掌握度 (0-100) ──
const galaxySubjects = ['数据结构', '网络安全', '物联网', '电气自动化', '机械设计', '高等数学', '人工智能']
// 7 顶点各自配色 —— 既给 radar 的 7 数据点上色, 也给 legend chip 上色, 保持一一对应
const SUBJECT_COLORS: readonly string[] = [
  '#1E5AE0',  // 1. 数据结构 — 品牌主蓝
  '#2EC4B6',  // 2. 网络安全 — 青绿
  '#FF8C42',  // 3. 物联网 — 橙
  '#9B5DE5',  // 4. 电气自动化 — 紫
  '#F15BB5',  // 5. 机械设计 — 粉
  '#00BBF9',  // 6. 高等数学 — 天蓝
  '#FEE440',  // 7. 人工智能 — 黄
]

// subject code → 颜色 (给环形图按学科取色, 跟 SUBJECT_COLORS 同源, 但按 code 索引更稳)
const SUBJECT_COLORS_BY_CODE: Readonly<Record<string, string>> = {
  data_structure:         '#1E5AE0',
  cybersecurity:             '#2EC4B6',
  iot:                    '#FF8C42',
  electrical_automation:  '#9B5DE5',
  mechanical_design:      '#F15BB5',
  advanced_math:          '#00BBF9',
  artificial_intelligence:'#FEE440',
}
const DEFAULT_COLOR = '#1E5AE0'

// hex → rgba 工具 (ECharts 填充用透明度)
function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// 安全取色: 越界 fallback 到主蓝
function colorAt(i: number): string {
  return SUBJECT_COLORS[i] ?? SUBJECT_COLORS[0]!
}

// 用固定 seed 让结果稳定 (避免 SSR / 重复渲染跳动)
const galaxyRadarData = computed<number[]>(() => {
  let seed = 13
  const rand = () => {
    seed = (seed * 9301 + 49297) % 233280
    return seed / 233280
  }
  return galaxySubjects.map(() => Math.floor(35 + rand() * 60))
})

// 每根轴的 label —— "学科 分数" 形式, 替换默认的纯 name
//   这样 7 个角上能直接看到自己的掌握度, 不必 hover tooltip
const galaxyAxisLabels = computed<string[]>(() =>
  galaxySubjects.map((subj, i) => `${subj} ${galaxyRadarData.value[i] ?? 0}`),
)

// 聚合 date → count
const dailyCounts = computed<Map<string, number>>(() => {
  const m = new Map<string, number>()
  for (const r of resources.value) {
    const d = r.timestamp.slice(0, 10)
    m.set(d, (m.get(d) ?? 0) + 1)
  }
  for (const e of exercises.value) {
    const d = e.timestamp.slice(0, 10)
    m.set(d, (m.get(d) ?? 0) + 1)
  }
  for (const rep of reports.value) {
    m.set(rep.week_end, (m.get(rep.week_end) ?? 0) + 1)
  }
  return m
})

// ECharts 数据: 全年 (yearStart → yearEnd), 没活动的天 count=0 也输出
//   → 这样整张日历都有格子, 不会出现"空白周"
function buildCalendarData(): Array<[string, number]> {
  const yearStart = new Date(`${currentYear}-01-01T00:00:00`)
  const yearEnd = new Date(`${Number(currentYear) + 1}-01-01T00:00:00`)
  const dayMs = 86_400_000
  const data: Array<[string, number]> = []
  const counts = dailyCounts.value
  for (let t = yearStart.getTime(); t < yearEnd.getTime(); t += dayMs) {
    const d = new Date(t)
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    data.push([iso, counts.get(iso) ?? 0])
  }
  return data
}

function buildOption(): echarts.EChartsOption {
  return {
    tooltip: {
      formatter: (p: any) =>
        `${p.value[0]}<br/>活动 <b>${p.value[1]}</b> 次`,
    },
    visualMap: {
      type: 'piecewise',
      orient: 'horizontal',
      right: 20,             // 右下角: 跟 calendar 右边对齐
      bottom: 4,
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 5,
      textStyle: { color: 'var(--x-body-mid)', fontSize: 11 },
      pieces: [
        { min: 0, max: 0,   color: '#F1F4F9', label: '0' },
        { min: 1, max: 3,   color: '#DBE7FF', label: '1-3' },
        { min: 4, max: 7,   color: '#7FA0F4', label: '4-7' },
        { min: 8, max: 99,  color: '#1E5AE0', label: '8+' },
      ],
    },
    calendar: {
      top: 32,               // 跟标题拉开距离, 不遮挡月份
      left: 24,
      right: 24,
      bottom: 36,            // 底部留 36px 给右下角 visualMap
      cellSize: ['auto', 18],
      range: currentYear,
      itemStyle: {
        borderWidth: 0.5,
        borderColor: 'rgba(0, 0, 0, 0.05)',
      },
      yearLabel: { show: false },
      monthLabel: { color: 'var(--x-body-mid)', fontSize: 12, margin: 8 },
      dayLabel: {
        firstDay: 1,
        color: 'var(--x-body-mid)',
        fontSize: 11,
        margin: 6,
        nameMap: ['日', '一', '二', '三', '四', '五', '六'],
      },
      splitLine: { show: false },
    },
    series: {
      type: 'heatmap',
      coordinateSystem: 'calendar',
      data: buildCalendarData(),
    },
  }
}

function initChart(): void {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  chart.setOption(buildOption())

  // 容器尺寸变化 → 重新 layout
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => chart?.resize())
    ro.observe(chartRef.value)
    // 挂在 chart 上, 卸载时 dispose 一起清理
    ;(chart as any)._ro = ro
  } else {
    window.addEventListener('resize', resize)
  }
}

function resize(): void {
  chart?.resize()
}

// 数据变化 → 重渲
watch([dailyCounts], () => {
  if (chart) chart.setOption(buildOption(), { notMerge: true })
})

// 新两个图: 后端数据回来后再重绘
watch([studyByDay], () => {
  if (trendChart) trendChart.setOption(buildTrendOption(), { notMerge: true })
})
watch([studyBySubject], () => {
  if (donutChart) donutChart.setOption(buildDonutOption(), { notMerge: true })
})

// ============================================================
// 小图 1: 计划完成柱状图 (最近 7 天)
// ============================================================
const barChartRef = ref<HTMLDivElement | null>(null)
let barChart: echarts.ECharts | null = null

function buildBarOption(): echarts.EChartsOption {
  const data = planCompletionData.value
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p: any) =>
        `${p[0].axisValue}<br/>完成 <b>${p[0].value}</b> 个计划`,
    },
    grid: { left: 32, right: 12, top: 14, bottom: 22 },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.day),
      axisLine: { lineStyle: { color: 'var(--x-hairline)' } },
      axisLabel: { color: 'var(--x-body-mid)', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'var(--x-hairline)' } },
      axisLabel: { color: 'var(--x-body-mid)', fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: data.map((d) => d.count),
      itemStyle: {
        color: '#1E5AE0',
        borderRadius: [4, 4, 0, 0],
      },
      barWidth: '55%',
    }],
  }
}

function initBarChart(): void {
  if (!barChartRef.value) return
  barChart = echarts.init(barChartRef.value, undefined, { renderer: 'canvas' })
  barChart.setOption(buildBarOption())
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => barChart?.resize())
    ro.observe(barChartRef.value)
    ;(barChart as any)._ro = ro
  }
}

// ============================================================
// 小图 2: 星图综合评价 (雷达图, 7 学科掌握度)
// ============================================================
const galaxyChartRef = ref<HTMLDivElement | null>(null)
let galaxyChart: echarts.ECharts | null = null

function buildGalaxyOption(): echarts.EChartsOption {
  return {
    // ── 整体出场动画: 慢一点 + cubic 缓动, 让雷达从中心扩散 ──
    animation: true,
    animationDuration: 1400,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 600,
    animationEasingUpdate: 'cubicOut',
    animationDelay: (idx: number) => idx * 60,   // 标题 / 雷达 / 数值 依次入场

    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>掌握度 <b>${p.value}</b>`,
    },
    radar: {
      center: ['50%', '54%'],
      radius: '60%',
      splitNumber: 4,
      axisName: {
        color: 'var(--x-body-mid)',
        fontSize: 11,
      },
      splitLine: {
        lineStyle: { color: 'var(--x-hairline)' },
      },
      splitArea: {
        areaStyle: { color: ['transparent', 'transparent'] },
      },
      axisLine: {
        lineStyle: { color: 'var(--x-hairline)' },
      },
      // 7 个角各带 "{name} {value}" —— 直接看掌握度, 不必 hover
      indicator: galaxyAxisLabels.value.map((name) => ({ name, max: 100 })),
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 8,
      // ── 描边: 单色蓝 + 发光 ──
      lineStyle: {
        color: '#1E5AE0',
        width: 2.5,
        shadowBlur: 10,
        shadowColor: 'rgba(30, 90, 224, 0.30)',
      },
      // ── 数据点: 蓝 + 白边 + 光晕 ──
      itemStyle: {
        color: '#1E5AE0',
        shadowBlur: 8,
        shadowColor: 'rgba(0, 0, 0, 0.25)',
        borderColor: '#FFFFFF',
        borderWidth: 2,
      },
      // ── 填充: 蓝色 18% 透明 ──
      areaStyle: {
        color: 'rgba(30, 90, 224, 0.18)',
        shadowBlur: 18,
        shadowColor: 'rgba(30, 90, 224, 0.20)',
      },
      data: [{
        name: '我的掌握度',
        value: galaxyRadarData.value,
      }],
    }],
  }
}

function initGalaxyChart(): void {
  if (!galaxyChartRef.value) return
  galaxyChart = echarts.init(galaxyChartRef.value, undefined, { renderer: 'canvas' })
  galaxyChart.setOption(buildGalaxyOption())
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => galaxyChart?.resize())
    ro.observe(galaxyChartRef.value)
    ;(galaxyChart as any)._ro = ro
  }
}

// ============================================================
// 小图 3: 30 天学习时长趋势 (折线图) — "我在进步吗?"
// ============================================================
const trendChartRef = ref<HTMLDivElement | null>(null)
let trendChart: echarts.ECharts | null = null

function buildTrendOption(): echarts.EChartsOption {
  const data = studyByDay.value
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p: any) => {
        const d = p[0].axisValue
        const m = p[0].value
        return m > 0
          ? `${d}<br/>学习 <b>${m}</b> 分钟`
          : `${d}<br/>无学习记录`
      },
    },
    grid: { left: 36, right: 16, top: 14, bottom: 28 },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.date.slice(5)),  // MM-DD
      axisLine: { lineStyle: { color: 'var(--x-hairline)' } },
      axisLabel: { color: 'var(--x-body-mid)', fontSize: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'var(--x-hairline)' } },
      axisLabel: { color: 'var(--x-body-mid)', fontSize: 11, formatter: '{value} 分' },
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: data.map((d) => d.minutes),
      lineStyle: { color: '#1E5AE0', width: 2 },
      itemStyle: { color: '#1E5AE0' },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(30, 90, 224, 0.30)' },
            { offset: 1, color: 'rgba(30, 90, 224, 0.02)' },
          ],
        },
      },
    }],
  }
}

function initTrendChart(): void {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value, undefined, { renderer: 'canvas' })
  trendChart.setOption(buildTrendOption())
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => trendChart?.resize())
    ro.observe(trendChartRef.value)
    ;(trendChart as any)._ro = ro
  }
}

// ============================================================
// 小图 4: 7 学科时间占比 (环形图 donut) — "我把时间花在哪了"
// ============================================================
const donutChartRef = ref<HTMLDivElement | null>(null)
let donutChart: echarts.ECharts | null = null

function buildDonutOption(): echarts.EChartsOption {
  // SUBJECT_CHOICES 的 code → 中文名 映射 (legend + tooltip 都用中文)
  const codeToName = new Map(SUBJECT_CHOICES.map((c) => [c.code, c.name]))
  const data = studyBySubject.value
    .filter((s) => s.minutes > 0)   // 没数据的学科不画
    .map((s) => {
      const code = s.code
      const color = SUBJECT_COLORS_BY_CODE[code] ?? DEFAULT_COLOR
      return {
        name: codeToName.get(code) ?? code,  // 显示中文, fallback code
        value: s.minutes,
        itemStyle: { color },
      }
    })
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/><b>${p.value}</b> 分钟 (${p.percent}%)`,
    },
    legend: {
      bottom: 0,
      left: 'center',
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: 'var(--x-body-mid)', fontSize: 11 },
    },
    series: [{
      type: 'pie',
      radius: ['52%', '76%'],
      center: ['50%', '44%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: 'var(--x-canvas)', borderWidth: 2 },
      label: { show: false },
      labelLine: { show: false },
      data: data.length > 0 ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: 'var(--x-hairline)' } }],
    }],
  }
}

function initDonutChart(): void {
  if (!donutChartRef.value) return
  donutChart = echarts.init(donutChartRef.value, undefined, { renderer: 'canvas' })
  donutChart.setOption(buildDonutOption())
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => donutChart?.resize())
    ro.observe(donutChartRef.value)
    ;(donutChart as any)._ro = ro
  }
}

onMounted(() => {
  initChart()
  initBarChart()
  initGalaxyChart()
  initTrendChart()
  initDonutChart()
})

function disposeChart(c: echarts.ECharts | null): void {
  const ro = (c as any)?._ro as ResizeObserver | undefined
  if (ro) ro.disconnect()
  c?.dispose()
}

onBeforeUnmount(() => {
  disposeChart(chart)
  disposeChart(barChart)
  disposeChart(galaxyChart)
  chart = barChart = galaxyChart = null
})
</script>

<template>
  <section class="x-overview">
    <!-- === 4 数字总览 === -->
    <div class="x-overview-stats">
      <div class="x-stat-card">
        <p class="x-eyebrow x-eyebrow-mute">资源</p>
        <p class="x-stat-num">{{ totalResources }}</p>
        <p class="x-stat-hint">累计看过的视频/文章/PDF/课件</p>
      </div>
      <div class="x-stat-card">
        <p class="x-eyebrow x-eyebrow-mute">答题</p>
        <p class="x-stat-num">{{ totalExercises }}</p>
        <p class="x-stat-hint">已点选 / 已出解析</p>
      </div>
      <div class="x-stat-card">
        <p class="x-eyebrow x-eyebrow-mute">累计学习</p>
        <p class="x-stat-num x-stat-num-primary">
          {{ Math.round(totalMinutes / 60 * 10) / 10 }}<span class="x-stat-unit">h</span>
        </p>
        <p class="x-stat-hint">来自资源观看时长</p>
      </div>
      <div class="x-stat-card">
        <p class="x-eyebrow x-eyebrow-mute">正确率</p>
        <p class="x-stat-num x-stat-num-aux" :class="accuracyPct !== null && accuracyPct >= 70 ? 'is-good' : 'is-mid'">
          {{ accuracyPct !== null ? `${accuracyPct}%` : '—' }}
        </p>
        <p class="x-stat-hint">
          {{ accuracyPct !== null
            ? `${exercises.filter(e => e.correct).length} 题对 / ${exercises.length} 总`
            : '还没答题' }}
        </p>
      </div>
    </div>

    <!-- === 26 周活动热力 (ECharts calendar) === -->
    <div class="x-overview-card x-heat-wide-card">
      <header class="x-overview-card-head x-overview-card-head-row">
        <div>
          <p class="x-eyebrow x-eyebrow-mute">{{ currentYear }} · 活动热力</p>
          <h2 class="x-overview-card-title">资源 + 答题 + 报告 综合活跃度</h2>
        </div>
        <p class="x-heat-wide-hint">
          每格 = 一天, 颜色越深 = 当天学习活动越多 (含资源 1 / 答题 1 / 周报 1)
        </p>
      </header>

      <div ref="chartRef" class="x-heat-chart" />
    </div>

    <!-- === 两个小图: 计划完成柱状 + 星图综合评价 === -->
    <div class="x-overview-twocol">
      <!-- 计划完成 (柱状) -->
      <div class="x-overview-card x-twocol-card">
        <header class="x-overview-card-head">
          <p class="x-eyebrow x-eyebrow-mute">最近 7 天 · 计划完成</p>
          <h2 class="x-overview-card-title">每天完成计划数</h2>
        </header>
        <div ref="barChartRef" class="x-mini-chart" />
      </div>

      <!-- 星图综合评价 (雷达图) -->
      <div class="x-overview-card x-twocol-card">
        <header class="x-overview-card-head">
          <p class="x-eyebrow x-eyebrow-mute">星图综合评价</p>
          <h2 class="x-overview-card-title">7 学科掌握度</h2>
        </header>
        <!-- 顶点 ↔ 学科 映射 (顺时针, 从顶部 12 点开始) — 纯标签, 仅做对照 -->
        <div class="x-radar-legend">
          <span
            v-for="(subj, i) in galaxySubjects"
            :key="i"
            class="x-radar-chip"
            :title="`顶点 ${i + 1}: ${subj} · 掌握度 ${galaxyRadarData[i]}`"
          >
            <span
              class="x-radar-chip-num"
              :style="{ background: colorAt(i) }"
            >{{ i + 1 }}</span>
            <span class="x-radar-chip-name">{{ subj }}</span>
          </span>
        </div>
        <div ref="galaxyChartRef" class="x-mini-chart" />
      </div>
    </div>

    <!-- === 两个小图: 30 天时长趋势 (折线) + 7 学科时间占比 (环形) === -->
    <div class="x-overview-twocol">
      <!-- 30 天时长趋势 (折线) -->
      <div class="x-overview-card x-twocol-card">
        <header class="x-overview-card-head">
          <p class="x-eyebrow x-eyebrow-mute">最近 30 天 · 学习时长</p>
          <h2 class="x-overview-card-title x-title-gradient-trend">"我在进步吗?"</h2>
        </header>
        <div ref="trendChartRef" class="x-mini-chart" />
      </div>

      <!-- 7 学科时间占比 (环形) -->
      <div class="x-overview-card x-twocol-card">
        <header class="x-overview-card-head">
          <p class="x-eyebrow x-eyebrow-mute">最近 30 天 · 学科时间分布</p>
          <h2 class="x-overview-card-title x-title-gradient-donut">"我把时间花在哪了"</h2>
        </header>
        <div ref="donutChartRef" class="x-mini-chart" />
      </div>
    </div>
  </section>
</template>

<style scoped>
/* ============================================================
   总览区 —— 在 3 个 tab 上方, 跨 tab 共享
   不再包大卡片: 4 张 stat + 热力卡 各自有 card 风格
   ============================================================ */
.x-overview {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 28px;
  /* 故意去掉 background / border-radius / box-shadow / padding:
     4 张 stat 卡 + 热力卡各自带 card 样式, 不需要外面再套一层 */
}

/* === 4 数字总览 === */
.x-overview-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  width: 92%;
  margin: 0 auto;
}
.x-stat-card {
  padding: 14px 16px;
  background: var(--x-canvas);
  border-radius: 10px;
  box-shadow: var(--x-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-stat-num {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 4px 0 0;
  font-variant-numeric: tabular-nums;
}
.x-stat-num-primary { color: var(--x-primary); }
.x-stat-num-aux.is-good { color: oklch(55% 0.18 142); }
.x-stat-num-aux.is-mid  { color: var(--x-body-mid); }
.x-stat-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-body-mid);
  margin-left: 2px;
}
.x-stat-hint {
  font-size: 11px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
  color: var(--x-body-mid);
  margin: 0;
  line-height: 1.4;
}

/* === 通用 overview card === */
.x-overview-card {
  padding: 12px 14px;       /* 比之前 (16/18) 更紧凑 */
  background: var(--x-canvas);
  border-radius: 10px;
  box-shadow: var(--x-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.x-overview-card-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.x-overview-card-head-row {
  flex-direction: row;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.x-overview-card-title {
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
  letter-spacing: -0.2px;
}
/* 两个新图的标题做彩色渐变, 一眼区分"趋势 vs 构成" */
.x-title-gradient-trend {
  background: linear-gradient(135deg, #1E5AE0 0%, #00BBF9 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
  font-weight: 700;
}
.x-title-gradient-donut {
  background: linear-gradient(135deg, #9B5DE5 0%, #F15BB5 50%, #FF8C42 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
  font-weight: 700;
}

/* === 26 周活动热力 (ECharts 居中, 跟 stat 卡同宽) === */
.x-heat-wide-card {
  width: 92%;            /* 跟上方 4 张 stat 卡完全对齐 */
  margin: 0 auto;
}

.x-heat-wide-hint {
  font-size: 11px;
  font-family: var(--x-font-mono);
  color: var(--x-body-mid);
  margin: 0;
  letter-spacing: 0.2px;
  line-height: 1.5;
  text-align: right;
  max-width: 50%;
  flex-shrink: 0;
}

.x-heat-chart {
  width: 100%;
  height: 250px;        /* 顶部留 32px 给月份标签, 18px cell × 7 行, 底部 36px 给 visualMap */
  padding-top: 4px;     /* 跟标题再隔一点 */
}

/* === 两个小图: 柱状 + 雷达, 92% 宽 + 两列等分 === */
.x-overview-twocol {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 92%;
  margin: 0 auto;
}

.x-twocol-card {
  /* 沿用 .x-overview-card 的 padding / radius / shadow */
}

.x-mini-chart {
  width: 100%;
  height: 200px;        /* 柱状 + 雷达 共用高度 */
}

/* === 雷达图 7 顶点 ↔ 学科 映射 (纯标签, 不再可点击) === */
.x-radar-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin-bottom: 8px;
  padding: 6px 8px;
  background: var(--x-canvas-soft);
  border-radius: 6px;
}

.x-radar-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  color: var(--x-body-mid);
  line-height: 1;
  white-space: nowrap;
  padding: 2px 4px;
  border-radius: 4px;
}

.x-radar-chip-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  background: var(--x-primary);
  color: #FFFFFF;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 700;
  flex-shrink: 0;
}

.x-radar-chip-name {
  font-weight: 500;
  color: var(--x-ink);
}

/* === 响应式 === */
@media (max-width: 900px) {
  .x-overview-stats,
  .x-heat-wide-card,
  .x-overview-twocol {
    width: 100%;
  }
  .x-overview-twocol {
    grid-template-columns: 1fr;     /* 窄屏两列变单列 */
  }
}

@media (max-width: 768px) {
  .x-overview-stats { grid-template-columns: 1fr 1fr; }
  .x-overview-card-head-row {
    flex-direction: column;
    gap: 4px;
  }
  .x-heat-wide-hint {
    text-align: left;
    max-width: 100%;
  }
}
</style>
