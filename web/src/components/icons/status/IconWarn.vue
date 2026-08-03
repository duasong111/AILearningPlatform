<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 3.5 L21.5 20 A1.5 1.5 0 0 1 20.2 22 H3.8 A1.5 1.5 0 0 1 2.5 20 Z" fill="#DBE7FF" />
    <line x1="12" y1="9" x2="12" y2="14.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <circle cx="12" cy="17.5" r="1.1" fill="currentColor" />
  </svg>
</template>
