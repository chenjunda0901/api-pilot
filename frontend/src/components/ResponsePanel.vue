<template>
  <div class="response-panel" role="region" aria-label="响应结果">
    <!-- ===== 合并元数据栏 + 视图 Tab ===== -->
    <div class="resp-headerbar" v-if="currentResponse" role="status" aria-live="polite">
      <span class="resp-headerbar-status" :class="responseStatusClass">
        {{ currentResponse.response_status }}
      </span>
      <div class="resp-headerbar-tabs" role="tablist" aria-label="响应视图切换">
        <button class="resp-hdr-tab" :class="{ active: respTab === 'pretty' }" @click="respTab = 'pretty'" role="tab" :aria-selected="respTab === 'pretty'" aria-controls="panel-pretty">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          Pretty
        </button>
        <button class="resp-hdr-tab" :class="{ active: respTab === 'raw' }" @click="respTab = 'raw'" role="tab" :aria-selected="respTab === 'raw'" aria-controls="panel-raw">Raw</button>
        <button class="resp-hdr-tab" :class="{ active: respTab === 'headers' }" @click="respTab = 'headers'" role="tab" :aria-selected="respTab === 'headers'" aria-controls="panel-headers">
          <span class="tab-count" v-if="headerCount">{{ headerCount }}</span>
          Headers
        </button>
        <button class="resp-hdr-tab" :class="{ active: respTab === 'cookies' }" @click="respTab = 'cookies'" role="tab" :aria-selected="respTab === 'cookies'" aria-controls="panel-cookies">
          <span class="tab-count" v-if="responseCookies.length">{{ responseCookies.length }}</span>
          Cookies
        </button>
        <button class="resp-hdr-tab" :class="{ active: respTab === 'schema' }" @click="respTab = 'schema'" role="tab" :aria-selected="respTab === 'schema'" aria-controls="panel-schema">Schema</button>
        <button class="resp-hdr-tab" :class="{ active: respTab === 'assertions' }" @click="respTab = 'assertions'" role="tab" :aria-selected="respTab === 'assertions'" aria-controls="panel-assertions">
          <span class="tab-count" v-if="assertionCount">{{ assertionCount }}</span>
          断言
        </button>
      </div>
      <div class="resp-headerbar-meta">
        <span class="resp-headerbar-item">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {{ currentResponse.duration || currentResponse.duration_ms || 0 }}ms
        </span>
        <span class="resp-headerbar-sep"></span>
        <span class="resp-headerbar-item">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          {{ formattedSize }}
        </span>
      </div>
    </div>

    <!-- ===== 空状态 / 加载 / 错误 ===== -->
    <div class="resp-body" v-if="!currentResponse && !loading">
      <div class="response-empty" role="status" aria-label="等待响应">
        <div class="response-empty-icon">
          <CircleAlert :size="32" />
        </div>
        <p class="response-empty-title">还没有发送请求</p>
        <p class="response-empty-desc">填写参数后点击发送，响应结果将显示在这里</p>
        <el-button type="primary" size="small" @click="$emit('send')">发送请求</el-button>
        <div v-if="isMockEnv" class="response-empty-mock">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>当前为 Mock 环境，请求将被拦截并返回预设响应</span>
        </div>
      </div>
    </div>

    <div class="resp-body" v-if="loading">
      <div class="resp-loading">
        <div class="loading-spinner"></div>
        <div class="resp-loading-text">
          <span class="resp-loading-title">请求发送中</span>
          <span class="resp-loading-desc">正在等待服务器响应...</span>
        </div>
      </div>
    </div>

    <div class="resp-body" v-if="currentResponse && currentResponse.response_status === 0 && currentResponse.error">
      <div class="resp-error">
        <div class="resp-error-icon">!</div>
        <div class="resp-error-title">请求失败</div>
        <div class="resp-error-msg">{{ currentResponse.error }}</div>
      </div>
    </div>

    <!-- ===== 响应内容 ===== -->
    <template v-if="currentResponse && !(currentResponse.response_status === 0 && currentResponse.error)">
      <!-- 统一工具栏 -->
      <div class="resp-toolbar" v-if="currentResponse && respTab !== 'headers' && respTab !== 'cookies' && respTab !== 'assertions' && respTab !== 'schema'" role="toolbar" aria-label="响应操作">
        <button class="resp-tool-btn" @click="toggleExpand" :title="expandAll ? '折叠全部' : '展开全部'">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ expandAll ? '折叠全部' : '展开全部' }}
        </button>
        <button class="resp-tool-btn" @click="formatResponseBody" :title="rawFormatted ? '显示原始内容' : '格式化 JSON'" v-if="respTab === 'raw'">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="17" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="17" y1="17" x2="3" y2="18"/></svg>
          {{ rawFormatted ? '原始' : '格式化' }}
        </button>
        <button class="resp-tool-btn" :class="{ 'copy-success': copySuccess }" @click="copyResponseBody" :title="copySuccess ? '已复制' : '复制响应内容'">
          <svg v-if="!copySuccess" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="var(--color-success)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          {{ copySuccess ? '已复制' : '复制' }}
        </button>
        <button class="resp-tool-btn" :class="{ 'copy-success': schemaCopied }" @click="copyJsonSchema" :title="schemaCopied ? '已复制' : '生成 JSON Schema'">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          {{ schemaCopied ? '已复制' : 'Schema' }}
        </button>
        <button class="resp-tool-btn" @click="downloadResponse" title="下载响应">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          下载
        </button>
      </div>

      <!-- Pretty 模式：JSON 折叠树 → 已合并到 ResponseBodyViewer -->
      <ResponseBodyViewer
        v-if="respTab !== 'assertions'"
        :mode="respTab"
        :body-text="bodyText"
        :content-type="contentType"
        :is-json="isJsonBody"
        :is-binary="isBinary"
        :is-html="isHtml"
        :is-xml="isXml"
        :is-text="contentType && contentType.includes('text/')"
        :json-data="parsedJsonBody"
        :truncated-text="truncatedBodyText"
        :formatted-size="formattedBinarySize"
        :content-type-label="contentType"
        :headers="headerArray"
        :cookies="responseCookies"
        :inferred-schema="inferredSchema"
        :expand-all="expandAll"
        :project-id="projectId"
        @extract-variable="onExtractVariable"
        @download="downloadResponse"
        @infer-schema="inferSchema"
      />

      <!-- 断言 模式 → 使用 ResponseAssertionSummary 组件 -->
      <div class="resp-content" v-if="respTab === 'assertions'" role="tabpanel" id="panel-assertions">
        <ResponseAssertionSummary :results="assertionResults" />
      </div>

      <!-- 响应历史导航 -->
      <div v-if="responseHistory.length > 1" class="response-history-nav">
        <button :class="{ disabled: currentHistoryIndex >= responseHistory.length - 1 }"
                @click="currentHistoryIndex++">&larr; 较旧</button>
        <span>{{ currentHistoryIndex + 1 }} / {{ responseHistory.length }}</span>
        <button :class="{ disabled: currentHistoryIndex <= 0 }"
                @click="currentHistoryIndex--">较新 &rarr;</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { CircleAlert } from 'lucide-vue-next'
