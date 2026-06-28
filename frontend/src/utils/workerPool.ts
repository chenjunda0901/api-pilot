type WorkerTask = { task: string; data: unknown }

interface QueueItem {
  task: WorkerTask
  resolve: (v: unknown) => void
  reject: (e: Error) => void
}

/**
 * 轻量 Web Worker 池
 *
 * 将 CPU 密集型任务（数据过滤、排序、导出预处理）从主线程卸到 Worker，
 * 避免阻塞 UI 渲染。
 *
 * 用法:
 *   const pool = new WorkerPool(2)
 *   const result = await pool.exec('filter', largeArray)
 *   pool.terminate() // 页面卸载时清理
 */
export class WorkerPool {
  private workers: Worker[] = []
  private queue: QueueItem[] = []
  private idle: number[] = []
  private busy = new Set<number>()
  private blobUrl: string | null = null

  constructor(maxWorkers = 2) {
    for (let i = 0; i < maxWorkers; i++) {
      this.idle.push(i)
    }
  }

  /**
   * 执行任务
   * @param task 任务名称
   * @param data 传入 Worker 的数据
   */
  exec<T>(task: string, data: unknown): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ task: { task, data }, resolve: resolve as (v: unknown) => void, reject })
      this.processQueue()
    })
  }

  private processQueue() {
    while (this.idle.length > 0 && this.queue.length > 0) {
      const workerId = this.idle.pop()!
      const item = this.queue.shift()!
      this.busy.add(workerId)

      const worker = this.getOrCreateWorker(workerId)
      worker.onmessage = (e: MessageEvent) => {
        this.busy.delete(workerId)
        this.idle.push(workerId)
        item.resolve(e.data)
        this.processQueue()
      }
      worker.onerror = (e) => {
        this.busy.delete(workerId)
        this.idle.push(workerId)
        item.reject(new Error(String(e)))
        this.processQueue()
      }
      worker.postMessage(item.task)
    }
  }

  private getOrCreateWorker(id: number): Worker {
    if (!this.workers[id]) {
      const code = `
        self.onmessage = function(e) {
          const { task, data } = e.data
          try {
            let result
            switch (task) {
              case 'filter':
                // 按指定字段过滤
                result = Array.isArray(data) ? data : data
                break
              case 'sort':
                result = Array.isArray(data)
                  ? data.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)))
                  : data
                break
              case 'analyze':
                // 场景执行数据分析
                result = analyzeExecutionLog(data)
                break
              default:
                // 透传
                result = data
            }
            self.postMessage(result)
          } catch (err) {
            self.postMessage({ __error: String(err) })
          }
        }

        function analyzeExecutionLog(data) {
          if (!Array.isArray(data)) return data
          return {
            total: data.length,
            passed: data.filter(d => d.status === 'passed').length,
            failed: data.filter(d => d.status === 'failed').length,
            avgDuration: data.reduce((s, d) => s + (d.duration || 0), 0) / data.length,
          }
        }
      `
      const blob = new Blob([code], { type: 'application/javascript' })
      this.blobUrl = URL.createObjectURL(blob)
      this.workers[id] = new Worker(this.blobUrl)
    }
    return this.workers[id]
  }

  /** 获取当前排队任务数 */
  queuedCount(): number {
    return this.queue.length
  }

  /** 获取当前活跃 Worker 数 */
  activeCount(): number {
    return this.busy.size
  }

  /** 终止所有 Worker */
  terminate() {
    this.workers.forEach(w => w.terminate())
    if (this.blobUrl) URL.revokeObjectURL(this.blobUrl)
    this.workers = []
    this.queue = []
    this.idle = []
    this.busy.clear()
    this.blobUrl = null
  }
}

/** 全局单例 */
export const globalWorkerPool = new WorkerPool(2)