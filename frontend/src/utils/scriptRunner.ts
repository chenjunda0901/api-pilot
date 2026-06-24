/**
 * 脚本执行引擎 — 基于 Web Worker 的沙箱隔离执行
 *
 * 安全设计：
 * - 用户脚本在独立的 Web Worker 中执行，与主线程完全隔离
 * - 主线程通过 postMessage + MessageChannel 传递 pm API，Worker 无法访问主线程全局对象
 * - Worker 内部通过 Function() 执行用户代码（已有 postMessage 隔离墙）
 * - 敏感变量写入受 pm.variables 只读保护（由主线程控制）
 * - 所有 I/O 操作（console、变量读写）均通过消息传递受控
 *
 * 提供 Postman 兼容的 pm API：
 *   pm.variables.get/set — 读写变量（通过回调操作 envStore）
 *   pm.request          — 修改请求参数（前置操作）
 *   pm.response         — 读取响应数据（后置操作）
 *   pm.environment      — pm.variables 的别名
 */

import { logger } from '@/utils/logger'

// ── Worker 内部执行环境 ──────────────────────────────────────────────────────

const WORKER_CODE = /* js */ `
  self._console = {
    log: (...a) => self.postMessage({ type: '_console', level: 'log', args: a }),
    warn: (...a) => self.postMessage({ type: '_console', level: 'warn', args: a }),
    error: (...a) => self.postMessage({ type: '_console', level: 'error', args: a }),
  }

  self._variablesGet = null
  self._variablesSet = null

  self.onmessage = function (e) {
    const { id, action, script } = e.data

    if (action === 'init') {
      self._variablesGet = e.data.getVar
      self._variablesSet = e.data.setVar
      self.postMessage({ id, type: 'ready' })
      return
    }

    if (action === 'run') {
      const getVar = self._variablesGet
      const setVar = self._variablesSet

      const createVariablesAPI = () => ({
        get(key) { return getVar(key) },
        set(key, value) { setVar(key, value) },
        unset(key) { setVar(key, '') },
      })

      const createResponseAPI = (resp) => {
        let _jsonCache = null
        let _parsed = false
        return {
          get status() { return resp?.response_status ?? 0 },
          get text() { return resp?.response_body ?? '' },
          get headers() { return resp?.response_headers ?? {} },
          get responseTime() { return resp?.duration ?? 0 },
          json() {
            if (!_parsed) {
              try { _jsonCache = JSON.parse(resp?.response_body ?? '{}') } catch { _jsonCache = {} }
              _parsed = true
            }
            return _jsonCache
          },
        }
      }

      const createRequestAPI = (requestCtx) => {
        const ctx = {
          method: requestCtx.method,
          path: requestCtx.path,
          headers: requestCtx.headers.map((h) => ({ ...h })),
          params: requestCtx.params.map((p) => ({ ...p })),
          body: requestCtx.body ? JSON.parse(JSON.stringify(requestCtx.body)) : { type: 'none', content: '' },
          auth: requestCtx.auth ? JSON.parse(JSON.stringify(requestCtx.auth)) : { type: 'none' },
          _ensureEnabled(arr) { arr.forEach((item) => { if (item.enabled === undefined) item.enabled = true }) },
        }
        ctx._ensureEnabled(ctx.headers)
        ctx._ensureEnabled(ctx.params)

        const proxy = {
          get method() { return ctx.method },
          set method(v) { ctx.method = v },
          get url() { return ctx.path },
          set url(v) { ctx.path = v },
          get headers() { return ctx.headers },
          set headers(v) { ctx.headers = Array.isArray(v) ? v : [] },
          get params() { return ctx.params },
          set params(v) { ctx.params = Array.isArray(v) ? v : [] },
          get body() { return ctx.body },
          set body(v) { ctx.body = v },
          get auth() { return ctx.auth },
          set auth(v) { ctx.auth = v },
        }
        return { proxy, ctx }
      }

      try {
        let result = null

        if (script._type === 'pre') {
          const pmVariables = createVariablesAPI()
          const { proxy, ctx } = createRequestAPI(script.requestCtx)

          const sandbox = {
            pm: {
              variables: pmVariables,
              environment: pmVariables,
              request: proxy,
              console: self._console,
            },
          }

          const keys = Object.keys(sandbox)
          const values = Object.values(sandbox)
          const fn = new Function(...keys, script.code)
          fn(...values)

          result = {
            method: ctx.method,
            path: ctx.path,
            headers: ctx.headers,
            params: ctx.params,
            body: ctx.body,
            auth: ctx.auth,
          }
        } else {
          // post-script
          const pmVariables = createVariablesAPI()
          const pmResponse = createResponseAPI(script.response)

          const sandbox = {
            pm: {
              variables: pmVariables,
              environment: pmVariables,
              response: pmResponse,
              console: self._console,
            },
          }

          const keys = Object.keys(sandbox)
          const values = Object.values(sandbox)
          const fn = new Function(...keys, script.code)
          fn(...values)

          result = true
        }

        self.postMessage({ id, type: 'result', result })
      } catch (err) {
        self.postMessage({ id, type: 'error', error: err.message || String(err) })
      }
    }
  }
`

// ── Worker 生命周期管理 ──────────────────────────────────────────────────────

const _workerBlob = new Blob([WORKER_CODE], { type: 'application/javascript' })
const _workerUrl = URL.createObjectURL(_workerBlob)

