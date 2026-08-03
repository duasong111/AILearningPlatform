---
version: beta
name: aiteach-design
description: AiTeach (学径) design system — Human / approachable + Academic-tech overlay. Built on oklch color palette with academic blue primary, growth teal-green secondary, and indigo AI accent. SF Pro for display/body, JetBrains Mono for tracked mono labels. Light canvas; cards use hairline borders by default, with a shadow-based opt-in style (see `shadows.card`) for views that want a modern borderless look.

colors:
  # ── Surface ──────────────────────────────────────────────
  bg:            "oklch(98.5% 0.004 240)"     # near-white page bg with faint blue tint
  surface:       "oklch(100% 0 0)"           # pure white card / panel surface
  surface-alt:   "oklch(96.5% 0.006 240)" # hover / pressed surface (slate-50 equivalent)
  canvas:        "oklch(100% 0 0)"           # alias for surface (backward compat)
  canvas-soft:   "oklch(96.5% 0.006 240)"   # alias for surface-alt
  canvas-mid:    "oklch(93% 0.008 240)"     # nested surfaces / table headers
  canvas-tint:    "oklch(94% 0.04 255)"     # primary-tinted surface

  # ── Text ──────────────────────────────────────────────────
  fg:            "oklch(20% 0.02 240)"       # primary text — near-black with blue tint
  fg-hover:      "oklch(25% 0.02 240)"       # hover text
  fg-secondary:  "oklch(38% 0.018 240)"     # secondary body text
  ink:           "oklch(20% 0.02 240)"       # alias (backward compat)
  body:          "oklch(38% 0.018 240)"     # alias (backward compat)
  body-mid:      "oklch(54% 0.014 240)"     # caption / mute text
  mute:          "oklch(54% 0.014 240)"     # disabled / placeholder

  # ── Border ────────────────────────────────────────────────
  border:        "oklch(91% 0.006 240)"      # hairline divider — 1px on light
  border-strong: "oklch(82% 0.01 240)"      # hover border
  hairline:      "oklch(91% 0.006 240)"     # alias (backward compat)
  hairline-strong:"oklch(82% 0.01 240)"     # alias (backward compat)

  # ── Primary — academic blue (trust, focus, main CTA) ─────
  primary:       "oklch(52% 0.18 255)"     # academic blue — filled CTA, active nav
  primary-hover: "oklch(46% 0.20 255)"     # pressed / hover
  primary-light: "oklch(94% 0.04 255)"     # tint surface for selected/active rows
  primary-fg:    "oklch(100% 0 0)"         # text on primary
  on-primary:    "oklch(100% 0 0)"         # alias (backward compat)

  # ── Secondary — growth teal-green (progress, learning) ────
  secondary:     "oklch(60% 0.14 168)"       # growth green — progress, completion
  secondary-light:"oklch(93% 0.04 168)"     # tint surface
  secondary-fg:  "oklch(100% 0 0)" # text on secondary

  # ── AI accent — indigo/violet (agent activity, generation) ─
  ai:            "oklch(55% 0.20 280)"       # indigo-violet — AI messages, agent badge
  ai-light:      "oklch(92% 0.05 280)"      # tint surface for AI elements
  ai-glow:       "oklch(65% 0.22 280 / 0.25)" # glow effect for generating state

  # ── Status ────────────────────────────────────────────────
  success:       "oklch(62% 0.16 155)"       # green — mastered, complete
  success-light: "oklch(94% 0.04 155)"      # tint surface
  warning:       "oklch(74% 0.14 80)"       # amber — learning, in-progress
  warning-light: "oklch(95% 0.04 80)"       # tint surface
  danger:        "oklch(58% 0.20 25)"        # red — error, danger
  danger-light:  "oklch(95% 0.04 25)"       # tint surface
  error:         "oklch(58% 0.20 25)"        # alias (backward compat)
  error-soft:    "oklch(95% 0.04 25)"       # alias (backward compat)

  # ── Translucent ink (outline border on light) ──────────────
  ink-alpha-06:  "oklch(20% 0.02 240 / 0.06)"
  ink-alpha-15:  "oklch(20% 0.02 240 / 0.15)"
  ink-alpha-30:  "oklch(20% 0.02 240 / 0.30)"
  ink-alpha-45:  "oklch(20% 0.02 240 / 0.45)"

