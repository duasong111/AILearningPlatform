<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { IconWarn } from '@/components/icons'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).href

const SCALE_DEFAULT = 1.5
const SCALE_MIN = 0.5
const SCALE_MAX = 3.0
const SCALE_STEP = 0.25
const THUMB_SCALE = 0.15

const props = defineProps<{ src: string }>()
const emit = defineEmits<{
  (e: 'text-selected', text: string): void
  (e: 'selection-cleared'): void
  (e: 'total-pages', n: number): void
}>()

const rootRef = ref<HTMLDivElement | null>(null)
const scrollRef = ref<HTMLDivElement | null>(null)
const thumbsRef = ref<HTMLDivElement | null>(null)

const loading = ref(true)
const loadError = ref(false)
const totalPages = ref(0)
const currentPage = ref(1)
const scale = ref(SCALE_DEFAULT)
const zooming = ref(false)

const zoomLabel = computed(() => Math.round((scale.value / SCALE_DEFAULT) * 100) + '%')

const renderedSet = new Set<number>()
const renderedThumbSet = new Set<number>()

let pdfDoc: PDFDocumentProxy | null = null
let renderObs: IntersectionObserver | null = null
let thumbObs: IntersectionObserver | null = null

// ── 初始化 ──────────────────────────────────────────────────────────────────
async function init(url: string): Promise<void> {
  renderObs?.disconnect()
  thumbObs?.disconnect()
  await pdfDoc?.cleanup()
  pdfDoc = null
  renderedSet.clear()
  renderedThumbSet.clear()
  if (scrollRef.value) scrollRef.value.innerHTML = ''
  if (thumbsRef.value) thumbsRef.value.innerHTML = ''
  loading.value = true
  loadError.value = false
  currentPage.value = 1
  scale.value = SCALE_DEFAULT

  try {
    pdfDoc = await pdfjsLib.getDocument({ url }).promise
    const numP = pdfDoc.numPages
    totalPages.value = numP
    emit('total-pages', numP)

    const page1 = await pdfDoc.getPage(1)
    const vp1 = page1.getViewport({ scale: SCALE_DEFAULT })
    const tvp = page1.getViewport({ scale: THUMB_SCALE })
    const tw = Math.ceil(tvp.width)
    const th = Math.ceil(tvp.height)

    // 主区域：页面占位符
    if (scrollRef.value) {
      const frag = document.createDocumentFragment()
      for (let i = 1; i <= numP; i++) {
        const div = document.createElement('div')
        div.className = 'pvr-page'
        div.dataset.pageNum = String(i)
        div.style.width = vp1.width + 'px'
        div.style.height = vp1.height + 'px'
        frag.appendChild(div)
      }
      scrollRef.value.appendChild(frag)
    }

    // 左侧缩略图：占位符
    if (thumbsRef.value) {
      const frag = document.createDocumentFragment()
      for (let i = 1; i <= numP; i++) {
        const wrap = document.createElement('div')
        wrap.className = 'pvr-thumb'
        wrap.dataset.thumbNum = String(i)
        const cvs = document.createElement('canvas')
        cvs.className = 'pvr-thumb-canvas'
        cvs.width = tw
        cvs.height = th
        const lbl = document.createElement('div')
        lbl.className = 'pvr-thumb-num'
        lbl.textContent = String(i)
        wrap.appendChild(cvs)
        wrap.appendChild(lbl)
        wrap.addEventListener('click', () => goToPage(i))
        frag.appendChild(wrap)
      }
      thumbsRef.value.appendChild(frag)
    }

    loading.value = false
    requestAnimationFrame(setupObs)
  } catch {
    loadError.value = true
    loading.value = false
  }
}

