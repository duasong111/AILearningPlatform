<script setup lang="ts">
/**
 * 课程 Onboarding 页面 - 左右分栏
 *
 *   路由: /course-onboarding/:code
 *   布局: 左侧课程卡片与介绍，右侧画像对话
 *   功能: 完成画像对话后进入课程学习
 */

import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { SUBJECT_CHOICES, addSubject, removeSubject, getSubjectDisplayName } from '@/api/subjects'
import { getProfile, completeProfile } from '@/api/profile'
import { listPlans } from '@/api/plan'
import { createConversation, listConversations, deleteConversation } from '@/api/conversations'
import { useConvWS, type WSStatus } from '@/composables/use_conv_ws'
import { useMySubjectsStore } from '@/stores/mySubjects'
import { useOnboardingStore } from '@/stores/onboarding'
import { useCurrentSubjectStore } from '@/stores/currentSubject'
import { SUBJECT_COVERS } from '@/data/subject-covers'
import type { SubjectCode } from '@/types/learning'
import type { ChatMessage, WSInboundEvent, PersistedMessage } from '@/types/chat'
import { IconArrow, IconCheck, IconChat, IconCross, IconHourglass, IconSparkle } from '@/components/icons'
import BlurText from '@/components/BlurText.vue'

const router = useRouter()
const route = useRoute()
const mySubjects = useMySubjectsStore()
const onboarding = useOnboardingStore()
const currentSubject = useCurrentSubjectStore()

// ─── state ────────────────────────────────────────────────
const subjectCode = computed(() => route.params.code as string)
const subjectInfo = computed(() => SUBJECT_CHOICES.find(s => s.code === subjectCode.value))
const subjectId = ref<number | null>(null)
const addingCode = ref<boolean>(false)
const lastError = ref<string>('')
const conversationId = ref<number | null>(null)
const profileMessages = ref<ChatMessage[]>([])
const draftInput = ref<string>('')
const sending = ref<boolean>(false)
const completing = ref<boolean>(false)
const isComplete = ref<boolean>(false)
const suggestions = ref<string[]>([])
const chatListRef = ref<HTMLElement | null>(null)
const buildDone = ref<boolean>(false)
// ai message id -> pending 状态
const pendingMap = ref<Record<number, boolean>>({})

// ws 相关
let ws: ReturnType<typeof useConvWS> | null = null
const wsStatus = ref<WSStatus>('idle')

// ─── 课程数据 ────────────────────────────────────────────
const SUBJECT_DESCS: Record<string, string> = {
  data_structure: '树、图、排序，与数据组织的艺术。',
  cybersecurity: '攻防、加密，与数字世界的安全守则。',
  iot: '传感器、嵌入式，与万物互联的蓝图。',
  electrical_automation: '语法、并发、生态，与 Python 编程的全景。',
  mechanical_design: '进程、内存、文件系统，与计算机操作系统的核心。',
  advanced_math: '需求、设计、测试、DevOps，与软件工程的全景。',
  artificial_intelligence: '神经网络、深度学习，与智能的边界。',
}

const SUBJECT_FULL_DESCS: Record<string, string> = {
  data_structure: '深入研究计算机科学的核心数据结构与算法。从线性表到树形结构，从图论到动态规划，掌握高效组织和处理数据的方法论。',
  cybersecurity: '探索网络空间安全的攻防技术。学习密码学原理、漏洞分析、渗透测试和安全防护，构建数字世界的安全防线。',
  iot: '理解物联网的完整技术栈。从传感器硬件到通信协议，从边缘计算到云平台，掌握万物互联的系统设计能力。',
  electrical_automation: '系统掌握 Python 编程语言。从基础语法到面向对象、并发异步、元类与描述符、内存管理到标准库与 Web/Django/FastAPI 生态。',
  mechanical_design: '系统掌握操作系统的原理与实践。从进程/线程管理、内存管理、文件系统到网络协议栈、内核子系统、同步原语与虚拟化，覆盖 Linux/macOS/Windows 共用知识。',
  advanced_math: '系统掌握软件工程的方法论。从需求工程、SOLID 原则、GoF 23 设计模式、分层/微服务架构、CI/CD、测试金字塔到敏捷方法与质量度量，覆盖工程实践全周期。',
  artificial_intelligence: '探索人工智能的前沿技术。学习机器学习、深度学习、自然语言处理和计算机视觉，理解智能系统的构建原理。',
}

