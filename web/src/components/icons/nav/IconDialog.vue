<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: speech bubble fill -->
    <path d="M5 5 H19 A2 2 0 0 1 21 7 V15 A2 2 0 0 1 19 17 H11 L7 21 V17 H5 A2 2 0 0 1 3 15 V7 A2 2 0 0 1 5 5 Z"
      fill="#DBE7FF" />
    <!-- primary: bubble outline + 3 dots -->
    <path d="M5 4.5 H19 A2.5 2.5 0 0 1 21.5 7 V15 A2.5 2.5 0 0 1 19 17.5 H10.5 L6.5 21.5 V17.5 H5 A2.5 2.5 0 0 1 2.5 15 V7 A2.5 2.5 0 0 1 5 4.5 Z"
      fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
    <circle cx="8" cy="11" r="1.1" fill="currentColor" />
    <circle cx="12" cy="11" r="1.1" fill="currentColor" />
    <circle cx="16" cy="11" r="1.1" fill="currentColor" />
  </svg>
</template>
