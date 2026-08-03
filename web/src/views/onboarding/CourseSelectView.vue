<script setup lang="ts">
/**
 * 课程选择页面 - 独立界面
 *
 *   路由: /course-select
 *   样式: 复刻 pages/选择课程.html 的横向滚动卡片设计
 *   功能: 用户选择一门课程后跳转到 /course-onboarding/:code
 */

import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { SUBJECT_CHOICES } from '@/api/subjects'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { useOnboardingStore } from '@/stores/onboarding'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { SUBJECT_COVERS } from '@/data/subject-covers'
import type { SubjectCode } from '@/types/learning'

const router = useRouter()
const mySubjects = useMySubjectsStore()
const onboarding = useOnboardingStore()
const currentSubject = useCurrentSubjectStore()

// ─── 课程数据 ────────────────────────────────────────────
const COVER_COLORS = [
  'oklch(22% 0.04 250)',
  'oklch(50% 0.20 260)',
  'oklch(40% 0.10 195)',
  'oklch(70% 0.14 210)',
  'oklch(28% 0.02 250)',
  'oklch(45% 0.16 320)',
  'oklch(60% 0.20 245)',
]

const SUBJECT_DESCS: Record<string, string> = {
  data_structure: '树、图、排序，与数据组织的艺术。',
  cybersecurity: '攻防、加密，与数字世界的安全守则。',
  iot: '传感器、嵌入式，与万物互联的蓝图。',
  electrical_automation: '电路、PLC、电机控制，与电气自动化的全貌。',
  mechanical_design: '机械制图、传动、零件，与机械设计的全貌。',
  advanced_math: '极限、导数、积分、级数，与高等数学的核心。',
  artificial_intelligence: '神经网络、深度学习，与智能的边界。',
}

const SUBJECT_FULL_DESCS: Record<string, string> = {
  data_structure: '深入研究计算机科学的核心数据结构与算法。从线性表到树形结构，从图论到动态规划，掌握高效组织和处理数据的方法论。',
  cybersecurity: '探索网络空间安全的攻防技术。学习密码学原理、漏洞分析、渗透测试和安全防护，构建数字世界的安全防线。',
  iot: '理解物联网的完整技术栈。从传感器硬件到通信协议，从边缘计算到云平台，掌握万物互联的系统设计能力。',
  electrical_automation: '系统掌握电气自动化的原理与实践。从电路基础、模拟/数字电路、电力电子到 PLC 编程、变频器与伺服系统、传感器检测与实时控制，覆盖工控现场全链路。',
  mechanical_design: '系统掌握机械设计的核心方法论。从机械制图、AutoCAD/SolidWorks 工具到材料力学、热力学、流体力学、传动系统与轴承/联轴器选型，覆盖机械产品设计全周期。',
  advanced_math: '系统掌握高等数学的核心知识。从极限、连续、导数、微分、积分到级数、泰勒展开、多元函数偏导、重积分与曲线/曲面积分，覆盖工科数学基础。',
  artificial_intelligence: '探索人工智能的前沿技术。学习机器学习、深度学习、自然语言处理和计算机视觉，理解智能系统的构建原理。',
}

// ─── 轮播状态 ────────────────────────────────────────────
const trackRef = ref<HTMLElement | null>(null)
const carouselRef = ref<HTMLElement | null>(null)
const activeCardIndex = ref<number>(0)

// 卡片尺寸常量 (与 CSS 保持一致)
const CARD_W = 320
const CARD_GAP = 32
const STRIDE = CARD_W + CARD_GAP
const N = SUBJECT_CHOICES.length
const MAX_SCROLL = (N - 1) * STRIDE
const DEFAULT_IDX = 0

let currentX = -DEFAULT_IDX * STRIDE
let targetX = -DEFAULT_IDX * STRIDE
let rafId: number | null = null
let wheelTimer: ReturnType<typeof setTimeout> | null = null

// ─── helpers ──────────────────────────────────────────────
function getCoverBg(index: number): string {
  return COVER_COLORS[index % COVER_COLORS.length] ?? '#F2F2F7'
}

function getSubjectDesc(code: string): string {
  return SUBJECT_DESCS[code] ?? ''
}

