<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { loginUser, registerUser } from '@/api/user'
import { useUserStore } from '@/stores/user'
import type { LoginForm, RegisterForm } from '@/types'
import RotatingText from '@/components/effects/RotatingText.vue'
import HyperspeedBackground from '@/components/effects/HyperspeedBackground.vue'
import { IconCheck, IconGradCap } from '@/components/icons'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ── Tab state: login | register ───────────────────────────
type AuthTab = 'login' | 'register'
const activeTab = ref<AuthTab>('register')

// ── Rotating text words ────────────────────────────────────
const rotatingWords = ['编程', '建模', '设计', '动画']

// ============================================================
// LOGIN FORM
// ============================================================
const loginForm = reactive<LoginForm>({
  email: '',
  password: '',
})

const showPassword = ref(false)
const submitting = ref(false)
const touched = reactive({ email: false, password: false })
const rememberMe = ref(true)
const loginMethod = ref<'email' | 'phone'>('email')

// ── Validation ─────────────────────────────────────────────
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const loginErrors = computed(() => {
  const e: Partial<Record<keyof LoginForm, string>> = {}
  if (touched.email && !loginForm.email.trim()) {
    e.email = '请输入邮箱地址'
  } else if (touched.email && !emailRegex.test(loginForm.email)) {
    e.email = '请输入有效的邮箱地址'
  }
  if (touched.password && !loginForm.password) {
    e.password = '请输入密码'
  } else if (touched.password && loginForm.password.length < 6) {
    e.password = '密码至少 6 位'
  }
  return e
})

const canLogin = computed(() => {
  return (
    emailRegex.test(loginForm.email) &&
    loginForm.password.length >= 6 &&
    !submitting.value
  )
})

// ── Submit ─────────────────────────────────────────────────
async function handleLogin() {
  touched.email = true
  touched.password = true
  if (!canLogin.value) return

  submitting.value = true
  try {
    const { data } = await loginUser({
      email: loginForm.email.trim(),
      password: loginForm.password,
    })
    userStore.setAuth({
      access: data.access,
      refresh: data.refresh,
      user: data.user,
    })
    ElMessage({
      message: `欢迎回来, ${data.user.username || data.user.email}`,
      customClass: 'x-toast',
    })
    const redirect =
      typeof route.query.redirect === 'string' &&
      route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/app'
    await router.replace(redirect)
  } catch (err) {
    let msg = '网络异常 — 请检查后端服务'
    if (err instanceof AxiosError) {
      const body = err.response?.data as
        | { detail?: string; message?: string; non_field_errors?: string[] }
        | undefined
      msg =
        body?.detail ||
        body?.message ||
        body?.non_field_errors?.[0] ||
        (err.response?.status === 401 ? '邮箱或密码不正确' : err.message)
    } else if (err instanceof Error) {
      msg = err.message
    }
    ElMessage({ message: msg, customClass: 'x-toast' })
  } finally {
    submitting.value = false
  }
}

// ============================================================
// REGISTER FORM
// ============================================================
const regForm = reactive<RegisterForm>({
  email: '',
  username: '',
  password: '',
  confirmPassword: '',
})

const showRegPassword = ref(false)
const showRegConfirm = ref(false)
const agreed = ref(false)
const regTouched = reactive({
  email: false,
  username: false,
  password: false,
  confirmPassword: false,
})

const regErrors = computed(() => {
  const e: Partial<Record<keyof RegisterForm, string>> = {}

  if (regTouched.email && !regForm.email.trim()) {
    e.email = '请输入邮箱'
  } else if (regTouched.email && !emailRegex.test(regForm.email)) {
    e.email = '邮箱格式不正确'
  }

  if (regTouched.username && !regForm.username.trim()) {
    e.username = '请输入显示名'
  } else if (regTouched.username && regForm.username.length < 3) {
    e.username = '显示名至少 3 个字符'
  } else if (regTouched.username && !/^[a-zA-Z0-9_]+$/.test(regForm.username)) {
    e.username = '只允许字母、数字、下划线'
  }

  if (regTouched.password && !regForm.password) {
    e.password = '请输入密码'
  } else if (regTouched.password && regForm.password.length < 6) {
    e.password = '密码至少 6 位'
  }

  if (regTouched.confirmPassword && regForm.confirmPassword !== regForm.password) {
    e.confirmPassword = '两次密码不一致'
  }

  return e
})

