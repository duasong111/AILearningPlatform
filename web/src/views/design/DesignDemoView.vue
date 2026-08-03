<script setup lang="ts">
/**
 * Design System Demo — DESIGN-x.ai.md token showcase
 * Route: /app/design-demo
 *
 * Sections:
 *   1. Color palette
 *   2. Typography
 *   3. Spacing & radius
 *   4. Shadows
 *   5. Buttons
 *   6. Form inputs
 *   7. Cards
 *   8. Badges / pills
 *   9. Choice option cards (quiz style)
 *  10. Progress / strength bars
 *  11. Status indicators
 *  12. Navigation items
 */
import { ref } from 'vue'
import {
  IconSparkle,
  IconRetry,
  IconArrow,
  IconGeometry,
  IconElectricity,
  IconCell,
  IconCheck,
  IconCross,
  IconHourglass,
  IconInfo,
  IconWarn,
  IconNotepad,
  IconHome,
  IconGalaxy,
  IconDialog,
  IconPlan,
  IconBook,
  IconExercise,
  IconExam,
} from '@/components/icons'

const textInput = ref('')
const selectVal = ref('medium')
const checkedRadio = ref('B')
const checkedMulti = ref<string[]>(['vue'])
const progressPct = ref(68)
</script>

<template>
  <div class="demo-page">
    <header class="demo-header">
      <h1>Design System Demo</h1>
      <p class="demo-subtitle">DESIGN-x.ai.md token showcase &mdash; <code>--x-*</code> CSS variables</p>
    </header>

    <!-- ════════════════════════════════════════════════
         §1  Color Palette
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§1 &nbsp;Color Palette</h2>

      <h3>Surface</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-canvas)">
          <span class="swatch-label">canvas</span>
          <span class="swatch-hex">#FFFFFF</span>
        </div>
        <div class="swatch" style="background: var(--x-canvas-soft)">
          <span class="swatch-label">canvas-soft</span>
          <span class="swatch-hex">#F8FAFC</span>
        </div>
        <div class="swatch" style="background: var(--x-canvas-card)">
          <span class="swatch-label">canvas-card</span>
          <span class="swatch-hex">#FFFFFF</span>
        </div>
        <div class="swatch" style="background: var(--x-canvas-mid)">
          <span class="swatch-label">canvas-mid</span>
          <span class="swatch-hex">#F1F5F9</span>
        </div>
        <div class="swatch" style="background: var(--x-canvas-tint)">
          <span class="swatch-label">canvas-tint</span>
          <span class="swatch-hex">#EFF6FF</span>
        </div>
        <div class="swatch swatch--bordered" style="background: var(--x-hairline)">
          <span class="swatch-label">hairline</span>
          <span class="swatch-hex">#E5E7EB</span>
        </div>
        <div class="swatch swatch--bordered" style="background: var(--x-hairline-strong)">
          <span class="swatch-label">hairline-strong</span>
          <span class="swatch-hex">#CBD5E1</span>
        </div>
      </div>

      <h3>Text / Ink</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-ink)">
          <span class="swatch-label swatch-label--light">ink</span>
          <span class="swatch-hex swatch-hex--light">#0F172A</span>
        </div>
        <div class="swatch" style="background: var(--x-ink-hover)">
          <span class="swatch-label swatch-label--light">ink-hover</span>
          <span class="swatch-hex swatch-hex--light">#1E293B</span>
        </div>
        <div class="swatch" style="background: var(--x-body)">
          <span class="swatch-label swatch-label--light">body</span>
          <span class="swatch-hex swatch-hex--light">#475569</span>
        </div>
        <div class="swatch" style="background: var(--x-body-mid)">
          <span class="swatch-label swatch-label--light">body-mid</span>
          <span class="swatch-hex swatch-hex--light">#64748B</span>
        </div>
        <div class="swatch" style="background: var(--x-mute)">
          <span class="swatch-label">mute</span>
          <span class="swatch-hex">#94A3B8</span>
        </div>
      </div>

      <h3>Brand / Primary</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-primary)">
          <span class="swatch-label swatch-label--light">primary</span>
          <span class="swatch-hex swatch-hex--light">#1E5AE0</span>
        </div>
        <div class="swatch" style="background: var(--x-primary-hover)">
          <span class="swatch-label swatch-label--light">primary-hover</span>
          <span class="swatch-hex swatch-hex--light">#1A4DC4</span>
        </div>
        <div class="swatch" style="background: var(--x-primary-soft)">
          <span class="swatch-label">primary-soft</span>
          <span class="swatch-hex">#DBE7FF</span>
        </div>
        <div class="swatch" style="background: var(--x-on-primary)">
          <span class="swatch-label">on-primary</span>
          <span class="swatch-hex">#FFFFFF</span>
        </div>
      </div>

      <h3>Accents</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-accent-blue)">
          <span class="swatch-label swatch-label--light">blue</span>
          <span class="swatch-hex swatch-hex--light">#1E5AE0</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-blue-soft)">
          <span class="swatch-label">blue-soft</span>
          <span class="swatch-hex">#93C5FD</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-blue-deep)">
          <span class="swatch-label swatch-label--light">blue-deep</span>
          <span class="swatch-hex swatch-hex--light">#1E40AF</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-amber)">
          <span class="swatch-label">amber</span>
          <span class="swatch-hex">#F59E0B</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-amber-soft)">
          <span class="swatch-label">amber-soft</span>
          <span class="swatch-hex">#FCD34D</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-amber-deep)">
          <span class="swatch-label swatch-label--light">amber-deep</span>
          <span class="swatch-hex swatch-hex--light">#B45309</span>
        </div>
        <div class="swatch" style="background: var(--x-accent-violet)">
          <span class="swatch-label swatch-label--light">violet</span>
          <span class="swatch-hex swatch-hex--light">#7C3AED</span>
        </div>
      </div>

      <h3>Semantic / Status</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-success)">
          <span class="swatch-label swatch-label--light">success</span>
          <span class="swatch-hex swatch-hex--light">#10B981</span>
        </div>
        <div class="swatch" style="background: var(--x-success-soft)">
          <span class="swatch-label">success-soft</span>
          <span class="swatch-hex">#D1FAE5</span>
        </div>
        <div class="swatch" style="background: var(--x-warning)">
          <span class="swatch-label">warning</span>
          <span class="swatch-hex">#F59E0B</span>
        </div>
        <div class="swatch" style="background: var(--x-warning-soft)">
          <span class="swatch-label">warning-soft</span>
          <span class="swatch-hex">#FEF3C7</span>
        </div>
        <div class="swatch" style="background: var(--x-danger)">
          <span class="swatch-label swatch-label--light">danger</span>
          <span class="swatch-hex swatch-hex--light">#DC2626</span>
        </div>
        <div class="swatch" style="background: var(--x-danger-soft)">
          <span class="swatch-label">danger-soft</span>
          <span class="swatch-hex">#FEE2E2</span>
        </div>
      </div>

      <h3>AI Accent</h3>
      <div class="swatch-row">
        <div class="swatch" style="background: var(--x-ai)">
          <span class="swatch-label swatch-label--light">ai</span>
          <span class="swatch-hex swatch-hex--light">#7C3AED</span>
        </div>
        <div class="swatch" style="background: var(--x-ai-soft)">
          <span class="swatch-label">ai-soft</span>
          <span class="swatch-hex">#EDE9FE</span>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §2  Typography
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§2 &nbsp;Typography</h2>

      <div class="type-row">
        <span class="type-label">Display 32/40</span>
        <span class="type-display">学径 AI 学习助手</span>
      </div>
      <div class="type-row">
        <span class="type-label">H1 24/32</span>
        <span class="type-h1">知识星图</span>
      </div>
      <div class="type-row">
        <span class="type-label">H2 20/28</span>
        <span class="type-h2">学习计划</span>
      </div>
      <div class="type-row">
        <span class="type-label">H3 16/24 bold</span>
        <span class="type-h3">刷题练习</span>
      </div>
      <div class="type-row">
        <span class="type-label">Body 16/24</span>
        <span class="type-body">这是一段正文内容，The quick brown fox jumps over the lazy dog.</span>
      </div>
      <div class="type-row">
        <span class="type-label">Caption 14/20</span>
        <span class="type-caption">辅助说明文字 · Caption text</span>
      </div>
      <div class="type-row">
        <span class="type-label">Small 12/16</span>
        <span class="type-small">最小可读字号 · 12px</span>
      </div>
      <div class="type-row">
        <span class="type-label">Mono 14/22</span>
        <span class="type-mono">const x = await fetch('/api/quiz/')</span>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §3  Spacing & Radius
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§3 &nbsp;Spacing Scale</h2>
      <div class="spacing-row">
        <div class="spacing-item" v-for="tok in [
          { name: 'xxs', val: '2px' },
          { name: 'xs', val: '4px' },
          { name: 'sm', val: '8px' },
          { name: 'md', val: '12px' },
          { name: 'lg', val: '16px' },
          { name: 'xl', val: '24px' },
          { name: '2xl', val: '32px' },
          { name: '3xl', val: '48px' },
          { name: '4xl', val: '64px' },
        ]" :key="tok.name">
          <div class="spacing-bar" :style="{ width: `var(--x-${tok.name})` }"></div>
          <span class="spacing-label">{{ tok.name }} <em>{{ tok.val }}</em></span>
        </div>
      </div>

      <h2 style="margin-top: var(--x-2xl)">§3b &nbsp;Radius Scale</h2>
      <div class="radius-row">
        <div class="radius-item" v-for="tok in [
          { name: 'sm', val: '6px' },
          { name: 'md', val: '10px' },
          { name: 'lg', val: '14px' },
          { name: 'xl', val: '20px' },
          { name: 'pill', val: '9999px' },
        ]" :key="tok.name">
          <div class="radius-box" :style="{ borderRadius: `var(--x-rounded-${tok.name})` }"></div>
          <span class="radius-label">{{ tok.name }} <em>{{ tok.val }}</em></span>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §4  Shadows
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§4 &nbsp;Shadows</h2>
      <p class="demo-note">DESIGN-x.ai.md: shadows only on floating UI (toast / modal / popover), never on content cards.</p>
      <div class="shadow-row">
        <div class="shadow-card shadow-card--toast">
          <strong>toast</strong>
          <span>4px 12px</span>
        </div>
        <div class="shadow-card shadow-card--popover">
          <strong>popover</strong>
          <span>8px 24px</span>
        </div>
        <div class="shadow-card shadow-card--modal">
          <strong>modal</strong>
          <span>12px 32px</span>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §5  Buttons
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§5 &nbsp;Buttons</h2>

      <h3>Variants</h3>
      <div class="btn-row">
        <button class="btn btn-primary">Primary 主要</button>
        <button class="btn btn-primary" disabled>Primary Disabled</button>
        <button class="btn btn-secondary">Secondary 次要</button>
        <button class="btn btn-secondary" disabled>Secondary Disabled</button>
        <button class="btn btn-ghost">Ghost 幽灵</button>
        <button class="btn btn-ghost" disabled>Ghost Disabled</button>
        <button class="btn btn-danger">Danger 危险</button>
      </div>

      <h3>Sizes</h3>
      <div class="btn-row">
        <button class="btn btn-primary btn-sm">Small 小</button>
        <button class="btn btn-primary">Default 默认</button>
        <button class="btn btn-primary btn-lg">Large 大</button>
      </div>

      <h3>Icon + Text</h3>
      <div class="btn-row">
        <button class="btn btn-primary">
          <span class="btn-icon"><IconSparkle :size="16" /></span> 生成题目
        </button>
        <button class="btn btn-secondary">
          <span class="btn-icon"><IconRetry :size="16" /></span> 重新生成
        </button>
        <button class="btn btn-ghost">
          <span class="btn-icon"><IconArrow :size="16" /></span> 查看详情
        </button>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §6  Form Inputs
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§6 &nbsp;Form Inputs</h2>

      <div class="form-grid">
        <div class="form-field">
          <label class="form-label">Text Input 文本框</label>
          <input v-model="textInput" class="form-input" placeholder="请输入内容..." />
        </div>

        <div class="form-field">
          <label class="form-label">Text Input (disabled)</label>
          <input class="form-input" value="不可编辑" disabled />
        </div>

        <div class="form-field">
          <label class="form-label">Select 下拉选择</label>
          <select v-model="selectVal" class="form-input form-select">
            <option value="easy">简单 Easy</option>
            <option value="medium">中等 Medium</option>
            <option value="hard">困难 Hard</option>
          </select>
        </div>

        <div class="form-field">
          <label class="form-label">Textarea 多行文本</label>
          <textarea class="form-input form-textarea" rows="3" placeholder="额外要求..."></textarea>
        </div>

        <div class="form-field">
          <label class="form-label">Number Count 数量</label>
          <div class="count-picker">
            <button class="count-btn" :class="{ active: false }">3</button>
            <button class="count-btn" :class="{ active: true }">5</button>
            <button class="count-btn" :class="{ active: false }">8</button>
          </div>
        </div>

        <div class="form-field">
          <label class="form-label">Checkbox 多选</label>
          <div class="check-group">
            <label class="check-label" v-for="opt in ['vue', 'react', 'svelte']" :key="opt">
              <input type="checkbox" :value="opt" v-model="checkedMulti" />
              <span>{{ opt }}</span>
            </label>
          </div>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §7  Cards
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§7 &nbsp;Cards</h2>

      <h3>Content Card (hairline border, no shadow)</h3>
      <div class="card-grid">
        <div class="card card-content">
          <div class="card-header">
            <span class="pill pill-blue">数学</span>
            <span class="card-meta">5 题 · 3 分钟前</span>
          </div>
          <p class="card-body">这是一张内容卡片的正文区域。卡片使用 hairline 边框而非阴影来区分层级。</p>
          <div class="card-footer">
            <button class="btn btn-ghost btn-sm"><span style="display:inline-flex;align-items:center;gap:6px">查看详情 <IconArrow :size="12" /></span></button>
          </div>
        </div>

        <div class="card card-content">
          <div class="card-header">
            <span class="pill pill-amber">物理</span>
            <span class="card-meta">8 题 · 1 小时前</span>
          </div>
          <p class="card-body">DESIGN-x.ai.md 规范：内容卡片使用 1px hairline 边框，圆角 lg (14px)，无阴影。hover 时边框升级为 hairline-strong。</p>
          <div class="card-footer">
            <span class="badge badge-success">已完成</span>
          </div>
        </div>
      </div>

      <h3>Hover Card (elevated on hover)</h3>
      <div class="card-grid">
        <div class="card card-hover">
          <div class="card-icon"><IconGeometry :size="28" /></div>
          <h4>几何基础</h4>
          <p>三角形、四边形、圆的基本性质</p>
        </div>
        <div class="card card-hover">
          <div class="card-icon"><IconElectricity :size="28" /></div>
          <h4>电学入门</h4>
          <p>欧姆定律、基尔霍夫定律</p>
        </div>
        <div class="card card-hover">
          <div class="card-icon"><IconCell :size="28" /></div>
          <h4>细胞生物学</h4>
          <p>细胞结构与功能</p>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §8  Badges / Pills
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§8 &nbsp;Badges &amp; Pills</h2>

      <h3>Subject Pills</h3>
      <div class="badge-row">
        <span class="pill pill-blue">数学</span>
        <span class="pill pill-amber">物理</span>
        <span class="pill pill-violet">化学</span>
        <span class="pill pill-green">生物</span>
      </div>

      <h3>Status Badges</h3>
      <div class="badge-row">
        <span class="badge badge-success">
          <span style="display:inline-flex"><IconCheck :size="12" /></span> 已完成
        </span>
        <span class="badge badge-warning">
          <span style="display:inline-flex"><IconHourglass :size="12" /></span> 生成中
        </span>
        <span class="badge badge-danger">
          <span style="display:inline-flex"><IconCross :size="12" /></span> 失败
        </span>
        <span class="badge badge-info">
          <span style="display:inline-flex"><IconInfo :size="12" /></span> 进行中
        </span>
        <span class="badge badge-muted">已过期</span>
      </div>

      <h3>Difficulty Tags</h3>
      <div class="badge-row">
        <span class="tag tag-easy">简单</span>
        <span class="tag tag-medium">中等</span>
        <span class="tag tag-hard">困难</span>
      </div>

      <h3>Correct / Wrong Indicators</h3>
      <div class="badge-row">
        <span class="verdict verdict-correct">
          <span style="display:inline-flex"><IconCheck :size="14" /></span> 正确
        </span>
        <span class="verdict verdict-wrong">
          <span style="display:inline-flex"><IconCross :size="14" /></span> 错误
        </span>
        <span class="verdict verdict-ungraded">— 未判分</span>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §9  Choice Option Cards (Quiz Style)
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§9 &nbsp;Choice Option Cards</h2>
      <p class="demo-note">刷题页面的选项卡片样式，含正确/错误/选中态</p>

      <div class="option-list">
        <div class="option-card option-card--selected">
          <span class="option-letter">A</span>
          <span class="option-text">勾股定理只适用于直角三角形</span>
        </div>
        <div class="option-card option-card--correct">
          <span class="option-letter">B</span>
          <span class="option-text">勾股定理表述为：直角三角形两直角边的平方和等于斜边的平方</span>
          <span class="option-badge">✓ 正确答案</span>
        </div>
        <div class="option-card option-card--wrong">
          <span class="option-letter">C</span>
          <span class="option-text">勾股定理可以用于任意三角形</span>
          <span class="option-badge">✗ 你的选择</span>
        </div>
        <div class="option-card">
          <span class="option-letter">D</span>
          <span class="option-text">勾股定理的逆定理同样成立</span>
        </div>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §10  Progress / Strength Bars
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§10 &nbsp;Progress &amp; Strength Bars</h2>

      <h3>Progress Bar</h3>
      <div class="progress-demo">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
        <span class="progress-label">{{ progressPct }}%</span>
      </div>

      <h3>Strength Bar (password style)</h3>
      <div class="strength-row">
        <div class="strength-segments">
          <div class="strength-seg" style="background: var(--x-strength-1)"></div>
          <div class="strength-seg strength-seg--empty"></div>
          <div class="strength-seg strength-seg--empty"></div>
          <div class="strength-seg strength-seg--empty"></div>
        </div>
        <span class="strength-text" style="color: var(--x-strength-1)">弱</span>
      </div>
      <div class="strength-row">
        <div class="strength-segments">
          <div class="strength-seg" style="background: var(--x-strength-2)"></div>
          <div class="strength-seg" style="background: var(--x-strength-2)"></div>
          <div class="strength-seg strength-seg--empty"></div>
          <div class="strength-seg strength-seg--empty"></div>
        </div>
        <span class="strength-text" style="color: var(--x-strength-2)">一般</span>
      </div>
      <div class="strength-row">
        <div class="strength-segments">
          <div class="strength-seg" style="background: var(--x-strength-3)"></div>
          <div class="strength-seg" style="background: var(--x-strength-3)"></div>
          <div class="strength-seg" style="background: var(--x-strength-3)"></div>
          <div class="strength-seg strength-seg--empty"></div>
        </div>
        <span class="strength-text" style="color: var(--x-strength-3)">较强</span>
      </div>
      <div class="strength-row">
        <div class="strength-segments">
          <div class="strength-seg" style="background: var(--x-strength-4)"></div>
          <div class="strength-seg" style="background: var(--x-strength-4)"></div>
          <div class="strength-seg" style="background: var(--x-strength-4)"></div>
          <div class="strength-seg" style="background: var(--x-strength-4)"></div>
        </div>
        <span class="strength-text" style="color: var(--x-strength-4)">强</span>
      </div>

      <h3>Quiz Progress Dots</h3>
      <div class="dot-row">
        <span class="dot dot--done dot--correct"></span>
        <span class="dot dot--done dot--wrong"></span>
        <span class="dot dot--current"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §11  Status / Feedback
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§11 &nbsp;Status &amp; Feedback</h2>

      <h3>Alert Banners</h3>
      <div class="alert alert-success">
        <span class="alert-icon"><IconCheck :size="16" /></span>
        <span>答案正确！勾股定理是直角三角形最重要的性质之一。</span>
      </div>
      <div class="alert alert-danger">
        <span class="alert-icon"><IconCross :size="16" /></span>
        <span>答案错误。勾股定理只适用于直角三角形，不能推广到任意三角形。</span>
      </div>
      <div class="alert alert-warning">
        <span class="alert-icon"><IconWarn :size="16" /></span>
        <span>生成超时，请检查网络连接后重试。</span>
      </div>
      <div class="alert alert-info">
        <span class="alert-icon"><IconInfo :size="16" /></span>
        <span>AI 正在分析你的答案，请稍候...</span>
      </div>

      <h3>Toast (floating, with shadow)</h3>
      <div class="toast-demo">
        <div class="toast">已复制到剪贴板</div>
        <div class="toast toast--error">操作失败，请重试</div>
      </div>

      <h3>Empty State</h3>
      <div class="empty-state">
        <div class="empty-icon"><IconNotepad :size="48" /></div>
        <p class="empty-title">暂无刷题记录</p>
        <p class="empty-desc">选择一门课程开始练习吧</p>
        <button class="btn btn-primary btn-sm">开始刷题</button>
      </div>
    </section>

    <!-- ════════════════════════════════════════════════
         §12  Navigation Items
         ════════════════════════════════════════════════ -->
    <section class="demo-section">
      <h2>§12 &nbsp;Navigation</h2>

      <div class="nav-demo">
        <div class="nav-item nav-item--active">
          <span class="nav-icon"><IconHome :size="18" /></span>
          <span>主页</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconGalaxy :size="18" /></span>
          <span>星图</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconDialog :size="18" /></span>
          <span>对话</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconPlan :size="18" /></span>
          <span>计划</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconBook :size="18" /></span>
          <span>书架</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconExercise :size="18" /></span>
          <span>刷题</span>
        </div>
        <div class="nav-item">
          <span class="nav-icon"><IconExam :size="18" /></span>
          <span>评测</span>
        </div>
      </div>
    </section>

    <footer class="demo-footer">
      <p>Design System Demo &mdash; tokens defined in <code>src/assets/base.css</code> &mdash; spec in <code>DESIGN-x.ai.md</code></p>
    </footer>
  </div>
