<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { BOOKS_CONFIG } from '@/data/books'
import type { BookConfig } from '@/data/books'
import { useBookStates } from './use_book_states'
import PdfViewer from './PdfViewer.vue'
import { useMinimaxChat } from './use_minimax_chat'
import type { MiniMaxMessage } from './use_minimax_chat'
import { accumulateStudyTime } from '@/api/learning'
import {
  BrandMark,
  IconCheck,
  IconCross,
  IconPause,
  IconPin,
  IconNotepad,
  IconSparkle,
} from '@/components/icons'
import { FlipCard } from '@/components/ui/flip-card'

type FilterKey = 'all' | 'reading' | 'paused' | 'done'
type SortKey = 'default' | 'status' | 'title'

const { getStatus, getLastRead, openBook, setStatus } = useBookStates()

const filter = ref<FilterKey>('all')
const sort = ref<SortKey>('default')

const filteredBooks = computed<BookConfig[]>(() => {
  let list =
    filter.value === 'all'
      ? [...BOOKS_CONFIG]
      : BOOKS_CONFIG.filter((b) => getStatus(b.id) === filter.value)

  if (sort.value === 'title') {
    list = [...list].sort((a, b) => a.title.localeCompare(b.title, 'zh'))
  } else if (sort.value === 'status') {
    const order: Record<string, number> = { reading: 0, paused: 1, done: 2, unread: 3 }
    list = [...list].sort((a, b) => (order[getStatus(a.id)] ?? 3) - (order[getStatus(b.id)] ?? 3))
  }
  return list
})

const counts = computed(() => ({
  all: BOOKS_CONFIG.length,
  reading: BOOKS_CONFIG.filter((b) => getStatus(b.id) === 'reading').length,
  paused: BOOKS_CONFIG.filter((b) => getStatus(b.id) === 'paused').length,
  done: BOOKS_CONFIG.filter((b) => getStatus(b.id) === 'done').length,
}))

// ── 实际页码（由 PDF.js 运行时回报，存 localStorage 跨会话保留）────────
const PAGES_LS_KEY = 'aiteach.bookPageCounts'
const actualPages = ref<Record<string, number>>((() => {
  try { return JSON.parse(localStorage.getItem(PAGES_LS_KEY) ?? '{}') as Record<string, number> }
  catch { return {} }
})())

function bookPages(id: string): number {
  return actualPages.value[id] ?? 0
}

function onTotalPages(n: number): void {
  if (!readerBook.value || actualPages.value[readerBook.value.id] === n) return
  actualPages.value = { ...actualPages.value, [readerBook.value.id]: n }
  try { localStorage.setItem(PAGES_LS_KEY, JSON.stringify(actualPages.value)) } catch { /* ignore */ }
}

const stats = computed(() => ({
  total: BOOKS_CONFIG.length,
  reading: counts.value.reading,
  done: counts.value.done,
  totalPages: BOOKS_CONFIG.reduce((s, b) => s + bookPages(b.id), 0),
}))

// ── Reader state ──────────────────────────────────────────
const readerBook = ref<BookConfig | null>(null)
const readerOpen = ref(false)
const aiPanelOpen = ref(false)

// ── PDF 文字选中上下文 ────────────────────────────────────
const selectedText = ref('')

function onTextSelected(text: string): void {
  selectedText.value = text
}

function onSelectionCleared(): void {
  selectedText.value = ''
}

function clearSelectedText(): void {
  selectedText.value = ''
  window.getSelection()?.removeAllRanges()
}


// ── AI chat state ─────────────────────────────────────────
interface ChatMsg {
  role: 'user' | 'ai'
  text: string
}
const aiMessages = ref<ChatMsg[]>([])
const aiInput = ref('')
const aiTyping = ref(false)
const aiInputEl = ref<HTMLTextAreaElement | null>(null)

const canSend = computed(() => aiInput.value.trim().length > 0 && !aiTyping.value)

const QUICK_QUESTIONS = [
  '介绍这本书的核心内容',
  '适合什么基础的读者？',
  '有哪些重点章节？',
  '给我一道练习题',
]

// ── Markdown 渲染 + think 标签解析 ───────────────────────
const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

interface ParsedMsg {
  thinkText: string
  contentHtml: string
  isThinking: boolean
}

function parseMsg(text: string): ParsedMsg {
  if (!text.startsWith('<think>')) {
    return { thinkText: '', contentHtml: DOMPurify.sanitize(md.render(text)), isThinking: false }
  }
  const closeIdx = text.indexOf('</think>')
  if (closeIdx === -1) {
    // 流式中，think 标签尚未闭合
    return { thinkText: text.slice(7), contentHtml: '', isThinking: true }
  }
  const rest = text.slice(closeIdx + 8).trim()
  return {
    thinkText: text.slice(7, closeIdx).trim(),
    contentHtml: rest ? DOMPurify.sanitize(md.render(rest)) : '',
    isThinking: false,
  }
}

// ── MiniMax 直连对话 ──────────────────────────────────────
const minimax = useMinimaxChat()
const chatHistory = ref<MiniMaxMessage[]>([])
let abortCtrl: AbortController | null = null
let readingTimer: ReturnType<typeof setInterval> | null = null

/**
 * 开始记录阅读时长 —— 进入阅读器即触发.
 * 立即 +1 分钟 (打开), 之后每 60 秒 +1 分钟.
 * 上报到 POST /api/learning/study-sessions/accumulate/,
 * 后端按 (user, subject, date, activity_type) 聚合 (每天每学科一行).
 */
function startReadingTrack(book: BookConfig): void {
  stopReadingTrack()  // 防重入
  // 立即报一次: 打开即算 1 分钟
  accumulateStudyTime({
    subject: book.subject,
    activity_type: 'reading',
    minutes: 1,
  }).catch(() => { /* 上报失败不影响阅读 */ })
  readingTimer = setInterval(() => {
    accumulateStudyTime({
      subject: book.subject,
      activity_type: 'reading',
      minutes: 1,
    }).catch(() => { /* 静默 */ })
  }, 60_000)
}