const passwordStrength = computed(() => {
  const pw = regForm.password
  if (!pw) return { score: 0, label: '' }
  let s = 0
  if (pw.length >= 6) s++
  if (pw.length >= 10) s++
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++
  if (/[0-9]/.test(pw) && /[^A-Za-z0-9]/.test(pw)) s++
  const labels = ['过弱', '弱', '一般', '较强', '强']
  return { score: s, label: labels[s] ?? '' }
})

const canRegister = computed(() => {
  return (
    emailRegex.test(regForm.email) &&
    regForm.username.trim().length >= 3 &&
    regForm.password.length >= 6 &&
    regForm.confirmPassword === regForm.password &&
    agreed.value &&
    !submitting.value
  )
})

async function handleRegister() {
  regTouched.username = true
  regTouched.email = true
  regTouched.password = true
  regTouched.confirmPassword = true

  if (!agreed.value) {
    ElMessage({ message: '× 请先同意服务协议与隐私政策', customClass: 'x-toast' })
    return
  }
  if (!canRegister.value) return

  submitting.value = true
  try {
    const { data } = await registerUser({
      username: regForm.username.trim(),
      email: regForm.email.trim(),
      password: regForm.password,
      confirmPassword: regForm.confirmPassword,
    })

    if (data.user_id || data.message?.includes('成功')) {
      ElMessage({ message: '→ 注册成功, 请登录', customClass: 'x-toast' })
      activeTab.value = 'login'
      // pre-fill email
      loginForm.email = regForm.email
    } else {
      ElMessage({ message: `× ${data.message || '注册失败'}`, customClass: 'x-toast' })
    }
  } catch (err) {
    let msg = '网络异常 — 请检查后端服务'
    if (err instanceof AxiosError) {
      const body = err.response?.data as { message?: string; detail?: string } | undefined
      msg = body?.message || body?.detail || msg
    }
    ElMessage({ message: `× ${msg}`, customClass: 'x-toast' })
  } finally {
    submitting.value = false
  }
}

// ============================================================
// 校园 SSO 登录
// ============================================================
function handleCampusSSO() {
  ElMessage({
    message: '校园 SSO 暂未对接, 请使用邮箱密码登录或注册',
    customClass: 'x-toast',
  })
}
</script>