</template>

<style scoped>
/* ── Page layout ─────────────────────────────────────── */
.demo-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--x-2xl) var(--x-xl) var(--x-4xl);
}
.demo-header {
  margin-bottom: var(--x-3xl);
}
.demo-header h1 {
  font-size: 32px;
  line-height: 40px;
  font-weight: 700;
  color: var(--x-ink);
}
.demo-subtitle {
  margin-top: var(--x-sm);
  font-size: 16px;
  color: var(--x-body);
}
.demo-subtitle code {
  font-family: var(--x-font-mono);
  font-size: 14px;
  background: var(--x-canvas-mid);
  padding: 2px 6px;
  border-radius: var(--x-rounded-sm);
}
.demo-section {
  margin-bottom: var(--x-3xl);
  padding-bottom: var(--x-3xl);
  border-bottom: 1px solid var(--x-hairline);
}
.demo-section:last-of-type {
  border-bottom: none;
}
.demo-section h2 {
  font-size: 20px;
  line-height: 28px;
  font-weight: 600;
  color: var(--x-ink);
  margin-bottom: var(--x-lg);
}
.demo-section h3 {
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  color: var(--x-body);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: var(--x-xl);
  margin-bottom: var(--x-md);
}
.demo-note {
  font-size: 14px;
  color: var(--x-body-mid);
  margin-bottom: var(--x-lg);
}

