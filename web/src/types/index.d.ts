// 用户登录的表单（UI 侧, camelCase）
//   后端约定: 用 email 作为登录账号, 字段名也是 email
export interface LoginForm {
  email: string
  password: string
}

// 用户注册的表单（UI 侧, camelCase）
//   - email:    后端唯一, 实际登录账号
//   - username: 后端必填但无唯一约束, 仅展示名
//   - confirmPassword: 仅前端一致性校验, 不直接发给后端
export interface RegisterForm {
  email: string
  username: string
  password: string
  confirmPassword: string
}

// 用户注册的请求体（wire 侧, snake_case）
//   与后端 POST /api/auth/register/ 字段一一对应
//   由 api/user.ts 的 registerUser() 从 RegisterForm 映射而来
export interface RegisterRequest {
  email: string
  username: string
  password: string
  password_confirm: string
}
