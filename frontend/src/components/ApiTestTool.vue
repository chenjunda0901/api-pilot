<template>
  <div class="api-test-tool">
    <!-- 顶部工具栏 -->
    <div class="test-toolbar">
      <div class="toolbar-left">
        <h2>API 测试工具</h2>
      </div>
      <div class="toolbar-right">
        <el-button size="small" text @click="toggleHistory">
          <History :size="14" /> 历史记录
          <span v-if="testHistory.length" class="history-badge">{{ testHistory.length }}</span>
        </el-button>
        <el-button size="small" text @click="toggleImport">
          <Upload :size="14" /> 导入
        </el-button>
        <el-button size="small" text @click="showCurlImport = true">
          <Terminal :size="14" /> 从 cURL 导入
        </el-button>
      </div>
    </div>

    <!-- 导入 cURL 弹窗 -->
    <el-dialog v-model="showCurlImport" title="从 cURL 导入" width="600px">
      <div class="curl-import">
        <el-input
          v-model="curlText"
          type="textarea"
          :rows="8"
          placeholder="粘贴 cURL 命令，例如：curl -X POST https://api.example.com/data -H Content-Type application/json"
        />
        <div class="curl-actions">
          <el-button type="primary" @click="importFromCurl">导入</el-button>
          <el-button @click="showCurlImport = false">取消</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 导入弹窗 -->
    <el-dialog v-model="showImport" title="导入 API" width="500px">
      <div class="import-dialog">
        <el-form label-width="80px">
          <el-form-item label="请求方式">
            <el-select v-model="importData.method" style="width: 100%">
              <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="URL">
            <el-input v-model="importData.url" placeholder="https://api.example.com/endpoint" />
          </el-form-item>
        </el-form>
        <div class="dialog-footer">
          <el-button type="primary" @click="doImport">导入</el-button>
          <el-button @click="showImport = false">取消</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 历史记录侧边栏 -->
    <el-drawer v-model="showHistory" title="测试历史" direction="rtl" size="400px">
      <div class="history-list">
        <div v-if="testHistory.length === 0" class="history-empty">
          <Clock :size="48" class="empty-icon" />
          <p>暂无历史记录</p>
        </div>
        <div
          v-for="item in testHistory"
          :key="item.id"
          class="history-item"
          :class="{ active: currentHistoryId === item.id }"
          @click="loadHistoryItem(item)"
        >
          <div class="history-method" :class="item.request.method.toLowerCase()">
            {{ item.request.method }}
          </div>
          <div class="history-info">
            <div class="history-url">{{ item.request.url }}</div>
            <div class="history-time">{{ formatTime(item.timestamp) }}</div>
          </div>
          <div v-if="item.response" class="history-status" :class="item.response.status < 400 ? 'success' : 'fail'">
            {{ item.response.status }}
          </div>
        </div>
      </div>
      <div v-if="testHistory.length > 0" class="history-footer">
        <el-button size="small" text type="danger" @click="clearHistory">清空历史</el-button>
      </div>
    </el-drawer>

    <!-- 主要内容区 -->
    <div class="test-content">
      <!-- 请求配置区 -->
      <div class="request-panel">
        <div class="request-url-bar">
          <el-select v-model="requestConfig.method" class="method-select">
            <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
          </el-select>
          <el-input
            v-model="requestConfig.url"
            placeholder="输入请求 URL"
            class="url-input"
            @keyup.enter="sendRequest"
          />
          <el-button type="primary" :loading="isLoading" @click="sendRequest">
            <Send :size="14" /> 发送
          </el-button>
        </div>

        <!-- 请求详情标签页 -->
        <el-tabs v-model="activeTab" class="request-tabs">
          <el-tab-pane label="Params" name="params">
            <div class="params-section">
              <div class="kv-list">
                <div v-for="(param, i) in requestConfig.params" :key="i" class="kv-row">
                  <el-checkbox v-model="param.enabled" />
                  <el-input v-model="param.key" placeholder="参数名" />
                  <el-input v-model="param.value" placeholder="参数值" />
                  <el-button text type="danger" aria-label="删除参数" @click="removeParam(i)">
                    <Minus :size="14" />
                  </el-button>
                </div>
                <el-button size="small" @click="addParam">
                  <Plus :size="14" /> 添加参数
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Headers" name="headers">
            <div class="headers-section">
              <div class="kv-list">
                <div v-for="(header, i) in requestConfig.headers" :key="i" class="kv-row">
                  <el-checkbox v-model="header.enabled" />
                  <el-input v-model="header.key" placeholder="请求头" />
                  <el-input v-model="header.value" placeholder="值" />
                  <el-button text type="danger" aria-label="删除请求头" @click="removeHeader(i)">
                    <Minus :size="14" />
                  </el-button>
                </div>
                <el-button size="small" @click="addHeader">
                  <Plus :size="14" /> 添加请求头
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Body" name="body">
            <div class="body-section">
              <el-radio-group v-model="requestConfig.bodyType" class="body-type-selector">
                <el-radio value="json">JSON</el-radio>
                <el-radio value="form">Form</el-radio>
                <el-radio value="raw">Raw</el-radio>
                <el-radio value="none">None</el-radio>
              </el-radio-group>
              <!-- JSON / Raw 体：Monaco Editor -->
              <JsonEditor
                v-if="requestConfig.bodyType === 'json' || requestConfig.bodyType === 'raw'"
                v-model="requestConfig.body"
                :height="220"
                language="json"
              />
              <!-- Form 体：Key-Value 列表 -->
              <div v-else-if="requestConfig.bodyType === 'form'" class="kv-list">
                <div v-for="(param, i) in requestConfig.bodyForm" :key="i" class="kv-row">
                  <el-checkbox v-model="param.enabled" />
                  <el-input v-model="param.key" placeholder="参数名" />
                  <el-input v-model="param.value" placeholder="参数值" />
                  <el-button text type="danger" aria-label="删除表单参数" @click="removeBodyForm(i)">
                    <Minus :size="14" />
                  </el-button>
                </div>
                <el-button size="small" @click="addBodyForm">
                  <Plus :size="14" /> 添加字段
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Auth" name="auth">
            <div class="auth-section">
              <el-radio-group v-model="requestConfig.authType" class="auth-type-selector">
                <el-radio value="none">None</el-radio>
                <el-radio value="basic">Basic Auth</el-radio>
                <el-radio value="bearer">Bearer Token</el-radio>
              </el-radio-group>
              <div v-if="requestConfig.authType === 'basic'" class="auth-form">
                <el-input v-model="requestConfig.authBasic.user" placeholder="用户名" />
                <el-input v-model="requestConfig.authBasic.pass" type="password" placeholder="密码" />
              </div>
              <div v-else-if="requestConfig.authType === 'bearer'" class="auth-form">
                <el-input v-model="requestConfig.authToken" placeholder="Token" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 响应区 -->
      <div class="response-panel">
        <div class="response-header">
          <span class="response-title">响应</span>
          <div v-if="currentResponse" class="response-meta">
            <span class="status-badge" :class="currentResponse.status < 400 ? 'success' : 'error'">
              {{ currentResponse.status }} {{ currentResponse.status_text }}
            </span>
            <span class="duration-badge">{{ currentResponse.duration }}ms</span>
            <span class="size-badge">{{ formatSize(currentResponse.size) }}</span>
          </div>
        </div>

        <!-- 响应标签页 -->
        <el-tabs v-model="responseTab" class="response-tabs">
          <el-tab-pane label="Body" name="body">
            <div v-if="currentResponse" class="response-body">
              <div class="response-toolbar">
                <el-button size="small" text @click="copyResponse">复制</el-button>
                <el-button size="small" text @click="formatResponseBody">格式化</el-button>
              </div>
              <div class="response-content">
                <pre>{{ formattedResponseBody }}</pre>
              </div>
            </div>
            <div v-else class="response-empty">
              <Send :size="48" class="empty-icon" />
              <p>点击发送按钮发送请求</p>
            </div>
          </el-tab-pane>
          <el-tab-pane label="Headers" name="headers">
            <div v-if="currentResponse?.headers" class="response-headers">
              <div v-for="(value, key) in currentResponse.headers" :key="key" class="header-item">
                <span class="header-key">{{ key }}</span>
                <span class="header-value">{{ value }}</span>
              </div>
            </div>
            <div v-else class="response-empty">
              <p>暂无响应头</p>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 错误信息 -->
        <div v-if="currentResponse?.error" class="response-error">
          <AlertCircle :size="16" />
          <span>{{ currentResponse.error }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { msgSuccess, msgError, msgWarning } from '@/utils/message'
import { History, Upload, Terminal, Send, Clock, AlertCircle, Plus, Minus } from 'lucide-vue-next'
import { useApiTest, type TestHistoryItem } from '../composables/useApiTest'
import JsonEditor from './JsonEditor.vue'

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']

const {
  isLoading,
  currentResponse,
  testHistory,
  sendRequest: sendTestRequest,
  parseCurl,
} = useApiTest()

const activeTab = ref('params')
const responseTab = ref('body')
const showCurlImport = ref(false)
const showImport = ref(false)
const showHistory = ref(false)
const curlText = ref('')
const currentHistoryId = ref<string | null>(null)

const requestConfig = reactive({
  method: 'GET',
  url: '',
  params: [] as Array<{ key: string; value: string; enabled: boolean }>,
  headers: [] as Array<{ key: string; value: string; enabled: boolean }>,
  body: '',
  bodyType: 'none',
  bodyForm: [] as Array<{ key: string; value: string; enabled: boolean }>,
  authType: 'none',
  authBasic: { user: '', pass: '' },
  authToken: '',
})

const importData = reactive({ method: 'GET', url: '' })

const formattedResponseBody = computed(() => {
  if (!currentResponse.value?.body) return ''
  try {
    return JSON.stringify(JSON.parse(currentResponse.value.body), null, 2)
  } catch {
    return currentResponse.value.body
  }
})

async function sendRequest() {
  if (!requestConfig.url) {
    msgWarning('请输入请求 URL')
    return
  }
  const headers: Record<string, string> = {}
  requestConfig.headers.forEach(h => {
    if (h.enabled && h.key) headers[h.key] = h.value
  })
  if (requestConfig.authType === 'basic') {
    headers['Authorization'] = `Basic ${btoa(unescape(encodeURIComponent(`${requestConfig.authBasic.user}:${requestConfig.authBasic.pass}`)))}`
  } else if (requestConfig.authType === 'bearer' && requestConfig.authToken) {
    headers['Authorization'] = `Bearer ${requestConfig.authToken}`
  }

  let url = requestConfig.url
  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'https://' + url
  const enabledParams = requestConfig.params.filter(p => p.enabled && p.key)
  if (enabledParams.length > 0) {
    url += (url.includes('?') ? '&' : '?') + new URLSearchParams(enabledParams.map(p => [p.key, p.value])).toString()
  }

  let body = ''
  if (requestConfig.bodyType !== 'none') {
    if (requestConfig.bodyType === 'json') {
      body = requestConfig.body
    } else if (requestConfig.bodyType === 'form') {
      body = new URLSearchParams(requestConfig.bodyForm.filter(p => p.enabled && p.key).map(p => [p.key, p.value])).toString()
    } else {
      body = requestConfig.body
    }
  }

  const response = await sendTestRequest({ url, method: requestConfig.method, headers, body })
  if (response) msgSuccess(`请求成功 (${response.status})`)
}

function importFromCurl() {
  if (!curlText.value) { msgWarning('请输入 cURL 命令'); return }
  const result = parseCurl(curlText.value)
  if (result) {
    requestConfig.method = result.method
    requestConfig.url = result.url
    requestConfig.headers = Object.entries(result.headers || {}).map(([key, value]) => ({ key, value, enabled: true }))
    if (result.body) { requestConfig.body = result.body; requestConfig.bodyType = 'raw' }
    showCurlImport.value = false
    curlText.value = ''
    msgSuccess('成功导入 cURL')
  } else {
    msgError('cURL 解析失败')
  }
}

function doImport() {
  requestConfig.method = importData.method
  requestConfig.url = importData.url
  showImport.value = false
}

function toggleHistory() { showHistory.value = !showHistory.value }
function toggleImport() { showImport.value = !showImport.value }

function loadHistoryItem(item: TestHistoryItem) {
  currentHistoryId.value = item.id
  requestConfig.method = item.request.method
  requestConfig.url = item.request.url
  if (item.request.headers) {
    requestConfig.headers = Object.entries(item.request.headers).map(([key, value]) => ({ key, value, enabled: true }))
  }
  if (item.request.body) { requestConfig.body = item.request.body; requestConfig.bodyType = 'raw' }
}

function clearHistory() { testHistory.value = []; msgSuccess('历史记录已清空') }

function copyResponse() {
  if (currentResponse.value?.body) {
    void navigator.clipboard.writeText(formattedResponseBody.value)
    msgSuccess('已复制到剪贴板')
  }
}

function formatResponseBody() {} // auto-formatted via computed

function formatTime(timestamp: number) { return new Date(timestamp).toLocaleString('zh-CN') }
function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function addParam() { requestConfig.params.push({ key: '', value: '', enabled: true }) }
function removeParam(i: number) { requestConfig.params.splice(i, 1) }
function addHeader() { requestConfig.headers.push({ key: '', value: '', enabled: true }) }
function removeHeader(i: number) { requestConfig.headers.splice(i, 1) }
function addBodyForm() { requestConfig.bodyForm.push({ key: '', value: '', enabled: true }) }
function removeBodyForm(i: number) { requestConfig.bodyForm.splice(i, 1) }
</script>

<style scoped>
/* ==========================================
 * API 测试工具 — 整体布局优化
 * ========================================== */

.api-test-tool {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface-bg);
  color: var(--text-primary);
}

