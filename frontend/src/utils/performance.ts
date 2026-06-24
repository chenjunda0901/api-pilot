/**
 * 性能监控工具
 * 用于收集和报告前端性能指标
 */

import { logger } from '@/utils/logger'

interface PerformanceMetric {
  name: string
  value: number
  timestamp: number
  url?: string
  userAgent?: string
}

interface PerformanceReport {
  metrics: PerformanceMetric[]
  summary: {
    totalMetrics: number
    averageLoadTime: number
    averageFirstPaint: number
    averageFirstContentfulPaint: number
    averageLargestContentfulPaint: number
    averageTimeToInteractive: number
    averageCumulativeLayoutShift: number
  }
  timestamp: number
}

class PerformanceMonitor {
  private metrics: PerformanceMetric[] = []
  private isInitialized = false

  /**
   * 初始化性能监控
   */
  init(): void {
    if (this.isInitialized) return

    // 监听页面加载性能
    this.observePageLoad()

    // 监听用户交互性能
    this.observeUserInteractions()

    // 监听资源加载性能
    this.observeResourceLoading()

    // 监听长任务
    this.observeLongTasks()

    // 监听布局偏移
    this.observeLayoutShift()

    this.isInitialized = true
  }

  /**
   * 观察页面加载性能
   */
  private observePageLoad(): void {
    // 使用 Performance API 获取页面加载指标
    window.addEventListener('load', () => {
      setTimeout(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        if (navigation) {
          // 页面加载时间
          this.addMetric('page_load_time', navigation.loadEventEnd - navigation.startTime)
          
          // DNS 查询时间
          this.addMetric('dns_lookup_time', navigation.domainLookupEnd - navigation.domainLookupStart)
          
          // TCP 连接时间
          this.addMetric('tcp_connection_time', navigation.connectEnd - navigation.connectStart)
          
          // 请求响应时间
          this.addMetric('request_response_time', navigation.responseEnd - navigation.requestStart)
          
          // DOM 解析时间
          this.addMetric('dom_parse_time', navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart)
          
          // 首次绘制时间
          const paintEntries = performance.getEntriesByType('paint')
          const firstPaint = paintEntries.find(entry => entry.name === 'first-paint')
          if (firstPaint) {
            this.addMetric('first_paint', firstPaint.startTime)
          }
          
          // 首次内容绘制时间
          const firstContentfulPaint = paintEntries.find(entry => entry.name === 'first-contentful-paint')
          if (firstContentfulPaint) {
            this.addMetric('first_contentful_paint', firstContentfulPaint.startTime)
          }
        }
      }, 0)
    })
  }

  /**
   * 观察用户交互性能
   */
  private observeUserInteractions(): void {
    // 监听点击事件
    document.addEventListener('click', (event) => {
      const target = event.target as HTMLElement
      const startTime = performance.now()
      
      // 使用 requestAnimationFrame 测量交互响应时间
      requestAnimationFrame(() => {
        const endTime = performance.now()
        this.addMetric('click_response_time', endTime - startTime, {
          element: target.tagName,
          className: target.className
        })
      })
    })

    // 监听输入事件
    document.addEventListener('input', (event) => {
      const target = event.target as HTMLInputElement
      const startTime = performance.now()
      
      requestAnimationFrame(() => {
        const endTime = performance.now()
        this.addMetric('input_response_time', endTime - startTime, {
          element: target.tagName,
          type: target.type
        })
      })
    })
  }

  /**
   * 观察资源加载性能
   */
  private observeResourceLoading(): void {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'resource') {
          const resourceEntry = entry as PerformanceResourceTiming
          this.addMetric('resource_load_time', resourceEntry.duration, {
            name: resourceEntry.name,
            type: resourceEntry.initiatorType,
            size: resourceEntry.transferSize
          })
        }
      }
    })

    observer.observe({ entryTypes: ['resource'] })
  }

  /**
   * 观察长任务
   */
  private observeLongTasks(): void {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'longtask') {
          this.addMetric('long_task_duration', entry.duration, {
            startTime: entry.startTime
          })
        }
      }
    })

    observer.observe({ entryTypes: ['longtask'] })
  }

  /**
   * 观察布局偏移
   */
  private observeLayoutShift(): void {
    let clsValue = 0
    let clsEntries: PerformanceEntry[] = []

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'layout-shift' && !(entry as unknown as { hadRecentInput?: boolean }).hadRecentInput) {
          clsValue += (entry as unknown as { value: number }).value
          clsEntries.push(entry)
        }
      }
    })

    observer.observe({ entryTypes: ['layout-shift'] })

    // 每5秒报告一次CLS
    setInterval(() => {
      if (clsEntries.length > 0) {
        this.addMetric('cumulative_layout_shift', clsValue, {
          entries: clsEntries.length
        })
        clsValue = 0
        clsEntries = []
      }
    }, 5000)
  }

  /**
   * 添加性能指标
   */
  private addMetric(name: string, value: number, metadata?: Record<string, unknown>): void {
    const metric: PerformanceMetric = {
      name,
      value,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent
    }

    this.metrics.push(metric)

    // 限制存储的指标数量
    if (this.metrics.length > 1000) {
      this.metrics = this.metrics.slice(-500)
    }

    // 开发环境下仅输出慢资源/慢交互日志（避免刷屏）
    if (import.meta.env.DEV) {
      const isSlowResource = name === 'resource_load_time' && value > 200
      const isSlowInteraction = name.includes('response_time') && value > 80
      const isSlowTask = name === 'long_task_duration'
      const isPageMetric = name.startsWith('page_') || name.startsWith('dns_') || name.startsWith('tcp_') || name.startsWith('request_') || name.startsWith('dom_')
      if (isSlowResource || isSlowInteraction || isSlowTask || isPageMetric) {
        logger.info(`[Performance] ${name}: ${value.toFixed(2)}ms`, metadata)
      }
    }
  }

  /**
   * 获取性能报告
   */
  getReport(): PerformanceReport {
    const summary = {
      totalMetrics: this.metrics.length,
      averageLoadTime: this.calculateAverage('page_load_time'),
      averageFirstPaint: this.calculateAverage('first_paint'),
      averageFirstContentfulPaint: this.calculateAverage('first_contentful_paint'),
      averageLargestContentfulPaint: this.calculateAverage('largest_contentful_paint'),
      averageTimeToInteractive: this.calculateAverage('time_to_interactive'),
      averageCumulativeLayoutShift: this.calculateAverage('cumulative_layout_shift')
    }

    return {
      metrics: [...this.metrics],
      summary,
      timestamp: Date.now()
    }
  }

  /**
   * 计算平均值
   */
  private calculateAverage(metricName: string): number {
    const filteredMetrics = this.metrics.filter(m => m.name === metricName)
    if (filteredMetrics.length === 0) return 0
    
    const sum = filteredMetrics.reduce((acc, m) => acc + m.value, 0)
    return sum / filteredMetrics.length
  }

  /**
   * 清除所有指标
   */
  clearMetrics(): void {
    this.metrics = []
  }

  /**
   * 导出指标到服务器
   */
  async exportMetrics(endpoint: string): Promise<void> {
    const report = this.getReport()
    
    try {
      await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(report)
      })
      
      // eslint-disable-next-line no-console
      logger.info('[PerformanceMonitor] Metrics exported successfully')
    } catch (error) {
      logger.error('[PerformanceMonitor] Failed to export metrics:', error)
    }
  }

  /**
   * 获取当前页面的性能指标
   */
  getCurrentPageMetrics(): PerformanceMetric[] {
    return this.metrics.filter(m => m.url === window.location.href)
  }

  /**
   * 获取最慢的资源
   */
  getSlowestResources(count: number = 10): PerformanceMetric[] {
    return this.metrics
      .filter(m => m.name === 'resource_load_time')
      .sort((a, b) => b.value - a.value)
      .slice(0, count)
  }

  /**
   * 获取最慢的交互
   */
  getSlowestInteractions(count: number = 10): PerformanceMetric[] {
    return this.metrics
      .filter(m => m.name.includes('response_time'))
      .sort((a, b) => b.value - a.value)
      .slice(0, count)
  }
}

// 创建单例实例
export const performanceMonitor = new PerformanceMonitor()

// 自动初始化
if (typeof window !== 'undefined') {
  performanceMonitor.init()
}

export default performanceMonitor