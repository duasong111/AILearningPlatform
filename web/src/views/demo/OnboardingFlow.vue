<script setup lang="ts">
/**
 * OnboardingFlow — 单卡内的问答流程
 *
 *   由 AppleCard 的默认 slot 渲染 (即弹窗内部). 维护自己的 step 状态 + 答案,
 *   答完最后一题 emit 'done' 让父级把卡片标记成 ✓.
 *
 *   支持 4 种题型: single (单选) / multi (多选) / text (文本) / slider (滑块).
 */

import { computed, reactive, ref } from 'vue'

export interface QuestionDef {
  kind: 'single' | 'multi' | 'text' | 'slider'
  q: string
  hint?: string
  options?: string[]
  min?: number
  max?: number
  step?: number
  placeholder?: string
}

export interface CardDef {
  id: string
  src: string
  title: string
  category: string
  questions: QuestionDef[]
}

const props = defineProps<{
  card: CardDef
  isDone: boolean
}>()

const emit = defineEmits<{
  (e: 'done'): void
}>()

const stepIdx = ref(0)
const total = computed(() => props.card.questions.length)
const isLast = computed(() => stepIdx.value === total.value - 1)
const cur = computed<QuestionDef>(() => props.card.questions[stepIdx.value]!)

const answers = reactive<Record<number, unknown>>({})

function next(): void {
  if (isLast.value) {
    emit('done')
    return
  }
  stepIdx.value++
}

function prev(): void {
  if (stepIdx.value > 0) stepIdx.value--
}

function pickSingle(idx: number, opt: string): void {
  answers[idx] = opt
}

function toggleMulti(idx: number, opt: string): void {
  const cur = (answers[idx] as string[] | undefined) ?? []
  const set = new Set(cur)
  if (set.has(opt)) set.delete(opt)
  else set.add(opt)
  answers[idx] = [...set]
}

function setText(idx: number, e: Event): void {
  answers[idx] = (e.target as HTMLTextAreaElement).value
}

function setSlider(idx: number, e: Event): void {
  answers[idx] = Number((e.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="of-wrap">
    <!-- step 指示 -->
    <div class="of-steps">
      <span class="of-step is-on">第 {{ stepIdx + 1 }} / {{ total }} 题</span>
      <span class="of-card-title">{{ card.title }}</span>
      <span v-if="isDone" class="of-done-badge">✓ 已完成</span>
    </div>

    <!-- 当前题目 -->
    <h3 class="of-q">{{ cur.q }}</h3>
    <p v-if="cur.hint" class="of-hint">{{ cur.hint }}</p>

    <!-- 选项渲染 -->
    <div v-if="cur.kind === 'single' && cur.options" class="of-options of-options--single">
      <button
        v-for="opt in cur.options"
        :key="opt"
        type="button"
        class="of-opt"
        :class="{ 'is-on': answers[stepIdx] === opt }"
        @click="pickSingle(stepIdx, opt)"
      >{{ opt }}</button>
    </div>

    <div v-else-if="cur.kind === 'multi' && cur.options" class="of-options of-options--multi">
      <button
        v-for="opt in cur.options"
        :key="opt"
        type="button"
        class="of-opt"
        :class="{ 'is-on': ((answers[stepIdx] as string[] | undefined) ?? []).includes(opt) }"
        @click="toggleMulti(stepIdx, opt)"
      >{{ opt }}</button>
    </div>

    <textarea
      v-else-if="cur.kind === 'text'"
      class="of-textarea"
      :placeholder="cur.placeholder ?? ''"
      :value="(answers[stepIdx] as string) ?? ''"
      @input="setText(stepIdx, $event)"
    />

    <div v-else-if="cur.kind === 'slider'" class="of-slider">
      <input
        type="range"
        :min="cur.min"
        :max="cur.max"
        :step="cur.step"
        :value="(answers[stepIdx] as number) ?? cur.min"
        @input="setSlider(stepIdx, $event)"
      />
      <div class="of-slider-val">{{ (answers[stepIdx] as number) ?? cur.min }} 分钟/天</div>
    </div>

    <!-- 导航 -->
    <div class="of-foot">
      <button
        type="button"
        class="of-btn of-btn--ghost"
        :disabled="stepIdx === 0"
        @click="prev"
      >← 上一题</button>
      <button
        type="button"
        class="of-btn of-btn--primary"
        @click="next"
      >{{ isLast ? '完成本卡' : '下一题' }} →</button>
    </div>
  </div>
</template>

<style scoped>
.of-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: var(--x-ink);
}

.of-steps {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--x-font-mono);
  font-size: 11px;
  color: var(--x-body-mid);
  letter-spacing: 0.04em;
}
.of-step.is-on { color: var(--x-primary); font-weight: 600; }
.of-card-title {
  margin-left: auto;
  font-family: var(--x-font-display);
  font-size: 12px;
  color: var(--x-ink);
  font-weight: 500;
}
.of-done-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  background: var(--x-success);
  color: #fff;
  border-radius: 999px;
}

.of-q {
  font-family: var(--x-font-display);
  font-size: 22px;
  font-weight: 600;
  margin: 4px 0 0;
  letter-spacing: -0.01em;
  line-height: 1.3;
}
.of-hint {
  margin: 0;
  font-size: 12.5px;
  color: var(--x-body-mid);
}

.of-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.of-opt {
  padding: 8px 14px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  background: var(--x-canvas-soft);
  color: var(--x-body);
  border: 1.5px solid var(--x-hairline);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.12s, background 0.12s, color 0.12s;
}
.of-opt:hover { border-color: var(--x-primary); color: var(--x-primary); }
.of-opt.is-on {
  background: var(--x-primary);
  border-color: var(--x-primary);
  color: #fff;
  font-weight: 600;
}

.of-textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px 14px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.55;
  color: var(--x-ink);
  background: var(--x-canvas-soft);
  border: 1.5px solid var(--x-hairline);
  border-radius: 10px;
  outline: none;
  resize: vertical;
  transition: border-color 0.15s;
}
.of-textarea:focus { border-color: var(--x-primary); }

.of-slider { display: flex; align-items: center; gap: 16px; }
.of-slider input[type='range'] {
  flex: 1;
  accent-color: var(--x-primary);
}
.of-slider-val {
  font-family: var(--x-font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--x-primary);
  min-width: 100px;
  text-align: right;
}

.of-foot {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}
.of-btn {
  padding: 8px 16px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid var(--x-hairline);
  border-radius: 999px;
  background: var(--x-canvas);
  color: var(--x-body);
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s, color 0.12s, filter 0.12s;
}
.of-btn--ghost:disabled { opacity: 0.4; cursor: not-allowed; }
.of-btn--ghost:hover:not(:disabled) {
  border-color: var(--x-primary);
  color: var(--x-primary);
}
.of-btn--primary {
  background: var(--x-primary);
  color: #fff;
  border-color: var(--x-primary);
}
.of-btn--primary:hover { filter: brightness(1.08); }
</style>