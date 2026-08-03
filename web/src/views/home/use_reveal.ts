import { onMounted, onBeforeUnmount, nextTick } from 'vue'

/**
 * 滚动揭示 composable —— 元素进入视口时加 is-visible 类。
 *
 * 默认监控所有挂在 `.x-reveal` 上的元素,触发后即取消监听。
 * 配合 CSS 中 `.x-reveal { opacity: 0; transform: translateY(20px) }`
 * 与 `.x-reveal.is-visible { opacity: 1; transform: none }` 实现淡入上滑。
 */
export interface UseRevealOptions {
  /** 监控的元素选择器,默认 ".x-reveal" */
  selector?: string
  /** 触发后加的类名,默认 "is-visible" */
  visibleClass?: string
  /** IntersectionObserver 阈值 */
  threshold?: number
  /** IntersectionObserver rootMargin */
  rootMargin?: string
}

export function useReveal(options: UseRevealOptions = {}): { rescan: () => void } {
  const {
    selector = '.x-reveal',
    visibleClass = 'is-visible',
    threshold = 0.12,
    rootMargin = '0px 0px -8% 0px',
  } = options

  let observer: IntersectionObserver | null = null

  function rescan(): void {
    observer?.disconnect()
    observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add(visibleClass)
            observer?.unobserve(e.target)
          }
        }
      },
      { threshold, rootMargin }
    )
    document.querySelectorAll(selector).forEach((el) => observer!.observe(el))
  }

  onMounted(async () => {
    await nextTick()
    rescan()
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
  })

  return { rescan }
}
