﻿<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getPracticeSession, type PracticeScene, type PracticeSession } from '@/api/practice'

const route = useRoute()

// ── 状态 ──
const session = ref<PracticeSession | null>(null)
const currentIndex = ref(0)
const loading = ref(true)
const errorMsg = ref('')
const iframeRef = ref<HTMLIFrameElement | null>(null)

// ── 计算属性 ──
const currentScene = computed<PracticeScene | null>(() =>
  session.value?.scenes?.[currentIndex.value] ?? null,
)
const totalScenes = computed(() => session.value?.scenes?.length ?? 0)
const hasNext = computed(() => currentIndex.value < totalScenes.value - 1)
const hasPrev = computed(() => currentIndex.value > 0)

const blobUrl = ref('')

// ── 加载实践会话 ──
onMounted(async () => {
  const sessionId = route.query.session
  if (!sessionId) {
    errorMsg.value = '缺少实践会话 ID'
    loading.value = false
    return
  }
  const id = Number(sessionId)
  if (Number.isNaN(id) || id <= 0) {
    errorMsg.value = '无效的实践会话 ID'
    loading.value = false
    return
  }
  try {
    const { data } = await getPracticeSession(id)
    session.value = data
    if (data.status === 'error') {
      errorMsg.value = data.error_message || '生成失败'
    }
  } catch (err: any) {
    errorMsg.value = err?.message || '加载实践会话失败'
  } finally {
    loading.value = false
  }
})

// ── 场景切换 ──
function goToScene(index: number): void {
  if (index >= 0 && index < totalScenes.value) {
    currentIndex.value = index
  }
}

function nextScene(): void { if (hasNext.value) currentIndex.value++ }
function prevScene(): void { if (hasPrev.value) currentIndex.value-- }

// ── iframe 渲染 ──
watch(currentScene, async (scene) => {
  if (!scene?.html) { blobUrl.value = ''; return }
  // 释放旧 blob URL
  if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
  const blob = new Blob([scene.html], { type: 'text/html' })
  blobUrl.value = URL.createObjectURL(blob)
  await nextTick()
})

// ── 语言标签颜色 ──
function langColor(lang: string): string {
  const map: Record<string, string> = {
    python: '#3776AB', javascript: '#F7DF1E', java: '#ED8B00', cpp: '#00599C',
  }
  return map[lang?.toLowerCase()] || '#10B981'
}
</script>

<template>
  <div class="xp-root">
    <!-- 加载态 -->
    <div v-if="loading" class="xp-load">
      <span class="xp-load-spin"></span>
      <span>加载实践内容…</span>
    </div>

    <!-- 错误态 -->
    <div v-else-if="errorMsg" class="xp-err">
      <span class="xp-err-ico">⚠️</span>
      <p>{{ errorMsg }}</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!session || totalScenes === 0" class="xp-err">
      <span class="xp-err-ico">📭</span>
      <p>实践内容为空</p>
    </div>

    <!-- 正常态 -->
    <template v-else>
      <!-- 左侧：场景列表 -->
      <aside class="xp-side">
        <div class="xp-side-hd">
          <h2 class="xp-side-ttl">{{ session.search_query }}</h2>
          <span class="xp-side-lang" :style="{ color: langColor(session.language) }">
            {{ session.language }}
          </span>
        </div>
        <div class="xp-scene-list">
          <button
            v-for="(scene, i) in session.scenes" :key="i"
            class="xp-scene-item"
            :class="{ 'is-active': i === currentIndex }"
            @click="goToScene(i)"
          >
            <span class="xp-scene-idx">{{ i + 1 }}</span>
            <span class="xp-scene-name">{{ scene.title }}</span>
          </button>
        </div>
      </aside>

      <!-- 右侧：场景内容 -->
      <section class="xp-main">
        <!-- 顶栏 -->
        <div class="xp-bar">
          <div class="xp-bar-nav">
            <button class="xp-nav-btn" :disabled="!hasPrev" @click="prevScene">◀ 上一个</button>
            <span class="xp-nav-idx">{{ currentIndex + 1 }} / {{ totalScenes }}</span>
            <button class="xp-nav-btn" :disabled="!hasNext" @click="nextScene">下一个 ▶</button>
          </div>
          <span class="xp-bar-ttl">{{ currentScene?.title }}</span>
        </div>

        <!-- iframe 渲染区 -->
        <div class="xp-frame-box">
          <iframe
            v-if="blobUrl"
            ref="iframeRef"
            :src="blobUrl"
            class="xp-frame"
            sandbox="allow-scripts allow-same-origin"
            title="实践场景"
          />
          <div v-else class="xp-frame-empty">请选择一个场景</div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.xp-root {
  position: fixed; inset: 68px 0 0 0;
  display: flex;
  background: #F2F2F7;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', var(--x-font-ui), sans-serif;
}

