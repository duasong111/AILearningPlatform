# Video Player Integration

## What the video player does

`/video` is a single-page auto-playing slideshow player. It generates a sequence of `slide` scenes from a topic description, renders each scene as a fullscreen slide, and narrates it with TTS. Slides auto-advance when their narration ends. There is no quiz, no interactive widget, no prev/next, no fullscreen toggle — just continuous playback.

Key behaviors:

- Generation starts immediately on page load (no submit button).
- The first slide plays as soon as it is generated; subsequent slides play while later slides are still being generated.
- Playback speeds: `1x` and `2x` only.
- Scenes are persisted on the server under the `uuid` (TTS audio excluded by design — text is kept so audio can be regenerated on a new device).
- Same `uuid` on a second visit (same or different device) reuses server-cached scenes instantly, no re-generation.

## URL

```text
GET {url}/video?desc={topic}&uuid={uuid}
```

Query parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `desc` | yes | Topic description, URL-encoded. Drives outline generation when no external outline is supplied. |
| `uuid` | yes | Stable identifier `^[a-zA-Z0-9_-]{1,64}$`. Used as the persistence key on the server. Reuse the same `uuid` to resume or cross-load. |

Browser-loadable example:

```text
http://localhost:3000/video?desc=%E5%B8%AE%E6%88%91%E7%94%9F%E6%88%90%E4%B8%80%E4%B8%AA%E4%BB%8B%E7%BB%8D%E9%80%92%E5%BD%92%E7%9A%84%E8%A7%86%E9%A2%91&uuid=my-video-001
```

For iframe embedding from a different origin, set `ALLOWED_FRAME_ANCESTORS` in the OpenMAIC server environment. See [startup-modes.md](startup-modes.md).

> **Hosted mode**: If using hosted OpenMAIC (open.maic.chat), include `Authorization: Bearer <access-code>` on every API request below.

## Two integration modes

### Mode A — Let OpenMAIC generate everything

You only need to open the URL. The page itself will:

1. POST `/api/generate/scene-outlines-stream` to generate the slide outline via LLM.
2. For each outline, POST `/api/generate/scene-content` to generate slide content.
3. For each content, POST `/api/generate/scene-actions` to generate narration actions.
4. For each speech action, POST `/api/generate/tts` to generate audio.
5. After each scene is fully generated, PUT `/api/video/{uuid}` to persist it.

You do not call any of these endpoints yourself — the page does it.

### Mode B — Supply the outline yourself

If you already have a curated outline (from a teacher, a CMS, an external LLM, etc.), you can skip step 1. Steps 2–5 still run, so you only avoid the LLM outline-generation round-trip.

The flow:

```text
1. POST /api/video/{uuid}/init    ← upload your outlines
2. Open {url}/video?uuid={uuid}   ← page reads outlines and continues
```

The page will detect the preloaded outlines, skip the outline LLM call, and proceed directly to content + actions + TTS generation.

## External outline API (Mode B)

### `POST /api/video/{uuid}/init`

Save an external outline to the server so the `/video` page picks it up.

Path parameter:

| Name | Type | Description |
|------|------|-------------|
| `uuid` | string | Same uuid you will use in the `/video` URL. Must match `^[a-zA-Z0-9_-]{1,64}$`. |

Request body:

```json
{
  "desc": "链表的定义与核心概念",
  "languageDirective": "用中文授课，保留 Head/Tail/Node 等英文术语",
  "outlines": [
    {
      "id": "scene_1",
      "type": "slide",
      "title": "链表的定义与核心概念",
      "description": "介绍链表的基本结构和与数组的区别",
      "keyPoints": [
        "由一系列节点组成的线性数据结构",
        "每个节点包含数据域和指针域",
        "头节点、尾节点、NULL 指针的作用"
      ],
      "order": 1
    },
    {
      "id": "scene_2",
      "type": "slide",
      "title": "单链表 vs 双向链表",
      "description": "对比单向和双向链表的结构差异与适用场景",
      "keyPoints": [
        "单向链表只能向后遍历",
        "双向链表可前后遍历但占用更多内存",
        "插入/删除操作复杂度"
      ],
      "order": 2
    }
  ]
}
```

Field reference:

| Field | Required | Description |
|-------|----------|-------------|
| `desc` | yes | Short topic title. Stored as the video description. Shown in the player UI. |
| `languageDirective` | recommended | 2–5 sentence instruction telling the downstream LLM which language to teach in and how to handle terminology. This string is forwarded verbatim to `slide-content` and `slide-actions` prompts. |
| `outlines` | yes | Array of scene outlines. See schema below. |
| `outlines[].id` | recommended | Stable id for the scene. If omitted, the server assigns one. |
| `outlines[].type` | required | Must be `"slide"`. Anything else is normalized to `slide` by the page. |
| `outlines[].title` | required | Scene title. Used as the slide title and TTS topic. |
| `outlines[].description` | required | 1–2 sentence teaching purpose. Forwarded to the `slide-content` prompt as the "purpose" of this scene. |
| `outlines[].keyPoints` | required | 3–5 bullets. Each bullet becomes either a content element on the slide or a key point in narration. Avoid filler; each bullet should carry distinct information. |
| `outlines[].order` | optional | Playback order. If omitted, array index is used. |

