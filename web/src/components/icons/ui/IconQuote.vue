<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: tail + body backdrop -->
    <path d="M5 6 H10 V13 H7 L6 18 V13 H5 Z" fill="#DBE7FF" />
    <path d="M14 6 H19 V13 H16 L15 18 V13 H14 Z" fill="#DBE7FF" />
    <!-- primary: outline + 2 large quote marks -->
    <path d="M5 5 H10 V13 H7 L6 17 V13 H5 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M14 5 H19 V13 H16 L15 17 V13 H14 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M6.5 8 H8.5 M15.5 8 H17.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
  </svg>
</template>
