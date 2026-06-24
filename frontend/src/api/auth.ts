import request from './request'

export interface UserInfo {
  id: number
  username: string
  nickname: string
  email: string
  role: string
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: UserInfo
}

export interface RegisterRequest {
  username: string
  password: string
  nickname?: string
  email?: string
}

export interface RegisterResponse {
  access_token: string
  refresh_token: string
  user: UserInfo
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
}

export interface ProfileUpdateRequest {
  nickname?: string
  email?: string
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

// ── 用户注册 ──
export function register(data: RegisterRequest, extraConfig?: { signal?: AbortSignal }) {
  return request.post<RegisterResponse>('/auth/register', data, extraConfig)
}

// ── 用户登录 ──
export function login(data: LoginRequest, extraConfig?: { signal?: AbortSignal }) {
  return request.post<LoginResponse>('/auth/login', data, extraConfig)
}

// ── 刷新 Token ──
export function refreshToken(refresh_token?: string) {
  return request.post<RefreshResponse>('/auth/refresh', refresh_token ? { refresh_token } : {})
}

// ── 退出登录 ──
export function logout() {
  return request.post('/auth/logout')
}

// ── 获取当前用户信息 ──
export function getMe() {
  return request.get<UserInfo>('/auth/me')
}

// ── 更新个人信息 ──
export function updateMe(data: ProfileUpdateRequest) {
  return request.put<UserInfo>('/auth/me', data)
}

// ── 修改密码 ──
export function changePassword(data: PasswordChangeRequest) {
  return request.put('/auth/password', data)
}

