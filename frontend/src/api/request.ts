import axios from 'axios'
import i18n from '@/i18n'
import router from '@/router'
import { logger } from '@/utils/logger'
import { globalRequestDeduplicator } from '@/composables/useRequestDeduplicator'
import { retryWithBackoff, isRetryableError } from '@/utils/retry'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,  // 确保 httpOnly cookie（refresh_token）随请求发送
  // 接受所有 HTTP 状态码，避免浏览器控制台显示 401/403 等预期错误
  validateStatus: () => true,
})

// ── Token 存储策略 ───────────────────────────────────────────────────────────
// access_token:   全程内存存储（XSS 防护），页面刷新后通过 refresh_token 恢复
// refresh_token:  ★ 已迁移到 httpOnly cookie（由后端 set-cookie 设置）
//                  不再写入 localStorage，彻底消除 XSS 盗取风险
//                  注意：若后端尚未支持 httpOnly cookie，此字段仍可能从
//                  localStorage 降级读取（兼容旧会话），新登录会话强制 cookie
//
// 迁移说明（2026-05-29）：
//   旧版将 refresh_token 存入 localStorage，存在 XSS 盗取风险。
//   新版由后端在登录/刷新响应中通过 Set-Cookie: refresh_token=xxx; HttpOnly 设置，
//   浏览器自动存储并仅在 HTTP 请求中发送，JavaScript 无法读写。
//   若后端尚未部署 httpOnly cookie，可通过 .env 设置 FORCE_REFRESH_TOKEN_COOKIE=false
//   降级为 localStorage（仅限内网/受控环境）。

const REFRESH_TOKEN_COOKIE_NAME = 'api_pilot_refresh_token'

function getRefreshTokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(?:^|; )' + REFRESH_TOKEN_COOKIE_NAME + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

export function clearRefreshTokenCookie() {
  if (typeof document === 'undefined') return
  document.cookie = REFRESH_TOKEN_COOKIE_NAME + '=; Max-Age=0; path=/'
}

// ── Token 并发刷新队列 ──────────────────────────────────────────────────
// 当多个请求同时收到 401 时，只触发一次 /auth/refresh，
// 其余请求挂起排队，等 refresh 成功后自动重发，避免"刷新风暴"。
let refreshingPromise: Promise<boolean> | null = null
const MAX_REFRESH_RETRIES = 3
const REFRESH_TIMEOUT_MS = 10000

/**
 * 判断是否存在"可能有效"的刷新凭据。
 *
 * ★ 关键设计：refresh_token 走 httpOnly cookie，JS 无法读取 document.cookie 看到它。
 *   但浏览器在每次 HTTP 请求时仍会自动带上该 cookie（受 withCredentials 控制）。
 *   因此"我能不能看到 refresh_token"并不能作为"我有没有 refresh_token"的判断依据。
 *
 * 改为检查更可靠的代理信号：localStorage 中是否有持久化的 user 对象。
 * - 首次访问（从未登录）：localStorage 无 user → 肯定没 refresh cookie → 不发 refresh 请求
 * - 老用户重载：localStorage 有 user → 可能有 refresh cookie → 尝试 refresh
 *   后端会做最终裁决：cookie 有效 → 返回新 access_token；cookie 过期/被吊销 → 401
 */
function hasLikelyRefreshToken(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return !!localStorage.getItem('user')
  } catch {
    return false
  }
}

/** 内存级 access_token 存储（XSS 防护） */
let _memoryAccessToken: string | null = null

export function setMemoryToken(token: string | null) {
  _memoryAccessToken = token
}

export function getMemoryToken(): string | null {
  return _memoryAccessToken
}

function base64UrlDecode(str: string): string {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  while (base64.length % 4) base64 += '='
  return atob(base64)
}

function decodeToken(token: string): { exp?: number } | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(base64UrlDecode(payload))
  } catch {
    return null
  }
}

