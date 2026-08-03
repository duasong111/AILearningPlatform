import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as subjectsApi from '@/api/subjects'
import { getProfile, completeProfile } from '@/api/profile'
import type { UserProfile } from '@/types/response'

/**
 * 欢迎弹窗触发模式 (SettingsView 里可配)
 *   - always: 每次登录成功后都弹 (默认)
 *   - first : 仅首次登录弹一次, 之后关掉就再不来
 *   - never : 永不弹 (用户主动关)
 */
export type WelcomeMode = 'always' | 'first' | 'never'

/**
 * Onboarding 状态 store
 *
 * 设计目标:
 *   - 登录后强制走一次 onboarding（无课程 → 必走，有课程 → 跳过）
 *   - 加课 → 自动跳 /onboarding 完成该课程的画像构建（per-subject）
 *   - 用 is_complete 字段判断画像是否完成（后端 UserProfileSerializer.get_is_complete）
 *
 * 状态机:
 *   idle ── load() ──→ loading
 *   loading ── ok ──→ ready(has_subjects, subjects)
 *
 * 不持久化：每次 App.vue onMounted 都重新拉一次，避免缓存导致跳转错误。
 *
 * 例外: 用户在 /course-select 点过 "稍后再选" → skipped = true
 *   → 路由守卫不再强制跳 course-select, 允许用户自由探索主界面.
 *   → 只持久化 skipped 这一个布尔, 其他状态继续不缓存.
 */
export const useOnboardingStore = defineStore(
  'onboarding',
  () => {
    // ─── state ────────────────────────────────────────────
    const loading = ref<boolean>(false)
    const lastError = ref<string>('')
    /** subject_code → profile.is_complete 映射（按需缓存） */
    const profileCompleteMap = ref<Record<string, boolean>>({})
    /**
     * 用户在 /course-select 主动选了"稍后再选 / Skip"
     * true = 跳过 onboarding 强制流程, 不再被守卫拦到 course-select
     */
    const skipped = ref<boolean>(false)
    /**
     * 欢迎弹窗开关 —— AppShell 判定条件后自动设为 true, 弹窗浮现.
     * 用户点 "去选课" / "先逛逛" / 关闭按钮 后关掉.
     */
    const welcomeOpen = ref<boolean>(false)
    /**
     * 触发模式: 决定何时弹. 持久化, 用户在 SettingsView 里改.
     * 默认 'first' —— 仅首次登录弹一次（新注册用户），符合用户预期
     */
    const welcomeMode = ref<WelcomeMode>('first')
    /**
     * 仅 'first' 模式用 —— 用户见过一次后置 true, 后续不再弹.
     * 跟 welcomeMode 分开, 这样切到 'always' 再切回 'first' 仍能从 'first' 状态继续.
     */
    const welcomeShown = ref<boolean>(false)

    // ─── getters ──────────────────────────────────────────
    const isLoading = computed(() => loading.value)

    function isProfileComplete(subjectCode: string): boolean {
      return profileCompleteMap.value[subjectCode] === true
    }

    // ─── actions ──────────────────────────────────────────
    /** 拉取并缓存某 subject 的画像完整度 */
    async function checkProfileComplete(subjectCode: string): Promise<boolean> {
      try {
        const { data } = await getProfile(subjectCode)
        profileCompleteMap.value[subjectCode] = !!data.is_complete
        return !!data.is_complete
      } catch (err) {
        profileCompleteMap.value[subjectCode] = false
        lastError.value = err instanceof Error ? err.message : 'profile check failed'
        return false
      }
    }

    /**
     * 引导决策: 登录后应该跳到哪？
     *   - 拉取 mySubjects
     *   - 若 0 门课 → 'onboarding' (强制走 onboarding)
     *   - 若 ≥1 门课 → 'home'    (进入主页)
     */
    async function decideEntryRoute(): Promise<'onboarding' | 'home'> {
      loading.value = true
      lastError.value = ''
      try {
        const { data } = await subjectsApi.listMySubjects()
        return data.length === 0 ? 'onboarding' : 'home'
      } catch (err) {
        lastError.value = err instanceof Error ? err.message : 'load failed'
        // 拉取失败保守按 onboarding 处理（让用户至少能进系统再排查）
        return 'onboarding'
      } finally {
        loading.value = false
      }
    }

    /**
     * 对单门课程判定: 用户是否可以进入其学习流程
     *   - 课程不存在 → false
     *   - 课程存在但画像未完整 → false（提示走 onboarding）
     *   - 课程存在 + 画像完整 → true
     */
    async function canEnterSubject(subjectCode: string): Promise<boolean> {
      return await checkProfileComplete(subjectCode)
    }

    /** 在 onboarding 完成时调用，刷新缓存并通知上游 */
    async function markOnboarded(subjectCode: string): Promise<void> {
      profileCompleteMap.value[subjectCode] = true
      try {
        await completeProfile(subjectCode)
      } catch {
        // 静默失败，本地缓存已更新
      }
    }

    /**
     * 用户主动跳过 onboarding —— 路由守卫看到这个标志就放行,
     * 让用户先探索主界面, 之后从 "我的课程" 主动加课即可.
     */
    function skipOnboarding(): void {
      skipped.value = true
    }

    /**
     * 反悔 / 重新引导 —— 用户加过课后想重新走选课流程时用.
     * 主要给 "个人中心 / 设置" 提供 "重新选课" 入口预留.
     */
    function unskipOnboarding(): void {
      skipped.value = false
    }

    /** 打开欢迎弹窗 */
    function openWelcome(): void {
      welcomeOpen.value = true
    }

    /**
     * 关闭欢迎弹窗 + 标记已见过 (供 'first' 模式用)
     * 不管用户点 "去选课" 还是 "先逛逛" 还是 X / ESC,
     * 一旦弹窗被消费过, 在 'first' 模式下后续就不再出现.
     */
    function closeWelcome(): void {
      welcomeOpen.value = false
      welcomeShown.value = true
    }

    /** 设置触发模式 (供 SettingsView 调用) */
    function setWelcomeMode(mode: WelcomeMode): void {
      welcomeMode.value = mode
      // 切到 'first' 且之前已见过 → 不重置, 保持已见
      // 切到 'always' → 下次登录必弹 (跟 welcomeShown 无关)
      // 切到 'never' → 关掉当前打开的弹窗, 以后也不弹
      if (mode === 'never') welcomeOpen.value = false
    }

    return {
      loading,
      lastError,
      profileCompleteMap,
      skipped,
      welcomeOpen,
      welcomeMode,
      welcomeShown,
      isLoading,
      isProfileComplete,
      checkProfileComplete,
      decideEntryRoute,
      canEnterSubject,
      markOnboarded,
      skipOnboarding,
      unskipOnboarding,
      openWelcome,
      closeWelcome,
      setWelcomeMode,
    }
  },
  {
    persist: {
      // 持久化跳过标志 + 欢迎弹窗模式/已见标记.
      // localStorage key: 'aiteach.onboarding'
      pick: ['skipped', 'welcomeMode', 'welcomeShown'],
    },
  },
)