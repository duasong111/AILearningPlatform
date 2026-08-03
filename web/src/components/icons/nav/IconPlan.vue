<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: calendar body + highlighted day cell -->
    <rect x="3.5" y="5.5" width="17" height="15" rx="2" fill="#DBE7FF" />
    <rect x="7" y="11" width="4" height="4" rx="1" fill="#FFFFFF" fill-opacity="0.6" />
    <!-- primary: header bar + grid + ringed highlight -->
    <rect x="3.5" y="5.5" width="17" height="4.5" fill="currentColor" />
    <rect x="3.5" y="5.5" width="17" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="1.5" />
    <line x1="3.5" y1="10" x2="20.5" y2="10" stroke="currentColor" stroke-width="1.5" />
    <line x1="8" y1="3" x2="8" y2="7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <line x1="16" y1="3" x2="16" y2="7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <rect x="6.5" y="13" width="5" height="5" rx="0.8" fill="none" stroke="currentColor" stroke-width="1.5" />
  </svg>
</template>