import { useEnvStore } from '../stores/envStore'
import { msgSuccess, msgError } from '../utils/message'

interface AssertionResult {
  type: string
  operator?: string
  expected: unknown
  actual: unknown
  passed: boolean
  message?: string
}

interface ResponseData {
  response_status: number
  response_body?: string | Record<string, unknown> | null
  response_headers?: Record<string, string> | Array<{ key: string; value: string }>
  duration?: number
  duration_ms?: number
  error?: string
  created_at?: string
  assertions?: AssertionResult[]
  assertion_results?: AssertionResult[]
}

const props = defineProps<{
  response: ResponseData | null
  loading: boolean
  isMockEnv?: boolean
  projectId?: number
}>()

const emit = defineEmits<{
  send: []
  'add-extract-rule': [rule: { variable: string; source: string; type: string; expression: string }]
}>()

const respTab = ref('pretty')
const rawFormatted = ref(true)
const expandAll = ref(true)
// showHtmlPreview removed — unused

// ── 响应历史 ──
interface HistoryEntry {
  id: number
  status: number
  body: unknown
  time: number
  headers?: Record<string, string> | Array<{ key: string; value: string }>
  assertions?: AssertionResult[]
  assertion_results?: AssertionResult[]
  error?: string
}
const responseHistory = ref<HistoryEntry[]>([])
const currentHistoryIndex = ref(0)

