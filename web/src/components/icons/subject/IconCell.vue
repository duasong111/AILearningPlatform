<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: cell body fill -->
    <circle cx="12" cy="12" r="9" fill="#DBE7FF" />
    <!-- primary: cell outline + nucleus + 2 organelles -->
    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6" />
    <circle cx="12" cy="12" r="3.2" fill="currentColor" />
    <circle cx="6.5" cy="9" r="1.2" fill="none" stroke="currentColor" stroke-width="1.3" />
    <circle cx="17" cy="16" r="1.4" fill="none" stroke="currentColor" stroke-width="1.3" />
  </svg>
</template>
