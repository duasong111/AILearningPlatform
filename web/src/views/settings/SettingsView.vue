<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { AxiosError } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useMySubjectsStore } from '@/stores/mySubjects'
import {
  useSettingsStore,
  type DefaultAgent,
  type FontScale,
  type ResponseStyle,
  type ThemeMode,
} from '@/stores/settings'
import { IconGuard, IconArrow } from '@/components/icons'
import { useOnboardingStore, type WelcomeMode } from '@/stores/onboarding'
import { getProfile, updateProfile } from '@/api/profile'
import { getSubjectDisplayName } from '@/api/subjects'
import type { UserProfile } from '@/types/response'
import type { SubjectCode } from '@/types/learning'

/**
 * 设置 (页) —— 跟其它内部页同源设计 (x-* 令牌, 卡片 + 分区块)
 *
 *   区块:
 *     1. 外观        主题 / 字号
 *     2. AI 行为     默认 agent / 响应风格
 *     3. 隐私        在线可见 / 数据共享 / 清空本地缓存
 *     4. 学习节奏    每日时长目标 / 连续打卡目标
 *     5. 通知        出题 / 判分 / AI 回复 三类提醒开关
 *     6. 数据导出    一键下载我的学习数据 (本地 JSON 快照)
 *     7. 高级 (reset) 恢复所有默认
 *
 *   主题: 当前只有 light 真生效, dark 标 "敬请期待" 防误操作
 *   字号: 同步到 <html data-fs="sm|md|lg">, CSS 里设 root font-size
 *   agent: 持久化, 给 TutorView / PracticeView 默认选这个
 *   响应风格: 持久化, 未来发给后端当 system prompt 前缀
 *   学习节奏 / 通知: 持久化, UI 实时生效 (后端接口未到前, 不影响)
 *   数据导出: 客户端拼 JSON 触发下载, 走隐私设置里"自己数据可携带"的设计意图
 */

const settings = useSettingsStore()
const userStore = useUserStore()
const mySubjects = useMySubjectsStore()

// 三个"区段选择"控件, 给一组互斥按钮组用
const AGENT_OPTIONS: { value: DefaultAgent; label: string; hint: string }[] = [
  { value: 'chat',     label: 'AI 助教',  hint: '自由聊天 / 闲谈' },
  { value: 'profile',  label: '画像',     hint: '构建学习画像 (LangChain profile agent)' },
  { value: 'practice', label: '出题',     hint: '出题 / 答 / 判分' },
]

const FONT_OPTIONS: { value: FontScale; label: string; px: number }[] = [
  { value: 'sm', label: '小', px: 14.7 },
  { value: 'md', label: '中', px: 16.0 },
  { value: 'lg', label: '大', px: 17.6 },
]

const RESPONSE_OPTIONS: { value: ResponseStyle; label: string; hint: string }[] = [
  { value: 'concise',  label: '简洁',  hint: '回复简短, 重点突出' },
  { value: 'balanced', label: '平衡',  hint: '回复完整, 详略适中' },
  { value: 'detailed', label: '详细',  hint: '回复详尽, 包含推导' },
]

const THEME_OPTIONS: { value: ThemeMode; label: string; available: boolean }[] = [
  { value: 'light', label: 'Light',   available: true },
  { value: 'dark',  label: 'Dark',    available: true },
  { value: 'auto',  label: 'Auto',    available: true },      // 跟随系统 (prefers-color-scheme)
]

// 学习节奏 (段 4) —— 5 档每日时长 / 3 档连续打卡
const DAILY_GOAL_OPTIONS: { value: number; label: string }[] = [
  { value: 15,  label: '15 分钟' },
  { value: 30,  label: '30 分钟' },
  { value: 60,  label: '1 小时' },
  { value: 90,  label: '1.5 小时' },
  { value: 120, label: '2 小时' },
]
const STREAK_GOAL_OPTIONS: { value: number; label: string }[] = [
  { value: 7,   label: '7 天' },
  { value: 30,  label: '30 天' },
  { value: 100, label: '100 天' },
]

// 欢迎弹窗触发模式 —— 控制登录后首次引导弹窗何时出现, 默认 'always'
const onboarding = useOnboardingStore()
const WELCOME_MODE_OPTIONS: { value: WelcomeMode; label: string; hint: string }[] = [
  { value: 'always', label: '每次',   hint: '每次登录后都弹 (默认)' },
  { value: 'first',  label: '仅首次', hint: '只在第一次登录后弹一次' },
  { value: 'never',  label: '永不',   hint: '不再弹出欢迎弹窗' },
]