/** 检查 Token 是否即将过期（5 分钟内过期视为即将过期） */
function isTokenExpiringSoon(): boolean {
  const token = getMemoryToken()
  if (!token) return false
  try {
    const payload = decodeToken(token)
    if (!payload?.exp) return false
    const TOKEN_EXPIRY_THRESHOLD_MS = 5 * 60 * 1000
    return (payload.exp * 1000 - Date.now()) < TOKEN_EXPIRY_THRESHOLD_MS
  } catch {
    return false
  }
}

/**
 * 主动刷新 Token（带重试）。
 * 在请求拦截器中非阻塞调用，不阻塞当前请求。
 * 最多重试 MAX_REFRESH_RETRIES 次，使用指数退避。
 */
async function proactiveRefresh(): Promise<void> {
  if (IS_LOGGING_OUT) return
  let retry = 0
  while (retry < MAX_REFRESH_RETRIES && !IS_LOGGING_OUT) {
    const ok = await refreshToken()
    if (ok) return
    retry++
    if (retry < MAX_REFRESH_RETRIES) {
      const delay = Math.min(500 * Math.pow(2, retry - 1), 3000)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
}

/** 无 XSS 风险的 token 读取策略：
 * - access_token: 仅从内存获取
 * - refresh_token: 仅从 httpOnly cookie 获取（FORCE_COOKIE=true 时）
 */
export function getToken(key: string): string | null {
  if (key === 'access_token') {
    return getMemoryToken()
  }
  if (key === 'refresh_token') {
    const fromCookie = getRefreshTokenFromCookie()
    return fromCookie || null
  }
  try { return localStorage.getItem(key) } catch { return null }
}

async function doRefreshToken(): Promise<boolean> {
  // 没有持久化用户信息时直接返回，避免无效请求导致控制台 401 报错
  // ★ 注意：不能用 getToken('refresh_token') 判断 httpOnly cookie 是否存在，
  //   JS 永远读不到 httpOnly cookie；这里用 localStorage.user 作代理信号
  if (!hasLikelyRefreshToken()) return false
  // refresh_token 由浏览器自动随 HTTP 请求发送（httpOnly cookie + withCredentials），
  // 后端会从 cookie 读取。Authorization Bearer 仅在可读到非 httpOnly 凭据时附加。
  try {
    const headers: Record<string, string> = {}
    const refreshToken = getToken('refresh_token')
    if (refreshToken) {
      headers.Authorization = 'Bearer ' + refreshToken
    }
    // 添加 10 秒超时，防止刷新请求无限挂起
    const res = await axios.post('/api/v1/auth/refresh', {}, {
      headers,
      withCredentials: true,  // 关键：确保浏览器发送 httpOnly cookie
      timeout: 10000,
    })
    const d = res.data?.data
    if (!d?.access_token) return false
    setMemoryToken(d.access_token)
    // refresh_token 由后端通过 httpOnly cookie 设置，不再写入 localStorage
    return true
  } catch {
    return false
  }
}

/**
 * 带排队锁和超时的 Token 刷新。
 * 确保多个并发请求只触发一次刷新，其他请求等待结果。
 * 添加 10 秒超时机制，防止刷新请求无限挂起。
 */
export async function refreshToken(): Promise<boolean> {
  if (refreshingPromise) return refreshingPromise
  refreshingPromise = Promise.race([
    doRefreshToken(),
    new Promise<boolean>((resolve) =>
      setTimeout(() => resolve(false), REFRESH_TIMEOUT_MS)
    )
  ])
  try {
    const result = await refreshingPromise
    return result
  } finally {
    refreshingPromise = null
  }
}

// ── 并发请求等待队列 ──────────────────────────────────────────────────
// 使用 refreshingPromise 作为锁机制，移除旧的 isRefreshing 标志
// refreshingPromise 已在上面定义，用于管理并发刷新请求

let IS_LOGGING_OUT = false  // 标记正在登出状态，避免 refresh token 循环

export function setLoggingOut(val: boolean) {
  IS_LOGGING_OUT = val
}

/**
 * Token 彻底失效时强制登出：
 * 清除用户状态 + 跳转登录页，避免 UI 显示已登录但实际无法请求
 */
async function forceLogout(): Promise<void> {
  if (IS_LOGGING_OUT) return
  IS_LOGGING_OUT = true
  try {
    // 清除内存中的 access_token
    setMemoryToken(null)
    // 清除 Pinia store 中的用户状态 + localStorage 持久化数据
    const { useUserStore } = await import('../stores/userStore')
    const { STORAGE_KEYS } = await import('../constants/events')
    const userStore = useUserStore()
    userStore.user = null
    userStore.setAccessToken(null)
    try { localStorage.removeItem(STORAGE_KEYS.USER) } catch { /* ignore */ }
    try { localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN) } catch { /* ignore */ }
    // 重置路由守卫的认证缓存
    try {
      const { resetAuthState } = await import('../router')
      resetAuthState()
    } catch { /* ignore */ }
    // 跳转登录页，携带 redirect 参数以便登录后返回
    const redirect = window.location.pathname + window.location.search
    await router.push({ path: '/login', query: { redirect } })
    // 提示用户（延迟显示，避免被路由切换打断）
    setTimeout(() => {
      void import('element-plus').then(mod =>
        mod.ElMessage.warning({
          message: '登录状态已失效，请重新登录',
          showClose: true,
          duration: 4000,
        })
      )
    }, 100)
  } catch (e) {
    logger.error('[request] forceLogout failed:', e)
  } finally {
    IS_LOGGING_OUT = false
  }
}

// ── 类型守卫 ────────────────────────────────────────────────────────────
interface AxiosErrorResponse {
  response?: {
    status?: number;
    data?: {
      message?: string;
      code?: string;
      detail?: string;
    };
  };
	  config?: {
	    url?: string;
	    method?: string;
	    headers?: Record<string, unknown>;
	    _retryCount?: number;
	    _skipDeduplication?: boolean;
	    _dedupCacheKey?: string;
	  };
  message?: string;
  code?: string;
}

function isAxiosErrorLike(err: unknown): err is AxiosErrorResponse {
  return typeof err === 'object' && err !== null
}

/**
 * 判断请求是否为写操作（POST / PUT / DELETE / PATCH）
 */
function isWriteRequest(method: string): boolean {
  return ['post', 'put', 'delete', 'patch'].includes(method?.toLowerCase())
}

request.interceptors.request.use((config) => {
  const token = getToken('access_token')
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  // 12.3: Token 过期前主动刷新（5 分钟内过期）
  // 非阻塞调用，不阻塞当前请求
  if (isTokenExpiringSoon()) {
    proactiveRefresh().catch((err) => { logger.error('[request] proactive refresh failed:', err) })
  }
  // 请求去重 cacheKey 注入（仅幂等请求）
  const method = (config.method || 'get').toLowerCase()
  if (['get', 'head', 'options'].includes(method) && !config._skipDeduplication) {
    const dedupKey = globalRequestDeduplicator.makeCacheKey(
      method.toUpperCase(),
      config.url || '',
      config.params as Record<string, unknown>
    )
    config._dedupCacheKey = dedupKey
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    // validateStatus: () => true 导致所有响应都流入这里，2xx 走正常流程，非 2xx 走错误处理
    if (response.status >= 200 && response.status < 300) {
      if (isTokenExpiringSoon()) {
        window.dispatchEvent(new CustomEvent("session-expiring"))
        refreshToken().catch(() => { })
      }
      return response.data
    }
    // 非 2xx：构造 fake AxiosError，交给下面的错误拦截器统一处理
    // ★ 必须保留原始 config 引用（而非新建精简对象），否则 _retryCount 等自定义字段会丢失，
    //   导致 validateStatus: () => true 模式下重试计数失效、无限刷新循环
    const fakeAxiosError = {
      response: {
        status: response.status,
        data: response.data,
      },
      config: response.config,
      message: `Request failed with status ${response.status}`,
      isAxiosError: true,
    }
    throw fakeAxiosError
  },
	  async (error: unknown) => {
	    const err: AxiosErrorResponse = isAxiosErrorLike(error) ? error : {}
	    const status = err.response?.status
	    const data = err.response?.data
	    const url = err.config?.url || ''
	    const method = err.config?.method || ''

	    // 请求被取消（AbortController signal）— 静默拒绝，不显示错误提示
	    // 调用方通过 config.signal: new AbortController().signal 传入，
	    // 路由切换/Tab 关闭时调用 controller.abort() 即可取消已发出的请求
	    if (err.code === 'ERR_CANCELED' || err.message?.includes('canceled')) {
	      return Promise.reject(err)
	    }

	    // ── 自动重试 ──────────────────────────────────────────────────────
	    // 幂等请求（GET/HEAD/OPTIONS）遇到可重试错误时自动重试（最多 3 次）
	    // 非幂等请求仅网络错误重试
	    const httpMethod = (method || '').toLowerCase()
	    const isIdempotent = ['get', 'head', 'options'].includes(httpMethod)
	    const retryCount = (err.config?._retryCount as number) || 0
	    if (retryCount < 3 && ((isIdempotent && isRetryableError(err)) || isRetryableError(err))) {
	      const config = err.config
	      if (config) {
	        config._retryCount = retryCount + 1
	        return retryWithBackoff(
	          () => request(config),
	          { maxRetries: 3 - retryCount, baseDelay: 1000, retryOn: isRetryableError }
	        )
	      }
	    }

	    // 网络错误（无法连接服务器）— 先检查更具体的错误
    if (err.message?.includes('Network Error') || err.message?.includes('ERR_')) {
      const msg = i18n.global.t('request.cannotConnect')
      void import('element-plus').then(mod => mod.ElMessage.error({ message: msg, showClose: true, duration: 5000 }))
      return Promise.reject(err)
    }

    // 超时或无响应
    if (err.code === 'ECONNABORTED' || err.message?.includes('timeout') || !err.response) {
      const msg = err.code === 'ECONNABORTED' || err.message?.includes('timeout')
        ? i18n.global.t('request.timeout')
        : i18n.global.t('request.networkError')
      void import('element-plus').then(mod => mod.ElMessage.error({ message: msg, showClose: true }))
      return Promise.reject(err)
    }

    if (url === '/auth/login' || url === '/auth/register') {
      // 仅 429 由拦截器提示（视图层无法区分），其余错误交由视图 catch 块处理，避免双重提示
      if (status === 429) {
        void import('element-plus').then(mod => mod.ElMessage.error(i18n.global.t('request.tooFrequent')))
      }
      return Promise.reject(err)
    }

    if (url === '/auth/refresh') {
      return Promise.reject(err)
    }

    // 401 未授权 — 尝试用 refresh_token 恢复 access_token
    if (status === 401) {
      const hasAccessToken = !!getToken('access_token')
      // ★ 用 localStorage.user 作代理信号判断是否存在 refresh cookie
      //   （httpOnly cookie JS 读不到，不能用 getToken('refresh_token') 判断）
      const hasRefreshToken = hasLikelyRefreshToken()
      if (IS_LOGGING_OUT) {
        return Promise.reject(err)
      }
      // 防止无限刷新循环：每个原始请求最多重试一次
      if (err.config?._retryCount && err.config._retryCount >= 1) {
        await forceLogout()
        return Promise.reject(err)
      }
      // 既无 access_token 也无 refresh_token：未登录状态
      if (!hasAccessToken && !hasRefreshToken) {
        if (isWriteRequest(method)) {
          void import('element-plus').then(mod => mod.ElMessage.warning('请先登录'))
          void router.push({ path: '/login', query: { redirect: window.location.pathname + window.location.search } })
          return new Promise<never>(() => {})
        }
        // 读操作：静默拒绝，由页面层自行处理（显示空状态等）
        return Promise.reject(err)
      }
      // 有 refresh_token（或 access_token 过期），尝试刷新
      {
        // 使用 refreshingPromise 作为锁，并发请求共享同一个刷新 Promise
        let ok = await refreshToken()
        let retry = 0
        while (!ok && retry < MAX_REFRESH_RETRIES && !IS_LOGGING_OUT) {
          const delay = Math.min(500 * Math.pow(2, retry), 3000)
          await new Promise(resolve => setTimeout(resolve, delay))
          retry++
          ok = await refreshToken()
        }

        if (ok) {
          const token = getToken('access_token')
          if (token && err.config) {
            const config = err.config
            config.headers = config.headers || {}
            config.headers.Authorization = 'Bearer ' + token
            config._retryCount = (config._retryCount || 0) + 1
            return request(config)
          }
        }

        // 刷新失败：token 已彻底失效，强制登出并跳转登录页
        await forceLogout()
        return Promise.reject(err)
      }
    }

    // 429 请求过于频繁
    if (status === 429) {
      const msg = data?.message || i18n.global.t('request.operationFrequent')
      void import('element-plus').then(mod => mod.ElMessage.warning(msg))
      return Promise.reject(err)
    }

    // 403 权限不足 — 后端 PROJECT_FORBIDDEN 等权限错误，非 token 过期
    // 不应尝试刷新 token（刷新后仍是同一用户，权限不会变）。
    // 处理策略：
    // - 默认显示全局警告提示
    // - 若请求配置了 _silent403: true，则不弹全局警告（组件自行处理，如显示无权限页面）
    // - 不自动跳转 dashboard，由各页面根据场景决定降级展示方式
    if (status === 403) {
      if (!err?.config?._silent403) {
        const msg = data?.message || i18n.global.t('request.projectForbidden')
        void import('element-plus').then(mod => {
          mod.ElMessage.warning({
            message: msg,
            showClose: true,
            duration: 4000,
          })
        })
      }
      return Promise.reject(err)
    }

    // 409 数据冲突（乐观锁）— 提示用户数据已被修改
    if (status === 409) {
      const msg = data?.message || i18n.global.t('request.dataConflict')
      void import('element-plus').then(mod => mod.ElMessage.warning({ message: msg, showClose: true, duration: 5000 }))
      return Promise.reject(err)
    }

    // 400 参数错误（接口不存在、参数无效等）
    if (status === 400) {
      // 静默处理：不显示错误弹窗，由各页面自行决定如何处理
      // 例如 ApiDetail.vue 会自动跳转到列表页
      return Promise.reject(err)
    }

    // 404 资源不存在
    if (status === 404) {
      // 静默处理：不显示警告弹窗，由各页面自行决定如何处理
      return Promise.reject(err)
    }

    // 422 参数校验失败
    if (status === 422) {
      const errorMsg = data?.message || i18n.global.t('request.paramError')
      const detail = data?.detail || ''
      const fullMsg = detail ? `${errorMsg}: ${detail}` : errorMsg
      void import('element-plus').then(mod => mod.ElMessage.error(fullMsg))
      return Promise.reject(err)
    }

    // 500+ 服务器错误
    if (status && status >= 500) {
      const msg = data?.message || i18n.global.t('request.serverBusy')
      void import('element-plus').then(mod => mod.ElMessage.error(msg))
      return Promise.reject(err)
    }

    // 其他错误（包括后端返回的友好错误消息）
    const msg = data?.message || err.message || i18n.global.t('request.operationFailed')
    // 避免显示英文或 technical 错误消息
    if (msg.length > 100 || !/[\u4e00-\u9fff]/.test(msg)) {
      void import('element-plus').then(mod => mod.ElMessage.error(i18n.global.t('request.operationFailed')))
    } else {
      void import('element-plus').then(mod => mod.ElMessage.error(msg))
    }
    return Promise.reject(err)
  },
)

export default request
