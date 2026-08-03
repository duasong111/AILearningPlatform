<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { IconChevron, IconArrow, IconHome } from '@/components/icons'
import defaultAvatar from '@/assets/avatar.jpg'

/**
 * 用户气泡 —— 已登录时显示头像+名字, 点击展开下拉菜单
 *   - 没有 props / emit, 自己读 useUserStore + useRouter
 *   - 点击外部自动收起 (mousedown 监听, 比 click 早一帧)
 *   - 登出: 清 userStore (持久化插件级联清 localStorage), 跳 /login
 *
 * AppShell 的 header 和 HomeView 的 nav 都引用同一份, 行为完全一致.
 */

const router = useRouter()
const userStore = useUserStore()
const mySubjectsStore = useMySubjectsStore()

const open = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const toggle = (): void => {
  open.value = !open.value
}

const handleLogout = (): void => {
  userStore.logout()
  // 登出时清掉本地课程, 避免下一个登录的用户在同设备上看到上一位的课程
  mySubjectsStore.reset()
  open.value = false
  ElMessage({ message: '→ Signed out', customClass: 'x-toast' })
  router.push('/login')
}

// 已登录用户从任意页面回首页 —— 跟 logo 点击一致, 但入口更明确
const handleGoHome = (): void => {
  open.value = false
  router.push({ name: 'home' })
}

// 点击 widget 外部 → 收起菜单. mousedown 比 click 早一帧, 避免和菜单内 item 抢事件.
const onDocMouseDown = (e: MouseEvent): void => {
  if (!open.value) return
  const root = rootRef.value
  if (root && !root.contains(e.target as Node)) {
    open.value = false
  }
}
onMounted(() => {
  document.addEventListener('mousedown', onDocMouseDown)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocMouseDown)
})
</script>

<template>
  <div ref="rootRef" class="x-user">
    <button
      type="button"
      class="x-user-trigger"
      :class="{ 'is-open': open }"
      @click="toggle"
      :aria-expanded="open"
      aria-haspopup="menu"
    >
      <span class="x-user-avatar">
        <img
          v-if="userStore.user?.avatar"
          :src="userStore.user.avatar"
          :alt="userStore.displayName"
        />
        <img v-else :src="defaultAvatar" :alt="userStore.displayName" />
      </span>
      <span class="x-user-name">{{ userStore.displayName }}</span>
      <span class="x-user-chevron" :class="{ 'is-open': open }" style="display:inline-flex;align-items:center"><IconChevron :size="10" /></span>
    </button>

    <transition name="x-fade-pop">
      <div v-if="open" class="x-user-menu" role="menu">
        <div class="x-user-menu-head">
          <p class="x-user-menu-name">{{ userStore.displayName }}</p>
          <p class="x-user-menu-email">{{ userStore.user?.email }}</p>
        </div>
        <hr class="x-user-menu-sep" />
        <button
          type="button"
          class="x-user-menu-item"
          role="menuitem"
          @click="handleGoHome"
        >
          <span class="x-user-menu-label">
            <span class="x-user-menu-leading" style="display:inline-flex;align-items:center"><IconHome :size="13" /></span>
            <span>主页 Home</span>
          </span>
        </button>
        <button
          type="button"
          class="x-user-menu-item is-danger"
          role="menuitem"
          @click="handleLogout"
        >
          <span class="x-user-menu-label">
            <span>Sign out</span>
            <span class="x-user-menu-trailing" style="display:inline-flex;align-items:center"><IconArrow :size="12" /></span>
          </span>
        </button>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.x-user {
  position: relative;
}

.x-user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--x-canvas-soft);
  color: var(--x-ink);
  border: 0;
  border-radius: var(--x-rounded-pill);
  padding: 4px 12px 4px 4px;
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 13px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: background 0.18s, box-shadow 0.18s;
}
.x-user-trigger:hover,
.x-user-trigger.is-open {
  background: var(--x-canvas-mid);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}

.x-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--x-primary);
  color: var(--x-on-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.x-user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.x-user-avatar-fallback {
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

.x-user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.x-user-chevron {
  font-size: 10px;
  color: var(--x-body-mid);
  transition: transform 0.15s;
}
.x-user-chevron.is-open {
  transform: rotate(180deg);
}

/* dropdown panel —— 平面高级感: 无边框, 大圆角, 多层柔阴影 */
.x-user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: var(--x-canvas);
  border: 0;
  border-radius: var(--x-rounded-md);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05),
              0 12px 32px rgba(15, 23, 42, 0.12);
  z-index: 100;
  overflow: hidden;
}
.x-user-menu-head {
  padding: 12px 14px 10px;
}
.x-user-menu-name {
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0;
}
.x-user-menu-email {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.4px;
  color: var(--x-body-mid);
  margin: 4px 0 0;
  word-break: break-all;
}
/* 菜单内分隔条 —— 用纯间距替代 hairline, 保留 HR 语义 */
.x-user-menu-sep {
  border: 0;
  margin: 6px 0;
  height: 0;
}
.x-user-menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 9px 14px;
  background: transparent;
  border: 0;
  color: var(--x-ink);
  font-family: var(--x-font-display);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s, color 0.12s;
}
.x-user-menu-item:hover {
  background: var(--x-canvas-soft);
}
.x-user-menu-item.is-danger:hover {
  color: var(--x-error);
}
/* 菜单项行内排版: 主文字 + 可选 leading / trailing glyph */
.x-user-menu-label {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.x-user-menu-leading {
  color: var(--x-body-mid);
  flex-shrink: 0;
}
.x-user-menu-trailing {
  color: var(--x-body-mid);
  margin-left: auto;
  flex-shrink: 0;
}
.x-user-menu-item:hover .x-user-menu-leading,
.x-user-menu-item:hover .x-user-menu-trailing {
  color: var(--x-primary);
}
.x-user-menu-item.is-danger:hover .x-user-menu-trailing {
  color: var(--x-error);
}

/* enter/leave animation for dropdown */
.x-fade-pop-enter-active,
.x-fade-pop-leave-active {
  transition: opacity 0.15s, transform 0.15s;
}
.x-fade-pop-enter-from,
.x-fade-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .x-user-chevron,
  .x-fade-pop-enter-active,
  .x-fade-pop-leave-active {
    transition: none;
  }
}
</style>