const currentResponse = computed(() => {
  if (responseHistory.value.length > 0) {
    const entry = responseHistory.value[currentHistoryIndex.value]
    return {
      ...entry,
      response_status: entry.status,
      response_body: entry.body,
      response_headers: entry.headers,
      duration: entry.time,
      assertions: entry.assertions,
      assertion_results: entry.assertion_results,
      error: entry.error,
    } as ResponseData
  }
  return props.response
})

watch(() => props.response, (newResp) => {
  if (!newResp) return
  const entry: HistoryEntry = {
    id: Date.now(),
    status: newResp.response_status || 0,
    body: newResp.response_body,
    time: newResp.duration || newResp.duration_ms || 0,
    headers: newResp.response_headers,
    assertions: newResp.assertions,
    assertion_results: newResp.assertion_results,
    error: newResp.error,
  }
  responseHistory.value.unshift(entry)
  if (responseHistory.value.length > 5) responseHistory.value.pop()
  currentHistoryIndex.value = 0
}, { immediate: true })

const envStore = useEnvStore()

async function onExtractVariable(payload: { name: string; value: string; path: string }) {
  if (!props.projectId) {
    msgError('无法获取项目 ID')
    return
  }
  try {
    await envStore.addVariable(props.projectId, payload.name, payload.value)
    msgSuccess('变量 {{' + payload.name + '}} 已保存')
    // 同时创建提取规则，后续请求自动更新变量值
    const isHeader = payload.path.startsWith('header.')
    const expression = isHeader
      ? payload.path.replace('header.', '')
      : '$.' + payload.path
    emit('add-extract-rule', {
      variable: payload.name,
      source: isHeader ? 'header' : 'body',
      type: 'jsonpath',
      expression,
    })
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number; data?: { message?: string } } })?.response?.status
    const serverMsg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
    if (status === 404) {
      msgError('环境不存在，请刷新后重试')
    } else if (serverMsg) {
      msgError(serverMsg)
    } else {
      msgError('变量保存失败')
    }
  }
}

// ── 计算响应大小 ──
const formattedSize = computed(() => {
  const body = currentResponse.value?.response_body
  if (!body) return '0 B'
  const raw = typeof body === 'string' ? body : JSON.stringify(body)
  const bytes = new Blob([raw]).size
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
})

// ── 响应 Content-Type ──
const responseContentType = computed(() => {
  const h = currentResponse.value?.response_headers
  if (!h) return ''
  if (Array.isArray(h)) {
    const ct = h.find((item: { key: string; value: string }) => item.key?.toLowerCase() === 'content-type')
    return ct?.value || ''
  }
  return h['content-type'] || ''
})

// ── 判断是否为 JSON ──
const isJsonBody = computed(() => {
  const body = currentResponse.value?.response_body
  if (!body) return false
  if (typeof body === 'object') return true
  try {
    JSON.parse(body)
    return true
  } catch {
    return false
  }
})

// ── 响应体类型推断（基于 Content-Type）──
const _responseBodyType = computed<'json' | 'html' | 'xml' | 'binary' | 'text'>(() => {
  const ct = responseContentType.value.toLowerCase()
  if (ct.includes('application/json') || ct.includes('text/json')) return 'json'
  if (ct.includes('text/html')) return 'html'
  if (ct.includes('text/xml') || ct.includes('application/xml') || ct.includes('+xml')) return 'xml'
  if (ct.includes('application/octet-stream') || ct.includes('image/') || ct.includes('audio/') ||
      ct.includes('video/') || ct.includes('application/pdf') || ct.includes('application/zip') ||
      ct.includes('application/gzip') || ct.includes('application/x-')) return 'binary'
  // 无法从 Content-Type 判断时，尝试 JSON 解析
  if (isJsonBody.value) return 'json'
  return 'text'
})

// ── Content-Type 分类计算属性 ──
const contentType = computed(() => responseContentType.value.toLowerCase())
const isHtml = computed(() => contentType.value.includes('text/html'))
const isXml = computed(() => contentType.value.includes('xml'))
const isBinary = computed(() =>
  contentType.value.includes('octet-stream') ||
  contentType.value.includes('image/') ||
  contentType.value.includes('audio/') ||
  contentType.value.includes('video/')
)
const bodyText = computed(() => {
  const body = currentResponse.value?.response_body
  if (!body) return ''
  return typeof body === 'string' ? body : JSON.stringify(body)
})
const bodySize = computed(() => new Blob([bodyText.value]).size)