/* 顶部工具栏 */
.test-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-xs);
}

.toolbar-left h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.toolbar-right {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.history-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 var(--space-1-5);
  border-radius: var(--radius-full);
  background: var(--primary-500);
  color: var(--text-inverse);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  margin-left: var(--space-1);
  box-shadow: 0 2px 4px var(--color-primary-alpha-20);
}

/* 主内容区 */
.test-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--space-4);
  gap: var(--space-4);
}

/* 请求面板 */
.request-panel {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
}

.request-url-bar {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-nested);
  align-items: center;
}

.method-select {
  width: 120px;
  flex-shrink: 0;
}

.method-select :deep(.el-input__wrapper) {
  height: var(--height-input-lg);
  border-radius: var(--radius-md);
  font-weight: var(--weight-semibold);
}

.url-input {
  flex: 1;
}

.url-input :deep(.el-input__wrapper) {
  height: var(--height-input-lg);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  box-shadow: 0 0 0 1px var(--border-default) inset;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.url-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--primary-300) inset;
}

.url-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--primary-400) inset;
}

.request-url-bar .el-button {
  height: var(--height-input-lg);
  padding: 0 var(--space-5);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-md);
}

.request-tabs {
  padding: 0 var(--space-4);
}

.request-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.request-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--border-subtle);
}

