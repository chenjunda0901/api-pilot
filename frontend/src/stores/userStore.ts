import { defineStore } from "pinia"
import { ref, computed } from "vue"
import request, { setMemoryToken, getMemoryToken, refreshToken } from "@/api/request"
import { logger } from "@/utils/logger"
import { register as apiRegister, login as apiLogin, logout as apiLogout, getMe } from "@/api/auth"
import { markAuthReady } from "@/router"
import type { User, LoginResponse } from "@/types"

import { STORAGE_KEYS } from "@/constants/events"

function safeGet<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function safeSetJSON(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch { /* localStorage 不可用 */ }
}

function safeRemove(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch { /* localStorage 不可用 */ }
}

export const useUserStore = defineStore("user", () => {
  const savedUser = safeGet<User | null>(STORAGE_KEYS.USER, null)
  const user = ref<User | null>(savedUser)

  /** access_token 仅在内存中保存，不写入 localStorage */
  const accessToken = ref<string | null>(null)

  // 刷新锁已移至 request.ts 的 refreshingPromise 统一管理

  /**
   * UI 层登录状态：仅检查 user 对象（用于显示头像/昵称等）。
   * 注意：此值可能与 HTTP 层 token 状态不同步（刷新后 user 从 localStorage 恢复
   * 但 memoryToken 可能尚未通过 refresh_token 恢复）。需要发送请求时应使用
   * ensureToken() 进行主动校验。
   */
  const isAuthenticated = computed(() => !!user.value)

  /** 未登录访客模式（用于禁用写操作 + 显示登录提示） */
  const isGuest = computed(() => !user.value)

  /** HTTP 层就绪状态：user 存在且内存中有有效 token，可正常发起认证请求 */
  const isTokenReady = computed(() => !!user.value && !!(getMemoryToken() || accessToken.value))
  const isAdmin = computed(() => user.value?.role === "admin")
  const displayName = computed(() => user.value?.nickname || user.value?.username || "")

  /** 获取当前有效的 access_token（内存优先，兼容旧版 localStorage） */
  function getAccessToken(): string | null {
    if (accessToken.value) return accessToken.value
    // 兼容旧版：从 localStorage 读取（用户升级后自动迁移到内存）
    try {
      const old = localStorage.getItem("access_token")
      if (old) {
        accessToken.value = old
        localStorage.removeItem("access_token")
        return old
      }
    } catch { /* localStorage 不可用 */ }
    return null
  }

  function setAccessToken(token: string | null) {
    accessToken.value = token
    setMemoryToken(token)
  }

  async function register(
    username: string,
    password: string,
    nickname?: string,
    email?: string,
    signal?: AbortSignal
  ): Promise<LoginResponse> {
    const body: Record<string, unknown> = { username, password }
    if (nickname) body.nickname = nickname
    if (email) body.email = email
    const res = await apiRegister(body as { username: string; password: string; nickname?: string; email?: string }, signal ? { signal } : undefined)
    const data = res.data as LoginResponse
    // 注册接口现在直接返回 token，无需二次登录
    if (data.access_token) {
      accessToken.value = data.access_token
      setMemoryToken(data.access_token)
      safeRemove(STORAGE_KEYS.REFRESH_TOKEN)
      safeSetJSON(STORAGE_KEYS.USER, data.user)
      user.value = data.user
    }
    // 标记认证就绪，跳过路由守卫的冗余 refresh
    try { markAuthReady() } catch { /* ignore */ }
    // 清除历史项目 ID 缓存，避免切换到错误的项目
    try { localStorage.removeItem("last_project_id") } catch { /* localStorage 不可用 */ }
    return data
  }

  async function login(
    username: string,
    password: string,
    signal?: AbortSignal
  ): Promise<LoginResponse> {
    const res = await apiLogin({ username, password }, { signal })
    const data = res.data as LoginResponse

    // access_token 存内存，refresh_token 仅走 httpOnly cookie
    accessToken.value = data.access_token
    setMemoryToken(data.access_token)
    safeRemove(STORAGE_KEYS.REFRESH_TOKEN)
    safeSetJSON(STORAGE_KEYS.USER, data.user)
    user.value = data.user
    // 标记认证就绪，跳过路由守卫的冗余 refresh
    try { markAuthReady() } catch { /* ignore */ }
    try { localStorage.removeItem("last_project_id") } catch { /* localStorage 不可用 */ }
    return data
  }

  async function logout() {
    // 登出时标记正在登出，避免 401 刷新 token 的循环尝试
    const { setLoggingOut, clearRefreshTokenCookie } = await import("@/api/request")
    setLoggingOut(true)
    try {
      await apiLogout()
    } catch (err) { logger.error('[userStore] logout failed:', err) }
    finally {
      // 确保所有清理操作都执行（即使 logout API 失败）
      // 1. 清除内存中的 access_token
      accessToken.value = null
      setMemoryToken(null)
      // 2. 清除用户信息
      user.value = null
      safeRemove(STORAGE_KEYS.USER)
      // 3. 清除 localStorage 中的 refresh_token（兼容旧版）
      safeRemove(STORAGE_KEYS.REFRESH_TOKEN)
      // 4. 清除 httpOnly cookie 中的 refresh_token
      clearRefreshTokenCookie()
      // 5. 重置换出标记
      setLoggingOut(false)
      // 6. 重置路由守卫的认证缓存，防止刷新后自动重新认证
      try {
        const { resetAuthState } = await import("@/router")
        resetAuthState()
      } catch (e) {
        logger.error('[userStore] resetAuthState failed:', e)
      }
      // 7. 重置其他 store 状态，防止登出后残留旧数据
      try {
        const { useApiStore } = await import('./apiStore')
        const { useEnvStore } = await import('./envStore')
        const { useProjectStore } = await import('./projectStore')
        const { useEditorStore } = await import('./editorStore')
        const { useTabsStore } = await import('./tabsStore')
        const { usePendingApiStore } = await import('./pendingApiStore')
        const { useHintBarStore } = await import('./hintBarStore')
        useApiStore().resetState()
        useEnvStore().resetState()
        useProjectStore().resetState()
        useEditorStore().resetState()
        useTabsStore().resetState()
        usePendingApiStore().resetState()
        useHintBarStore().resetState()
      } catch (e) {
        logger.error('[userStore] reset other stores failed:', e)
      }
    }
  }

  async function fetchUserInfo() {
    try {
      const res = await getMe()
      const u = res.data as User
      user.value = u
      safeSetJSON(STORAGE_KEYS.USER, u)
    } catch (err) {
      logger.error('[userStore] fetchUserInfo failed:', err)
      // 失败时不清理 user，保留 localStorage 恢复的状态
    }
  }

  /**
   * 主动确保 HTTP 层 token 可用。
   *
   * 解决的核心问题：
   *   user 对象从 localStorage 恢复后（UI 显示已登录），
   *   但 memoryAccessToken 在刷新后丢失，导致请求 401。
   *
   * 调用时机：发送请求前、执行写操作前等需要认证的入口。
   *
   * @returns true = token 可用（原有或刚恢复），false = 无法恢复，需重新登录
   */
  async function ensureToken(): Promise<boolean> {
    // 已有有效 token → 直接通过
    if (getMemoryToken()) return true

    // 有 user 信息但无 token → 尝试用 refresh_token cookie 恢复
    // 使用 request.ts 中统一的 refreshingPromise 锁，避免双锁并发
    if (!user.value) return false

    const ok = await refreshToken()
    if (ok) {
      // refresh 成功后同步到 userStore
      const token = getMemoryToken()
      if (token) accessToken.value = token
    }
    return ok
  }

  return {
    user,
    accessToken,
    isAuthenticated,
    isGuest,
    isTokenReady,
    isAdmin,
    displayName,
    getAccessToken,
    setAccessToken,
    ensureToken,
    register,
    login,
    logout,
    fetchUserInfo,
  }
})
