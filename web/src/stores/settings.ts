import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

/**
 * 用户设置 store —— 持久化到 localStorage, 跨刷新保留
 *
 *   - theme: 'light' (dark 暂未实现, UI 标"敬请期待"防误操作)
 *   - fontScale: 'sm' | 'md' | 'lg', 透过 document.documentElement[data-fs] 切换根级 CSS 钩子
 *   - defaultAgent: 'chat' | 'profile' | 'practice', TutorView / PracticeView 创建新会话时默认用
 *   - responseStyle: 'concise' | 'balanced' | 'detailed', 渲染到 system 提示
 *   - dailyGoalMinutes / streakGoalDays: 学习节奏目标 (SettingsView 段 4)
 *   - notifications.{newQuiz, quizResult, tutorReply}: 三类事件通知开关 (段 5)
 *   - privacy: { showOnline, shareAnalytics, clearLocalCache() }
 *
 *   切换时透过 watch 同步到 <html> 的 data-attrs, CSS 用 [data-fs="lg"] 之类的选择器
 *   真正的主题样式后续接; 现在 UI 看起来"没变化"是预期的 (theme 只持久化, 不动 CSS)
 */

export type FontScale = 'sm' | 'md' | 'lg'
export type ThemeMode = 'light' | 'dark' | 'auto'
export type DefaultAgent = 'chat' | 'profile' | 'practice'
export type ResponseStyle = 'concise' | 'balanced' | 'detailed'

export interface PrivacySettings {
  showOnline: boolean
  shareAnalytics: boolean
}

export interface NotifSettings {
  newQuiz: boolean         // 每周有新的"学科测验"被推荐时提醒
  quizResult: boolean      // 提交的题判分完时弹通知
  tutorReply: boolean      // AI 助教回复时弹通知
}

export const useSettingsStore = defineStore(
  'settings',
  () => {
    const theme = ref<ThemeMode>('light')
    const fontScale = ref<FontScale>('md')
    const defaultAgent = ref<DefaultAgent>('chat')
    const responseStyle = ref<ResponseStyle>('balanced')
    const privacy = ref<PrivacySettings>({
      showOnline: true,
      shareAnalytics: false,
    })
    // 学习节奏 (SettingsView 段 4)
    const dailyGoalMinutes = ref<number>(60)        // 每日学习时长目标 (15/30/60/90/120)
    const streakGoalDays = ref<number>(30)          // 连续打卡目标 (7/30/100)
    // 通知 (SettingsView 段 5)
    const notifications = ref<NotifSettings>({
      newQuiz: true,
      quizResult: true,
      tutorReply: false,
    })

    // ─── 同步到 <html> data-attrs (CSS 钩子) ─────────────────────
    function applyToDOM(): void {
      if (typeof document === 'undefined') return
      const root = document.documentElement
      root.setAttribute('data-fs', fontScale.value)
      // theme: 当前只持久化, 不动 CSS (dark 模式等下个迭代)
      root.setAttribute('data-theme', theme.value)
    }

    watch(
      [theme, fontScale],
      () => applyToDOM(),
      { immediate: true },
    )

    // ─── 工具 ─────────────────────────────────────────────
    function setFontScale(s: FontScale): void { fontScale.value = s }
    function setTheme(t: ThemeMode): void { theme.value = t }
    function setDefaultAgent(a: DefaultAgent): void { defaultAgent.value = a }
    function setResponseStyle(s: ResponseStyle): void { responseStyle.value = s }
    function setShowOnline(v: boolean): void { privacy.value.showOnline = v }
    function setShareAnalytics(v: boolean): void { privacy.value.shareAnalytics = v }
    function setDailyGoalMinutes(n: number): void {
      // 限定在 5 档合法档位上, 避免外部乱传
      const ok = [15, 30, 60, 90, 120]
      dailyGoalMinutes.value = ok.includes(n) ? n : 60
    }
    function setStreakGoalDays(n: number): void {
      const ok = [7, 30, 100]
      streakGoalDays.value = ok.includes(n) ? n : 30
    }
    function setNotification<K extends keyof NotifSettings>(
      k: K,
      v: boolean,
    ): void {
      notifications.value = { ...notifications.value, [k]: v }
    }

    /**
     * 清空本地缓存 —— 删掉所有 aiteach.* 的 localStorage key + 登出
     *   不删 aiteach.mastery (那是用户学习进度的兜底); 只删 user/subjects/conv cache 等
     */
    function clearLocalCache(): void {
      if (typeof localStorage === 'undefined') return
      const keys: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i)
        if (k && k.startsWith('aiteach.')) keys.push(k)
      }
      for (const k of keys) localStorage.removeItem(k)
    }

    function resetAll(): void {
      theme.value = 'light'
      fontScale.value = 'md'
      defaultAgent.value = 'chat'
      responseStyle.value = 'balanced'
      privacy.value = { showOnline: true, shareAnalytics: false }
      dailyGoalMinutes.value = 60
      streakGoalDays.value = 30
      notifications.value = { newQuiz: true, quizResult: true, tutorReply: false }
    }

    return {
      theme, fontScale, defaultAgent, responseStyle, privacy,
      dailyGoalMinutes, streakGoalDays, notifications,
      setFontScale, setTheme, setDefaultAgent, setResponseStyle,
      setShowOnline, setShareAnalytics,
      setDailyGoalMinutes, setStreakGoalDays, setNotification,
      clearLocalCache, resetAll,
    }
  },
  {
    persist: {
      key: 'aiteach.settings',
      pick: [
        'theme', 'fontScale', 'defaultAgent', 'responseStyle', 'privacy',
        'dailyGoalMinutes', 'streakGoalDays', 'notifications',
      ],
    },
  },
)