/* ── §1 Swatches ─────────────────────────────────────── */
.swatch-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--x-sm);
  margin-bottom: var(--x-md);
}
.swatch {
  width: 100px;
  height: 72px;
  border-radius: var(--x-rounded-md);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: var(--x-sm);
  border: 1px solid var(--x-ink-alpha-06);
}
.swatch--bordered {
  border-color: var(--x-hairline-strong);
}
.swatch-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--x-ink);
}
.swatch-label--light {
  color: rgba(255, 255, 255, 0.85);
}
.swatch-hex {
  font-size: 10px;
  font-family: var(--x-font-mono);
  color: var(--x-body);
}
.swatch-hex--light {
  color: rgba(255, 255, 255, 0.65);
}

/* ── §2 Typography ───────────────────────────────────── */
.type-row {
  display: flex;
  align-items: baseline;
  gap: var(--x-lg);
  padding: var(--x-sm) 0;
  border-bottom: 1px solid var(--x-ink-alpha-06);
}
.type-label {
  flex-shrink: 0;
  width: 130px;
  font-size: 12px;
  font-family: var(--x-font-mono);
  color: var(--x-mute);
}
.type-display { font-size: 32px; line-height: 40px; font-weight: 700; }
.type-h1 { font-size: 24px; line-height: 32px; font-weight: 600; }
.type-h2 { font-size: 20px; line-height: 28px; font-weight: 600; }
.type-h3 { font-size: 16px; line-height: 24px; font-weight: 600; }
.type-body { font-size: 16px; line-height: 24px; color: var(--x-body); }
.type-caption { font-size: 14px; line-height: 20px; color: var(--x-body-mid); }
.type-small { font-size: 12px; line-height: 16px; color: var(--x-body-mid); }
.type-mono {
  font-size: 14px;
  line-height: 22px;
  font-family: var(--x-font-mono);
  color: var(--x-ink);
  background: var(--x-canvas-mid);
  padding: 2px 8px;
  border-radius: var(--x-rounded-sm);
}

