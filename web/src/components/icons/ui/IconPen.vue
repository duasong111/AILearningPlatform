<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: pen tip body -->
    <path d="M3 21 L3 17 L13 7 L17 11 L7 21 Z" fill="#DBE7FF" />
    <!-- primary: outline + nib + cap clip -->
    <path d="M13 7 L17 11 L7 21 L3 21 L3 17 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <line x1="14" y1="6" x2="18" y2="10" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
    <line x1="3" y1="21" x2="6" y2="18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
    <path d="M11 9 L15 13" stroke="currentColor" stroke-width="1" />
  </svg>
</template>