<template>
  <div class="auth-shell">
    <!-- ── Left: brand panel ─────────────────────────── -->
    <aside class="brand-panel">
      <HyperspeedBackground />

      <div class="brand-content">
        <!-- Logo -->
        <a class="brand-logo" @click="router.push('/')">
          <div class="brand-logo-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M7 8h10M7 12h7M7 16h4" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <span class="brand-logo-text">学径</span>
        </a>

        <!-- Headline with RotatingText -->
        <h1 class="brand-headline">
          学<RotatingText
            :texts="rotatingWords"
            :rotation-interval="2500"
            :stagger-duration="0.05"
            stagger-from="first"
            split-by="words"
            main-class-name="rotating-inline"
            split-level-class-name="rotating-word"
          />，上<span class="headline-pill">学径</span>！
        </h1>

        <p class="brand-slogan">有志者，学径成</p>

        <p class="brand-sub">
          由多个专业 AI Agent 协同驱动，基于知识图谱与检索增强，为每位学习者构建专属学习路径。
        </p>

        <!-- Feature cards -->
        <div class="brand-features">
          <div class="brand-feature">
            <div class="brand-feature-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="5" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                <circle cx="13" cy="5" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                <circle cx="9" cy="14" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                <path d="M7 6l2 6M11 6l-2 6" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="brand-feature-body">
              <div class="brand-feature-title">智能体协同</div>
              <div class="brand-feature-desc">8 个专业 Agent 覆盖画像、规划、出题、答疑、评估全流程</div>
            </div>
          </div>
          <div class="brand-feature">
            <div class="brand-feature-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M3 9l3 3 9-9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M3 15h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="brand-feature-body">
              <div class="brand-feature-title">知识星图驱动</div>
              <div class="brand-feature-desc">基于 DAG 学习路径 + 向量检索，精准定位知识缺口</div>
            </div>
          </div>
          <div class="brand-feature">
            <div class="brand-feature-icon">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <rect x="2" y="3" width="14" height="10" rx="2" stroke="currentColor" stroke-width="1.5"/>
                <path d="M6 16h6M9 13v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="7" cy="8" r="1.5" stroke="currentColor" stroke-width="1"/>
                <path d="M11 7h3M11 9h2" stroke="currentColor" stroke-width="1" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="brand-feature-body">
              <div class="brand-feature-title">多模态交互</div>
              <div class="brand-feature-desc">支持文字、代码、图片、语音等多种答题方式</div>
            </div>
          </div>
        </div>
      </div>

      <div class="brand-footer">v2.0 · Powered by LangGraph + RAG</div>
    </aside>

    <!-- ── Right: form panel ─────────────────────────── -->
    <main class="form-panel">
      <!-- Mobile brand -->
      <a class="mobile-brand" @click="router.push('/')">
        <span class="brand-logo-icon mobile-logo">学</span>
        <span>学径</span>
      </a>

      <div class="form-wrap">
        <!-- Welcome -->
        <div class="form-welcome">
          <h2>{{ activeTab === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ activeTab === 'login' ? '登录你的账号，继续学习旅程' : '注册账号，开始学习之旅' }}</p>
        </div>

        <!-- Auth tabs: login | register -->
        <div class="auth-tabs">
          <button
            class="auth-tab"
            :class="{ active: activeTab === 'login' }"
            @click="activeTab = 'login'"
          >登录</button>
          <button
            class="auth-tab"
            :class="{ active: activeTab === 'register' }"
            @click="activeTab = 'register'"
          >注册</button>
        </div>

        <!-- ── Login form ─────────────────────────────────── -->
        <form
          v-show="activeTab === 'login'"
          class="auth-form"
          @submit.prevent="handleLogin"
          novalidate
        >
          <div class="field" :class="{ 'has-error': loginErrors.email }">
            <label class="field-label">邮箱地址</label>
            <input
              class="field-input"
              :class="{ error: loginErrors.email }"
              type="email"
              placeholder="your@university.edu"
              autocomplete="email"
              spellcheck="false"
              v-model="loginForm.email"
              @blur="touched.email = true"
            />
            <div v-if="loginErrors.email" class="field-error">{{ loginErrors.email }}</div>
          </div>

          <div class="field" :class="{ 'has-error': loginErrors.password }">
            <label class="field-label">密码</label>
            <div class="field-pw-wrap">
              <input
                class="field-input"
                :class="{ error: loginErrors.password }"
                :type="showPassword ? 'text' : 'password'"
                placeholder="输入密码"
                autocomplete="current-password"
                v-model="loginForm.password"
                @blur="touched.password = true"
              />
              <button
                type="button"
                class="field-pw-toggle"
                @click="showPassword = !showPassword"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              >
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M2 9s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>
            </div>
            <div v-if="loginErrors.password" class="field-error">{{ loginErrors.password }}</div>
          </div>

          <div class="check-row">
            <label class="check-label">
              <input type="checkbox" v-model="rememberMe" /> 记住登录状态
            </label>
            <a class="check-link">忘记密码？</a>
          </div>

          <button
            class="btn-submit"
            :class="{ loading: submitting }"
            type="submit"
            :disabled="!canLogin"
          >
            <span v-if="!submitting" class="btn-text">登 录</span>
            <span v-else class="spinner"></span>
          </button>
        </form>

        <!-- ── Register form ──────────────────────────────── -->
        <form
          v-show="activeTab === 'register'"
          class="auth-form"
          @submit.prevent="handleRegister"
          novalidate
        >
          <div class="field" :class="{ 'has-error': regErrors.email }">
            <label class="field-label">邮箱</label>
            <input
              class="field-input"
              :class="{ error: regErrors.email }"
              type="email"
              autocomplete="email"
              spellcheck="false"
              v-model="regForm.email"
              @blur="regTouched.email = true"
              placeholder="name@example.com"
            />
            <div v-if="regErrors.email" class="field-error">{{ regErrors.email }}</div>
          </div>

          <div class="field" :class="{ 'has-error': regErrors.username }">
            <label class="field-label">显示名</label>
            <input
              class="field-input"
              :class="{ error: regErrors.username }"
              type="text"
              autocomplete="username"
              spellcheck="false"
              v-model="regForm.username"
              @blur="regTouched.username = true"
              placeholder="3-20 个字符, 字母数字下划线"
            />
            <div v-if="regErrors.username" class="field-error">{{ regErrors.username }}</div>
          </div>

          <div class="field" :class="{ 'has-error': regErrors.password }">
            <label class="field-label">密码</label>
            <div class="field-pw-wrap">
              <input
                class="field-input"
                :class="{ error: regErrors.password }"
                :type="showRegPassword ? 'text' : 'password'"
                autocomplete="new-password"
                v-model="regForm.password"
                @blur="regTouched.password = true"
                placeholder="至少 6 位"
              />
              <button
                type="button"
                class="field-pw-toggle"
                @click="showRegPassword = !showRegPassword"
                :aria-label="showRegPassword ? '隐藏密码' : '显示密码'"
              >
                <svg v-if="!showRegPassword" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M2 9s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M3 3l12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <path d="M6.5 6.5a2.5 2.5 0 003.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <path d="M2 9s2.5-5 7-5c1.5 0 2.8.4 3.9 1.1M16 9s-2.5 5-7 5c-1.5 0-2.8-.4-3.9-1.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
            <!-- Password strength bar -->
            <div v-if="regForm.password" class="strength-bar">
              <div class="strength-bars">
                <div
                  v-for="i in 4"
                  :key="i"
                  class="strength-segment"
                  :class="{ active: i <= passwordStrength.score }"
                  :style="i <= passwordStrength.score ? { background: ['#dc2626','#f59e0b','#3b82f6','#22c55e'][passwordStrength.score - 1] } : {}"
                ></div>
              </div>
              <span class="strength-label" :style="{ color: ['#dc2626','#f59e0b','#3b82f6','#22c55e'][passwordStrength.score - 1] || '' }">
                {{ passwordStrength.label }}
              </span>
            </div>
            <div v-if="regErrors.password" class="field-error">{{ regErrors.password }}</div>
          </div>

          <div class="field" :class="{ 'has-error': regErrors.confirmPassword }">
            <label class="field-label">确认密码</label>
            <div class="field-pw-wrap">
              <input
                class="field-input"
                :class="{ error: regErrors.confirmPassword }"
                :type="showRegConfirm ? 'text' : 'password'"
                autocomplete="new-password"
                v-model="regForm.confirmPassword"
                @blur="regTouched.confirmPassword = true"
                placeholder="再输一次密码"
              />
              <button
                type="button"
                class="field-pw-toggle"
                @click="showRegConfirm = !showRegConfirm"
                :aria-label="showRegConfirm ? '隐藏密码' : '显示密码'"
              >
                <svg v-if="!showRegConfirm" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M2 9s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" stroke="currentColor" stroke-width="1.5"/>
                  <circle cx="9" cy="9" r="2.5" stroke="currentColor" stroke-width="1.5"/>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M3 3l12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <path d="M6.5 6.5a2.5 2.5 0 003.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                  <path d="M2 9s2.5-5 7-5c1.5 0 2.8.4 3.9 1.1M16 9s-2.5 5-7 5c-1.5 0-2.8-.4-3.9-1.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
            <div v-if="regErrors.confirmPassword" class="field-error">{{ regErrors.confirmPassword }}</div>
          </div>

          <!-- Agreement -->
          <label class="check-label" style="user-select:none; cursor:pointer; margin-bottom: 8px;">
            <input type="checkbox" v-model="agreed" />
            <span style="font-size:13px; color:var(--x-body-mid);">
              我已阅读并同意 <a class="check-link" style="font-size:13px;">服务协议</a> 与
              <a class="check-link" style="font-size:13px;">隐私政策</a>
            </span>
          </label>

          <button
            class="btn-submit"
            :class="{ loading: submitting }"
            type="submit"
            :disabled="!canRegister"
          >
            <span v-if="!submitting" class="btn-text">注 册</span>
            <span v-else class="spinner"></span>
          </button>
        </form>

        <!-- Divider (only show in login tab) -->
        <div v-show="activeTab === 'login'" class="divider"><span>或通过以下方式登录</span></div>

        <!-- 校园 SSO (only show in login tab) -->
        <div v-show="activeTab === 'login'" class="sso-row">
          <button class="btn-sso btn-sso-campus" type="button" @click="handleCampusSSO">
            <IconGradCap :size="18" />
            <span>校园 SSO 登录</span>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ── Layout ──────────────────────────────────────────── */