// 格式化大小（适合二进制提示）
const formattedBinarySize = computed(() => {
  if (bodySize.value < 1024) return `${bodySize.value} bytes`
  if (bodySize.value < 1024 * 1024) return `${(bodySize.value / 1024).toFixed(1)} KB`
  return `${(bodySize.value / (1024 * 1024)).toFixed(1)} MB`
})

// 截断的文本（未知类型限制 10KB）
const truncatedBodyText = computed(() => {
  const text = bodyText.value
  if (text.length <= 10240) return text
  return text.slice(0, 10240) + '\n\n... (已截断，仅显示前 10KB)'
})

// ── 解析 JSON ──
const parsedJsonBody = computed(() => {
  const body = currentResponse.value?.response_body
  if (!body) return null
  if (typeof body === 'object') return body
  try {
    return JSON.parse(body)
  } catch {
    return null
  }
})

// ── Raw body — getRawBody removed (unused)

// ── 状态码样式（语义色徽章）─
const responseStatusClass = computed(() => {
  const s = currentResponse.value?.response_status
  if (!s || s === 0) return 'status-5xx'
  if (s >= 200 && s < 300) return 'status-2xx'
  if (s >= 300 && s < 400) return 'status-3xx'
  if (s >= 400 && s < 500) return 'status-4xx'
  return 'status-5xx'
})

const _durationClass = computed(() => {
  const d = currentResponse.value?.duration || currentResponse.value?.duration_ms || 0
  if (d < 200) return 'fast'
  if (d > 1000) return 'slow'
  return 'normal'
})

function toggleExpand() {
  expandAll.value = !expandAll.value
}

// ── 响应头处理 ──
const headerArray = computed(() => {
  const h = currentResponse.value?.response_headers
  if (!h) return []
  if (Array.isArray(h)) return h
  return Object.entries(h).map(([key, value]) => ({ key, value }))
})

const headerCount = computed(() => headerArray.value.length)

// ── 统一断言结果（兼容 assertions 和 assertion_results） ──
const assertionResults = computed<AssertionResult[]>(() => {
  const resp = currentResponse.value
  if (!resp) return []
  return resp.assertion_results || resp.assertions || []
})

const assertionCount = computed(() => assertionResults.value.length)
// assertion sub-computed removed (unused — kept assertionCount and assertionResults)

const assertionTypeLabel: Record<string, string> = {
  status: '状态码',
  jsonpath: 'JSONPath',
  regex: '正则匹配',
  header: '响应头',
  response_time: '响应时间',
  body_contains: '包含内容',
}

// ── Cookies 解析 ──
interface CookieInfo {
  name: string
  value: string
  domain?: string
  path?: string
}

const responseCookies = computed((): CookieInfo[] => {
  const h = currentResponse.value?.response_headers
  if (!h) return []

  let setCookieValues: string[] = []
  if (Array.isArray(h)) {
    setCookieValues = h
      .filter((item: { key: string; value: string }) => item.key?.toLowerCase() === 'set-cookie')
      .map((item: { key: string; value: string }) => item.value)
  } else {
    const sc = h['set-cookie']
    if (sc) {
      setCookieValues = Array.isArray(sc) ? sc : [sc]
    }
  }

  return setCookieValues.map(cookieStr => parseSetCookie(cookieStr)).filter(Boolean) as CookieInfo[]
})

function parseSetCookie(cookieStr: string): CookieInfo | null {
  if (!cookieStr) return null
  const parts = cookieStr.split(';').map(s => s.trim())
  const [nameValue, ...attrs] = parts
  if (!nameValue) return null

  const eqIdx = nameValue.indexOf('=')
  if (eqIdx < 0) return null

  const name = nameValue.slice(0, eqIdx).trim()
  const value = nameValue.slice(eqIdx + 1).trim()

  let domain: string | undefined
  let path: string | undefined

  for (const attr of attrs) {
    const lower = attr.toLowerCase()
    if (lower.startsWith('domain=')) {
      domain = attr.slice(7).trim()
    } else if (lower.startsWith('path=')) {
      path = attr.slice(5).trim()
    }
  }

  return { name, value, domain, path }
}