// 通知 (段 5) —— 三类事件开关
const NOTIF_OPTIONS: Array<{
  key: 'newQuiz' | 'quizResult' | 'tutorReply'
  label: string
  hint: string
}> = [
  { key: 'newQuiz',    label: '新出题提醒',  hint: '系统推荐新学科评测时通知' },
  { key: 'quizResult', label: '判分完成',     hint: '提交的题解析生成后弹窗' },
  { key: 'tutorReply', label: 'AI 助教回复',   hint: '会话有新回复时通知 (常驻后台时尤其有用)' },
]

// 清空本地缓存 (二次确认防误点)
async function handleClearCache(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确定要清空本地缓存吗?\n\n将清掉:\n  - 登录态 (token / user)\n  - 学科列表\n  - 练习数据\n  - 各种偏好\n  - **但** 不动后端, 重新登录会再拉',
      '清空本地缓存',
      {
        confirmButtonText: '清空',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return  // 取消
  }
  settings.clearLocalCache()
  ElMessage({ message: '→ 本地缓存已清空, 请重新登录', customClass: 'x-toast', duration: 4000 })
  // 强制跳登录
  setTimeout(() => { window.location.href = '/login' }, 800)
}

function handleResetAll(): void {
  ElMessageBox.confirm('恢复所有设置为默认值?', '重置', {
    confirmButtonText: '重置',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      settings.resetAll()
      ElMessage({ message: '→ 已恢复默认', customClass: 'x-toast' })
    })
    .catch(() => { /* 取消 */ })
}

function pickTheme(t: ThemeMode): void {
  if (!THEME_OPTIONS.find((o) => o.value === t)?.available) {
    ElMessage({ message: '→ 该主题暂未上线, 敬请期待', customClass: 'x-toast' })
    return
  }
  settings.setTheme(t)
  // Auto: 跟随系统. store 只存字面值 'auto', 由 main.css 的 prefers-color-scheme 媒体查询接管.
  // 这里强制把 'auto' 反映到 data-theme (取当前实际生效的 mode) 以保证 UI 反馈一致.
  if (t === 'auto') {
    const mql = window.matchMedia('(prefers-color-scheme: dark)')
    document.documentElement.setAttribute('data-theme', mql.matches ? 'dark' : 'light')
  }
}

// ─── 学习画像 (per-subject) ───────────────────────────────
const selectedSubject = ref<SubjectCode | ''>(
  (mySubjects.subjects[0]?.name as SubjectCode | undefined) ?? '',
)

interface LPDraft {
  course: string
  knowledge_base: number
  cognitive_style: number
  learning_goal_score: number
  available_time: number
  common_mistakes: string
  interest_direction: string
}
function emptyLP(): LPDraft {
  return { course: '', knowledge_base: 0, cognitive_style: 0, learning_goal_score: 0, available_time: 0, common_mistakes: '', interest_direction: '' }
}
function lpFromServer(p: UserProfile): LPDraft {
  return {
    course: p.course ?? '',
    knowledge_base: p.knowledge_base,
    cognitive_style: p.cognitive_style,
    learning_goal_score: p.learning_goal_score,
    available_time: p.available_time,
    common_mistakes: (p.common_mistakes ?? []).join(', '),
    interest_direction: (p.interest_direction ?? []).join(', '),
  }
}

const lpServer = ref<UserProfile | null>(null)
const lpDraft = reactive<LPDraft>(emptyLP())
const lpLoading = ref(false)
const lpSaving = ref(false)
const lpError = ref('')

async function loadLP(): Promise<void> {
  if (!selectedSubject.value) { lpServer.value = null; Object.assign(lpDraft, emptyLP()); return }
  lpLoading.value = true; lpError.value = ''
  try {
    const { data } = await getProfile(selectedSubject.value)
    lpServer.value = data; Object.assign(lpDraft, lpFromServer(data))
  } catch (err) {
    if (err instanceof AxiosError && err.response?.status === 404) lpError.value = '该学科还没有画像数据'
    else lpError.value = err instanceof Error ? err.message : 'Load failed'
    lpServer.value = null; Object.assign(lpDraft, emptyLP())
  } finally { lpLoading.value = false }
}
watch(selectedSubject, loadLP, { immediate: true })

const lpIsDirty = computed(() => {
  if (!lpServer.value) return false
  const saved = lpFromServer(lpServer.value)
  return (Object.keys(saved) as (keyof LPDraft)[]).some(k => saved[k] !== lpDraft[k])
})
function lpReset(): void { if (lpServer.value) Object.assign(lpDraft, lpFromServer(lpServer.value)) }
function clampScore(n: number): number { return Math.max(0, Math.min(100, Math.round(n))) }
function parseTags(s: string): string[] { return s.split(',').map(t => t.trim()).filter(Boolean) }

