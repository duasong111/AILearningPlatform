<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { getProfile, updateProfile } from '@/api/profile'
import { getSubjectDisplayName } from '@/api/subjects'
import type { User, UserProfile } from '@/types/response'
import type { SubjectCode } from '@/types/learning'
import { IconGuard, IconArrow } from '@/components/icons'

/**
 * 个人中心 —— 编辑 User 字段
 *
 *   ⚠ 后端目前没有 PATCH /api/users/<id>/ 或类似接口,
 *     UserSerializer 只在登录响应里出现一次, 不可写.
 *
 *   现状策略:
 *     - 表单 draft 与 store.user 解耦, 用户随便改
 *     - Save 时本地写回 store (持久化插件 → localStorage), toast 提示 "local only"
 *     - 等后端补接口后, 在 onSave() 里加一行 http.patch(...) 即可
 *
 *   字段集与 backend/users/serializers.py:18-28 的 UserSerializer 对齐.
 *   email + id 永远 readonly.
 */

const userStore = useUserStore()

// 表单可编辑字段 (排除 readonly: id / email / username)
//   username 在后端是 USERNAME_FIELD 的 fallback 显示名, 设为 readonly 更安全
interface ProfileDraft {
  real_name: string
  gender: 'M' | 'F' | 'O' | ''
  age: number | null
  occupation: string
  city: string
  bio: string
  learning_goal: string
  interest_tags: string                  // UI 用逗号分隔字符串, 保存时 parse 成 string[]
}

function emptyDraft(): ProfileDraft {
  return {
    real_name: '', gender: '', age: null,
    occupation: '', city: '', bio: '',
    learning_goal: '', interest_tags: '',
  }
}

function draftFromUser(u: User | null): ProfileDraft {
  if (!u) return emptyDraft()
  return {
    real_name:     u.real_name ?? '',
    gender:        (u.gender ?? '') as ProfileDraft['gender'],
    age:           u.age ?? null,
    occupation:    u.occupation ?? '',
    city:          u.city ?? '',
    bio:           u.bio ?? '',
    learning_goal: u.learning_goal ?? '',
    interest_tags: (u.interest_tags ?? []).join(', '),
  }
}

const form = reactive<ProfileDraft>(draftFromUser(userStore.user))
const saving = ref(false)

// 外部 store 变化 (e.g. 多 tab 刷新, 登出登录) → 同步回 draft
watch(
  () => userStore.user,
  (u) => {
    Object.assign(form, draftFromUser(u))
  },
)

onMounted(() => {
  // 确保 user 已 hydration (持久化插件早就同步过, 这里防御一下)
  if (userStore.user) Object.assign(form, draftFromUser(userStore.user))
})

// === Validation ===
const errors = computed(() => {
  const e: Partial<Record<keyof ProfileDraft, string>> = {}
  if (form.real_name.length > 100) e.real_name = '不超过 100 字符'
  if (form.age !== null && (form.age < 0 || form.age > 150)) e.age = '0 — 150 之间'
  if (form.bio.length > 500) e.bio = '不超过 500 字符'
  if (form.learning_goal.length > 500) e.learning_goal = '不超过 500 字符'
  if (form.interest_tags.length > 200) e.interest_tags = '不超过 200 字符'
  return e
})

const hasErrors = computed(() => Object.keys(errors.value).length > 0)
const isDirty = computed(() => {
  const saved = draftFromUser(userStore.user)
  return (Object.keys(saved) as (keyof ProfileDraft)[]).some(
    (k) => saved[k] !== form[k],
  )
})

// === Actions ===
function handleReset(): void {
  Object.assign(form, draftFromUser(userStore.user))
}

