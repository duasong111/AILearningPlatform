const MINIMAX_URL = 'https://api.minimaxi.com/v1/chat/completions'
const MINIMAX_MODEL = 'MiniMax-M3'

export interface MiniMaxMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export function useMinimaxChat() {
  async function* stream(
    messages: MiniMaxMessage[],
    signal?: AbortSignal,
  ): AsyncGenerator<string> {
    const apiKey = import.meta.env.VITE_MINIMAX_API_KEY
    if (!apiKey) {
      throw new Error('VITE_MINIMAX_API_KEY 未配置 —— 检查 web/.env')
    }

    // 30s 总超时 —— 防 minimax 流式卡住浏览器永远等.
    // (fetch 自身不支持 stream-timeout, 用 AbortController 在外层 race 一个 setTimeout)
    const timeoutCtrl = new AbortController()
    const timeoutMs = 60_000
    const timeoutId = setTimeout(() => {
      timeoutCtrl.abort(new Error('MiniMax stream timeout 60s'))
    }, timeoutMs)

    // signal: 任意上游 abort 触发都取消, 内部 timeout 也触发取消
    const composedSignal = (() => {
      if (!signal) return timeoutCtrl.signal
      // 合并: 任一信号 abort 都会触发
      const linked = AbortSignal.any
        ? AbortSignal.any([signal, timeoutCtrl.signal])
        : (() => {
            const ac = new AbortController()
            const onAbort = () => ac.abort()
            signal.addEventListener('abort', onAbort, { once: true })
            timeoutCtrl.signal.addEventListener('abort', onAbort, { once: true })
            return ac.signal
          })()
      return linked
    })()

    let resp: Response
    try {
      resp = await fetch(MINIMAX_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          model: MINIMAX_MODEL,
          messages,
          stream: true,
        }),
        signal: composedSignal,
      })
    } catch (e) {
      clearTimeout(timeoutId)
      const err = e as Error
      // 把 opaque "network error" 拆出原因
      let reason = err.message || String(e)
      if (err.name === 'AbortError') reason = '请求被取消 (用户切书 / 60s 超时)'
      if (/network\s*error/i.test(reason)) reason = '跨域/CORS 失败或网络中断 (浏览器 opaque)'
      if (/timeout/i.test(err.name + reason)) reason = '60s 流式超时'
      // dev 模式 console 显式打出来方便排错
      console.error('[minimax] fetch failed:', { name: err.name, msg: err.message, reason })
      throw new Error(reason)
    }
    clearTimeout(timeoutId)

    if (!resp.ok) {
      const errText = await resp.text().catch(() => '')
      const err = new Error(`MiniMax API ${resp.status}: ${errText.slice(0, 200)}`)
      console.error('[minimax] non-OK response:', err.message)
      throw err
    }

    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    // 过滤 <think>...</think> 思考块 + 同 tag 多行. 让用户看不到"思考过程"那种"反应慢"的观感.
    // 思路: 累计当前累计的可见内容, 检查它是否还在 <<think>> 内.
    let visible = ''        // 累计的 (含思考块) 完整内容
    let _lastVisible = ''   // 上一轮已 yield 的"过滤后"累计内容, 用于 diff 出本轮新正文

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const data = trimmed.slice(5).trim()
        if (data === '[DONE]') return
        try {
          const parsed = JSON.parse(data) as {
            choices?: { delta?: { content?: string } }[]
          }
          const chunk = parsed.choices?.[0]?.delta?.content
          if (!chunk) continue
          // 累加到 visible, 切掉 (含) <think>...</think>
          visible += chunk
          // 匹配开标签 + (0+ 任意非贪婪) + 闭标签, 一次 strip 掉所有
          const stripped = visible.replace(/<think>[\s\S]*?(<\/think>|<\/reasoning>|$)/, '').replace(/<think>/g, '')
          // 如果去除思考后比上一段 visible 更长 -> 有新正文 yield
          if (stripped.length > _lastVisible.length) {
            const delta = stripped.slice(_lastVisible.length)
            _lastVisible = stripped
            if (delta) yield delta
          } else {
            _lastVisible = stripped
          }
        } catch {
          // 忽略格式异常的 SSE 行
        }
      }
    }
  }

  return { stream }
}