typography:
  display-xl:
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 48px
    fontWeight: 700
    lineHeight: 56px
    letterSpacing: -0.01em
  display-lg:
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 36px
    fontWeight: 700
    lineHeight: 44px
    letterSpacing: -0.008em
  display-md:
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 28px
    fontWeight: 600
    lineHeight: 36px
    letterSpacing: -0.004em
  display-sm:
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 22px
    fontWeight: 600
    lineHeight: 30px
    letterSpacing: 0
  display-xs:
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 600
    lineHeight: 26px
    letterSpacing: 0
  body-lg:
    fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 28px
    letterSpacing: 0
  body-md:
    fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 400
    lineHeight: 24px
    letterSpacing: 0
  body-sm:
    fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 20px
    letterSpacing: 0
  caption-mono:
    fontFamily: "'JetBrains Mono', 'SF Mono', 'IBM Plex Mono', ui-monospace, Menlo, monospace"
    fontSize: 12px
    fontWeight: 500
    lineHeight: 16px
    letterSpacing: 1.4px
  caption-mono-sm:
    fontFamily: "'JetBrains Mono', 'SF Mono', 'IBM Plex Mono', ui-monospace, Menlo, monospace"
    fontSize: 11px
    fontWeight: 500
    lineHeight: 16px
    letterSpacing: 1.2px
  button-md:
    fontFamily: "'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: 15px
    fontWeight: 500
    lineHeight: 24px
    letterSpacing: 0

rounded:
  none:  0px
  sm:    6px
  md:    10px
  lg:    14px
  xl:    20px
  pill:  9999px
  full:  9999px

spacing:
  xxs: 2px
  xs:  4px
  sm:  8px
  md:  12px
  lg: 16px
  xl:  24px
  2xl: 32px
  3xl: 48px
  4xl: 64px

shadows:
  none:     "none"
  sm:       "0 1px 2px oklch(20% 0.02 240 / 0.06)"
  md:       "0 4px 12px oklch(20% 0.02 240 / 0.08)"
  lg:       "0 12px 32px oklch(20% 0.02 240 / 0.10)"
  glow:     "0 0 24px var(--ai-glow)"
  # Card shadows — used by views that opt into the modern
  # "borderless + shadow" card style (starting with ReportsView).
  # When applying, drop `border` on the container, set
  # `box-shadow: var(--shadow-card)`, and pair with a hover state
  # using `shadow-card-hover` + `translateY(-2px)`.
  card:        "0 2px 4px oklch(20% 0.02 240 / 0.06), 0 8px 24px oklch(20% 0.02 240 / 0.10)"
  card-hover:  "0 4px 8px oklch(20% 0.02 240 / 0.08), 0 16px 40px oklch(20% 0.02 240 / 0.14)"
  toast:    "0 4px 12px oklch(20% 0.02 240 / 0.08), 0 1px 3px oklch(20% 0.02 240 / 0.04)"
  modal:    "0 12px 32px oklch(20% 0.02 240 / 0.10), 0 2px 8px oklch(20% 0.02 240 / 0.05)"
  popover:  "0 8px 24px oklch(20% 0.02 240 / 0.08)"

