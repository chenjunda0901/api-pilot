import { ref } from 'vue'

export type ConnectionQuality = 'fast' | 'normal' | 'slow' | 'unknown'

export interface NetworkDetectorOptions {
  /** 心跳检测间隔 (ms)，0 表示不启用心跳 */
  pingInterval?: number
  /** 心跳 URL */
  pingUrl?: string
  /** 连接质量判定 — fast 阈值 (ms) */
  fastThreshold?: number
  /** 连接质量判定 — slow 阈值 (ms) */
  slowThreshold?: number
}

/**
 * 网络状态检测 composable
 *
 * 基于 navigator.onLine + 心跳探测，提供响应式网络状态和连接质量评估。
 * 支持网络恢复/断开回调，便于全局处理网络变化。
 *
 * 用法:
 *   const detector = createNetworkDetector()
 *   detector.onOnline(() => refreshData())
 *   detector.onOffline(() => showBanner())
 */
export function createNetworkDetector(options: NetworkDetectorOptions = {}) {
  const {
    pingInterval = 30000,
    pingUrl = '/api/v1/ping',
    fastThreshold = 200,
    slowThreshold = 1000,
  } = options

  const isOnline = ref(typeof navigator !== 'undefined' ? navigator.onLine : true)
  const connectionQuality = ref<ConnectionQuality>('unknown')

  // 最近 5 次请求耗时（用于判定连接质量）
  const recentLatencies: number[] = []
  let pingTimer: ReturnType<typeof setInterval> | null = null
  const onlineCallbacks: (() => void)[] = []
  const offlineCallbacks: (() => void)[] = []

  function updateConnectionQuality() {
    if (recentLatencies.length < 2) {
      connectionQuality.value = 'unknown'
      return
    }
    const avg = recentLatencies.reduce((a, b) => a + b, 0) / recentLatencies.length
    if (avg < fastThreshold) connectionQuality.value = 'fast'
    else if (avg > slowThreshold) connectionQuality.value = 'slow'
    else connectionQuality.value = 'normal'
  }

  /**
   * 记录一次请求耗时（由 request.ts 拦截器调用）
   */
  function recordLatency(ms: number) {
    recentLatencies.push(ms)
    if (recentLatencies.length > 5) recentLatencies.shift()
    updateConnectionQuality()
  }

  async function performPing() {
    try {
      const start = performance.now()
      await fetch(pingUrl, { method: 'HEAD', cache: 'no-store' })
      const latency = performance.now() - start
      recordLatency(latency)
      if (!isOnline.value) {
        isOnline.value = true
        onlineCallbacks.forEach(cb => cb())
      }
    } catch {
      // ping 失败但不触发离线，避免短暂故障误判
    }
  }

  function startPing() {
    if (pingInterval > 0 && pingTimer === null) {
      pingTimer = setInterval(performPing, pingInterval)
    }
  }

  function stopPing() {
    if (pingTimer !== null) {
      clearInterval(pingTimer)
      pingTimer = null
    }
  }

  // 浏览器在线/离线事件
  function handleOnline() {
    isOnline.value = true
    onlineCallbacks.forEach(cb => cb())
    // 恢复后立即 ping 一次验证
    performPing()
  }

  function handleOffline() {
    isOnline.value = false
    connectionQuality.value = 'unknown'
    offlineCallbacks.forEach(cb => cb())
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
  }

  startPing()

  function destroy() {
    stopPing()
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
    onlineCallbacks.length = 0
    offlineCallbacks.length = 0
  }

  return {
    /** 当前是否在线 */
    isOnline,
    /** 连接质量评估 */
    connectionQuality,
    /** 记录一次请求耗时 */
    recordLatency,
    /** 网络恢复回调 */
    onOnline: (cb: () => void) => { onlineCallbacks.push(cb) },
    /** 网络断开回调 */
    onOffline: (cb: () => void) => { offlineCallbacks.push(cb) },
    /** 销毁，清理事件监听 */
    destroy,
  }
}

/** 全局单例 */
export let globalNetworkDetector: ReturnType<typeof createNetworkDetector> | null = null

/**
 * 初始化全局网络检测器
 * 在 main.ts 中调用
 */
export function initGlobalNetworkDetector(options?: NetworkDetectorOptions) {
  globalNetworkDetector = createNetworkDetector(options)
  return globalNetworkDetector
}