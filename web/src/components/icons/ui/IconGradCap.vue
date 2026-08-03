<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 18" :height="size ?? 18" viewBox="0 0 24 24" aria-hidden="true">
    <!-- soft: mortarboard top diamond fill -->
    <path d="M12 4.5 L21 9 L12 13.5 L3 9 Z" fill="#DBE7FF" />
    <!-- primary: mortarboard outline -->
    <path d="M12 3.5 L21.5 8.2 L12 12.9 L2.5 8.2 Z" fill="none" stroke="currentColor"
      stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round" />
    <!-- primary: cap body (trapezoid) -->
    <path d="M6.5 10 V14 C6.5 15.5 9 16.5 12 16.5 C15 16.5 17.5 15.5 17.5 14 V10"
      fill="none" stroke="currentColor" stroke-width="1.6"
      stroke-linejoin="round" stroke-linecap="round" />
    <!-- primary: tassel string from top -->
    <path d="M21 9 V14.5" fill="none" stroke="currentColor" stroke-width="1.6"
      stroke-linecap="round" />
    <!-- primary: tassel ball -->
    <circle cx="21" cy="15.6" r="1.2" fill="currentColor" />
  </svg>
</template>