// ── Schema 推断 ──
const inferredSchema = ref<Record<string, unknown> | null>(null)

function inferSchemaFromData(data: unknown): Record<string, unknown> {
  if (data === null) return { type: 'null' }
  if (Array.isArray(data)) return { type: 'array', items: data.length > 0 ? inferSchemaFromData(data[0]) : {} }
  if (typeof data === 'object') {
    const props: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(data as Record<string, unknown>)) {
      props[k] = inferSchemaFromData(v)
    }
    return { type: 'object', properties: props }
  }
  return { type: typeof data }
}

function inferSchema() {
  const body = parsedJsonBody.value
  if (!body) { msgError('响应体非 JSON 格式，无法推断 Schema'); return }
  inferredSchema.value = inferSchemaFromData(body)
  respTab.value = 'schema'
}

// formatJson removed (unused)

// ── 时间格式化 ──
function _formatTime(t: string) {
  if (!t) return ''
  try { return new Date(t).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
  catch { return '' }
}

// ── 操作函数 ──
const copySuccess = ref(false)
const copySuccessTimer = ref<ReturnType<typeof setTimeout> | null>(null)

async function copyResponseBody() {
  const body = currentResponse.value?.response_body
  if (!body) return
  const text = typeof body === 'string' ? body : JSON.stringify(body, null, 2)
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta)
  }
  copySuccess.value = true
  if (copySuccessTimer.value) clearTimeout(copySuccessTimer.value)
  copySuccessTimer.value = setTimeout(() => { copySuccess.value = false }, 2000)
}

// 一键生成 JSON Schema 并复制
const schemaCopied = ref(false)
const schemaCopiedTimer = ref<ReturnType<typeof setTimeout> | null>(null)

interface JsonSchema {
  type: string
  example?: string | number | boolean
  properties?: Record<string, JsonSchema>
  items?: JsonSchema
}

function generateJsonSchema(obj: unknown, depth = 0): JsonSchema {
  if (depth > 10) return { type: 'object' }
  if (obj === null) return { type: 'null' }
  if (typeof obj === 'string') return { type: 'string', example: obj.length > 50 ? obj.slice(0, 50) + '...' : obj }
  if (typeof obj === 'number') return { type: Number.isInteger(obj) ? 'integer' : 'number', example: obj }
  if (typeof obj === 'boolean') return { type: 'boolean', example: obj }
  if (Array.isArray(obj)) {
    if (obj.length === 0) return { type: 'array', items: {} }
    const firstItem = obj[0]
    return { type: 'array', items: firstItem !== undefined ? generateJsonSchema(firstItem, depth + 1) : {} }
  }
  if (typeof obj === 'object') {
    const properties: Record<string, JsonSchema> = {}
    for (const [key, value] of Object.entries(obj)) {
      properties[key] = generateJsonSchema(value, depth + 1)
    }
    return { type: 'object', properties }
  }
  return {}
}

async function copyJsonSchema() {
  const body = currentResponse.value?.response_body
  if (!body) return
  const obj = typeof body === 'string' ? (() => { try { return JSON.parse(body) } catch { return null } })() : body
  if (!obj) { msgError('响应体非 JSON 格式，无法生成 Schema'); return }
  const schema = generateJsonSchema(obj)
  const text = JSON.stringify(schema, null, 2)
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta)
  }
  schemaCopied.value = true
  msgSuccess('JSON Schema 已生成并复制')
  if (schemaCopiedTimer.value) clearTimeout(schemaCopiedTimer.value)
  schemaCopiedTimer.value = setTimeout(() => { schemaCopied.value = false }, 2500)
}

