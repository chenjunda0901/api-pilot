/**
 * 安全的 JSON 解析工具
 * 提供统一的 JSON 解析接口，带错误处理
 */

/**
 * 安全解析 JSON 字符串，解析失败时返回默认值
 */
export function safeJsonParse<T = unknown>(
  str: string | null | undefined,
  fallback: T
): T {
  if (!str) return fallback
  if (typeof str !== 'string') return fallback
  try {
    return JSON.parse(str) as T
  } catch {
    return fallback
  }
}

/**
 * 安全解析 JSON，解析失败时返回原始字符串
 */
export function tryJsonParse<T = unknown>(str: string): T | string {
  if (!str || typeof str !== 'string') return str
  try {
    return JSON.parse(str) as T
  } catch {
    return str
  }
}

/**
 * 安全解析 JSON，返回 null 表示解析失败
 */
export function parseJsonOrNull<T = unknown>(str: string | null | undefined): T | null {
  if (!str) return null
  try {
    return JSON.parse(str) as T
  } catch {
    return null
  }
}

/**
 * 安全序列化 JSON，null/undefined 返回空字符串
 */
export function safeJsonStringify(val: unknown, fallback = '{}'): string {
  if (val === null || val === undefined) return fallback
  try {
    return JSON.stringify(val)
  } catch {
    return fallback
  }
}
