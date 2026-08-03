<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: house body fill -->
    <path d="M5 11 L12 4 L19 11 V19 A1 1 0 0 1 18 20 H6 A1 1 0 0 1 5 19 Z" fill="#DBE7FF" />
    <!-- primary: roof line + door -->
    <path d="M3.5 11 L12 3 L20.5 11" fill="none" stroke="currentColor" stroke-width="1.6"
      stroke-linecap="round" stroke-linejoin="round" />
    <path d="M10 20 V14 A1 1 0 0 1 11 13 H13 A1 1 0 0 1 14 14 V20" fill="none"
      stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>
