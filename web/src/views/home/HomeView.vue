<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useStarfield } from './use_starfield'
import { useTypewriter } from './use_typewriter'
import { useReveal } from './use_reveal'
import { useUserStore } from '@/stores/user'
import { useSettingsStore } from '@/stores/settings'
import UserWidget from '@/components/UserWidget.vue'
import { BrandMark, IconArrow } from '@/components/icons'

const router = useRouter()
const userStore = useUserStore()
const settings = useSettingsStore()

// 主题切换 —— 仅 light / dark 二态循环 (auto 留给设置页), 一颗按钮搞定
function toggleTheme(): void {
  const next: 'light' | 'dark' = settings.theme === 'dark' ? 'light' : 'dark'
  settings.setTheme(next)
}

// ============================================================
// 静态展示数据 —— 按区块组织,纯数据,无副作用
// ============================================================

// Hero 下方的 3 个 feature pill —— 对应平台核心卖点
const heroPills = [
  { dot: 'blue', text: '7 大专业智能体' },
  { dot: 'green', text: '8 大学科领域' },
  { dot: 'purple', text: '多模态资源自动生成' },
]

// 核心模块 —— 跟 /app/* 实际路由对应, 不再用泛化的概念词
const features = [
  {
    eyebrow: '01 / TUTOR',
    title: 'AI 对话',
    body: '智能学习助手, 理解你的提问, 多轮上下文辅导, 给出可延伸的解答。',
    // cta: '体验对话',
  },
  {
    eyebrow: '02 / PLANNER',
    title: '学习计划',
    body: 'AI 基于画像与目标生成的个性化学习路线图, 每天该学什么一目了然。',
    cta: '查看路线',
  },
  {
    eyebrow: '03 / GALAXY',
    title: '知识星图',
    body: '暗色画布上的知识图谱, 把每门课的脉络与节点关系可视化导航。',
    cta: '进入星图',
  },
  {
    eyebrow: '04 / PRACTICE',
    title: '刷题中心',
    body: '自适应出题、专项训练、错题归档 —— 把弱点变成下一道练习。',
    cta: '开始刷题',
  },
  {
    eyebrow: '05 / STUDIO',
    title: 'AI 教学工坊',
    body: '视频、讲义、百科、问答 —— 一个节点对应四类多模态资源自动生成。',
    cta: '探索工坊',
  },
  {
    eyebrow: '06 / ASSESS',
    title: '评测系统',
    body: '能力评估、章节测验与认证考试, 给学习成果一份可量化的证书。',
    cta: '查看评测',
  },
]

const courses = [
  { tag: 'CS-101', title: 'Python 入门到精通', level: '入门', topics: '语法 · 函数式 · OOP' },
  { tag: 'NC-201', title: '网络通信', level: '中级', topics: 'TCP/IP · HTTP · 路由协议' },
  { tag: 'SS-301', title: '系统安全', level: '中级', topics: '权限控制 · 加密 · 防护' },
  { tag: 'DS-401', title: '数据结构与算法', level: '进阶', topics: '算法 · 复杂度分析' },
]

// ============================================================
// 模板 refs
// ============================================================
const heroCanvasRef = ref<HTMLCanvasElement | null>(null)

// ============================================================
// 页面级 composables —— 副作用全部封装好,挂载/卸载自管理
// ============================================================
useStarfield(heroCanvasRef)
useReveal()

// 命名重映射以匹配现有 template 绑定
const { text: cyclingText, showCursor } = useTypewriter([
  '人工智能',
  '智能助教',
  '学习伙伴',
  '思考伙伴',
])

// ============================================================
// 交互
// ============================================================
const handleSignUp = (): void => {
  router.push('/register')
}
const handleTry = (): void => {
  router.push('/login')
}
const handleFeature = (title: string): void => {
  // ElMessage({ message: `→ ${title}`, customClass: 'x-toast' })
}
const handleCourse = (title: string): void => {
  // ElMessage({ message: `→ ${title}`, customClass: 'x-toast' })
}

// 已登录用户的主 CTA —— 直接进入内部应用
const handleEnterApp = (): void => {
  router.push('/app')
}
</script>

