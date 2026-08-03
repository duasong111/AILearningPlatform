<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 14" :height="size ?? 14" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M7 10 L12 15 L17 10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