const COVER_COLORS: Record<string, string> = {
  data_structure: 'oklch(22% 0.04 250)',
  cybersecurity: 'oklch(50% 0.20 260)',
  iot: 'oklch(40% 0.10 195)',
  electrical_automation: 'oklch(45% 0.20 280)',  // Python 紫蓝色, 跟默认 data_structure 区分
  mechanical_design: 'oklch(35% 0.15 230)',  // 操作系统 — 蓝绿色
  advanced_math: 'oklch(50% 0.18 30)',    // 软件工程 — 暖橙红色
  artificial_intelligence: 'oklch(60% 0.20 245)',
}

// ─── helpers ──────────────────────────────────────────────
function getCoverBg(): string {
  return COVER_COLORS[subjectCode.value] || 'oklch(22% 0.04 250)'
}

function getSubjectDesc(): string {
  return SUBJECT_DESCS[subjectCode.value] || ''
}

function getSubjectFullDesc(): string {
  return SUBJECT_FULL_DESCS[subjectCode.value] || ''
}

// ─── 初始化课程 ──────────────────────────────────────────
async function initSubject(): Promise<void> {
  addingCode.value = true
  lastError.value = ''
  try {
    const { data } = await addSubject(subjectCode.value)
    subjectId.value = data.id
    const existing = mySubjects.subjects.find((s) => s.name === data.name)
    if (!existing) mySubjects.subjects.push(data)
    currentSubject.set(data.name as SubjectCode)
    await openProfileConversation(data.id)
  } catch (err: unknown) {
    // 处理 409 Conflict（课程已存在）
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { status?: number; data?: { subject?: { id?: number } } } }
      if (axiosErr.response?.status === 409 && axiosErr.response.data?.subject?.id) {
        // 课程已存在，直接使用现有的 subject
        subjectId.value = axiosErr.response.data.subject.id
        const existing = mySubjects.subjects.find((s) => s.name === subjectCode.value)
        if (!existing) {
          // 重新加载课程列表
          await mySubjects.loadFromBackend()
        }
        currentSubject.set(subjectCode.value as SubjectCode)
        await openProfileConversation(axiosErr.response.data.subject.id)
        return
      }
    }
    lastError.value = err instanceof Error ? err.message : 'Add subject failed'
  } finally {
    addingCode.value = false
  }
}

async function openProfileConversation(subjectId: number): Promise<void> {
  try {
    const list = await listConversations({ subject: subjectId, agent: 'profile' })
    let conv: { id: number; title: string; agent: string } | undefined = list.data[0]
    if (!conv) {
      const created = await createConversation({
        subject_id: subjectId,
        title: '画像构建',
        agent: 'profile',
      })
      conv = { id: created.data.id, title: created.data.title, agent: 'profile' }
    }
    if (!conv) return   // exhaustive: 让 TS 知道下面 conv 一定有值
    conversationId.value = conv.id

    ws = useConvWS({
      onEvent: handleWSEvent,
      onClose: (reason) => {
        wsStatus.value = 'closed'
        if (!reason.clean && reason.code !== 1000) {
          lastError.value = `对话连接断开 (${reason.code})`
        }
      },
    })
    wsStatus.value = 'connecting'
    await ws.connect(conv.id, 'profile')
    wsStatus.value = 'open'
  } catch (err) {
    lastError.value = err instanceof Error ? err.message : 'Open conversation failed'
  }
}