.auth-shell {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  background: var(--x-canvas);
  color: var(--x-ink);
}

/* ── Left: brand panel ───────────────────────────────── */
.brand-panel {
  position: relative;
  overflow: hidden;
  padding: 80px 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #0a1628;
  color: #fff;
}

.brand-content {
  position: relative;
  z-index: 1;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 48px;
  cursor: pointer;
  color: inherit;
}
.brand-logo-icon {
  position: relative;
  isolation: isolate;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--x-primary);
  display: grid;
  place-items: center;
  color: #fff;
  font: 700 22px/1 var(--x-font-display);
  box-shadow: 0 0 40px rgba(30, 90, 224, 0.4);
  flex-shrink: 0;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.brand-logo-icon:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 50px rgba(30, 90, 224, 0.55);
}

.brand-logo-icon::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 16px;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(255, 255, 255, 0.55) 90deg,
    transparent 180deg,
    transparent 360deg
  );
  opacity: 0.75;
  z-index: -1;
  animation: x-brand-mark-spin 4s linear infinite;
}

.brand-logo-icon::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 14px;
  background: radial-gradient(
    circle at center,
    rgba(96, 165, 250, 0.45) 0%,
    transparent 70%
  );
  z-index: -1;
  animation: x-brand-mark-pulse 2.4s ease-in-out infinite;
}

