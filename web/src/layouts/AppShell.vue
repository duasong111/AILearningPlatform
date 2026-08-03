<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UserWidget from '@/components/UserWidget.vue'
import WelcomeModal from '@/components/WelcomeModal.vue'
import { getSubjectDisplayName } from '@/api/subjects'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { useOnboardingStore } from '@/stores/onboarding'
import { useUserStore } from '@/stores/user'
import type { SubjectCode } from '@/types/learning'
import {
  BrandMark,
  IconHome,
  IconGalaxy,
  IconDialog,
  IconPlan,
  IconBook,
  IconVideo,
  IconExercise,
  IconExam,
} from '@/components/icons'

const router = useRouter()
const route = useRoute()
const currentSubject = useCurrentSubjectStore()
const mySubjects = useMySubjectsStore()
const onboarding = useOnboardingStore()
const userStore = useUserStore()

/**
 * 首次登录欢迎弹窗触发逻辑
 *   触发由 onboarding.welcomeMode 决定:
 *     - 'always': 每次登录后 + 0 门课 → 弹
 *     - 'first' : 仅在 !welcomeShown 时弹 (首次)
 *     - 'never' : 永不弹
 *   关闭: 用户点 "去选课" / "先逛逛" / X / ESC → closeWelcome() 标记已见过
 */
watch(
  () => ({
    authed: userStore.isAuthenticated,
    subjectsLen: mySubjects.subjects.length,
    loading: mySubjects.loading,
    mode: onboarding.welcomeMode,
    shown: onboarding.welcomeShown,
    open: onboarding.welcomeOpen,
    path: route.path,
  }),
  (s) => {
    // 通用前置条件
    if (!s.authed || s.loading) return
    if (!s.path.startsWith('/app')) return
    if (s.open) return                      // 已开着, 不重复触发
    if (onboarding.welcomeOpen) return

    // 按模式判定
    if (s.mode === 'never') return         // 永不弹
    if (s.mode === 'first' && s.shown) return  // 仅首次, 已见过
    // 已有课程的也不弹 (避免骚扰已有进度的用户)
    if (s.subjectsLen > 0) return

    onboarding.openWelcome()
  },
  { immediate: true },
)

interface NavItem {
  label: string
  to: string
  icon?: Component | null    // 可选: 不传 = 纯文字 (设置/个人中心 走这种)
}

const navItems: NavItem[] = [
  // 多种形式，方便之后切换 ──
  // { label: '带图标',  to: '/app/example', icon: IconHome },   // 前面会有蓝色徽章 + 图标
  // { label: '纯文字',  to: '/app/example' },                   // 前面不渲染图标位
  { label: '主 页', to: '/app/home', icon: IconHome },
  { label: '星 图', to: '/app/galaxy', icon: IconGalaxy },
  { label: '对 话', to: '/app/dialog', icon: IconDialog },
  { label: '计 划', to: '/app/plan', icon: IconPlan },
  { label: '书 架', to: '/app/book', icon: IconBook },
  { label: '视 频 课', to: '/app/video', icon: IconVideo },
  { label: '刷 题', to: '/app/exercise', icon: IconExercise },
  { label: '评 测', to: '/app/exam', icon: IconExam },
  // { label: '学 习 记 录', to: '/app/records', icon: IconRecords },  // 已并入 /app/home, 入口删除
  // { label: '个 人 中 心', to: '/app/profile' },     // 无图标 —— 纯文字
  // { label: '设 置', to: '/app/settings', icon: IconSettings },  // 隐藏设置入口
]

// ── 学科下拉 ──
const ownedSubjects = computed(() =>
  mySubjects.subjects.map((s) => ({
    code: s.name as SubjectCode,
    name: s.display_name || getSubjectDisplayName(s.name),
  })),
)

const currentSubjectName = computed(() =>
  getSubjectDisplayName(currentSubject.code),
)

const dropdownOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

function toggleDropdown(): void {
  dropdownOpen.value = !dropdownOpen.value
}

function pickSubject(code: SubjectCode): void {
  currentSubject.set(code)
  dropdownOpen.value = false
}

function goAddSubject(): void {
  dropdownOpen.value = false
  router.push('/app/plan/courses')
}