/* 响应面板 */
.response-panel {
  flex: 1;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-nested);
}

.response-title {
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.response-meta {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.status-badge {
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.status-badge.success {
  background: var(--grad-status-2xx);
  color: var(--success-text);
  border: 1px solid var(--success-border);
}

.status-badge.error {
  background: var(--grad-status-5xx);
  color: var(--error-text);
  border: 1px solid var(--error-border);
}

.duration-badge,
.size-badge {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.response-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.response-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
}

.response-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
}

.response-body {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.response-toolbar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-muted);
}

.response-content {
  flex: 1;
  padding: var(--space-4);
  overflow: auto;
  background: var(--surface-code);
}

.response-content pre {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: var(--text-primary);
}

.response-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: var(--space-3);
}

.response-empty .empty-icon {
  opacity: 0.5;
  animation: emptyFloat 3s ease-in-out infinite;
}

@keyframes emptyFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.response-headers {
  padding: var(--space-4);
}

.header-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-default);
}

.header-item:last-child {
  border-bottom: none;
}

.header-key {
  font-weight: var(--weight-semibold);
  color: var(--primary-600);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  min-width: 140px;
}

.header-value {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  word-break: break-all;
  flex: 1;
}

.response-error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--grad-status-5xx);
  color: var(--error-text);
  border-top: 1px solid var(--error-border);
  font-size: var(--text-sm);
}