// ─── WS 事件处理 ──────────────────────────────────────────
function handleWSEvent(ev: WSInboundEvent): void {
  if (ev.type === 'history') {
    profileMessages.value = ev.messages.map(toChatMessage)
    scrollChatToBottom()
  } else if (ev.type === 'accepted') {
    profileMessages.value.push(toChatMessage(ev.user_message))
    scrollChatToBottom()
  } else if (ev.type === 'chunk') {
    pendingMap.value[ev.ai_message_id] = true
    appendOrCreateAssistant(ev.ai_message_id, ev.content, false)
  } else if (ev.type === 'resume') {
    appendOrCreateAssistant(ev.ai_message_id, ev.content, true)
  } else if (ev.type === 'complete') {
    pendingMap.value[ev.ai_message_id] = false
    appendOrCreateAssistant(ev.ai_message_id, ev.content, true)
    if (ev.meta) {
      if (typeof ev.meta.is_complete === 'boolean') {
        isComplete.value = ev.meta.is_complete
      }
      if (Array.isArray(ev.meta.suggestions)) {
        suggestions.value = ev.meta.suggestions.filter((s: unknown) => typeof s === 'string')
      }
    }
  } else if (ev.type === 'error') {
    lastError.value = ev.message
  } else if (ev.type === 'state') {
    if (ev.ai_state === 'generating' && ev.current_ai_message_id) {
      ensureAssistantBubble(ev.current_ai_message_id)
    }
  }
}

function toChatMessage(m: PersistedMessage): ChatMessage {
  // 后端 PersistedMessage 是历史持久化格式 (id:number, role, created_at),
  // 前端 ChatMessage 用 id:string + kind + ts. 字段映射 + 类型转换.
  return {
    id: String(m.id),
    kind: m.role,
    content: m.content,
    ts: m.created_at,
  }
}

function ensureAssistantBubble(aiId: number): void {
  const aiIdStr = String(aiId)
  const existing = profileMessages.value.find((m) => m.id === aiIdStr)
  if (!existing) {
    profileMessages.value.push({
      id: aiIdStr,
      kind: 'assistant',
      content: '',
      ts: new Date().toISOString(),
    })
  }
}

function appendOrCreateAssistant(aiId: number, content: string, replace: boolean): void {
  const aiIdStr = String(aiId)
  const existing = profileMessages.value.find((m) => m.id === aiIdStr)
  if (existing) {
    if (replace) existing.content = content
    else existing.content += content
  } else {
    profileMessages.value.push({
      id: aiIdStr,
      kind: 'assistant',
      content,
      ts: new Date().toISOString(),
    })
  }
  scrollChatToBottom()
}

