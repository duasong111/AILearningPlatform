<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 2.5 L13.6 4.7 L16.3 3.9 L17.1 6.6 L19.8 7.4 L18.9 10.1 L21.1 11.7 L19 13.7 L20 16.3 L17.3 17.1 L16.5 19.7 L13.8 18.9 L12 21 L10.2 18.9 L7.5 19.7 L6.7 17.1 L4 16.3 L5 13.7 L2.9 11.7 L5.1 10.1 L4.2 7.4 L6.9 6.6 L7.7 3.9 L10.4 4.7 Z"
      fill="#DBE7FF" />
    <circle cx="12" cy="12" r="3.4" fill="currentColor" />
    <circle cx="12" cy="12" r="1.4" fill="#DBE7FF" />
  </svg>
</template>
