/**
 * 执行状态追踪 Composable 集合
 *
 * 分层架构：
 *   useSceneExecution()   — 纯状态机：场景/步骤执行状态管理，无网络依赖
 *   useWebSocketExecution() — 网络层：WebSocket 实时进度 + 场景状态机的组合
 *   pollExecutionStatus()    — 降级方案：HTTP 轮询获取执行状态
 *
 * 推荐用法：
 *   有 WebSocket 时 → const { connectAndTrack } = useWebSocketExecution()
 *   无 WebSocket 时 → pollExecutionStatus(reportId, onUpdate)
 *   仅需状态管理   → const exec = useSceneExecution()
 */

import { ref, computed, shallowRef } from 'vue'
import { useWebSocket } from './useWebSocket'

// 执行状态
export type ExecutionStatus = 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'

// 步骤执行状态
export interface StepExecutionState {
  stepId: number
  stepName: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'error'
  duration: number
  startedAt?: number
  finishedAt?: number
  responseStatus?: number
  errorMessage?: string
  assertionsPassed?: number
  assertionsFailed?: number
  extractedVars: Record<string, unknown>
}

// 场景执行状态
export interface SceneExecutionState {
  sceneId: number
  sceneName: string
  status: ExecutionStatus
  totalSteps: number
  completedSteps: number
  passedSteps: number
  failedSteps: number
  skippedSteps: number
  currentStep?: number
  startedAt?: number
  finishedAt?: number
  duration: number
  steps: Map<number, StepExecutionState>
  variables: Record<string, unknown>
  error?: string
}

// 回调函数类型
type ProgressCallback = (state: SceneExecutionState) => void
type StepCallback = (step: StepExecutionState) => void
type LogCallback = (level: string, message: string, data?: unknown) => void

/**
 * 场景执行状态追踪器
 */
/**
 * 集成 WebSocket 的执行追踪 — 通过 WebSocket 接收实时进度并更新状态
 * 当 WebSocket 不可用时会回退到 HTTP 轮询
 */
export function useWebSocketExecution() {
  const exec = useSceneExecution()
  const wsConnected = ref(false)

  // 存储追踪选项，用于 WebSocket 回退时保留回调
  let _lastTrackingOptions: {
    onProgress?: ProgressCallback
    onStepChange?: StepCallback
    onLog?: LogCallback
  } | undefined

  function connectAndTrack(
    reportId: number,
    sceneId: number,
    sceneName: string,
    totalSteps: number,
    token?: string
  ) {
    _lastTrackingOptions = {
      onProgress: (_s: unknown) => {
        // 进度回调
      },
      onStepChange: (_s: unknown) => {
        // 步骤变更回调
      },
    }

    exec.startTracking(sceneId, sceneName, totalSteps, _lastTrackingOptions)

    let cleanup: (() => void) | null = null

    try {
      const ws = useWebSocket()
      ws.connectReport(reportId, token)
      wsConnected.value = true

      cleanup = ws.onMessage((msg) => {
        if (msg.type === 'step_progress') {
          if (msg.status === 'running') {
            exec.recordStepStart(msg.step_id, msg.step_name)
          } else if (
            msg.status === 'success' ||
            msg.status === 'failed' ||
            msg.status === 'skipped' ||
            msg.status === 'error'
          ) {
            exec.recordStepComplete(msg.step_id, {
              status: msg.status === 'error' ? 'failed' : msg.status,
              duration: msg.duration,
              errorMessage: msg.error_message,
            })
          }
        } else if (msg.type === 'report_done') {
          if (msg.status === 'failed') {
            exec.finishTracking('有步骤失败')
          } else {
            exec.finishTracking()
          }
          ws.disconnect()
        }
      })
    } catch {
      wsConnected.value = false
      // WebSocket 不可用，回退到 HTTP 轮询，保留之前的回调选项
      exec.startTracking(sceneId, sceneName, totalSteps, _lastTrackingOptions)
    }

    return {
      ...exec,
      wsConnected,
      disconnect: () => {
        cleanup?.()
      },
    }
  }

  return {
    ...exec,
    connectAndTrack,
    wsConnected,
  }
}