function downloadResponse() {
  const body = currentResponse.value?.response_body
  if (!body) return
  const text = typeof body === 'string' ? body : JSON.stringify(body, null, 2)
  const blob = new Blob([text], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `response_${Date.now()}.json`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  msgSuccess('响应已下载')
}

function formatResponseBody() {
  const body = currentResponse.value?.response_body
  if (!body) return
  try {
    const raw = typeof body === 'string' ? body : JSON.stringify(body)
    JSON.parse(raw)
    rawFormatted.value = !rawFormatted.value
    msgSuccess(rawFormatted.value ? '已格式化' : '已显示原始内容')
  } catch {
    msgError('非 JSON 格式，无法格式化')
  }
}

onBeforeUnmount(() => {
  if (copySuccessTimer.value) clearTimeout(copySuccessTimer.value)
  if (schemaCopiedTimer.value) clearTimeout(schemaCopiedTimer.value)
})
</script>

<style scoped>
.response-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.resp-headerbar {
  display: flex;
  align-items: center;
  gap: 0;
  height: 32px;
  flex-shrink: 0;
  padding: 0 var(--space-3);
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
}

/* ===== 合并 headerbar：状态徽章 | Tab | 元数据 ===== */

/* 左侧状态码 */
.resp-headerbar-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 10px;
  height: 24px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.status-2xx { background: var(--grad-status-2xx); color: var(--success); font-weight: 700; }
.status-3xx { background: var(--grad-status-3xx); color: var(--info); font-weight: 700; }
.status-4xx { background: var(--grad-status-4xx); color: var(--warning); font-weight: 700; }
.status-5xx { background: var(--grad-status-5xx); color: var(--error); font-weight: 700; }

/* 中间 Tab 区 */
.resp-headerbar-tabs {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: center;
  gap: 0;
  height: 100%;
}
.resp-hdr-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 12px;
  height: 100%;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.resp-hdr-tab svg { opacity: 0.75; }
.resp-hdr-tab svg { opacity: 1; }
.resp-hdr-tab.active {
  color: var(--primary-700);
  border-bottom-color: var(--primary-500);
  font-weight: var(--weight-semibold);
}

/* 右侧元数据 */
.resp-headerbar-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.resp-headerbar-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}
.resp-headerbar-item svg { opacity: 0.75; }
.resp-headerbar-item.fast { color: var(--success-text); }
.resp-headerbar-item.slow { color: var(--warning-text); }

/* 元数据圆点分隔 */
.resp-headerbar-sep {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--text-muted);
  opacity: 0.65;
}

/* 标签计数 */
.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--surface-nested);
  color: var(--text-muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  order: 1;
  font-family: var(--font-mono);
}

/* ===== 内容区 ===== */
.resp-content {
  flex: 1;
  overflow: auto;
  min-height: 200px;
}
.resp-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* ===== 工具栏 — 增强 ===== */
.resp-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  height: 36px;
}
.copy-success { color: var(--success-text); }
.copy-success svg { animation: checkPop 0.3s var(--ease-spring); }
@keyframes checkPop {
  0% { transform: scale(0.5); opacity: 0; }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); opacity: 1; }
}

.resp-tool-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
  height: 30px;
}
.resp-tool-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-default);
}
.resp-tool-btn:active { transform: scale(0.97); }

/* ===== Pretty body ===== */
.resp-pretty-body { padding: 0 var(--space-2); }

/* ===== Raw wrapper ===== */
.resp-raw-wrapper { position: relative; }

/* ===== 非 JSON 提示 ===== */
.resp-nonjson-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  margin: var(--space-2);
  background: var(--color-warning-alpha-08);
  border: 1px solid var(--color-warning-alpha-12);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--warning-text);
}

/* ===== 二进制响应提示 ===== */
.resp-binary-hint {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6) var(--space-4);
  margin: var(--space-2);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  justify-content: center;
}
.resp-binary-icon {
  font-size: var(--text-xl);
  opacity: 0.5;
}
.resp-binary-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.resp-nonjson-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.resp-nonjson-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-warning-alpha-12);
  font-weight: var(--weight-bold);
  font-size: var(--text-2xs);
  flex-shrink: 0;
}
.resp-nonjson-ctype {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  font-family: var(--font-mono);
  margin-top: 2px;
}

/* ===== Pretty 模式：非 JSON 内容视图 ===== */
.resp-nonjson-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.resp-text-pre {
  flex: 1;
  margin: var(--space-3);
  padding: var(--space-3);
  background: var(--surface-code);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-primary);
}

.resp-xml-pre {
  /* XML 语法高亮基本样式 */
  color: var(--text-primary);
}