/* 加载态 */
.xp-load {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 12px;
  font-size: 15px; color: #8E8E93;
}
.xp-load-spin {
  width: 18px; height: 18px; border: 2px solid #E5E5EA; border-top-color: #1E5AE0;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 错误态 */
.xp-err {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; color: #8E8E93; font-size: 15px;
}
.xp-err-ico { font-size: 40px; }

/* 左侧栏 */
.xp-side {
  width: 240px; flex-shrink: 0;
  background: rgba(255,255,255,0.68); backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border-right: 0.5px solid rgba(0,0,0,0.08);
  display: flex; flex-direction: column; padding: 20px 16px;
}
.xp-side-hd { margin-bottom: 16px; }
.xp-side-ttl {
  font-size: 16px; font-weight: 700; color: #1C1C1E; margin: 0 0 6px;
  letter-spacing: -0.01em;
}
.xp-side-lang {
  font-size: 12px; font-weight: 600; text-transform: uppercase;
  background: rgba(0,0,0,0.04); padding: 2px 8px; border-radius: 4px;
}
.xp-scene-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.xp-scene-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 10px; border: none; background: none;
  cursor: pointer; text-align: left; transition: background 0.15s;
  font-family: inherit; width: 100%;
}
.xp-scene-item:hover { background: rgba(0,0,0,0.04); }
.xp-scene-item.is-active { background: rgba(30,90,224,0.08); }
.xp-scene-idx {
  width: 22px; height: 22px; border-radius: 50%;
  background: #E5E5EA; color: #8E8E93; font-size: 12px; font-weight: 600;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.xp-scene-item.is-active .xp-scene-idx { background: #1E5AE0; color: #fff; }
.xp-scene-name { font-size: 14px; color: #1C1C1E; line-height: 1.3; }
.xp-scene-item.is-active .xp-scene-name { color: #1E5AE0; font-weight: 500; }

/* 右侧主区 */
.xp-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.xp-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 24px; background: rgba(255,255,255,0.8);
  border-bottom: 0.5px solid rgba(0,0,0,0.06);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
.xp-bar-nav { display: flex; align-items: center; gap: 12px; }
.xp-nav-btn {
  padding: 6px 14px; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px;
  background: #fff; color: #1C1C1E; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.xp-nav-btn:hover:not(:disabled) { border-color: #1E5AE0; color: #1E5AE0; }
.xp-nav-btn:disabled { opacity: 0.35; cursor: default; }
.xp-nav-idx { font-size: 13px; color: #8E8E93; font-weight: 500; }
.xp-bar-ttl { font-size: 15px; font-weight: 600; color: #1C1C1E; }

/* iframe 渲染区 */
.xp-frame-box { flex: 1; position: relative; overflow: hidden; }
.xp-frame { width: 100%; height: 100%; border: none; background: #fff; }
.xp-frame-empty {
  position: absolute; inset: 0; display: flex; align-items: center;
  justify-content: center; color: #C7C7CC; font-size: 15px;
}
</style>
