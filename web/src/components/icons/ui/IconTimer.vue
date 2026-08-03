<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: clock face -->
    <circle cx="12" cy="13" r="8" fill="#DBE7FF" />
    <!-- primary: top button + outline + hands -->
    <rect x="9" y="2" width="6" height="2.5" rx="1" fill="currentColor" />
    <circle cx="12" cy="13" r="8" fill="none" stroke="currentColor" stroke-width="1.6" />
    <path d="M12 8.5 V13 L15 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