// ── Observer ────────────────────────────────────────────────────────────────
function setupRenderObs(): void {
  if (!scrollRef.value) return
  renderObs = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue
        const el = e.target as HTMLDivElement
        const n = Number(el.dataset.pageNum)
        if (!renderedSet.has(n)) { renderedSet.add(n); renderPage(n, el) }
      }
    },
    { root: scrollRef.value, rootMargin: '600px 0px', threshold: 0 },
  )
  scrollRef.value.querySelectorAll('.pvr-page').forEach((el) => renderObs!.observe(el))
}

function setupThumbObs(): void {
  if (!thumbsRef.value) return
  thumbObs = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue
        const el = e.target as HTMLDivElement
        const n = Number(el.dataset.thumbNum)
        const cvs = el.querySelector('canvas') as HTMLCanvasElement | null
        if (!renderedThumbSet.has(n) && cvs) { renderedThumbSet.add(n); renderThumb(n, cvs) }
      }
    },
    { root: thumbsRef.value, rootMargin: '300px 0px', threshold: 0 },
  )
  thumbsRef.value.querySelectorAll('.pvr-thumb').forEach((el) => thumbObs!.observe(el))
}

function setupObs(): void {
  setupRenderObs()
  setupThumbObs()
}

// ── 渲染单页（含文字层） ────────────────────────────────────────────────────
async function renderPage(n: number, container: HTMLDivElement): Promise<void> {
  if (!pdfDoc) return
  try {
    const page = await pdfDoc.getPage(n)
    const vp = page.getViewport({ scale: scale.value })
    container.style.position = 'relative'

    const cvs = document.createElement('canvas')
    cvs.width = vp.width
    cvs.height = vp.height
    // canvas 不拦截鼠标，让文字层可以正常被选中
    cvs.style.cssText = 'display:block;position:absolute;top:0;left:0;pointer-events:none'
    container.appendChild(cvs)
    await page.render({ canvas: cvs, viewport: vp }).promise

    const td = document.createElement('div')
    // pdfjs-dist 6.x: 容器必须有 textLayer 类，CSS 规则才能生效
    td.className = 'textLayer'
    td.style.cssText = 'position:absolute;top:0;left:0;pointer-events:auto'
    // TextLayer 内部用 CSS calc(var(--total-scale-factor) * rawDims.pageWidth) 设置宽高
    // --total-scale-factor = vp.scale * vp.userUnit（我们直接用像素级 scale，不需再乘 PDF_TO_CSS）
    td.style.setProperty('--total-scale-factor', String(vp.scale * vp.userUnit))
    td.style.setProperty('--scale-round-x', '1px')
    td.style.setProperty('--scale-round-y', '1px')
    container.appendChild(td)

    const textLayer = new pdfjsLib.TextLayer({
      textContentSource: page.streamTextContent(),
      container: td,
      viewport: vp,
    })
    await textLayer.render()
  } catch (e) { console.warn('[PdfViewer] page', n, e) }
}

// ── 渲染缩略图 ───────────────────────────────────────────────────────────────
async function renderThumb(n: number, cvs: HTMLCanvasElement): Promise<void> {
  if (!pdfDoc) return
  try {
    const page = await pdfDoc.getPage(n)
    const vp = page.getViewport({ scale: THUMB_SCALE })
    cvs.width = vp.width
    cvs.height = vp.height
    await page.render({ canvas: cvs, viewport: vp }).promise
  } catch { /* ignore */ }
}

// ── 页面导航 ─────────────────────────────────────────────────────────────────
function goToPage(n: number): void {
  const el = scrollRef.value?.querySelector<HTMLElement>(`[data-page-num="${n}"]`)
  el?.scrollIntoView({ block: 'start', behavior: 'smooth' })
}

function activateThumb(n: number): void {
  if (!thumbsRef.value) return
  let target: HTMLElement | undefined
  thumbsRef.value.querySelectorAll('.pvr-thumb').forEach((el) => {
    const active = Number((el as HTMLElement).dataset.thumbNum) === n
    el.classList.toggle('pvr-thumb-active', active)
    if (active) target = el as HTMLElement
  })
  target?.scrollIntoView({ block: 'nearest', behavior: 'auto' })
}