/* ── §3 Spacing & Radius ─────────────────────────────── */
.spacing-row {
  display: flex;
  flex-direction: column;
  gap: var(--x-sm);
}
.spacing-item {
  display: flex;
  align-items: center;
  gap: var(--x-md);
}
.spacing-bar {
  height: 16px;
  background: var(--x-primary-soft);
  border: 1px solid var(--x-accent-blue-soft);
  border-radius: 2px;
  min-width: 2px;
}
.spacing-label {
  font-size: 13px;
  font-family: var(--x-font-mono);
  color: var(--x-body);
  white-space: nowrap;
}
.spacing-label em {
  font-style: normal;
  color: var(--x-mute);
}

.radius-row {
  display: flex;
  gap: var(--x-xl);
  flex-wrap: wrap;
}
.radius-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--x-sm);
}
.radius-box {
  width: 64px;
  height: 64px;
  background: var(--x-primary-soft);
  border: 2px solid var(--x-primary);
}
.radius-label {
  font-size: 13px;
  font-family: var(--x-font-mono);
  color: var(--x-body);
}
.radius-label em {
  font-style: normal;
  color: var(--x-mute);
}

/* ── §4 Shadows ──────────────────────────────────────── */
.shadow-row {
  display: flex;
  gap: var(--x-2xl);
  flex-wrap: wrap;
}
.shadow-card {
  width: 180px;
  padding: var(--x-xl);
  background: var(--x-canvas-card);
  border-radius: var(--x-rounded-lg);
  display: flex;
  flex-direction: column;
  gap: var(--x-xs);
}
.shadow-card strong {
  font-weight: 600;
  font-size: 14px;
}
.shadow-card span {
  font-size: 12px;
  font-family: var(--x-font-mono);
  color: var(--x-body-mid);
}
.shadow-card--toast { box-shadow: var(--x-shadow-toast); }
.shadow-card--popover { box-shadow: var(--x-shadow-popover); }
.shadow-card--modal { box-shadow: var(--x-shadow-modal); }