/* HTML 操作按钮 */
.resp-html-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* HTML iframe 预览 */
.resp-html-preview {
  flex: 1;
  width: 100%;
  border: none;
  background: var(--white);
  min-height: 300px;
}

/* 二进制下载链接 */
.resp-download-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--primary-400);
  border-radius: var(--radius-sm);
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.resp-download-link:hover {
  background: var(--primary-500);
  color: var(--text-inverse);
  border-color: var(--primary-500);
}

/* ===== 空状态 — 简洁灵动 ===== */
.response-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-7) var(--space-4);
  color: var(--text-muted);
  gap: var(--space-2);
  text-align: center;
  min-height: 240px;
}
.response-empty-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-2xl);
  background: linear-gradient(145deg, var(--primary-50), var(--primary-100));
  color: var(--primary-500);
  margin-bottom: var(--space-3);
  transition: all var(--duration-slow) var(--ease-smooth);
  box-shadow:
    0 8px 24px -8px var(--color-primary-alpha-20),
    inset 0 1px 0 var(--color-white-alpha-60);
  animation: emptyBreathe 4s ease-in-out infinite;
}
@keyframes emptyBreathe {
  0%, 100% { transform: scale(1); box-shadow: 0 8px 24px -8px var(--color-primary-alpha-20), inset 0 1px 0 var(--color-white-alpha-60); }
  50% { transform: scale(1.04); box-shadow: 0 12px 32px -8px var(--color-primary-alpha-30), inset 0 1px 0 var(--color-white-alpha-80); }
}
.response-empty:hover .response-empty-icon {
  background: linear-gradient(145deg, var(--primary-100), var(--primary-200));
  color: var(--primary-600);
  transform: scale(1.08);
}
.response-empty-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin: 0;
  letter-spacing: -0.01em;
}
.response-empty-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin: 0 0 var(--space-3);
  max-width: 280px;
  line-height: var(--leading-relaxed);
}
.response-empty-mock {
  display: flex; align-items: center; gap: var(--space-2);
  margin-top: var(--space-4);
  padding: var(--space-2) var(--space-4);
  background: var(--color-primary-alpha-08);
  border: 1px solid var(--color-primary-alpha-12);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--primary-600);
}
.resp-loading {
  color: var(--text-muted);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  justify-content: center;
  padding: var(--space-12) var(--space-6);
}

.resp-loading-text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  text-align: left;
}

.resp-loading-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

.resp-loading-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* 加载动画 */
.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 错误 — 增强 ===== */
.resp-error {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: var(--space-12) 24px; text-align: center;
}
.resp-error-icon {
  width: 48px; height: 48px; border-radius: 50%;
  background: var(--color-error-alpha-10); color: var(--error-text);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-2xl); font-weight: var(--weight-bold);
  margin-bottom: var(--space-3);
}
.resp-error-title {
  font-size: var(--text-sm); font-weight: var(--weight-bold);
  color: var(--text-primary); margin-bottom: var(--space-1);
}
.resp-error-msg {
  font-size: var(--text-xs); color: var(--text-muted);
  max-width: 300px; word-break: break-all; line-height: 1.5;
}

/* ===== 空表格 ===== */
.resp-empty-table { padding: var(--space-8); text-align: center; color: var(--text-muted); font-size: var(--text-sm); }

/* ===== Cookies 表格 ===== */
.response-cookies-table { padding: var(--space-3); }
.cookie-row {
  display: grid;
  grid-template-columns: 140px 1fr 180px;
  gap: var(--space-2);
  padding: var(--space-1-5) 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
}
.cookie-name { font-weight: var(--weight-medium); color: var(--primary-600); }
.cookie-value { font-family: var(--font-mono); color: var(--text-secondary); word-break: break-all; }
.cookie-meta { color: var(--text-muted); }

/* ===== Schema 面板 ===== */
.schema-panel { padding: var(--space-3); }
.schema-json {
  background: var(--surface-code);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  max-height: 350px;
  overflow: auto;
  white-space: pre-wrap;
}

