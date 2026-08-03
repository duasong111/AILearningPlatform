<script setup lang="ts">
/**
 * 视频课首页 (重写版)
 *
 *   路由: /app/video
 *   详情页: /app/video/:id -> VideoPlayerView.vue
 *
 *   设计:
 *     - 左侧 280px 栏: 只展示 "当前学科下学习计划中的 video item"
 *       (从 LearningPlan.memory.items[type=video] 取)
 *     - 右侧: 默认空状态 + 提示文案; 选中即跳到详情页
 *     - 列表项状态:
 *         有 video_record_id -> 直接跳播放页
 *         没有               -> 调用 startVideoCourse 触发生成, 跳详情页轮询
 *
 *   数据流:
 *     plan.memory.items[].video_record_id  <- ->  VideoCourseRecord.id
 *     后端在 VideoCourseGenerateView 接收 plan_id + plan_node_id,
 *     创建记录后回填 plan.memory.items[].video_record_id
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { getSubjectDisplayName } from '@/api/subjects'
import { startVideoCourse } from '@/api/video'
import { listPlans, type LearningPlan } from '@/api/plan'
import { IconCheck, IconHourglass, IconArrow, IconVideo } from '@/components/icons'

const router = useRouter()
const currentSubject = useCurrentSubjectStore()
const mySubjects = useMySubjectsStore()

// 当前学科 id (用于 listPlans 过滤)
const subjectId = computed<number | null>(() => {
  const s = mySubjects.subjects.find((m) => m.name === currentSubject.code)
  return s?.id ?? null
})

// -- 列表数据 --
// 一条 LearningPlan 就是一步 (step); video 类型的 plan 直接对应一段视频
interface VideoEntry {
  plan: LearningPlan
  // 视频绑定字段从 plan.memory 读 (后端 VideoCourseGenerateView 回填到 plan.memory.video_record_id)
  videoRecordId: number | null
  videoUuid: string | null
  videoState: 'generating' | 'complete' | 'error' | null
}

const entries = ref<VideoEntry[]>([])
const loading = ref(false)
const generating = ref<number | null>(null) // plan id
const errorMsg = ref<string>('')

async function loadEntries(): Promise<void> {
  if (!subjectId.value) {
    entries.value = []
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
const { data } = await listPlans(currentSubject.code)
    const plans = Array.isArray(data) ? data : (data as { results: LearningPlan[] }).results ?? []
    const out: VideoEntry[] = []
    for (const plan of plans) {
      // 只显示 video 类型的 step
      if (plan.memory?.step_type !== 'video') continue
      const mem = plan.memory as {
        video_record_id?: number
        video_uuid?: string
        video_state?: string
      }
      out.push({
        plan,
        videoRecordId: mem.video_record_id ?? null,
        videoUuid: mem.video_uuid ?? null,
        videoState: (mem.video_state as VideoEntry['videoState']) ?? null,
      })
    }
    // 按预期完成时间排序, 跟 PlanScheduleView 一致
    out.sort((a, b) => {
      const aT = a.plan.expected_completion_time ?? ''
      const bT = b.plan.expected_completion_time ?? ''
      return aT.localeCompare(bT)
    })
    entries.value = out
  } catch (e: unknown) {
    errorMsg.value = (e as Error).message || '加载失败'
    entries.value = []
  } finally {
    loading.value = false
  }
}

// -- 列表项点击 --
async function onPick(entry: VideoEntry, idx: number): Promise<void> {
  // 已有 record_id: 直接跳详情页
  if (entry.videoRecordId) {
    router.push({ name: 'app-video-detail', params: { id: String(entry.videoRecordId) } })
    return
  }
  // 否则: 生成 (回填到 plan)
  if (!subjectId.value) {
    ElMessage({ message: 'x 缺少学科信息', customClass: 'x-toast' })
    return
  }
  if (generating.value !== null) return // 防重入
  generating.value = entry.plan.id
  try {
    const { data } = await startVideoCourse({
      subjectId: subjectId.value,
      topic: entry.plan.node_name,
      extraPrompt: (entry.plan.memory as { step_desc?: string } | undefined)?.step_desc ?? '',
      planId: entry.plan.id,
      // 兼容后端老逻辑 (PlanItem.id 字段), 现在用 plan.id 自身作为绑定键
      planNodeId: String(entry.plan.id),
    })
    // 乐观更新本地条目
    entry.videoRecordId = data.id
    entry.videoState = data.state as VideoEntry['videoState']
    // 跳转详情页轮询
    router.push({ name: 'app-video-detail', params: { id: String(data.id) } })
  } catch (e: unknown) {
    ElMessage({
      message: 'x 启动失败: ' + ((e as Error).message || '未知错误'),
      customClass: 'x-toast',
    })
  } finally {
    generating.value = null
  }
}

// -- 派生 --
const subjectName = computed<string>(() => {
  const code = currentSubject.code
  return getSubjectDisplayName(code) || code || '未选学科'
})

function statusOf(entry: VideoEntry): { text: string; tone: 'ready' | 'generating' | 'error' | 'pending' } {
  if (!entry.videoRecordId) return { text: '未生成', tone: 'pending' }
  if (entry.videoState === 'complete') return { text: '可观看', tone: 'ready' }
  if (entry.videoState === 'error') return { text: '生成失败', tone: 'error' }
  return { text: '生成中', tone: 'generating' }
}

onMounted(() => {
  void loadEntries()
})
</script>

<template>
  <div class="vc-shell">
    <!-- 左侧: 计划中的视频列表 -->
    <aside class="vc-side">
      <header class="vc-side-header">
        <div class="vc-side-title-row">
          <IconVideo :size="16" />
          <h2 class="vc-side-title">视频课</h2>
        </div>
        <p class="vc-side-sub">
          来自 <strong>{{ subjectName }}</strong> 学习计划
          <span v-if="entries.length" class="vc-side-count">{{ entries.length }}</span>
        </p>
      </header>

      <div v-if="loading" class="vc-side-loading">加载中…</div>

      <div v-else-if="errorMsg" class="vc-side-error">x {{ errorMsg }}</div>

      <div v-else-if="entries.length === 0" class="vc-side-empty">
        当前学科没有视频课计划。<br />
        去「计划」页生成一份试试。
      </div>

      <ul v-else class="vc-list">
        <li
          v-for="e in entries"
          :key="e.plan.id"
        >
          <button
            type="button"
            class="vc-item"
            :class="{ 'is-busy': generating === e.plan.id }"
            :disabled="generating !== null"
            @click="onPick(e, 0)"
          >
            <span class="vc-item-ico">
              <IconVideo :size="14" />
            </span>
            <span class="vc-item-body">
              <span class="vc-item-name">{{ e.plan.node_name }}</span>
              <span v-if="(e.plan.memory as { step_desc?: string } | undefined)?.step_desc" class="vc-item-desc">
                {{ (e.plan.memory as { step_desc?: string }).step_desc }}
              </span>
            </span>
            <span class="vc-item-state" :data-tone="statusOf(e).tone">
              <template v-if="statusOf(e).tone === 'ready'">
                <IconCheck :size="11" /> {{ statusOf(e).text }}
              </template>
              <template v-else-if="statusOf(e).tone === 'generating'">
                <IconHourglass :size="11" /> {{ statusOf(e).text }}
              </template>
              <template v-else-if="statusOf(e).tone === 'error'">x {{ statusOf(e).text }}</template>
              <template v-else>
                <IconArrow :size="11" /> {{ statusOf(e).text }}
              </template>
            </span>
            <span v-if="generating === e.plan.id" class="vc-item-spinner" aria-label="生成中" />
          </button>
        </li>
      </ul>
    </aside>

    <!-- 右侧: 默认空状态 -->
    <section class="vc-main">
      <div class="vc-main-empty">
        <div class="vc-main-empty-art" aria-hidden="true">
          <IconVideo :size="40" />
        </div>
        <h3 class="vc-main-empty-title">从左侧选一段视频开始</h3>
        <p class="vc-main-empty-sub">
          点击左侧任意条目, 可直接观看已生成的视频课,<br />
          或触发生成新的视频课程。
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* 全局壳 */
.vc-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 20px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 24px 60px;
  font-family: var(--x-font-display);
  color: var(--x-ink);
  background: var(--x-canvas);
  min-height: 100%;
  box-sizing: border-box;
}