Response:

```json
{
  "success": true,
  "data": {
    "uuid": "my-video-001",
    "outlineCount": 2
  }
}
```

Errors:

| Status | Meaning |
|--------|---------|
| `400 INVALID_REQUEST` | Bad uuid or empty body. |
| `400 MISSING_REQUIRED_FIELD` | `desc` or `outlines` missing. |
| `400 NO_VALID_OUTLINES` | `outlines` is empty or none are `type: "slide"`. |

### `GET /api/video/{uuid}/outlines`

Returns the preloaded outlines (used internally by the `/video` page; usually you do not need to call this directly).

Response:

```json
{
  "success": true,
  "data": {
    "uuid": "my-video-001",
    "desc": "链表的定义与核心概念",
    "languageDirective": "用中文授课...",
    "outlines": [ /* same shape as input */ ]
  }
}
```

If no outlines have been preloaded, returns `404`.

## Persistence APIs (used by both modes)

The `/video` page calls these automatically — you usually do not.

### `GET /api/video/{uuid}`

Read the persisted scenes for a uuid.

Response:

```json
{
  "success": true,
  "data": {
    "video": {
      "uuid": "my-video-001",
      "desc": "...",
      "scenes": [
        {
          "id": "scene_1",
          "stageId": "video-player",
          "type": "slide",
          "title": "链表的定义与核心概念",
          "order": 1,
          "content": { /* full slide content (text elements, charts, layouts) */ },
          "actions": [
            { "type": "speech", "text": "..." },
            { "type": "spotlight", "selector": "..." }
          ],
          "whiteboard": [],
          "createdAt": 1718800000000,
          "updatedAt": 1718800000000
        }
      ],
      "createdAt": "2026-...",
      "updatedAt": "2026-..."
    }
  }
}
```

Notes:

- `scenes[].actions` never contains TTS-only fields (`audioId`, `audioUrl`). They are stripped on save; audio is regenerated client-side on demand.
- `404` if no scenes have been generated yet.

### `PUT /api/video/{uuid}`

Save scenes. The page calls this after each scene is fully generated (content + actions).

Request body:

```json
{
  "desc": "链表的定义与核心概念",
  "scenes": [
    {
      "id": "scene_1",
      "stageId": "video-player",
      "type": "slide",
      "title": "...",
      "order": 1,
      "content": { /* slide content */ },
      "actions": [ /* actions, TTS fields stripped */ ],
      "whiteboard": []
    }
  ]
}
```

### `GET /api/video-media/{uuid}/{path...}`

Read a persisted media file (slide background image, etc.).

### `POST /api/video-media/{uuid}/{path...}`

Upload a media file. Request body is base64 JSON:

```json
{
  "data": "<base64>",
  "mimeType": "image/png"
}
```

## Server-side disk layout

When OpenMAIC persists video data, files are written under `data/videos/`:

```text
data/videos/
  {uuid}.json              ← persisted scenes (PUT /api/video/{uuid})
  {uuid}/
    media/
      <hash>.<ext>        ← uploaded images / videos
    outlines.json         ← preloaded outlines (POST /api/video/{uuid}/init)
```

The `outlines.json` is only present when Mode B was used to seed the video.

## Prompt for generating outlines externally

Use the following prompt to produce outlines compatible with the `/video` page. You can run this in your own LLM (Anthropic, OpenAI, local model, etc.) before calling `POST /api/video/{uuid}/init`.

### System prompt

```text
You are designing a slide-deck outline for a single-screen auto-playing video player.

## Output

Return exactly one JSON object (no markdown fences, no prose):

{
  "languageDirective": "...",
  "outlines": [ /* scene outlines */ ]
}

## Scene contract

Each scene MUST be a normal slide — no quiz, no interactive widget, no simulation,
no exercise, no project-based learning. Every scene will be rendered as a static
slide and narrated with TTS.

Required fields per outline:

  id        — stable string id, e.g. "scene_1"
  type      — always "slide"
  title     — short scene title (≤ 20 characters in the teaching language)
  description — 1–2 sentences: what this slide teaches and why it matters
  keyPoints — 3–5 bullets, each carrying distinct teachable content
  order     — integer, 1-based, increasing

## Density rules

- 8–14 scenes total for a 15–20 minute video. Prefer 10–12.
- Each scene should be 1–3 minutes of narration.
- Order scenes so the narrative flows: concept → structure → comparison → example → summary.
- Each keyPoint should be specific enough to be its own slide section or TTS sentence.
- Do not duplicate content across scenes.
- The first scene should set up the topic and why it matters; the last scene should summarize.

## languageDirective

Write 2–5 sentences covering:
  - the teaching language
  - how to handle English/foreign terms (keep as-is, translate in parentheses, etc.)
  - the audience level (beginner / intermediate / advanced)
  - terminology style (formal / casual / bilingual)

Example:
  "用中文授课，保留 Head/Tail/Node/Next 等英文术语。
   面向有 C 语言基础的本科二年级学生。
   难度中等，类比数组帮助理解。
   关键术语首次出现时附英文。"

## Strict prohibitions

- DO NOT include quiz, test, interactive, simulation, demo, practice, exercise, PBL scenes.
- DO NOT include widgetType, widgetOutline, quizConfig, interactiveConfig.
- DO NOT return a bare array — always wrap in { languageDirective, outlines }.
- DO NOT wrap output in markdown code fences.
```

