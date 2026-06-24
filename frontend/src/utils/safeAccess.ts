/**
 * 安全数据访问工具
 * 提供防御性编程，防止 undefined/null 错误
 */

import { ElMessage } from 'element-plus'

/**
 * 安全获取对象属性值
 * @param obj 对象
 * @param path 属性路径，如 'a.b.c'
 * @param defaultValue 默认值
 */
export function safeGet<T = unknown>(obj: unknown, path: string, defaultValue: T): T {
  if (obj == null) return defaultValue

  // 拒绝原型链属性访问，防止 __proto__/constructor 污染
  const REJECTED_KEYS = new Set(['__proto__', 'constructor', 'prototype'])

  const keys = path.split('.')
  let result: unknown = obj

  for (const key of keys) {
    if (result == null) return defaultValue
    if (typeof result !== 'object') return defaultValue
    if (REJECTED_KEYS.has(key)) return defaultValue
    result = (result as Record<string, unknown>)[key]
  }

  return result as T ?? defaultValue
}

/**
 * 安全调用函数
 * @param fn 要执行的函数
 * @param fallback 出错时的返回值
 */
export function safeCall<T>(fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch {
    return fallback
  }
}

/**
 * 安全执行异步函数
 */
export async function safeAsync<T>(
  promise: Promise<T>,
  fallback: T,
  errorMessage?: string
): Promise<T> {
  try {
    return await promise
  } catch {
    if (errorMessage) {
      ElMessage.warning(errorMessage)
    }
    return fallback
  }
}

/**
 * 安全解析 JSON
 */
export function safeJSONParse<T = unknown>(str: string, fallback: T): T {
  try {
    return JSON.parse(str) as T
  } catch {
    return fallback
  }
}

/**
 * 安全序列化 JSON
 */
export function safeJSONStringify(obj: unknown, fallback: string = '{}'): string {
  try {
    return JSON.stringify(obj)
  } catch {
    return fallback
  }
}

/**
 * 类型守卫：检查是否为对象
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/**
 * 类型守卫：检查是否为数组
 */
export function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value)
}

/**
 * 安全访问数组元素
 */
export function safeArrayGet<T>(arr: unknown[], index: number, fallback: T): T {
  if (!Array.isArray(arr)) return fallback
  return arr[index] ?? fallback
}

/**
 * 安全调用方法
 */
export function safeInvoke<T>(
  obj: unknown,
  methodName: string,
  args: unknown[] = [],
  fallback?: T
): T | undefined {
  if (obj == null) return fallback
  const method = (obj as Record<string, unknown>)[methodName]
  if (typeof method !== 'function') return fallback
  try {
    return (method as (...args: unknown[]) => T).apply(obj, args)
  } catch {
    return fallback
  }
}

/**
 * 延迟执行（防抖）
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn(...args)
    }, delay)
  }
}

/**
 * 延迟执行（节流）
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastTime = 0
  return (...args: Parameters<T>) => {
    const now = Date.now()
    if (now - lastTime >= delay) {
      lastTime = now
      fn(...args)
    }
  }
}

/**
 * 重试机制
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxAttempts?: number
    delay?: number
    onRetry?: (attempt: number, error: unknown) => void
  } = {}
): Promise<T> {
  const { maxAttempts = 3, delay = 1000, onRetry } = options
  
  let lastError: unknown
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      if (attempt < maxAttempts) {
        onRetry?.(attempt, err)
        await new Promise(resolve => setTimeout(resolve, delay * attempt))
      }
    }
  }
  
  throw lastError
}

/**
 * 显示友好错误提示（避免技术术语）
 */
export function showFriendlyError(error: unknown, fallbackMessage = '操作失败，请稍后重试') {
  // 提取后端返回的中文错误消息
  if (isObject(error)) {
    const msg = safeGet(error, 'response.data.message', '')
    const data = safeGet(error, 'response.data', {})
    
    // 有友好的中文消息
    if (typeof msg === 'string' && msg.length < 100 && /[\u4e00-\u9fa5]/.test(msg)) {
      ElMessage.error(msg)
      return
    }
    
    // 后端返回的 code
    const code = safeGet(data, 'code', '')
    if (code) {
      ElMessage.error(fallbackMessage)
      return
    }
  }
  
  // 浏览器原生错误
  if (error instanceof TypeError) {
    ElMessage.error('数据处理失败，请刷新页面后重试')
    return
  }
  
  if (error instanceof ReferenceError) {
    ElMessage.error('系统异常，请刷新页面')
    return
  }
  
  // 默认友好消息
  ElMessage.error(fallbackMessage)
}

/**
 * 空状态检查
 */
export function isEmpty(value: unknown): boolean {
  if (value == null) return true
  if (typeof value === 'string') return value.trim() === ''
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

/**
 * 提供默认值的工具函数
 */
export function withDefault<T>(value: T | null | undefined, defaultValue: T): T {
  return value ?? defaultValue
}

/**
 * 链式安全调用
 */
export class SafeChain<T> {
  private value: T

  constructor(value: T) {
    this.value = value
  }

  get<K extends keyof T>(key: K): SafeChain<T[K]> {
    const val = this.value?.[key]
    return new SafeChain(val as T[K])
  }

  call<K extends keyof T>(
    key: K,
    ...args: unknown[]
  ): SafeChain<ReturnType<T[K]> | undefined> {
    const fn = this.value?.[key]
    if (typeof fn === 'function') {
      try {
        const result = fn(...args)
        return new SafeChain(result as ReturnType<T[K]>)
      } catch {
        return new SafeChain(undefined as ReturnType<T[K]>)
      }
    }
    return new SafeChain(undefined as ReturnType<T[K]>)
  }

  valueOf(): T | undefined {
    return this.value
  }

  or(defaultValue: T): T {
    return this.value ?? defaultValue
  }
}

export function safe<T>(value: T): SafeChain<T> {
  return new SafeChain(value)
}