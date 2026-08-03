<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMySubjectsStore } from '@/stores/mySubjects'
import type { MySubject } from '@/types/response'
import { IconSparkle, IconArrow, IconPlus } from '@/components/icons'

/**
 * 我的课程
 *
 *   - 真后端: POST/DELETE /api/subjects/  (backend/users/views.py:167-235)
 *   - 列表来源: useMySubjectsStore (本地源 + localStorage 持久化, 详见 store)
 *   - 加课对话框: Element Plus ElDialog —— 唯一不手写的弹层, 因为 dialog 涉及
 *     focus trap / esc-to-close 这些细节, 手写得不偿失
 */

const router = useRouter()
const store = useMySubjectsStore()

// 进入页面尝试一次后端 hydration; stub 返 [] 不会冲掉本地列表
onMounted(() => {
  store.loadFromBackend()
})

// === Add Course ===
function goToAddCourse(): void {
  router.push('/course-select')
}

// === Remove ===
async function handleRemove(s: MySubject): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `从「我的课程」中移除「${s.display_name}」?\n关联的知识点掌握度将一并删除, 无法恢复.`,
      'Remove course',
      {
        confirmButtonText: 'Remove',
        cancelButtonText: 'Cancel',
        type: 'warning',
        customClass: 'x-toast',
      },
    )
  } catch {
    return                                  // 用户点了取消
  }
  try {
    await store.remove(s.id)
    ElMessage({ message: `→ Removed`, customClass: 'x-toast' })
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Remove failed'
    ElMessage({ message: `× ${msg}`, customClass: 'x-toast' })
  }
}

function handleEnter(s: MySubject): void {
  router.push({ name: 'app-course-detail', params: { subjectCode: s.name } })
}

const hasCourses = computed(() => store.subjects.length > 0)
</script>

<template>
  <div class="x-courses">
    <header class="x-courses-head">
      <div class="x-head-left">
        <p class="x-eyebrow x-eyebrow-mute">LEARNING ⏤ MY COURSES</p>
        <h1 class="x-title">我的课程</h1>
        <p class="x-subtitle" v-if="hasCourses">
          {{ store.count }} 门进行中
        </p>
      </div>
      <button
        v-if="hasCourses"
        class="x-btn x-btn-primary"
        @click="goToAddCourse"
      >
        <span style="display:inline-flex;align-items:center;gap:6px"><IconPlus :size="13" /> Add course</span>
      </button>
    </header>

    <!-- EMPTY -->
    <div v-if="!hasCourses" class="x-empty">
      <div class="x-empty-mark"><IconSparkle :size="48" /></div>
      <p class="x-empty-title">你还没有添加任何课程</p>
      <p class="x-empty-sub">从课程目录里选一门开始, 或直接添加。</p>
      <div class="x-empty-actions">
        <button class="x-btn x-btn-primary" @click="goToAddCourse">
          <span style="display:inline-flex;align-items:center;gap:6px">添加课程 <IconArrow :size="13" /></span>
        </button>
      </div>
    </div>

    <!-- LIST -->
    <div v-else class="x-course-grid">
      <article
        v-for="s in store.subjects"
        :key="s.id"
        class="x-course-card"
      >
        <header class="x-course-card-head">
          <p class="x-eyebrow x-eyebrow-mute">{{ s.name.toUpperCase() }}</p>
          <h3 class="x-course-card-title">{{ s.display_name }}</h3>
        </header>
        <p class="x-course-card-meta">
          Added <span class="x-mono">{{ s.created_at.slice(0, 10) }}</span>
        </p>
        <footer class="x-course-card-foot">
          <button
            class="x-btn x-btn-outline-sm x-btn-danger"
            @click="handleRemove(s)"
          >Remove</button>
          <button
            class="x-btn x-btn-primary x-btn-sm"
            @click="handleEnter(s)"
          ><span style="display:inline-flex;align-items:center;gap:4px">Enter <IconArrow :size="12" /></span></button>
        </footer>
      </article>
    </div>
  </div>
</template>

<style scoped>
.x-courses {
  padding: 32px 40px 48px;
  max-width: var(--x-container);
  margin: 0 auto;
}

/* === HEAD === */
.x-courses-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}
.x-head-left { min-width: 0; }
.x-title {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--x-ink);
  margin: 8px 0 4px;
}
.x-subtitle {
  font-size: 14px;
  color: var(--x-body);
  margin: 0;
}

/* === EMPTY === */
.x-empty {
  text-align: center;
  padding: 80px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  border: 1px dashed var(--x-hairline-strong);
  border-radius: var(--x-rounded-md);
  background:
    radial-gradient(ellipse 40% 60% at 50% 50%, var(--x-blue-alpha-06), transparent 70%);
}
.x-empty-mark {
  color: var(--x-primary);
  animation: x-spin 14s linear infinite;
  margin-bottom: 8px;
  display: inline-flex;
}
.x-empty-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  color: var(--x-ink);
  margin: 0;
}
.x-empty-sub {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
}
.x-empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

/* === GRID === */
.x-course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.x-course-card {
  background: var(--x-canvas);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.12s, transform 0.12s;
  position: relative;
  overflow: hidden;
}
.x-course-card:hover {
  border-color: var(--x-hairline-strong);
  transform: translateY(-1px);
}
.x-course-card-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.x-course-card-title {
  font-family: var(--x-font-display);
  font-size: 18px;
  font-weight: 500;
  color: var(--x-ink);
  margin: 0;
}
.x-course-card-meta {
  font-size: 13px;
  color: var(--x-body-mid);
  margin: 0;
  flex: 1;
}
.x-mono {
  font-family: var(--x-font-mono);
  font-size: 12px;
}
.x-course-card-foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid var(--x-hairline);
  padding-top: 12px;
}

/* === Add dialog picker === */
.x-pick-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
}
.x-pick-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--x-hairline);
}
.x-pick-row:last-child {
  border-bottom: 0;
}
.x-pick-row.is-owned .x-pick-name {
  color: var(--x-body-mid);
}
.x-pick-meta { min-width: 0; }
.x-pick-name {
  font-family: var(--x-font-display);
  font-size: 14px;
  color: var(--x-ink);
  margin: 0 0 2px;
}

/* === buttons === */
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--x-font-display);
  font-size: 13px;
  font-weight: 500;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.12s, color 0.12s, border-color 0.12s, transform 0.1s;
  white-space: nowrap;
}
.x-btn:active:not(:disabled) {
  transform: scale(0.98);
}
.x-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: 1px solid var(--x-primary);
  padding: 9px 18px;
}
.x-btn-primary:hover:not(:disabled) {
  background: var(--x-primary-hover);
  border-color: var(--x-primary-hover);
}
.x-btn-sm { padding: 6px 14px; font-size: 12px; }
.x-btn-outline-sm {
  background: transparent;
  color: var(--x-ink);
  border: 1px solid var(--x-ink-alpha-15);
  padding: 6px 14px;
  font-size: 12px;
}
.x-btn-outline-sm:hover:not(:disabled) {
  background: var(--x-canvas-soft);
  border-color: var(--x-ink-alpha-30);
}
.x-btn-danger:hover:not(:disabled) {
  color: var(--x-error);
  border-color: var(--x-error);
  background: var(--x-error-soft);
}

/* === eyebrow === */
.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.x-eyebrow-mute {
  color: var(--x-body-mid);
}

@keyframes x-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .x-empty-mark,
  .x-course-card {
    animation: none;
    transition: none;
  }
}

@media (max-width: 768px) {
  .x-courses {
    padding: 24px 16px 40px;
  }
  .x-courses-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