/* ── §5 Buttons ──────────────────────────────────────── */
.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--x-md);
  margin-bottom: var(--x-lg);
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--x-sm);
  padding: 0 var(--x-lg);
  height: 40px;
  border: none;
  border-radius: var(--x-rounded-md);
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-sm { height: 32px; padding: 0 var(--x-md); font-size: 13px; }
.btn-lg { height: 48px; padding: 0 var(--x-xl); font-size: 16px; }
.btn-icon {
  font-size: 16px;
  line-height: 1;
}

.btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.btn-primary:hover:not(:disabled) {
  background: var(--x-primary-hover);
}

.btn-secondary {
  background: var(--x-canvas);
  color: var(--x-ink);
  border: 1px solid var(--x-hairline);
}
.btn-secondary:hover:not(:disabled) {
  border-color: var(--x-hairline-strong);
  background: var(--x-canvas-soft);
}

.btn-ghost {
  background: transparent;
  color: var(--x-primary);
}
.btn-ghost:hover:not(:disabled) {
  background: var(--x-canvas-tint);
}

.btn-danger {
  background: var(--x-danger);
  color: #fff;
}
.btn-danger:hover:not(:disabled) {
  background: #B91C1C;
}

/* ── §6 Form Inputs ──────────────────────────────────── */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--x-lg);
}
@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
}
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--x-xs);
}
.form-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--x-body);
}
.form-input {
  height: 40px;
  padding: 0 var(--x-md);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  font-family: var(--x-font-display);
  font-size: 14px;
  color: var(--x-ink);
  background: var(--x-canvas);
  transition: border-color 0.15s ease;
  outline: none;
}
.form-input:focus {
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
}
.form-input:disabled {
  background: var(--x-canvas-mid);
  color: var(--x-mute);
  cursor: not-allowed;
}
.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%2394A3B8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}
.form-textarea {
  height: auto;
  padding: var(--x-md);
  resize: vertical;
  line-height: 22px;
}

