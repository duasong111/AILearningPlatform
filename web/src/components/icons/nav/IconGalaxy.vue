<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: large central node halo -->
    <circle cx="12" cy="12" r="6" fill="#DBE7FF" />
    <!-- primary: 4-point star at center + 3 satellite nodes + connecting lines -->
    <path d="M12 7 L13.2 10.8 L17 12 L13.2 13.2 L12 17 L10.8 13.2 L7 12 L10.8 10.8 Z"
      fill="currentColor" />
    <circle cx="4.5" cy="5" r="1.4" fill="currentColor" />
    <circle cx="19" cy="6" r="1" fill="currentColor" />
    <circle cx="19" cy="18.5" r="1.4" fill="currentColor" />
    <path d="M6 6 L9.5 9.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <path d="M18 7 L14.5 10" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
    <path d="M18 18 L14 14" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" />
  </svg>
</template>
