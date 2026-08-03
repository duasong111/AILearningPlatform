<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- 主色圆角方背景 -->
    <rect x="1" y="1" width="22" height="22" rx="5" fill="#1E5AE0" />

    <!-- 白色 L 形直角 (左下) -->
    <path d="M6 8 V16 H14"
      fill="none" stroke="#FFFFFF" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" />

    <!-- 白色圆点 1 (右上) -->
    <circle cx="17" cy="7" r="1.9" fill="#FFFFFF" />

    <!-- 白色圆点 2 (沿斜向左下) -->
    <circle cx="13" cy="12" r="1.9" fill="#FFFFFF" />
  </svg>
</template>