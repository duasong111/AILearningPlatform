<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: 2x2 grid backdrop -->
    <rect x="3" y="3" width="8" height="8" rx="1.5" fill="#DBE7FF" />
    <!-- primary: 3x3 outline + highlighted cell -->
    <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" />
    <line x1="9" y1="3" x2="9" y2="21" stroke="currentColor" stroke-width="1.2" />
    <line x1="15" y1="3" x2="15" y2="21" stroke="currentColor" stroke-width="1.2" />
    <line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="1.2" />
    <line x1="3" y1="15" x2="21" y2="15" stroke="currentColor" stroke-width="1.2" />
    <rect x="15" y="15" width="6" height="6" rx="1" fill="currentColor" />
  </svg>
</template>
