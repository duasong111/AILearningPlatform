<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: large sparkle backdrop -->
    <path d="M12 4 L13.6 10.4 L20 12 L13.6 13.6 L12 20 L10.4 13.6 L4 12 L10.4 10.4 Z" fill="#DBE7FF" />
    <!-- primary: large 4-point star + small accent star -->
    <path d="M12 4 L13.6 10.4 L20 12 L13.6 13.6 L12 20 L10.4 13.6 L4 12 L10.4 10.4 Z" fill="currentColor" />
    <path d="M19 5 L19.6 7 L21.5 7.6 L19.6 8.2 L19 10.2 L18.4 8.2 L16.5 7.6 L18.4 7 Z" fill="currentColor" />
  </svg>
</template>