function getSubjectFullDesc(code: string | undefined): string {
  if (!code) return ''
  return SUBJECT_FULL_DESCS[code] || ''
}

function isOwned(code: string | undefined): boolean {
  if (!code) return false
  return mySubjects.subjects.some(s => s.name === code)
}

// ─── 轮播核心逻辑 ──────────────────────────────────────
function setActive(idx: number): void {
  activeCardIndex.value = idx
}

function goTo(i: number): void {
  const idx = Math.max(0, Math.min(N - 1, i))
  targetX = -idx * STRIDE
}

function step(dir: number): void {
  goTo(activeCardIndex.value + dir)
}

function loop(): void {
  const k = 0.14
  currentX += (targetX - currentX) * k

  if (trackRef.value) {
    trackRef.value.style.transform = `translate3d(${currentX}px, 0, 0)`
  }

  const idx = Math.round(-currentX / STRIDE)
  const clamped = Math.max(0, Math.min(N - 1, idx))
  if (clamped !== activeCardIndex.value) {
    setActive(clamped)
  }

  rafId = requestAnimationFrame(loop)
}

function handleWheel(e: WheelEvent): void {
  e.preventDefault()
  const primary = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY
  const scaled = primary * 1.15
  targetX = Math.max(-MAX_SCROLL, Math.min(0, targetX - scaled))

  if (wheelTimer) clearTimeout(wheelTimer)
  wheelTimer = setTimeout(() => {
    const nearest = Math.round(-targetX / STRIDE)
    const c = Math.max(0, Math.min(N - 1, nearest))
    targetX = -c * STRIDE
  }, 180)
}

function handleKeydown(e: KeyboardEvent): void {
  if (e.target && (e.target as HTMLElement).tagName === 'INPUT') return
  if (e.key === 'ArrowRight') { e.preventDefault(); step(1) }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1) }
  else if (e.key === 'Enter') { e.preventDefault(); selectCourse() }
}

// 拖拽支持
let dragStart: number | null = null
let startX = 0

function handlePointerDown(e: PointerEvent): void {
  dragStart = e.clientX
  startX = currentX
  ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
}

function handlePointerMove(e: PointerEvent): void {
  if (dragStart == null) return
  const dx = e.clientX - dragStart
  targetX = Math.max(-MAX_SCROLL, Math.min(0, startX + dx))
}

function handlePointerUp(e: PointerEvent): void {
  if (dragStart == null) return
  dragStart = null
  const nearest = Math.round(-targetX / STRIDE)
  const c = Math.max(0, Math.min(N - 1, nearest))
  targetX = -c * STRIDE
}

function handleResize(): void {
  targetX = -activeCardIndex.value * STRIDE
}

function selectCourse(): void {
  const code = SUBJECT_CHOICES[activeCardIndex.value]?.code
  if (code) {
    router.push(`/course-onboarding/${code}`)
  }
}

// 当前详情面板的学科 code —— 模板里多处用到, 集中一处方便判空
const currentDetailCode = computed<string | undefined>(
  () => SUBJECT_CHOICES[activeCardIndex.value]?.code,
)

function enterCourse(code: string | undefined): void {
  if (!code) return
  // 设置当前学科
  const subject = mySubjects.subjects.find(s => s.name === code)
  if (subject) {
    currentSubject.set(subject.name as SubjectCode)
    // 标记画像已完成（已选课程的画像肯定已完成）
    onboarding.markOnboarded(code)
  }
  // 跳转到课程学习页面
  router.push('/app/home')
}

function goBack(): void {
  router.push('/app/plan/courses')
}

/**
 * 跳过选课 → 放用户先进主界面自由探索
 *   1. onboarding.skipOnboarding() 写持久化标志
 *   2. 路由守卫看到这个标志后不再强制拦截 /app/*
 *   3. 跳到 /app/home, 用户可从「我的课程 / 书架」主动加课
 */
function skipForNow(): void {
  onboarding.skipOnboarding()
  router.push('/app/home')
}

