import { onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { Ref } from 'vue'

/**
 * 星空粒子背景 composable —— Hero 专用。
 *
 * 接收一个 canvas ref,在挂载后初始化粒子动画,卸载时释放
 * RAF/resize 监听。粒子颜色 95%+ 是白色,极少量 sunset/dusk
 * 与品牌设计文档(DESIGN-x.ai.md)一致。
 */
export interface UseStarfieldOptions {
  /** 粒子密度系数,默认 12000(每平方像素 12000 一颗) */
  densityDivisor?: number
  /** 粒子最少 / 最多颗数,夹住密度上下限 */
  minCount?: number
  maxCount?: number
}

interface Star {
  x: number
  y: number
  r: number
  vx: number
  vy: number
  alpha: number
  alphaDelta: number
  color: string
}

const STAR_COLORS = {
  white: 'rgba(255,255,255,1)',
  sunset: 'rgba(255,122,23,1)',
  dusk: 'rgba(124,58,237,1)',
}

export function useStarfield(
  canvasRef: Ref<HTMLCanvasElement | null>,
  options: UseStarfieldOptions = {}
): { stop: () => void } {
  const { densityDivisor = 12000, minCount = 50, maxCount = 120 } = options

  let rafId: number | null = null
  let resizeHandler: (() => void) | null = null

  function start(): void {
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    let stars: Star[] = []

    const seed = (): void => {
      const { offsetWidth: w, offsetHeight: h } = canvas
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.scale(dpr, dpr)
      const count = Math.min(
        maxCount,
        Math.max(minCount, Math.floor((w * h) / densityDivisor))
      )
      stars = Array.from({ length: count }, () => {
        const roll = Math.random()
        const color =
          roll > 0.96
            ? STAR_COLORS.sunset
            : roll > 0.92
              ? STAR_COLORS.dusk
              : STAR_COLORS.white
        return {
          x: Math.random() * w,
          y: Math.random() * h,
          r: Math.random() * 1.2 + 0.3,
          vx: (Math.random() - 0.5) * 0.12,
          vy: (Math.random() - 0.5) * 0.12,
          alpha: Math.random() * 0.6 + 0.15,
          alphaDelta: (Math.random() - 0.5) * 0.008,
          color,
        }
      })
    }

    const animate = (): void => {
      const { offsetWidth: w, offsetHeight: h } = canvas
      ctx.clearRect(0, 0, w, h)
      for (const s of stars) {
        s.x += s.vx
        s.y += s.vy
        s.alpha += s.alphaDelta
        if (s.alpha < 0.1 || s.alpha > 0.85) s.alphaDelta *= -1
        if (s.x < -2) s.x = w + 2
        if (s.x > w + 2) s.x = -2
        if (s.y < -2) s.y = h + 2
        if (s.y > h + 2) s.y = -2
        ctx.globalAlpha = s.alpha
        ctx.fillStyle = s.color
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.globalAlpha = 1
      rafId = requestAnimationFrame(animate)
    }

    seed()
    animate()
    resizeHandler = seed
    window.addEventListener('resize', seed)
  }

  function stop(): void {
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler)
      resizeHandler = null
    }
  }

  onMounted(async () => {
    await nextTick()
    start()
  })

  onBeforeUnmount(stop)

  return { stop }
}
