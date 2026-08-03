<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: pin head backdrop -->
    <path d="M12 2 A6 6 0 0 1 18 8 C18 12 12 21 12 21 C12 21 6 12 6 8 A6 6 0 0 1 12 2 Z"
      fill="#DBE7FF" />
    <!-- primary: outline + center hole + small inner dot -->
    <path d="M12 2 A6 6 0 0 1 18 8 C18 12 12 21 12 21 C12 21 6 12 6 8 A6 6 0 0 1 12 2 Z"
      fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <circle cx="12" cy="8" r="2" fill="currentColor" />
  </svg>
</template>
