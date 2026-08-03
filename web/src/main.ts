import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import PrimeVue from 'primevue/config'

// AI 聊天 markdown 渲染依赖:
//   - KaTeX 公式字体 (markdown-it-texmath 用)
//   - highlight.js github-dark 配 .x-md :deep(pre) 的暗背景
import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github-dark.css'

import App from './App.vue'
import router from './router'
import '@/assets/main.css'

// 单一 Pinia 实例 + 持久化插件
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

// ============================================================
// 首屏前应用持久化主题 — 否则用户访问 / (HomeView, 不引 useSettingsStore)
// 时主题永远是默认 light, 哪怕 localStorage 里存了 dark. 这里提前同步到 <html>,
// 这样 Vue 挂载前 CSS 已经能匹配 html[data-theme='dark'] 选择器.
// ============================================================
;(function applyPersistedThemeEarly(): void {
  try {
    const raw = localStorage.getItem('aiteach.settings')
    if (!raw) return
    const parsed = JSON.parse(raw) as { theme?: 'light' | 'dark' | 'auto' }
    const t = parsed.theme
    if (t === 'light' || t === 'dark') {
      document.documentElement.setAttribute('data-theme', t)
    } else if (t === 'auto') {
      // auto: 把字面值先写上, 真深浅由 main.css 的 prefers-color-scheme 媒体查询接管
      document.documentElement.setAttribute('data-theme', 'auto')
    }
  } catch {
    /* localStorage 不可用 / 解析失败 — 忽略, 让 store 后续补救 */
  }
})()

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(ElementPlus)
app.use(PrimeVue)

// ============================================================
// 全局错误兜底 —— 防某个 view 挂载抛错把整个 main 区域卡死
//
//   之前症状: 切到某个路由, 该 view 在 mount 阶段抛错 (例如 chunk 加载失败,
//   composable 内部 throw, 模板 v-if 条件错误), Vue 默认 ErrorHandler 只
//   console.error 然后不挂载. 配合 <transition mode="out-in">, transition 进入
//   状态永久卡住, 后续所有 navigation 都不再触发新 view mount, 整个 main 区域
//   一直白屏, 只有顶部 nav 还活着.
//
//   这个 handler 兜住错误:
//     1. 打印详细错误到 console (含路由信息)
//     2. 调用 router.replace 跳到 /app/home (已知能正常 mount 的入口)
//     3. 用 ElMessage 弹一条 toast 告诉用户发生了什么
// ============================================================
router.onError((err, to) => {
  // eslint-disable-next-line no-console
  console.error('[router] navigation error', {
    to: to.fullPath,
    name: to.name,
    err,
  })
  // 异步 import 失败 / component 抛错 -> 跳回主页保命
  if (to.path.startsWith('/app')) {
    router.replace('/app/home').catch(() => { /* swallow */ })
  }
})

// 兜底: 任何 view 在 setup / render 阶段抛错 (如 v-if 引用 undefined)
// 也会被这个 hook 接住, 走同样的"跳回主页 + toast"逻辑
app.config.errorHandler = (err, instance, info) => {
  // eslint-disable-next-line no-console
  console.error('[vue] component error', { err, info, instance })
  // 只对 /app/* 下的 view 错误自动恢复, 不影响 /login / /register 流程
  if (router.currentRoute.value.path.startsWith('/app')) {
    router.replace('/app/home').catch(() => { /* swallow */ })
  }
}

app.mount('#app')
