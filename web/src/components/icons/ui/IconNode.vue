<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: soft rotated square backdrop -->
    <rect x="4" y="4" width="16" height="16" rx="2" transform="rotate(45 12 12)" fill="#DBE7FF" />
    <!-- primary: outline + center dot -->
    <rect x="4" y="4" width="16" height="16" rx="2" transform="rotate(45 12 12)" fill="none" stroke="currentColor" stroke-width="1.6" />
    <circle cx="12" cy="12" r="2.5" fill="currentColor" />
  </svg>
</template>