components:
  nav-bar:
    backgroundColor: "oklch(100% 0 0 / 0.85)"
    textColor: "{colors.fg}"
    typography: "{typography.body-sm}"
    padding: "{spacing.md} {spacing.xl}"
    backdropOpacity: 0.85
  nav-link:
    textColor: "{colors.body-mid}"
    typography: "{typography.caption-mono}"
    activeTextColor: "{colors.fg}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-fg}"
    borderColor: "{colors.primary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.xs} {spacing.lg}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.fg}"
    borderColor: "{colors.border}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.xs} {spacing.lg}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.fg-secondary}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.xs} {spacing.lg}"
  button-outline-on-light:
    backgroundColor: "transparent"
    textColor: "{colors.fg}"
    borderColor: "{colors.ink-alpha-15}"
    typography: "{typography.button-md}"
    rounded: "{rounded.md}"
    padding: "{spacing.sm} {spacing.lg}"
  button-outline-sm:
    backgroundColor: "transparent"
    textColor: "{colors.fg}"
    borderColor: "{colors.ink-alpha-15}"
    typography: "{typography.button-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.xs} {spacing.md}"
  text-input:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.fg}"
    borderColor: "{colors.border}"
    focusBorderColor: "{colors.primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md} {spacing.lg}"
  card-content:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.fg}"
    borderColor: "{colors.border}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  card-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.fg}"
    borderColor: "{colors.border}"
    hoverBorderColor: "{colors.border-strong}"
    hoverShadow: "{shadows.md}"
    typography: "{typography.body-md}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  hero-band:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.fg}"
    typography: "{typography.display-xl}"
    padding: "{spacing.4xl} {spacing.xl}"
  content-band:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.fg}"
    typography: "{typography.display-lg}"
    padding: "{spacing.4xl} {spacing.xl}"
  eyebrow-mono:
    textColor: "{colors.fg}"
    typography: "{typography.caption-mono}"
  divider-hairline:
    borderColor: "{colors.border}"
  footer:
    backgroundColor: "{colors.surface-alt}"
    textColor: "{colors.body}"
    typography: "{typography.body-sm}"
    padding: "{spacing.3xl} {spacing.xl}"
  badge-primary:
    backgroundColor: "{colors.primary-light}"
    textColor: "{colors.primary}"
  badge-success:
    backgroundColor: "{colors.success-light}"
    textColor: "{colors.success}"
  badge-warning:
    backgroundColor: "{colors.warning-light}"
    textColor: "oklch(45% 0.12 80)"
  badge-ai:
    backgroundColor: "{colors.ai-light}"
    textColor: "{colors.ai}"
  avatar:
    backgroundColor: "{colors.primary-light}"
    textColor: "{colors.primary}"
  progress-fill:
    backgroundColor: "{colors.primary}"
    borderRadius: "{rounded.full}"
  progress-fill-success:
    backgroundColor: "{colors.secondary}"
  progress-fill-ai:
    backgroundColor: "{colors.ai}"
  app-nav:
    backgroundColor: "oklch(100% 0 0 / 0.85)"
    backdropFilter: "blur(16px)"
    borderBottomColor: "{colors.border}"
    height: 56px
  app-shell-row:
    backgroundColor: "transparent"
    activeBackground: "{colors.primary-light}"
    activeIndicator: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md} {spacing.lg}"
  ex-pricing-tier:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-pricing-tier-featured:
    backgroundColor: "{colors.canvas-tint}"
    borderColor: "{colors.primary}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-auth-form-card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
  ex-modal-card:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.lg}"
    padding: "{spacing.xl}"
    shadow: "{shadows.modal}"
  ex-empty-state-card:
    backgroundColor: "{colors.surface-alt}"
    rounded: "{rounded.lg}"
    padding: "{spacing.3xl}"
  ex-toast:
    backgroundColor: "{colors.surface}"
    borderColor: "{colors.border}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md} {spacing.lg}"
    shadow: "{shadows.toast}"
    typography: "{typography.body-sm}"


---

## Overview

AiTeach (学径) is a multi-agent personalized learning platform with a **human, approachable, and academic-tech** aesthetic. The surface is a near-white canvas with a faint blue tint (`oklch(98.5% 0.004 240)`), hairline borders carrying all elevation cues, and a deliberate three-color system: **academic blue** (primary), **growth teal-green** (secondary/progress), and **indigo/violet** (AI activity).

Typography is two-faced: **SF Pro Display** for display headlines (weight 700), **SF Pro Text** for body, paired with **JetBrains Mono** UPPERCASE tracked eyebrows. Light mode only — no dark mode counterpart.