/* 左侧栏 */
.vc-side {
  background: var(--x-canvas-card);
  border-radius: 16px;
  padding: 18px 14px;
  border: 1px solid var(--x-hairline);
  align-self: start;
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  overscroll-behavior: contain;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
              0 8px 24px rgba(15, 23, 42, 0.05);
}

.vc-side-header {
  padding: 0 6px 12px;
  border-bottom: 1px solid var(--x-hairline);
  margin-bottom: 10px;
}
.vc-side-title-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--x-primary);
}
.vc-side-title {
  font: 600 16px/1.2 var(--x-font-display);
  color: var(--x-ink);
  margin: 0;
  letter-spacing: -0.01em;
}
.vc-side-sub {
  font: 400 11px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
  margin: 6px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.vc-side-sub strong {
  color: var(--x-ink);
  font-weight: 600;
}
.vc-side-count {
  font: 500 10px/1 var(--x-font-display);
  background: var(--x-primary-soft);
  color: var(--x-primary);
  padding: 3px 7px;
  border-radius: 999px;
  margin-left: 4px;
}

.vc-side-loading,
.vc-side-error,
.vc-side-empty {
  padding: 24px 12px;
  font: 400 12px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
  text-align: center;
}
.vc-side-error {
  color: var(--x-error);
}

.vc-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px; /* 增加卡片间距 */
}