function scrollChatToBottom(): void {
  requestAnimationFrame(() => {
    const el = chatListRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

// ─── 发送消息 ──────────────────────────────────────────────
function sendMessage(): void {
  if (!ws || !conversationId.value || !draftInput.value.trim()) return
  sending.value = true
  suggestions.value = []
  try {
    ws.send({ type: 'message', content: draftInput.value })
    draftInput.value = ''
  } catch (err) {
    lastError.value = err instanceof Error ? err.message : 'Send failed'
  } finally {
    sending.value = false
  }
}

function sendSuggestion(text: string): void {
  if (!ws || !conversationId.value || !text.trim()) return
  sending.value = true
  suggestions.value = []
  try {
    ws.send({ type: 'message', content: text })
  } catch (err) {
    lastError.value = err instanceof Error ? err.message : 'Send failed'
  } finally {
    sending.value = false
  }
}

const canSubmitProfile = computed(
  () => wsStatus.value === 'open' && draftInput.value.trim().length > 0 && !sending.value,
)

// ─── 完成 ──────────────────────────────────────────────────
async function finishOnboarding(): Promise<void> {
  completing.value = true
  try {
    if (isComplete.value) {
      await completeProfile(subjectCode.value)
      await onboarding.markOnboarded(subjectCode.value)
      buildDone.value = true
      await playBuildAnimation()
      return
    }
    const { data } = await getProfile(subjectCode.value)
    if (!data.is_complete) {
      ElMessage({ message: '画像尚未完成，请继续与助手对话', type: 'warning', customClass: 'x-toast' })
      return
    }
    await onboarding.markOnboarded(subjectCode.value)
    buildDone.value = true
    await playBuildAnimation()
  } catch (err) {
    lastError.value = err instanceof Error ? err.message : 'Check failed'
  } finally {
    completing.value = false
  }
}

interface BuildStep {
  label: string
  detail: string
  done: boolean
  active: boolean
}
const buildSteps = ref<BuildStep[]>([
  { label: '分析学习画像', detail: '提取学习目标、基础水平、时间安排等维度', done: false, active: false },
  { label: '匹配知识图谱', detail: '根据画像匹配课程知识点和难度', done: false, active: false },
  { label: '生成学习计划', detail: '按知识点展开 5 步学习流程', done: false, active: false },
  { label: '规划学习路径', detail: '确定执行 Agent 和前置提示词', done: false, active: false },
])

async function playBuildAnimation(): Promise<void> {
  // 前 3 步按固定节奏推进 (分析画像 → 匹配图谱 → 生成计划)
  for (let i = 0; i < buildSteps.value.length - 1; i++) {
    const step = buildSteps.value[i]
    if (!step) continue
    step.active = true
    await new Promise(r => setTimeout(r, 800 + Math.random() * 600))
    step.active = false
    step.done = true
  }

  // 最后一步 (规划学习路径) 持续转圈, 轮询等待 Celery task 完成
  const lastIdx = buildSteps.value.length - 1
  const lastStep = buildSteps.value[lastIdx]
  if (lastStep) lastStep.active = true

  const POLL_INTERVAL = 2000
  const MAX_WAIT = 30000
  const start = Date.now()
  let plansReady = false

  while (Date.now() - start < MAX_WAIT) {
    try {
      const { data } = await listPlans(subjectCode.value as any)
      if (data.length > 0) {
        plansReady = true
        break
      }
    } catch {
      // 计划还没生成, 继续轮询
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL))
  }

  if (lastStep) {
    lastStep.active = false
    lastStep.done = true
  }
  await new Promise(r => setTimeout(r, 400))

  if (!plansReady) {
    // 超时兜底: 计划可能仍在后台生成, 不阻塞用户
    ElMessage({ message: '学习计划仍在生成中，稍后可在计划页查看', type: 'info', customClass: 'x-toast' })
  }

  const hadCourses = mySubjects.subjects.length > 1
  router.replace(hadCourses ? '/app/plan/courses' : '/app/home')
}

function goBack(): void {
  router.push('/course-select')
}

// ─── cleanup: 画像未完成时删除对话和学科 ──────────────────
async function cleanupIncompleteOnboarding(): Promise<void> {
  if (isComplete.value) return // 画像已完成，不需要清理

  // 删除对话
  if (conversationId.value) {
    try {
      await deleteConversation(conversationId.value)
    } catch {
      // ignore
    }
  }

  // 删除学科对象
  if (subjectId.value) {
    try {
      await removeSubject(subjectId.value)
      // 从 store 中移除
      mySubjects.subjects = mySubjects.subjects.filter(s => s.id !== subjectId.value)
    } catch {
      // ignore
    }
  }
}

// ─── lifecycle ────────────────────────────────────────────
onMounted(async () => {
  await mySubjects.loadFromBackend().catch(() => undefined)
  if (!subjectInfo.value) {
    router.replace('/course-select')
    return
  }
  await initSubject()
})

onBeforeUnmount(async () => {
  // 关闭 WS
  if (ws) {
    try { ws.close() } catch { /* noop */ }
    ws = null
  }
  // 画像未完成时清理对话和学科
  await cleanupIncompleteOnboarding()
})
</script>

<template>
  <div class="x-co">
    <!-- 左侧：课程卡片与介绍 -->
    <aside class="x-co-left">
      <div class="x-co-card" :style="{ background: getCoverBg() }">
        <img
          v-if="SUBJECT_COVERS[subjectCode]"
          :src="SUBJECT_COVERS[subjectCode]"
          :alt="subjectInfo?.name"
          class="x-co-card-img"
        />
        <div class="x-co-card-overlay">
          <span class="x-co-card-num">0{{ SUBJECT_CHOICES.findIndex(s => s.code === subjectCode) + 1 }}</span>
        </div>
        <div class="x-co-card-meta">
          <span>{{ subjectCode }}</span>
          <span>计算机科学</span>
        </div>
      </div>
      <div class="x-co-info">
        <h1 class="x-co-title">{{ subjectInfo?.name }}</h1>
        <p class="x-co-desc">{{ getSubjectDesc() }}</p>
        <div class="x-co-divider"></div>
        <p class="x-co-full-desc">{{ getSubjectFullDesc() }}</p>
      </div>
      <button class="x-back-btn" @click="goBack">
        <IconArrow :size="14" style="transform: rotate(180deg)" /> 返回课程列表
      </button>
    </aside>

    <!-- 右侧：画像对话 -->
    <main class="x-co-right">
      <!-- 构建动画 -->
      <div v-if="buildDone" class="x-build-overlay">
        <div class="x-build-content">
          <div class="x-build-icon">
            <IconCheck :size="48" />
          </div>
          <h2 class="x-build-title">画像已建立</h2>
          <p class="x-build-sub">正在为「{{ subjectInfo?.name }}」构建学习计划</p>
          <div class="x-build-steps">
            <div
              v-for="(bs, i) in buildSteps"
              :key="i"
              class="x-build-step"
              :class="{ 'is-done': bs.done, 'is-active': bs.active }"
            >
              <div class="x-build-step-indicator">
                <span v-if="bs.done" class="x-build-check"><IconCheck :size="14" /></span>
                <span v-else-if="bs.active" class="x-build-spinner"></span>
                <span v-else class="x-build-dot"></span>
              </div>
              <div class="x-build-step-content">
                <span class="x-build-step-label">{{ bs.label }}</span>
                <span class="x-build-step-detail">{{ bs.detail }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 对话区 -->
      <template v-else>
        <header class="x-chat-header">
          <div class="x-chat-header-left">
            <IconChat :size="18" />
            <h2 class="x-chat-title">构建学习画像</h2>
          </div>
          <div class="x-chat-status">
            <span
              class="x-status-dot"
              :class="{
                'is-open': wsStatus === 'open',
                'is-connecting': wsStatus === 'connecting',
                'is-error': wsStatus === 'error',
              }"
            ></span>
            <span class="x-status-text">
              {{ wsStatus === 'open' ? '已连接' : wsStatus === 'connecting' ? '连接中...' : '未连接' }}
            </span>
          </div>
        </header>

        <div ref="chatListRef" class="x-chat-list">
          <template v-for="m in profileMessages" :key="m.id">
            <div class="x-msg-row" :class="{ 'is-mine': m.kind === 'user' }">
              <div v-if="m.kind === 'assistant'" class="x-avatar">AI</div>
              <div class="x-bubble" :class="{ 'is-mine': m.kind === 'user' }">
                <BlurText
                  v-if="m.kind === 'assistant'"
                  :text="m.content"
                  :streaming="pendingMap[m.serverId ?? 0] ?? false"
                  class="x-bubble-text"
                />
                <p v-else class="x-bubble-text">{{ m.content }}</p>
              </div>
            </div>
          </template>
          <div v-if="profileMessages.length === 0" class="x-chat-empty">
            <IconHourglass :size="20" />
            <span>AI 正在准备提问…</span>
          </div>
        </div>

        <!-- 快捷回复 -->
        <div v-if="suggestions.length > 0" class="x-suggestions">
          <button
            v-for="s in suggestions"
            :key="s"
            class="x-suggestion-btn"
            :disabled="sending"
            @click="sendSuggestion(s)"
          >{{ s }}</button>
        </div>

        <!-- 画像完成状态 -->
        <div v-if="isComplete" class="x-complete-banner">
          <IconCheck :size="15" />
          <span>画像已完成</span>
        </div>

        <form class="x-chat-input" @submit.prevent="sendMessage">
          <textarea
            v-model="draftInput"
            rows="1"
            placeholder="输入你的回答…"
            :disabled="wsStatus !== 'open'"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <button
            type="submit"
            class="x-send-btn"
            :disabled="!canSubmitProfile"
            :title="sending ? '发送中' : '发送'"
          >
            <IconArrow :size="16" />
          </button>
        </form>

        <footer class="x-chat-footer">
          <button class="x-btn x-btn-ghost x-btn-sm" @click="goBack">
            <IconCross :size="12" /> 取消
          </button>
          <button
            class="x-btn x-btn-primary x-btn-sm"
            :disabled="completing"
            @click="finishOnboarding"
          >
            {{ completing ? '校验中…' : isComplete ? '进入学习 →' : '我完成了' }}
          </button>
        </footer>
        <p v-if="lastError" class="x-error">{{ lastError }}</p>
      </template>
    </main>
  </div>
</template>

<style scoped>
.x-co {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: oklch(98.5% 0.005 240);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'PingFang SC', system-ui, sans-serif;
}

/* 左侧 */
.x-co-left {
  width: 400px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: oklch(100% 0 0);
  border-right: 1px solid oklch(92% 0.005 240);
  overflow-y: auto;
}
.x-co-card {
  position: relative;
  height: 280px;
  overflow: hidden;
  flex-shrink: 0;
}
.x-co-card-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.x-co-card::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,0.7));
}
.x-co-card-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  padding: 24px;
  z-index: 1;
}
.x-co-card-num {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 72px;
  font-weight: 600;
  line-height: 0.85;
  color: oklch(98% 0.005 240);
}
.x-co-card-meta {
  position: absolute;
  bottom: 14px;
  left: 24px;
  right: 24px;
  display: flex;
  justify-content: space-between;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: oklch(98% 0.005 240);
  opacity: 0.8;
  z-index: 1;
}

