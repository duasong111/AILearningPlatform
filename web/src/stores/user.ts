import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/response'

/**
 * 用户身份 store —— 跨页面共享的认证态。
 *
 * - 使用 setup 语法（与项目 `<script setup>` 风格一致）
 * - 通过 pinia-plugin-persistedstate 持久化到 localStorage
 * - 是路由守卫判断登录态的唯一来源
 *
 * 字段对齐后端 /api/auth/login/ 响应 (2026-06):
 *   - access  : 短期 JWT (15 min), 每次请求塞 Authorization 头
 *   - refresh : 长期 JWT (7 d),   用于刷新 access
 *   - user    : 后端返回的完整用户档案
 */
export const useUserStore = defineStore(
  'user',
  () => {
    // ─── state ────────────────────────────────────────────
    const access = ref<string>('')
    const refresh = ref<string>('')
    const user = ref<User | null>(null)

    // ─── getters ──────────────────────────────────────────
    const isAuthenticated = computed<boolean>(() => access.value.length > 0)
    const displayName = computed<string>(
      () => user.value?.username ?? user.value?.email ?? 'Guest',
    )

    // ─── actions ──────────────────────────────────────────
    function setAuth(payload: {
      access: string
      refresh: string
      user: User
    }): void {
      access.value = payload.access
      refresh.value = payload.refresh
      user.value = payload.user
    }

    // 仅刷新 token 对, 不动 user —— 由 http 拦截器的 401 自愈逻辑调用
    function updateTokens(payload: { access: string; refresh: string }): void {
      access.value = payload.access
      refresh.value = payload.refresh
    }

    // ============================================================
    // 主动 token 续期 —— WS 连接前调
    //   WS 握手时把 access 放 URL query, 后端 JWTAuthMiddleware 校验.
    //   一旦握手通过, 连接期间 token 不再被复查 (即使过期 WS 也不会断).
    //   但握手时如果 access 已过期会 4401 拒连接.
    //
    //   策略: 解 JWT payload (不验签, 只读 exp), 余量 < 60s 时主动 refresh.
    //   refreshToken() 走 axios → http 拦截器, 返回新 pair 写回 store.
    //
    //   返回值: 当前有效的 access token (可能是续期后的). 失败抛错.
    // ============================================================
    async function ensureFreshAccess(): Promise<string> {
      if (!access.value) throw new Error('not authenticated')
      // 解 JWT payload — 三段, base64url 解第二段
      let exp = 0
      try {
        const parts = access.value.split('.')
        if (parts.length === 3) {
          // base64url → base64
          const b64 = parts[1]!.replace(/-/g, '+').replace(/_/g, '/')
          const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
          const payload = JSON.parse(atob(padded)) as { exp?: number }
          exp = payload.exp ?? 0
        }
      } catch {
        // 解析失败就当 token 不可信 → 强制 refresh
        exp = 0
      }
      const nowSec = Math.floor(Date.now() / 1000)
      const remaining = exp - nowSec
      if (remaining > 60) return access.value           // 还有 ≥60s, 直接用

      if (!refresh.value) throw new Error('refresh token missing')
      // 懒 import 防止 user store ↔ api/user.ts 循环依赖
      const { refreshToken } = await import('@/api/user')
      const { data } = await refreshToken({
        access: access.value,
        refresh: refresh.value,
      })
      access.value = data.access
      refresh.value = data.refresh
      return data.access
    }

    function logout(): void {
      access.value = ''
      refresh.value = ''
      user.value = null
    }

    return {
      access,
      refresh,
      user,
      isAuthenticated,
      displayName,
      setAuth,
      updateTokens,
      ensureFreshAccess,
      logout,
    }
  },
  {
    persist: {
      key: 'aiteach.user',
      // 只持久化必要字段（默认是全部 state）
      pick: ['access', 'refresh', 'user'],
    },
  }
)