function stopReadingTrack(): void {
  if (readingTimer !== null) {
    clearInterval(readingTimer)
    readingTimer = null
  }
}

function openReader(book: BookConfig): void {
  readerBook.value = book
  openBook(book.id)
  selectedText.value = ''
  aiTyping.value = false
  aiMessages.value = [
    {
      role: 'ai',
      text: `欢迎阅读《${book.title}》，我是你的专属阅读助手学径，学习途中有任何疑惑都可以随时向我提问！`,
    },
  ]
  chatHistory.value = [
    {
      role: 'system',
      content:
        `你是《${book.title}》（作者：${book.author}）的专属阅读助手，` +
        `该书属于${book.catName}领域，共${book.chaptersTotal}章。` +
        `用户正在 PDF 阅读器中阅读这本书，请结合书中具体内容回答问题，避免泛泛而谈。` +
        `若用户消息中以"[引用]"开头，则引用内容是用户从 PDF 中选中的原文，请优先针对该段内容作答。`,
    },
  ]
  readerOpen.value = true
  document.body.style.overflow = 'hidden'
  startReadingTrack(book)
}

function closeReader(): void {
  stopReadingTrack()
  abortCtrl?.abort()
  abortCtrl = null
  chatHistory.value = []
  readerOpen.value = false
  aiPanelOpen.value = false
  selectedText.value = ''
  document.body.style.overflow = ''
}

// 浏览器返回键拦截：阅读器打开时先关闭阅读器，不离开页面
onBeforeRouteLeave(() => {
  if (readerOpen.value) {
    closeReader()
    return false
  }
})

function toggleAiPanel(): void {
  aiPanelOpen.value = !aiPanelOpen.value
}

function markDone(): void {
  if (readerBook.value) setStatus(readerBook.value.id, 'done')
}
function markDoneById(bookId: string): void {
  setStatus(bookId, 'done')
}

function markPaused(): void {
  if (readerBook.value) setStatus(readerBook.value.id, 'paused')
}

function markReading(): void {
  if (readerBook.value) setStatus(readerBook.value.id, 'reading')
}
function markReadingById(bookId: string): void {
  setStatus(bookId, 'reading')
}

/**
 * 进度百分比: 简单用 status 推算 (无 PDF.js 报总页数前的兜底)
 *   done → 100 / paused → 50 / reading → 30 / unread → 0
 */
function progressPct(book: BookConfig): number {
  const s = getStatus(book.id)
  if (s === 'done') return 100
  if (s === 'paused') return 50
  if (s === 'reading') return 30
  return 0
}

function openInNewTab(): void {
  if (readerBook.value) window.open(readerBook.value.pdfUrl, '_blank', 'noopener')
}

function fillQuickQuestion(q: string): void {
  aiInput.value = q
  aiInputEl.value?.focus()
  autoResize()
}

async function sendAiMessage(): Promise<void> {
  const q = aiInput.value.trim()
  if (!q || !readerBook.value || aiTyping.value) return

  const ctx = selectedText.value
  const content = ctx
    ? `[引用] ${ctx.slice(0, 200)}${ctx.length > 200 ? '…' : ''}\n\n${q}`
    : q

  aiMessages.value.push({ role: 'user', text: content })
  aiInput.value = ''
  autoResize()
  clearSelectedText()

  // 占位 AI 消息，流式 chunk 逐步填充
  const msgIdx = aiMessages.value.length
  aiMessages.value.push({ role: 'ai', text: '' })
  aiTyping.value = true

  // 把用户消息追加到多轮历史
  chatHistory.value.push({ role: 'user', content })

  abortCtrl = new AbortController()
  let fullText = ''

  try {
    for await (const chunk of minimax.stream(chatHistory.value, abortCtrl.signal)) {
      fullText += chunk
      aiMessages.value[msgIdx]!.text = fullText
    }
    // 把 AI 回复追加到历史，保持多轮上下文
    if (fullText) chatHistory.value.push({ role: 'assistant', content: fullText })
  } catch (e) {
    const err = e as Error
    if (err.name !== 'AbortError') {
      aiMessages.value[msgIdx]!.text = `请求失败，请检查网络后重试。（${err.message}）`
    }
  } finally {
    aiTyping.value = false
    abortCtrl = null
  }
}

function autoResize(): void {
  const el = aiInputEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 96) + 'px'
}

function onAiKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendAiMessage()
  }
}

function onGlobalKeydown(e: KeyboardEvent): void {
  if (!readerOpen.value) return
  const tag = (document.activeElement as HTMLElement)?.tagName
  if (e.key === 'Escape' && tag !== 'TEXTAREA' && tag !== 'INPUT') closeReader()
}

// 书籍 ID 到备用封面图片的映射（assets/book 目录下的图片）
const FALLBACK_COVERS: Record<string, string> = {
  'deep_learning_limu': new URL('@/assets/book/deeplearn.jpeg', import.meta.url).href,
  'data_structure_yan': new URL('@/assets/book/datastrct.jpg', import.meta.url).href,
  'os_concepts_9th': new URL('@/assets/book/systemctloperation.jpeg', import.meta.url).href,
  'db_system_5th': new URL('@/assets/book/database.jpeg', import.meta.url).href,
  'computer_network_xie': new URL('@/assets/book/computernetwork.jpg', import.meta.url).href,
}

function handleCoverError(e: Event): void {
  const img = e.target as HTMLImageElement
  const book = filteredBooks.value.find(b => b.coverUrl === img.src)

  // 如果找到了对应书籍且有备用封面，则使用备用封面
  if (book && FALLBACK_COVERS[book.id]) {
    img.src = FALLBACK_COVERS[book.id]!
  } else {
    // 如果没有备用封面，则隐藏图片并显示 fallback 文字
    img.style.display = 'none'
    const wrap = img.closest('.book-cover-img-wrap')
    if (wrap) wrap.classList.add('cover-img-error')
  }
}

