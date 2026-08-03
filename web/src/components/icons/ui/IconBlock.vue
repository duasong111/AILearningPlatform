<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: 4-quadrant block backdrop -->
    <rect x="3" y="3" width="18" height="18" rx="2" fill="#DBE7FF" />
    <rect x="11" y="3" width="2" height="18" fill="#FFFFFF" fill-opacity="0.6" />
    <rect x="3" y="11" width="18" height="2" fill="#FFFFFF" fill-opacity="0.6" />
    <!-- primary: outline + cross dividers + 1 highlighted quadrant -->
    <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" />
    <line x1="12" y1="3" x2="12" y2="21" stroke="currentColor" stroke-width="1.4" />
    <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="1.4" />
    <rect x="12" y="12" width="9" height="9" fill="currentColor" />
  </svg>
</template>