.vc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  color: inherit;
  transition: background 0.15s, border-color 0.15s, transform 0.1s, box-shadow 0.15s;
  position: relative;
  /* 确保可点击 */
  pointer-events: auto;
  z-index: 1;
}
.vc-item:hover:not(:disabled) {
  background: var(--x-canvas-soft);
  border-color: var(--x-hairline);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.vc-item:active:not(:disabled) {
  transform: translateY(0.5px);
}
.vc-item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.vc-item.is-busy {
  background: var(--x-primary-soft);
  border-color: var(--x-primary);
}

.vc-item-ico {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.vc-item.is-busy .vc-item-ico {
  background: var(--x-primary);
  color: var(--x-on-primary);
}

.vc-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px; /* 增加行间距 */
}
.vc-item-name {
  font: 600 12px/1.5 var(--x-font-display);
  color: var(--x-ink);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.vc-item-desc {
  font: 400 11px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.vc-item-state {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font: 600 10px/1 var(--x-font-display);
  padding: 3px 6px;
  border-radius: 5px;
  flex-shrink: 0;
  white-space: nowrap;
}
.vc-item-state[data-tone='ready'] {
  background: var(--x-success-soft);
  color: var(--x-success);
}
.vc-item-state[data-tone='generating'] {
  background: var(--x-warning-soft);
  color: var(--x-warning);
}
.vc-item-state[data-tone='error'] {
  background: var(--x-error-soft);
  color: var(--x-error);
}
.vc-item-state[data-tone='pending'] {
  background: var(--x-canvas-soft);
  color: var(--x-primary);
}

.vc-item-spinner {
  position: absolute;
  right: 10px;
  top: 50%;
  margin-top: -6px;
  width: 12px;
  height: 12px;
  border: 2px solid var(--x-blue-alpha-18);
  border-top-color: var(--x-primary);
  border-radius: 50%;
  animation: vc-spin 0.7s linear infinite;
}
@keyframes vc-spin {
  to { transform: rotate(360deg); }
}

/* 右侧主区 (默认空状态) */
.vc-main {
  background: var(--x-canvas-card);
  border-radius: 16px;
  border: 1px dashed var(--x-hairline-strong, var(--x-hairline));
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
              0 8px 24px rgba(15, 23, 42, 0.05);
}

.vc-main-empty {
  text-align: center;
  padding: 48px 24px;
  max-width: 380px;
}
.vc-main-empty-art {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  border-radius: 18px;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}
.vc-main-empty-title {
  font: 600 18px/1.3 var(--x-font-display);
  color: var(--x-ink);
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}
.vc-main-empty-sub {
  font: 400 13px/1.6 var(--x-font-display);
  color: var(--x-body-mid);
  margin: 0;
}

/* 响应式 */
@media (max-width: 900px) {
  .vc-shell {
    grid-template-columns: 1fr;
  }
  .vc-side {
    position: static;
    max-height: none;
  }
  .vc-main {
    min-height: 320px;
  }
}
</style>
