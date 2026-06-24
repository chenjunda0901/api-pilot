// ============================================================
// 用户 & 认证类型
// ============================================================

export interface User {
  id: number
  username: string
  nickname: string
  email: string
  role: "admin" | "member" | "viewer" | "editor" | "owner"
  created_at?: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
}
