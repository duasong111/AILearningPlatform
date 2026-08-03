<script setup lang="ts">
/**
 * WelcomeModal —— 首次登录欢迎弹窗
 *
 * 触发场景: 用户登录后, 满足"已登录 + 0 门课 + 没跳过 onboarding"条件时,
 * AppShell 自动设为 visible=true, 弹窗浮现, 让用户在"立刻选课"和
 * "先逛逛"之间二选一.
 *
 * 设计: 用 Element Plus 的 ElDialog (自带 ESC 关闭 / 点遮罩关闭 / 锁滚动),
 * 不自己撸 overlay 逻辑, 省事且无障碍行为跟项目其它 dialog 一致.
 */
import { ElDialog } from 'element-plus'
import { useRouter } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const onboarding = useOnboardingStore()

function pickCourse(): void {
  onboarding.closeWelcome()
  router.push('/course-select')
}

function browseFirst(): void {
  // 同时写 skip 标志 → 后续登录不会再自动弹 (除非用户主动重新引导)
  onboarding.skipOnboarding()
  onboarding.closeWelcome()
}
</script>

<template>
  <ElDialog
    :model-value="onboarding.welcomeOpen"
    title="欢迎来到学径"
    width="440px"
    align-center
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    :show-close="true"
    @update:model-value="onboarding.closeWelcome()"
  >
    <!-- 内容 -->
    <div class="x-welcome-body">
      <div class="x-welcome-emoji" aria-hidden="true">👋</div>
      <p class="x-welcome-lead">
        上手只需 30 秒 — 选一门学科开始学习, 或者先四处看看也行。
      </p>

      <!-- 选项预览 -->
      <div class="x-welcome-options">
        <div class="x-welcome-opt">
          <div class="x-welcome-opt-mark">①</div>
          <div class="x-welcome-opt-text">
            <strong>去选课</strong>
            <span>从 7 门学科里挑一个感兴趣的, 进入学习</span>
          </div>
        </div>
        <div class="x-welcome-opt">
          <div class="x-welcome-opt-mark">②</div>
          <div class="x-welcome-opt-text">
            <strong>先逛逛</strong>
            <span>看看主界面长什么样, 之后再从「我的课程」加</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <template #footer>
      <div class="x-welcome-actions">
        <button class="x-btn x-btn-ghost" type="button" @click="browseFirst">
          先逛逛
        </button>
        <button class="x-btn x-btn-primary" type="button" @click="pickCourse">
          去选课 →
        </button>
      </div>
    </template>
  </ElDialog>
</template>

<style scoped>
.x-welcome-body {
  padding: 4px 0 8px;
}
.x-welcome-emoji {
  font-size: 38px;
  text-align: center;
  margin-bottom: 14px;
  line-height: 1;
}
.x-welcome-lead {
  font-size: 14.5px;
  line-height: 1.65;
  color: var(--x-body);
  text-align: center;
  margin: 0 0 22px;
}

.x-welcome-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.x-welcome-opt {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-md);
}
.x-welcome-opt-mark {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--x-primary);
  color: var(--x-on-primary);
  display: grid;
  place-items: center;
  font-family: var(--x-font-mono);
  font-size: 12px;
  font-weight: 700;
}
.x-welcome-opt-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.x-welcome-opt-text strong {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--x-ink);
}
.x-welcome-opt-text span {
  font-size: 12.5px;
  color: var(--x-body-mid);
  line-height: 1.5;
}

.x-welcome-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.x-btn {
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  border-radius: var(--x-rounded-md);
  padding: 9px 20px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.1s;
}
.x-btn:active { transform: scale(0.98); }
.x-btn-ghost {
  background: var(--x-canvas);
  color: var(--x-body);
  border-color: var(--x-hairline);
}
.x-btn-ghost:hover { background: var(--x-canvas-soft); }
.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border-color: var(--x-primary);
}
.x-btn-primary:hover { background: var(--x-primary-hover); border-color: var(--x-primary-hover); }
</style>