function ctaLabel(id: string): string {
  const s = getStatus(id)
  if (s === 'reading') return '▶ 继续阅读'
  if (s === 'paused') return '▶ 恢复阅读'
  if (s === 'done') return '✓ 重新阅读'
  return '▶ 开始阅读'
}

function lastReadLabel(id: string): string {
  const t = getLastRead(id)
  if (!t) return '尚未阅读'
  const diff = Date.now() - new Date(t).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} 小时前`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days} 天前`
  return `${Math.floor(days / 7)} 周前`
}

function readerCurrentStatus(): string {
  if (!readerBook.value) return ''
  return getStatus(readerBook.value.id)
}

onMounted(() => document.addEventListener('keydown', onGlobalKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
  document.body.style.overflow = ''
  abortCtrl?.abort()
  stopReadingTrack()  // 组件卸载时停掉 60s 周期上报, 避免 timer 残留
})
</script>

<template>
  <div class="shelf-page">
    <!-- ── Header ──────────────────────────────────────── -->
    <div class="shelf-header">
      <div class="shelf-header-inner">
        <h1 class="shelf-title">我的书架</h1>
        <p class="shelf-sub">
          共 <strong>{{ counts.all }}</strong> 本书，{{ counts.reading }} 本在读，{{ counts.done }} 本已完成。
        </p>
        <div class="chip-row">
          <button
            v-for="(label, key) in ({ all: '全部', reading: '在读', paused: '暂停', done: '已完成' } as Record<FilterKey, string>)"
            :key="key"
            class="chip"
            :class="{ active: filter === key }"
            @click="filter = key"
          >
            {{ label }}
            <span class="chip-num">{{ counts[key] }}</span>
          </button>
          <span class="chip-spacer" />
          <label class="chip-sort">
            排序
            <select v-model="sort" class="chip-sort-sel">
              <option value="default">默认顺序</option>
              <option value="status">按状态</option>
              <option value="title">书名 A→Z</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <!-- ── Body ───────────────────────────────────────── -->
    <div class="shelf-body">
      <!-- Stats bar -->
      <div class="statsbar">
        <div class="stat-box">
          <div class="stat-label">书架总数</div>
          <div class="stat-val">{{ stats.total }}<span class="stat-unit">本</span></div>
          <div class="stat-foot">{{ stats.reading }} 在读 · {{ stats.done }} 完成</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">在读中</div>
          <div class="stat-val">{{ stats.reading }}<span class="stat-unit">本</span></div>
          <div class="stat-foot">{{ counts.paused }} 本已暂停</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">已完成</div>
          <div class="stat-val">{{ stats.done }}<span class="stat-unit">本</span></div>
          <div class="stat-foot">
            完成率 {{ stats.total ? Math.round((stats.done / stats.total) * 100) : 0 }}%
          </div>
        </div>
        <div class="stat-box">
          <div class="stat-label">总页数</div>
          <div class="stat-val">{{ stats.totalPages ? stats.totalPages.toLocaleString() : '—' }}<span v-if="stats.totalPages" class="stat-unit">页</span></div>
          <div class="stat-foot">{{ stats.totalPages ? stats.total + ' 本合计' : '打开书籍后自动统计' }}</div>
        </div>
      </div>

      <!-- Book grid -->
      <div v-if="filteredBooks.length" class="shelf-grid">
        <FlipCard
          v-for="book in filteredBooks"
          :key="book.id"
          class="book-flip"
        >
          <!-- 正面: 封面 + 标题 + 元数据 + CTA -->
          <article class="book-card book-card--front" @click="openReader(book)">
            <div class="cover-wrap">
              <div class="book-cover-img-wrap">
                <img
                  :src="book.coverUrl"
                  :alt="book.title"
                  class="book-cover-img"
                  @error="handleCoverError"
                />
                <div class="cover-fallback-text">{{ book.catName }}</div>
              </div>
              <div
                class="cover-badge"
                :class="{
                  'badge-done': getStatus(book.id) === 'done',
                  'badge-paused': getStatus(book.id) === 'paused',
                  'badge-reading': getStatus(book.id) === 'reading',
                }"
              >
                <span v-if="getStatus(book.id) === 'done'"><span style="display:inline-flex;align-items:center;vertical-align:-2px"><IconCheck :size="10" /></span> 完成</span>
                <span v-else-if="getStatus(book.id) === 'paused'"><span style="display:inline-flex;align-items:center;vertical-align:-2px"><IconPause :size="10" /></span> 暂停</span>
                <span v-else-if="getStatus(book.id) === 'reading'">● 在读</span>
                <span v-else>未读</span>
              </div>
            </div>

            <div class="card-body">
              <div class="card-title">{{ book.title }}</div>
              <div class="card-author">{{ book.author }}</div>
              <div class="card-meta">
                <span>{{ book.chaptersTotal }} 章</span>
                <span class="card-dot">·</span>
                <span>{{ bookPages(book.id) ? bookPages(book.id).toLocaleString() + ' 页' : '页数加载中' }}</span>
                <span class="card-dot">·</span>
                <span>{{ book.catName }}</span>
              </div>
              <div class="card-last-read">{{ lastReadLabel(book.id) }}</div>
              <button
                class="card-cta"
                :class="{ 'cta-done': getStatus(book.id) === 'done' }"
                @click.stop="openReader(book)"
              >
                {{ ctaLabel(book.id) }}
              </button>
            </div>
          </article>

          <!-- 背面: 进度 + 快捷操作 -->
          <template #back>
            <div class="book-card book-card--back" @click="openReader(book)">
              <div class="back-head">
                <div class="back-eyebrow">{{ book.catName }}</div>
                <div class="back-title">{{ book.title }}</div>
                <div class="back-author">{{ book.author }}</div>
              </div>

              <!-- 阅读进度 -->
              <div class="back-progress">
                <div class="back-progress-label">
                  <span>阅读进度</span>
                  <span class="back-progress-pct">{{ progressPct(book) }}%</span>
                </div>
                <div class="back-progress-track">
                  <div class="back-progress-fill" :style="{ width: `${progressPct(book)}%` }" />
                </div>
                <div class="back-progress-meta">
                  {{ bookPages(book.id).toLocaleString() }} / {{ '—' }} 页
                  · {{ book.chaptersTotal }} 章
                </div>
              </div>

              <!-- 最近阅读 -->
              <div class="back-last-read">
                <div class="back-last-read-label">最近</div>
                <div class="back-last-read-value">{{ lastReadLabel(book.id) }}</div>
              </div>

              <!-- 快捷操作 -->
              <div class="back-actions">
                <button class="back-btn back-btn--primary" @click.stop="openReader(book)">
                  <span style="display:inline-flex;align-items:center;gap:5px">
                    <span style="display:inline-flex"><IconNotepad :size="11" /></span>
                    {{ ctaLabel(book.id) }}
                  </span>
                </button>
                <div class="back-btn-row">
                  <button
                    v-if="getStatus(book.id) !== 'reading'"
                    class="back-btn"
                    @click.stop="markReadingById(book.id)"
                  >设为在读</button>
                  <button
                    v-if="getStatus(book.id) !== 'done'"
                    class="back-btn"
                    @click.stop="markDoneById(book.id)"
                  >标完成</button>
                </div>
              </div>

              <div class="back-hint">悬停翻回 · 点击正面继续</div>
            </div>
          </template>
        </FlipCard>
      </div>

      <!-- Empty state -->
      <div v-else class="shelf-empty">
        <div class="empty-icon" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-body-mid)"><IconSparkle :size="44" /></div>
        <div class="empty-title">该分类下暂无书籍</div>
        <div class="empty-hint">切换筛选条件，或点击书卡开始阅读</div>
      </div>
    </div>
  </div>

  <!-- ── Reader overlay ─────────────────────────────────── -->
  <Teleport to="body">
    <div v-if="readerOpen" class="reader-overlay" :class="{ 'ai-open': aiPanelOpen }">
      <div class="reader-top">
        <button class="reader-close" aria-label="关闭阅读器" @click="closeReader"><IconCross :size="16" /></button>
        <div class="reader-info">
          <div class="reader-title">{{ readerBook?.title }}</div>
          <div class="reader-meta">{{ readerBook?.author }} · {{ readerBook?.chaptersTotal }} 章{{ readerBook && bookPages(readerBook.id) ? ' · ' + bookPages(readerBook.id).toLocaleString() + ' 页' : '' }}</div>
        </div>
        <div class="reader-actions">
          <template v-if="readerBook">
            <button
              v-if="readerCurrentStatus() !== 'reading' && readerCurrentStatus() !== 'unread'"
              class="r-btn"
              @click="markReading"
            >▶ 继续在读</button>
            <button
              v-if="readerCurrentStatus() === 'reading'"
              class="r-btn"
              @click="markPaused"
            ><span style="display:inline-flex;align-items:center;gap:5px"><IconPause :size="11" /> 暂停</span></button>
            <button
              v-if="readerCurrentStatus() !== 'done'"
              class="r-btn"
              @click="markDone"
            ><span style="display:inline-flex;align-items:center;gap:5px"><IconCheck :size="11" /> 标为完成</span></button>
          </template>
          <button class="r-btn" @click="openInNewTab">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6">
              <path d="M5 2H2v8h8V7M7 2h3v3M10 2 5 7" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            新标签打开
          </button>
          <button class="r-btn r-btn-primary" @click="toggleAiPanel">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="6" cy="6" r="4"/>
              <circle cx="6" cy="6" r="1.5" fill="currentColor"/>
            </svg>
            AI 助手
          </button>
        </div>
      </div>

      <div class="reader-body">
        <!-- PDF viewer (PDF.js, supports text selection) -->
        <div class="reader-pdf-area">
          <PdfViewer
            v-if="readerBook"
            :src="readerBook.pdfUrl"
            @text-selected="onTextSelected"
            @selection-cleared="onSelectionCleared"
            @total-pages="onTotalPages"
          />
        </div>

        <!-- AI panel -->
        <aside class="ai-panel" :class="{ open: aiPanelOpen }">
          <div class="ai-head">
            <div class="ai-head-row">
              <div class="ai-avatar">
                <span style="display:inline-flex"><BrandMark :size="18" /></span>
                <span class="ai-status-dot" />
              </div>
              <div class="ai-info">
                <div class="ai-name">
                  学径 AI
                  <span class="ai-badge">RAG</span>
                </div>
                <div class="ai-context">
                  正在阅读《<span class="ai-book-ref">{{ readerBook?.title }}</span>》
                </div>
              </div>
            </div>
          </div>

          <div class="ai-quick">
            <div class="ai-quick-title">快速提问</div>
            <div class="ai-quick-row">
              <button
                v-for="q in QUICK_QUESTIONS"
                :key="q"
                class="ai-quick-chip"
                @click="fillQuickQuestion(q)"
              >{{ q }}</button>
            </div>
          </div>

          <div class="ai-chat">
            <div
              v-for="(msg, i) in aiMessages"
              :key="i"
              class="chat-msg"
              :class="msg.role"
            >
              <div class="msg-avatar" :class="msg.role">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
              <div class="msg-body">
                <div class="msg-name">
                  {{ msg.role === 'user' ? '你' : '学径 AI' }}
                  <span class="msg-role-label">{{ msg.role === 'user' ? '提问' : '回答' }}</span>
                </div>
                <!-- 用户消息：纯文本 -->
                <div v-if="msg.role === 'user'" class="msg-bubble">{{ msg.text }}</div>
                <!-- AI 消息：解析 think 标签 + 渲染 markdown -->
                <div v-else class="msg-bubble ai-bubble">
                  <template v-if="msg.text">
                    <!-- 流式思考中（think 未闭合）-->
                    <div v-if="parseMsg(msg.text).isThinking" class="think-block think-active">
                      <div class="think-label">
                        <span class="think-icon" style="display:inline-flex;align-items:center"><IconNotepad :size="10" /></span>思考中
                        <span class="think-dots"><span /><span /><span /></span>
                      </div>
                      <div class="think-text">{{ parseMsg(msg.text).thinkText }}</div>
                    </div>
                    <!-- 思考完毕（可折叠）-->
                    <details v-else-if="parseMsg(msg.text).thinkText" class="think-block">
                      <summary class="think-label">
                        <span class="think-icon" style="display:inline-flex;align-items:center"><IconNotepad :size="10" /></span>查看思考过程
                      </summary>
                      <div class="think-text">{{ parseMsg(msg.text).thinkText }}</div>
                    </details>
                    <!-- 主体内容（markdown）-->
                    <div
                      v-if="parseMsg(msg.text).contentHtml"
                      class="md-content"
                      v-html="parseMsg(msg.text).contentHtml"
                    />
                    <!-- 仅有 think 内容、主体还没来时不留白 -->
                  </template>
                </div>
              </div>
            </div>

            <!-- aiTyping 且最后一条 AI 消息为空（think 还没到来）时显示 loading dots -->
            <div v-if="aiTyping && !aiMessages.at(-1)?.text" class="chat-msg ai">
              <div class="msg-avatar ai"><span style="display:inline-flex"><BrandMark :size="14" /></span></div>
              <div class="msg-body">
                <div class="msg-name">学径 AI <span class="msg-role-label">回复中…</span></div>
                <div class="msg-bubble">
                  <div class="typing-dots"><span /><span /><span /></div>
                </div>
              </div>
            </div>
          </div>

          <!-- 选中文字引用卡片 -->
          <div v-if="selectedText" class="ai-quote-bar">
            <div class="ai-quote-label">
              <span class="ai-quote-icon" style="display:inline-flex;align-items:center"><IconPin :size="11" /></span>
              <span>已选中内容</span>
              <button class="ai-quote-clear" aria-label="清除选中" @click="clearSelectedText"><IconCross :size="10" /></button>
            </div>
            <div class="ai-quote-text">{{ selectedText.slice(0, 100) }}{{ selectedText.length > 100 ? '…' : '' }}</div>
          </div>

          <div class="ai-input-wrap">
            <div class="ai-input-box">
              <textarea
                ref="aiInputEl"
                v-model="aiInput"
                class="ai-textarea"
                :placeholder="selectedText ? '针对选中内容提问…' : '向 AI 提问关于这本书的内容…'"
                rows="1"
                @input="autoResize"
                @keydown="onAiKeydown"
              />
              <button class="ai-send-btn" :disabled="!canSend" aria-label="发送" @click="sendAiMessage">
                <svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="m2 7 10-5-5 5 5 5-10-5z" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
            <div class="ai-hint">
              <span>{{ selectedText ? '将结合选中内容回答' : '基于本书内容回答' }}</span>
              <span><kbd>Enter</kbd> 发送 · <kbd>Shift+Enter</kbd> 换行</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Page shell ─────────────────────────────────────────── */
