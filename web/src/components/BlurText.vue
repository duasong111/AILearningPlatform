<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue'

/**
 * Blur Text 流式渲染组件
 *
 * 效果: 全局字符队列，10ms 出一个字，逐个从模糊 + 缩放出现
 * - streaming=true: 新字符进队列，10ms 间隔 pop，逐字动画
 * - streaming=false: 所有字符直接显示，无动画
 */
const props = withDefaults(
  defineProps<{
    text: string
    streaming?: boolean   // 流式进行中时才走队列
    stepDuration?: number // 相邻字符出队间隔 ms，默认 10
  }>(),
  { streaming: true, stepDuration: 10 },
)

const displayedChars = ref<string[]>([])   // 已显示的字符
const pendingQueue = ref<string[]>([])     // 待显示字符队列
let timer: ReturnType<typeof setTimeout> | null = null

function scheduleNext() {
  // 不论 timer 是否在跑，每次追加新字符都确保下一次 flush 已安排
  if (timer !== null) return
  timer = setTimeout(() => {
    timer = null
    flushQueue()
  }, props.stepDuration)
}

function flushQueue() {
  const ch = pendingQueue.value.shift()
  if (ch === undefined) return
  displayedChars.value.push(ch)
  if (pendingQueue.value.length > 0) {
    scheduleNext()
  }
}

function reset() {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
  displayedChars.value = []
  pendingQueue.value = []
}

watch(
  () => props.text,
  (newText) => {
    if (!newText) {
      reset()
      return
    }

    const current = displayedChars.value.join('') + pendingQueue.value.join('')
    // 去掉<think>...</think>思考标签
    if (newText !== newText.replace(/<think>[\s\S]*?<\/think>/g, '')) {
      newText = newText.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
    }

    // 文本缩短 → 重置
    if (newText.length <= current.length) {
      reset()
      if (!props.streaming) {
        displayedChars.value = newText.split('')
      }
      return
    }

    // 非流式：直接显示，跳过队列
    if (!props.streaming) {
      reset()
      displayedChars.value = newText.split('')
      return
    }

    // 流式：追加新字符到队列
    const newChars = newText.slice(current.length).split('')
    pendingQueue.value.push(...newChars)
    scheduleNext()
  },
  { immediate: true },
)

onBeforeUnmount(() => reset())
</script>

<template>
  <span class="blur-text" aria-live="polite">
    <span
      v-for="(c, i) in displayedChars"
      :key="i"
      class="blur-text-char"
    >{{ c === ' ' ? ' ' : c }}</span>
  </span>
</template>

<style scoped>
.blur-text {
  display: inline;
  word-break: break-word;
}

.blur-text-char {
  display: inline-block;
  transform-origin: center bottom;
  animation: char-appear 350ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes char-appear {
  0% {
    opacity: 0;
    filter: blur(6px);
    transform: scale(0.7) translateY(3px);
  }
  50% {
    opacity: 0.85;
    filter: blur(1px);
    transform: scale(1.04) translateY(0);
  }
  100% {
    opacity: 1;
    filter: blur(0);
    transform: scale(1) translateY(0);
  }
}
</style>