/* 历史记录侧边栏 */
.history-list {
  padding: var(--space-3);
}

.history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  color: var(--text-muted);
}

.history-empty .empty-icon {
  margin-bottom: var(--space-3);
  opacity: 0.5;
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  margin-bottom: var(--space-1);
}

.history-item:hover,
.history-item.active {
  background: var(--surface-hover);
}

.history-method {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  min-width: 48px;
  text-align: center;
}

.history-method.get {
  background: var(--method-get-bg);
  color: var(--method-get-text);
}

.history-method.post {
  background: var(--method-post-bg);
  color: var(--method-post-text);
}

.history-method.put {
  background: var(--method-put-bg);
  color: var(--method-put-text);
}

.history-method.delete {
  background: var(--method-delete-bg);
  color: var(--method-delete-text);
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-url {
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
}

.history-time {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

.history-status {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.history-status.success {
  color: var(--success-text);
}

.history-status.fail {
  color: var(--error-text);
}

.history-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}

/* cURL 导入弹窗 */
.curl-import {
  padding: var(--space-3);
}

.curl-actions {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
  margin-top: var(--space-4);
}

/* Key-Value 列表 */
.kv-list {
  padding: var(--space-4);
}

.kv-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.kv-row .el-checkbox {
  width: 24px;
  flex-shrink: 0;
}

.kv-row .el-input {
  flex: 1;
}

.kv-row .el-button {
  flex-shrink: 0;
}

/* 导入弹窗 */
.import-dialog {
  padding: var(--space-3);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

/* 暗色模式增强 */
html.dark .test-toolbar {
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
}

html.dark .request-url-bar {
  background: var(--surface-nested);
  border-bottom-color: var(--border-subtle);
}

html.dark .url-input :deep(.el-input__wrapper) {
  background: var(--surface-input);
}

html.dark .response-header {
  background: var(--surface-nested);
  border-bottom-color: var(--border-subtle);
}

html.dark .response-content {
  background: var(--surface-code);
}

html.dark .history-item:hover,
html.dark .history-item.active {
  background: var(--surface-hover);
}
</style>