// ─── lifecycle ────────────────────────────────────────────
onMounted(async () => {
  await mySubjects.loadFromBackend().catch(() => undefined)
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('resize', handleResize)
  rafId = requestAnimationFrame(loop)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('resize', handleResize)
  if (rafId) cancelAnimationFrame(rafId)
  if (wheelTimer) clearTimeout(wheelTimer)
})
</script>

<template>
  <div class="x-cs">
    <!-- 顶部导航 -->
    <header class="x-masthead">
      <div class="x-brand">
        <span class="x-brand-mark" aria-hidden="true"></span>
        <span class="x-brand-name">学径</span>
        <span class="x-brand-tag">课程目录 / Catalogue</span>
      </div>
      <div class="x-masthead-meta">
        <span class="x-item"><span class="x-live-dot"></span>选择课程</span>
        <span class="x-item">共 <strong>{{ SUBJECT_CHOICES.length }}</strong> 门课程</span>
      </div>
    </header>

    <!-- 主体：轮播区 -->
    <main class="x-stage">
      <div ref="carouselRef" class="x-carousel" @wheel.prevent="handleWheel">
        <div class="x-center-axis" aria-hidden="true"></div>
        <div
          ref="trackRef"
          class="x-track"
          @pointerdown="handlePointerDown"
          @pointermove="handlePointerMove"
          @pointerup="handlePointerUp"
          @pointercancel="handlePointerUp"
        >
          <div
            v-for="(c, index) in SUBJECT_CHOICES"
            :key="c.code"
            class="x-card"
            :class="{
              'is-active': activeCardIndex === index,
              'is-adjacent': Math.abs(activeCardIndex - index) === 1,
              'is-owned': isOwned(c.code)
            }"
            @click="goTo(index)"
          >
            <span class="x-card-corner tl"></span>
            <span class="x-card-corner tr"></span>
            <span class="x-card-corner bl"></span>
            <span class="x-card-corner br"></span>
            <div class="x-card-cover" :style="{ background: getCoverBg(index) }">
              <img
                :src="SUBJECT_COVERS[c.code]"
                :alt="c.name"
                class="x-card-cover-img"
              />
              <div class="x-card-cover-overlay">
                <span class="x-card-num">{{ String(index + 1).padStart(2, '0') }}</span>
              </div>
              <div v-if="isOwned(c.code)" class="x-card-owned-badge">
                <span class="x-owned-icon">✓</span>
                <span>已学习</span>
              </div>
              <div class="x-card-meta-cover">
                <span>{{ c.code }}</span>
                <span>计算机科学</span>
              </div>
            </div>
            <div class="x-card-body">
              <div>
                <div class="x-card-title">{{ c.name }}</div>
                <div class="x-card-sub">{{ getSubjectDesc(c.code) }}</div>
              </div>
              <div class="x-card-foot">
                <span class="x-card-arrow">›</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 详情区 -->
      <div class="x-detail">
        <div class="x-detail-col">
          <div class="x-kicker">课程</div>
          <div class="x-code-block">
            <span class="x-num">{{ String(activeCardIndex + 1).padStart(2, '0') }}</span>
            {{ SUBJECT_CHOICES[activeCardIndex]?.code }}
          </div>
          <div class="x-cat-block">计算机科学</div>
        </div>
        <div class="x-detail-col">
          <h2 class="x-detail-title">{{ SUBJECT_CHOICES[activeCardIndex]?.name }}</h2>
          <p class="x-detail-body">{{ getSubjectFullDesc(SUBJECT_CHOICES[activeCardIndex]?.code) }}</p>
        </div>
        <div class="x-detail-col x-detail-action">
          <button
            v-if="isOwned(currentDetailCode)"
            class="x-btn x-btn-success x-btn-xl"
            @click="enterCourse(currentDetailCode)"
          >
            进入学习 →
          </button>
          <button
            v-else
            class="x-btn x-btn-primary x-btn-xl"
            @click="selectCourse"
          >
            选择这门课程 →
          </button>
          <button class="x-btn x-btn-ghost x-btn-sm" @click="goBack">
            返回课程列表
          </button>
          <!-- 跳过入口: 让用户能先进主界面自由探索, 之后从「我的课程」主动加课 -->
          <button
            class="x-btn x-btn-skip"
            type="button"
            title="先不选课, 进主界面看看"
            @click="skipForNow"
          >
            <span class="x-btn-skip-label">稍后再选, 先逛逛 →</span>
            <span class="x-btn-skip-hint">可随时从「我的课程」加课</span>
          </button>
        </div>
      </div>
    </main>

    <!-- 底部 HUD -->
    <footer class="x-hud">
      <div class="x-hud-counter">
        <span class="x-num">{{ String(activeCardIndex + 1).padStart(2, '0') }}</span>
        <span class="x-total">/ {{ String(N).padStart(2, '0') }}</span>
        <div class="x-hud-progress">
          <div class="x-hud-progress-bar" :style="{ width: `${(activeCardIndex + 1) / N * 100}%` }"></div>
        </div>
      </div>
      <div class="x-hud-hint">
        <span><kbd>滚轮</kbd>浏览</span>
        <span><kbd>←</kbd> <kbd>→</kbd>切换</span>
        <span><kbd>Enter</kbd>选中</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.x-cs {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: oklch(20% 0.022 250);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'PingFang SC', system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  background-color: oklch(98.5% 0.005 240);
  background-image: radial-gradient(circle at 1px 1px, oklch(88% 0.008 240) 1px, transparent 0);
  background-size: 24px 24px;
  background-position: -1px -1px;
}