function onMainScroll(): void {
  if (!scrollRef.value || !totalPages.value) return
  const top = scrollRef.value.scrollTop
  const pages = scrollRef.value.querySelectorAll<HTMLDivElement>('.pvr-page')
  let found = 1
  for (const el of pages) {
    if (el.offsetTop <= top + 80) found = Number(el.dataset.pageNum) || found
    else break
  }
  if (found !== currentPage.value) {
    currentPage.value = found
    activateThumb(found)
  }
}

// ── 缩放 ─────────────────────────────────────────────────────────────────────
function zoomIn(): void {
  if (scale.value >= SCALE_MAX || zooming.value) return
  scale.value = parseFloat(Math.min(SCALE_MAX, scale.value + SCALE_STEP).toFixed(2))
  applyZoom()
}

function zoomOut(): void {
  if (scale.value <= SCALE_MIN || zooming.value) return
  scale.value = parseFloat(Math.max(SCALE_MIN, scale.value - SCALE_STEP).toFixed(2))
  applyZoom()
}

function resetZoom(): void {
  if (scale.value === SCALE_DEFAULT || zooming.value) return
  scale.value = SCALE_DEFAULT
  applyZoom()
}

function applyZoom(): void {
  if (!pdfDoc || !scrollRef.value) return
  zooming.value = true
  renderObs?.disconnect()
  renderedSet.clear()
  const s = scale.value
  pdfDoc.getPage(1).then((page) => {
    const vp = page.getViewport({ scale: s })
    scrollRef.value?.querySelectorAll<HTMLDivElement>('.pvr-page').forEach((div) => {
      div.style.width = vp.width + 'px'
      div.style.height = vp.height + 'px'
      div.innerHTML = ''
    })
    requestAnimationFrame(() => {
      setupRenderObs()
      zooming.value = false
    })
  })
}

// ── 文字选中 ─────────────────────────────────────────────────────────────────
function onSelectionChange(): void {
  const sel = window.getSelection()
  const text = sel?.toString().trim() ?? ''
  if (text.length > 0) {
    // 只接受 PDF 滚动区内的选中
    const range = sel?.rangeCount ? sel.getRangeAt(0) : null
    if (scrollRef.value?.contains(range?.commonAncestorContainer ?? null)) {
      emit('text-selected', text)
    }
  } else {
    // 等焦点稳定后判断：若焦点移到 viewer 外部（如 AI 输入框），则保留选中状态
    setTimeout(() => {
      const active = document.activeElement
      const focusInViewer = !active || active === document.body || rootRef.value?.contains(active)
      if (focusInViewer) emit('selection-cleared')
    }, 50)
  }
}

watch(() => props.src, (url) => { if (url) init(url) })

onMounted(() => {
  document.addEventListener('selectionchange', onSelectionChange)
  if (props.src) init(props.src)
})
onBeforeUnmount(() => {
  document.removeEventListener('selectionchange', onSelectionChange)
  renderObs?.disconnect()
  thumbObs?.disconnect()
  pdfDoc?.cleanup()
})
</script>

