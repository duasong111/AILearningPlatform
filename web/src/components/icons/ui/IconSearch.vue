<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="10" cy="10" r="6" fill="#DBE7FF" />
    <circle cx="10" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="1.6" />
    <line x1="14.5" y1="14.5" x2="20" y2="20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  </svg>
</template>
