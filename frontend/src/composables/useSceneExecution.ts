// frontend/src/composables/useSceneExecution.ts
import { ref, onUnmounted, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import request from '../api/request'
import { EVENTS } from '../constants/events'
import { msgWarning } from '../utils/message'
import { logger } from '../utils/logger'

export interface AssertionDiff {
  type: string
  expected: string
  actual: string
  diff: string
  operator: string
}

export interface AssertionSummary {
  type: string
  op: string
  expected: string
  actual?: string
  passed: boolean
  diff?: AssertionDiff
}

/** 安全将 unknown 值转为字符串，避免 [object Object] */
function safeStringify(v: unknown): string {
  if (v === undefined) return ''
  if (v === null) return 'null'
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (typeof v === 'object') return JSON.stringify(v)
  return ''
}

export interface StepResult {
  name: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped'
  duration_ms?: number
  step_id?: number
  method?: string
  request_url?: string
  request_headers?: string
  request_body?: string
  response_status?: number
  response_headers?: string
  response_body?: string
  assertion_summary?: AssertionSummary[]
  error_message?: string
  script_output?: string
  script_error?: string
  variable_substitutions?: Record<string, string>
}

export interface SceneExecutionOptions {
  projectId: number
  requireLogin: (action: string) => Promise<boolean>
  selectedSceneId: Ref<number | null>
  saveScene: () => Promise<void>
  envId: Ref<number | null>
  eventBus: { emit: (event: string, data?: unknown) => void }
  selectedStepKeys?: Ref<Set<string>>
  datasetId?: Ref<number | null>
}

export interface RawAssertion {
  type?: string
  operator?: string
  expected?: unknown
  actual?: unknown
  passed?: boolean
  status?: string
  diff?: AssertionDiff
}

interface RawReportStep {
  name?: string
  request_method?: string
  request_url?: string
  status?: string
  duration?: number
  scene_step_id?: number
  request_headers?: string
  request_body?: string
  response_status?: number
  response_headers?: string
  response_body?: string
  assertions?: RawAssertion[]
  error_message?: string
  pass_count?: number
  fail_count?: number
  skip_count?: number
  total_count?: number
  script_output?: string
  script_error?: string
}

// WebSocket 消息类型
interface WSMessage {
  type: string
  report_id?: number
  step_index?: number
  total_steps?: number
  step_id?: number
  step_name?: string
  status?: string
  duration?: number
  error_message?: string
  pass_count?: number
  fail_count?: number
  skip_count?: number
}

export function useSceneExecution(options: SceneExecutionOptions) {
  const { projectId, requireLogin, selectedSceneId, saveScene, envId, eventBus, datasetId } = options
  const router = useRouter()

  const execVisible = ref(false)
  const execSceneName = ref('')
  const execSteps = ref<StepResult[]>([])
  const execDoneCount = ref(0)
  const execPassCount = ref(0)
  const execFailCount = ref(0)
  const execSkipCount = ref(0)
  const execTotalSteps = ref(0)
  const execDuration = ref(0)
  const execStatus = ref<'running' | 'success' | 'failed' | 'interrupted' | ''>('')
  const execCurrentStepIndex = ref(-1)

  let execRerunSceneId: number | null = null
  let currentReportId: number | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let ws: WebSocket | null = null
  let useWebSocket = true  // 是否使用 WebSocket（降级时自动切换为轮询）
  let _execTimeoutTimer: ReturnType<typeof setInterval> | null = null
  let connectTimeout: ReturnType<typeof setTimeout> | null = null
  let _execStartTime = 0
  const connected = ref(false)
  const connecting = ref(false)

  function formatAssertions(assertions: RawAssertion[]) {
    if (!assertions || !Array.isArray(assertions)) return []
    return assertions.map((a: RawAssertion) => ({
      type: a.type || 'status',
      op: a.operator || 'eq',
      expected: safeStringify(a.expected),
      actual: safeStringify(a.actual),
      passed: a.passed !== undefined ? a.passed : (a.status === 'pass'),
      diff: a.diff,
    }))
  }

  function connectWebSocket() {
    // 清理旧连接，避免重连时消息重复
    if (ws) {
      ws.onclose = null
      ws.onmessage = null
      ws.onerror = null
      try { ws.close() } catch { /* ignore close error */ }
      ws = null
    }
    // 清理旧的连接超时定时器
    if (connectTimeout) {
      clearTimeout(connectTimeout)
      connectTimeout = null
    }
    connected.value = false

    if (!currentReportId || !useWebSocket) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/report/${currentReportId}`
    try {
      ws = new WebSocket(wsUrl)

      // 连接超时保护：5 秒内未建立连接则降级
      connectTimeout = setTimeout(() => {
        if (!connected.value && useWebSocket) {
          logger.warn('[WebSocket] Connection timeout (5s), falling back to polling')
          useWebSocket = false
          if (ws) {
            ws.onclose = null
            try { ws.close() } catch { /* ignore close error */ }
            ws = null
          }
          if (execStatus.value === 'running') {
            startFallbackPolling()
          }
        }
      }, 5000)

      ws.onopen = () => {
        clearTimeout(connectTimeout!)
        connectTimeout = null
        connected.value = true
        connecting.value = false
        logger.info('[WebSocket] Connected:', currentReportId)
        stopFallbackPolling()
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          if (msg.type === 'step_progress') {
            handleStepProgress(msg)
          } else if (msg.type === 'report_done') {
            handleReportDone(msg)
          }
        } catch (err) {
          logger.error('[WebSocket] Parse message failed:', err)
        }
      }

      ws.onerror = () => {
        logger.warn('[WebSocket] Error, falling back to polling')
        useWebSocket = false
        if (ws) {
          ws.onclose = null  // 防止 onclose 再次触发 startFallbackPolling
          ws.close()
        }
        ws = null
        // 立即启动降级轮询（不等待 onclose）
        if (execStatus.value === 'running') {
          startFallbackPolling()
        }
      }

      ws.onclose = () => {
        ws = null
        // 如果报告未完成，降级为轮询
        if (execStatus.value === 'running') {
          startFallbackPolling()
        }
      }
    } catch (err) {
      logger.warn('[WebSocket] Connection failed:', err)
      useWebSocket = false
    }
  }

  function handleStepProgress(msg: WSMessage) {
    const stepIndex = msg.step_index ?? 0
    const stepName = msg.step_name || `Step ${msg.step_id}`

    if (stepIndex < 0) {
      logger.warn('[WebSocket] Invalid step_index:', stepIndex)
      return
    }

    while (execSteps.value.length <= stepIndex) {
      execSteps.value.push({ status: 'pending', name: `步骤 ${execSteps.value.length + 1}` })
    }

    if (!execSteps.value[stepIndex]) {
      logger.error('[WebSocket] Step data missing at index:', stepIndex)
      return
    }

    const currentStep = execSteps.value[stepIndex]
    const newStatus = msg.status as StepResult['status']

    if (currentStep.status === newStatus && currentStep.step_id === msg.step_id) {
      return
    }

    execSteps.value[stepIndex] = {
      ...currentStep,
      name: stepName,
      status: newStatus,
      duration_ms: (msg.duration || 0) * 1000,
      step_id: msg.step_id,
      error_message: msg.error_message || '',
    }

    if (newStatus === 'running') {
      execCurrentStepIndex.value = stepIndex
    }

    if (newStatus === 'success' || newStatus === 'failed' || newStatus === 'skipped') {
      updateStats()
    }
  }

  function handleReportDone(msg: WSMessage) {
    execStatus.value = msg.status === 'success' ? 'success' : 'failed'
    execDoneCount.value = (msg.pass_count || 0) + (msg.fail_count || 0) + (msg.skip_count || 0)
    execPassCount.value = msg.pass_count || 0
    execFailCount.value = msg.fail_count || 0
    execSkipCount.value = msg.skip_count || 0

    if (ws) {
      ws.close()
      ws = null
    }
    stopFallbackPolling()
  }

  function updateStats() {
    let passed = 0
    let failed = 0
    let skipped = 0

    for (const step of execSteps.value) {
      if (step.status === 'success') passed++
      else if (step.status === 'failed' || step.status === 'error') failed++
      else if (step.status === 'skipped') skipped++
    }

    execPassCount.value = passed
    execFailCount.value = failed
    execSkipCount.value = skipped
    execDoneCount.value = passed + failed + skipped
  }

  function startFallbackPolling() {
    if (pollTimer || !currentReportId) return

    logger.info('[Execution] Falling back to polling')
    let pollCount = 0

    pollTimer = setInterval(async () => {
      if (!currentReportId) return
      pollCount++
      try {
        const res = await request.get(`/projects/${projectId}/reports/${currentReportId}`)
        const data = res.data

        if (data.steps) {
          const newSteps = data.steps.map((s: RawReportStep) => ({
            name: s.name || (s.request_method ? s.request_method + ' ' + (s.request_url || '') : '步骤执行异常'),
            status: (s.status || 'pending') as 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'error',
            duration_ms: (s.duration || 0) * 1000,
            step_id: s.scene_step_id,
            method: s.request_method || '',
            request_url: s.request_url || '',
            request_headers: s.request_headers || '',
            request_body: s.request_body || '',
            response_status: s.response_status || 0,
            response_headers: s.response_headers || '',
            response_body: s.response_body || '',
            assertion_summary: formatAssertions(s.assertions),
            error_message: s.error_message || '',
            script_output: s.script_output || '',
            script_error: s.script_error || '',
          }))

          let changed = false
          if (newSteps.length !== execSteps.value.length) {
            changed = true
          } else {
            for (let i = 0; i < newSteps.length; i++) {
              const oldStep = execSteps.value[i]
              const newStep = newSteps[i]
              if (oldStep.status !== newStep.status ||
                  oldStep.step_id !== newStep.step_id ||
                  oldStep.duration_ms !== newStep.duration_ms) {
                changed = true
                break
              }
            }
          }

          if (changed) {
            execSteps.value = newSteps
            updateStats()
          }
        }

        const prevDone = execDoneCount.value
        execPassCount.value = data.pass_count || 0
        execFailCount.value = data.fail_count || 0
        execSkipCount.value = data.skip_count || 0
        execDoneCount.value = execPassCount.value + execFailCount.value + execSkipCount.value
        execTotalSteps.value = data.total_count || execSteps.value.length
        execDuration.value = data.duration || 0
        execStatus.value = (data.status || 'running') as 'running' | 'success' | 'failed'

        if (prevDone !== execDoneCount.value) {
          updateStats()
        }

        if (data.status === 'success' || data.status === 'failed') {
          stopFallbackPolling()
        }
      } catch (err) {
        logger.error('[Execution] Poll failed:', err)
      }
    }, 1000)
  }

  function stopFallbackPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function stopPolling() {
    if (connectTimeout) {
      clearTimeout(connectTimeout)
      connectTimeout = null
    }
    if (_execTimeoutTimer) {
      clearInterval(_execTimeoutTimer)
      _execTimeoutTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    stopFallbackPolling()
    eventBus.emit(EVENTS.SCENE_COMPLETE)
  }

  function resetExecState(sceneId: number, sceneName: string) {
    // 先清理旧连接
    stopFallbackPolling()
    if (ws) {
      try { ws.close(1000, 'rerun') } catch { /* ignore close error */ }
      ws = null
    }
    if (_execTimeoutTimer) { clearInterval(_execTimeoutTimer); _execTimeoutTimer = null }
    _execStartTime = 0

    useWebSocket = true  // 每次重新执行时重置，允许再次尝试 WebSocket
    connected.value = false
    connecting.value = false

    execRerunSceneId = sceneId
    execSceneName.value = sceneName
    execSteps.value = []
    execDoneCount.value = 0
    execPassCount.value = 0
    execFailCount.value = 0
    execSkipCount.value = 0
    execTotalSteps.value = 0
    execDuration.value = 0
    execStatus.value = 'running'
    execCurrentStepIndex.value = -1
    execVisible.value = true
  }

  async function runScene(s: { id: number; name: string }) {
    if (!await requireLogin('运行测试场景')) return
    if (selectedSceneId.value && s.id === selectedSceneId.value) {
      await saveScene()
    }
    if (!envId.value) {
      msgWarning('请先选择执行环境')
      return
    }
    let url = `/projects/${projectId}/run/scene/${s.id}?env_id=${envId.value}`
    // 有勾选步骤时只运行勾选的步骤
    if (options.selectedStepKeys && options.selectedStepKeys.value.size > 0) {
      // _key 格式为 step_{id}_{index}，用于唯一标识步骤
      const stepIds = [...options.selectedStepKeys.value]
        .map(k => { const m = k.match(/^step_(\d+)_/); return m ? m[1] : null })
        .filter(Boolean)
        .join(',')
      if (stepIds) url += `&step_ids=${stepIds}`
    }
    // 数据驱动：传递数据集 ID
    if (datasetId?.value) {
      url += `&dataset_id=${datasetId.value}`
    }
    const res = await request.post(url)
    currentReportId = res.data.report_id
    resetExecState(s.id, s.name)
    _execStartTime = Date.now()
    _execTimeoutTimer = setInterval(() => {
      if (execStatus.value === 'running' && Date.now() - _execStartTime > 10 * 60 * 1000) {
        msgWarning('前端显示已超时，后端可能仍在执行，请稍后刷新查看报告')
        execStatus.value = 'interrupted'
        // 超时后清理连接和轮询，重置进度指示器
        if (ws) {
          ws.onclose = null
          try { ws.close() } catch { /* ignore */ }
          ws = null
        }
        stopFallbackPolling()
        if (_execTimeoutTimer) { clearInterval(_execTimeoutTimer); _execTimeoutTimer = null }
        eventBus.emit(EVENTS.SCENE_COMPLETE)
      }
    }, 30_000)
    eventBus.emit(EVENTS.SCENE_RUNNING, s.name)
    connectWebSocket()
    if (!useWebSocket) startFallbackPolling()
  }

  async function runSceneStress(s: { id: number; name: string }) {
    if (!await requireLogin('压测场景')) return
    if (selectedSceneId.value && s.id === selectedSceneId.value) {
      await saveScene()
    }
    if (!envId.value) {
      msgWarning('请先选择执行环境')
      return
    }
    const res = await request.post(`/projects/${projectId}/run/scene/${s.id}/stress?env_id=${envId.value}`)
    currentReportId = res.data.report_id
    resetExecState(s.id, s.name)
    _execStartTime = Date.now()
    _execTimeoutTimer = setInterval(() => {
      if (execStatus.value === 'running' && Date.now() - _execStartTime > 10 * 60 * 1000) {
        msgWarning('前端显示已超时，后端可能仍在执行，请稍后刷新查看报告')
        execStatus.value = 'interrupted'
        // 超时后清理连接和轮询，重置进度指示器
        if (ws) {
          ws.onclose = null
          try { ws.close() } catch { /* ignore */ }
          ws = null
        }
        stopFallbackPolling()
        if (_execTimeoutTimer) { clearInterval(_execTimeoutTimer); _execTimeoutTimer = null }
        eventBus.emit(EVENTS.SCENE_COMPLETE)
      }
    }, 30_000)
    eventBus.emit(EVENTS.SCENE_RUNNING, s.name)
    connectWebSocket()
    if (!useWebSocket) startFallbackPolling()
  }

  function viewReport() {
    if (currentReportId) void router.push(`/projects/${projectId}/reports/${currentReportId}`)
    execVisible.value = false
  }

  async function rerunScene() {
    if (execRerunSceneId) {
      const s = { id: execRerunSceneId, name: execSceneName.value }
      execVisible.value = false
      await new Promise(r => setTimeout(r, 300))
      await runScene(s)
    }
  }

  function cancelExecution() {
    stopPolling()
    execVisible.value = false
    msgWarning('已取消')
  }

  function minimizeExecution() {
    execVisible.value = false
  }

  onUnmounted(() => stopPolling())

  return {
    execVisible, execSceneName, execSteps,
    execDoneCount, execPassCount, execFailCount, execSkipCount,
    execTotalSteps, execDuration, execStatus, execCurrentStepIndex,
    runScene, runSceneStress, stopPolling, viewReport,
    rerunScene, cancelExecution, minimizeExecution,
  }
}
