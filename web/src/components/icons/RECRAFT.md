# Recraft Icon 生成规范

> 用 Recraft AI 重新生成 / 补齐 icon 库时的操作手册。
> 目标: 一次性产出 24×24 duotone SVG, 直接接入 `src/components/icons/`。
> 当前已交付的 44 个 icon 都是**手写** SVG, 本文档用来描述"如果用 Recraft 重新做"应该怎么调。

---

## 1. 选型与模型

| 维度 | 选择 | 理由 |
|---|---|---|
| 工具 | MCP `mcp__recraft__*` | 项目已配好, 直接调 |
| 模型 | `recraftv4_1` | v4.1 性价比最高, vector 质量够用 |
| `input_image_type` | `vector_illustration` | 出 SVG, 可编辑; 别用 `icon` (仅 v2 支持) |
| 备选 (高保真) | `recraftv4_1_pro` | 慢 2-3×, 视觉一致性好, 风格定型后切 |
| 兜底 (老) | `recraftv3` | 兼容 `logo_raster` 风格 |

**批量生成时**:
- `n: 4-6` 让 Recraft 一次出多张, 人工挑最干净的那张
- 一次调用 ≈ 1 个 credit, 一组 6 张 ≈ 1 credit

---

## 2. 风格创建 (一次性, 必做)

**不要直接 generate, 先 create_style** —— Recraft 默认风格会出来紫色 / 黑色 / 杂乱线稿, 跟蓝白 duotone 体系对不上。

```python
mcp__recraft__create_style(
    input_image_type="vector_illustration",
    model="recraftv4_1",
    input_style_images_urls=[<5 张参考 icon 的托管 URL>],
    style_prompt=(
        "Duotone flat vector icon, soft pastel blue backdrop shape "
        "paired with a single-color foreground glyph. "
        "24x24 viewBox, 2px rounded stroke. "
        "Minimalist, geometric, single-color foreground only. "
        "No gradients, no shadows, no 3D, no text, no outlines around the backdrop."
    )
)
```

参考图建议: 从 `src/components/icons/{nav,status,ui}/` 里选 5 个最具代表性的
(推荐 `IconHome` `IconCheck` `IconSearch` `IconSparkle` `IconBulb`),
先把它们的 SVG 渲染成 PNG 托管到 OSS / 公共 URL, 再喂给 create_style。

记下返回的 `style_id`, 后续所有 generate 都用这个 ID (不是 `input_style` 字符串)。

---

## 3. Prompt 模板 (按 5 类)

每条 prompt 都遵守同一骨架, 只换 `{subject}` 和 `{category_intent}`:

```
Flat duotone vector icon of {subject}. {category_intent}.
24x24 viewBox, rounded 2px stroke, no outlines around backdrop.
Single-color foreground glyph on a soft pastel-blue rounded backdrop shape.
Minimalist, geometric, friendly, no text, no gradients, no shadows, no 3D.
```

### 3.1 brand/ (2 个)
```
{subject}: logo wordmark / brand mark
{category_intent}: 圆形或圆角方形容器, 内部单一字形 (字母 / 路径)
```
- BrandMark prompt: `Flat duotone brand logo mark, stylized "L" path with a dot endpoint, on a rounded square pastel-blue backdrop. 24x24 viewBox. Single-color foreground, no text labels.`
- BrandFavicon prompt: 同上但视觉对比更强 (用于浏览器 favicon 16×16)

### 3.2 nav/ (10 个)
```
{category_intent}: 单一识别物体, 适配 16-18px 显示, 顶栏导航用
```
- 例子: `Flat duotone vector icon of a house silhouette with a pitched roof, on a soft pastel-blue backdrop. 24x24 viewBox, rounded 2px stroke, no outlines around backdrop. Minimalist, single-color foreground.`

### 3.3 subject/ (7 个)
```
{category_intent}: 学科符号 (数学公式片段 / 物理实验器 / 化学瓶 / DNA / 几何体 / 电路 / 细胞)
```
- 例子 (Chemistry): `Flat duotone vector icon of a chemistry flask with bubbles, on a soft pastel-blue backdrop. 24x24 viewBox, rounded 2px stroke. Minimalist, single-color foreground.`

### 3.4 status/ (10 个)
```
{category_intent}: 高识别度符号, 圆/方底色块 + 前景符号, 适配 11-18px
```
- 例子 (Check): `Flat duotone vector icon of a check mark inside a circle, on a soft pastel-blue circular backdrop. 24x24 viewBox, rounded 2px stroke. Minimalist, single-color foreground.`
- 例外: `IconSparkle` / `IconRetry` / `IconArrow` / `IconChevron` 这类**无背景**符号, prompt 改为 `on a transparent background, single-color glyph only` —— 它们的设计就只是前景 path, 不带 backdrop

### 3.5 ui/ (15 个)
```
{category_intent}: 工具/上下文符号, 主体清晰, 适配 12-16px
```

