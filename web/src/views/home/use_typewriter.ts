import { ref, onMounted, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'

/**
 * 循环打字效果 composable —— Hero 词语循环用。
 *
 * 输入一组词,按"逐字打 → 停顿 → 逐字删 → 下一词"的节奏循环。
 * 同时返回一个闪烁的光标 ref(showCursor),实现终端式效果。
 */
export interface UseTypewriterOptions {
  /** 每字打字间隔,默认 130ms */
  typeMs?: number
  /** 每字删除间隔,默认 60ms */
  deleteMs?: number
  /** 整词显示完后的停顿,默认 1600ms */
  holdMs?: number
  /** 光标闪烁周期,默认 600ms */
  cursorMs?: number
}

export function useTypewriter(
  words: string[],
  options: UseTypewriterOptions = {}
): { text: Ref<string>; showCursor: Ref<boolean> } {
  const {
    typeMs = 130,
    deleteMs = 60,
    holdMs = 1600,
    cursorMs = 600,
  } = options

  const text = ref<string>('')
  const showCursor = ref<boolean>(true)
  let typingTimer: number | null = null
  let cursorTimer: number | null = null

  function run(): void {
    if (words.length === 0) return
    let wordIdx = 0
    let charIdx = 0
    let deleting = false

    const step = (): void => {
      const word = words[wordIdx] ?? ''
      if (!deleting) {
        text.value = word.slice(0, charIdx + 1)
        charIdx++
        if (charIdx >= word.length) {
          typingTimer = window.setTimeout(() => {
            deleting = true
            step()
          }, holdMs)
          return
        }
      } else {
        text.value = word.slice(0, charIdx - 1)
        charIdx--
        if (charIdx <= 0) {
          deleting = false
          wordIdx = (wordIdx + 1) % words.length
        }
      }
      typingTimer = window.setTimeout(step, deleting ? deleteMs : typeMs)
    }

    step()
  }

  onMounted(() => {
    cursorTimer = window.setInterval(() => {
      showCursor.value = !showCursor.value
    }, cursorMs)
    run()
  })

  onBeforeUnmount(() => {
    if (typingTimer !== null) window.clearTimeout(typingTimer)
    if (cursorTimer !== null) window.clearInterval(cursorTimer)
  })

  return { text, showCursor }
}