<template>
  <div class="x-home">
    <!-- ============================================================
         NAV BAR
         ============================================================ -->
    <header class="x-nav">
      <div class="x-nav-inner">
        <a class="x-logo">
          <span class="x-brand-icon"><BrandMark :size="22" /></span>
          <span class="x-logo-text">学径 <span class="x-logo-sub">LearnPath</span></span>
          <span class="x-live">
            <span class="x-live-dot"></span>
            <span class="x-live-text">LIVE</span>
          </span>
        </a>

        <div class="x-nav-cta">
          <!-- 主题切换: 始终在最左, 不论登录态都可见 -->
          <button
            class="x-theme-toggle"
            type="button"
            :aria-label="settings.theme === 'dark' ? '切换到 Light 主题' : '切换到 Dark 主题'"
            :title="settings.theme === 'dark' ? '切换到 Light' : '切换到 Dark'"
            @click="toggleTheme"
          >
            <!-- 当前是 dark: 显示太阳 (点击会切回亮) -->
            <svg v-if="settings.theme === 'dark'" width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="4.2" stroke="currentColor" stroke-width="1.6"/>
              <path d="M12 2v2.4M12 19.6V22M4.2 4.2l1.7 1.7M18.1 18.1l1.7 1.7M2 12h2.4M19.6 12H22M4.2 19.8l1.7-1.7M18.1 5.9l1.7-1.7"
                stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            <!-- 当前是 light: 显示月亮 (点击会切到暗) -->
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M20.5 14.5A8.5 8.5 0 019.5 3.5a8.5 8.5 0 1011 11z"
                stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" fill="currentColor" fill-opacity="0.08"/>
            </svg>
          </button>

          <!-- 未登录: Sign in / Sign up 双 CTA -->
          <template v-if="!userStore.isAuthenticated">
            <button class="x-btn x-btn-outline-sm" @click="handleTry">Sign in</button>
            <button class="x-btn x-btn-primary" @click="handleSignUp">Sign up now</button>
          </template>

          <!-- 已登录: Enter app + UserWidget (头像下拉) -->
          <template v-else>
            <button class="x-btn x-btn-primary" @click="handleEnterApp">
              <span style="display:inline-flex;align-items:center;gap:6px">Enter app <IconArrow :size="14" /></span>
            </button>
            <UserWidget />
          </template>
        </div>
      </div>
    </header>

    <!-- ============================================================
         HERO BAND — with starfield canvas
         ============================================================ -->
    <section class="x-band x-hero">
      <canvas ref="heroCanvasRef" class="x-hero-canvas"></canvas>
      <div class="x-hero-glow"></div>

      <div class="x-band-inner x-hero-content">
        <p class="x-eyebrow x-reveal x-reveal-1">INTRODUCING 学径 LEARNPATH ⏤ JUN 2026</p>

        <h1 class="x-display-xl x-reveal x-reveal-2">
          <span class="x-display-line">你的专属</span>
          <span class="x-display-line">
            <span class="x-highlight">AI 学习教练</span>，
            <span class="x-cycling-word">{{ cyclingText }}</span><span class="x-cursor" v-show="showCursor">_</span>
          </span>
        </h1>

        <p class="x-hero-body x-reveal x-reveal-3">
          多智能体协同 · 知识图谱驱动 · 多模态内容生成<br />
          为每位学习者构建科学、高效、可持续的个性化学习体系。
        </p>

        <div class="x-hero-actions x-reveal x-reveal-4">
          <button class="x-btn x-btn-primary x-btn-lg" @click="handleSignUp">
            开始学习之旅
          </button>
          <button class="x-btn x-btn-outline-on-light" @click="handleFeature('announcement')">
            了解更多
          </button>
        </div>

        <!-- feature pills -->
        <div class="x-pill-row x-reveal x-reveal-4">
          <div v-for="p in heroPills" :key="p.text" class="x-pill">
            <span class="x-pill-dot" :class="`is-${p.dot}`"></span>
            <span>{{ p.text }}</span>
          </div>
        </div>
      </div>

      <!-- bottom hairline marker -->
      <div class="x-hero-marker x-reveal">
        <span class="x-eyebrow x-eyebrow-mute">SCROLL ↓</span>
      </div>
    </section>

    <hr class="x-divider" />

    <!-- ============================================================
         GRAPH STRIP — 知识图谱节点生长动画
         首屏进入视口时, .x-reveal → .is-visible 触发节点/连线 stagger
         纯 SVG + CSS keyframes, 不引任何库. 7 节点 ↔ "7 大专业智能体".
         ============================================================ -->
    <section class="x-band x-graph-band">
      <div class="x-band-inner">
        <div class="x-graph-wrap x-reveal">
          <svg class="x-graph" viewBox="0 0 1000 240" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
            <!-- ─── 中心 → 外围 6 条 (e1–e6) ─── -->
            <line class="x-g-edge x-g-edge-1" x1="500" y1="120" x2="180" y2="110" />
            <line class="x-g-edge x-g-edge-2" x1="500" y1="120" x2="310" y2="50" />
            <line class="x-g-edge x-g-edge-3" x1="500" y1="120" x2="320" y2="190" />
            <line class="x-g-edge x-g-edge-4" x1="500" y1="120" x2="680" y2="50" />
            <line class="x-g-edge x-g-edge-5" x1="500" y1="120" x2="690" y2="190" />
            <line class="x-g-edge x-g-edge-6" x1="500" y1="120" x2="820" y2="110" />

            <!-- ─── 兄弟边 4 条 (e7–e10) ─── -->
            <line class="x-g-edge x-g-edge-7" x1="180" y1="110" x2="310" y2="50" />
            <line class="x-g-edge x-g-edge-8" x1="180" y1="110" x2="320" y2="190" />
            <line class="x-g-edge x-g-edge-9" x1="680" y1="50" x2="820" y2="110" />
            <line class="x-g-edge x-g-edge-10" x1="690" y1="190" x2="820" y2="110" />

            <!-- ─── 外围 6 节点 (n2–n7) ─── -->
            <circle class="x-g-node x-g-node-2" cx="180" cy="110" r="8" />
            <circle class="x-g-node x-g-node-3" cx="310" cy="50" r="8" />
            <circle class="x-g-node x-g-node-4" cx="320" cy="190" r="8" />
            <circle class="x-g-node x-g-node-5" cx="680" cy="50" r="8" />
            <circle class="x-g-node x-g-node-6" cx="690" cy="190" r="8" />
            <circle class="x-g-node x-g-node-7" cx="820" cy="110" r="8" />

            <!-- ─── 中心节点 (n1) —— 最后画, 在 SVG stacking 中浮在最上 ─── -->
            <circle class="x-g-node x-g-node-center" cx="500" cy="120" r="14" />
          </svg>

          <!-- 副标题, 跟 PRODUCT band 同款 mute eyebrow -->
          <p class="x-eyebrow x-eyebrow-mute x-graph-cap">
            MULTI-AGENT ⏤ KNOWLEDGE GRAPH ORCHESTRATION
          </p>
        </div>
      </div>
    </section>

    <hr class="x-divider" />

    <!-- ============================================================
         PRODUCT / FEATURES — with dot-grid bg
         ============================================================ -->
    <section class="x-band x-products">
      <div class="x-dot-grid" aria-hidden="true"></div>
      <div class="x-band-inner">
        <p class="x-eyebrow x-reveal">PRODUCT ⏤ CORE MODULES</p>
        <h2 class="x-display-md x-reveal">
          六 大 模 块 <br />
          构成学径的全部能力
        </h2>

        <div class="x-feature-grid">
          <article v-for="(f, i) in features" :key="f.title" class="x-card x-feature-card x-reveal"
            :style="{ transitionDelay: `${i * 80}ms` }" @click="handleFeature(f.title)">
            <p class="x-eyebrow x-eyebrow-mute">{{ f.eyebrow }}</p>
            <h3 class="x-display-sm">{{ f.title }}</h3>
            <p class="x-body">{{ f.body }}</p>
            <div class="x-card-cta">
              <button class="x-btn x-btn-outline-sm" @click.stop="handleFeature(f.title)">
               
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>

    <hr class="x-divider" />

    <!-- ============================================================
         COURSES
         ============================================================ -->
    <section class="x-band x-courses">
      <div class="x-band-inner">
        <p class="x-eyebrow x-reveal">COURSES ⏤ FEATURED THIS MONTH</p>
        <h2 class="x-display-md x-reveal">
          数 门 课 程<br />
          快来一起加入我们的学习
        </h2>

        <div class="x-course-grid">
          <article v-for="(c, i) in courses" :key="c.title" class="x-card x-course-card x-reveal"
            :style="{ transitionDelay: `${i * 60}ms` }" @click="handleCourse(c.title)">
            <p class="x-eyebrow x-eyebrow-mute">{{ c.tag }}</p>
            <h3 class="x-display-xs">{{ c.title }}</h3>
            <div class="x-course-meta">
              <div class="x-course-chips">
                <span class="x-course-chip is-level">{{ c.level }}</span>
                <span class="x-course-chip">{{ c.topics }}</span>
              </div>
              <span class="x-arrow"><IconArrow :size="16" /></span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <hr class="x-divider" />

    <!-- ============================================================
         FOOTER
         ============================================================ -->
    <footer class="x-footer">
      <div class="x-band-inner x-footer-inner">
        <div class="x-footer-brand">
          <span class="x-brand-icon x-brand-icon-sm"><BrandMark :size="16" /></span>
          <span>学径 LearnPath</span>
        </div>
        <div class="x-footer-cols">
          <div class="x-footer-col">
            <p class="x-eyebrow x-eyebrow-mute">PRODUCT</p>
            <a class="x-footer-link">Tutor</a>
            <a class="x-footer-link">Courses</a>
            <a class="x-footer-link">Insights</a>
          </div>
          <div class="x-footer-col">
            <p class="x-eyebrow x-eyebrow-mute">COMPANY</p>
            <a class="x-footer-link">About</a>
            <a class="x-footer-link">Careers</a>
            <a class="x-footer-link">Contact</a>
          </div>
          <div class="x-footer-col">
            <p class="x-eyebrow x-eyebrow-mute">LEGAL</p>
            <a class="x-footer-link">Privacy</a>
            <a class="x-footer-link">Terms</a>
          </div>
        </div>
        <div class="x-footer-bottom">© 2026 学径 LEARNPATH. ALL RIGHTS RESERVED.</div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ============================================================
   ROOT
   ============================================================ */
