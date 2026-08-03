<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: head + shoulders silhouette backdrop -->
    <circle cx="12" cy="9" r="3.5" fill="#DBE7FF" />
    <path d="M5 20 A7 7 0 0 1 19 20 Z" fill="#DBE7FF" />
    <!-- primary: outline -->
    <circle cx="12" cy="9" r="3.5" fill="none" stroke="currentColor" stroke-width="1.6" />
    <path d="M5.5 19.5 A6.5 6.5 0 0 1 18.5 19.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
  </svg>
</template>