### User prompt template

```text
Design a slide-deck outline for an auto-playing teaching video on the topic below.

## Topic

{user's topic description}

## Audience (optional)

{audience level, e.g. "大学本科二年级", "零基础成人学员"}

## Target length (optional)

{e.g. "约 15 分钟", "10–12 张幻灯片"}

## Language (optional)

{e.g. "中文授课，保留英文术语"}

Produce exactly {N} scenes (omit if you want 8–14 default).
Each scene becomes one fullscreen slide with TTS narration.
```

### Worked example

Input topic: "链表入门"  
Audience: "大学本科一年级，已学过 C 语言数组"  
Target length: "约 12 分钟"

Expected output (abbreviated):

```json
{
  "languageDirective": "用中文授课，保留 Head/Tail/Node/Next/Linked List 等英文术语。面向已学过 C 语言数组的本科一年级学生。难度入门级，多用数组类比。术语首次出现时附英文。",
  "outlines": [
    {
      "id": "scene_1",
      "type": "slide",
      "title": "什么是链表",
      "description": "用一句话定义链表，引出与数组的核心区别——链表不要求连续内存。",
      "keyPoints": [
        "链表是由节点组成的线性数据结构",
        "每个节点包含数据域与指针域",
        "节点在内存中可散落分布，不像数组连续"
      ],
      "order": 1
    },
    {
      "id": "scene_2",
      "type": "slide",
      "title": "单链表的结构",
      "description": "展示 Head→A→B→C→NULL 的结构图，说明单向指针的含义。",
      "keyPoints": [
        "Head 指向第一个节点",
        "每个节点的 Next 指向下一个节点",
        "最后一个节点的 Next 为 NULL"
      ],
      "order": 2
    }
  ]
}
```

## End-to-end example (Mode B)

```bash
# 1. Preload outlines
curl -X POST http://localhost:3000/api/video/my-video-001/init \
  -H "Content-Type: application/json" \
  -d '{
    "desc": "链表入门",
    "languageDirective": "用中文授课，保留英文术语，面向本科一年级。",
    "outlines": [ /* see schema above */ ]
  }'

# 2. Open the player (browser / iframe)
open "http://localhost:3000/video?uuid=my-video-001"
# or
# <iframe src="http://localhost:3000/video?uuid=my-video-001" />
```

The page will:

- Detect the preloaded outlines via `GET /api/video/{uuid}/outlines`.
- Skip `/api/generate/scene-outlines-stream`.
- Loop through each outline calling `scene-content` + `scene-actions` + `tts`.
- Persist progress with `PUT /api/video/{uuid}` after each scene.

If a visitor opens the same `uuid` on another device (or after a refresh), `GET /api/video/{uuid}` returns the persisted scenes instantly and no re-generation happens.

## TTS behavior

- Speech actions are emitted by `scene-actions`; their `text` is what gets spoken.
- Audio is generated per speech action by `POST /api/generate/tts`.
- Audio is **never** persisted to the server. Each visit regenerates it from the persisted text.
- The page falls back gracefully when TTS fails — the slide still displays, just silently.
- Chrome may block the very first playback attempt until the user interacts with the page; this is logged but not treated as an error.

## Speed control

The player UI exposes `1x` and `2x` playback rates. There is no other control — no prev/next/page-dot/fullscreen toggle. This is by product design for the auto-play experience.

## Error handling

| Symptom | Likely cause |
|---------|--------------|
| `No valid outlines provided` | The `init` request contained no `type: "slide"` outlines. |
| `Failed to persist video` | Disk write failed — check `data/videos/` permissions. |
| Silent playback on first load | Chrome autoplay policy; the user needs to click or scroll first. |
| Player stuck on "正在自动生成视频大纲" | `/api/generate/scene-outlines-stream` failed; check server logs. |
| `Video not found` on reload | The uuid has never been saved; nothing to restore. |

## Source map

| Concern | File |
|---------|------|
| Player page | `app/video/page.tsx` |
| Scene content prompt | `lib/prompts/templates/slide-content/system.md` |
| Scene actions prompt | `lib/prompts/templates/slide-actions/system.md` |
| Outline prompt (default) | `lib/prompts/templates/requirements-to-outlines/system.md` |
| Outline type | `lib/types/generation.ts` (`SceneOutline`) |
| Video storage | `lib/server/video-storage.ts` |
| Persistence API | `app/api/video/[uuid]/route.ts` |
| Media API | `app/api/video-media/[uuid]/[...path]/route.ts` |
| Playback engine | `lib/playback/engine.ts` |
| Audio player | `lib/utils/audio-player.ts` |