<template id="app">
  <router-view></router-view>
</template>

<script setup lang="ts" name="App">
/**
 * App.vue —— 根组件
 *
 * 启动时根据登录态 + 课程状态决定初始跳转:
 *   - 未登录 → /login (路由守卫处理)
 *   - 已登录 + 无课程 → /onboarding (走 onboarding 三步流程)
 *   - 已登录 + 有课程 → /app/home (主应用)
 *
 * 实现: 不在 App.vue 主动跳转 (避免与路由守卫竞态),
 *       改由路由守卫在每次跳转前统一判断, 见 router/index.ts:215-237
 *
 * 这里只挂一个全局错误兜底 handler (主入口 main.ts 已经设置过,
 * 这里加一个 component-level 兜底双保险)
 */

import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(() => {
  // 仅做防御性 hydration: token / user 应该已在持久化插件里恢复
  if (!userStore.isAuthenticated) {
    // 没 token → 不主动跳, 让守卫把 /welcome 等要求 auth 的路由导去 /login
    return
  }
})
</script>

<style scoped>
</style>