async function lpSave(): Promise<void> {
  if (!selectedSubject.value || lpSaving.value) return
  lpSaving.value = true
  try {
    const payload: Partial<UserProfile> = {
      course: lpDraft.course.trim() || null,
      knowledge_base: clampScore(lpDraft.knowledge_base),
      cognitive_style: clampScore(lpDraft.cognitive_style),
      learning_goal_score: clampScore(lpDraft.learning_goal_score),
      available_time: clampScore(lpDraft.available_time),
      common_mistakes: parseTags(lpDraft.common_mistakes),
      interest_direction: parseTags(lpDraft.interest_direction),
    }
    const { data } = await updateProfile(selectedSubject.value, payload)
    lpServer.value = data; Object.assign(lpDraft, lpFromServer(data))
    ElMessage({ message: '→ 学习画像已保存', customClass: 'x-toast' })
  } catch (err) {
    ElMessage({ message: `× ${err instanceof Error ? err.message : 'Save failed'}`, customClass: 'x-toast' })
  } finally { lpSaving.value = false }
}

function scoreLabel(n: number): string {
  if (n >= 80) return '高'; if (n >= 50) return '中'; if (n >= 20) return '低'; return '未评估'
}

// ─── 我的学科 (compact) ───────────────────────────────────
const subjectCards = computed(() =>
  mySubjects.subjects.map(s => ({
    id: s.id, name: s.name, display_name: s.display_name,
    joinedAt: s.created_at,
    hasLP: lpServer.value?.subject?.id === s.id,
  })),
)

// ─── 学习统计 (compact) ───────────────────────────────────
const lpMistakeChips = computed<string[]>(() => parseTags(lpDraft.common_mistakes))
const lpInterestChips = computed<string[]>(() => parseTags(lpDraft.interest_direction))

const profileStats = computed(() => {
  const subjectCount = mySubjects.subjects.length
  const scores: Array<[string, number]> = [
    ['知识基础', lpServer.value?.knowledge_base ?? 0],
    ['认知风格', lpServer.value?.cognitive_style ?? 0],
    ['目标明确度', lpServer.value?.learning_goal_score ?? 0],
    ['可用时间', lpServer.value?.available_time ?? 0],
  ]
  const hasLP = lpServer.value !== null
  const lpProgressLabel = hasLP ? scores.reduce<[string, number]>((a, b) => (b[1] > a[1] ? b : a), ['', 0])[0] || '—' : '—'
  return [
    { label: '已选学科', value: String(subjectCount), hint: '来自 我的课程 列表' },
    { label: '画像进度', value: hasLP ? lpProgressLabel : '—', hint: hasLP ? '当前 LP 4 维最高项' : '请先保存画像' },
    { label: '易错点', value: String(lpMistakeChips.value.length), hint: 'LP 里标记的常见错点' },
    { label: '兴趣方向', value: String(lpInterestChips.value.length), hint: 'LP 里填的兴趣关键词' },
  ]
})

