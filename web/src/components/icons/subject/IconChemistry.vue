<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: flask body fill -->
    <path d="M9 4 H15 V10 L19 17 A2 2 0 0 1 17 21 H7 A2 2 0 0 1 5 17 L9 10 Z" fill="#DBE7FF" />
    <!-- primary: flask outline + neck + bubbles -->
    <path d="M9 4 H15 M9 4 V10 L5 17 A2 2 0 0 0 7 21 H17 A2 2 0 0 0 19 17 L15 10 V4"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
    <line x1="7.5" y1="15" x2="16.5" y2="15" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <circle cx="10" cy="18" r="0.8" fill="currentColor" />
    <circle cx="13" cy="19" r="0.6" fill="currentColor" />
    <circle cx="15" cy="17" r="0.6" fill="currentColor" />
  </svg>
</template>
