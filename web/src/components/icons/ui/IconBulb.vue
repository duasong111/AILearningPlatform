<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: bulb glass backdrop -->
    <path d="M12 3 A7 7 0 0 1 17 14 V16 A1 1 0 0 1 16 17 H8 A1 1 0 0 1 7 16 V14 A7 7 0 0 1 12 3 Z"
      fill="#DBE7FF" />
    <!-- primary: outline + filament + base -->
    <path d="M12 3 A7 7 0 0 1 17 14 V16 A1 1 0 0 1 16 17 H8 A1 1 0 0 1 7 16 V14 A7 7 0 0 1 12 3 Z"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <line x1="9" y1="19" x2="15" y2="19" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <line x1="10" y1="21" x2="14" y2="21" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <path d="M10 10 L12 12 L14 10" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
