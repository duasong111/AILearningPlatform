<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: atom nucleus + ring fill -->
    <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="#DBE7FF" />
    <circle cx="12" cy="12" r="2" fill="#FFFFFF" fill-opacity="0.6" />
    <!-- primary: 3 orbital ellipses + nucleus + orbiting dot -->
    <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.4" />
    <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.4" transform="rotate(60 12 12)" />
    <ellipse cx="12" cy="12" rx="9" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.4" transform="rotate(-60 12 12)" />
    <circle cx="12" cy="12" r="2" fill="currentColor" />
    <circle cx="20" cy="12" r="1.2" fill="currentColor" />
  </svg>
</template>
