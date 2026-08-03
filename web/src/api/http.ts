import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { useUserStore } from '@/stores/user'
import { ENDPOINTS } from './endpoints'
import type { RefreshResponse } from '@/types/response'

declare module 'axios' {
  export interface AxiosRequestConfig {
    _skipAuthRefresh?: boolean
    _retry?: boolean
  }
  export interface InternalAxiosRequestConfig {
    _skipAuthRefresh?: boolean
    _retry?: boolean
  }
}

const getBaseURL = (): string => {
  const envURL = import.meta.env.VITE_BASE_URL
  if (envURL) return `http://${envURL}`
  return ''
}

const http: AxiosInstance = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    try {
      const raw = localStorage.getItem('aiteach.user')
      if (raw) {
        const data = JSON.parse(raw) as { access?: string }
        if (data.access) {
          config.headers.set('Authorization', `Bearer ${data.access}`)
        }
      }
    } catch {}
    return config
  },
  (error) => Promise.reject(error),
)

let refreshing: Promise<string> | null = null

async function runRefresh(): Promise<string> {
  const userStore = useUserStore()
  const oldRefresh = userStore.refresh
  const oldAccess = userStore.access
  if (!oldRefresh) {
    throw new Error('No refresh token available')
  }

  const { data } = await http.post<RefreshResponse>(
    ENDPOINTS.REFRESH,
    { access: oldAccess, refresh: oldRefresh },
    { _skipAuthRefresh: true },
  )

  userStore.updateTokens({ access: data.access, refresh: data.refresh })
  return data.access
}

function forceLogout(): void {
  try {
    const userStore = useUserStore()
    userStore.logout()
  } catch {
    localStorage.removeItem('aiteach.user')
  }
  const current = window.location.pathname + window.location.search
  const onAuthPage = current.startsWith('/login') || current.startsWith('/register')
  const redirect = onAuthPage ? '' : `?redirect=${encodeURIComponent(current)}`
  window.location.href = `/login${redirect}`
}

http.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`[HTTP] ← ${response.status} ${response.config.url ?? ''}`, response.data)
    return response
  },
  async (error: AxiosError) => {
    console.error(`[HTTP] × ${error.config?.url ?? ''}`, {
      message: error.message,
      code: error.code,
      status: error.response?.status,
      responseData: error.response?.data,
    })

    const config = error.config as InternalAxiosRequestConfig | undefined
    const status = error.response?.status
    const url = config?.url ?? ''

    const isAuthLogin = url.includes('/auth/login')
    const isAuthRefresh = url.includes('/auth/refresh')
    if (
      status !== 401 ||
      !config ||
      config._retry ||
      config._skipAuthRefresh ||
      isAuthLogin ||
      isAuthRefresh
    ) {
      if (status === 401 && !isAuthLogin && !isAuthRefresh && !config?._skipAuthRefresh) {
        forceLogout()
      }
      return Promise.reject(error)
    }

    config._retry = true
    try {
      if (!refreshing) {
        refreshing = runRefresh().finally(() => {
          refreshing = null
        })
      }
      const newAccess = await refreshing
      config.headers.set('Authorization', `Bearer ${newAccess}`)
      return http.request(config)
    } catch (refreshErr) {
      forceLogout()
      return Promise.reject(refreshErr)
    }
  },
)

export default http