@keyframes x-brand-mark-spin {
  to { transform: rotate(360deg); }
}

@keyframes x-brand-mark-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.55;
  }
  50% {
    transform: scale(1.20);
    opacity: 0.95;
  }
}
.brand-logo-text {
  font: 700 28px/1 var(--x-font-display);
  color: #fff;
  letter-spacing: -0.02em;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
}

/* Headline */
.brand-headline {
  font: 700 46px/1.18 var(--x-font-display);
  color: #fff;
  letter-spacing: -0.03em;
  margin-bottom: 26px;
  max-width: 540px;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.28);
}

.rotating-inline {
  display: inline-flex;
  overflow: hidden;
  height: calc(1.18em + 6px);
  align-items: center;
  margin: 0 2px;
  vertical-align: baseline;
}
.rotating-inline :deep(span) {
  display: inline-flex;
}
.rotating-inline :deep(.rotating-word) {
  background: linear-gradient(135deg, #1e5ae0 0%, #5b8def 100%);
  border-radius: 8px;
  padding: 2px 12px;
  color: #fff;
  font-weight: 800;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.18);
}

.headline-pill {
  font-weight: 800;
  padding: 0 2px;
  background: linear-gradient(135deg, #93c5fd 0%, #c4b5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-slogan {
  position: relative;
  font: 600 23px/1.4 var(--x-font-display);
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: 0.06em;
  margin-bottom: 16px;
  margin-left: 20px;
  background: linear-gradient(90deg, #60a5fa 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.brand-slogan::before {
  content: '';
  position: absolute;
  left: -20px;
  top: 0.25em;
  bottom: 0.25em;
  width: 3px;
  border-radius: 2px;
  background: linear-gradient(180deg, #60a5fa 0%, #c084fc 100%);
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.6);
}

.brand-sub {
  font: 400 16px/1.78 var(--x-font-display);
  color: rgba(255, 255, 255, 0.7);
  max-width: 460px;
  margin-bottom: 56px;
  letter-spacing: 0.01em;
}

/* Feature cards */
.brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.brand-feature {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 20px;
  border-radius: var(--x-rounded-md);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
  max-width: 440px;
}
.brand-feature-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(30, 90, 224, 0.2);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: #60a5fa;
}
.brand-feature-body { flex: 1; }
.brand-feature-title {
  font: 600 14.5px/1.3 var(--x-font-display);
  color: rgba(255, 255, 255, 0.96);
  margin-bottom: 5px;
  letter-spacing: 0.01em;
}
.brand-feature-desc {
  font: 400 12.5px/1.55 var(--x-font-display);
  color: rgba(255, 255, 255, 0.56);
  letter-spacing: 0.01em;
}

/* Footer */
.brand-footer {
  position: absolute;
  bottom: 40px;
  left: 72px;
  z-index: 2;
  font: 400 11.5px/1 var(--x-font-mono);
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* ── Right: form panel ───────────────────────────────── */
.form-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: var(--x-canvas);
  position: relative;
}

.form-wrap {
  width: 100%;
  max-width: 420px;
}

/* Welcome */
.form-welcome {
  margin-bottom: 24px;
}
.form-welcome h2 {
  font: 700 28px/1.3 var(--x-font-display);
  color: var(--x-ink);
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}
.form-welcome p {
  font: 400 14.5px/1.5 var(--x-font-display);
  color: var(--x-body-mid);
}

/* Auth tabs */
.auth-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 24px;
  border-bottom: 1.5px solid var(--x-hairline);
  padding-bottom: 0;
}
.auth-tab {
  padding: 6px 16px;
  font: 600 14px/1 var(--x-font-display);
  color: var(--x-body-mid);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1.5px;
}
.auth-tab:hover {
  color: var(--x-ink);
}
.auth-tab.active {
  color: var(--x-primary);
  border-bottom-color: var(--x-primary);
}