**通用守则**:
- 必须带 `no text, no gradients, no shadows, no 3D` —— Recraft 默认会加光泽
- 必须带 `rounded 2px stroke` —— 否则会出尖锐折线
- 想要"无 backdrop" 的 icon, 必须显式说 `on a transparent background, single-color glyph only`

---

## 4. 单条 icon 的生成步骤

```python
# Step 1: 拿风格 ID (一次创建, 多次复用)
style_id = "<create_style 返回的 id>"

# Step 2: 生成 4-6 张候选
result = mcp__recraft__generate_image(
    prompt=PROMPT,                                  # §3 模板
    image_size="1:1",
    input_image_type="vector_illustration",
    input_style_id=style_id,
    model="recraftv4_1",
    n=4,                                            # 出 4 张挑
)

# Step 3: 从 result["images"] 里挑 url
best_url = pick_cleanest(result["images"])         # 人工或程序挑
```

---

## 5. 后处理 (Recraft 不会帮你做)

Recraft 出来的 SVG 通常不符合我们的 SFC 模板, 必须手工改。

### 5.1 颜色替换 (关键)

Recraft 会把软色渲成它自己的浅蓝 (不是精确 `#DBE7FF`), 主色也是灰阶或深色,
需要批量替换:

```bash
# 1. 下载 SVG
curl -o tmp.svg "$best_url"

# 2. 颜色替换 —— 用 sed 把"近似色"都归到我们的两个色值
#    软色: 任何 fill="...blue浅色" → fill="#DBE7FF"
#    主色: 任何 fill/stroke 非软色 → fill="currentColor" (或 stroke="currentColor")
# 建议: 拿眼睛看, Recraft 出的色可能跟 #DBE7FF 差几个色阶, 直接在编辑器里改
```

替换完后, SVG 里**只能**出现两个颜色值: `#DBE7FF` 和 `currentColor`。

### 5.2 viewBox 校验

Recraft 默认 viewBox 可能是 `0 0 32 32` 或 `0 0 100 100`, 必须改成 `0 0 24 24`。
改完跑 `npm run type-check` (SFC 模板里写死了 24×24)。

### 5.3 包成 SFC

把清理过的 SVG 内容包成 SFC (§ 4 of README):

```vue
<script setup lang="ts">
defineProps<{ size?: number | string }>()
</script>
<template>
  <svg :width="size ?? 16" :height="size ?? 16" viewBox="0 0 24 24" aria-hidden="true">
    <!-- 把 Recraft 的 path 复制进来, fill/stroke 值已替换 -->
  </svg>
</template>
```

### 5.4 注册到 barrel

在 `src/components/icons/index.ts` 对应区段加一行:

```ts
export { default as IconXxx } from './<dir>/IconXxx.vue'
```

---

## 6. 校验清单

每张 Recraft 出的 icon 在合并前必过:

- [ ] viewBox = `0 0 24 24`
- [ ] 软色唯一, 值为 `#DBE7FF`
- [ ] 主色唯一, 值为 `currentColor` (fill 或 stroke)
- [ ] 描边 path 带 `stroke-linecap="round" stroke-linejoin="round"`
- [ ] 没有 `text` 元素 / 渐变 / filter / shadow
- [ ] 在 11px / 14px / 18px / 22px 四档 size 下都视觉清晰
- [ ] 命名跟 `src/components/icons/index.ts` 注册名一致
- [ ] `npm run type-check` 通过

视觉走查: 把候选 4 张并排, 在 DesignDemo 页面 ( `/app/design` ) 上跟已有 icon 对齐看。

---

## 7. 成本估算 (单次)

| 项 | 数量 | 单价 | 小计 |
|---|---|---|---|
| `create_style` | 1 | ~1 credit | 1 |
| `generate_image` (n=4) | 44 (icon 数) | ~4 credits | 176 |
| 人工筛选 + 后处理 | 44 | — | ~2h |

44 个 icon 一次刷新大约 **177 credits**, 按 Recraft Pro plan (≈500 credits/月) 单月可刷 2-3 轮。

---

## 8. 已知坑 (踩过记录)

- Recraft **不会保留** `currentColor` 概念 —— 它不知道我们的父级 color 体系, 必须后处理替换
- Recraft **不会**自动出 24×24, 默认会出 32×32 或更大, 改 viewBox 不会改 path 坐标, 视觉会"放大" —— 后处理时**整张重描**比改 viewBox 靠谱
- v3 / v4 的 `icon` 输入类型走的不是 vector pipeline, 出来是 PNG, 必须再调 `vectorize_image` —— 别用
- 创 style 时喂参考图必须是**已 host 的 URL**, 本地文件要先 `request_upload_url` 上传
- Recraft 对中文 prompt 解析不稳定, 所有 prompt **写英文**, 在描述里提 "for a Chinese learning platform" 之类上下文
- 状态类的 `IconSparkle` / `IconArrow` 这种**无背景**的, 创 style 时**不要**混进参考图集, 否则出来的都带背景