async function handleSave(): Promise<void> {
  if (hasErrors.value || saving.value) return
  saving.value = true
  try {
    // ── TODO: backend PATCH endpoint pending ────────────────
    // const { data } = await http.patch('/api/users/me/', payload)
    // userStore.user = data
    //
    // 现状: 本地写回 store, persist 插件自动落 localStorage
    if (!userStore.user) {
      throw new Error('Not authenticated')
    }
    const updated: User = {
      ...userStore.user,
      real_name:     form.real_name.trim() || null,
      gender:        (form.gender || null) as User['gender'],
      age:           form.age,
      occupation:    form.occupation.trim() || null,
      city:          form.city.trim() || null,
      bio:           form.bio.trim() || null,
      learning_goal: form.learning_goal.trim() || null,
      interest_tags: form.interest_tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    }
    userStore.user = updated
    ElMessage({
      message: '→ Saved (local only — backend endpoint pending)',
      customClass: 'x-toast',
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Save failed'
    ElMessage({ message: `× ${msg}`, customClass: 'x-toast' })
  } finally {
    saving.value = false
  }
}

function handleAvatarClick(): void {
  ElMessage({
    message: '→ TODO: avatar upload (backend endpoint pending)',
    customClass: 'x-toast',
  })
}

const avatarFallback = computed<string>(() => {
  const n = userStore.displayName
  return n && n.length > 0 ? n.charAt(0).toUpperCase() : '?'
})

// ============================================================
// 学习画像 (per-subject UserProfile) —— 调真后端
//   GET   /api/profile/?subject=<code>  自动 get_or_create
//   PATCH /api/profile/?subject=<code>  写回 6 个字段
//
//   字段语义 (源自 backend UserProfile model):
//     - knowledge_base       知识基础 (0-100)
//     - cognitive_style      认知风格 (0-100, e.g. 视觉/听觉倾向)
//     - learning_goal_score  学习目标明确度 (0-100)
//     - available_time       可用学习时间 (0-100, 相对单位)
//     - common_mistakes      易错知识点 string[]
//     - interest_direction   兴趣方向 string[]
//     - course               备注课程名 (string)
//
//   ⚠ 这些值也会被 AI 助教 (ProfileConsumer LangChain agent) 在对话中写入.
//     用户手编后下一次对话仍可能覆盖. UI 提示一下避免困惑.
// ============================================================
const mySubjects = useMySubjectsStore()

// 当前选中要查看/编辑的学科. 默认第一个;无学科时为空.
const selectedSubject = ref<SubjectCode | ''>(
  (mySubjects.subjects[0]?.name as SubjectCode | undefined) ?? '',
)

interface LPDraft {
  course: string
  knowledge_base: number
  cognitive_style: number
  learning_goal_score: number
  available_time: number
  common_mistakes: string                  // UI 逗号串, save 时 parse 成 string[]
  interest_direction: string
}

function emptyLP(): LPDraft {
  return {
    course: '',
    knowledge_base: 0,
    cognitive_style: 0,
    learning_goal_score: 0,
    available_time: 0,
    common_mistakes: '',
    interest_direction: '',
  }
}

function lpFromServer(p: UserProfile): LPDraft {
  return {
    course:               p.course ?? '',
    knowledge_base:       p.knowledge_base,
    cognitive_style:      p.cognitive_style,
    learning_goal_score:  p.learning_goal_score,
    available_time:       p.available_time,
    common_mistakes:      (p.common_mistakes      ?? []).join(', '),
    interest_direction:   (p.interest_direction   ?? []).join(', '),
  }
}

const lpServer = ref<UserProfile | null>(null)    // 服务器上现存的快照, 用于 Reset
const lpDraft = reactive<LPDraft>(emptyLP())
const lpLoading = ref(false)
const lpSaving = ref(false)
const lpError = ref('')

async function loadLP(): Promise<void> {
  if (!selectedSubject.value) {
    lpServer.value = null
    Object.assign(lpDraft, emptyLP())
    return
  }
  lpLoading.value = true
  lpError.value = ''
  try {
    const { data } = await getProfile(selectedSubject.value)
    lpServer.value = data
    Object.assign(lpDraft, lpFromServer(data))
  } catch (err) {
    // 后端约定: 没有该学科时抛 404 "用户还没有创建任何学科,请先创建学科"
    //          虽然走 mySubjectsStore 选的应该都存在, 但兜底处理一下
    if (err instanceof AxiosError && err.response?.status === 404) {
      lpError.value = '该学科还没有画像数据, 请先在 AI 助教中聊一段或手动保存.'
    } else {
      lpError.value = err instanceof Error ? err.message : 'Load failed'
    }
    lpServer.value = null
    Object.assign(lpDraft, emptyLP())
  } finally {
    lpLoading.value = false
  }
}

// 切学科 / 进入页面 → reload
watch(selectedSubject, loadLP, { immediate: true })

const lpIsDirty = computed(() => {
  if (!lpServer.value) return false
  const saved = lpFromServer(lpServer.value)
  return (Object.keys(saved) as (keyof LPDraft)[]).some(
    (k) => saved[k] !== lpDraft[k],
  )
})

function lpReset(): void {
  if (lpServer.value) {
    Object.assign(lpDraft, lpFromServer(lpServer.value))
  }
}

async function lpSave(): Promise<void> {
  if (!selectedSubject.value || lpSaving.value) return
  lpSaving.value = true
  try {
    const payload: Partial<UserProfile> = {
      course:               lpDraft.course.trim() || null,
      knowledge_base:       clampScore(lpDraft.knowledge_base),
      cognitive_style:      clampScore(lpDraft.cognitive_style),
      learning_goal_score:  clampScore(lpDraft.learning_goal_score),
      available_time:       clampScore(lpDraft.available_time),
      common_mistakes:      parseTags(lpDraft.common_mistakes),
      interest_direction:   parseTags(lpDraft.interest_direction),
    }
    const { data } = await updateProfile(selectedSubject.value, payload)
    lpServer.value = data
    Object.assign(lpDraft, lpFromServer(data))
    ElMessage({ message: '→ 学习画像已保存', customClass: 'x-toast' })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Save failed'
    ElMessage({ message: `× ${msg}`, customClass: 'x-toast' })
  } finally {
    lpSaving.value = false
  }
}

function clampScore(n: number): number {
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, Math.round(n)))
}
function parseTags(s: string): string[] {
  return s.split(',').map((t) => t.trim()).filter(Boolean)
}

