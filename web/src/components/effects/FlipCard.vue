<script setup lang="ts">
/**
 * FlipCard — inspira-ui 移植版
 *   上游: https://github.com/unovue/inspira-ui (app/components/inspira/ui/flip-card/FlipCard.vue)
 *   原作者: Aceternity UI, MIT License
 *
 * 上游用 Tailwind, 这里翻译为 scoped CSS + 项目设计 token:
 *   - perspective-[1000px]  → perspective: 1000px
 *   - transform-3d           → transform-style: preserve-3d
 *   - backface-hidden        → backface-visibility: hidden
 *   - group-hover:transform-[rotateY(180deg)] → .group:hover .card { transform: rotateY(180deg) }
 *
 * 用法:
 *   <FlipCard>
 *     <h3>正面内容</h3>
 *     <template #back>
 *       <p>背面内容</p>
 *     </template>
 *   </FlipCard>
 *
 * Props:
 *   rotate  'x' 水平翻转 (上下翻) | 'y' 垂直翻转 (左右翻), 默认 'y'
 *   width   卡宽 (px), 默认 224 (w-56)
 *   height  卡高 (px), 默认 288 (h-72)
 *   class   额外 class
 */

interface FlipCardProps {
  rotate?: 'x' | 'y'
  width?: number
  height?: number
  class?: string
}

const props = withDefaults(defineProps<FlipCardProps>(), {
  rotate: 'y',
  width: 224,
  height: 288,
})

// 上游 cn() 等价: 过滤掉空值再 join
function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
</script>

<template>
  <div
    :class="cn('x-flip', props.class)"
    :style="{
      '--flip-w': `${width}px`,
      '--flip-h': `${height}px`,
    }"
  >
    <div :class="cn('x-flip-card', `is-${rotate}`)">
      <!-- 正面: 默认 slot -->
      <div class="x-flip-face x-flip-front">
        <slot />
      </div>

      <!-- 背面: 命名 slot #back -->
      <div :class="cn('x-flip-face x-flip-back', `is-${rotate}`)">
        <slot name="back" />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 外层: perspective 容器 ──────────────────────── */
.x-flip {
  width: var(--flip-w, 224px);
  height: var(--flip-h, 288px);
  perspective: 1000px;             /* 上游 perspective-[1000px] */
  /* 兼容 webkit */
  -webkit-perspective: 1000px;
}

/* ── 内部: 翻转容器 (group hover 时整体旋转 180°) ── */
.x-flip-card {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  transform-style: preserve-3d;   /* 上游 transform-3d */
  -webkit-transform-style: preserve-3d;
}

/* hover 翻转: rotate='y' 时绕 Y 轴 (左右翻), rotate='x' 时绕 X 轴 (上下翻) */
.x-flip:hover .x-flip-card.is-y { transform: rotateY(180deg); }
.x-flip:hover .x-flip-card.is-x { transform: rotateX(180deg); }

/* ── 共用: 两面共享基础 ─────────────────────────── */
.x-flip-face {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 16px;            /* 上游 rounded-2xl */
  border: 1px solid var(--x-hairline);
  backface-visibility: hidden;     /* 上游 backface-hidden */
  -webkit-backface-visibility: hidden;
}

/* 正面默认 slot 容器: 由调用方决定内部样式, 这里只给浅底 */
.x-flip-front {
  background: var(--x-canvas);
}

/* 背面: 上游 bg-black/80 + text-slate-200 + p-4, 翻译为深底 */
.x-flip-back {
  background: rgba(13, 17, 24, 0.92);
  color: oklch(82% 0.02 255);
  padding: 16px;
  /* 初始就反着摆, 翻 180° 后才"正"过来 */
  transform: rotateY(180deg);
  -webkit-transform: rotateY(180deg);
}
.x-flip-back.is-x {
  /* X 轴翻: 上下翻, 初始 rotateX */
  transform: rotateX(180deg);
  -webkit-transform: rotateX(180deg);
}

/* hover 时: 正面 Y 翻 → 背面 Y 翻, 总和抵消回到正面 */
.x-flip:hover .x-flip-back.is-y {
  transform: rotateY(360deg);
  -webkit-transform: rotateY(360deg);
}
.x-flip:hover .x-flip-back.is-x {
  transform: rotateX(360deg);
  -webkit-transform: rotateX(360deg);
}
</style>