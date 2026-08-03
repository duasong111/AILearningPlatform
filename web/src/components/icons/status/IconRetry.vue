<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: 3/4 ring backdrop -->
    <path d="M12 4 A8 8 0 1 0 19.5 16" fill="none" stroke="#DBE7FF" stroke-width="3.5" stroke-linecap="round" />
    <!-- primary: arrow head + ring -->
    <path d="M19 17 L19.5 11.5 L14 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M12 4 A8 8 0 1 0 19.5 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
  </svg>
</template>