/* 顶部导航 */
.x-masthead {
  height: 72px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid oklch(92% 0.005 240);
  background: oklch(98.5% 0.005 240 / 0.85);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  flex-shrink: 0;
  z-index: 10;
}
.x-brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.x-brand-mark {
  width: 30px;
  height: 30px;
  border: 1.5px solid oklch(20% 0.022 250);
  border-radius: 6px;
  position: relative;
  display: grid;
  place-items: center;
}
.x-brand-mark::before {
  content: "";
  width: 9px;
  height: 9px;
  background: oklch(60% 0.20 245);
  border-radius: 2px;
}
.x-brand-name {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', system-ui, sans-serif;
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.022em;
  line-height: 1;
}
.x-brand-tag {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: oklch(48% 0.018 250);
  letter-spacing: 0.22em;
  text-transform: uppercase;
  padding-top: 2px;
}
.x-masthead-meta {
  display: flex;
  align-items: center;
  gap: 28px;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: oklch(48% 0.018 250);
  letter-spacing: 0.22em;
  text-transform: uppercase;
}
.x-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.x-item strong { color: oklch(20% 0.022 250); font-weight: 600; }
.x-live-dot {
  width: 7px; height: 7px;
  background: oklch(60% 0.20 245);
  border-radius: 50%;
  position: relative;
  display: inline-block;
}
.x-live-dot::before {
  content: "";
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: oklch(60% 0.20 245);
  opacity: 0.4;
  animation: pulse 1.8s ease-out infinite;
}
@keyframes pulse {
  0%   { transform: scale(0.8); opacity: 0.5; }
  80%  { transform: scale(2.2); opacity: 0; }
  100% { transform: scale(2.2); opacity: 0; }
}

/* 主体 */
.x-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

/* 轮播区 */
.x-carousel {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  min-height: 0;
}
.x-carousel::before, .x-carousel::after {
  content: "";
  position: absolute;
  top: 0; bottom: 0;
  width: 120px;
  pointer-events: none;
  z-index: 5;
}
.x-carousel::before { left: 0; background: linear-gradient(to right, oklch(98.5% 0.005 240) 25%, transparent); }
.x-carousel::after  { right: 0; background: linear-gradient(to left, oklch(98.5% 0.005 240) 25%, transparent); }

.x-center-axis {
  position: absolute;
  top: 0; bottom: 0;
  left: 50%;
  width: 1px;
  background: oklch(60% 0.20 245);
  opacity: 0.25;
  z-index: 4;
  pointer-events: none;
}
.x-center-axis::before, .x-center-axis::after {
  content: "";
  position: absolute;
  left: -3px;
  width: 7px;
  height: 7px;
  background: oklch(60% 0.20 245);
  transform: rotate(45deg);
}
.x-center-axis::before { top: 12px; }
.x-center-axis::after  { bottom: 12px; }