.x-co-info {
  padding: 24px;
  flex: 1;
}
.x-co-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.025em;
  margin: 0 0 8px;
}
.x-co-desc {
  font-size: 14px;
  color: oklch(48% 0.018 250);
  margin: 0;
}
.x-co-divider {
  height: 1px;
  background: oklch(92% 0.005 240);
  margin: 20px 0;
}
.x-co-full-desc {
  font-size: 13.5px;
  line-height: 1.65;
  color: oklch(20% 0.022 250);
  margin: 0;
}

.x-back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  background: none;
  border: none;
  border-top: 1px solid oklch(92% 0.005 240);
  font-family: inherit;
  font-size: 13px;
  color: oklch(48% 0.018 250);
  cursor: pointer;
  transition: color 120ms;
}
.x-back-btn:hover { color: oklch(20% 0.022 250); }

/* 右侧 */
.x-co-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 构建动画 */
.x-build-overlay {
  position: absolute;
  inset: 0;
  background: oklch(98.5% 0.005 240);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.x-build-content {
  text-align: center;
  max-width: 480px;
  padding: 40px;
}
.x-build-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: oklch(60% 0.20 245);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}
.x-build-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 8px;
}
.x-build-sub {
  font-size: 14px;
  color: oklch(48% 0.018 250);
  margin: 0 0 32px;
}
.x-build-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
  text-align: left;
}
.x-build-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: oklch(100% 0 0);
  border: 1px solid oklch(92% 0.005 240);
  border-radius: 8px;
  transition: all 200ms;
}
.x-build-step.is-active {
  border-color: oklch(60% 0.20 245);
  background: oklch(94% 0.04 245);
}
.x-build-step.is-done {
  border-color: oklch(60% 0.18 145);
  background: oklch(96% 0.02 145);
}
.x-build-step-indicator {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.x-build-check {
  color: oklch(60% 0.18 145);
}
.x-build-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid oklch(92% 0.005 240);
  border-top-color: oklch(60% 0.20 245);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.x-build-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(82% 0.008 240);
}
.x-build-step-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.x-build-step-label {
  font-size: 14px;
  font-weight: 500;
}
.x-build-step-detail {
  font-size: 12px;
  color: oklch(48% 0.018 250);
}

