<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 12 H19 M13 6 L19 12 L13 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="19" cy="12" r="2.2" fill="#DBE7FF" />
    <path d="M19 12 L17 10 M19 12 L17 14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
