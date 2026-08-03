import { onBeforeUnmount, ref } from 'vue'
import { useUserStore } from '@/stores/user'
import type { WSInboundEvent, WSOutboundMessage } from '@/types/chat'

/**
 * 会话 WS 包装 —— 2026-06 对齐新后端
 *   URL: ws(s)://<host>/ws/conversations/<id>/?token=<jwt>
 *
 *   - 认证: backend JWTAuthMiddleware 读 ?token=, 匿名时 close(4401)
 *   - 续期: connect() 内部先 await userStore.ensureFreshAccess(),
 *           保证用 fresh token 握手 (旧 token 接近过期会被先 refresh 一次)
 *   - 重连: 不自动. UI 决定何时再 connect (一般用 "Reconnect" 按钮)
 *   - 卸载: onBeforeUnmount 自动 close, 防止泄漏
 *
 *   用法:
 *     const ws = useConvWS({ onEvent, onClose })
 *     await ws.connect(conversationId)
 *     ws.send({ type: 'message', content: '...' })
 *     ws.close()
 */

export type WSStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

interface Options {
  onEvent: (ev: WSInboundEvent) => void
  onClose?: (reason: { code: number; reason: string; clean: boolean }) => void
}

function buildWSURL(token: string, conversationId: number, _agentType?: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const params = new URLSearchParams({ token })
  // 后端统一路由: /ws/conversations/<id>/  (ConversationStreamConsumer 按 conversation.agent 分发)
  const url = `${proto}//${host}/ws/conversations/${conversationId}/?${params.toString()}`
  console.log('[ws] Building URL:', url.replace(/token=[^&]+/, 'token=***'))
  return url
}

export function useConvWS(opts: Options) {
  const userStore = useUserStore()
  const status = ref<WSStatus>('idle')
  const currentConvId = ref<number | null>(null)
  let socket: WebSocket | null = null
  // 连接过程中的 Promise (open 时 resolve, 早 close 时 reject).
  //   并发 connect(sameConvId) 会复用这个 Promise, 不重复握手.
  let pendingOpen: Promise<void> | null = null

  async function connect(conversationId: number, agentType?: string): Promise<void> {
    // 同一 conv 已开 → no-op (幂等)
    if (
      socket &&
      currentConvId.value === conversationId &&
      socket.readyState === WebSocket.OPEN
    ) {
      return
    }
    // 同一 conv 正在连接 → 复用那个 Promise (避免并发 connect 抢同一个 socket)
    if (
      socket &&
      currentConvId.value === conversationId &&
      socket.readyState === WebSocket.CONNECTING &&
      pendingOpen
    ) {
      return pendingOpen
    }
    // 切了会话 → 先关掉旧的，并等待关闭完成
    if (socket && currentConvId.value !== conversationId) {
      const oldSocket = socket
      try { oldSocket.close(1000, 'switch-conv') } catch { /* noop */ }
      // 等待 socket 真正关闭
      await new Promise<void>((resolve) => {
        const checkClosed = () => {
          if (oldSocket.readyState === WebSocket.CLOSED) {
            resolve()
          } else {
            setTimeout(checkClosed, 50)
          }
        }
        checkClosed()
      })
      socket = null
      pendingOpen = null
    }

    status.value = 'connecting'
    currentConvId.value = conversationId

    // 关键: 握手前确保 token 新鲜 (剩余 ≥60s).
    //   过期 token 会导致 backend close(4401), 用户看到"还没开始就断了".
    let token: string
    try {
      token = await userStore.ensureFreshAccess()
    } catch (err) {
      status.value = 'error'
      opts.onClose?.({
        code: 4401,
        reason: err instanceof Error ? err.message : 'token refresh failed',
        clean: false,
      })
      throw err
    }

    // 包成 Promise: 这个 await 真正等到 socket 'open' 才返回.
    //   旧版只 await ensureFreshAccess, new WebSocket 后立刻返回, 调用方拿到时
    //   socket 还在 CONNECTING, 紧接着 send 会被丢. 现在补齐.
    pendingOpen = new Promise<void>((resolve, reject) => {
      let sock: WebSocket
      try {
        sock = new WebSocket(buildWSURL(token, conversationId, agentType))
      } catch (err) {
        status.value = 'error'
        const reason = err instanceof Error ? err.message : 'WS init failed'
        opts.onClose?.({ code: 0, reason, clean: false })
        reject(new Error(reason))
        return
      }
      socket = sock
      let opened = false

      sock.addEventListener('open', () => {
        opened = true
        status.value = 'open'
        console.log('[ws] Connected to conversation:', conversationId)
        resolve()
      })

      sock.addEventListener('message', (e) => {
        let data: unknown
        try {
          data = JSON.parse(typeof e.data === 'string' ? e.data : '')
        } catch {
          console.warn('[ws] non-JSON message ignored:', e.data)
          return
        }
        if (!data || typeof data !== 'object' || !('type' in data)) {
          console.warn('[ws] event missing type:', data)
          return
        }
        console.log('[ws] Received event:', (data as any).type, data)
        opts.onEvent(data as WSInboundEvent)
      })

      sock.addEventListener('error', (err) => {
        console.error('[ws] WebSocket error:', err)
        status.value = 'error'
      })

      sock.addEventListener('close', (e) => {
        console.log('[ws] Closed:', e.code, e.reason, 'wasClean:', e.wasClean)
        status.value = 'closed'
        if (socket === sock) socket = null
        if (pendingOpen) pendingOpen = null
        opts.onClose?.({
          code: e.code,
          reason: e.reason || (e.code === 4401 ? 'auth' : 'socket closed'),
          clean: e.wasClean,
        })
        if (!opened) {
          reject(new Error(`socket closed before open (code=${e.code})`))
        }
      })
    })
    return pendingOpen
  }

  function send(payload: WSOutboundMessage): boolean {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('[ws] send() failed: socket not open, readyState:', socket?.readyState)
      return false
    }
    const jsonStr = JSON.stringify(payload)
    console.log('[ws] Sending:', jsonStr)
    socket.send(jsonStr)
    return true
  }

  function close(): void {
    if (
      socket &&
      (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
    ) {
      try {
        socket.close(1000, 'client-close')
      } catch { /* noop */ }
    }
    socket = null
    pendingOpen = null
    currentConvId.value = null
    status.value = 'idle'
  }

  onBeforeUnmount(close)

  return { status, currentConvId, connect, send, close }
}
