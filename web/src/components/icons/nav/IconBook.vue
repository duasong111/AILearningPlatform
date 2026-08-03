<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: right page fill -->
    <path d="M12 6.5 V19 H20 A1 1 0 0 0 21 18 V5 H13 A1 1 0 0 0 12 6.5 Z" fill="#DBE7FF" />
    <!-- primary: outline + spine + page lines -->
    <path d="M12 6.5 A1 1 0 0 0 11 5.5 H3 V18 A1 1 0 0 0 4 19 H12 V6.5 Z" fill="none"
      stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M12 6.5 A1 1 0 0 1 13 5.5 H21 V18 A1 1 0 0 1 20 19 H12 V6.5 Z" fill="none"
      stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <line x1="5.5" y1="9" x2="9.5" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="5.5" y1="12" x2="9.5" y2="12" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="14.5" y1="9" x2="18.5" y2="9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
    <line x1="14.5" y1="12" x2="18.5" y2="12" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
  </svg>
</template>