/* Form */
.auth-form {
  display: flex;
  flex-direction: column;
}

.field {
  margin-bottom: 16px;
}
.field-label {
  display: block;
  font: 500 13px/1 var(--x-font-display);
  color: var(--x-ink);
  margin-bottom: 7px;
}
.field-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1.5px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  font: 400 14.5px/1 var(--x-font-display);
  color: var(--x-ink);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input::placeholder {
  color: var(--x-mute);
}
.field-input:focus {
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px rgba(30, 90, 224, 0.1);
}
.field-input.error {
  border-color: var(--x-danger);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.08);
}
.field-error {
  font: 400 12px/1.4 var(--x-font-display);
  color: var(--x-danger);
  margin-top: 6px;
}

/* Password toggle */
.field-pw-wrap {
  position: relative;
}
.field-pw-wrap .field-input {
  padding-right: 44px;
}
.field-pw-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  color: var(--x-body-mid);
  display: grid;
  place-items: center;
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  transition: all 0.15s;
}
.field-pw-toggle:hover {
  color: var(--x-ink);
  background: var(--x-canvas-soft);
}

/* Strength bar */
.strength-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}
.strength-bars {
  display: flex;
  gap: 4px;
  flex: 1;
}
.strength-segment {
  flex: 1;
  height: 3px;
  border-radius: 999px;
  background: var(--x-hairline);
  transition: background 0.2s;
}
.strength-label {
  font-size: 11px;
  font-weight: 600;
  min-width: 28px;
  text-align: right;
}

