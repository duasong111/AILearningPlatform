<script setup lang="ts">
/**
 * StreamingMarkdown — 流式 Markdown 渲染组件（简洁版）
 *
 *   - 流式进行中: 直接渲染 markdown，底部闪烁光标
 *   - 流式结束: 光标消失，markdown 完整展示
 *   - 自动解析 <think>...</think> 思考标签为收起块
 */
import { computed } from 'vue'
import MarkdownContent from './MarkdownContent.vue'

const props = defineProps<{
  text: string
  pending?: boolean
}>()

/** 解析思考标签和正文 */
function parseContent(raw: string): { thinkText: string; mainText: string; isThinking: boolean } {
  const trimmed = raw.trimStart()
  if (!trimmed.startsWith('<think>')) {
    return { thinkText: '', mainText: raw, isThinking: false }
  }
  const closeIdx = trimmed.indexOf('</think>')
  if (closeIdx === -1) {
    return { thinkText: trimmed.slice(7), mainText: '', isThinking: true }
  }
  return {
    thinkText: trimmed.slice(7, closeIdx).trim(),
    mainText: trimmed.slice(closeIdx + 8).trim(),
    isThinking: false,
  }
}

const parsed = computed(() => parseContent(props.text))
</script>

<template>
  <div class="x-stream-md">
    <!-- 思考块（如果有） -->
    <details v-if="parsed.thinkText" class="x-think" :open="parsed.isThinking">
      <summary class="x-think-summary">
        <span class="x-think-label">
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><circle cx="5" cy="5" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M5 3v2.5l1.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          {{ parsed.isThinking ? '思考中…' : '已思考' }}
        </span>
      </summary>
      <p class="x-think-text">{{ parsed.thinkText }}</p>
    </details>

    <!-- 正文 markdown：始终清晰渲染，流式时末尾加光标 -->
    <div v-if="parsed.mainText" class="x-stream-md-body" :class="{ 'is-streaming': pending }">
      <MarkdownContent :text="parsed.mainText" />
      <span v-if="pending" class="x-cursor">|</span>
    </div>
  </div>
</template>

<style scoped>
.x-stream-md { position: relative; }

/* 思考块 */
.x-think {
  margin-bottom: 8px;
  border: 1px solid var(--x-hairline);
  border-radius: 8px;
  overflow: hidden;
}
.x-think-summary {
  padding: 6px 10px;
  cursor: pointer;
  font-size: 12px;
  color: var(--x-body-mid);
  background: var(--x-canvas-soft);
  user-select: none;
}
.x-think-label {
  display: inline-flex; align-items: center; gap: 4px;
}
.x-think-text {
  padding: 6px 10px;
  margin: 0;
  font-size: 12px;
  color: var(--x-body-mid);
  white-space: pre-wrap;
}

/* 正文 */
.x-stream-md-body.is-streaming {
  /* streaming 中无额外样式干扰 */
}

/* 闪烁光标 */
.x-cursor {
  display: inline;
  color: var(--x-primary);
  font-weight: 700;
  animation: x-blink 0.8s step-end infinite;
}
@keyframes x-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
