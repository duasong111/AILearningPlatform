<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: top doc fill -->
    <rect x="7" y="3" width="13" height="16" rx="2" fill="#DBE7FF" />
    <!-- primary: stacked docs outline + lines -->
    <rect x="4" y="6" width="13" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" />
    <rect x="7" y="3" width="13" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" />
    <line x1="10" y1="9" x2="17" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="10" y1="12" x2="17" y2="12" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="10" y1="15" x2="15" y2="15" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
  </svg>
</template>
