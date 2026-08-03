<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: bolt glow backdrop -->
    <path d="M13 3 L5 13 H10 L9 21 L19 10 H13 Z" fill="#DBE7FF" />
    <!-- primary: lightning bolt outline -->
    <path d="M13 3 L5 13 H10 L9 21 L19 10 H13 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M13 3 L5 13 L13 13" fill="currentColor" />
    <path d="M19 10 L11 21 L11 10" fill="currentColor" fill-opacity="0.85" />
  </svg>
</template>
