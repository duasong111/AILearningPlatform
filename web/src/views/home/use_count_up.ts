import { ref, onMounted, onBeforeUnmount } from 'vue'
import type { Ref } from 'vue'

/**
 * 数字"从 0 滚到目标值"动画 composable。
 *
 * 当指定的元素滚入视口时,启动一次 easeOutCubic 滚动,
 * 把 displayValues 各字符串实时格式化输出。
 */
export interface CountUpItem {
  target: number
  suffix: string
  decimals?: number
}

export interface UseCountUpOptions {
  /** 动画总时长,默认 1600ms */
  durationMs?: number
  /** IntersectionObserver 触发阈值,默认 0.4 */
  threshold?: number
}

export function useCountUp(
  items: CountUpItem[],
  triggerRef: Ref<HTMLElement | null>,
  options: UseCountUpOptions = {}
): { displayValues: Ref<string[]> } {
  const { durationMs = 1600, threshold = 0.4 } = options
  const displayValues = ref<string[]>(items.map(() => '0'))
  let observer: IntersectionObserver | null = null

  function format(value: number, item: CountUpItem): string {
    const decimals = item.decimals ?? 0
    if (decimals === 0 && item.target >= 1000) {
      return Math.floor(value).toLocaleString() + item.suffix
    }
    return value.toFixed(decimals) + item.suffix
  }

  function run(): void {
    const start = performance.now()
    const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3)

    const tick = (now: number): void => {
      const progress = Math.min(1, (now - start) / durationMs)
      const eased = easeOutCubic(progress)
      items.forEach((item, i) => {
        displayValues.value[i] = format(item.target * eased, item)
      })
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  onMounted(() => {
    if (!triggerRef.value) return
    observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            run()
            observer?.disconnect()
            break
          }
        }
      },
      { threshold }
    )
    observer.observe(triggerRef.value)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
  })

  return { displayValues }
}
