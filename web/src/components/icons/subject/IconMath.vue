<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: π backdrop -->
    <path d="M5 9 H19 A2 2 0 0 1 21 11 V14 A2 2 0 0 1 19 16 H5 Z" fill="#DBE7FF" />
    <!-- primary: π strokes + x symbol -->
    <path d="M5 8 H19 M9 8 V17 M15 8 V17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <line x1="8" y1="19" x2="16" y2="19" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
  </svg>
</template>