**Key Characteristics:**
- **oklch() color palette** — perceptually uniform, modern color format. Primary academic blue at `oklch(52% 0.18 255)`.
- **Three-color system**: Blue (primary CTA) + Teal-green (secondary, progress) + Indigo/violet (AI accent).
- **SF Pro Display / SF Pro Text** — Apple's system font stack for display and body text. JetBrains Mono for mono labels.
- **Hairline borders** carry elevation on light surfaces. Shadows reserved for floating UI (cards are border-only by default).
- **Badge variants** including `badge-ai` for AI-generated content and `badge-success`/`badge-warning` for status.
- **Avatar system** with primary-light background, AI shimmer animation, typing dots for generating state.
- **Dark canvas for knowledge galaxy** (`oklch(14% 0.02 250)`) — the one exception to the light-surface rule, creating dramatic contrast.

## Colors

### Surface
- **Background** (`{colors.bg}` — `oklch(98.5% 0.004 240)`): The near-white page background with a barely perceptible blue tint.
- **Surface** (`{colors.surface}` — `oklch(100% 0 0)`): Pure white — cards, panels, input backgrounds.
- **Surface Alt** (`{colors.surface-alt}` — `oklch(96.5% 0.006 240)`): Hover/pressed state surface, slightly darker than white.
- **Border** (`{colors.border}` — `oklch(91% 0.006 240)`): 1px hairline dividers — the brand's primary elevation cue.
- **Border Strong** (`{colors.border-strong}` — `oklch(82% 0.01 240)`): Hover border for interactive surfaces.

