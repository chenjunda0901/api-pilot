/**
 * 指数退避自动重试工具
 *
 * 提供自动重试能力，适用于网络错误、服务器临时故障等场景。
 * 策略：幂等请求（GET/HEAD/OPTIONS）遇到网络错误或 5xx 自动重试，
 *       非幂等请求仅网络错误重试，4xx 不重试。
 */

/** 随机抖动，防止惊群效应 */
function jitter(max = 1000): number {
  return Math.random() * max
}

/**
 * 指数退避自动重试
 * @param fn 要执行并可能重试的异步函数
 * @param options 配置选项
 * @returns fn 的结果
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number
    baseDelay?: number
    maxDelay?: number
    retryOn?: (error: unknown) => boolean
  } = {}
): Promise<T> {
  const {
    maxRetries = 5,
    baseDelay = 1000,
    maxDelay = 30000,
    retryOn = () => true,
  } = options

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn()
    } catch (error) {
      if (attempt === maxRetries || !retryOn(error)) {
        throw error
      }
      const delay = Math.min(baseDelay * Math.pow(2, attempt) + jitter(), maxDelay)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }

  throw new Error('Unreachable')
}

/**
 * 判断错误是否可重试
 *
 * 策略:
 *   - 网络错误/超时: 可重试
 *   - 5xx 服务器错误: 可重试
 *   - 4xx 客户端错误 (除 429): 不可重试
 *   - 429 限流: 不可重试
 */
export function isRetryableError(error: unknown): boolean {
  const err = error as {
    response?: { status?: number }
    message?: string
    code?: string
  }

  // 网络错误或超时
  if (
    err.message?.includes('Network Error') ||
    err.message?.includes('timeout') ||
    err.code === 'ECONNABORTED' ||
    err.code === 'ERR_NETWORK'
  ) {
    return true
  }

  const status = err.response?.status
  if (!status) return true // 无状态码，视为网络错误

  if (status >= 500) return true
  if (status === 429) return false
  if (status >= 400 && status < 500) return false

  return true
}