.x-track {
  display: flex;
  gap: 32px;
  padding: 0 calc(50% - 160px);
  will-change: transform;
  align-items: center;
  cursor: grab;
}
.x-track:active { cursor: grabbing; }

/* 卡片 */
.x-card {
  flex-shrink: 0;
  width: 320px;
  height: 440px;
  background: oklch(100% 0 0);
  border: 1px solid oklch(92% 0.005 240);
  display: flex;
  flex-direction: column;
  position: relative;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.55s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.55s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.55s cubic-bezier(0.2, 0.8, 0.2, 1), border-color 0.55s cubic-bezier(0.2, 0.8, 0.2, 1);
  opacity: 0.36;
  transform: scale(0.92) translateY(0);
  border-radius: 4px;
}
.x-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: oklch(60% 0.20 245);
  transform: scaleX(0);
  transform-origin: left center;
  z-index: 5;
  transition: transform 0.45s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.x-card.is-active::before { transform: scaleX(1); }

.x-card-corner {
  position: absolute;
  width: 10px;
  height: 10px;
  border-color: oklch(60% 0.20 245);
  border-style: solid;
  z-index: 6;
  opacity: 0;
  transition: opacity 0.35s ease;
}
.x-card-corner.tl { top: 8px;    left: 8px;    border-width: 1.5px 0 0 1.5px; }
.x-card-corner.tr { top: 8px;    right: 8px;   border-width: 1.5px 1.5px 0 0; }
.x-card-corner.bl { bottom: 8px; left: 8px;    border-width: 0 0 1.5px 1.5px; }
.x-card-corner.br { bottom: 8px; right: 8px;   border-width: 0 1.5px 1.5px 0; }
.x-card.is-active .x-card-corner { opacity: 1; }

.x-card.is-active {
  opacity: 1;
  transform: scale(1.06) translateY(-14px);
  box-shadow: 0 1px 0 0 oklch(60% 0.20 245) inset, 0 30px 60px -28px rgba(20, 30, 80, 0.35), 0 12px 28px -16px rgba(20, 30, 80, 0.18);
  border-color: oklch(60% 0.20 245);
  z-index: 2;
}
.x-card.is-adjacent { opacity: 0.7; }
.x-card.is-owned {
  opacity: 0.85;
  filter: grayscale(0.3);
}
.x-card.is-owned.is-active {
  opacity: 0.9;
  filter: grayscale(0.15);
}

/* 已学习徽章 */
.x-card-owned-badge {
  position: absolute;
  top: 14px;
  left: 22px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  border-radius: 20px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
  font-size: 11px;
  font-weight: 500;
  color: oklch(98% 0.005 240);
  z-index: 2;
  letter-spacing: 0.02em;
}
.x-owned-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: oklch(60% 0.18 145);
  border-radius: 50%;
  font-size: 10px;
  color: #fff;
}

.x-card-cover {
  height: 58%;
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 22px 16px;
  overflow: hidden;
  border-bottom: 1px solid oklch(92% 0.005 240);
}
.x-card-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 22px 22px;
  pointer-events: none;
}
.x-card-cover-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}
.x-card-cover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.7));
  z-index: 1;
}
.x-card-num {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 80px;
  font-weight: 600;
  line-height: 0.85;
  letter-spacing: -0.05em;
  color: oklch(98% 0.005 240);
  font-variant-numeric: tabular-nums;
  z-index: 1;
  position: relative;
}
.x-card-meta-cover {
  position: absolute;
  bottom: 14px;
  left: 22px;
  right: 22px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 9.5px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: oklch(98% 0.005 240);
  opacity: 0.78;
  z-index: 1;
}

.x-card-body {
  flex: 1;
  padding: 18px 22px 18px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: oklch(100% 0 0);
}
.x-card-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 22px;
  font-weight: 600;
  line-height: 1.18;
  letter-spacing: -0.018em;
}
.x-card-sub {
  font-size: 12px;
  color: oklch(48% 0.018 250);
  line-height: 1.45;
  margin-top: 6px;
}
.x-card-foot {
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
}
.x-card-arrow {
  color: oklch(60% 0.20 245);
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 18px;
  line-height: 1;
  transform: translateX(0);
  transition: transform 0.3s ease;
}
.x-card:hover .x-card-arrow { transform: translateX(4px); }