.shelf-page {
  min-height: 100%;
  background: var(--x-canvas);
}

/* ── Header ─────────────────────────────────────────────── */
.shelf-header {
  border-bottom: 1px solid var(--x-hairline);
  padding: 24px 40px 18px;
}
.shelf-header-inner {
  max-width: var(--x-container);
  margin: 0 auto;
}
.shelf-title {
  font-family: var(--x-font-display);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin-bottom: 4px;
}
.shelf-sub {
  font-size: 13px;
  color: var(--x-body-mid);
  margin-bottom: 14px;
}
.shelf-sub strong {
  color: var(--x-ink);
  font-weight: 600;
}

/* ── Chip row ───────────────────────────────────────────── */
.chip-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.chip {
  padding: 5px 13px;
  border-radius: var(--x-rounded-pill);
  border: 1px solid var(--x-hairline);
  background: var(--x-canvas);
  color: var(--x-body);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--x-font-display);
  transition: border-color 0.15s, color 0.15s, background 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.chip:hover {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.chip.active {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-color: var(--x-primary);
  font-weight: 600;
}
.chip-num {
  font-family: var(--x-font-mono);
  font-size: 11px;
  opacity: 0.75;
}
.chip.active .chip-num {
  opacity: 0.9;
}
.chip-spacer {
  flex: 1;
}
.chip-sort {
  font-size: 12px;
  color: var(--x-body-mid);
  font-family: var(--x-font-display);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.chip-sort-sel {
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--x-body);
  font-family: var(--x-font-display);
  font-weight: 500;
  cursor: pointer;
  outline: none;
  padding: 2px 4px;
}

/* ── Body ───────────────────────────────────────────────── */
.shelf-body {
  max-width: var(--x-container);
  margin: 0 auto;
  padding: 28px 40px 80px;
}

/* ── Stats bar ──────────────────────────────────────────── */
.statsbar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}
.stat-box {
  padding: 16px 20px;
  background: var(--x-canvas);
  border-radius: var(--x-rounded-lg);
  box-shadow: var(--x-shadow-card);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.stat-box:hover {
  box-shadow: var(--x-shadow-card-hover);
  transform: translateY(-2px);
}
.stat-label {
  font-size: 11px;
  color: var(--x-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  margin-bottom: 6px;
}
.stat-val {
  font-size: 24px;
  font-weight: 600;
  color: var(--x-ink);
  font-family: var(--x-font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.stat-unit {
  font-size: 13px;
  color: var(--x-body-mid);
  font-weight: 500;
  margin-left: 4px;
  font-family: var(--x-font-display);
}
.stat-foot {
  font-size: 11px;
  color: var(--x-mute);
  margin-top: 4px;
  font-family: var(--x-font-mono);
}

/* ── Shelf grid ─────────────────────────────────────────── */
.shelf-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

/* ── FlipCard wrapper (覆盖上游 h-72 w-56 默认尺寸) ────── */
.book-flip {
  width: 100% !important;
  height: 360px !important;
}

/* ── Book card ──────────────────────────────────────────── */
.book-card {
  background: transparent;
  border-radius: var(--x-rounded-lg);
  box-shadow: none;
  cursor: pointer;
  transition: transform 0.2s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  width: 100%;
  height: 100%;
}
.book-card:hover {
  transform: translateY(-4px);
}

.cover-wrap {
  position: relative;
  padding: 8px 0 6px;
  background: transparent;
  display: flex;
  justify-content: center;
}
.book-cover-img-wrap {
  width: 130px;
  height: 175px;
  border-radius: 5px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12), 0 1px 3px rgba(15, 23, 42, 0.08);
  background: var(--x-canvas-mid);
  display: flex;
  align-items: center;
  justify-content: center;
}
.book-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.35s cubic-bezier(0.28, 0, 0.22, 1);
}
.book-card:hover .book-cover-img {
  transform: scale(1.04);
}
.cover-fallback-text {
  position: absolute;
  inset: 0;
  display: none;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: var(--x-body-mid);
  background: var(--x-canvas-mid);
}
.book-cover-img-wrap.cover-img-error .cover-fallback-text {
  display: flex;
}

.cover-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.95);
  color: var(--x-ink);
  padding: 3px 8px;
  border-radius: var(--x-rounded-pill);
  font-family: var(--x-font-mono);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
}
.cover-badge.badge-done {
  background: var(--x-success);
  color: #fff;
}
.cover-badge.badge-paused {
  background: var(--x-warning);
  color: #fff;
}
.cover-badge.badge-reading {
  background: var(--x-primary);
  color: #fff;
}

