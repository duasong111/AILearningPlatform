<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: filled triangle -->
    <path d="M4 19 L20 19 L12 5 Z" fill="#DBE7FF" />
    <!-- primary: triangle outline + interior altitude + 90° marker -->
    <path d="M4 19 L20 19 L12 5 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M12 5 L12 19" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2 1.5" stroke-linecap="round" />
    <path d="M11 19 L11 17 L13 17 L13 19" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" />
  </svg>
</template>