.x-home {
  background: var(--x-canvas);
  color: var(--x-ink);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ============================================================
   TYPOGRAPHY PRIMITIVES
   ============================================================ */
.x-display-xl {
  font-family: var(--x-font-display);
  font-size: 64px;
  font-weight: 600;
  line-height: 68px;
  letter-spacing: -1.6px;
  color: var(--x-ink);
}

.x-display-md {
  font-family: var(--x-font-display);
  font-size: 36px;
  font-weight: 600;
  line-height: 44px;
  letter-spacing: -0.8px;
  color: var(--x-ink);
}

.x-display-sm {
  font-family: var(--x-font-display);
  font-size: 28px;
  font-weight: 600;
  line-height: 36px;
  letter-spacing: -0.4px;
  color: var(--x-ink);
}

.x-display-xs {
  font-family: var(--x-font-display);
  font-size: 20px;
  font-weight: 600;
  line-height: 28px;
  letter-spacing: -0.2px;
  color: var(--x-ink);
}

.x-display-line {
  display: block;
}

.x-cycling-word {
  display: inline-block;
  background: linear-gradient(180deg, var(--x-ink) 0%, var(--x-body) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Hero 中 "AI 学习教练" 的渐变高亮 —— 蓝→紫, 跟设计稿 brand-name 渐变同源
   故意跟 .x-cycling-word (灰渐变) 区分: 高亮强调身份, 打字机强调动态 */
.x-highlight {
  background: linear-gradient(135deg, var(--x-primary) 0%, oklch(58% 0.18 285) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
}

.x-cursor {
  display: inline-block;
  margin-left: 4px;
  color: var(--x-primary);
  -webkit-text-fill-color: var(--x-primary);
  font-weight: 600;
}

.x-body {
  font-size: 16px;
  font-weight: 400;
  line-height: 24px;
  color: var(--x-body);
}

.x-body-sm-mute {
  font-size: 14px;
  line-height: 20px;
  color: var(--x-body-mid);
}

.x-eyebrow {
  font-family: var(--x-font-mono);
  font-size: 14px;
  line-height: 20px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--x-ink);
}

.x-eyebrow-mute {
  color: var(--x-body-mid);
}

/* ============================================================
   BANDS / LAYOUT
   ============================================================ */
.x-band {
  background: var(--x-canvas);
  padding: 64px 24px;
  position: relative;
}

.x-band-inner {
  max-width: var(--x-container);
  margin: 0 auto;
  position: relative;
}

/* HR 分隔条 —— 保留语义, 视觉上完全隐身, 用 band 自带 padding 撑开间距 */
.x-divider {
  border: 0;
  margin: 0;
  height: 0;
}

/* ============================================================
   BUTTONS
   ============================================================ */
.x-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--x-font-display);
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  border-radius: var(--x-rounded-pill);
  cursor: pointer;
  transition: background 0.18s, color 0.18s,
              box-shadow 0.18s, transform 0.15s;
  white-space: nowrap;
}

.x-btn:active {
  transform: scale(0.97);
}

.x-btn-primary {
  background: var(--x-primary);
  color: var(--x-on-primary);
  border: 0;
  padding: 9px 17px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08),
              0 4px 12px rgba(30, 90, 224, 0.25);
}

