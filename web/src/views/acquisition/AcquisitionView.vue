<script setup lang="ts">
/**
 * 登录后欢迎页 (Acquisition)
 *
 *   路由: /welcome  (在 AppShell 外, 跟 login/register 同级)
 *   流程: 用户登录成功 → router.replace('/welcome') → 在这里挑选下一步
 *
 *   视觉:
 *     顶部 LampEffect (灯柱 + 光锥) + 大标题 "欢迎来到学径" + BlurText 流式进入
 *     中部 4 张快速入口卡: 刷题 / 星图 / 计划 / 记录
 *     底部 学科 chip 多选 (用于"立刻刷题"携带参数) + 跳过入口
 */

import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import LampEffect from '@/components/ui/lamp-effect/LampEffect.vue'
import BlurText from '@/components/BlurText.vue'
import { useUserStore } from '@/stores/user'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import type { SubjectCode } from '@/types/learning'

const router = useRouter()
const userStore = useUserStore()
const mySubjects = useMySubjectsStore()
const currentSubject = useCurrentSubjectStore()
const { user } = storeToRefs(userStore)

const displayName = computed<string>(
  () => user.value?.username || user.value?.email?.split('@')[0] || '同学',
)

onMounted(async () => {
  // 拉一下我的学科列表 (供下方 chips 显示)
  await mySubjects.loadFromBackend().catch(() => undefined)
})

// ── 快速入口 ──
interface QuickAction {
  key: string
  emoji: string
  title: string
  hint: string
  route: string
  primary?: boolean
}
const quickActions: QuickAction[] = [
  { key: 'practice', emoji: '🎯', title: '立刻刷题', hint: 'AI 根据薄弱点生成个性化题目', route: '/app/exercise', primary: true },
  { key: 'galaxy',   emoji: '🗺', title: '探索知识星图', hint: '看看你的知识地图长什么样', route: '/app/galaxy' },
  { key: 'plan',     emoji: '📋', title: '看看今日计划', hint: '今天要学什么一目了然', route: '/app/plan' },
  { key: 'records',  emoji: '📊', title: '回看学习记录', hint: '资源 / 习题 / 报告 三 tab', route: '/app/records' },
]

// ── 学科多选 (用于"立刻刷题"携带 selected subjects) ──
const selectedSubjects = ref<Set<string>>(new Set())
function toggleSubject(code: string): void {
  const s = new Set(selectedSubjects.value)
  if (s.has(code)) s.delete(code)
  else s.add(code)
  selectedSubjects.value = s
}

const hasSubjects = computed(() => mySubjects.subjects.length > 0)

function goAction(action: QuickAction): void {
  if (action.key === 'practice' && selectedSubjects.value.size > 0) {
    // 同步当前学科 = 用户选的第一个, 让 PracticeView 默认选中
    const first = [...selectedSubjects.value][0] as SubjectCode | undefined
    if (first) currentSubject.set(first)
  }
  router.replace(action.route)
}

function skip(): void {
  router.replace('/app/home')
}
</script>

<template>
  <div class="x-acq">
    <div class="x-acq-inner">
      <!-- 顶部: 灯效 + 欢迎语 -->
      <LampEffect class="x-acq-lamp">
        <p class="x-acq-eyebrow">AI · LEARNING ASSISTANT</p>
        <h1 class="x-acq-title">
          欢迎来到学径
          <span class="x-acq-name">, {{ displayName }} 👋</span>
        </h1>
        <p class="x-acq-sub">
          <BlurText
            :text="'准备好开始今天的学习了吗? 选一个方向, 我们陪你走。'"
            :delay="35"
            :duration="500"
          />
        </p>
      </LampEffect>

      <!-- 快速入口卡片 -->
      <section class="x-acq-actions">
        <button
          v-for="a in quickActions"
          :key="a.key"
          class="x-acq-action"
          :class="{ 'is-primary': a.primary }"
          @click="goAction(a)"
        >
          <span class="x-acq-action-emoji">{{ a.emoji }}</span>
          <span class="x-acq-action-body">
            <span class="x-acq-action-title">{{ a.title }}</span>
            <span class="x-acq-action-hint">{{ a.hint }}</span>
          </span>
          <span class="x-acq-action-arrow">→</span>
        </button>
      </section>

      <!-- 学科多选 (用于刷题快速带上) -->
      <section v-if="hasSubjects" class="x-acq-subjects">
        <div class="x-acq-section-head">
          <span class="x-acq-section-title">想练哪几门?</span>
          <span class="x-acq-section-hint">
            {{ selectedSubjects.size > 0
              ? `已选 ${selectedSubjects.size} 门 — 点「立刻刷题」即用`
              : '不选也没关系, 进刷题页再选' }}
          </span>
        </div>
        <div class="x-acq-subjects-chips">
          <button
            v-for="s in mySubjects.subjects"
            :key="s.id"
            type="button"
            class="x-acq-chip"
            :class="{ active: selectedSubjects.has(s.name) }"
            @click="toggleSubject(s.name)"
          >
            {{ s.display_name || s.name }}
          </button>
        </div>
      </section>

      <!-- 跳过 -->
      <div class="x-acq-foot">
        <button class="x-acq-skip" @click="skip">
          跳过, 直接进入主页 →
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.x-acq {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  padding: 24px 24px 64px;
  display: flex;
  justify-content: center;
}