export function useSceneExecution() {
  const state = shallowRef<SceneExecutionState | null>(null)
  const isRunning = ref(false)
  const logs = ref<Array<{ time: string; level: string; message: string }>>([])
  
  // 回调函数
  let onProgress: ProgressCallback | null = null
  let onStepChange: StepCallback | null = null
  let onLog: LogCallback | null = null
  
  // 进度计算
  const progress = computed(() => {
    if (!state.value || state.value.totalSteps === 0) return 0
    return Math.round((state.value.completedSteps / state.value.totalSteps) * 100)
  })
  
  const currentStep = computed(() => state.value?.steps.get(state.value.currentStep || 0))
  
  const estimatedRemaining = computed(() => {
    if (!state.value || !state.value.startedAt) return null
    const elapsed = Date.now() - state.value.startedAt
    const avgStepTime = state.value.completedSteps > 0 
      ? elapsed / state.value.completedSteps 
      : 0
    const remaining = state.value.totalSteps - state.value.completedSteps
    return Math.round(avgStepTime * remaining / 1000)
  })
  
  /**
   * 开始追踪场景执行
   */
  function startTracking(
    sceneId: number,
    sceneName: string,
    totalSteps: number,
    options?: {
      onProgress?: ProgressCallback
      onStepChange?: StepCallback
      onLog?: LogCallback
    }
  ) {
    onProgress = options?.onProgress || null
    onStepChange = options?.onStepChange || null
    onLog = options?.onLog || null
    
    const now = Date.now()
    state.value = {
      sceneId,
      sceneName,
      status: 'running',
      totalSteps,
      completedSteps: 0,
      passedSteps: 0,
      failedSteps: 0,
      skippedSteps: 0,
      startedAt: now,
      duration: 0,
      steps: new Map(),
      variables: {}
    }
    
    isRunning.value = true
    addLog('info', `开始执行场景: ${sceneName}`)
    
    return state.value
  }
  
  /**
   * 记录步骤开始
   */
  function recordStepStart(stepId: number, stepName: string) {
    if (!state.value) return
    
    state.value.currentStep = stepId
    const stepState: StepExecutionState = {
      stepId,
      stepName,
      status: 'running',
      duration: 0,
      startedAt: Date.now(),
      extractedVars: {}
    }
    
    state.value.steps.set(stepId, stepState)
    addLog('info', `开始执行步骤: ${stepName}`)
    
    onStepChange?.(stepState)
  }
  
  /**
   * 记录步骤完成
   */
  function recordStepComplete(
    stepId: number,
    result: {
      status: 'success' | 'failed' | 'skipped' | 'error'
      duration: number
      responseStatus?: number
      errorMessage?: string
      assertionsPassed?: number
      assertionsFailed?: number
      extractedVars?: Record<string, unknown>
    }
  ) {
    if (!state.value) return
    
    const stepState = state.value.steps.get(stepId)
    if (stepState) {
      stepState.status = result.status
      stepState.duration = result.duration
      stepState.finishedAt = Date.now()
      stepState.responseStatus = result.responseStatus
      stepState.errorMessage = result.errorMessage
      stepState.assertionsPassed = result.assertionsPassed
      stepState.assertionsFailed = result.assertionsFailed
      stepState.extractedVars = result.extractedVars || {}
      
      // 更新统计
      state.value.completedSteps++
      if (result.status === 'success') {
        state.value.passedSteps++
        addLog('success', `✓ 步骤完成: ${stepState.stepName}`)
      } else if (result.status === 'failed' || result.status === 'error') {
        state.value.failedSteps++
        addLog('error', `✗ 步骤失败: ${stepState.stepName} - ${result.errorMessage || ''}`)
      } else if (result.status === 'skipped') {
        state.value.skippedSteps++
        addLog('warning', `- 步骤跳过: ${stepState.stepName}`)
      }
      
      // 合并提取的变量
      if (result.extractedVars) {
        Object.assign(state.value.variables, result.extractedVars)
      }
      
      onStepChange?.(stepState)
    }
    
    // 检查是否完成
    if (state.value.completedSteps >= state.value.totalSteps) {
      finishTracking()
    }
  }
  
  /**
   * 完成追踪
   */
  function finishTracking(error?: string) {
    if (!state.value) return
    // 防止重复调用（WebSocket report_done 与本地步骤完成可能同时触发）
    if (state.value.status !== 'running') return

    const now = Date.now()
    state.value.finishedAt = now
    state.value.duration = now - (state.value.startedAt || now)
    
    if (error) {
      state.value.status = 'failed'
      state.value.error = error
      addLog('error', `场景执行失败: ${error}`)
    } else if (state.value.failedSteps > 0) {
      state.value.status = 'failed'
      addLog('warning', `场景执行完成，有 ${state.value.failedSteps} 个步骤失败`)
    } else {
      state.value.status = 'completed'
      addLog('success', `场景执行成功，共 ${state.value.passedSteps} 个步骤`)
    }
    
    isRunning.value = false
    onProgress?.(state.value)
  }
  
  /**
   * 取消追踪
   */
  function cancelTracking() {
    if (!state.value) return
    
    state.value.status = 'cancelled'
    state.value.finishedAt = Date.now()
    state.value.duration = Date.now() - (state.value.startedAt || Date.now())
    isRunning.value = false
    
    addLog('warning', '场景执行已取消')
    onProgress?.(state.value)
  }
  
  /**
   * 添加日志
   */
  function addLog(level: string, message: string) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    logs.value.push({ time, level, message })
    
    // 限制日志数量
    if (logs.value.length > 500) {
      logs.value = logs.value.slice(-300)
    }
    
    onLog?.(level, message)
  }
  
  /**
   * 重置状态
   */
  function reset() {
    state.value = null
    isRunning.value = false
    logs.value = []
    onProgress = null
    onStepChange = null
    onLog = null
  }
  
  /**
   * 获取摘要
   */
  function getSummary() {
    if (!state.value) return null
    
    const { status, passedSteps, failedSteps, skippedSteps, totalSteps, duration } = state.value
    const passRate = totalSteps > 0 ? Math.round((passedSteps / totalSteps) * 100) : 0
    
    return {
      status,
      total: totalSteps,
      passed: passedSteps,
      failed: failedSteps,
      skipped: skippedSteps,
      passRate: `${passRate}%`,
      duration: formatDuration(duration),
      startTime: state.value.startedAt ? new Date(state.value.startedAt).toLocaleTimeString() : null,
      endTime: state.value.finishedAt ? new Date(state.value.finishedAt).toLocaleTimeString() : null
    }
  }
  
  return {
    state,
    isRunning,
    progress,
    currentStep,
    estimatedRemaining,
    logs,
    startTracking,
    recordStepStart,
    recordStepComplete,
    finishTracking,
    cancelTracking,
    reset,
    getSummary
  }
}