.card-body {
  padding: 12px 16px 14px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;          /* 允许内部 flex 子项收缩, 避免溢出被 overflow:hidden 切掉 */
}
.card-cta {
  padding: 7px 12px;
  border-radius: var(--x-rounded-pill);
  background: var(--x-primary);
  color: var(--x-on-primary);
  font-size: 12px;
  font-weight: 600;
  font-family: var(--x-font-display);
  border: none;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;         /* CTA 永远完整显示, 让其它内容 (last-read / meta) 让位 */
  margin-top: 8px;        /* 与 last-read 拉开间距, 不靠弹性撑 */
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--x-ink);
  line-height: 1.4;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-author {
  font-size: 12px;
  color: var(--x-mute);
  margin-bottom: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.card-meta {
  font-size: 11px;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}
.card-dot {
  opacity: 0.4;
}
.card-last-read {
  font-size: 11px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  margin-bottom: 12px;
  flex: 1;
}
.card-cta {
  padding: 7px 12px;
  border-radius: var(--x-rounded-pill);
  background: var(--x-primary);
  color: var(--x-on-primary);
  font-size: 12px;
  font-weight: 600;
  font-family: var(--x-font-display);
  border: none;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-cta:hover {
  background: var(--x-primary-hover);
}
.card-cta.cta-done {
  background: var(--x-canvas-soft);
  color: var(--x-success);
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.card-cta.cta-done:hover {
  background: var(--x-canvas-mid);
}

/* ── Book card 背面 (FlipCard #back slot) ────────────────── */
.book-card--back {
  background: linear-gradient(155deg, var(--x-canvas) 0%, var(--x-canvas-soft) 100%);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: var(--x-ink);
  /* 取消正面 hover 的 translate, 背面靠 FlipCard 整体翻转展示 */
  transform: none !important;
}
.book-card--back:hover {
  transform: none !important;
  box-shadow: none !important;
}

.back-head {
  border-bottom: 1px dashed var(--x-hairline);
  padding-bottom: 8px;
}
.back-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 10px;
  color: var(--x-body-mid);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.back-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  line-height: 1.3;
  margin-bottom: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.back-author {
  font-size: 11px;
  color: var(--x-mute);
}

.back-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.back-progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
}
.back-progress-pct {
  font-weight: 600;
  color: var(--x-primary);
}
.back-progress-track {
  height: 4px;
  border-radius: 2px;
  background: var(--x-canvas-mid);
  overflow: hidden;
}
.back-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--x-primary), oklch(60% 0.15 200));
  transition: width 0.4s ease;
}
.back-progress-meta {
  font-size: 10px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  letter-spacing: 0.04em;
}