<template>
  <div ref="rootRef" class="pvr-root">
    <!-- 工具栏 -->
    <div class="pvr-toolbar" :style="{ visibility: loading || loadError ? 'hidden' : 'visible' }">
      <div class="pvr-zoom-group">
        <button
          class="pvr-tb-btn"
          title="缩小"
          :disabled="scale <= SCALE_MIN || zooming"
          @click="zoomOut"
        >
          <svg viewBox="0 0 14 14" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="2" y1="7" x2="12" y2="7" />
          </svg>
        </button>
        <button
          class="pvr-tb-scale"
          title="点击恢复默认缩放"
          :disabled="zooming"
          @click="resetZoom"
        >
          {{ zoomLabel }}
        </button>
        <button
          class="pvr-tb-btn"
          title="放大"
          :disabled="scale >= SCALE_MAX || zooming"
          @click="zoomIn"
        >
          <svg viewBox="0 0 14 14" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="7" y1="2" x2="7" y2="12" />
            <line x1="2" y1="7" x2="12" y2="7" />
          </svg>
        </button>
      </div>
      <div class="pvr-page-info">
        第 <strong>{{ currentPage }}</strong> / {{ totalPages }} 页
      </div>
    </div>

    <!-- 主体：左侧缩略图 + 右侧主滚动区 -->
    <div class="pvr-body">
      <div ref="thumbsRef" class="pvr-thumbs" />
      <div ref="scrollRef" class="pvr-scroll" @scroll="onMainScroll" />
    </div>

    <!-- 加载 / 错误 遮罩 -->
    <div v-if="loading || loadError" class="pvr-overlay">
      <template v-if="loading">
        <div class="pvr-spinner" />
        <span>加载 PDF 中…</span>
      </template>
      <template v-else>
        <div class="pvr-err-icon" style="display:inline-flex;align-items:center;justify-content:center;color:var(--x-error, oklch(58% 0.20 25))"><IconWarn :size="32" /></div>
        <p class="pvr-err-msg">PDF 加载失败</p>
        <a :href="src" target="_blank" rel="noopener" class="pvr-open-link">在新标签页打开</a>
      </template>
    </div>
  </div>
</template>

<!-- 全局：PDF.js 动态注入的元素，无法使用 scoped -->
<!-- .textLayer 规则直接对应 pdfjs-dist/web/pdf_viewer.css，必须完整复制 -->
<style>
/* ── pdfjs-dist 6.x TextLayer 必需 CSS ───────────────────────────── */
.pvr-scroll .textLayer {
  position: absolute;
  text-align: initial;
  inset: 0;
  overflow: clip;
  opacity: 1;
  line-height: 1;
  text-size-adjust: none;
  forced-color-adjust: none;
  transform-origin: 0 0;
  caret-color: CanvasText;
  z-index: 0;
  --min-font-size: 1;
  --text-scale-factor: calc(var(--total-scale-factor) * var(--min-font-size));
  --min-font-size-inv: calc(1 / var(--min-font-size));
  pointer-events: auto;
}

.pvr-scroll .textLayer :is(span, br) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
  user-select: text;
  -webkit-user-select: text;
}

/* 关键：字号 + transform，缺少此规则所有文字尺寸为 0 */
.pvr-scroll .textLayer > :not(.markedContent),
.pvr-scroll .textLayer .markedContent span:not(.markedContent) {
  z-index: 1;
  --font-height: 0;
  font-size: calc(var(--text-scale-factor) * var(--font-height));
  --scale-x: 1;
  --rotate: 0deg;
  transform: rotate(var(--rotate)) scaleX(var(--scale-x)) scale(var(--min-font-size-inv));
}

.pvr-scroll .textLayer .endOfContent {
  display: block;
  position: absolute;
  inset: 100% 0 0;
  z-index: 0;
  cursor: default;
  user-select: none;
}

.pvr-scroll .textLayer.selecting .endOfContent {
  top: 0;
}

.pvr-scroll .textLayer ::selection {
  background-color: rgba(30, 90, 224, 0.3);
  color: transparent;
}

.pvr-scroll .textLayer br::selection {
  background: transparent;
}

/* JS 创建的页面和缩略图容器 */
.pvr-page {
  background: #fff;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.08), 0 8px 24px rgba(15, 23, 42, 0.04);
  flex-shrink: 0;
}

.pvr-thumb {
  cursor: pointer;
  border: 2px solid var(--x-hairline);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: border-color 0.14s;
  flex-shrink: 0;
  width: 90px;
}
.pvr-thumb:hover { border-color: var(--x-primary-soft); }
.pvr-thumb-active { border-color: var(--x-primary) !important; }

