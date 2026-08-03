<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: sand fill bottom -->
    <path d="M7 4 H17 L13 12 L17 20 H7 L11 12 Z" fill="#DBE7FF" />
    <path d="M8 17 H16 L13 12.5 L16 7 H8 L11 11.5 Z" fill="#DBE7FF" />
    <!-- primary: outline + top bar + bottom bar + sand top dot -->
    <path d="M7 4 H17 L13 12 L17 20 H7 L11 12 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <line x1="6" y1="4" x2="18" y2="4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <line x1="6" y1="20" x2="18" y2="20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <circle cx="12" cy="12" r="1.2" fill="currentColor" />
  </svg>
</template>
