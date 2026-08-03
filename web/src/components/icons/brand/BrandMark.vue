<script setup lang="ts">
/**
 * BrandMark —— 站标 (navbar / 品牌位)
 *
 * 设计跟浏览器 favicon (public/favicon.svg) 保持一致:
 *   - 实色主蓝圆角方背景 (var(--x-primary), 亮 / 暗主题都跟随)
 *   - 白色 L 路径 (左下直角)
 *   - 白色单圆点 (右上, 跟 favicon 一致, 移除斜向左下第二个点 → 更干净)
 *
 * 背景用 token, 前景硬白 —— 因为白字配实色蓝底在亮 / 暗主题下都高对比.
 */
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 22" :height="size ?? 22" viewBox="0 0 24 24" aria-hidden="true">
    <!-- 实色蓝底圆角方 -->
    <rect x="2" y="2" width="20" height="20" rx="5" fill="var(--x-primary)" />

    <!-- 白色 L 形 (左下直角, 开口朝右上) -->
    <path d="M8 8 V16 H16"
      fill="none" stroke="#FFFFFF" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round" />

    <!-- 白色单圆点 (右上) -->
    <circle cx="16" cy="8" r="2" fill="#FFFFFF" />
  </svg>
</template>