/* Check row */
.check-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.check-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font: 400 13px/1 var(--x-font-display);
  color: var(--x-body-mid);
  cursor: pointer;
  user-select: none;
}
.check-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--x-primary);
}
.check-link {
  font: 500 13px/1 var(--x-font-display);
  color: var(--x-primary);
  cursor: pointer;
  transition: opacity 0.15s;
}
.check-link:hover {
  opacity: 0.8;
}

/* Submit */
.btn-submit {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: var(--x-rounded-md);
  background: var(--x-primary);
  color: #fff;
  font: 600 15px/1 var(--x-font-display);
  letter-spacing: -0.01em;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}
.btn-submit:hover:not(:disabled) {
  filter: brightness(1.08);
  box-shadow: 0 4px 16px rgba(30, 90, 224, 0.25);
}
.btn-submit:active:not(:disabled) {
  filter: brightness(0.95);
}
.btn-submit:disabled {
  opacity: 0.5;
  cursor: default;
  filter: none;
  box-shadow: none;
}
.btn-submit .spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
.btn-submit.loading .btn-text { display: none; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Divider */
.divider {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 24px 0;
}
.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--x-hairline);
}
.divider span {
  font: 400 12.5px/1 var(--x-font-display);
  color: var(--x-body-mid);
  white-space: nowrap;
}

/* SSO */
.sso-row {
  display: flex;
  gap: 12px;
}
.btn-sso {
  flex: 1;
  height: 44px;
  border: 1.5px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font: 500 13.5px/1 var(--x-font-display);
  color: var(--x-ink);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-sso:hover {
  border-color: var(--x-hairline-strong);
  background: var(--x-canvas-soft);
}
.btn-sso svg {
  flex-shrink: 0;
}

/* Campus SSO — 主推入口, 用主色强调 */
.btn-sso-campus {
  gap: 10px;
  font: 500 14px/1 var(--x-font-display);
  color: var(--x-primary);
  border-color: rgba(30, 90, 224, 0.28);
  background: linear-gradient(180deg, #ffffff 0%, #f3f6ff 100%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset, 0 1px 2px rgba(30, 90, 224, 0.06);
  position: relative;
}
.btn-sso-campus::before {
  content: '推荐';
  position: absolute;
  top: -8px;
  right: 12px;
  font: 600 10px/1 var(--x-font-display);
  color: #fff;
  background: var(--x-primary);
  padding: 3px 7px;
  border-radius: 999px;
  letter-spacing: 0.04em;
}
.btn-sso-campus:hover {
  border-color: var(--x-primary);
  background: linear-gradient(180deg, #ffffff 0%, #e7eeff 100%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.6) inset, 0 2px 8px rgba(30, 90, 224, 0.14);
}

/* ── Mobile brand ────────────────────────────────────── */
.mobile-brand {
  display: none;
  align-items: center;
  gap: 10px;
  position: absolute;
  top: 24px;
  left: 24px;
  cursor: pointer;
  color: var(--x-ink);
  font: 600 15px/1 var(--x-font-display);
}
.mobile-logo {
  width: 32px;
  height: 32px;
  font-size: 16px;
  border-radius: 8px;
  box-shadow: none;
}

/* ── Responsive ──────────────────────────────────────── */
@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }
  .brand-panel {
    display: none;
  }
  .mobile-brand {
    display: flex;
  }
  .form-panel {
    min-height: 100vh;
    padding-top: 80px;
  }
}

@media (max-width: 480px) {
  .form-panel {
    padding: 80px 16px 32px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none !important;
  }
}
</style>