function onClickOutside(e: MouseEvent): void {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target as Node)) {
    dropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside, true)
  mySubjects.loadFromBackend()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside, true)
})

// 高亮判断 —— 精确匹配 OR 前缀匹配, 兼容有子路由的 nav 项 (e.g. /app/plan
//   下有 /app/plan/course/:code 和 /app/plan/course/:code/node/:nodeId,
//   在子路由里 "计划" 也应该保持高亮)
//
//   加 + '/' 是为了防 /app/plan-xxx 这种假想路径被误判为 /app/plan 的子路径.
function isActive(to: string): boolean {
  return route.path === to || route.path.startsWith(to + '/')
}

function goPublic(): void {
  router.push('/')
}
</script>

<template>
  <div class="x-shell">
    <header class="x-nav">
      <a class="x-nav-logo" @click="goPublic">
        <span class="x-nav-logo-icon"><BrandMark :size="30" /></span>
        <span class="x-nav-logo-text">学径</span>
      </a>

      <nav class="x-nav-links" aria-label="Primary">
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" class="x-nav-link"
          :class="{ 'is-active': isActive(item.to) }">
          <span v-if="item.icon" class="x-nav-glyph" :class="{ 'is-active': isActive(item.to) }">
            <component :is="item.icon" :size="22" />
          </span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="x-nav-right">
        <!-- 学科选择器 -->
        <div ref="dropdownRef" class="x-subject-dropdown">
          <button class="x-subject-trigger" @click.stop="toggleDropdown">
            <span class="x-subject-trigger-text">{{ currentSubjectName }}</span>
            <span class="x-subject-chevron" :class="{ open: dropdownOpen }">
              <svg width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7 10 L12 15 L17 10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </button>

          <transition name="x-drop">
            <div v-if="dropdownOpen" class="x-subject-panel">
              <div v-if="ownedSubjects.length === 0" class="x-subject-empty">
                暂无学科，请先添加
              </div>
              <button
                v-for="sub in ownedSubjects"
                :key="sub.code"
                class="x-subject-item"
                :class="{ 'is-active': sub.code === currentSubject.code }"
                @click="pickSubject(sub.code)"
              >
                <span class="x-subject-item-name">{{ sub.name }}</span>
                <span v-if="sub.code === currentSubject.code" class="x-subject-check">
                  <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M5 12.5 L10 17 L19 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </span>
              </button>
              <div class="x-subject-divider"></div>
              <button class="x-subject-add" @click="goAddSubject">
                <span class="x-subject-add-icon">
                  <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 5 V19 M5 12 H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                  </svg>
                </span>
                <span>添加学科</span>
              </button>
            </div>
          </transition>
        </div>

        <UserWidget />
      </div>
    </header>

    <main class="x-main">
      <!--
        router-view 包裹策略:
          - <keep-alive> 缓存已访问过的 view, 切回 (包括同 path 不同 query)
            不再 unmount/remount, view 自己用 route.query 响应式更新.
          - <transition> 不加 mode="out-in": 旧 view 离场 + 新 view 进场 并行,
            避免 transition 半挂 (前一个 view 出场卡住) 时新 view 永远不 mount
          - 不再 :key="$route.fullPath": 那个 key 会把 "同 path 不同 query"
            (例如 /app/home?tab=history → ?tab=exercises) 强制 remount,
            整个 view 闪一下 + 数据重新 fetch. 去掉之后 query 变化仅触发
            view 内部 computed 重算, 状态由 view 自己的 <keep-alive> 维护.
      -->
      <router-view v-slot="{ Component }">
        <keep-alive>
          <transition name="x-fade">
            <component :is="Component" />
          </transition>
        </keep-alive>
      </router-view>
    </main>

    <!-- 首次登录欢迎弹窗 —— AppShell 顶层挂载, 全 /app/* 路由共享 -->
    <WelcomeModal />
  </div>
</template>

<style scoped>
.x-shell {
  min-height: 100vh;
  background: var(--x-canvas);
  color: var(--x-ink);
  display: flex;
  flex-direction: column;
}

.x-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 68px;
  background: oklch(100% 0 0 / 0.78);
  backdrop-filter: blur(28px) saturate(180%);
  -webkit-backdrop-filter: blur(28px) saturate(180%);
  box-shadow:
    0 1px 0 oklch(20% 0.02 240 / 0.06),
    0 6px 24px oklch(20% 0.02 240 / 0.05);
  display: flex;
  align-items: center;
  padding: 0 32px;
  gap: 8px;
  transition: box-shadow 0.2s ease, background 0.2s ease;
}

/* Logo */
.x-nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 800;
  color: var(--x-ink);
  text-decoration: none;
  margin-right: 20px;
  flex-shrink: 0;
  letter-spacing: -0.01em;
}