// 评分语义化标签 (滑块右侧小字)
function scoreLabel(n: number): string {
  if (n >= 80) return '高'
  if (n >= 50) return '中'
  if (n >= 20) return '低'
  return '未评估'
}

// 用于 chip 预览
const lpMistakeChips = computed<string[]>(() => parseTags(lpDraft.common_mistakes))
const lpInterestChips = computed<string[]>(() => parseTags(lpDraft.interest_direction))

// ============================================================
// "我的学科" + "学习统计" 两个新 section 的 computeds
//
//   设计意图:
//     - "我的学科": 让用户看到自己已选课程的全貌, 当前 LP 选学科用下拉,
//       这个 section 是"以学科为主语的卡片矩阵", 跟 LP 互补不重复
//     - "学习统计": 4 数字 (学科数 / 画像进度 / 兴趣方向 / 错点)
//       全是真实数据推导, 没编造数字
// ============================================================

// 学科卡片 —— 简单映射 mySubjects.subjects, 后端没有 per-subject 进度时不造假
interface SubjectCardVM {
  id: number
  name: SubjectCode | string
  display_name: string
  joinedAt: string
  hasLP: boolean        // 当前数据里这个学科有没有 UserProfile 记录
}
const subjectCards = computed<SubjectCardVM[]>(() =>
  mySubjects.subjects.map((s) => ({
    id: s.id,
    name: s.name,
    display_name: s.display_name,
    joinedAt: s.created_at,
    hasLP: lpServer.value?.subject?.id === s.id,   // 当前 LP 服务端快照恰好对应这学科
  })),
)

// 4 数字统计 —— 全部从 stores + 真实字段推导
interface StatVM { label: string; value: string; hint: string }
const profileStats = computed<StatVM[]>(() => {
  const subjectCount = mySubjects.subjects.length
  // 当前 LP 的 4 个评分, 没数据时全部用 "—" 占位
  const scores: Array<[string, number]> = [
    ['知识基础',      lpServer.value?.knowledge_base       ?? 0],
    ['认知风格',      lpServer.value?.cognitive_style      ?? 0],
    ['目标明确度',    lpServer.value?.learning_goal_score  ?? 0],
    ['可用时间',      lpServer.value?.available_time       ?? 0],
  ]
  // 找当前 LP 中分最高的那个维度做 "画像进度"
  const hasLP = lpServer.value !== null
  const lpProgressLabel = hasLP
    ? scores.reduce<[string, number]>((a, b) => (b[1] > a[1] ? b : a), ['', 0])[0] || '—'
    : '—'
  // 错点 / 兴趣 chip 数
  const mistakeCount = lpMistakeChips.value.length
  const interestCount = lpInterestChips.value.length
  return [
    { label: '已选学科',   value: String(subjectCount), hint: '来自 我的课程 列表' },
    {
      label: '画像进度',
      value: hasLP ? lpProgressLabel : '—',
      hint: hasLP ? '当前 LP 4 维评分里最高的那一项' : '请先在下方画像区保存一次',
    },
    { label: '易错点',     value: String(mistakeCount), hint: 'LP 里标记的常见错点' },
    { label: '兴趣方向',   value: String(interestCount), hint: 'LP 里填的兴趣关键词' },
  ]
})

// 账号开通时间 —— 后端 UserSerializer 没暴露 date_joined, 用 "已开通" + 用户名 fallback
//   不造假注册日期, 只显示一段描述性状态
const accountStatusText = computed<string>(() => {
  if (!userStore.user) return '未登录'
  return `账号已开通 · ${userStore.user.email || userStore.user.username}`
})
</script>