### Text
- **Foreground** (`{colors.fg}` — `oklch(20% 0.02 240)`): Primary text — near-black with a subtle blue cast (not pure #000000).
- **Foreground Secondary** (`{colors.fg-secondary}` — `oklch(38% 0.018 240)`): Secondary body copy.
- **Muted** (`{colors.mute}` — `oklch(54% 0.014 240)`): Captions, timestamps, disabled states.

### Primary (Academic Blue)
- **`{colors.primary}`** `oklch(52% 0.18 255)`: Academic blue — filled CTA, focus borders, active nav indicator. The brand's primary "color".
- **`{colors.primary-hover}`** `oklch(46% 0.20 255)`: Pressed/hover state for filled primary buttons.
- **`{colors.primary-light}`** `oklch(94% 0.04 255)`: Tint surface for selected/active rows, badges, avatars.
- **`{colors.primary-fg}`** `oklch(100% 0 0)`: White text on primary.

### Secondary (Growth Teal-Green)
- **`{colors.secondary}`** `oklch(60% 0.14 168)`: Growth teal-green — used for progress bars, mastery indicators, completion states.
- **`{colors.secondary-light}`** `oklch(93% 0.04 168)`: Tint surface.
- **`{colors.secondary-fg}`** `oklch(100% 0 0)`: White text on secondary.

### AI Accent (Indigo/Violet)
- **`{colors.ai}`** `oklch(55% 0.20 280)`: Indigo-violet — AI messages, agent badges, AI activity indicators. The "agent color".
- **`{colors.ai-light}`** `oklch(92% 0.05 280)`: Tint surface for AI-related UI (chat bubbles, badges).
- **`{colors.ai-glow}`** `oklch(65% 0.22 280 / 0.25)`: Glow effect for AI generating state.

### Status
- **Success** (`{colors.success}` — `oklch(62% 0.16 155)`) / **Success Light** (`oklch(94% 0.04 155)`)
- **Warning** (`{colors.warning}` — `oklch(74% 0.14 80)`) / **Warning Light** (`oklch(95% 0.04 80)`)
- **Danger** (`{colors.danger}` — `oklch(58% 0.20 25)`) / **Danger Light** (`oklch(95% 0.04 25)`)

### Translucent Ink
The brand's outline-button border colour:
- `ink-alpha-06` `oklch(20% 0.02 240 / 0.06)` — faint bg, dot-grid pattern
- `ink-alpha-15` `oklch(20% 0.02 240 / 0.15)` — **default outline button border** (signature on light)
- `ink-alpha-30` `oklch(20% 0.02 240 / 0.30)` — hover outline border
- `ink-alpha-45` `oklch(20% 0.02 240 / 0.45)` — focus border

## Typography

### Font Family
Three faces:
1. **SF Pro Display** — display headlines, weight 700 with tight tracking.
2. **SF Pro Text** — body copy, weight 400.
3. **JetBrains Mono** — uppercase section eyebrows and metric counters with positive tracking (1.2–1.4 px).

### Hierarchy

| Token | Size | Weight | Line Height | Use |
|---|---|---|---|---|
| `{typography.display-xl}` | 48px | 700 | 56px | Hero headline. |
| `{typography.display-lg}` | 36px | 700 | 44px | Sub-hero displays. |
| `{typography.display-md}` | 28px | 600 | 36px | Section headlines. |
| `{typography.display-sm}` | 22px | 600 | 30px | Card-cluster headings. |
| `{typography.display-xs}` | 18px | 600 | 26px | Inline displays. |
| `{typography.body-lg}` | 18px | 400 | 28px | Lead paragraphs. |
| `{typography.body-md}` | 15px | 400 | 24px | Default body. |
| `{typography.body-sm}` | 13px | 400 | 20px | Secondary body. |
| `{typography.caption-mono}` | 12px | 500 | 16px | Section eyebrow (JetBrains Mono UPPERCASE). |
| `{typography.caption-mono-sm}` | 11px | 500 | 16px | Small mono labels. |
| `{typography.button-md}` | 15px | 500 | 24px | Button label. |

### Principles
- **Display weight 700** on headlines for maximum typographic anchor on light backgrounds.
- **JetBrains Mono UPPERCASE** with1.4 px tracking for every section eyebrow — the brand's signature label style.
- SF Pro Text body at 15px (not 16px) for a tighter, more editorial feel.

## Spacing

Base unit: 4 px.

| Token | Value | Use |
|---|---|---|
| `{spacing.xxs}` | 2px | Micro spacing |
| `{spacing.xs}` | 4px | Tight inline |
| `{spacing.sm}` | 8px | Default small |
| `{spacing.md}` | 12px | Default medium |
| `{spacing.lg}` | 16px | Default large |
| `{spacing.xl}` | 24px | Section padding |
| `{spacing.2xl}` | 32px | Large gap |
| `{spacing.3xl}` | 48px | Section padding |
| `{spacing.4xl}` | 64px | Hero padding |

## Layout

### Grid & Container
- Marketing content centres at ~1200 px (`--content-max`).
- App content is full-width or max-width 90% for dense views.

### Responsive Breakpoints

| Name | Width | Key Changes |
|---|---|---|
| Mobile | < 768px | Grids 1-up or 2-up; hamburger nav. |
| Desktop | ≥ 768px | Full layout. |

### Navigation

**`nav-bar`** — sticky top nav with `backdrop-filter: blur(16px)` on a semi-transparent white surface.
- Height: 56px (`--nav-h`).
- Logo with a28×28px primary-colored icon block.

**`nav-link`** — set in `caption-mono` (JetBrains Mono), active state uses `primary-light` background with `primary` text.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Level 0 — Flat | No shadow, no border. | Default. |
| Level 1 — Hairline | 1px solid `{colors.border}` | Card chrome, button outlines, dividers. |
| Level 2 — Float | `shadows.sm` / `shadows.md` / `shadows.lg` | Hover states on cards. NOT default — only on hover. |
| Level 3 — Floating UI | `shadows.toast` / `shadows.modal` / `shadows.popover` | Toast, modal, popover only. |
| Galaxy canvas | Dark (`oklch(14% 0.02 250)`) with glow effects | Knowledge graph — the one exception to light-only surfaces. |

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.none}` | 0px | Full-bleed bands. |
| `{rounded.sm}` | 6px | Small surfaces, avatars, badge. |
| `{rounded.md}` | 10px | **Default for buttons and inputs.** |
| `{rounded.lg}` | 14px | **Card chrome** — slightly softer than before. |
| `{rounded.xl}` | 20px | Featured banners (continue-learning). |
| `{rounded.pill}` | 9999px | Pills / full round for badges. |
| `{rounded.full}` | 9999px | Circular avatar containers. |

## Components

### Buttons

**`button-primary`** — filled academic blue pill.
- Background `{colors.primary}`, text `{colors.primary-fg}`,1px solid border, padding `xs lg`, shape `md` (10px — not pill).
- Hover: `primary-hover`.

**`button-secondary`** — white surface with hairline border.
- Background `{colors.surface}`, text `{colors.fg}`,1px solid `{colors.border}`, shape `md`.
- Hover: `surface-alt` background, `border-strong` border.

**`button-ghost`** — transparent, no border.
- Text `{colors.fg-secondary}`, shape `md`.
- Hover: `surface-alt` background.

**`button-outline-sm`** — smaller outline pill for inline CTAs.
- Same as outline with tighter padding.

### Badges

**`badge-primary`** — blue tinted pill.
**`badge-success`** — green tinted pill for mastered/complete.
**`badge-warning`** — amber tinted pill for in-progress.
**`badge-ai`** — indigo tinted pill for AI-generated content.

### Cards

**`card-content`** — white surface, 1px hairline border, `rounded.lg` 14px, padding `xl` 24px. No shadow.
**`card-hover`** — same as card-content + on hover: `border-strong` + `shadow-md`.

### Progress Bar

**`progress-fill`** — `rounded.full` (pill), primary blue by default.
**`progress-fill-success`** — secondary teal-green, used for mastery.
**`progress-fill-ai`** — indigo/violet, used for AI activity.

### Avatar

- White surface with `primary-light` background, `primary` text. Circular (`rounded.full`).
- Sizes: `avatar-sm` 28px, default36px, `avatar-lg` 48px.

### AI Animations

**Typing dots** — three dots with staggered scale/opacity animation (1.4s ease-in-out, 0.2s stagger).
**AI shimmer** — gradient animation on `ai-light` → `primary-light` → `ai-light` background (2s ease-in-out infinite). Used during AI generation.
**Node pulse** — SVG `animate` element on knowledge graph nodes during "learning" state.

### Entry Animations

- `fadeUp` — translateY(16px) →0, opacity 0 → 1, 0.5s ease both.
- `fadeIn` — opacity 0 → 1, 0.4s ease both.
- `scaleIn` — scale(0.95) → 1, opacity 0 → 1, 0.4s ease both.
- `anim-delay-1` through `anim-delay-6` — 0.1–0.6s stagger for staggered entrance.

## Do's and Don'ts

### Do
- Use `oklch()` values from the color palette for all new color assignments.
- Use `{rounded.md}` (10px) on buttons and inputs as the default radius — not `rounded.sm`.
- Use `badge-ai` with `ai-light`/`ai` colors for any AI-generated content indicators.
- Use `primary-light` / `primary` for active nav states.
- Use `secondary` (teal-green) for progress and mastery indicators.
- Use `shadows.sm` / `shadows.md` only on hover for cards, never as default.
- Use `shadows.toast` / `shadows.modal` / `shadows.popover` for floating UI only.
- Pair SF Pro Display (headlines, weight 700) with SF Pro Text (body) and JetBrains Mono (mono labels).

### Don't
- Don't introduce dark mode for non-galaxy surfaces. Light canvas only.
- Don't use hex colors — use `oklch()` equivalents from the palette.
- Don't use `rounded.pill` (9999px) on buttons — use `rounded.md` (10px) as the default button shape.
- Don't use `shadow` on cards as default — hairline borders carry elevation.
- Don't use `accent-violet` or other xAI-era colors. The AI accent is `{colors.ai}` (indigo/violet).
- Don't use `rgba(255, 255, 255, ...)` borders on light surfaces — use `ink-alpha-15` or `border` instead.