.x-btn-primary:hover {
  background: var(--x-primary-hover);
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.10),
              0 8px 20px rgba(30, 90, 224, 0.35);
}

/* 大号 primary CTA —— 用在 hero 主按钮 "开始学习之旅", 比导航栏的小号 primary 重 */
.x-btn-lg {
  font-size: 15px;
  padding: 13px 29px;
  border-radius: 10px;
}

/* 第二级 CTA —— 用 fill 代替 outline, 不画边, 仍保留 "次要" 视觉重量 */
.x-btn-outline-on-light {
  background: var(--x-canvas-soft);
  color: var(--x-ink);
  border: 0;
  padding: 11px 21px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.x-btn-outline-on-light:hover {
  background: var(--x-canvas-mid);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}

.x-btn-outline-sm {
  background: var(--x-canvas-soft);
  color: var(--x-ink);
  border: 0;
  padding: 7px 15px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.x-btn-outline-sm:hover {
  background: var(--x-canvas-mid);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}

/* ============================================================
   NAV (with LIVE pulse)
   ============================================================ */
.x-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  /* 用极淡的多层阴影替代 1px 描边, 给 sticky 顶栏留出"漂浮"感 */
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04),
              0 8px 24px rgba(15, 23, 42, 0.04);
}

.x-nav-inner {
  max-width: var(--x-container);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
}

