<script setup lang="ts">
import { computed, watch, nextTick, onBeforeUnmount, ref } from 'vue'
import { renderMarkdown } from '@/composables/use_markdown'
import MindMap from 'simple-mind-map'
import 'simple-mind-map/dist/simpleMindMap.esm.min.css'

/**
 * Markdown + LaTeX 公式渲染 + 思维导图
 *
 *   - 自动跑 markdown-it + KaTeX + highlight.js
 *   - 识别 ```mindmap 代码块，渲染为交互式思维导图
 *   - 流式安全: 不完整 markdown / 公式不崩, 退化成原文
 *   - html:false, 不允许 AI 注入原生 HTML
 */

const props = defineProps<{ text?: string; content?: string }>()
const html = computed(() => renderMarkdown(props.text ?? props.content ?? ''))
const containerRef = ref<HTMLElement>()

// 思维导图实例列表，用于清理
const mindMapInstances: MindMap[] = []

function destroyMindMaps(): void {
  for (const mm of mindMapInstances) {
    try { mm.destroy() } catch { /* ignore */ }
  }
  mindMapInstances.length = 0
}

function mountMindMaps(): void {
  const el = containerRef.value
  if (!el) return

  const placeholders = el.querySelectorAll<HTMLElement>('.x-md-mindmap-placeholder')
  for (const ph of placeholders) {
    // 跳过已挂载的
    if (ph.dataset.mounted) continue

    const encoded = ph.dataset.mindmap
    if (!encoded) continue

    try {
      const json = decodeURIComponent(
        atob(encoded).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
      )
      const data = JSON.parse(json)

      // 清空占位内容
      ph.innerHTML = ''
      ph.style.height = '400px'
      ph.style.width = '100%'
      ph.style.borderRadius = '12px'
      ph.style.overflow = 'hidden'
      ph.style.background = '#fafbfd'
      ph.dataset.mounted = 'true'

      // simple-mind-map 的 d.ts 极严, 这里只用到它真实支持的子集 —— cast any 跳过类型噪音
      const mm = new (MindMap as any)({
        el: ph,
        data,
        readonly: true,
        layout: 'mindMap',
        theme: 'primary',
        themeConfig: {
          primaryColor: '#0071e3',
          bgColor: '#fafbfd',
          lineColor: '#c0c6cf',
        },
        enableShortcutOnlyWhenMouseInSvg: true,
        mousewheelAction: 'zoom',
      })
      mindMapInstances.push(mm)
    } catch (err) {
      console.warn('[MarkdownContent] failed to mount mindmap:', err)
      ph.textContent = '思维导图渲染失败'
    }
  }
}

// 文本变化时重新挂载
watch(() => props.text, () => {
  destroyMindMaps()
  nextTick(() => mountMindMaps())
}, { immediate: true })

onBeforeUnmount(() => {
  destroyMindMaps()
})
</script>

<template>
  <div ref="containerRef" class="x-md" v-html="html"></div>
</template>

<style scoped>
.x-md {
  font-family: var(--x-font-display);
  font-size: 14px;
  line-height: 1.65;
  color: var(--x-ink);
  word-wrap: break-word;
}

/* ============================================================
   Typography (深度选择器, 穿透 v-html 子节点)
   ============================================================ */
.x-md :deep(h1),
.x-md :deep(h2),
.x-md :deep(h3),
.x-md :deep(h4),
.x-md :deep(h5),
.x-md :deep(h6) {
  font-family: var(--x-font-display);
  font-weight: 600;
  color: var(--x-ink);
  margin: 14px 0 8px;
  line-height: 1.3;
  letter-spacing: -0.2px;
}
.x-md :deep(h1) { font-size: 20px; border-bottom: 1px solid var(--x-hairline); padding-bottom: 4px; }
.x-md :deep(h2) { font-size: 17px; }
.x-md :deep(h3) { font-size: 15px; }
.x-md :deep(h4),
.x-md :deep(h5),
.x-md :deep(h6) { font-size: 14px; }
.x-md :deep(h1:first-child),
.x-md :deep(h2:first-child),
.x-md :deep(h3:first-child) { margin-top: 0; }

.x-md :deep(p) {
  margin: 6px 0;
}
.x-md :deep(p:first-child) { margin-top: 0; }
.x-md :deep(p:last-child) { margin-bottom: 0; }

.x-md :deep(strong) { font-weight: 600; color: var(--x-ink); }
.x-md :deep(em) { font-style: italic; }

/* ============================================================
   Lists
   ============================================================ */
.x-md :deep(ul),
.x-md :deep(ol) {
  margin: 6px 0;
  padding-left: 22px;
}
.x-md :deep(li) {
  margin: 2px 0;
}
.x-md :deep(li > p) {                 /* 内嵌段落: 不要再加 margin */
  margin: 0;
}

/* ============================================================
   Code
   ============================================================ */
.x-md :deep(code) {
  font-family: var(--x-font-mono);
  font-size: 12.5px;
  background: var(--x-canvas-mid);
  color: var(--x-ink);
  padding: 1px 6px;
  border-radius: 4px;
  word-wrap: break-word;
}
.x-md :deep(pre) {
  margin: 10px 0;
  padding: 12px 14px;
  background: var(--x-ink);            /* 暗背景, 突出代码块 */
  color: #e1e7ef;
  border-radius: var(--x-rounded-sm);
  overflow-x: auto;
  font-size: 12.5px;
  line-height: 1.55;
}
.x-md :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: inherit;
  border-radius: 0;
}

/* ============================================================
   Blockquote / hr
   ============================================================ */
.x-md :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid var(--x-primary);
  background: var(--x-canvas-tint);
  color: var(--x-body);
}
.x-md :deep(blockquote > p) { margin: 4px 0; }
.x-md :deep(hr) {
  border: 0;
  border-top: 1px solid var(--x-hairline);
  margin: 14px 0;
}

/* ============================================================
   Tables
   ============================================================ */
.x-md :deep(table) {
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 13px;
  display: block;                       /* 让 overflow 生效 */
  overflow-x: auto;
  max-width: 100%;
}
.x-md :deep(th),
.x-md :deep(td) {
  border: 1px solid var(--x-hairline);
  padding: 6px 10px;
  text-align: left;
}
.x-md :deep(th) {
  background: var(--x-canvas-soft);
  font-weight: 600;
}
.x-md :deep(tr:nth-child(2n) td) {
  background: var(--x-canvas-soft);
}

/* ============================================================
   Links
   ============================================================ */
.x-md :deep(a) {
  color: var(--x-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.x-md :deep(a:hover) {
  text-decoration-thickness: 2px;
}

/* ============================================================
   Math (KaTeX) —— 包了一层 .eq / .eq-display 的容器
   KaTeX 自己有完整 CSS (main.ts 里全局导入), 这里只调整间距
   ============================================================ */
.x-md :deep(.katex-display) {
  margin: 10px 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 0;
}
.x-md :deep(.katex) {
  font-size: 1em;                       /* 跟正文字号一致, 不要默认的 1.21em */
}

/* ============================================================
   Image
   ============================================================ */
.x-md :deep(img) {
  max-width: 100%;
  border-radius: var(--x-rounded-sm);
  margin: 6px 0;
}
</style>