/* ===== 断言 — 增强 ===== */
.assertion-list { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-3); }
.assertion-summary {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  margin-bottom: var(--space-1);
}
.assertion-summary-total { color: var(--text-secondary); font-weight: var(--weight-medium); }
.assertion-summary-pass { color: var(--success-text); font-weight: var(--weight-semibold); }
.assertion-summary-fail { color: var(--error-text); font-weight: var(--weight-semibold); }
.assertion-collapse-toggle {
  margin-left: auto;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 1px 8px;
  font-size: var(--text-2xs);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.assertion-collapse-toggle:hover {
  border-color: var(--primary-400);
  color: var(--primary-600);
}
.assertion-item {
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  overflow: hidden;
}
.assertion-item.passed {
  background: var(--assertion-pass-bg);
  border: 1px solid var(--assertion-pass-border);
}
.assertion-item.failed {
  background: var(--assertion-fail-bg);
  border: 1px solid var(--assertion-fail-border);
}
.assertion-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
}
.assertion-icon { flex-shrink: 0; }
.pass-icon { color: var(--success); }
.fail-icon { color: var(--error); }
.assertion-type-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
}
.assertion-message {
  color: var(--text-secondary);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.assertion-detail {
  padding: 0 var(--space-3) var(--space-2) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.assertion-compare {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
}
.compare-label {
  color: var(--text-muted);
  min-width: 28px;
  flex-shrink: 0;
}
.compare-value {
  word-break: break-all;
}
.compare-value.expected {
  color: var(--text-secondary);
}
.compare-value.actual {
  font-weight: var(--weight-semibold);
}
.assertion-item.failed .compare-value.actual {
  color: var(--error-text);
}
.assertion-item.passed .compare-value.actual {
  color: var(--success-text);
}
.assertion-collapsed-hint {
  text-align: center;
  padding: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-2xs);
  font-style: italic;
}
.no-assertions { padding: var(--space-8); text-align: center; color: var(--text-muted); font-size: var(--text-sm); }

/* ===== 历史导航 ===== */
.response-history-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  border-top: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}
.response-history-nav button {
  background: none;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 1px 8px;
  cursor: pointer;
  color: var(--text-secondary);
}
.response-history-nav button:hover:not(.disabled) { border-color: var(--primary-400); color: var(--primary-600); }
.response-history-nav button.disabled { opacity: 0.4; cursor: not-allowed; }

/* ===== Dark Mode ===== */
html.dark .response-panel { background: var(--surface-card); }
html.dark .resp-headerbar {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}
html.dark .resp-headerbar-status { color: var(--text-primary); }
html.dark .resp-headerbar-item { color: var(--text-secondary); }
html.dark .resp-body { background: var(--surface-card); }
html.dark .response-empty { color: var(--text-muted); }
html.dark .response-empty-icon { background: var(--surface-hover); color: var(--text-muted); }
html.dark .response-empty:hover .response-empty-icon { background: var(--color-success-alpha-12); color: var(--primary-400); }
html.dark .response-empty-title { color: var(--text-primary); }
html.dark .response-empty-desc { color: var(--text-secondary); }
html.dark .response-empty-mock {
  background: var(--color-success-alpha-10);
  border-color: var(--color-success-alpha-18);
  color: var(--primary-400);
}
html.dark .resp-error {
  background: var(--error-bg);
  border: 1px solid var(--color-error-alpha-12);
}
html.dark .resp-error-title { color: var(--error); }
html.dark .resp-error-msg { color: var(--text-secondary); }
html.dark .resp-hdr-tab { color: var(--text-secondary); }
html.dark .resp-hdr-tab.active {
  color: var(--primary-300);
  border-bottom-color: var(--primary-400);
}
html.dark .resp-content {
  background: var(--surface-nested);
  color: var(--text-primary);
}
html.dark .resp-toolbar { background: var(--surface-nested); }
html.dark .resp-loading { color: var(--text-muted); }
html.dark .loading-spinner { border-color: var(--border-subtle); border-top-color: var(--primary-400); }

/* ===== Dark Mode：非 JSON 视图 ===== */
html.dark .resp-text-pre {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
  color: var(--text-primary);
}
html.dark .resp-html-preview { background: var(--surface-card); }
html.dark .resp-download-link {
  background: var(--color-primary-alpha-12);
  border-color: var(--primary-500);
  color: var(--primary-300);
}
html.dark .resp-download-link:hover {
  background: var(--primary-500);
  color: var(--text-on-primary);
}
</style>