<template>
  <div class="x-profile">
    <!-- 未登录守卫 —— userStore 持久化插件理论上同步 hydrate,
         但 hydration 时序竞争时可能短暂为 null, 渲染 form 会"全是占位符".
         加这层保护, 异常时给一个明确提示而不是"看着像空白" -->
    <div v-if="!userStore.user" class="x-guard">
      <p class="x-guard-mark" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-body-mid)"><IconGuard :size="40" /></p>
      <p class="x-guard-title">未登录</p>
      <p class="x-guard-hint">登录后查看个人中心。</p>
      <router-link to="/login" class="x-btn x-btn-primary"><span style="display:inline-flex;align-items:center;gap:6px">去登录 <IconArrow :size="12" /></span></router-link>
    </div>
    <header class="x-profile-head">
      <p class="x-eyebrow x-eyebrow-mute">ACCOUNT ⏤ PROFILE</p>
      <h1 class="x-title">个人中心</h1>
    </header>

    <!-- AVATAR + IDENTITY -->
    <section class="x-section x-identity">
      <button
        type="button"
        class="x-avatar"
        @click="handleAvatarClick"
        :aria-label="'Change avatar'"
      >
        <img
          v-if="userStore.user?.avatar"
          :src="userStore.user.avatar"
          :alt="userStore.displayName"
        />
        <span v-else class="x-avatar-fallback">{{ avatarFallback }}</span>
        <span class="x-avatar-edit">↑</span>
      </button>
      <div class="x-identity-text">
        <p class="x-eyebrow x-eyebrow-mute">USERNAME</p>
        <p class="x-identity-handle">{{ userStore.user?.username || '—' }}</p>
        <p class="x-identity-email">{{ userStore.user?.email || '—' }}</p>
      </div>
    </section>

    <!-- FORM -->
    <form class="x-section x-form" @submit.prevent="handleSave">
      <div class="x-form-row">
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="p-real">REAL NAME</label>
          <input
            id="p-real"
            class="x-input"
            :class="{ 'is-error': errors.real_name }"
            type="text"
            v-model="form.real_name"
            placeholder="——"
          />
          <p v-if="errors.real_name" class="x-field-error">{{ errors.real_name }}</p>
        </div>
        <div class="x-field x-field-narrow">
          <label class="x-eyebrow x-eyebrow-mute" for="p-age">AGE</label>
          <input
            id="p-age"
            class="x-input"
            :class="{ 'is-error': errors.age }"
            type="number"
            min="0" max="150"
            v-model.number="form.age"
            placeholder="——"
          />
          <p v-if="errors.age" class="x-field-error">{{ errors.age }}</p>
        </div>
      </div>

      <div class="x-form-row">
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute">GENDER</label>
          <div class="x-radio-row">
            <label
              v-for="g in ['M', 'F', 'O'] as const"
              :key="g"
              class="x-radio"
              :class="{ 'is-checked': form.gender === g }"
            >
              <input type="radio" :value="g" v-model="form.gender" />
              <span>{{ g === 'M' ? '男' : g === 'F' ? '女' : '其他' }}</span>
            </label>
            <button
              v-if="form.gender"
              type="button"
              class="x-clear-btn"
              @click="form.gender = ''"
              aria-label="Clear gender"
            >×</button>
          </div>
        </div>
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="p-occ">OCCUPATION</label>
          <input
            id="p-occ"
            class="x-input"
            type="text"
            v-model="form.occupation"
            placeholder="——"
          />
        </div>
      </div>

      <div class="x-form-row">
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="p-city">CITY</label>
          <input
            id="p-city"
            class="x-input"
            type="text"
            v-model="form.city"
            placeholder="——"
          />
        </div>
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="p-tags">
            INTEREST TAGS <span class="x-hint">— comma-separated</span>
          </label>
          <input
            id="p-tags"
            class="x-input"
            :class="{ 'is-error': errors.interest_tags }"
            type="text"
            v-model="form.interest_tags"
            placeholder="algorithm, ai, music"
          />
          <p v-if="errors.interest_tags" class="x-field-error">{{ errors.interest_tags }}</p>
        </div>
      </div>

      <div class="x-field x-field-full">
        <label class="x-eyebrow x-eyebrow-mute" for="p-bio">BIO</label>
        <textarea
          id="p-bio"
          class="x-input x-textarea"
          :class="{ 'is-error': errors.bio }"
          rows="4"
          v-model="form.bio"
          placeholder="一句话介绍自己…"
        ></textarea>
        <p v-if="errors.bio" class="x-field-error">{{ errors.bio }}</p>
        <p v-else class="x-counter">{{ form.bio.length }} / 500</p>
      </div>

      <div class="x-field x-field-full">
        <label class="x-eyebrow x-eyebrow-mute" for="p-goal">LEARNING GOAL</label>
        <textarea
          id="p-goal"
          class="x-input x-textarea"
          :class="{ 'is-error': errors.learning_goal }"
          rows="3"
          v-model="form.learning_goal"
          placeholder="你想要达成的学习目标…"
        ></textarea>
        <p v-if="errors.learning_goal" class="x-field-error">{{ errors.learning_goal }}</p>
        <p v-else class="x-counter">{{ form.learning_goal.length }} / 500</p>
      </div>

      <!-- ACTIONS -->
      <div class="x-form-actions">
        <button
          type="button"
          class="x-btn x-btn-outline-sm"
          :disabled="!isDirty || saving"
          @click="handleReset"
        >Reset</button>
        <button
          type="submit"
          class="x-btn x-btn-primary"
          :disabled="!isDirty || hasErrors || saving"
        >{{ saving ? 'Saving…' : 'Save changes →' }}</button>
      </div>
    </form>

    <!-- ============================================================
         学习画像 (per-subject UserProfile) —— 真后端
         ============================================================ -->
    <section class="x-section x-lp">
      <header class="x-lp-head">
        <div>
          <p class="x-eyebrow x-eyebrow-mute">LEARNING ⏤ PROFILE</p>
          <h2 class="x-lp-title">学习画像</h2>
          <p class="x-lp-hint">
            每门课程一份, 用于个性化推荐与练习难度调节。
            <span class="x-lp-hint-mute">AI 助教在对话中也会写入这些值。</span>
          </p>
        </div>
        <select
          v-if="mySubjects.subjects.length > 0"
          v-model="selectedSubject"
          class="x-subject-pick"
        >
          <option
            v-for="s in mySubjects.subjects"
            :key="s.id"
            :value="s.name"
          >{{ s.display_name }} ({{ s.name }})</option>
        </select>
      </header>

      <!-- 无课程: 引导加课 -->
      <div v-if="mySubjects.subjects.length === 0" class="x-lp-empty">
        <p class="x-lp-empty-msg">学习画像基于课程展开。请先在「我的课程」中添加至少一门。</p>
      </div>

      <!-- 加载中 -->
      <div v-else-if="lpLoading" class="x-lp-state">
        <span class="x-eyebrow x-eyebrow-mute">LOADING</span>
        <span class="x-lp-state-msg">加载 {{ getSubjectDisplayName(selectedSubject || '') }} 的画像…</span>
      </div>

      <!-- 错误 -->
      <div v-else-if="lpError" class="x-lp-state x-lp-state-error">
        <span class="x-eyebrow x-eyebrow-mute">ERROR</span>
        <span class="x-lp-state-msg">× {{ lpError }}</span>
        <button class="x-btn-link" @click="loadLP">Retry →</button>
      </div>

      <!-- 表单 -->
      <form v-else class="x-lp-form" @submit.prevent="lpSave">
        <!-- 课程备注 -->
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="lp-course">
            COURSE NOTE <span class="x-hint">— 自定义课程名 (e.g. "数据结构 - 期末复习")</span>
          </label>
          <input
            id="lp-course"
            class="x-input"
            type="text"
            v-model="lpDraft.course"
            placeholder="——"
          />
        </div>

        <!-- 4 个 0-100 分数滑块 -->
        <div class="x-lp-scores">
          <!-- KNOWLEDGE BASE -->
          <div class="x-field x-slider-field">
            <label class="x-eyebrow x-eyebrow-mute" for="lp-kb">
              KNOWLEDGE BASE <span class="x-hint">— 知识基础</span>
            </label>
            <div class="x-slider-row">
              <input
                id="lp-kb" class="x-slider"
                type="range" min="0" max="100" step="1"
                v-model.number="lpDraft.knowledge_base"
              />
              <span class="x-score-readout">
                <span class="x-score-num">{{ lpDraft.knowledge_base }}</span>
                <span class="x-score-label">{{ scoreLabel(lpDraft.knowledge_base) }}</span>
              </span>
            </div>
          </div>

          <!-- COGNITIVE STYLE -->
          <div class="x-field x-slider-field">
            <label class="x-eyebrow x-eyebrow-mute" for="lp-cs">
              COGNITIVE STYLE <span class="x-hint">— 认知风格</span>
            </label>
            <div class="x-slider-row">
              <input
                id="lp-cs" class="x-slider"
                type="range" min="0" max="100" step="1"
                v-model.number="lpDraft.cognitive_style"
              />
              <span class="x-score-readout">
                <span class="x-score-num">{{ lpDraft.cognitive_style }}</span>
                <span class="x-score-label">{{ scoreLabel(lpDraft.cognitive_style) }}</span>
              </span>
            </div>
          </div>

          <!-- LEARNING GOAL -->
          <div class="x-field x-slider-field">
            <label class="x-eyebrow x-eyebrow-mute" for="lp-lg">
              GOAL CLARITY <span class="x-hint">— 学习目标明确度</span>
            </label>
            <div class="x-slider-row">
              <input
                id="lp-lg" class="x-slider"
                type="range" min="0" max="100" step="1"
                v-model.number="lpDraft.learning_goal_score"
              />
              <span class="x-score-readout">
                <span class="x-score-num">{{ lpDraft.learning_goal_score }}</span>
                <span class="x-score-label">{{ scoreLabel(lpDraft.learning_goal_score) }}</span>
              </span>
            </div>
          </div>

          <!-- AVAILABLE TIME -->
          <div class="x-field x-slider-field">
            <label class="x-eyebrow x-eyebrow-mute" for="lp-at">
              AVAILABLE TIME <span class="x-hint">— 可用学习时间</span>
            </label>
            <div class="x-slider-row">
              <input
                id="lp-at" class="x-slider"
                type="range" min="0" max="100" step="1"
                v-model.number="lpDraft.available_time"
              />
              <span class="x-score-readout">
                <span class="x-score-num">{{ lpDraft.available_time }}</span>
                <span class="x-score-label">{{ scoreLabel(lpDraft.available_time) }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 易错点 -->
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="lp-cm">
            COMMON MISTAKES <span class="x-hint">— 易错知识点, 逗号分隔</span>
          </label>
          <input
            id="lp-cm"
            class="x-input"
            type="text"
            v-model="lpDraft.common_mistakes"
            placeholder="e.g. 红黑树旋转, 动态规划状态定义"
          />
          <div v-if="lpMistakeChips.length > 0" class="x-chip-preview">
            <span
              v-for="(t, i) in lpMistakeChips"
              :key="i"
              class="x-chip x-chip-warn"
            >{{ t }}</span>
          </div>
        </div>

        <!-- 兴趣方向 -->
        <div class="x-field">
          <label class="x-eyebrow x-eyebrow-mute" for="lp-id">
            INTEREST DIRECTION <span class="x-hint">— 兴趣方向, 逗号分隔</span>
          </label>
          <input
            id="lp-id"
            class="x-input"
            type="text"
            v-model="lpDraft.interest_direction"
            placeholder="e.g. 算法竞赛, 系统设计, 机器学习"
          />
          <div v-if="lpInterestChips.length > 0" class="x-chip-preview">
            <span
              v-for="(t, i) in lpInterestChips"
              :key="i"
              class="x-chip"
            >{{ t }}</span>
          </div>
        </div>

        <!-- META: updated time -->
        <p v-if="lpServer" class="x-lp-meta">
          Updated <span class="x-mono">{{ lpServer.updated_at.slice(0, 19).replace('T', ' ') }}</span>
        </p>

        <!-- ACTIONS -->
        <div class="x-form-actions">
          <button
            type="button"
            class="x-btn x-btn-outline-sm"
            :disabled="!lpIsDirty || lpSaving"
            @click="lpReset"
          >Reset</button>
          <button
            type="submit"
            class="x-btn x-btn-primary"
            :disabled="!lpIsDirty || lpSaving"
          >{{ lpSaving ? 'Saving…' : 'Save profile →' }}</button>
        </div>
      </form>
    </section>

    <!-- ============================================================
         我的学科 —— 列出 mySubjects, 每张卡显示加入时间 + 是否有画像
         跟下方 x-lp 的"选学科查看画像"形成上下游: 这里看全貌, 那里编辑细节
         ============================================================ -->
    <section class="x-section x-courses">
      <header class="x-courses-head">
        <div>
          <p class="x-eyebrow x-eyebrow-mute">学径 ⏤ MY SUBJECTS</p>
          <h2 class="x-courses-title">我的学科</h2>
          <p class="x-courses-hint">你正在学 / 已选的学科。每门学科可以有自己的学习画像。</p>
        </div>
        <router-link to="/app/plan" class="x-btn x-btn-outline-sm">
          + 管理课程
        </router-link>
      </header>

      <div v-if="subjectCards.length === 0" class="x-courses-empty">
        还没选任何课程, 前往「<router-link to="/app/plan" class="x-link-inline">我的课程</router-link>」添加。
      </div>

      <div v-else class="x-courses-grid">
        <article
          v-for="card in subjectCards"
          :key="card.id"
          class="x-course-card"
          :class="{ 'is-current': card.hasLP }"
        >
          <header class="x-course-card-head">
            <h3 class="x-course-card-name">{{ card.display_name }}</h3>
            <span v-if="card.hasLP" class="x-course-card-tag">当前画像</span>
          </header>
          <p class="x-course-card-code">{{ card.name }}</p>
          <footer class="x-course-card-foot">
            <span class="x-course-card-joined">
              加入于 {{ card.joinedAt.slice(0, 10) }}
            </span>
          </footer>
        </article>
      </div>
    </section>

    <!-- ============================================================
         学习统计 —— 4 数字, 全派生自当前 LP + mySubjects, 不造假
         跟 ReportsView 的 dashboard 互不重复 (那里是"全部学科的题数",
         这里是"当前选中学科的画像状态")
         ============================================================ -->
    <section class="x-section x-stats">
      <header class="x-stats-head">
        <p class="x-eyebrow x-eyebrow-mute">学径 ⏤ STATS</p>
        <h2 class="x-stats-title">学习统计</h2>
        <p class="x-stats-hint">{{ accountStatusText }}</p>
      </header>

      <div class="x-stats-grid">
        <div v-for="s in profileStats" :key="s.label" class="x-stat-card">
          <p class="x-eyebrow x-eyebrow-mute">{{ s.label }}</p>
          <p class="x-stat-card-value">{{ s.value }}</p>
          <p class="x-stat-card-hint">{{ s.hint }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
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

.x-profile {
  padding: 32px 40px 48px;
  /* max-width: 880px; */
  margin: 0 auto;
}

.x-profile-head {
  margin-bottom: 24px;
}
.x-title {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 8px 0;
}

.x-section {
  background: var(--x-canvas);
  border-radius: var(--x-rounded-md);
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--x-shadow-card);
}

/* === IDENTITY === */
.x-identity {
  display: flex;
  align-items: center;
  gap: 24px;
}
.x-avatar {
  position: relative;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  overflow: hidden;
  background: var(--x-primary);
  color: var(--x-on-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 0;
  cursor: pointer;
  font-family: var(--x-font-display);
  font-size: 36px;
  font-weight: 600;
}
.x-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.x-avatar-edit {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--x-ink);
  color: var(--x-canvas);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  border: 2px solid var(--x-canvas);
}
.x-identity-text {
  flex: 1;
  min-width: 0;
}
.x-identity-handle {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 6px 0 2px;
}
.x-identity-email {
  font-family: var(--x-font-mono);
  font-size: 12px;
  color: var(--x-body-mid);
  margin: 0;
}

/* === FORM === */
.x-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.x-form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.x-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-field-full {
  width: 100%;
}
.x-field-narrow {
  max-width: 140px;
}

.x-input {
  width: 100%;
  background: var(--x-canvas);
  color: var(--x-ink);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  padding: 9px 12px;
  font-family: var(--x-font-display);
  font-size: 14px;
  outline: none;
  transition: border-color 0.12s, background 0.12s;
}
.x-input::placeholder { color: var(--x-mute); }
.x-input:focus {
  border-color: var(--x-primary);
}
.x-input.is-error {
  border-color: var(--x-error);
}
.x-textarea {
  resize: vertical;
  font-family: var(--x-font-display);
  line-height: 1.5;
}
.x-field-error {
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-error);
  margin: 0;
}
.x-counter {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-mute);
  align-self: flex-end;
  margin: 0;
}
.x-hint {
  font-weight: 400;
  letter-spacing: 0.4px;
  text-transform: none;
  color: var(--x-mute);
}

