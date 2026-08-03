// ============================================================
// Markdown + KaTeX + highlight.js 渲染器
//
//   - 单例 md 实例 (跨组件共用; 配置一次, 千万次复用)
//   - 安全: html:false, AI 内容不允许原生 HTML
//   - texmath 插件接入 KaTeX, 支持 $inline$ / $$display$$
//   - hljs 给 fenced code 上色
//   - 流式安全: 不完整的 markdown / 公式不崩, 退化成原文
//
//   markdown-it-texmath 没有 first-party @types, 在 src/types/shims.d.ts 里声明.
// ============================================================

import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import texmath from 'markdown-it-texmath'
import katex from 'katex'

let _md: MarkdownIt | null = null

function getMd(): MarkdownIt {
  if (_md) return _md
  const md = new MarkdownIt({
    html: false,                    // ❗AI 内容不可信, 禁用原生 HTML
    linkify: true,                  // 裸 URL → <a>
    breaks: true,                   // \n → <br>, 适合 chat 短句换行
    typographer: false,             // 不动引号 / 标点, 中文场景下省事
    highlight: (str: string, lang: string): string => {
      // mindmap 代码块 → 输出占位 div，由 MarkdownContent 后处理挂载思维导图
      if (lang === 'mindmap') {
        try {
          JSON.parse(str) // 验证是合法 JSON
          const encoded = btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (_, p1) => String.fromCharCode(parseInt(p1, 16))))
          return `<div class="x-md-mindmap-placeholder" data-mindmap="${encoded}"></div>`
        } catch {
          // JSON 解析失败，当普通代码块处理
        }
      }
      // fenced code block: ```lang ... ```
      if (lang && hljs.getLanguage(lang)) {
        try {
          const html = hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
          return `<pre class="x-md-pre hljs"><code class="hljs language-${lang}">${html}</code></pre>`
        } catch {
          // fall through
        }
      }
      // 没指定 lang / lang 不认 → 退化成纯 escape (md 自带 escape)
      const escaped = md.utils.escapeHtml(str)
      return `<pre class="x-md-pre hljs"><code class="hljs">${escaped}</code></pre>`
    },
  })

  // texmath 接 KaTeX —— 同时支持 $..$/$$..$$ 和 \(..\)/\[..\]
  md.use(texmath, {
    engine: katex,
    delimiters: ['dollars', 'brackets'],
    katexOptions: {
      throwOnError: false,           // ❗流式 / 残缺公式不抛, fallback 原文
      output: 'html',                // 不要 mathml, html 更稳
    },
  })

  _md = md
  return md
}

/** 把一段 markdown 文本渲染成 HTML 字符串. 安全, 可直接 v-html. */
export function renderMarkdown(text: string): string {
  if (!text) return ''
  try {
    // 去掉<think>...</think>思考标签
    const cleaned = text.replace(/<think>[\s\S]*?<\/think>/g, '').trim()
    return getMd().render(cleaned)
  } catch (err) {
    // 任何 parse 异常 → 退化成 escape 文本, 不让 UI 崩
    // eslint-disable-next-line no-console
    console.warn('[markdown] render failed:', err)
    return getMd().utils.escapeHtml(text)
  }
}