/* 对话区 */
.x-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid oklch(92% 0.005 240);
  background: oklch(100% 0 0);
  flex-shrink: 0;
}
.x-chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  color: oklch(60% 0.20 245);
}
.x-chat-title {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: oklch(20% 0.022 250);
}
.x-chat-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.x-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: oklch(82% 0.008 240);
}
.x-status-dot.is-open { background: oklch(60% 0.18 145); }
.x-status-dot.is-connecting { background: oklch(70% 0.15 80); animation: pulse 1.2s ease-in-out infinite; }
.x-status-dot.is-error { background: oklch(60% 0.20 25); }
@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
.x-status-text {
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 11px;
  color: oklch(48% 0.018 250);
}

.x-chat-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 24px;
}
.x-msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.x-msg-row.is-mine { justify-content: flex-end; }
.x-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, oklch(60% 0.20 245), #7b8cff);
  color: #fff;
  font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.x-bubble {
  max-width: 72%;
  padding: 10px 14px;
  background: oklch(100% 0 0);
  border: 1px solid oklch(92% 0.005 240);
  border-radius: 16px 16px 16px 4px;
  line-height: 1.6;
}
.x-bubble.is-mine {
  background: oklch(60% 0.20 245);
  color: #fff;
  border-color: transparent;
  border-radius: 16px 16px 4px 16px;
}
.x-bubble-text {
  font-size: 13.5px;
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.x-typing {
  display: inline-block;
  color: oklch(60% 0.20 245);
  animation: typing 1s steps(2) infinite;
  margin-left: 1px;
}
.x-bubble.is-mine .x-typing { color: rgba(255,255,255,0.6); }
@keyframes typing { 50% { opacity: 0.2; } }
.x-chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: oklch(48% 0.018 250);
}