/* === RADIO === */
.x-radio-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.x-radio {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border: 1px solid var(--x-ink-alpha-15);
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  font-size: 13px;
  color: var(--x-body);
  background: transparent;
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.x-radio input {
  /* hide native, keep accessible */
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.x-radio:hover {
  border-color: var(--x-ink-alpha-30);
  color: var(--x-ink);
}
.x-radio.is-checked {
  background: var(--x-primary-soft);
  color: var(--x-primary);
  border-color: var(--x-primary);
}
.x-clear-btn {
  background: transparent;
  border: 0;
  color: var(--x-mute);
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
}
.x-clear-btn:hover {
  color: var(--x-body);
}

/* === ACTIONS === */
.x-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--x-hairline);
  padding-top: 16px;
  margin-top: 8px;
}
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
}
.x-btn:active:not(:disabled) { transform: scale(0.98); }
.x-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: 1px solid var(--x-primary);
  padding: 9px 20px;
}
.x-btn-primary:hover:not(:disabled) {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
}
.x-btn-outline-sm {
  background: transparent;
  color: var(--x-ink);
  border: 1px solid var(--x-ink-alpha-15);
  padding: 7px 14px;
  font-size: 12px;
}
.x-btn-outline-sm:hover:not(:disabled) {
  background: var(--x-canvas-soft);
  border-color: var(--x-ink-alpha-30);
}