.count-picker {
  display: flex;
  gap: 0;
}
.count-btn {
  flex: 1;
  height: 40px;
  border: 1px solid var(--x-hairline);
  background: var(--x-canvas);
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 500;
  color: var(--x-body);
  cursor: pointer;
  transition: all 0.15s ease;
}
.count-btn:first-child { border-radius: var(--x-rounded-md) 0 0 var(--x-rounded-md); }
.count-btn:last-child { border-radius: 0 var(--x-rounded-md) var(--x-rounded-md) 0; }
.count-btn + .count-btn { border-left: none; }
.count-btn.active {
  background: var(--x-primary);
  border-color: var(--x-primary);
  color: var(--x-on-primary);
}
.count-btn:hover:not(.active) {
  background: var(--x-canvas-soft);
}

.check-group {
  display: flex;
  gap: var(--x-lg);
  height: 40px;
  align-items: center;
}
.check-label {
  display: flex;
  align-items: center;
  gap: var(--x-xs);
  font-size: 14px;
  color: var(--x-ink);
  cursor: pointer;
}
.check-label input[type="checkbox"] {
  accent-color: var(--x-primary);
  width: 16px;
  height: 16px;
}

/* ── §7 Cards ────────────────────────────────────────── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--x-lg);
  margin-bottom: var(--x-lg);
}
.card {
  border-radius: var(--x-rounded-lg);
  padding: var(--x-lg);
}
.card-content {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  transition: border-color 0.15s ease;
}
.card-content:hover {
  border-color: var(--x-hairline-strong);
}
.card-hover {
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  cursor: pointer;
  transition: all 0.2s ease;
}
.card-hover:hover {
  border-color: var(--x-primary);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--x-md);
}
.card-meta {
  font-size: 12px;
  color: var(--x-mute);
}
.card-body {
  font-size: 14px;
  line-height: 22px;
  color: var(--x-body);
  margin-bottom: var(--x-md);
}
.card-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}
.card-icon {
  color: var(--x-primary);
  margin-bottom: var(--x-sm);
  display: inline-flex;
}
.card-hover h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
  margin-bottom: var(--x-xs);
}
.card-hover p {
  font-size: 13px;
  color: var(--x-body-mid);
  line-height: 20px;
}

/* ── §8 Badges / Pills ───────────────────────────────── */
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--x-sm);
  margin-bottom: var(--x-md);
}
.pill {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 var(--x-md);
  border-radius: var(--x-rounded-pill);
  font-size: 12px;
  font-weight: 500;
}
.pill-blue { background: var(--x-primary-soft); color: var(--x-primary); }
.pill-amber { background: var(--x-warning-soft); color: var(--x-accent-amber-deep); }
.pill-violet { background: var(--x-ai-soft); color: var(--x-accent-violet); }
.pill-green { background: var(--x-success-soft); color: var(--x-success); }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 var(--x-sm);
  border-radius: var(--x-rounded-sm);
  font-size: 12px;
  font-weight: 500;
}
.badge-success { background: var(--x-success-soft); color: var(--x-success); }
.badge-warning { background: var(--x-warning-soft); color: var(--x-accent-amber-deep); }
.badge-danger { background: var(--x-danger-soft); color: var(--x-danger); }
.badge-info { background: var(--x-canvas-tint); color: var(--x-primary); }
.badge-muted { background: var(--x-canvas-mid); color: var(--x-mute); }

.tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 var(--x-sm);
  border-radius: var(--x-rounded-sm);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}
.tag-easy { background: var(--x-success-soft); color: var(--x-success); }
.tag-medium { background: var(--x-warning-soft); color: var(--x-accent-amber-deep); }
.tag-hard { background: var(--x-danger-soft); color: var(--x-danger); }

.verdict {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 var(--x-md);
  border-radius: var(--x-rounded-md);
  font-size: 13px;
  font-weight: 600;
}
.verdict-correct { background: var(--x-success-soft); color: var(--x-success); }
.verdict-wrong { background: var(--x-danger-soft); color: var(--x-danger); }
.verdict-ungraded { background: var(--x-canvas-mid); color: var(--x-mute); }

/* ── §9 Choice Option Cards ──────────────────────────── */
.option-list {
  display: flex;
  flex-direction: column;
  gap: var(--x-sm);
  max-width: 560px;
}
.option-card {
  display: flex;
  align-items: flex-start;
  gap: var(--x-md);
  padding: var(--x-md) var(--x-lg);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  background: var(--x-canvas-card);
  cursor: pointer;
  transition: all 0.15s ease;
}
.option-card:hover {
  border-color: var(--x-hairline-strong);
  background: var(--x-canvas-soft);
}
.option-card--selected {
  border-color: var(--x-primary);
  background: var(--x-canvas-tint);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
}
.option-card--correct {
  border-color: var(--x-success);
  background: var(--x-success-soft);
}
.option-card--wrong {
  border-color: var(--x-danger);
  background: var(--x-danger-soft);
}
.option-letter {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--x-rounded-sm);
  background: var(--x-canvas-mid);
  font-size: 13px;
  font-weight: 600;
  color: var(--x-body);
}
.option-card--selected .option-letter {
  background: var(--x-primary);
  color: var(--x-on-primary);
}
.option-card--correct .option-letter {
  background: var(--x-success);
  color: #fff;
}
.option-card--wrong .option-letter {
  background: var(--x-danger);
  color: #fff;
}
.option-text {
  font-size: 14px;
  line-height: 22px;
  color: var(--x-ink);
  padding-top: 3px;
  flex: 1;
}
.option-badge {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding-top: 4px;
}
.option-card--correct .option-badge { color: var(--x-success); }
.option-card--wrong .option-badge { color: var(--x-danger); }

