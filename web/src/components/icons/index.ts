/**
 * Icon family — AI-generated duotone SVGs from Recraft.
 *
 * Conventions:
 *   - 每个 SFC 接受 `size?: number | string` (默认 18)
 *   - 软色层 (e.g. #DBE7FF) 在 SVG 内 hardcode
 *   - 主色层用 `fill="currentColor"`, 由父级 CSS `color:` 控制
 *   - 所有 SVG `viewBox="0 0 24 24"`, stroke 1.5–2px
 *
 * Usage:
 *   <script setup lang="ts">
 *   import { IconHome, IconGalaxy } from '@/components/icons'
 *   </script>
 *   <template>
 *     <span style="color: var(--x-primary)"><IconHome :size="18" /></span>
 *   </template>
 */

// ── Brand ────────────────────────────────────────────────
export { default as BrandMark } from './brand/BrandMark.vue'
export { default as BrandFavicon } from './brand/BrandFavicon.vue'

// ── Top navigation (11) ──────────────────────────────────
export { default as IconHome } from './nav/IconHome.vue'
export { default as IconGalaxy } from './nav/IconGalaxy.vue'
export { default as IconDialog } from './nav/IconDialog.vue'
export { default as IconPlan } from './nav/IconPlan.vue'
export { default as IconBook } from './nav/IconBook.vue'
export { default as IconVideo } from './nav/IconVideo.vue'
export { default as IconExercise } from './nav/IconExercise.vue'
export { default as IconExam } from './nav/IconExam.vue'
export { default as IconRecords } from './nav/IconRecords.vue'
export { default as IconProfile } from './nav/IconProfile.vue'
export { default as IconSettings } from './nav/IconSettings.vue'

// ── Subject / domain icons (7) ───────────────────────────
export { default as IconMath } from './subject/IconMath.vue'
export { default as IconPhysics } from './subject/IconPhysics.vue'
export { default as IconChemistry } from './subject/IconChemistry.vue'
export { default as IconBiology } from './subject/IconBiology.vue'
export { default as IconGeometry } from './subject/IconGeometry.vue'
export { default as IconElectricity } from './subject/IconElectricity.vue'
export { default as IconCell } from './subject/IconCell.vue'

// ── Status / feedback (10) ───────────────────────────────
export { default as IconCheck } from './status/IconCheck.vue'
export { default as IconCross } from './status/IconCross.vue'
export { default as IconWarn } from './status/IconWarn.vue'
export { default as IconInfo } from './status/IconInfo.vue'
export { default as IconSparkle } from './status/IconSparkle.vue'
export { default as IconRetry } from './status/IconRetry.vue'
export { default as IconArrow } from './status/IconArrow.vue'
export { default as IconChevron } from './status/IconChevron.vue'
export { default as IconPlus } from './status/IconPlus.vue'
export { default as IconHourglass } from './status/IconHourglass.vue'

// ── UI / tool / context (16) ─────────────────────────────
export { default as IconGear } from './ui/IconGear.vue'
export { default as IconGuard } from './ui/IconGuard.vue'
export { default as IconNode } from './ui/IconNode.vue'
export { default as IconBlock } from './ui/IconBlock.vue'
export { default as IconPen } from './ui/IconPen.vue'
export { default as IconGrid } from './ui/IconGrid.vue'
export { default as IconQuote } from './ui/IconQuote.vue'
export { default as IconNotepad } from './ui/IconNotepad.vue'
export { default as IconEncyclopedia } from './ui/IconEncyclopedia.vue'
export { default as IconChat } from './ui/IconChat.vue'
export { default as IconBulb } from './ui/IconBulb.vue'
export { default as IconPin } from './ui/IconPin.vue'
export { default as IconSearch } from './ui/IconSearch.vue'
export { default as IconPause } from './ui/IconPause.vue'
export { default as IconTimer } from './ui/IconTimer.vue'
export { default as IconGradCap } from './ui/IconGradCap.vue'
