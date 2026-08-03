<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: two overlapping bubbles -->
    <path d="M3 8 A2 2 0 0 1 5 6 H14 A2 2 0 0 1 16 8 V13 A2 2 0 0 1 14 15 H9 L6 18 V15 H5 A2 2 0 0 1 3 13 Z"
      fill="#DBE7FF" />
    <path d="M9 11 H19 A2 2 0 0 1 21 13 V17 A2 2 0 0 1 19 19 H17 V21.5 L14.5 19 H10 A2 2 0 0 1 9 17 Z" fill="currentColor" />
  </svg>
</template>
