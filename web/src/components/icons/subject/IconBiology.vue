<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: leaf backdrop -->
    <path d="M5 19 C5 12 10 6 19 5 C19 14 14 19 5 19 Z" fill="#DBE7FF" />
    <!-- primary: leaf outline + central vein -->
    <path d="M5 19 C5 12 10 6 19 5 C19 14 14 19 5 19 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M5 19 L13 11" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <path d="M9 19 L13 15" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <path d="M11 17 L15 13" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
  </svg>
</template>
