<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: video screen fill -->
    <rect x="3" y="5.5" width="18" height="13" rx="2" fill="#DBE7FF" />
    <!-- primary: screen outline -->
    <rect x="3.75" y="6.25" width="16.5" height="11.5" rx="1.6" fill="none"
      stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <!-- primary: play triangle in the middle -->
    <path d="M10.5 9.5 L10.5 14.5 L14.8 12 Z" fill="currentColor" stroke="currentColor"
      stroke-width="1.4" stroke-linejoin="round" />
    <!-- primary: video base bar (player bottom) -->
    <line x1="6" y1="20.5" x2="18" y2="20.5" stroke="currentColor" stroke-width="1.6"
      stroke-linecap="round" />
  </svg>
</template>