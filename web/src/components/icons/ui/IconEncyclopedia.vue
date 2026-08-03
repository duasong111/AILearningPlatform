<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: right page -->
    <path d="M12 5.5 V20 H20 A1.5 1.5 0 0 0 21.5 18.5 V5.5 Z" fill="#DBE7FF" />
    <!-- primary: 2 books stacked + bookmark -->
    <path d="M2.5 6.5 A1.5 1.5 0 0 1 4 5 H11 V19 H4 A1.5 1.5 0 0 1 2.5 17.5 Z"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M12 5.5 A1.5 1.5 0 0 1 13.5 4 H20.5 A1.5 1.5 0 0 1 22 5.5 V17.5 A1.5 1.5 0 0 1 20.5 19 H13.5 A1.5 1.5 0 0 1 12 17.5 Z"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <line x1="14.5" y1="8" x2="19.5" y2="8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <line x1="14.5" y1="11" x2="19.5" y2="11" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <line x1="14.5" y1="14" x2="19.5" y2="14" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <path d="M16.5 4 V7.5 L18 6.5 L19.5 7.5 V4" fill="currentColor" />
  </svg>
</template>
