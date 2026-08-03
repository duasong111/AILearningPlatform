# Icon 库使用规范

> Duotone 蓝白 SVG icon 系统 — 当前共 **44 个** icon, 覆盖品牌 / 导航 / 学科 / 状态 / UI 五类。
> 全部手写, 不依赖图标库。所有 icon 都是单文件 SFC + `defineProps<{ size?: number | string }>()`。

---

## 1. 目录结构

```
src/components/icons/
├── index.ts                  ← 唯一的 barrel, 所有 import 入口
├── brand/
│   ├── BrandMark.vue         ← 站标 (24×24 圆角方 + L 路径)
│   └── BrandFavicon.vue      ← 浏览器 favicon 用, 颜色对比更强
├── nav/         (10)         ← 顶栏导航: Home / Galaxy / Dialog / Plan / Book / ...
├── subject/     (7)          ← 学科徽标: Math / Physics / Chemistry / ...
├── status/      (10)         ← 反馈类: Check / Cross / Warn / Sparkle / ...
└── ui/          (15)         ← 工具类: Gear / Search / Notepad / Chat / Bulb / ...
```

**新增 icon 只能加到这 5 个目录之一**, 不要在 view 里内联 `<svg>`。

---

## 2. 设计令牌 (Design Tokens)

| 维度 | 规则 | 出处 |
|---|---|---|
| `viewBox` | 永远 `0 0 24 24` | — |
| 默认 size | 16 (UI) / 17-18 (顶栏 nav) / 22 (品牌 logo) | 各 SFC 内置 |
| 软色 (backdrop) | `#DBE7FF` —— **SVG 内硬编码** | 与 `--x-primary-soft` 同色 |
| 主色 (foreground) | `currentColor` —— 由父级 `color:` 控制 | 跟 `--x-primary` / 错误色切换 |
| 描边宽 | 1.5 – 2.2 px | 1.6 是 nav, 2-2.2 是状态/强调 |
| 圆角 (stroked paths) | `stroke-linecap="round" stroke-linejoin="round"` | 不要省略, 否则锯齿 |
| 无障碍 | `aria-hidden="true"` (装饰用) | 屏幕阅读器跳过 |

色板来源 `src/assets/base.css`:

```css
--x-primary:        #1E5AE0   /* 主色, 父元素 color: var(--x-primary) */
--x-primary-soft:   #DBE7FF   /* 软色, SVG 内直接 fill="#DBE7FF" */
--x-error:          oklch(58% 0.20 25)   /* 错误态 */
```

---

## 3. Duotone 配色规则 —— **核心约定**

每个 icon 最多两层:

```vue
<!-- 软色 backdrop: 永远 fill="#DBE7FF" -->
<rect x="2" y="2" width="20" height="20" rx="6" fill="#DBE7FF" />

<!-- 主色 foreground: 永远 fill="currentColor" 或 stroke="currentColor" -->
<path d="M8 8 V16 H16" fill="none" stroke="currentColor" stroke-width="2" />
```

**为什么主色用 `currentColor`**: 让父级 CSS 的 `color:` 决定主色,
就能用同一个 icon 切 active / hover / 错误态, 不用维护多套 svg。

调用方必须给父元素加 `color` —— 单写 `<IconCheck />` 会 fallback 到 `currentColor` 默认色 (通常继承自 body):

```vue
<!-- ✅ 正确: 父级 inline-flex + color -->
<span style="display:inline-flex;color:var(--x-primary)">
  <IconCheck :size="16" />
</span>

<!-- ❌ 错误: SVG 会塌掉, 没基线对齐 -->
<div><IconCheck :size="16" /></div>
```

---

## 4. 标准 SFC 模板

```vue
<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>

<template>
  <svg
    :width="size ?? 16"
    :height="size ?? 16"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <!-- soft backdrop -->
    <element ... fill="#DBE7FF" />
    <!-- primary foreground (currentColor) -->
    <element ... fill="currentColor" />
  </svg>
</template>
```

注意:
- 组件名永远 `IconXxx` (PascalCase, 前缀 `Icon` / `Brand`)
- 文件名 = 组件名 + `.vue`
- 不要写 `<style scoped>` (icon 是纯图形, 颜色由父级控制)
- 不要给 svg 加外层 `<div>`, 让父级容器管布局

---

## 5. 三种常见用法

### 5.1 顶栏 / 按钮内联

```vue
<button class="x-btn x-btn-primary">
  <span style="display:inline-flex;align-items:center;gap:6px">
    <IconPlus :size="13" /> Add course
  </span>
</button>
```

### 5.2 状态徽章

```vue
<span class="x-qa-badge is-answered">
  <span style="display:inline-flex;align-items:center;gap:3px">
    <IconCheck :size="11" /> 已解决
  </span>
</span>
```

### 5.3 动态切换 (用 `<component :is>`)

```vue
<component
  :is="isCorrect ? IconCheck : IconCross"
  :size="20"
/>
```

适用: 对错状态、加载中/失败二态、空态切换。

---

## 6. 新增一个 icon 的流程

1. **定类**: 选好 `brand/ nav/ subject/ status/ ui/` 五个目录之一
2. **起名**: PascalCase + 目录前缀 (例: `ui/IconBulb.vue`, `nav/IconRecords.vue`)
3. **写 SFC**: 套上面 §4 模板, 默认 size 跟同目录其他 icon 保持一致
4. **画图**: viewBox 24×24, 软色 + 主色两层, 描边 1.6 / 2
5. **注册到 barrel**: 在 `index.ts` 对应区块加一行 `export { default as IconXxx } from './<dir>/IconXxx.vue'`
6. **跑 type-check**: `npm run type-check` —— 漏注册会报模块找不到

完成后, 业务侧直接 `import { IconXxx } from '@/components/icons'` 就能用。

---

## 7. Do / Don't

| ✅ Do | ❌ Don't |
|---|---|
| 用 `<IconXxx :size="14" />` 组件 | 在 view 里内联 `<svg ...>...</svg>` |
| 父级 `display:inline-flex` + `color: var(--x-primary)` | 让 SVG 裸放在 block 容器里 |
| `currentColor` 作为主色 | 在 icon 内硬编码 `fill="#1E5AE0"` |
| 软色统一 `#DBE7FF` | 改软色成浅灰 / 浅粉 / 其他 |
| 描边 `stroke-linecap="round"` | 写方头 stroke, 锯齿明显 |
| 装饰用 `aria-hidden="true"` | 装饰用 icon 不写 aria |

---

## 8. 何时该新增 vs 复用现有

| 场景 | 动作 |
|---|---|
| 概念已存在 (e.g. "错误") | 复用 `IconCross`, 改 size + color |
| 同概念不同重量 (light/bold) | 优先复用, 真要补再开新文件 |
| 全新的语义节点 | 新建, 不要往现有 icon 里塞第二含义 |
| 状态 icon 加动画 (spin / pulse) | 在父级加 `animation`, 别改 SFC |

---

**维护者备忘**: 任何调整软色 / 默认 size / viewBox 都会影响全站 16+ view, 改之前先在 DesignDemo 页面 (`/app/design`) 跑一遍。