.x-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--x-ink);
  font-size: 16px;
}

.x-logo-img {
  width: 26px;
  height: 26px;
  object-fit: contain;
}

/* BrandMark wrapper —— 不再画背景, BrandMark 自带 soft color 背景 */
.x-brand-icon {
  display: inline-grid;
  place-items: center;
  width: 32px;
  height: 32px;
  color: var(--x-primary);
  flex-shrink: 0;
}

.x-brand-icon-sm {
  width: 24px;
  height: 24px;
}

/* "学径" 主名后跟一行小号 "LearnPath" 副名 */
.x-logo-sub {
  font-family: var(--x-font-display);
  font-weight: 400;
  font-size: 14px;
  color: var(--x-body-mid);
  margin-left: 4px;
}

.x-logo-text {
  font-weight: 500;
}

.x-live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  margin-left: 4px;
  border: 0;
  border-radius: var(--x-rounded-pill);
  background: rgba(245, 158, 11, 0.14);
  box-shadow: 0 1px 2px rgba(245, 158, 11, 0.08);
}

.x-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--x-accent-amber);
  box-shadow: 0 0 6px var(--x-amber-alpha-50);
  animation: x-pulse 1.6s ease-in-out infinite;
}

.x-live-text {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 1.2px;
  color: var(--x-accent-amber-deep);
}

@keyframes x-pulse {

  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }

  50% {
    opacity: 0.4;
    transform: scale(0.85);
  }
}

@keyframes x-spin {
  to {
    transform: rotate(360deg);
  }
}

