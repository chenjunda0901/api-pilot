import type { RouteRecordRaw } from 'vue-router'

/**
 * 路由预加载 composable
 *
 * 策略:
 * 1. Hover 预加载 — 鼠标悬停导航链接时触发 dynamic import
 * 2. 空闲预加载 — requestIdleCallback 预加载"可能访问"的路由
 * 3. 数据预加载 — 结合 SWR，提前获取页面数据
 *
 * 用法:
 *   const prefetcher = useRoutePrefetcher(routes)
 *   // hover 时调用:
 *   prefetcher.prefetch('ApiDetail')
 *   // 空闲时:
 *   prefetcher.prefetchOnIdle(['Dashboard', 'Apis', 'Scenes'])
 */
export function useRoutePrefetcher(routes: RouteRecordRaw[]) {
  const prefetched = new Set<string>()

  /** 预加载单个路由的组件 chunk */
  function prefetch(routeName: string) {
    if (prefetched.has(routeName)) return
    const route = findRoute(routes, routeName)
    if (route?.component && typeof route.component === 'function') {
      ;(route.component as () => Promise<any>)().then(() => {
        prefetched.add(routeName)
      }).catch(() => { /* 静默失败 */ })
    }
  }

  /** 空闲时预加载一组路由 */
  function prefetchOnIdle(routeNames: string[]) {
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(() => {
        routeNames.forEach(name => prefetch(name))
      }, { timeout: 2000 })
    }
  }

  return { prefetch, prefetchOnIdle, prefetched }
}

function findRoute(routes: RouteRecordRaw[], name: string): RouteRecordRaw | undefined {
  for (const route of routes) {
    if (route.name === name) return route
    if (route.children) {
      const found = findRoute(route.children, name)
      if (found) return found
    }
  }
  return undefined
}