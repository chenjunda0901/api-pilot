/**
 * WebSocket composable — 实时执行进度与通知推送
 *
 * 用法:
 *   const ws = useWebSocket()
 *   ws.connectReport(reportId, token)
 *   ws.onMessage((msg) => { ... })
 *   ws.disconnect()
 */

import { ref, onUnmounted } from 'vue'
import { logger } from '@/utils/logger'

export interface StepProgressMessage {
  type: 'step_progress'
  report_id: number
  step_index: number
  total_steps: number
  step_id: number
  step_name: string
  status: 'running' | 'success' | 'failed' | 'skipped' | 'error'
  duration: number
  error_message: string
  timestamp: string
}

export interface ReportDoneMessage {
  type: 'report_done'
  report_id: number
  status: 'success' | 'failed'
  pass_count: number
  fail_count: number
  total_count: number
  timestamp: string
}

export type WSMessage = StepProgressMessage | ReportDoneMessage

type MessageHandler = (msg: WSMessage) => void

export function useWebSocket() {
  const connected = ref(false)
  const connecting = ref(false)
  let ws: WebSocket | null = null
  let handlers: MessageHandler[] = []
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  // 高频消息节流：step_progress 消息使用 RAF 缓冲
  let _rafId: number | null = null
  let _bufferedMessages: WSMessage[] = []

  function flushMessages() {
    const msgs = _bufferedMessages
    _bufferedMessages = []
    _rafId = null
    // 只取最后一条消息（最新状态 wins）
    if (msgs.length > 0) {
      const lastMsg = msgs[msgs.length - 1]
      handlers.forEach((h) => h(lastMsg))
    }
  }

  /** 获取 WebSocket 基础 URL */
  function getBaseUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}`
  }

  /** 内部连接方法：统一处理 WebSocket 创建、事件绑定、错误处理 */
  function _connect(url: string, options?: { autoReconnect?: { id: number; token: string } }) {
    disconnect()

    if (!url.includes('token=')) {
      logger.warn('[useWebSocket] 缺少 access token，连接已取消')
      return
    }

    connecting.value = true
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      connecting.value = false
    }

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data) as WSMessage
        // 对 step_progress 消息进行 RAF 节流，减少高频更新
        if (msg.type === 'step_progress') {
          _bufferedMessages.push(msg)
          if (!_rafId) {
            _rafId = requestAnimationFrame(flushMessages)
          }
        } else {
          handlers.forEach((h) => h(msg))
        }
      } catch {
        // 忽略非 JSON 消息
      }
    }

    ws.onclose = () => {
      connected.value = false
      connecting.value = false
      ws = null
      // 仅 project 房间自动重连（报告执行是一次性的）
      if (options?.autoReconnect) {
        scheduleReconnect(options.autoReconnect.id, options.autoReconnect.token)
      }
    }

    ws.onerror = () => {
      connected.value = false
      connecting.value = false
    }
  }

  /** 连接到报告执行进度房间 */
  function connectReport(reportId: number, token?: string) {
    const baseUrl = getBaseUrl()
    if (!token) return
    const url = `${baseUrl}/ws/report/${reportId}?token=${encodeURIComponent(token)}`
    _connect(url) // 报告房间不自动重连
  }

  /** 连接到项目事件房间 */
  function connectProject(projectId: number, token?: string) {
    const baseUrl = getBaseUrl()
    if (!token) return
    const url = `${baseUrl}/ws/project/${projectId}?token=${encodeURIComponent(token)}`
    _connect(url, { autoReconnect: { id: projectId, token } })
  }

  function scheduleReconnect(projectId: number, token?: string) {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(() => {
      connectProject(projectId, token)
    }, 3000) // 3 秒后重连
  }

  /** 注册消息处理器 */
  function onMessage(handler: MessageHandler) {
    handlers.push(handler)
    return () => {
      handlers = handlers.filter((h) => h !== handler)
    }
  }

  /** 发送心跳 */
  function ping() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }

  /** 断开连接 */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onclose = null // 防止触发自动重连
      ws.close()
      ws = null
    }
    connected.value = false
    connecting.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    connecting,
    connectReport,
    connectProject,
    onMessage,
    ping,
    disconnect,
  }
}