.x-nav-logo:hover {
  text-decoration: none;
}

.x-nav-logo-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  color: var(--x-primary);
  flex-shrink: 0;
}

.x-nav-logo-text {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--x-ink);
}

/* Nav links */
.x-nav-links {
  display: flex;
  align-items: center;
  gap: 3px;
  flex: 1;
  list-style: none;
  overflow-x: auto;
  scrollbar-width: none;
}

.x-nav-links::-webkit-scrollbar {
  display: none;
}

.x-nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.x-nav-link:hover {
  background: var(--x-canvas-soft);
  color: var(--x-ink);
}

.x-nav-link.is-active {
  background: transparent;
  color: var(--x-primary);
  font-weight: 600;
}
.x-nav-link.is-active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  height: 3px;
  width: calc(100% - 28px);
  transform: translateX(-50%);
  background: var(--x-primary);
  border-radius: 2px;
}

.x-nav-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  color: var(--x-body-mid);
  transition: color 0.15s;
}

.x-nav-link:hover .x-nav-glyph {
  color: var(--x-ink);
}

.x-nav-glyph.is-active {
  color: var(--x-primary);
}

/* Right slot */
.x-nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
  flex-shrink: 0;
}

/* ── Subject Dropdown ─────────────────────────────────── */
.x-subject-dropdown {
  position: relative;
}

.x-subject-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: 8px;
  padding: 6px 10px 6px 14px;
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  font-family: inherit;
}

.x-subject-trigger:hover {
  border-color: var(--x-primary);
}

.x-subject-trigger-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.x-subject-chevron {
  font-size: 12px;
  color: var(--x-body-mid);
  transition: transform 0.2s;
  display: inline-block;
}

.x-subject-chevron.open {
  transform: rotate(180deg);
}

.x-subject-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 180px;
  max-height: 360px;
  overflow-y: auto;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10), 0 2px 6px rgba(15, 23, 42, 0.06);
  padding: 4px;
  z-index: 200;
}

.x-subject-empty {
  padding: 14px 12px;
  font-size: 13px;
  color: var(--x-body-mid);
  text-align: center;
}

.x-subject-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 9px 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--x-ink);
  cursor: pointer;
  transition: background 0.12s;
  text-align: left;
}

.x-subject-item:hover {
  background: var(--x-canvas-soft);
}

.x-subject-item.is-active {
  background: var(--x-primary-soft);
  color: var(--x-primary);
  font-weight: 600;
}

.x-subject-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.x-subject-check {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--x-primary);
  margin-left: 8px;
}

.x-subject-divider {
  height: 1px;
  background: var(--x-hairline);
  margin: 4px 8px;
}

.x-subject-add {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--x-primary);
  cursor: pointer;
  transition: background 0.12s;
}

.x-subject-add:hover {
  background: var(--x-primary-soft);
}

.x-subject-add-icon {
  font-size: 15px;
  font-weight: 700;
  line-height: 1;
}

/* dropdown animation */
.x-drop-enter-active,
.x-drop-leave-active {
  transition: opacity 0.14s, transform 0.14s;
}

.x-drop-enter-from,
.x-drop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── Main Content ────────────────────────────────────── */
.x-main {
  flex: 1;
  min-width: 0;
  background: var(--x-canvas);
}

/* ── Page Transition ────────────────────────────────── */
.x-fade-enter-active,
.x-fade-leave-active {
  transition: opacity 0.12s;
}

.x-fade-enter-from,
.x-fade-leave-to {
  opacity: 0;
}

/* ── Responsive ─────────────────────────────────────── */
@media (max-width: 768px) {
  .x-nav {
    padding: 0 16px;
    gap: 4px;
  }

  .x-nav-logo-text {
    display: none;
  }

  .x-nav-link {
    padding: 6px 8px;
    font-size: 12px;
  }
}
</style>