.pvr-thumb-canvas {
  display: block;
  background: #fff;
  width: 100%;
  height: auto;
}
.pvr-thumb-num {
  font-size: 10px;
  color: var(--x-mute);
  font-family: var(--x-font-mono);
  padding: 2px 0;
  text-align: center;
  width: 100%;
  background: var(--x-canvas-soft);
  font-variant-numeric: tabular-nums;
}
.pvr-thumb-active .pvr-thumb-num {
  color: var(--x-primary);
  font-weight: 600;
  background: var(--x-primary-soft);
}
</style>

<style scoped>
/* ── 根容器 ───────────────────────────────────────────── */
.pvr-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--x-canvas-mid);
  overflow: hidden;
  position: relative;
}

/* ── 工具栏 ───────────────────────────────────────────── */
.pvr-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 14px;
  background: var(--x-canvas);
  border-bottom: 1px solid var(--x-hairline);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.pvr-zoom-group {
  display: flex;
  align-items: center;
  gap: 3px;
}

.pvr-tb-btn {
  width: 26px;
  height: 26px;
  border-radius: var(--x-rounded-sm);
  border: 1px solid var(--x-hairline);
  background: var(--x-canvas-soft);
  color: var(--x-body);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.13s, color 0.13s;
}
.pvr-tb-btn:hover:not(:disabled) {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.pvr-tb-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.pvr-tb-scale {
  padding: 3px 8px;
  min-width: 52px;
  border-radius: var(--x-rounded-sm);
  border: 1px solid var(--x-hairline);
  background: var(--x-canvas-soft);
  color: var(--x-body-mid);
  font-size: 11px;
  font-family: var(--x-font-mono);
  font-weight: 500;
  cursor: pointer;
  text-align: center;
  transition: border-color 0.13s, color 0.13s;
}
.pvr-tb-scale:hover:not(:disabled) {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.pvr-tb-scale:disabled { opacity: 0.5; cursor: not-allowed; }

.pvr-page-info {
  margin-left: auto;
  font-size: 12px;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  font-variant-numeric: tabular-nums;
}
.pvr-page-info strong {
  color: var(--x-primary);
  font-weight: 700;
}

/* ── 主体 ─────────────────────────────────────────────── */
.pvr-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── 左侧缩略图面板 ───────────────────────────────────── */
.pvr-thumbs {
  width: 110px;
  flex-shrink: 0;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--x-canvas-soft);
  border-right: 1px solid var(--x-hairline);
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  scrollbar-width: thin;
  scrollbar-color: var(--x-hairline) transparent;
}
.pvr-thumbs::-webkit-scrollbar { width: 4px; }
.pvr-thumbs::-webkit-scrollbar-thumb { background: var(--x-hairline); border-radius: 4px; }

/* ── 主滚动区 ─────────────────────────────────────────── */
.pvr-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: var(--x-hairline-strong) transparent;
}
.pvr-scroll::-webkit-scrollbar { width: 8px; }
.pvr-scroll::-webkit-scrollbar-thumb {
  background: var(--x-hairline-strong);
  border-radius: 4px;
}

/* ── 加载/错误遮罩 ────────────────────────────────────── */
.pvr-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--x-canvas-mid);
  color: var(--x-body-mid);
  font-size: 13px;
  z-index: 10;
}

.pvr-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--x-hairline);
  border-top-color: var(--x-primary);
  border-radius: 50%;
  animation: pvr-spin 0.8s linear infinite;
}
@keyframes pvr-spin { to { transform: rotate(360deg); } }

.pvr-err-icon { font-size: 28px; color: var(--x-warning); }
.pvr-err-msg { color: var(--x-body); margin: 0; }
.pvr-open-link {
  display: inline-block;
  padding: 6px 14px;
  background: var(--x-primary);
  color: #fff;
  border-radius: var(--x-rounded-pill);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s;
}
.pvr-open-link:hover { background: var(--x-primary-hover); }
</style>
