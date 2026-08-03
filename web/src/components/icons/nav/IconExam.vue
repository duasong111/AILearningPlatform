<script setup lang="ts">
/**
 * IconExam — 评测 / 批改
 *   语义: 试卷 + 对勾 → "已批改 / 评测"
 *   duotone: 软色 (#DBE7FF) 纸张主体 + 主色 (currentColor) 边框 / 勾 / 顶部夹子
 */
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: paper body -->
    <path d="M6 4 H15 L18 7 V20 A1 1 0 0 1 17 21 H6 A1 1 0 0 1 5 20 V5 A1 1 0 0 1 6 4 Z"
      fill="#DBE7FF" />
    <!-- primary: paper outline + folded corner + clip + check -->
    <path d="M6 4 H15 L18 7 V20 A1 1 0 0 1 17 21 H6 A1 1 0 0 1 5 20 V5 A1 1 0 0 1 6 4 Z"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M15 4 V7 H18" fill="none" stroke="currentColor" stroke-width="1.6"
      stroke-linejoin="round" stroke-linecap="round" />
    <!-- check inside paper -->
    <path d="M8.5 13.5 L11 16 L15.5 11" fill="none" stroke="currentColor" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
