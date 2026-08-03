import http from './http'
import { ENDPOINTS } from './endpoints'
import type { LoginForm, RegisterForm, RegisterRequest } from '../types'
import type {
  LoginResponse,
  RefreshRequest,
  RefreshResponse,
  RegisterResponse,
} from '@/types/response'

// 用户登录
//   字段: { email, password } → 响应: { access, refresh, user }
export function loginUser(data: LoginForm): Promise<{ data: LoginResponse }> {
  const payload = {
    email: data.email.trim(),
    password: data.password,
  }
  return http.post(ENDPOINTS.LOGIN, payload)
}

// 用户注册
//   - 把 UI 侧 camelCase 的 confirmPassword 映射成 wire 侧 snake_case 的 password_confirm
//   - 后端要求: email (唯一, 登录用) / username (展示名) / password (≥6) / password_confirm (==password)
export function registerUser(data: RegisterForm): Promise<{ data: RegisterResponse }> {
  const payload: RegisterRequest = {
    email: data.email.trim(),
    username: data.username.trim(),
    password: data.password,
    password_confirm: data.confirmPassword,
  }
  return http.post(ENDPOINTS.REGISTER, payload)
}

// 刷新 access / refresh —— 2026-06 对齐后端
//   - body 同时携带 access + refresh (非 SimpleJWT 默认)
//   - 标 `_skipAuthRefresh` 让 http 拦截器跳过 401-refresh 逻辑,
//     否则 refresh 自身的 401 会被重新走 refresh, 死循环
export function refreshToken(data: RefreshRequest): Promise<{ data: RefreshResponse }> {
  return http.post(ENDPOINTS.REFRESH, data, {
    _skipAuthRefresh: true,
  } as unknown as Parameters<typeof http.post>[2])
}

// 默认导出
export default {
  loginUser,
  registerUser,
  refreshToken,
}