// 段 6: 数据导出 —— 拼装一份用户当前快照, 客户端触发下载
//   内容: user (脱敏: 不含 access/refresh) + 学科列表 + 全部设置
//   ⚠ 这是"本地数据可携带"演示, 不依赖后端 export endpoint
function handleExportData(): void {
  const snapshot = {
    exportedAt: new Date().toISOString(),
    appVersion: '0.1.0-alpha',
    user: userStore.user
      ? {
          id:        userStore.user.id,
          email:     userStore.user.email,
          username:  userStore.user.username,
          real_name: userStore.user.real_name,
          occupation: userStore.user.occupation,
          city: userStore.user.city,
          bio: userStore.user.bio,
          learning_goal: userStore.user.learning_goal,
          interest_tags: userStore.user.interest_tags,
        }
      : null,
    subjects: mySubjects.subjects.map((s) => ({
      id: s.id,
      name: s.name,
      display_name: s.display_name,
      created_at: s.created_at,
    })),
    settings: {
      theme:              settings.theme,
      fontScale:          settings.fontScale,
      defaultAgent:       settings.defaultAgent,
      responseStyle:      settings.responseStyle,
      dailyGoalMinutes:   settings.dailyGoalMinutes,
      streakGoalDays:     settings.streakGoalDays,
      notifications:      settings.notifications,
      privacy:            settings.privacy,
    },
  }
  const json = JSON.stringify(snapshot, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `xuejing-export-${Date.now()}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage({
    message: '→ 已下载 (本地快照, 未上传服务器)',
    customClass: 'x-toast',
  })
}
</script>

<template>
  <div class="x-set">
    <!-- 未登录守卫 —— settings 持久化到 localStorage 理论上跨刷新保留,
         但极端 race (持久化插件 hydration 还没完成就渲染) 时 v-model 绑定异常.
         防御: user==null 时给一个明确提示而不是看到一堆占位 -->
    <div v-if="!userStore.user" class="x-guard">
      <p class="x-guard-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-body-mid)"><IconGuard :size="40" /></p>
      <p class="x-guard-title">未登录</p>
      <p class="x-guard-hint">登录后查看设置。</p>
      <router-link to="/login" class="x-btn x-btn-primary"><span style="display:inline-flex;align-items:center;gap:6px">去登录 <IconArrow :size="12" /></span></router-link>
    </div>
    <header class="x-set-head">
      <p class="x-eyebrow x-eyebrow-mute">ACCOUNT ⏤ SETTINGS</p>
      <h1 class="x-set-title">设置</h1>
      <p class="x-set-sub">外观、AI 行为、隐私。改动立即生效, 跨刷新保留。</p>
    </header>

    <div class="x-set-body">
      <!-- ── 学习区块: 学习画像 / 我的学科 / 学习统计 (紧凑展示) ── -->
      <section class="x-section x-section-learning">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">学习</p>
          <h2 class="x-section-title">学习画像与统计</h2>
        </header>

        <!-- 学习统计 4 格 -->
        <div class="x-stats-mini-grid">
          <div v-for="s in profileStats" :key="s.label" class="x-stat-mini">
            <p class="x-stat-mini-value">{{ s.value }}</p>
            <p class="x-stat-mini-label">{{ s.label }}</p>
            <p class="x-stat-mini-hint">{{ s.hint }}</p>
          </div>
        </div>

        <!-- 我的学科 (紧凑) -->
        <div class="x-lp-subjects-mini">
          <p class="x-lp-subjects-mini-label">我的学科</p>
          <div v-if="subjectCards.length === 0" class="x-lp-empty-inline">尚未添加任何学科</div>
          <div v-else class="x-lp-subject-chips">
            <span
              v-for="c in subjectCards" :key="c.id"
              class="x-lp-chip"
              :class="{ 'x-lp-chip-active': c.hasLP }"
            >{{ c.display_name }}</span>
          </div>
        </div>

        <!-- 学习画像: 学科选择 + 4 滑块 + 易错点/兴趣方向 -->
        <div class="x-lp-form-mini">
          <div class="x-lp-form-mini-row">
            <select v-model="selectedSubject" class="x-subject-pick">
              <option v-for="s in mySubjects.subjects" :key="s.id" :value="s.name">
                {{ s.display_name }} ({{ s.name }})
              </option>
            </select>
          </div>

          <div v-if="lpLoading" class="x-lp-state-inline">加载 {{ getSubjectDisplayName(selectedSubject || '') }} 的画像…</div>
          <div v-else-if="lpError" class="x-lp-state-inline x-lp-state-error">× {{ lpError }}</div>
          <template v-else>
            <!-- 4 维评分 compact -->
            <div class="x-lp-scores-mini">
              <div class="x-lp-score-mini-item">
                <span class="x-lp-score-mini-label">知识基础</span>
                <div class="x-slider-wrap">
                  <input type="range" min="0" max="100" step="1" v-model.number="lpDraft.knowledge_base" class="x-slider" />
                  <span class="x-score-readout"><span class="x-score-num">{{ lpDraft.knowledge_base }}</span><span class="x-score-label">{{ scoreLabel(lpDraft.knowledge_base) }}</span></span>
                </div>
              </div>
              <div class="x-lp-score-mini-item">
                <span class="x-lp-score-mini-label">认知风格</span>
                <div class="x-slider-wrap">
                  <input type="range" min="0" max="100" step="1" v-model.number="lpDraft.cognitive_style" class="x-slider" />
                  <span class="x-score-readout"><span class="x-score-num">{{ lpDraft.cognitive_style }}</span><span class="x-score-label">{{ scoreLabel(lpDraft.cognitive_style) }}</span></span>
                </div>
              </div>
              <div class="x-lp-score-mini-item">
                <span class="x-lp-score-mini-label">目标明确度</span>
                <div class="x-slider-wrap">
                  <input type="range" min="0" max="100" step="1" v-model.number="lpDraft.learning_goal_score" class="x-slider" />
                  <span class="x-score-readout"><span class="x-score-num">{{ lpDraft.learning_goal_score }}</span><span class="x-score-label">{{ scoreLabel(lpDraft.learning_goal_score) }}</span></span>
                </div>
              </div>
              <div class="x-lp-score-mini-item">
                <span class="x-lp-score-mini-label">可用时间</span>
                <div class="x-slider-wrap">
                  <input type="range" min="0" max="100" step="1" v-model.number="lpDraft.available_time" class="x-slider" />
                  <span class="x-score-readout"><span class="x-score-num">{{ lpDraft.available_time }}</span><span class="x-score-label">{{ scoreLabel(lpDraft.available_time) }}</span></span>
                </div>
              </div>
            </div>
            <!-- 易错点 + 兴趣方向 -->
            <div class="x-lp-tags-mini">
              <input class="x-input x-input-sm" type="text" v-model="lpDraft.common_mistakes" placeholder="易错点 (逗号分隔)" />
              <div v-if="lpMistakeChips.length" class="x-chip-preview">
                <span v-for="(t,i) in lpMistakeChips" :key="i" class="x-chip x-chip-warn">{{ t }}</span>
              </div>
            </div>
            <div class="x-lp-tags-mini">
              <input class="x-input x-input-sm" type="text" v-model="lpDraft.interest_direction" placeholder="兴趣方向 (逗号分隔)" />
              <div v-if="lpInterestChips.length" class="x-chip-preview">
                <span v-for="(t,i) in lpInterestChips" :key="i" class="x-chip">{{ t }}</span>
              </div>
            </div>
            <div class="x-lp-actions-mini">
              <button type="button" class="x-btn x-btn-outline-sm" :disabled="!lpIsDirty || lpSaving" @click="lpReset">重置</button>
              <button type="button" class="x-btn x-btn-primary" :disabled="!lpIsDirty || lpSaving" @click="lpSave">
                {{ lpSaving ? '保存中…' : '保存画像' }}
              </button>
            </div>
          </template>
        </div>
      </section>

      <!-- 1. 外观 -->
      <!-- 1. 外观 -->
      <section class="x-section">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">外观</p>
          <h2 class="x-section-title">主题与字号</h2>
        </header>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">主题</p>
            <p class="x-row-hint">Light / Dark 即时切换, Auto 跟随系统时间设置。</p>
          </div>
          <div class="x-seg">
            <button
              v-for="t in THEME_OPTIONS"
              :key="t.value"
              class="x-seg-btn"
              :class="{ 'is-active': settings.theme === t.value, 'is-disabled': !t.available }"
              :disabled="!t.available"
              @click="pickTheme(t.value)"
            >{{ t.label }}</button>
          </div>
        </div>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">字号</p>
            <p class="x-row-hint">缩放全站基础字号, 重启刷新后保留。</p>
          </div>
          <div class="x-seg">
            <button
              v-for="f in FONT_OPTIONS"
              :key="f.value"
              class="x-seg-btn"
              :class="{ 'is-active': settings.fontScale === f.value }"
              @click="settings.setFontScale(f.value)"
            >
              <span class="x-seg-btn-label">{{ f.label }}</span>
              <span class="x-seg-btn-hint">{{ f.px }}px</span>
            </button>
          </div>
        </div>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">欢迎弹窗</p>
            <p class="x-row-hint">登录后的首次引导弹窗, 默认每次都弹。</p>
          </div>
          <div class="x-seg">
            <button
              v-for="m in WELCOME_MODE_OPTIONS"
              :key="m.value"
              class="x-seg-btn"
              :class="{ 'is-active': onboarding.welcomeMode === m.value }"
              :title="m.hint"
              @click="onboarding.setWelcomeMode(m.value)"
            >{{ m.label }}</button>
          </div>
        </div>
      </section>

      <!-- 2. AI 行为 -->
      <section class="x-section">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">AI 行为</p>
          <h2 class="x-section-title">默认 agent 与回复风格</h2>
        </header>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">默认 agent</p>
            <p class="x-row-hint">新开会话时默认用。已有会话不受影响。</p>
          </div>
          <div class="x-cards-3">
            <button
              v-for="a in AGENT_OPTIONS"
              :key="a.value"
              class="x-mini-card"
              :class="{ 'is-active': settings.defaultAgent === a.value }"
              @click="settings.setDefaultAgent(a.value)"
            >
              <p class="x-mini-card-name">{{ a.label }}</p>
              <p class="x-mini-card-hint">{{ a.hint }}</p>
            </button>
          </div>
        </div>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">回复风格</p>
            <p class="x-row-hint">影响 AI 输出的详略程度。简洁 → 详细。</p>
          </div>
          <div class="x-seg">
            <button
              v-for="r in RESPONSE_OPTIONS"
              :key="r.value"
              class="x-seg-btn"
              :class="{ 'is-active': settings.responseStyle === r.value }"
              @click="settings.setResponseStyle(r.value)"
            >
              <span class="x-seg-btn-label">{{ r.label }}</span>
              <span class="x-seg-btn-hint">{{ r.hint }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 3. 隐私 -->
      <section class="x-section">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">隐私</p>
          <h2 class="x-section-title">可见性与数据</h2>
        </header>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">显示我在线</p>
            <p class="x-row-hint">学习期间在「同班」列表里显出来。</p>
          </div>
          <button
            class="x-toggle"
            :class="{ 'is-on': settings.privacy.showOnline }"
            @click="settings.setShowOnline(!settings.privacy.showOnline)"
            :aria-pressed="settings.privacy.showOnline"
          >
            <span class="x-toggle-knob"></span>
          </button>
        </div>

        <div class="x-row">
          <div class="x-row-label">
            <!-- <p class="x-row-name">分享使用数据</p> -->
            <p class="x-row-hint">匿名的学习模式 + 出题对错比例, 帮助改进产品。</p>
          </div>
          <button
            class="x-toggle"
            :class="{ 'is-on': settings.privacy.shareAnalytics }"
            @click="settings.setShareAnalytics(!settings.privacy.shareAnalytics)"
            :aria-pressed="settings.privacy.shareAnalytics"
          >
            <span class="x-toggle-knob"></span>
          </button>
        </div>

        <div class="x-row x-row-danger">
          <div class="x-row-label">
            <p class="x-row-name">清空本地缓存</p>
            <p class="x-row-hint">登出 + 删所有 aiteach.* 的 localStorage. 后端数据不动。</p>
          </div>
          <button class="x-btn x-btn-danger" @click="handleClearCache">
            清空缓存
          </button>
        </div>
      </section>

      <!-- 4. 学习节奏 -->
     

      <!-- 5. 通知 -->
      <!-- <section class="x-section">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">通知</p>
          <h2 class="x-section-title">三类事件提醒</h2>
        </header>

        <div
          v-for="n in NOTIF_OPTIONS"
          :key="n.key"
          class="x-row"
        >
          <div class="x-row-label">
            <p class="x-row-name">{{ n.label }}</p>
            <p class="x-row-hint">{{ n.hint }}</p>
          </div>
          <button
            class="x-toggle"
            :class="{ 'is-on': settings.notifications[n.key] }"
            @click="settings.setNotification(n.key, !settings.notifications[n.key])"
            :aria-pressed="settings.notifications[n.key]"
            :aria-label="n.label"
          >
            <span class="x-toggle-knob"></span>
          </button>
        </div>
      </section> -->

      <!-- 6. 数据导出 -->
      <section class="x-section">
        <header class="x-section-head">
          <p class="x-eyebrow x-eyebrow-mute">数据</p>
          <h2 class="x-section-title">我的学习数据</h2>
        </header>

        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">导出本地快照</p>
            <p class="x-row-hint">
              一次性下载 个人信息 (脱敏) + 学科列表 + 当前所有设置 的 JSON 文件。
              走浏览器本地下载, 不会上传到任何服务器。
            </p>
          </div>
          <button class="x-btn x-btn-outline-sm" @click="handleExportData">
            导出 ↓
          </button>
        </div>
      </section>

      <!-- 7. 高级 (reset) -->
      <section class="x-section x-section-foot">
        <div class="x-row">
          <div class="x-row-label">
            <p class="x-row-name">恢复默认设置</p>
            <p class="x-row-hint">把所有偏好回滚到出厂值。</p>
          </div>
          <button class="x-btn x-btn-outline-sm" @click="handleResetAll">
            重置
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* ============================================================
   ROOT + HEADER  (跟其它内部页一致)
   ============================================================ */

/* === 未登录守卫: 居中卡片 + 跳转 CTA === */
.x-guard {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  gap: 10px;
}
.x-guard-mark {
  font-size: 36px;
  color: var(--x-body-mid);
  margin: 0 0 8px;
  opacity: 0.5;
}
.x-guard-title {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
  letter-spacing: -0.2px;
}
.x-guard-hint {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0 0 16px;
}
.x-guard .x-btn { display: inline-block; text-decoration: none; }

.x-set {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  color: var(--x-ink);
  display: flex;
  flex-direction: column;
}
.x-set-head {
  padding: 32px 40px 24px;
  border-bottom: 1px solid var(--x-hairline);
}
.x-set-title {
  font-family: var(--x-font-display);
  font-size: calc(28px * var(--x-font-scale, 1));
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 8px 0 6px;
}
.x-set-sub {
  font-size: calc(13px * var(--x-font-scale, 1));
  color: var(--x-body);
  margin: 0;
}

.x-set-body {
  flex: 1;
  padding: 24px 40px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ============================================================
   SECTION
   ============================================================ */
.x-section {
  background: var(--x-canvas-card);
  border: 0;
  border-radius: var(--x-rounded-lg);
  padding: 24px 28px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
              0 8px 24px rgba(15, 23, 42, 0.05);
  transition: box-shadow 0.3s cubic-bezier(0.2, 0.7, 0.2, 1),
              transform 0.3s cubic-bezier(0.2, 0.7, 0.2, 1);
}

/* light sweep on hover */
.x-section::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -60%;
  width: 50%;
  height: 200%;
  background: linear-gradient(115deg,
      transparent 0%,
      var(--x-blue-alpha-06) 50%,
      transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.7s ease;
  pointer-events: none;
}

.x-section:hover {
  box-shadow: 0 4px 8px rgba(15, 23, 42, 0.06),
              0 20px 48px rgba(15, 23, 42, 0.10);
  transform: translateY(-4px);
}

.x-section:hover::before {
  transform: translateX(280%);
}
.x-section-head {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--x-hairline);
  margin-bottom: 4px;
}
.x-section-title {
  font-family: var(--x-font-display);
  font-size: calc(16px * var(--x-font-scale, 1));
  font-weight: 500;
  color: var(--x-ink);
  margin: 6px 0 0;
}
.x-section-foot {
  background: var(--x-canvas-card);
}

/* ============================================================
   ROW  (label 左, control 右)
   ============================================================ */
.x-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px 0;
  border-bottom: 1px solid var(--x-hairline);
}
.x-row:last-child { border-bottom: 0; }
.x-row-danger { color: var(--x-error); }
.x-row-label {
  flex: 1;
  min-width: 0;
}
.x-row-name {
  font-family: var(--x-font-display);
  font-size: calc(14px * var(--x-font-scale, 1));
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 2px;
}
.x-row-hint {
  font-size: calc(12px * var(--x-font-scale, 1));
  color: var(--x-body-mid);
  margin: 0;
  line-height: 1.5;
}

/* ============================================================
   SEG (segmented control)
   ============================================================ */
.x-seg {
  display: inline-flex;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-pill);
  padding: 3px;
  flex-shrink: 0;
}

/* 5 档 / 3 档变体 —— 跟默认 (2-3 档) 相比 padding 更紧, 避免窄 row 内换行 */
.x-seg-5 { padding: 2px; }
.x-seg-5 .x-seg-btn { padding: 5px 9px; font-size: 12.5px; }
.x-seg-3 { padding: 3px; }
.x-seg-3 .x-seg-btn { padding: 6px 12px; font-size: 12.5px; }
.x-seg-btn {
  border: 0;
  background: transparent;
  padding: 6px 14px;
  font-family: var(--x-font-display);
  font-size: calc(13px * var(--x-font-scale, 1));
  color: var(--x-body);
  cursor: pointer;
  border-radius: var(--x-rounded-pill);
  transition: background 0.12s, color 0.12s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.x-seg-btn:hover:not(:disabled):not(.is-disabled) { color: var(--x-ink); }
.x-seg-btn.is-active {
  background: var(--x-canvas);
  color: var(--x-primary);
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}
.x-seg-btn.is-disabled,
.x-seg-btn:disabled {
  color: var(--x-mute);
  cursor: not-allowed;
  opacity: 0.6;
}
.x-seg-btn-label { font-weight: inherit; }
.x-seg-btn-hint {
  font-size: calc(11px * var(--x-font-scale, 1));
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
}
.x-seg-btn.is-active .x-seg-btn-hint { color: var(--x-primary); }

/* ============================================================
   MINI CARDS  (3-up for agent selection)
   ============================================================ */
.x-cards-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  flex-shrink: 0;
  min-width: 360px;
}
.x-mini-card {
  text-align: left;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}
.x-mini-card:hover { background: var(--x-canvas-mid); }
.x-mini-card.is-active {
  background: var(--x-primary-soft);
  border-color: var(--x-primary);
}
.x-mini-card-name {
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0 0 2px;
}
.x-mini-card.is-active .x-mini-card-name { color: var(--x-primary); }
.x-mini-card-hint {
  font-size: 11px;
  color: var(--x-body-mid);
  margin: 0;
  line-height: 1.4;
}

/* ============================================================
   TOGGLE  (iOS-style switch)
   ============================================================ */
.x-toggle {
  position: relative;
  width: 40px;
  height: 22px;
  background: var(--x-canvas-mid);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  flex-shrink: 0;
  padding: 0;
  transition: background 0.15s, border-color 0.15s;
}
.x-toggle-knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 18px;
  height: 18px;
  background: var(--x-canvas);
  border-radius: 50%;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.15);
  transition: transform 0.18s;
}
.x-toggle.is-on {
  background: var(--x-primary);
  border-color: var(--x-primary);
}
.x-toggle.is-on .x-toggle-knob {
  transform: translateX(18px);
}

/* ============================================================
   PRIMITIVES
   ============================================================ */
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

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
  border: 1px solid var(--x-ink-alpha-15);
  padding: 6px 14px;
  font-size: 12px;
}
.x-btn-outline-sm:hover:not(:disabled) {
  background: var(--x-canvas-soft);
  border-color: var(--x-ink-alpha-30);
}
.x-btn-danger {
  background: transparent;
  color: var(--x-error);
  border: 1px solid var(--x-error-soft);
  padding: 7px 16px;
  font-size: 13px;
}
.x-btn-danger:hover:not(:disabled) {
  background: var(--x-error-soft);
}

/* ============================================================
   LEARNING SECTION COMPACT STYLES
   ============================================================ */
.x-section-learning { background: var(--x-canvas); }

.x-stats-mini-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.x-stat-mini {
  padding: 12px 14px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
  border: 1px solid var(--x-hairline);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.x-stat-mini-value {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--x-ink);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.3px;
  line-height: 1.1;
  margin: 0;
}
.x-stat-mini-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--x-body);
  font-family: var(--x-font-display);
  margin: 0;
}
.x-stat-mini-hint {
  font-size: 10px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  margin: 2px 0 0;
  line-height: 1.3;
}

.x-lp-subjects-mini {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.x-lp-subjects-mini-label {
  font-size: 11px;
  font-family: var(--x-font-mono);
  color: var(--x-body-mid);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}
.x-lp-empty-inline {
  font-size: 12px;
  color: var(--x-mute);
  font-style: italic;
}
.x-lp-subject-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.x-lp-chip {
  display: inline-flex;
  align-items: center;
  background: var(--x-canvas-soft);
  color: var(--x-body);
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
  font-size: 12px;
  font-family: var(--x-font-display);
  border: 1px solid var(--x-hairline);
  transition: border-color 0.12s, color 0.12s;
}
.x-lp-chip:hover { border-color: var(--x-ink-alpha-30); color: var(--x-ink); }
.x-lp-chip.x-lp-chip-active {
  background: var(--x-primary-soft);
  color: var(--x-primary);
  border-color: var(--x-primary);
  font-weight: 500;
}

.x-lp-form-mini {
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-top: 1px solid var(--x-hairline);
  padding-top: 14px;
}
.x-lp-form-mini-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.x-subject-pick {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-pill);
  padding: 6px 12px;
  font-family: var(--x-font-display);
  font-size: 12.5px;
  color: var(--x-ink);
  cursor: pointer;
  outline: none;
  transition: border-color 0.12s;
}
.x-subject-pick:hover { border-color: var(--x-ink-alpha-30); }
.x-subject-pick:focus { border-color: var(--x-primary); }

.x-lp-state-inline {
  font-size: 12px;
  color: var(--x-body-mid);
  padding: 10px 0;
  text-align: center;
}
.x-lp-state-inline.x-lp-state-error { color: var(--x-error); }

.x-lp-scores-mini {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 20px;
}
.x-lp-score-mini-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.x-lp-score-mini-label {
  font-size: 11px;
  font-family: var(--x-font-mono);
  color: var(--x-body-mid);
  min-width: 60px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.x-slider-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.x-slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--x-hairline);
  border-radius: 999px;
  outline: none;
  cursor: pointer;
  min-width: 0;
}
.x-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--x-primary);
  border: 2px solid var(--x-canvas);
  cursor: pointer;
  box-shadow: 0 1px 3px var(--x-ink-alpha-15);
}
.x-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--x-primary);
  border: 2px solid var(--x-canvas);
  cursor: pointer;
}
.x-score-readout {
  display: inline-flex;
  align-items: baseline;
  gap: 3px;
  font-family: var(--x-font-mono);
  flex-shrink: 0;
}
.x-score-num {
  font-size: 12px;
  font-weight: 500;
  color: var(--x-ink);
  font-variant-numeric: tabular-nums;
}
.x-score-label {
  font-size: 9px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--x-body-mid);
}

.x-lp-tags-mini { display: flex; flex-direction: column; gap: 4px; }
.x-input-sm {
  background: var(--x-canvas);
  color: var(--x-ink);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  padding: 7px 10px;
  font-family: var(--x-font-display);
  font-size: 12px;
  outline: none;
  transition: border-color 0.12s;
  width: 100%;
}
.x-input-sm:focus { border-color: var(--x-primary); }
.x-input-sm::placeholder { color: var(--x-mute); }

.x-chip-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 2px;
}
.x-chip {
  display: inline-flex;
  align-items: center;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  padding: 2px 8px;
  border-radius: var(--x-rounded-pill);
  font-size: 11px;
  font-family: var(--x-font-display);
}
.x-chip.x-chip-warn {
  background: var(--x-error-soft);
  color: var(--x-error);
}

.x-lp-actions-mini {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--x-hairline);
  padding-top: 10px;
}

@media (max-width: 768px) {
  .x-set-head, .x-set-body { padding-left: 16px; padding-right: 16px; }
  .x-row { flex-direction: column; align-items: stretch; gap: 12px; }
  .x-cards-3 { grid-template-columns: 1fr; min-width: 0; }
  .x-stats-mini-grid { grid-template-columns: 1fr 1fr; }
  .x-lp-scores-mini { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
  .x-stats-mini-grid { grid-template-columns: 1fr 1fr; }
}
</style>