/* 快捷回复 */
.x-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 24px;
}
.x-suggestion-btn {
  padding: 6px 14px;
  background: oklch(100% 0 0);
  border: 1px solid oklch(92% 0.005 240);
  border-radius: 999px;
  font-size: 13px;
  color: oklch(60% 0.20 245);
  cursor: pointer;
  transition: all 120ms;
}
.x-suggestion-btn:hover:not(:disabled) {
  border-color: oklch(60% 0.20 245);
  background: oklch(94% 0.04 245);
}

/* 完成状态 */
.x-complete-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: oklch(96% 0.02 145);
  color: oklch(45% 0.15 145);
  font-size: 13px;
  font-weight: 500;
}

/* 输入区 */
.x-chat-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 24px;
  border-top: 1px solid oklch(92% 0.005 240);
  background: oklch(100% 0 0);
  flex-shrink: 0;
}
.x-chat-input textarea {
  flex: 1;
  resize: none;
  padding: 10px 14px;
  background: oklch(98.5% 0.005 240);
  border: 1px solid oklch(92% 0.005 240);
  border-radius: 12px;
  font-family: inherit;
  font-size: 13.5px;
  color: oklch(20% 0.022 250);
  outline: none;
  transition: border-color 160ms;
  line-height: 1.5;
}
.x-chat-input textarea:focus { border-color: oklch(60% 0.20 245); }
.x-send-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: none;
  background: oklch(60% 0.20 245);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 120ms, transform 120ms;
}
.x-send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.x-send-btn:not(:disabled):hover { transform: scale(1.06); }

.x-chat-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  border-top: 1px solid oklch(92% 0.005 240);
  background: oklch(99% 0.003 240);
  flex-shrink: 0;
}

/* 按钮 */
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: all 120ms;
  border-radius: 8px;
}
.x-btn-primary {
  background: oklch(60% 0.20 245);
  color: #fff;
}
.x-btn-primary:hover:not(:disabled) { opacity: 0.9; }
.x-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.x-btn-ghost {
  background: transparent;
  color: oklch(48% 0.018 250);
}
.x-btn-ghost:hover { color: oklch(20% 0.022 250); }
.x-btn-sm { font-size: 13px; padding: 8px 16px; }

.x-error {
  font-size: 12px;
  color: oklch(60% 0.20 25);
  margin: 0;
  padding: 0 24px 12px;
}
</style>