.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute { color: var(--x-body-mid); }

/* ============================================================
   LEARNING PROFILE section
   ============================================================ */
.x-lp { margin-top: 4px; }
.x-lp-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.x-lp-title {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 6px 0 4px;
}
.x-lp-hint {
  font-size: 12px;
  color: var(--x-body);
  margin: 0;
  max-width: 480px;
  line-height: 1.5;
}
.x-lp-hint-mute { color: var(--x-mute); }

.x-subject-pick {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-pill);
  padding: 7px 14px;
  font-family: var(--x-font-display);
  font-size: 13px;
  color: var(--x-ink);
  cursor: pointer;
  outline: none;
  transition: border-color 0.12s;
  max-width: 100%;
}
.x-subject-pick:hover { border-color: var(--x-ink-alpha-30); }
.x-subject-pick:focus { border-color: var(--x-primary); }

.x-lp-empty,
.x-lp-state {
  padding: 32px 16px;
  text-align: center;
  border: 1px dashed var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-soft);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.x-lp-empty-msg,
.x-lp-state-msg {
  font-size: 13px;
  color: var(--x-body);
  margin: 0;
}
.x-lp-state-error .x-lp-state-msg {
  color: var(--x-error);
  font-family: var(--x-font-mono);
}
.x-btn-link {
  background: transparent;
  border: 0;
  color: var(--x-primary);
  cursor: pointer;
  font-family: var(--x-font-mono);
  font-size: 12px;
  letter-spacing: 0.8px;
  padding: 6px 12px;
  border-radius: var(--x-rounded-pill);
  transition: background 0.12s;
}
.x-btn-link:hover:not(:disabled) { background: var(--x-primary-soft); }

