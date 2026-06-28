/**
 * SWR (stale-while-revalidate) 缓存策略 composable
 *
 * 策略:
 *   1. 请求时 → 有缓存且未过期 → 直接返回缓存
 *   2. 有缓存但已过期 → 返回缓存（stale）+ 后台刷新（revalidate）
 *   3. 无缓存 → 发起新请求并缓存
 *
 * 用法:
 *   const data = await swr.get('key1', () => fetchData(), { ttl: 60000 })
 *   swr.mutate('key1', newData)  // 手动更新缓存
 */

interface CacheEntry<T> {
  data: T
  expiresAt: number
  isValidating: boolean
}

export function createSWRCache() {
  const cache = new Map<string, CacheEntry<unknown>>()
  const pendingRefreshes = new Map<string, Promise<unknown>>()

  /**
   * 获取缓存数据（如有）
   * @param key 缓存键
   * @param fetcher 数据获取函数
   * @param options TTL 配置
   */
  function get<T>(key: string, fetcher: () => Promise<T>, options: { ttl?: number } = {}): Promise<T> {
    const { ttl = 60000 } = options
    const entry = cache.get(key) as CacheEntry<T> | undefined

    // 缓存有效 → 直接返回
    if (entry && Date.now() < entry.expiresAt) {
      return Promise.resolve(entry.data)
    }

    // 缓存过期 → 返回 stale 数据 + 后台刷新
    if (entry && Date.now() >= entry.expiresAt) {
      refreshInBackground(key, fetcher, ttl)
      return Promise.resolve(entry.data)
    }

    // 无缓存 → 发起新请求
    return fetchAndCache(key, fetcher, ttl)
  }

  async function fetchAndCache<T>(key: string, fetcher: () => Promise<T>, ttl: number): Promise<T> {
    // 如果已有进行中的请求，复用
    const pending = pendingRefreshes.get(key) as Promise<T> | undefined
    if (pending) return pending

    const promise = fetcher()
      .then(data => {
        cache.set(key, { data, expiresAt: Date.now() + ttl, isValidating: false })
        return data
      })
      .finally(() => {
        pendingRefreshes.delete(key)
      })

    pendingRefreshes.set(key, promise)
    return promise
  }

  async function refreshInBackground<T>(key: string, fetcher: () => Promise<T>, ttl: number): Promise<void> {
    // 已有进行中的刷新，忽略
    if (pendingRefreshes.has(key)) return

    const entry = cache.get(key) as CacheEntry<T> | undefined
    if (entry) entry.isValidating = true

    const promise = fetcher()
      .then(data => {
        cache.set(key, { data, expiresAt: Date.now() + ttl, isValidating: false })
      })
      .catch(() => {
        // 刷新失败，标记为非验证中，保留旧数据
        if (entry) entry.isValidating = false
      })
      .finally(() => {
        pendingRefreshes.delete(key)
      })

    pendingRefreshes.set(key, promise)
  }

  /**
   * 手动更新缓存
   */
  function mutate<T>(key: string, data: T, ttl = 60000) {
    cache.set(key, { data, expiresAt: Date.now() + ttl, isValidating: false })
  }

  /**
   * 获取缓存条目（不触发请求）
   */
  function getCache<T>(key: string): T | undefined {
    const entry = cache.get(key)
    return entry ? (entry.data as T) : undefined
  }

  /**
   * 清空所有缓存
   */
  function clear() {
    cache.clear()
    pendingRefreshes.clear()
  }

  return {
    get,
    mutate,
    getCache,
    clear,
  }
}

/** 全局单例 */
export const globalSWRCache = createSWRCache()