.back-last-read {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-size: 11px;
  padding: 6px 10px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-sm);
}
.back-last-read-label {
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  letter-spacing: 0.06em;
}
.back-last-read-value {
  color: var(--x-ink);
  font-weight: 500;
}

.back-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: auto;
}
.back-btn {
  padding: 6px 10px;
  font-size: 11.5px;
  font-weight: 500;
  font-family: var(--x-font-display);
  background: var(--x-canvas);
  color: var(--x-body);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  cursor: pointer;
  transition: border-color 0.12s, color 0.12s, background 0.12s;
}
.back-btn:hover {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.back-btn--primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-color: var(--x-primary);
  font-weight: 600;
}
.back-btn--primary:hover {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
  color: var(--x-on-primary);
}
.back-btn-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.back-hint {
  text-align: center;
  font-size: 10px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  letter-spacing: 0.05em;
  margin-top: 2px;
  opacity: 0.7;
}

/* ── Empty state ────────────────────────────────────────── */
.shelf-empty {
  padding: 100px 0;
  text-align: center;
}
.empty-icon {
  font-size: 44px;
  margin-bottom: 14px;
  opacity: 0.25;
  color: var(--x-body-mid);
}
.empty-title {
  font-size: 17px;
  font-weight: 500;
  color: var(--x-body);
  margin-bottom: 6px;
  font-family: var(--x-font-display);
}
.empty-hint {
  font-size: 13px;
  color: var(--x-mute);
  max-width: 360px;
  margin: 0 auto;
  line-height: 1.6;
}

