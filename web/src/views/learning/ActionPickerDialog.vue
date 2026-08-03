<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getSubjectDisplayName } from '@/api/subjects'
import type { SubjectCode } from '@/types/learning'
import type { ResourceHistoryItem } from '@/types/learning'
import type { ExerciseRecord } from '@/types/learning'
import {
  IconCross,
  IconArrow,
  IconPlan,
  IconBook,
  IconGalaxy,
  IconExercise,
  IconExam,
} from '@/components/icons'

/**
 * 学习记录 —— 资源/答题 行的 "去哪儿" 弹窗
 *
 *   父级 (LearningRecordsView) 通过 v-model:open + :item 传进来,
 *   用户点某个跳转按钮 → router.push + 关闭弹窗 + toast 提示.
 *
 *   5 个跳转目标按"该 subject 关联的位置"组合:
 *     - 计划 /app/plan         — 课程总览 + 画像
 *     - 书架 /app/book         — 已添加的学科
 *     - 星图 /app/galaxy       — 该 subject 的 3D 知识图谱
 *     - 刷题 /app/exercise     — 该 subject 的自适应练习
 *     - 评测 /app/exam         — 该 subject 的 AI 出题
 *
 *   subject 来自 item.subject, 跳转时附在 query 上让目标页可选
 *   拿这个 subject (没拿的话会回退到全部, 行为不偏离预期).
 */

// ============================================================
// 入参类型 —— 资源 OR 答题 (联合类型, 实际同一弹窗)
// ============================================================
type PickerItem =
  | { kind: 'resource'; data: ResourceHistoryItem }
  | { kind: 'exercise'; data: ExerciseRecord }

const props = defineProps<{
  open: boolean
  item: PickerItem | null
}>()

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
}>()

const router = useRouter()

const subject = computed<SubjectCode | null>(() => props.item?.data.subject ?? null)
const subjectDisplay = computed<string>(() =>
  subject.value ? getSubjectDisplayName(subject.value) : '—',
)
const itemTitle = computed<string>(() => {
  if (!props.item) return ''
  if (props.item.kind === 'resource') return props.item.data.resource_name
  return props.item.data.question
})
const itemSubtitle = computed<string>(() => {
  if (!props.item) return ''
  if (props.item.kind === 'resource') {
    const r = props.item.data
    return `${labelOfType(r.type)} · ${r.duration_min} 分钟 · ${formatDate(r.timestamp)}`
  }
  const e = props.item.data
  return `${e.knowledge_node} · ${e.correct ? '答对' : '答错'} · ${formatDate(e.timestamp)}`
})

function labelOfType(t: string): string {
  return ({ video: '视频', article: '文章', pdf: 'PDF', interactive: '交互课件' } as const)[t as 'video'] ?? t
}
function formatDate(iso: string): string {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// ============================================================
// 5 个跳转目标 —— 跟该 subject 强关联
// ============================================================
interface Destination {
  to: string                                  // 路由 (含 ?subject= query)
  label: string
  hint: string
  icon: typeof IconPlan
}

const destinations = computed<Destination[]>(() => {
  const sub = subject.value ?? ''
  return [
    {
      to: `/app/plan?subject=${sub}`,
      label: '进入计划',
      hint: '查看该学科的课程 + 学习画像',
      icon: IconPlan,
    },
    {
      to: `/app/book?subject=${sub}`,
      label: '去书架',
      hint: '查看已添加的学科, 补全你正在学的',
      icon: IconBook,
    },
    {
      to: `/app/galaxy?subject=${sub}`,
      label: '看星图',
      hint: '该学科的 3D 知识图谱 + 节点掌握度',
      icon: IconGalaxy,
    },
    {
      to: `/app/exercise?subject=${sub}`,
      label: '刷题',
      hint: '基于该学科的自适应出题 + 判分',
      icon: IconExercise,
    },
    {
      to: `/app/exam?subject=${sub}`,
      hint: '该学科的 AI 出题 (配置题数 + 难度)',
      label: '评测',
      icon: IconExam,
    },
  ]
})

// ============================================================
// Actions
// ============================================================
function close(): void {
  emit('update:open', false)
}

function go(to: string, label: string): void {
  close()
  // query 是 string 类型, vue-router 接受 string
  router.push(to).catch((err) => {
    // 路由重复 navigate 会被 reject 一次, 静默吞掉
    if (err?.name !== 'NavigationDuplicated') {
      // eslint-disable-next-line no-console
      console.error('[picker] navigate failed', err)
    }
  })
  ElMessage({
    message: `→ 已跳转: ${label}`,
    customClass: 'x-toast',
  })
}

// ESC 关闭
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Escape' && props.open) close()
}
</script>

