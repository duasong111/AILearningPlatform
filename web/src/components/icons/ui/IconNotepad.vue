<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 64" :height="size ?? 64" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: notepad page fill -->
    <rect x="4" y="4" width="16" height="18" rx="2" fill="#DBE7FF" />
    <!-- primary: header strip + 3 content lines + clip ring -->
    <rect x="8" y="2" width="8" height="3" rx="1" fill="currentColor" />
    <rect x="4" y="4" width="16" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" />
    <line x1="7" y1="11" x2="17" y2="11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="7" y1="14.5" x2="17" y2="14.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="7" y1="18" x2="13" y2="18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
  </svg>
</template>