.x-lp-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* === SLIDERS === */
.x-lp-scores {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px 24px;
  padding: 4px 0;
}
.x-slider-field { gap: 8px; }
.x-slider-row {
  display: flex;
  align-items: center;
  gap: 12px;
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
  margin: 0;
  padding: 0;
}
.x-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--x-primary);
  border: 2px solid var(--x-canvas);
  cursor: pointer;
  box-shadow: 0 1px 3px var(--x-ink-alpha-15);
  transition: transform 0.1s;
}
.x-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}
.x-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--x-primary);
  border: 2px solid var(--x-canvas);
  cursor: pointer;
  box-shadow: 0 1px 3px var(--x-ink-alpha-15);
}
.x-score-readout {
  min-width: 64px;
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-family: var(--x-font-mono);
}
.x-score-num {
  font-size: 14px;
  font-weight: 500;
  color: var(--x-ink);
  font-variant-numeric: tabular-nums;
  min-width: 28px;
  text-align: right;
}
.x-score-label {
  font-size: 10px;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--x-body-mid);
}

/* === CHIP PREVIEW (易错/兴趣) === */
.x-chip-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.x-chip {
  display: inline-flex;
  align-items: center;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  padding: 3px 10px;
  border-radius: var(--x-rounded-pill);
  font-size: 12px;
  font-family: var(--x-font-display);
}
.x-chip-warn {
  background: var(--x-error-soft);
  color: var(--x-error);
}