<template>
  <teleport to="body">
    <transition name="x-picker-fade">
      <div
        v-if="open"
        class="x-picker-backdrop"
        @click.self="close"
        @keydown="onKeydown"
        tabindex="-1"
      >
        <div class="x-picker" role="dialog" aria-modal="true" aria-labelledby="pickerTitle">
          <header class="x-picker-head">
            <p class="x-eyebrow x-eyebrow-mute">{{ subjectDisplay }}</p>
            <h3 id="pickerTitle" class="x-picker-title">{{ itemTitle }}</h3>
            <p class="x-picker-subtitle">{{ itemSubtitle }}</p>
            <button class="x-picker-close" aria-label="关闭" @click="close"><IconCross :size="14" /></button>
          </header>

          <div class="x-picker-body">
            <p class="x-picker-hint">点击下方任一位置跳转 —— 帮你把"看过的 / 答过的"和"接下来要做的"接上。</p>
            <ul class="x-picker-list">
              <li v-for="d in destinations" :key="d.to">
                <button class="x-picker-dest" @click="go(d.to, d.label)">
                  <span class="x-picker-dest-glyph" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-primary)"><component :is="d.icon" :size="20" /></span>
                  <span class="x-picker-dest-body">
                    <span class="x-picker-dest-label">{{ d.label }}</span>
                    <span class="x-picker-dest-hint">{{ d.hint }}</span>
                  </span>
                  <span class="x-picker-dest-arrow" style="display:inline-flex;align-items:center"><IconArrow :size="14" /></span>
                </button>
              </li>
            </ul>
          </div>

          <footer class="x-picker-foot">
            <button class="x-btn x-btn-outline-sm" @click="close">取消</button>
          </footer>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
/* ============================================================
   弹窗 —— 居中卡片 + 5 个跳转目标列表
   ============================================================ */
.x-picker-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: oklch(0% 0 0 / 0.45);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  outline: none;     /* 自带 tabindex=-1 隐藏 focus ring */
}

.x-picker {
  width: 100%;
  max-width: 480px;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 16px;
  box-shadow: 0 24px 60px oklch(0% 0 0 / 0.18);
  display: flex;
  flex-direction: column;
}

.x-picker-head {
  position: relative;
  padding: 22px 24px 18px;
  border-bottom: 1px solid var(--x-hairline);
}
.x-picker-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.2px;
  color: var(--x-ink);
  margin: 4px 0 4px;
  padding-right: 32px;       /* 给关闭按钮让位 */
  line-height: 1.4;
  word-break: break-word;
}
.x-picker-subtitle {
  font-size: 12px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
  color: var(--x-body-mid);
  margin: 0;
}
.x-picker-close {
  position: absolute;
  top: 14px;
  right: 14px;
  background: transparent;
  border: 0;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 22px;
  line-height: 1;
  color: var(--x-body-mid);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.x-picker-close:hover {
  background: var(--x-canvas-soft);
  color: var(--x-ink);
}

.x-picker-body {
  padding: 18px 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.x-picker-hint {
  font-size: 12.5px;
  color: var(--x-body);
  margin: 0;
  line-height: 1.6;
  padding: 10px 12px;
  background: var(--x-canvas-soft);
  border-radius: 8px;
  border-left: 3px solid var(--x-primary);
}

.x-picker-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.x-picker-dest {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.12s, box-shadow 0.15s;
}
.x-picker-dest:hover {
  border-color: var(--x-primary);
  transform: translateX(2px);
  box-shadow: 0 2px 8px oklch(52% 0.18 255 / 0.10);
}
.x-picker-dest-glyph {
  font-size: 20px;
  line-height: 1;
  color: var(--x-primary);
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}
.x-picker-dest-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.x-picker-dest-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  font-family: var(--x-font-display);
}
.x-picker-dest-hint {
  font-size: 11.5px;
  color: var(--x-body-mid);
  line-height: 1.4;
}
.x-picker-dest-arrow {
  font-size: 16px;
  color: var(--x-body-mid);
  flex-shrink: 0;
  transition: transform 0.12s, color 0.15s;
}
.x-picker-dest:hover .x-picker-dest-arrow {
  color: var(--x-primary);
  transform: translateX(4px);
}

.x-picker-foot {
  padding: 14px 24px;
  border-top: 1px solid var(--x-hairline);
  display: flex;
  justify-content: flex-end;
  background: var(--x-canvas-soft);
}

/* === 进出过渡 === */
.x-picker-fade-enter-active,
.x-picker-fade-leave-active {
  transition: opacity 0.15s ease;
}
.x-picker-fade-enter-from,
.x-picker-fade-leave-to {
  opacity: 0;
}
.x-picker-fade-enter-active .x-picker,
.x-picker-fade-leave-active .x-picker {
  transition: transform 0.18s cubic-bezier(0.2, 0.7, 0.2, 1);
}
.x-picker-fade-enter-from .x-picker { transform: translateY(8px) scale(0.98); }
.x-picker-fade-leave-to   .x-picker { transform: translateY(4px) scale(0.99); }

/* === 复用 x-btn (跟其他 view 风格一致) === */
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
.x-btn-outline-sm {
  background: transparent;
  color: var(--x-ink);
  border: 1px solid var(--x-ink-alpha-15, var(--x-hairline));
  padding: 6px 14px;
  font-size: 12px;
}
.x-btn-outline-sm:hover:not(:disabled) {
  background: var(--x-canvas-soft);
  border-color: var(--x-ink-alpha-30, var(--x-hairline));
}

.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--x-ink);
  margin: 0;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

@media (max-width: 480px) {
  .x-picker { max-width: 100%; }
  .x-picker-dest { padding: 10px 12px; gap: 10px; }
  .x-picker-dest-glyph { font-size: 18px; width: 20px; }
}
</style>