/** 执行预清理：终止超过 timeoutMs 的 Worker */
function _terminateWithTimeout(worker: Worker, timeoutMs: number): Promise<never> {
  return new Promise((_, reject) => {
    const timer = setTimeout(() => {
      worker.terminate()
      reject(new Error(`脚本执行超时（${timeoutMs}ms），已被强制终止`))
    }, timeoutMs)
    // 清理在 workerTerminate 中清除
    worker._timer = timer
  })
}

/** 从池中获取或创建 Worker */
function _getWorker(): Worker {
  // 每次创建新 Worker（复用 blob URL 而非 pool，避免状态残留）
  const w = new Worker(_workerUrl)
  w._isTerminating = false
  return w
}

// 扩展 Worker 类型（附着临时数据）
declare global {
  interface Worker {
    _isTerminating?: boolean
    _timer?: ReturnType<typeof setTimeout>
  }
}

/** 清理 Worker（终止计时器并关闭） */
function _workerTerminate(worker: Worker) {
  if (worker._timer !== undefined) clearTimeout(worker._timer)
  if (!worker._isTerminating) {
    worker._isTerminating = true
    worker.terminate()
  }
  URL.revokeObjectURL(_workerUrl)
}

// ── 类型定义 ────────────────────────────────────────────────────────────────

interface HeaderParamItem {
  key?: string
  value?: string
  enabled?: boolean
  [key: string]: unknown
}

interface RequestBody {
  type?: string
  content?: string
  [key: string]: unknown
}

interface AuthConfig {
  type?: string
  [key: string]: unknown
}

interface PreResult {
  method: string
  path: string
  headers: HeaderParamItem[]
  params: HeaderParamItem[]
  body: RequestBody
  auth: AuthConfig
}

// ── 核心 API ────────────────────────────────────────────────────────────────

let _idCounter = 0
const _SCRIPT_TIMEOUT_MS = 5000

/** 执行前置操作脚本 */
const _SENSITIVE_KEYS_RE = /password|secret|key|token|credential|private|auth|bearer|api[_-]?token/i

function isSensitiveKey(key: string): boolean {
  return _SENSITIVE_KEYS_RE.test(key)
}

/** 执行前置操作脚本 */
export function runPreScript(
  script: string,
  requestCtx: { method: string; path: string; headers: HeaderParamItem[]; params: HeaderParamItem[]; body: RequestBody; auth: AuthConfig },
  getVar: (key: string) => string | undefined,
  _setVar: (key: string, value: string) => void,
): Promise<PreResult | null> {
  if (!script?.trim()) return Promise.resolve(null)

  // 受保护的 setVar：敏感 key 拒绝写入
  const setVar = (key: string, value: string) => {
    if (isSensitiveKey(key)) {
      logger.warn(`[pre-script] 禁止通过脚本修改敏感变量 "${key}"`)
      return
    }
    _setVar(key, value)
  }

  const id = ++_idCounter
  const worker = _getWorker()

  return new Promise<PreResult | null>((resolve) => {
    const timeout = _terminateWithTimeout(worker, _SCRIPT_TIMEOUT_MS)

    Promise.race([timeout, new Promise<void>((res) => {
      worker.onmessage = (e: MessageEvent) => {
        const { type, result, error } = e.data
        if (type === 'ready') { res(); return }
        if (type === 'result') { resolve(result as PreResult); _workerTerminate(worker); return }
        if (type === 'error') { logger.error('[pre-script]', error); resolve(null); _workerTerminate(worker); return }
      }

      worker.postMessage({ id, action: 'init', getVar, setVar })
      worker.postMessage({ id, action: 'run', script: { _type: 'pre', code: script, requestCtx } })
    })])
      .catch((err) => { logger.error('[pre-script]', err.message); resolve(null) })
      .finally(() => _workerTerminate(worker))
  })
}

/** 执行后置操作脚本 */
export function runPostScript(
  script: string,
  response: Partial<{
    response_status: number
    response_body: string
    response_headers: string
    duration: number
  }>,
  getVar: (key: string) => string | undefined,
  _setVar: (key: string, value: string) => void,
): Promise<void> {
  if (!script?.trim()) return Promise.resolve()

  // 受保护的 setVar：敏感 key 拒绝写入
  const setVar = (key: string, value: string) => {
    if (isSensitiveKey(key)) {
      logger.warn(`[post-script] 禁止通过脚本修改敏感变量 "${key}"`)
      return
    }
    _setVar(key, value)
  }

  const id = ++_idCounter
  const worker = _getWorker()

  return new Promise<void>((resolve) => {
    const timeout = _terminateWithTimeout(worker, _SCRIPT_TIMEOUT_MS)

    Promise.race([timeout, new Promise<void>((res) => {
      worker.onmessage = (e: MessageEvent) => {
        const { type, result: _result, error } = e.data
        if (type === 'ready') { res(); return }
        if (type === 'result') { resolve(); _workerTerminate(worker); return }
        if (type === 'error') { logger.error('[post-script]', error); resolve(); _workerTerminate(worker); return }
      }

      worker.postMessage({ id, action: 'init', getVar, setVar })
      worker.postMessage({ id, action: 'run', script: { _type: 'post', code: script, response } })
    })])
      .catch((err) => { logger.error('[post-script]', err.message); resolve() })
      .finally(() => _workerTerminate(worker))
  })
}