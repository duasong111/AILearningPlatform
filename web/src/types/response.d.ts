// ============================================================
// User —— 后端 /api/auth/login/ 响应里的 user 字段
// ============================================================
export interface User {
  id: number
  username: string
  email: string
  avatar: string | null
  real_name: string | null
  gender: 'M' | 'F' | null
  age: number | null
  occupation: string | null
  city: string | null
  bio: string | null
  learning_goal: string | null
  interest_tags: string[]
}

// ============================================================
// 登录返回响应 — 2026-06 对齐后端, 标准 SimpleJWT 格式
//   不再包裹 {code, message}, 成功即 200, 失败由 axios 抛错
// ============================================================
export interface LoginResponse {
  access: string   // JWT access token (短期, 15min)
  refresh: string  // JWT refresh token (长期, 7d)
  user: User
}

// ============================================================
// 注册返回响应 —— 对齐 backend UserRegisterView (snake_case)
//   成功: { message: '注册成功', user_id: <int> }
//   失败 (400): serializer.errors, 例 {"email": ["..."], "password_confirm": ["..."]}
// ============================================================
export interface RegisterResponse {
  message: string
  user_id?: number
}

// ============================================================
// Refresh token —— POST /api/auth/refresh/
//   请求体: { access, refresh }   (后端期望两个一起带, 不是 SimpleJWT 默认的 refresh-only)
//   响应:   { access, refresh }   (rotation 打开, 旧 refresh 会作废)
// ============================================================
export interface RefreshRequest {
  access: string
  refresh: string
}
export interface RefreshResponse {
  access: string
  refresh: string
}

// ============================================================
// Subject —— /api/subjects/
//   - GET 返回预定义 7 门 (NOTE: 后端 list 方法 override 了 queryset, 返回的不是用户已选)
//   - POST { name: <code> } 创建用户学科, 返回 MySubject
//   - DELETE /api/subjects/<id>/ 删除
// ============================================================
export interface SubjectChoice {
  code: string                  // 与 backend SUBJECT_CHOICES key 对应
  name: string                  // 显示名 (后端返的是 name 字段, 不是 display_name)
}

// 后端 SubjectSerializer 输出形状
export interface MySubject {
  id: number
  name: string                  // subject code, e.g. "data_structure"
  display_name: string          // 显示名 (由 SerializerMethodField 给出)
  created_at: string
  updated_at: string
}

// ============================================================
// UserProfile —— /api/profile/?subject=<code>  (per-subject)
//   后端 UserProfileSerializer 输出
// ============================================================
export interface UserProfile {
  id: number
  subject: MySubject
  course: string | null
  knowledge_base: number
  cognitive_style: number
  learning_goal_score: number
  available_time: number
  common_mistakes: string[]
  interest_direction: string[]
  created_at: string
  updated_at: string
  /** 后端 UserProfileSerializer.get_is_complete() 输出：
   *  frontend onboarding 流程用此字段判断用户是否完成画像构建 */
  is_complete: boolean
}