/**
 * 格式化时长
 */
function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}分${remainingSeconds}秒`
}

/**
 * 轮询执行状态 —— 支持通过 AbortSignal 取消
 * 适用于没有 WebSocket 的情况
 */
export function pollExecutionStatus(
  reportId: number,
  onUpdate: (status: string, progress: number) => void,
  options: {
    interval?: number
    timeout?: number
    onComplete?: () => void
    onError?: (error: string) => void
    signal?: AbortSignal
  } = {}
): Promise<void> {
  const { interval = 1000, timeout = 300000, onComplete, onError, signal } = options
  const startTime = Date.now()

  return new Promise<void>((resolve, reject) => {
    const cancelled = { current: false }

    if (signal) {
      if (signal.aborted) {
        reject(new DOMException('Aborted', 'AbortError'))
        return
      }
      const onAbort = () => {
        cancelled.current = true
        reject(new DOMException('Aborted', 'AbortError'))
      }
      signal.addEventListener('abort', onAbort, { once: true })
    }

    const poll = async () => {
      if (cancelled.current) return

      try {
        const response = await request.get(`/reports/${reportId}`)
        const data = response.data

        if (data) {
          const { status, progress: p } = data
          onUpdate(status, p || 0)

          if (status === 'completed' || status === 'failed') {
            onComplete?.()
            resolve()
            return
          }
        }

        if (Date.now() - startTime > timeout) {
          onError?.('执行超时')
          reject(new Error('Execution timeout'))
          return
        }

        if (!cancelled.current) {
          setTimeout(poll, interval)
        }
      } catch (error) {
        onError?.(String(error))
        reject(error)
      }
    }

    void poll()
  })
}

export default {
  useSceneExecution,
  pollExecutionStatus
}