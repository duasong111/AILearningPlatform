<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: pen tip body fill -->
    <path d="M4 20 L4 16 L14 6 L18 10 L8 20 Z" fill="#DBE7FF" />
    <!-- primary: pen body outline + nib tip + clip detail -->
    <path d="M14 6 L18 10 L8 20 L4 20 L4 16 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    <path d="M15 5 L19 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    <path d="M4 20 L7 17" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
  </svg>
</template>