/* ── §10 Progress / Strength ─────────────────────────── */
.progress-demo {
  display: flex;
  align-items: center;
  gap: var(--x-md);
  max-width: 400px;
  margin-bottom: var(--x-xl);
}
.progress-bar {
  flex: 1;
  height: 8px;
  background: var(--x-canvas-mid);
  border-radius: var(--x-rounded-pill);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--x-primary);
  border-radius: var(--x-rounded-pill);
  transition: width 0.3s ease;
}
.progress-label {
  font-size: 13px;
  font-family: var(--x-font-mono);
  color: var(--x-body);
  min-width: 36px;
  text-align: right;
}

.strength-row {
  display: flex;
  align-items: center;
  gap: var(--x-md);
  margin-bottom: var(--x-sm);
  max-width: 300px;
}
.strength-segments {
  display: flex;
  gap: 4px;
  flex: 1;
}
.strength-seg {
  flex: 1;
  height: 6px;
  border-radius: 3px;
}
.strength-seg--empty {
  background: var(--x-canvas-mid);
}
.strength-text {
  font-size: 13px;
  font-weight: 500;
  min-width: 32px;
}

.dot-row {
  display: flex;
  gap: var(--x-sm);
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--x-canvas-mid);
  border: 2px solid var(--x-hairline);
}
.dot--current {
  border-color: var(--x-primary);
  background: var(--x-canvas-tint);
  box-shadow: 0 0 0 3px var(--x-blue-alpha-06);
}
.dot--done {
  border-color: transparent;
}
.dot--correct { background: var(--x-success); }
.dot--wrong { background: var(--x-danger); }

/* ── §11 Alerts / Toast / Empty ──────────────────────── */
.alert {
  display: flex;
  align-items: flex-start;
  gap: var(--x-sm);
  padding: var(--x-md) var(--x-lg);
  border-radius: var(--x-rounded-md);
  font-size: 14px;
  line-height: 22px;
  margin-bottom: var(--x-sm);
}
.alert-icon {
  flex-shrink: 0;
  line-height: 22px;
  display: inline-flex;
  align-items: center;
}
.alert-success { background: var(--x-success-soft); color: var(--x-success); }
.alert-danger { background: var(--x-danger-soft); color: var(--x-danger); }
.alert-warning { background: var(--x-warning-soft); color: var(--x-accent-amber-deep); }
.alert-info { background: var(--x-canvas-tint); color: var(--x-primary); }

.toast-demo {
  display: flex;
  gap: var(--x-md);
  flex-wrap: wrap;
  margin-bottom: var(--x-xl);
}
.toast {
  display: inline-flex;
  align-items: center;
  height: 40px;
  padding: 0 var(--x-lg);
  background: var(--x-canvas-card);
  border: 1px solid var(--x-hairline);
  border-radius: var(--x-rounded-md);
  box-shadow: var(--x-shadow-toast);
  font-size: 14px;
  color: var(--x-ink);
}
.toast--error {
  border-color: var(--x-danger);
  color: var(--x-danger);
}

.empty-state {
  text-align: center;
  padding: var(--x-3xl) var(--x-xl);
  background: var(--x-canvas-soft);
  border-radius: var(--x-rounded-lg);
  border: 1px dashed var(--x-hairline);
}
.empty-icon {
  color: var(--x-primary);
  opacity: 0.5;
  margin-bottom: var(--x-md);
  display: inline-flex;
}
.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--x-ink);
  margin-bottom: var(--x-xs);
}
.empty-desc {
  font-size: 14px;
  color: var(--x-body-mid);
  margin-bottom: var(--x-lg);
}

/* ── §12 Navigation ──────────────────────────────────── */
.nav-demo {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-width: 220px;
  background: var(--x-canvas-soft);
  padding: var(--x-sm);
  border-radius: var(--x-rounded-lg);
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--x-md);
  padding: var(--x-sm) var(--x-md);
  border-radius: var(--x-rounded-md);
  font-size: 14px;
  color: var(--x-body);
  cursor: pointer;
  transition: all 0.15s ease;
}
.nav-item:hover {
  background: var(--x-canvas-mid);
  color: var(--x-ink);
}
.nav-item--active {
  background: var(--x-primary-soft);
  color: var(--x-primary);
  font-weight: 500;
}
.nav-icon {
  width: 24px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--x-body);
}

.nav-item--active .nav-icon {
  color: var(--x-primary);
}

/* ── Footer ──────────────────────────────────────────── */
.demo-footer {
  text-align: center;
  padding: var(--x-2xl) 0;
  font-size: 13px;
  color: var(--x-mute);
}
.demo-footer code {
  font-family: var(--x-font-mono);
  background: var(--x-canvas-mid);
  padding: 2px 6px;
  border-radius: var(--x-rounded-sm);
}
</style>
