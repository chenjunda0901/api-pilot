/**
 * 请求去重 composable
 *
 * 相同 cacheKey 的并发请求共享同一个 Promise，
 * 避免冗余网络请求，减少服务器压力。
 *
 * 使用方式:
 *   const dedup = createRequestDeduplicator()
 *   const data = await dedup.deduplicate(cacheKey, () => api.fetchData())
 */

export function createRequestDeduplicator() {
  const pendingRequests = new Map<string, Promise<unknown>>()

  /**
   * 对相同 cacheKey 的请求去重
   * @param cacheKey 缓存键（由 method + url + params 生成）
   * @param request 实际的请求函数
   */
  function deduplicate<T>(cacheKey: string, request: () => Promise<T>): Promise<T> {
    const existing = pendingRequests.get(cacheKey)
    if (existing) {
      return existing as Promise<T>
    }
    const promise = request().finally(() => {
      pendingRequests.delete(cacheKey)
    })
    pendingRequests.set(cacheKey, promise)
    return promise
  }

  /**
   * 生成标准化的 cacheKey
   */
  function makeCacheKey(method: string, url: string, params?: Record<string, unknown>): string {
    const normalizedMethod = method.toUpperCase()
    const normalizedParams = params ? JSON.stringify(params, Object.keys(params).sort()) : ''
    return `${normalizedMethod}:${url}:${normalizedParams}`
  }

  /** 清空所有进行中的请求 */
  function clear() {
    pendingRequests.clear()
  }

  /** 当前进行中的请求数量 */
  function pendingCount(): number {
    return pendingRequests.size
  }

  return {
    deduplicate,
    makeCacheKey,
    clear,
    pendingCount,
  }
}

/** 全局单例 */
export const globalRequestDeduplicator = createRequestDeduplicator()