/* ── Reader overlay ─────────────────────────────────────── */
.reader-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: var(--x-canvas);
  display: flex;
  flex-direction: column;
  animation: fade-in 0.2s ease;
}
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.reader-top {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 22px;
  border-bottom: 1px solid var(--x-hairline);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.reader-close {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: none;
  background: var(--x-canvas-soft);
  color: var(--x-ink);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
  transition: background 0.15s;
  flex-shrink: 0;
}
.reader-close:hover {
  background: var(--x-hairline);
}
.reader-info {
  flex: 1;
  min-width: 0;
}
.reader-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--x-ink);
  font-family: var(--x-font-display);
  letter-spacing: -0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.reader-meta {
  font-size: 11px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  margin-top: 2px;
}
.reader-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.r-btn {
  padding: 6px 11px;
  border-radius: var(--x-rounded-sm);
  border: 1px solid var(--x-hairline);
  background: var(--x-canvas);
  color: var(--x-body);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--x-font-display);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: border-color 0.15s, color 0.15s;
  white-space: nowrap;
}
.r-btn:hover {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.r-btn-primary {
  background: var(--x-primary);
  border-color: var(--x-primary);
  color: var(--x-on-primary);
  font-weight: 600;
}
.r-btn-primary:hover {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
  color: var(--x-on-primary);
}

.reader-body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 460px;
  min-height: 0;
}

.reader-pdf-area {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* AI panel */
.ai-panel {
  background: var(--x-canvas);
  border-left: 1px solid var(--x-hairline);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.ai-head {
  padding: 14px 18px;
  border-bottom: 1px solid var(--x-hairline);
  flex-shrink: 0;
}
.ai-head-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--x-primary-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--x-primary);
  font-size: 13px;
  font-weight: 700;
  position: relative;
  flex-shrink: 0;
}
.ai-status-dot {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--x-success);
  border: 2px solid var(--x-canvas);
}
.ai-info {
  flex: 1;
  min-width: 0;
}
.ai-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--x-ink);
  display: flex;
  align-items: center;
  gap: 6px;
}
.ai-badge {
  font-size: 9px;
  background: var(--x-primary-soft);
  color: var(--x-primary);
  padding: 2px 6px;
  border-radius: var(--x-rounded-sm);
  font-weight: 600;
  letter-spacing: 0.06em;
}
.ai-context {
  font-size: 11px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-book-ref {
  color: var(--x-primary);
  font-weight: 600;
}

.ai-quick {
  padding: 10px 18px;
  border-bottom: 1px solid var(--x-hairline);
  flex-shrink: 0;
}
.ai-quick-title {
  font-size: 10px;
  color: var(--x-mute);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  margin-bottom: 8px;
}
.ai-quick-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.ai-quick-chip {
  padding: 4px 10px;
  font-size: 11px;
  background: var(--x-canvas-soft);
  color: var(--x-body);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  font-family: var(--x-font-display);
  transition: border-color 0.14s, color 0.14s, background 0.14s;
  font-weight: 500;
}
.ai-quick-chip:hover {
  border-color: var(--x-primary);
  color: var(--x-primary);
  background: var(--x-canvas-tint);
}

.ai-chat {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: var(--x-hairline) transparent;
}
.ai-chat::-webkit-scrollbar {
  width: 4px;
}
.ai-chat::-webkit-scrollbar-thumb {
  background: var(--x-hairline);
  border-radius: 4px;
}

.chat-msg {
  display: flex;
  gap: 8px;
  animation: msg-in 0.22s ease;
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.msg-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  margin-top: 2px;
}
.msg-avatar.user {
  background: var(--x-body);
}
.msg-avatar.ai {
  background: var(--x-primary-soft);
  color: var(--x-primary);
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--x-ink);
  margin-bottom: 3px;
}
.msg-role-label {
  color: var(--x-mute);
  font-weight: 400;
  margin-left: 4px;
  font-size: 10px;
}
.msg-bubble {
  font-size: 12.5px;
  color: var(--x-ink);
  line-height: 1.6;
  background: var(--x-canvas-soft);
  padding: 8px 11px;
  border-radius: var(--x-rounded-md);
  border-top-left-radius: 3px;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-msg.user .msg-bubble {
  background: var(--x-canvas-tint);
  border-top-left-radius: var(--x-rounded-md);
  border-top-right-radius: 3px;
}

.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--x-mute);
  animation: typing 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

.ai-input-wrap {
  padding: 10px 14px 14px;
  border-top: 1px solid var(--x-hairline);
  background: var(--x-canvas-soft);
  flex-shrink: 0;
}
.ai-input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-lg);
  padding: 7px 7px 7px 12px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ai-input-box:focus-within {
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px rgba(30, 90, 224, 0.08);
}
.ai-textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-family: var(--x-font-display);
  font-size: 12.5px;
  color: var(--x-ink);
  line-height: 1.5;
  resize: none;
  max-height: 96px;
  min-height: 20px;
}
.ai-textarea::placeholder {
  color: var(--x-mute);
}
.ai-send-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: none;
  background: var(--x-primary);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
  flex-shrink: 0;
}
.ai-send-btn:hover:not(:disabled) {
  background: var(--x-primary-hover);
}
.ai-send-btn:disabled {
  background: var(--x-hairline);
  cursor: not-allowed;
  color: var(--x-mute);
}
.ai-send-btn svg {
  width: 13px;
  height: 13px;
}
.ai-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 10px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
}
.ai-hint kbd {
  font-family: var(--x-font-mono);
  padding: 1px 4px;
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: 3px;
  color: var(--x-body-mid);
  margin: 0 2px;
}

