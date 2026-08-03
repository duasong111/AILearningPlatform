<script setup lang="ts">
import { BendingGallery } from '@/components/ui/bending-gallery'

const galleryItems = [
  { image: 'https://picsum.photos/seed/1/800/600', text: '数据结构' },
  { image: 'https://picsum.photos/seed/2/800/600', text: '机器学习' },
  { image: 'https://picsum.photos/seed/3/800/600', text: '操作系统' },
  { image: 'https://picsum.photos/seed/4/800/600', text: '高等数学' },
]
</script>

<template>
  <div class="x-demo">
    <header class="x-demo-head">
      <p class="x-demo-eyebrow">UI COMPONENT · DEMO</p>
      <h1 class="x-demo-title">Bending Gallery</h1>
      <p class="x-demo-sub">拖动鼠标滚轮滑动，卡片沿弧线排列，产生视觉纵深效果。</p>
    </header>
    <div class="x-demo-gallery">
      <BendingGallery :items="galleryItems" :bend="2" :card-scale="2" />
    </div>
  </div>
</template>

<style scoped>
.x-demo {
  min-height: calc(100vh - 56px);
  background: var(--x-canvas);
  display: flex;
  flex-direction: column;
}
.x-demo-head {
  padding: 32px 40px 16px;
}
.x-demo-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--x-primary);
  margin: 0 0 8px;
  text-transform: uppercase;
}
.x-demo-title {
  font-family: var(--x-font-display);
  font-size: clamp(26px, 4vw, 34px);
  font-weight: 700;
  color: var(--x-ink);
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.x-demo-sub {
  font-size: 14px;
  color: var(--x-body);
  margin: 0;
}
.x-demo-gallery {
  flex: 1;
  min-height: 0;
}
</style>
