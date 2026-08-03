<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <circle cx="12" cy="12" r="10" fill="#DBE7FF" />
    <path d="M8.5 8.5 L15.5 15.5 M15.5 8.5 L8.5 15.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
  </svg>
</template>