/* 详情区 */
.x-detail {
  height: 180px;
  border-top: 1px solid oklch(92% 0.005 240);
  padding: 24px 40px 22px;
  display: grid;
  grid-template-columns: 1.05fr 2.3fr 1.4fr;
  gap: 36px;
  background: oklch(99.5% 0.003 240);
  flex-shrink: 0;
}
.x-detail-col { display: flex; flex-direction: column; justify-content: center; }
.x-detail-action { align-items: center; gap: 12px; }

.x-kicker {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: oklch(48% 0.018 250);
  letter-spacing: 0.22em;
  text-transform: uppercase;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-kicker::before { content: "//"; color: oklch(60% 0.20 245); }

.x-code-block {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.x-code-block .x-num { color: oklch(60% 0.20 245); font-weight: 600; }
.x-cat-block {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: oklch(48% 0.018 250);
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.x-detail-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 30px;
  font-weight: 600;
  line-height: 1.12;
  letter-spacing: -0.025em;
  margin-bottom: 12px;
}
.x-detail-body {
  font-size: 13.5px;
  line-height: 1.65;
  max-width: 64ch;
}

.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: all 120ms ease;
}
.x-btn-primary {
  background: oklch(60% 0.20 245);
  color: #fff;
  border-radius: 8px;
}
.x-btn-primary:hover { opacity: 0.9; }
.x-btn-success {
  background: oklch(60% 0.18 145);
  color: #fff;
  border-radius: 8px;
}
.x-btn-success:hover { opacity: 0.9; }
.x-btn-disabled {
  background: oklch(88% 0.008 240);
  color: oklch(60% 0.01 240);
  border-radius: 8px;
  cursor: not-allowed;
}
.x-btn-xl {
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}
.x-btn-ghost {
  background: transparent;
  color: oklch(48% 0.018 250);
}
.x-btn-ghost:hover { color: oklch(20% 0.022 250); }
.x-btn-sm { font-size: 13px; padding: 6px 12px; }

/* 跳过选课入口 —— 比 ghost 还轻, 纯文字带下划线, 跟详情区其它主操作拉开层级 */
.x-btn-skip {
  background: transparent;
  border: none;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  cursor: pointer;
  font-family: inherit;
  color: oklch(54% 0.014 240);
  transition: color 0.15s;
  margin-top: 4px;
}
.x-btn-skip:hover { color: oklch(36% 0.02 240); }
.x-btn-skip-label {
  font-size: 13.5px;
  text-decoration: underline;
  text-underline-offset: 4px;
  text-decoration-color: oklch(85% 0.01 240);
}
.x-btn-skip:hover .x-btn-skip-label { text-decoration-color: currentColor; }
.x-btn-skip-hint {
  font-size: 11px;
  color: oklch(60% 0.014 240);
  font-family: var(--x-font-mono);
  letter-spacing: 0.4px;
}

/* 底部 HUD */
.x-hud {
  height: 52px;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid oklch(92% 0.005 240);
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  color: oklch(48% 0.018 250);
  letter-spacing: 0.22em;
  text-transform: uppercase;
  flex-shrink: 0;
  background: oklch(99% 0.003 240 / 0.85);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.x-hud-counter {
  display: flex;
  align-items: center;
  gap: 14px;
}
.x-hud-counter .x-num {
  color: oklch(20% 0.022 250);
  font-weight: 600;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}
.x-hud-counter .x-total { color: oklch(48% 0.018 250); }
.x-hud-progress {
  width: 220px;
  height: 1px;
  background: oklch(82% 0.008 240);
  position: relative;
  margin-left: 10px;
}
.x-hud-progress-bar {
  height: 100%;
  background: oklch(60% 0.20 245);
  transition: width 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.x-hud-hint {
  display: flex;
  gap: 22px;
}
.x-hud-hint span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.x-hud-hint kbd {
  display: inline-block;
  padding: 2px 7px;
  border: 1px solid oklch(82% 0.008 240);
  border-radius: 3px;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 9.5px;
  color: oklch(20% 0.022 250);
  text-transform: none;
  letter-spacing: 0;
  background: oklch(100% 0 0);
}
</style>