/* nav CTA wrapper —— 容纳 Sign in / Sign up 或 Enter app + UserWidget */
.x-nav-cta {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 主题切换按钮 —— 36×36 圆形图标按钮, 与 Sign in / Sign up 视觉重量对齐,
   颜色全走 token, 亮 / 暗主题都会自然反相 */
.x-theme-toggle {
  width: 36px;
  height: 36px;
  border: 1px solid var(--x-hairline);
  border-radius: 50%;
  background: var(--x-canvas);
  color: var(--x-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
  flex-shrink: 0;
  padding: 0;
}
.x-theme-toggle:hover {
  background: var(--x-canvas-soft);
  border-color: var(--x-hairline-strong);
}
.x-theme-toggle:active {
  transform: scale(0.94);
}

/* ============================================================
   HERO + starfield + glow
   ============================================================ */
.x-hero {
  padding-top: 120px;
  padding-bottom: 120px;
  overflow: hidden;
}

.x-hero-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

/* extremely subtle radial glow — accent colors stay rare */
.x-hero-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(ellipse 50% 40% at 20% 50%, var(--x-blue-alpha-06), transparent 70%),
    radial-gradient(ellipse 40% 35% at 80% 20%, var(--x-amber-alpha-08), transparent 70%);
}

.x-hero-content {
  position: relative;
  z-index: 1;
}

.x-hero .x-eyebrow {
  margin-bottom: 32px;
}

.x-hero .x-display-xl {
  margin-bottom: 32px;
  margin-left: -2px;
}

.x-hero-body {
  font-size: 18px;
  line-height: 28px;
  color: var(--x-body);
  max-width: 540px;
  margin-bottom: 32px;
}

.x-hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* Hero CTA 下的 feature pill row —— 3 个胶囊横排, 强调平台卖点 */
.x-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.x-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 0;
  border-radius: var(--x-rounded-pill);
  font-size: 13px;
  color: var(--x-body);
  backdrop-filter: blur(10px) saturate(160%);
  -webkit-backdrop-filter: blur(10px) saturate(160%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
              0 4px 14px rgba(15, 23, 42, 0.04);
}

.x-pill-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.x-pill-dot.is-blue {
  background: var(--x-primary);
}

.x-pill-dot.is-green {
  background: oklch(62% 0.14 168);
}

.x-pill-dot.is-purple {
  background: oklch(58% 0.18 285);
}

.x-hero-marker {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1;
  animation: x-bob 2.4s ease-in-out infinite;
}

@keyframes x-bob {

  0%,
  100% {
    transform: translate(-50%, 0);
    opacity: 0.6;
  }

  50% {
    transform: translate(-50%, 6px);
    opacity: 1;
  }
}

/* ============================================================
   GRAPH STRIP — 知识图谱节点生长 (替代原 stats band)

   原则:
     - 不引任何动画/可视化库, 全部 CSS keyframes + SVG
     - 元素首次进入视口才开始动画 (依赖 .x-reveal → .is-visible)
     - 中心节点持续 pulse 让"在跑"的感觉延续, 不只是一次性 build-up
   ============================================================ */
.x-graph-band {
  padding: 56px 24px;
}

.x-graph-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.x-graph {
  width: 100%;
  max-width: 880px;
  height: auto;
  display: block;
  /* 留点呼吸感, 不让节点贴 band 边界 */
  padding: 0 8px;
}

.x-graph-cap {
  text-align: center;
  font-size: 12px;
  letter-spacing: 1.6px;
}

/* ─── 节点 base ─── */
.x-g-node {
  fill: var(--x-ink);
  opacity: 0;
  transform-origin: center;
  transform-box: fill-box;
}

/* 中心节点 —— 大一号, 主色, 带柔光 + 持续呼吸 */
.x-g-node-center {
  fill: var(--x-primary);
  filter: drop-shadow(0 0 6px var(--x-blue-alpha-06, rgba(64, 96, 232, 0.35)));
}

/* ─── 连线 base ─── */
.x-g-edge {
  stroke: var(--x-ink);
  stroke-opacity: 0.28;
  stroke-width: 1.2;
  fill: none;
  /* 大于任何一条线的长度, 让 offset → 0 的过程覆盖整段 */
  stroke-dasharray: 400;
  stroke-dashoffset: 400;
}

/* ─── 进入视口后触发整套动画 ─── */
.x-graph-wrap.is-visible .x-g-node-center {
  animation:
    x-g-node-in 600ms cubic-bezier(0.2, 0.7, 0.2, 1) forwards,
    x-g-pulse-center 2.4s ease-in-out 800ms infinite;
}

.x-graph-wrap.is-visible .x-g-node {
  animation: x-g-node-in 500ms cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}

.x-graph-wrap.is-visible .x-g-edge {
  animation: x-g-edge-draw 700ms cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}

/* ─── Stagger: 中心 → 内圈边 → 外圈节点 → 兄弟边 ─── */
.x-graph-wrap.is-visible .x-g-edge-1 {
  animation-delay: 220ms;
}

.x-graph-wrap.is-visible .x-g-edge-2 {
  animation-delay: 300ms;
}

.x-graph-wrap.is-visible .x-g-edge-3 {
  animation-delay: 380ms;
}

.x-graph-wrap.is-visible .x-g-edge-4 {
  animation-delay: 460ms;
}

.x-graph-wrap.is-visible .x-g-edge-5 {
  animation-delay: 540ms;
}

.x-graph-wrap.is-visible .x-g-edge-6 {
  animation-delay: 620ms;
}

.x-graph-wrap.is-visible .x-g-node-2 {
  animation-delay: 440ms;
}

.x-graph-wrap.is-visible .x-g-node-3 {
  animation-delay: 520ms;
}

.x-graph-wrap.is-visible .x-g-node-4 {
  animation-delay: 600ms;
}

.x-graph-wrap.is-visible .x-g-node-5 {
  animation-delay: 680ms;
}

.x-graph-wrap.is-visible .x-g-node-6 {
  animation-delay: 760ms;
}

.x-graph-wrap.is-visible .x-g-node-7 {
  animation-delay: 840ms;
}

.x-graph-wrap.is-visible .x-g-edge-7 {
  animation-delay: 1000ms;
}

.x-graph-wrap.is-visible .x-g-edge-8 {
  animation-delay: 1080ms;
}

.x-graph-wrap.is-visible .x-g-edge-9 {
  animation-delay: 1160ms;
}

.x-graph-wrap.is-visible .x-g-edge-10 {
  animation-delay: 1240ms;
}

@keyframes x-g-node-in {
  0% {
    opacity: 0;
    transform: scale(0.3);
  }

  60% {
    opacity: 1;
    transform: scale(1.18);
  }

  100% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes x-g-edge-draw {
  to {
    stroke-dashoffset: 0;
  }
}

/* 中心节点保留 r=14, 用 transform scale 做呼吸不影响 layout */
@keyframes x-g-pulse-center {

  0%,
  100% {
    transform: scale(1);
    filter: drop-shadow(0 0 6px var(--x-blue-alpha-06, rgba(64, 96, 232, 0.35)));
  }

  50% {
    transform: scale(1.12);
    filter: drop-shadow(0 0 14px var(--x-blue-alpha-06, rgba(64, 96, 232, 0.55)));
  }
}

/* ============================================================
   PRODUCTS / FEATURES — dot grid + card hover sweep
   ============================================================ */
.x-products {
  overflow: hidden;
}

.x-dot-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(var(--x-ink-alpha-06) 1px, transparent 1px);
  background-size: 24px 24px;
  -webkit-mask-image: radial-gradient(ellipse 60% 80% at 50% 0%, #000 0%, transparent 70%);
  mask-image: radial-gradient(ellipse 60% 80% at 50% 0%, #000 0%, transparent 70%);
  pointer-events: none;
}

.x-products .x-eyebrow,
.x-courses .x-eyebrow {
  margin-bottom: 16px;
}

.x-products .x-display-md,
.x-courses .x-display-md {
  margin-bottom: 48px;
}

.x-feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.x-card {
  background: var(--x-canvas-card);
  border: 0;
  border-radius: var(--x-rounded-lg);
  padding: 32px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  /* 多层柔阴影 = "漂浮在画布上" 的体感, 取代 1px 边线 */
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
              0 8px 24px rgba(15, 23, 42, 0.05);
  transition: box-shadow 0.3s cubic-bezier(0.2, 0.7, 0.2, 1),
              transform 0.3s cubic-bezier(0.2, 0.7, 0.2, 1);
}

/* light sweep across card on hover — primary-tinted on light theme */
.x-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -60%;
  width: 50%;
  height: 200%;
  background: linear-gradient(115deg,
      transparent 0%,
      var(--x-blue-alpha-06) 50%,
      transparent 100%);
  transform: translateX(-100%);
  transition: transform 0.7s ease;
  pointer-events: none;
}

.x-card:hover {
  box-shadow: 0 4px 8px rgba(15, 23, 42, 0.06),
              0 20px 48px rgba(15, 23, 42, 0.10);
  transform: translateY(-4px);
}

.x-card:hover::before {
  transform: translateX(280%);
}

.x-feature-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 280px;
}

.x-feature-card .x-display-sm {
  margin-top: 8px;
}

.x-card-cta {
  margin-top: auto;
  position: relative;
  z-index: 1;
}

/* ============================================================
   COURSES
   ============================================================ */
.x-course-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.x-course-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.x-course-meta {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

/* 课程卡底部 chip 组 —— 两枚: 难度 + 核心覆盖
   故意做得比 hero 的 .x-pill 更"扁平/无圆点", 让两套体系视觉分明 */
.x-course-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.x-course-chip {
  font-family: var(--x-font-mono);
  font-size: 11px;
  letter-spacing: 0.8px;
  color: var(--x-body-mid);
  padding: 4px 9px;
  border: 0;
  border-radius: 4px;
  background: var(--x-canvas-soft);
  white-space: nowrap;
}

/* 难度等级 chip —— 用稍深的填色代替描边, 跟"覆盖范围" chip 拉开层级 */
.x-course-chip.is-level {
  color: var(--x-ink);
  background: var(--x-canvas-mid);
  font-weight: 600;
}

.x-arrow {
  color: var(--x-ink);
  font-size: 16px;
  transition: transform 0.2s, color 0.2s;
  flex-shrink: 0;
}

.x-course-card:hover .x-arrow {
  transform: translateX(4px);
  color: var(--x-primary);
}

/* ============================================================
   FOOTER
   ============================================================ */
.x-footer {
  background: var(--x-canvas);
  padding: 48px 24px;
}

.x-footer-inner {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 48px;
  align-items: start;
}

.x-footer-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: var(--x-ink);
}

.x-footer-cols {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}

.x-footer-col {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.x-footer-col .x-eyebrow {
  margin-bottom: 4px;
}

.x-footer-link {
  font-size: 14px;
  color: var(--x-body);
  cursor: pointer;
  transition: color 0.15s;
}

.x-footer-link:hover {
  color: var(--x-ink);
}

.x-footer-bottom {
  grid-column: 1 / -1;
  /* 不画分隔线, 用更大上 padding + 颜色降级给"页脚版权"自然下沉感 */
  padding-top: 32px;
  margin-top: 16px;
  font-size: 12px;
  color: var(--x-body-mid);
  font-family: var(--x-font-mono);
  letter-spacing: 1.2px;
  opacity: 0.85;
}

/* ============================================================
   SCROLL REVEAL
   ============================================================ */
.x-reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.7s cubic-bezier(0.2, 0.7, 0.2, 1),
    transform 0.7s cubic-bezier(0.2, 0.7, 0.2, 1);
  will-change: opacity, transform;
}

.x-reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* hero reveal staggering */
.x-reveal-1.is-visible {
  transition-delay: 0ms;
}

.x-reveal-2.is-visible {
  transition-delay: 120ms;
}

.x-reveal-3.is-visible {
  transition-delay: 240ms;
}

.x-reveal-4.is-visible {
  transition-delay: 360ms;
}

/* ============================================================
   RESPONSIVE
   ============================================================ */
@media (max-width: 1024px) {
  .x-display-xl {
    font-size: 48px;
    line-height: 54px;
    letter-spacing: -1.2px;
  }

  /* 6 张卡 3 列 → 2 列 (中屏上 2x3 比 3x2 更不拥挤) */
  .x-feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .x-course-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {

  .x-live,
  .x-logo-sub {
    display: none;
  }

  .x-band {
    padding: 48px 16px;
  }

  .x-hero {
    padding-top: 80px;
    padding-bottom: 100px;
  }

  .x-display-xl {
    font-size: 36px;
    line-height: 42px;
    letter-spacing: -0.8px;
  }

  .x-display-md {
    font-size: 28px;
    line-height: 36px;
    letter-spacing: -0.4px;
  }

  .x-display-sm {
    font-size: 24px;
    line-height: 32px;
  }

  .x-feature-grid,
  .x-course-grid {
    grid-template-columns: 1fr;
  }

  .x-footer-inner {
    grid-template-columns: 1fr;
  }

  .x-footer-cols {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .x-reveal {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .x-live-dot,
  .x-hero-marker,
  .x-cursor {
    animation: none;
  }

  .x-card::before {
    display: none;
  }
}
</style>
