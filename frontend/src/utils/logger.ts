/**
 * 统一日志模块 —— 生产环境可关闭，开发环境保留
 * 替代直接使用 console.log/warn/error
 */

const isDev = import.meta.env.DEV

export const logger = {
  error(...args: unknown[]) {
    if (isDev) {
      console.error('[API Pilot]', ...args)
    }
  },
  warn(...args: unknown[]) {
    if (isDev) {
      console.warn('[API Pilot]', ...args)
    }
  },
  info(...args: unknown[]) {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.info('[API Pilot]', ...args)
    }
  },
  debug(...args: unknown[]) {
    if (isDev) {
      // eslint-disable-next-line no-console
      console.debug('[API Pilot]', ...args)
    }
  },
}

/**
 * 判断错误是否为 401 未授权错误。
 * 用于在组件 catch 块中静默跳过未登录用户的 API 错误日志。
 */
export function isSilentAuthError(e: unknown): boolean {
  const err = e as { response?: { status?: number } }
  return err?.response?.status === 401
}
