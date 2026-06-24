/**
 * 深度比较工具函数
 * 用于精确比较两个对象/数组是否相等，避免 JSON.stringify 的键顺序问题
 */

/**
 * 深度比较两个值是否相等
 * @param a 第一个值
 * @param b 第二个值
 * @returns 是否相等
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  // 处理 null 和 undefined
  if (a === b) return true
  
  // 处理 null 和 undefined 差异
  if (a == null || b == null) return a === b
  
  // 处理不同类型
  if (typeof a !== typeof b) return false
  
  // 处理原始类型
  if (typeof a !== 'object') return a === b
  
  // 处理数组
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false
    }
    return true
  }
  
  // 处理对象
  if (Array.isArray(a) !== Array.isArray(b)) return false
  
  const aObj = a as Record<string, unknown>
  const bObj = b as Record<string, unknown>
  
  const aKeys = Object.keys(aObj)
  const bKeys = Object.keys(bObj)
  
  if (aKeys.length !== bKeys.length) return false
  
  for (const key of aKeys) {
    if (!Object.prototype.hasOwnProperty.call(bObj, key)) return false
    if (!deepEqual(aObj[key], bObj[key])) return false
  }
  
  return true
}

/**
 * 深度比较多个值是否全部相等
 * @param ...values 要比较的值数组
 * @returns 是否全部相等
 */
export function deepEqualAll(...values: unknown[]): boolean {
  if (values.length < 2) return true
  const first = values[0]
  return values.every(v => deepEqual(first, v))
}

/**
 * 深度克隆对象（避免引用问题）
 * @param obj 要克隆的对象
 * @returns 克隆后的对象
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  const cloned = {} as Record<string, unknown>
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloned[key] = deepClone((obj as Record<string, unknown>)[key])
    }
  }
  return cloned as T
}

/**
 * 获取两个对象之间的差异
 * @param a 第一个对象
 * @param b 第二个对象
 * @returns 差异的对象表示
 */
export function deepDiff(a: unknown, b: unknown): Record<string, unknown> | null {
  const diffs: Record<string, unknown> = {}
  
  if (typeof a !== 'object' || typeof b !== 'object') {
    if (a !== b) {
      diffs['_'] = b
    }
    return Object.keys(diffs).length > 0 ? diffs : null
  }
  
  const aObj = (a || {}) as Record<string, unknown>
  const bObj = (b || {}) as Record<string, unknown>
  
  const allKeys = new Set([...Object.keys(aObj), ...Object.keys(bObj)])
  
  for (const key of allKeys) {
    const aVal = aObj[key]
    const bVal = bObj[key]
    
    if (!deepEqual(aVal, bVal)) {
      if (typeof bVal === 'object' && bVal !== null) {
        diffs[key] = bVal
      } else {
        diffs[key] = bVal
      }
    }
  }
  
  return Object.keys(diffs).length > 0 ? diffs : null
}