/* 选中文字引用卡片 */
.ai-quote-bar {
  margin: 0 14px 0;
  padding: 8px 10px;
  background: var(--x-canvas-tint);
  border: 1px solid var(--x-primary-soft);
  border-radius: var(--x-rounded-md);
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  border-bottom: none;
}
.ai-quote-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 600;
  color: var(--x-primary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ai-quote-icon {
  font-size: 11px;
}
.ai-quote-clear {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--x-body-mid);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0 2px;
  transition: color 0.12s;
}
.ai-quote-clear:hover {
  color: var(--x-danger);
}
.ai-quote-text {
  font-size: 11.5px;
  color: var(--x-body);
  line-height: 1.5;
  font-style: italic;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── Responsive ─────────────────────────────────────────── */
@media (max-width: 1024px) {
  .reader-body { grid-template-columns: 1fr 380px; }
}
@media (max-width: 880px) {
  .shelf-header { padding: 18px 20px 14px; }
  .shelf-body { padding: 20px 20px 60px; }
  .statsbar { grid-template-columns: repeat(2, 1fr); }
  .shelf-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
  .reader-body { grid-template-columns: 1fr; }
  .ai-panel { display: none; }
  .reader-overlay.ai-open .reader-pdf-area { display: none; }
  .reader-overlay.ai-open .ai-panel { display: flex; }
  .reader-actions .r-btn:not(.r-btn-primary) { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .book-card,
  .book-cover-img,
  .reader-overlay { animation: none; transition: none; }
}

/* ── Think 区块 ─────────────────────────────────────────── */
.think-block {
  margin-bottom: 6px;
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-soft);
  font-size: 11.5px;
  overflow: hidden;
}
.think-label {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 9px;
  font-size: 11px;
  font-weight: 600;
  color: var(--x-body-mid);
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.think-label::-webkit-details-marker { display: none; }
.think-icon {
  font-size: 10px;
  color: var(--x-primary);
  opacity: 0.7;
}
.think-block.think-active .think-label {
  color: var(--x-primary);
}
.think-dots {
  display: inline-flex;
  gap: 3px;
  margin-left: 2px;
}
.think-dots span {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--x-primary);
  opacity: 0.5;
  animation: typing 1.2s ease-in-out infinite;
}
.think-dots span:nth-child(2) { animation-delay: 0.15s; }
.think-dots span:nth-child(3) { animation-delay: 0.3s; }
.think-text {
  padding: 6px 9px 8px;
  color: var(--x-mute);
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  border-top: 1px solid var(--x-hairline);
  max-height: 200px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--x-hairline) transparent;
}

/* ── AI 气泡（无顶部圆角，内容直接铺） ─────────────────── */
.ai-bubble {
  padding: 0;
  background: transparent;
  border: none;
}
.ai-bubble .think-block:first-child,
.ai-bubble .md-content:first-child {
  margin-top: 0;
}

/* ── Markdown 正文 ──────────────────────────────────────── */
.md-content {
  font-size: 12.5px;
  color: var(--x-ink);
  line-height: 1.65;
  background: var(--x-canvas-soft);
  padding: 8px 11px;
  border-radius: var(--x-rounded-md);
  border-top-left-radius: 3px;
  word-break: break-word;
}
.md-content :deep(p) { margin: 0 0 6px; }
.md-content :deep(p:last-child) { margin-bottom: 0; }
.md-content :deep(ul),
.md-content :deep(ol) { margin: 4px 0 6px; padding-left: 18px; }
.md-content :deep(li) { margin: 2px 0; }
.md-content :deep(strong) { font-weight: 600; color: var(--x-ink); }
.md-content :deep(em) { font-style: italic; }
.md-content :deep(code) {
  font-family: var(--x-font-mono);
  font-size: 11.5px;
  background: var(--x-canvas-mid);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--x-primary);
}
.md-content :deep(pre) {
  background: var(--x-canvas-mid);
  border-radius: var(--x-rounded-sm);
  padding: 8px 10px;
  overflow-x: auto;
  margin: 6px 0;
  font-size: 11px;
  line-height: 1.5;
  scrollbar-width: thin;
}
.md-content :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--x-ink);
  font-size: inherit;
}
.md-content :deep(blockquote) {
  margin: 6px 0;
  padding: 4px 10px;
  border-left: 3px solid var(--x-primary);
  color: var(--x-body-mid);
  font-style: italic;
}
.md-content :deep(h1),
.md-content :deep(h2),
.md-content :deep(h3) {
  font-weight: 600;
  color: var(--x-ink);
  margin: 8px 0 4px;
  line-height: 1.3;
}
.md-content :deep(h1) { font-size: 14px; }
.md-content :deep(h2) { font-size: 13px; }
.md-content :deep(h3) { font-size: 12.5px; }
.md-content :deep(hr) { border: none; border-top: 1px solid var(--x-hairline); margin: 8px 0; }
.md-content :deep(a) { color: var(--x-primary); text-decoration: underline; }
.md-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin: 8px 0;
}
.md-content :deep(th),
.md-content :deep(td) {
  border: 1px solid var(--x-hairline);
  padding: 5px 10px;
  text-align: left;
  line-height: 1.5;
}
.md-content :deep(th) {
  background: var(--x-canvas-mid);
  font-weight: 600;
  color: var(--x-ink);
}
.md-content :deep(tr:nth-child(even) td) {
  background: var(--x-canvas-soft);
}
</style>