.x-lp-meta {
  font-size: 11px;
  color: var(--x-mute);
  margin: 4px 0 0;
}
.x-mono {
  font-family: var(--x-font-mono);
}

/* ============================================================
   "我的学科" + "学习统计" 两个新 section 的样式
   ============================================================ */

/* === 我的学科 === */
.x-courses {
  margin-top: 4px;
}
.x-courses-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.x-courses-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.2px;
  color: var(--x-ink);
  margin: 4px 0 4px;
}
.x-courses-hint {
  font-size: 12.5px;
  color: var(--x-body-mid);
  margin: 0;
  line-height: 1.5;
}
.x-courses-empty {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--x-body-mid);
  background: var(--x-canvas-soft);
  border: 1px dashed var(--x-hairline);
  border-radius: 10px;
}
.x-courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}
.x-course-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  background: var(--x-canvas-soft);
  border: 1px solid var(--x-hairline);
  border-radius: 10px;
  transition: border-color 0.15s, transform 0.15s;
}
.x-course-card:hover {
  border-color: var(--x-ink-alpha-30, var(--x-hairline));
  transform: translateY(-1px);
}
.x-course-card.is-current {
  border-color: var(--x-primary);
  background: var(--x-primary-soft);
}
.x-course-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.x-course-card-name {
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  margin: 0;
}
.x-course-card.is-current .x-course-card-name { color: var(--x-primary); }
.x-course-card-tag {
  font-size: 10px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.4px;
  padding: 2px 6px;
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-radius: 4px;
  font-weight: 600;
}
.x-course-card-code {
  font-size: 11px;
  font-family: var(--x-font-mono);
  color: var(--x-body-mid);
  margin: 0;
  letter-spacing: 0.4px;
}
.x-course-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 6px;
}
.x-course-card-joined {
  font-size: 11px;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
}

/* === 学习统计 4 数字 === */
.x-stats {
  margin-top: 4px;
}
.x-stats-head {
  margin-bottom: 16px;
}
.x-stats-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.2px;
  color: var(--x-ink);
  margin: 4px 0 4px;
}
.x-stats-hint {
  font-size: 12.5px;
  color: var(--x-body-mid);
  margin: 0;
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
}
.x-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.x-stat-card {
  padding: 16px 18px;
  background: var(--x-canvas-soft);
  border-radius: 10px;
  box-shadow: var(--x-shadow-card);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.x-stat-card-value {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--x-ink);
  line-height: 1.1;
  letter-spacing: -0.3px;
  margin: 2px 0 0;
  font-variant-numeric: tabular-nums;
  /* 长文本(比如"目标明确度" 4 字)不被挤压, 字号自适应 */
  word-break: break-all;
}
.x-stat-card-hint {
  font-size: 11px;
  font-family: var(--x-font-mono);
  letter-spacing: 0.2px;
  color: var(--x-body-mid);
  margin: 0;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .x-profile { padding: 24px 16px 40px; }
  .x-form-row { grid-template-columns: 1fr; }
  .x-identity { flex-direction: column; align-items: flex-start; }
  .x-lp-scores { grid-template-columns: 1fr; }
  .x-lp-head { flex-direction: column; align-items: stretch; }
  .x-courses-head { flex-direction: column; align-items: stretch; }
  .x-courses-grid { grid-template-columns: 1fr 1fr; }
  .x-stats-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 480px) {
  .x-courses-grid,
  .x-stats-grid { grid-template-columns: 1fr; }
}
</style>