.x-acq-inner {
  width: 100%;
  max-width: 1100px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ── LampEffect 内部文案样式 ───────────────────────── */
/* 上游 LampEffect 是深底 (synthwave 风格, min-h-screen + bg-slate-950).
   上游内部分层用 -translate-y-80 / scale-y-125 等位移, 容器太矮会让
   spotlight / 辉光线被裁掉看不见. 这里覆盖高度, 60vh 给足空间. */
.x-acq-lamp {
  margin-top: 8px;
  min-height: 60vh !important;     /* 覆盖上游 min-h-screen */
  height: 60vh;
}

.x-acq-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: oklch(78% 0.04 255);
  margin: 0 0 14px;
  text-transform: uppercase;
}

.x-acq-title {
  font-family: var(--x-font-display);
  font-size: clamp(34px, 6vw, 56px);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
  color: #fff;
  margin: 0 0 16px;
  display: inline;
  /* 亮色渐变让标题在光圈里更醒目 */
  background: linear-gradient(180deg, #fff 0%, oklch(80% 0.12 230) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.x-acq-name {
  font-size: 0.7em;
  font-weight: 500;
  color: oklch(85% 0.04 255);
  -webkit-text-fill-color: oklch(85% 0.04 255);
}

.x-acq-sub {
  font-size: 16px;
  line-height: 1.55;
  color: oklch(85% 0.04 255);
  margin: 0;
  max-width: 540px;
  margin-inline: auto;
}

/* ── 快速入口卡片 (4 张) ─────────────────────────── */
.x-acq-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.x-acq-action {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--x-canvas);
  border: 1.5px solid var(--x-hairline);
  border-radius: var(--x-rounded-md, 12px);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, transform 0.1s, box-shadow 0.15s;
  font-family: inherit;
}

.x-acq-action:hover {
  border-color: var(--x-primary);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px oklch(56% 0.19 255 / 0.08);
}

.x-acq-action.is-primary {
  background: linear-gradient(135deg, var(--x-primary-soft), oklch(96% 0.04 255));
  border-color: var(--x-primary);
}

.x-acq-action-emoji {
  font-size: 28px;
  flex-shrink: 0;
  line-height: 1;
}

.x-acq-action-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.x-acq-action-title {
  font-family: var(--x-font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
}

.x-acq-action-hint {
  font-size: 12.5px;
  color: var(--x-body-mid);
  line-height: 1.4;
}

.x-acq-action-arrow {
  font-size: 18px;
  color: var(--x-body-mid);
  transition: transform 0.15s, color 0.15s;
  flex-shrink: 0;
}

.x-acq-action:hover .x-acq-action-arrow {
  color: var(--x-primary);
  transform: translateX(4px);
}

/* ── 学科多选 ─────────────────────────────────────── */
.x-acq-subjects {
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md, 12px);
  padding: 20px 24px;
}

.x-acq-section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.x-acq-section-title {
  font-family: var(--x-font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--x-ink);
}

.x-acq-section-hint {
  font-size: 12px;
  color: var(--x-body-mid);
}

.x-acq-subjects-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.x-acq-chip {
  padding: 7px 14px;
  background: var(--x-canvas);
  border: 1.5px solid var(--x-hairline);
  border-radius: 999px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: var(--x-body);
  cursor: pointer;
  transition: all 0.12s;
}

.x-acq-chip:hover:not(.active) {
  border-color: oklch(80% 0.02 250);
}

.x-acq-chip.active {
  background: var(--x-primary);
  border-color: var(--x-primary);
  color: #fff;
  font-weight: 600;
}

/* ── 跳过 ────────────────────────────────────────── */
.x-acq-foot {
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

.x-acq-skip {
  background: transparent;
  border: 0;
  color: var(--x-body-mid);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 999px;
  transition: color 0.12s, background 0.12s;
}

.x-acq-skip:hover {
  color: var(--x-primary);
  background: var(--x-primary-soft);
}

/* ── 移动端 ──────────────────────────────────────── */
@media (max-width: 640px) {
  .x-acq { padding: 12px 16px 40px; }
  .x-acq-section-head { flex-direction: column; gap: 4px; align-items: flex-start; }
}
</style>