<template>
  <div class="shared-docs-view">
    <!-- 密码验证 -->
    <div v-if="needPassword" class="password-gate">
      <div class="password-card">
        <FileText :size="40" class="doc-icon" />
        <h2>{{ docInfo?.name || t('sharedDocs.defaultDocName') }}</h2>
        <p class="password-hint">{{ t('sharedDocs.passwordHint') }}</p>
        <el-input
          v-model="passwordInput"
          type="password"
          :placeholder="t('sharedDocs.passwordPlaceholder')"
          size="large"
          show-password
          @keydown.enter="submitPassword"
        />
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="submitPassword"
          class="password-submit"
        >
          {{ t('common.confirm') }}
        </el-button>
        <p v-if="passwordError" class="password-error">{{ passwordError }}</p>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <EmptyState
      v-else-if="loadError"
      illustration="api"
      :title="docInfo?.name || t('sharedDocs.loadFailed')"
      :description="loadError"
    >
      <template #action>
        <el-button type="primary" size="small" @click="loadDoc">{{ t('sharedDocs.reload') }}</el-button>
      </template>
    </EmptyState>

    <!-- 文档内容 -->
    <template v-else-if="apis.length > 0">
      <!-- 顶部导航 -->
      <div class="doc-header">
        <div class="doc-header-left">
          <div class="doc-hero-kicker">{{ t('sharedDocs.kicker') }}</div>
          <h1>{{ docInfo?.name || t('sharedDocs.defaultDocName') }}</h1>
          <p class="doc-desc" v-if="docInfo?.description">{{ docInfo.description }}</p>
          <div class="doc-hero-meta">
            <span class="doc-meta-pill">{{ t('sharedDocs.apiCount', { count: apis.length }) }}</span>
            <span class="doc-meta-pill">{{ t('sharedDocs.categoryCount', { count: categories.length }) }}</span>
            <span class="doc-meta-pill">{{ selectedApi?.method || '—' }} {{ selectedApi?.path || t('sharedDocs.waitingSelect') }}</span>
          </div>
          <div class="doc-hero-note">{{ t('sharedDocs.note') }}</div>
        </div>
        <div class="doc-header-right">
          <el-input
            v-model="searchQuery"
            :placeholder="t('sharedDocs.searchPlaceholder')"
            size="small"
            clearable
            style="width: 200px"
          >
            <template #prefix><Search :size="14" /></template>
          </el-input>
        </div>
      </div>

      <div class="doc-body">
        <!-- 左侧：API 目录树 -->
        <aside class="doc-sidebar">
          <div class="sidebar-title">{{ t('sharedDocs.sidebarTitle') }}</div>
          <div class="sidebar-tree">
            <div
              v-for="cat in categoryTree"
              :key="cat.id"
              class="tree-node"
            >
              <div class="cat-label" @click="toggleCategory(cat.id)">
                <span class="cat-arrow">{{ expandedCategories.has(cat.id) ? '▾' : '▸' }}</span>
                <FolderOpen :size="14" class="cat-icon" />
                <span>{{ cat.name }}</span>
                <span class="cat-count">{{ cat.apis.length }}</span>
              </div>
              <div v-if="expandedCategories.has(cat.id)" class="cat-apis">
                <div
                  v-for="api in cat.apis"
                  :key="api.id"
                  class="api-item"
                  :class="{ active: selectedApi?.id === api.id }"
                  @click="selectApi(api)"
                >
                  <span class="method-tag" :class="api.method.toLowerCase()">{{ api.method }}</span>
                  <span class="api-name">{{ api.name }}</span>
                </div>
              </div>
            </div>
            <!-- 无分类接口 -->
            <div v-if="uncategorizedApis.length > 0" class="tree-node">
              <div class="cat-label" @click="showUncategorized = !showUncategorized">
                <span class="cat-arrow">{{ showUncategorized ? '▾' : '▸' }}</span>
                <span>{{ t('sharedDocs.uncategorized') }}</span>
                <span class="cat-count">{{ uncategorizedApis.length }}</span>
              </div>
              <div v-if="showUncategorized" class="cat-apis">
                <div
                  v-for="api in uncategorizedApis"
                  :key="api.id"
                  class="api-item"
                  :class="{ active: selectedApi?.id === api.id }"
                  @click="selectApi(api)"
                >
                  <span class="method-tag" :class="api.method.toLowerCase()">{{ api.method }}</span>
                  <span class="api-name">{{ api.name }}</span>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <!-- 右侧：API 详情 -->
        <main class="doc-main" v-if="selectedApi">
          <div class="api-header">
            <span class="api-method" :class="selectedApi.method.toLowerCase()">{{ selectedApi.method }}</span>
            <span class="api-path">{{ selectedApi.path }}</span>
          </div>
          <h2 class="api-name-title">{{ selectedApi.name }}</h2>
          <p class="api-desc" v-if="selectedApi.description && !selectedApi.description_md">{{ selectedApi.description }}</p>
          <div v-if="selectedApi.description_md" class="api-md-desc" v-html="renderMarkdown(selectedApi.description_md)"></div>

          <!-- 请求参数（含描述） -->
          <div class="section" v-if="parseParams(selectedApi.params).length > 0">
            <h3>{{ t('sharedDocs.queryParams') }}</h3>
            <el-table :data="parseParams(selectedApi.params)" size="small" stripe>
              <el-table-column prop="key" :label="t('sharedDocs.nameCol')" width="160">
                <template #default="{ row }">
                  <code>{{ row.key || row.name || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="type" :label="t('sharedDocs.typeCol')" width="100">
                <template #default="{ row }">
                  {{ row.type || 'string' }}
                </template>
              </el-table-column>
              <el-table-column prop="required" :label="t('sharedDocs.requiredCol')" width="60">
                <template #default="{ row }">
                  <el-tag v-if="row.required" size="small" type="danger">{{ t('sharedDocs.yes') }}</el-tag>
                  <span v-else class="opt">{{ t('sharedDocs.no') }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="value" :label="t('sharedDocs.exampleValueCol')" width="180">
                <template #default="{ row }">
                  <code>{{ row.value || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="description" :label="t('sharedDocs.descriptionCol')" />
            </el-table>
          </div>

          <!-- 请求头 -->
          <div class="section" v-if="parseHeaders(selectedApi.headers).length > 0">
            <h3>{{ t('sharedDocs.requestHeaders') }}</h3>
            <el-table :data="parseHeaders(selectedApi.headers)" size="small" stripe>
              <el-table-column prop="key" :label="t('sharedDocs.nameCol')" width="160" />
              <el-table-column prop="value" :label="t('sharedDocs.valueCol')" width="200">
                <template #default="{ row }">
                  <code>{{ row.value || '-' }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="description" :label="t('sharedDocs.descriptionCol')" />
            </el-table>
          </div>

          <!-- 请求体 -->
          <div class="section" v-if="hasBody(selectedApi.body)">
            <h3>{{ t('sharedDocs.requestBody') }}</h3>
            <div class="body-type">{{ t('sharedDocs.bodyType', { type: getBodyType(selectedApi.body) }) }}</div>
            <pre class="code-block" v-if="getBodyContent(selectedApi.body)">{{ getBodyContent(selectedApi.body) }}</pre>
          </div>

          <!-- 请求示例 -->
          <div class="section" v-if="getRequestExamples(selectedApi).length > 0">
            <h3>{{ t('sharedDocs.requestExample') }}</h3>
            <div v-for="(ex, i) in getRequestExamples(selectedApi)" :key="'req-' + i" class="example-block">
              <div class="example-label">{{ ex.name || t('sharedDocs.exampleLabel', { index: i + 1 }) }}</div>
              <pre class="code-block">{{ formatJson(ex.body) }}</pre>
            </div>
          </div>

          <!-- 认证方式 -->
          <div class="section" v-if="selectedApi.auth_type && selectedApi.auth_type !== 'none'">
            <h3>{{ t('sharedDocs.authType') }}</h3>
            <el-tag>{{ selectedApi.auth_type }}</el-tag>
          </div>

          <!-- 响应示例 -->
          <div class="section" v-if="getResponseExamples(selectedApi).length > 0">
            <h3>{{ t('sharedDocs.responseExample') }}</h3>
            <div v-for="(ex, i) in getResponseExamples(selectedApi)" :key="'res-' + i" class="example-block">
              <div class="example-label">
                {{ ex.name || t('sharedDocs.exampleLabel', { index: i + 1 }) }}
                <span v-if="ex.status_code" class="status-badge" :class="statusClass(ex.status_code)">{{ ex.status_code }}</span>
              </div>
              <pre class="code-block">{{ formatJson(ex.body || ex.content) }}</pre>
            </div>
          </div>

          <!-- 响应 Schema -->
          <div class="section" v-if="selectedApi.response_schema">
            <h3>{{ t('sharedDocs.responseSchema') }}</h3>
            <pre class="code-block">{{ formatJson(selectedApi.response_schema) }}</pre>
          </div>

          <!-- 代码示例 -->
          <div class="section">
            <h3>{{ t('sharedDocs.codeExample') }}</h3>
            <div class="lang-tabs">
              <button
                v-for="lang in languages"
                :key="lang.value"
                class="lang-tab"
                :class="{ active: selectedLang === lang.value }"
                @click="selectedLang = lang.value"
              >
                {{ lang.label }}
              </button>
            </div>
            <pre class="code-block">{{ getCodeSnippet(selectedLang) }}</pre>
          </div>

          <!-- Try it out -->
          <div class="section try-it-section">
            <h3>{{ t('sharedDocs.tryIt') }}</h3>
            <div class="try-it-form">
              <div class="try-it-row">
                <el-select v-model="tryItMethod" size="small" style="width: 110px">
                  <el-option v-for="m in ['GET','POST','PUT','DELETE','PATCH','HEAD','OPTIONS']" :key="m" :label="m" :value="m" />
                </el-select>
                <el-input v-model="tryItUrl" size="small" placeholder="https://api.example.com/path" class="try-it-url" />
                <el-button size="small" type="primary" :loading="tryItLoading" @click="tryItOut">{{ t('sharedDocs.send') }}</el-button>
              </div>
              <div v-if="tryItBody" class="try-it-body">
                <div class="try-it-label">{{ t('sharedDocs.tryItBody') }}</div>
                <el-input v-model="tryItBody" type="textarea" :rows="3" size="small" />
              </div>
              <div v-if="tryItResult" class="try-it-result">
                <div class="try-it-label">{{ t('sharedDocs.tryItResponse') }} <span :class="tryItResult.status < 300 ? 'status-ok' : 'status-err'">{{ tryItResult.status }}</span> ({{ tryItResult.duration }}ms)</div>
                <pre class="code-block">{{ tryItResult.body }}</pre>
              </div>
            </div>
          </div>
        </main>

        <!-- 未选择 API -->
        <main v-else class="doc-main doc-empty">
          <FileText :size="48" class="empty-icon" />
          <p>{{ t('sharedDocs.selectApiHint') }}</p>
        </main>
      </div>
    </template>

    <!-- 空状态 -->
    <EmptyState
      v-else-if="!loading"
      illustration="api"
      :title="docInfo?.name || t('sharedDocs.docNotFound')"
      :description="t('sharedDocs.docExpired')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import request from '../api/request'
import EmptyState from '../components/EmptyState.vue'
import { FileText, Search, FolderOpen } from 'lucide-vue-next'
import DOMPurify from 'dompurify'
import { msgError } from '@/utils/message'

const route = useRoute()
const { t } = useI18n()
const token = computed(() => route.params.token as string)

const loading = ref(false)
const needPassword = ref(false)
const passwordInput = ref('')
const passwordError = ref('')
const loadError = ref('')
const docInfo = ref<Record<string, unknown>>(null)
const apis = ref<Record<string, unknown>[]>([])
const categories = ref<Record<string, unknown>[]>([])
const selectedApi = ref<Record<string, unknown> | null>(null)
const searchQuery = ref('')
const expandedCategories = ref(new Set<number>())
const showUncategorized = ref(false)
const selectedLang = ref('curl')

// Try it out 状态
const tryItMethod = ref('GET')
const tryItUrl = ref('')
const tryItBody = ref('')
const tryItLoading = ref(false)
const tryItResult = ref<{ status: number; duration: number; body: string } | null>(null)

const languages = [
  { value: 'curl', label: 'cURL' },
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'go', label: 'Go' },
  { value: 'java', label: 'Java' },
]

// 选中 API 时初始化 Try it out
watch(selectedApi, (api) => {
  if (api) {
    tryItMethod.value = (api.method as string) || 'GET'
    tryItUrl.value = 'https://api.example.com' + ((api.path as string) || '/')
    tryItBody.value = hasBody(api.body) ? getBodyContent(api.body) : ''
    tryItResult.value = null
  }
})

// 简易 Markdown 渲染（带 DOMPurify XSS 防御）
function renderMarkdown(md: string): string {
  if (!md) return ''
  let html = md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
  // DOMPurify sanitize 深度防御：仅允许 Markdown 渲染的白名单标签
  return DOMPurify.sanitize(html, { ALLOWED_TAGS: ['h1','h2','h3','strong','em','code','br'] })
}

// 目录树构建
const categoryTree = computed(() => {
  const rootCats = categories.value.filter((c) => !c.parent_id)
  return rootCats.map((cat) => ({
    ...cat,
    apis: apis.value.filter(
      (a) => a.category_id === cat.id && matchSearch(a)
    ),
  }))
})

const uncategorizedApis = computed(() => {
  return apis.value.filter((a) => !a.category_id && matchSearch(a))
})

function matchSearch(api: Record<string, unknown>): boolean {
  if (!searchQuery.value) return true
  const q = searchQuery.value.toLowerCase()
  const name = typeof api.name === 'string' ? api.name.toLowerCase() : ''
  const path = typeof api.path === 'string' ? api.path.toLowerCase() : ''
  return name.includes(q) || path.includes(q)
}

function toggleCategory(id: number) {
  const newSet = new Set(expandedCategories.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  expandedCategories.value = newSet
}

function selectApi(api: Record<string, unknown>) {
  selectedApi.value = api
}

function parseParams(params: string | Record<string, unknown>[]): Record<string, unknown>[] {
  if (Array.isArray(params)) return params
  try {
    return JSON.parse(params || '[]')
  } catch {
    return []
  }
}

function parseHeaders(headers: string | Record<string, unknown>[]): Record<string, unknown>[] {
  if (Array.isArray(headers)) return headers
  try {
    return JSON.parse(headers || '[]')
  } catch {
    return []
  }
}

function hasBody(body: unknown): boolean {
  if (!body) return false
  try {
    const t = typeof body === 'string' ? JSON.parse(body) : body
    return t.type && t.type !== 'none' && t.content
  } catch {
    return false
  }
}

function getBodyType(body: unknown): string {
  try {
    const t = typeof body === 'string' ? JSON.parse(body) : body
    return t.type || 'none'
  } catch {
    return 'raw'
  }
}

function getBodyContent(body: unknown): string {
  try {
    const t = typeof body === 'string' ? JSON.parse(body) : body
    return typeof t.content === 'string' ? t.content : JSON.stringify(t.content, null, 2)
  } catch {
    return ''
  }
}

function formatJson(data: unknown): string {
  if (!data) return ''
  try {
    const obj = typeof data === 'string' ? JSON.parse(data) : data
    return JSON.stringify(obj, null, 2)
  } catch {
    return typeof data === 'string' ? data : JSON.stringify(data)
  }
}

function getRequestExamples(api: Record<string, unknown>): Record<string, unknown>[] {
  const examples = api.request_examples
  if (!examples) return []
  if (Array.isArray(examples)) return examples
  try { return JSON.parse(examples) } catch { return [] }
}

function getResponseExamples(api: Record<string, unknown>): Record<string, unknown>[] {
  const examples = api.response_examples
  if (!examples) return []
  if (Array.isArray(examples)) return examples
  try { return JSON.parse(examples) } catch { return [] }
}

function statusClass(code: number | string) {
  const n = Number(code)
  if (n >= 200 && n < 300) return 'status-2xx'
  if (n >= 300 && n < 400) return 'status-3xx'
  if (n >= 400 && n < 500) return 'status-4xx'
  if (n >= 500) return 'status-5xx'
  return ''
}

function getCodeSnippet(lang: string): string {
  if (!selectedApi.value) return ''
  const api = selectedApi.value
  const url = (api.path as string) || '/'
  const method = (api.method as string) || 'GET'

  switch (lang) {
    case 'curl':
      return `curl -X ${method} "https://api.example.com${url}"${
        api.headers ? parseHeaders(api.headers as string | Record<string, unknown>[]).map((h) => `\n  -H "${h.key}: ${h.value}"`).join('') : ''
      }${
        hasBody(api.body) ? `\n  -d '${getBodyContent(api.body)}'` : ''
      }`
    case 'python':
      return `import requests\n\nurl = "https://api.example.com${url}"\n${
        hasBody(api.body) ? `data = ${getBodyContent(api.body)}\n` : ''
      }response = requests.${method.toLowerCase()}(
    url${
      hasBody(api.body) ? ',\n    json=data' : ''
    }${
      parseHeaders(api.headers as string | Record<string, unknown>[]).length > 0 ? ',\n    headers=headers' : ''
    }
)\nprint(response.json())`
    case 'javascript':
      return `fetch("https://api.example.com${url}", {
  method: "${method}",${
    hasBody(api.body) ? `\n  body: JSON.stringify(${getBodyContent(api.body)}),` : ''
  }
})\n  .then(res => res.json())\n  .then((data) => void data)`
    case 'go':
      return `package main\n\nimport (\n\t"fmt"\n\t"io/ioutil"\n\t"net/http"\n)\n\nfunc main() {\n\turl := "https://api.example.com${url}"\n\treq, _ := http.NewRequest("${method}", url, nil)\n\tclient := &http.Client{}\n\tresp, _ := client.Do(req)\n\tbody, _ := ioutil.ReadAll(resp.Body)\n\tfmt.Println(string(body))\n}`
    case 'java':
      return `import java.net.http.*;
import java.net.URI;

HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com${url}"))
    .${method === 'GET' ? 'GET()' : method === 'POST' ? 'POST(HttpRequest.BodyPublishers.noBody())' : 'method("' + method + '", HttpRequest.BodyPublishers.noBody())'}
    .build();
client.send(request, HttpResponse.BodyHandlers.ofString());`
    default:
      return t('sharedDocs.unsupportedLang')
  }
}

async function tryItOut() {
  if (!tryItUrl.value) return
  tryItLoading.value = true
  tryItResult.value = null
  const start = Date.now()
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)
  try {
    const resp = await fetch(tryItUrl.value, {
      method: tryItMethod.value,
      headers: { 'Content-Type': 'application/json' },
      body: ['POST', 'PUT', 'PATCH'].includes(tryItMethod.value) && tryItBody.value ? tryItBody.value : undefined,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    const text = await resp.text()
    let body = text
    try { body = JSON.stringify(JSON.parse(text), null, 2) } catch { /* not JSON */ }
    tryItResult.value = { status: resp.status, duration: Date.now() - start, body }
  } catch (e: unknown) {
    clearTimeout(timeoutId)
    let message: string
    if (e instanceof DOMException && e.name === 'AbortError') {
      message = t('sharedDocs.requestTimeout')
    } else if (e instanceof TypeError && e.message.includes('Failed to fetch')) {
      message = t('sharedDocs.networkError')
    } else if (e instanceof Error) {
      message = t('sharedDocs.requestFailed', { message: e.message || t('sharedDocs.unknownError') })
    } else {
      message = t('sharedDocs.requestFailedUnknown')
    }
    tryItResult.value = { status: 0, duration: Date.now() - start, body: message }
  } finally {
    tryItLoading.value = false
  }
}

async function loadDoc() {
  loading.value = true
  loadError.value = ''
  try {
    const res = passwordInput.value
      ? await request.post(`/shared/docs/${token.value}`, { password: passwordInput.value })
      : await request.get(`/shared/docs/${token.value}`)
    if (res.data?.need_password) {
      needPassword.value = true
      docInfo.value = res.data
      loading.value = false
      return
    }
    needPassword.value = false
    docInfo.value = { name: res.data.name, description: res.data.description }
    apis.value = res.data.apis || []
    categories.value = res.data.categories || []
    // 自动展开第一个分类
    if (categories.value.length > 0) {
      const firstId = categories.value[0]?.id ?? 0
      if (firstId) expandedCategories.value = new Set([...expandedCategories.value, firstId])
    }
    // 自动选中第一个 API
    if (apis.value.length > 0) {
      selectedApi.value = apis.value[0] ?? null
    }
    // 密码验证成功后，将密码保留在内存变量中（不写入 sessionStorage，
    // 防止 XSS 或浏览器扩展窃取明文密码）
    // 页面生命周期内密码通过 submitPassword 闭包持有，刷新页面后需重新输入
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } }; message?: string }
    loadError.value = err?.response?.data?.message || err?.message || t('sharedDocs.loadFailedMsg')
    apis.value = []
    categories.value = []
    selectedApi.value = null
    if (!needPassword.value) {
      msgError(loadError.value)
    }
  } finally {
    loading.value = false
  }
}

async function submitPassword() {
  if (!passwordInput.value) {
    passwordError.value = t('sharedDocs.inputPassword')
    return
  }
  passwordError.value = ''
  await loadDoc()
}

onMounted(() => {
  if (token.value) {
    void loadDoc()
  }
})
</script>

<style scoped>
/* ===== 页面容器：全屏高度，纵向布局 ===== */
.shared-docs-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--surface-page);
}

/* ===== 密码验证遮罩层 ===== */
.password-gate {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--surface-bg);
}

/* 密码输入卡片 */
.password-card {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-9);
  width: 360px;
  text-align: center;
  box-shadow: var(--shadow-card);
}

.password-card .doc-icon {
  color: var(--primary-400);
  margin-bottom: var(--space-3);
}

.password-card h2 {
  font-size: var(--text-lg2);
  margin-bottom: var(--space-2);
  color: var(--text-primary);
}

.password-hint {
  color: var(--text-muted);
  margin-bottom: var(--space-6);
  font-size: var(--text-base);
}

.password-error {
  color: var(--error);
  font-size: var(--text-sm);
  margin-top: var(--space-2);
}

.password-submit {
  margin-top: var(--space-4);
  width: 100%;
}

/* ===== 加载骨架屏 ===== */
.loading-state {
  padding: var(--space-9);
  max-width: 800px;
  margin: 0 auto;
}

/* ===== 文档顶部 Hero 区域 ===== */
.doc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  border-bottom: 2px solid var(--border-subtle);
  background: linear-gradient(135deg, var(--color-primary-alpha-04) 0%, var(--surface-card) 60%, var(--color-primary-alpha-04) 100%);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.doc-header-left {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.doc-header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* Kicker — 与 PageLayout .page-kicker 保持一致 */
.doc-hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--primary-600);
}

.doc-header h1 {
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  margin: 0;
  color: var(--text-primary);
}

.doc-desc {
  color: var(--text-muted);
  font-size: var(--font-size-sm);
  margin-top: var(--space-1);
}

/* Hero 区域元信息行 */
.doc-hero-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  flex-wrap: wrap;
}

.doc-meta-pill {
  display: inline-flex;
  align-items: center;
  font-size: var(--font-size-2xs);
  color: var(--text-secondary);
  background: var(--surface-nested);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-full);
}

.doc-hero-note {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

/* ===== 文档主体：左侧目录 + 右侧详情 ===== */
.doc-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧 API 目录树 ===== */
.doc-sidebar {
  width: 280px;
  border-right: 1px solid var(--border-subtle);
  overflow-y: auto;
  padding: var(--space-3) 0;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  color: var(--text-muted);
  padding: var(--space-2) var(--space-4);
  letter-spacing: var(--tracking-wide);
}

.tree-node {
  margin-bottom: var(--space-0-5);
}

/* 分类标签行 */
.cat-label {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1-5) var(--space-4);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  user-select: none;
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.cat-label:hover {
  background: var(--surface-hover);
}

.cat-arrow {
  width: var(--space-3);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
}

.cat-icon {
  color: var(--warning);
  flex-shrink: 0;
}

/* 分类内接口计数徽标 */
.cat-count {
  margin-left: auto;
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  background: var(--surface-nested);
  padding: 0 var(--space-1-5);
  border-radius: var(--radius-full);
}

.cat-apis {
  padding-left: var(--space-2);
}

/* API 列表项 */
.api-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-7);
  cursor: pointer;
  border-radius: var(--radius-sm);
  margin: var(--space-0-5) var(--space-2);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.api-item:hover {
  background: var(--surface-hover);
}

.api-item.active {
  background: var(--primary-50);
}

/* HTTP 方法标签（目录树内） */
.method-tag {
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-bold);
  padding: var(--space-0-5) var(--space-1);
  border-radius: var(--radius-xs);
  min-width: 32px;
  text-align: center;
  flex-shrink: 0;
}

.method-tag.get { background: var(--method-get-bg); color: var(--method-get-text); }
.method-tag.post { background: var(--method-post-bg); color: var(--method-post-text); }
.method-tag.put { background: var(--method-put-bg); color: var(--method-put-text); }
.method-tag.delete { background: var(--method-delete-bg); color: var(--method-delete-text); }
.method-tag.patch { background: var(--method-patch-bg); color: var(--method-patch-text); }
.method-tag.head { background: var(--method-head-bg); color: var(--method-head-text); }
.method-tag.options { background: var(--method-options-bg); color: var(--method-options-text); }

.api-name {
  font-size: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 右侧 API 详情区 ===== */
.doc-main {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5) var(--space-6);
  max-width: var(--layout-max-width);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* 未选择 API 时的空状态 */
.doc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.doc-empty .empty-icon {
  opacity: 0.4;
  margin-bottom: var(--space-3);
}

/* API 方法 + 路径行 */
.api-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

/* API 方法徽章（详情区，比目录树更大） */
.api-method {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-sm);
}

.api-method.get { background: var(--method-get-bg); color: var(--method-get-text); border: 1px solid var(--method-get-border); }
.api-method.post { background: var(--method-post-bg); color: var(--method-post-text); border: 1px solid var(--method-post-border); }
.api-method.put { background: var(--method-put-bg); color: var(--method-put-text); border: 1px solid var(--method-put-border); }
.api-method.delete { background: var(--method-delete-bg); color: var(--method-delete-text); border: 1px solid var(--method-delete-border); }
.api-method.patch { background: var(--method-patch-bg); color: var(--method-patch-text); border: 1px solid var(--method-patch-border); }
.api-method.head { background: var(--method-head-bg); color: var(--method-head-text); border: 1px solid var(--method-head-border); }
.api-method.options { background: var(--method-options-bg); color: var(--method-options-text); border: 1px solid var(--method-options-border); }

.api-path {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  color: var(--text-primary);
}

.api-name-title {
  font-size: var(--text-2xl);
  margin: 0 0 var(--space-2) 0;
}

.api-desc {
  color: var(--text-muted);
  font-size: var(--text-base);
  margin-bottom: var(--space-6);
}

/* 详情区各段落（参数表、请求体、响应示例等） */
.section {
  margin-bottom: var(--space-7);
}

.section h3 {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  margin-bottom: var(--space-3);
  color: var(--text-primary);
}

.body-type {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

/* 代码块（请求体、响应示例、代码片段） */
.code-block {
  background: var(--surface-code);
  color: var(--text-primary);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: var(--leading-relaxed);
}

.opt {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* 代码示例语言切换标签 */
.lang-tabs {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.lang-tab {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border-default);
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-smooth);
}

.lang-tab:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.lang-tab.active {
  background: var(--primary-500);
  color: var(--text-inverse);
  border-color: var(--primary-500);
}

/* ===== 暗色模式适配 ===== */
html.dark .password-card {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-card);
}

html.dark .doc-header {
  background: linear-gradient(135deg, var(--color-primary-alpha-06) 0%, var(--surface-card) 60%, var(--color-primary-alpha-04) 100%);
  border-bottom-color: var(--border-subtle);
}

html.dark .doc-hero-kicker {
  color: var(--primary-400);
}

html.dark .doc-meta-pill {
  background: var(--surface-nested);
}

html.dark .doc-sidebar {
  border-right-color: var(--border-subtle);
}

html.dark .api-item.active {
  background: var(--color-primary-alpha-12);
}

html.dark .cat-count {
  background: var(--surface-nested);
}

html.dark .code-block {
  background: var(--surface-code);
}

html.dark .lang-tab {
  background: var(--surface-nested);
  border-color: var(--border-default);
  color: var(--text-muted);
}

html.dark .lang-tab:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

html.dark .lang-tab.active {
  background: var(--primary-500);
  border-color: var(--primary-500);
}

/* ===== Markdown 描述渲染 ===== */
.api-md-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-loose);
  margin-bottom: var(--space-6);
  padding: var(--space-3) var(--space-4);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
}

.api-md-desc :deep(h1),
.api-md-desc :deep(h2),
.api-md-desc :deep(h3) {
  color: var(--text-primary);
  margin: var(--space-2) 0 var(--space-1);
}

.api-md-desc :deep(code) {
  background: var(--surface-code);
  padding: var(--space-0-5) var(--space-1);
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

/* ===== 示例区块 ===== */
.example-block {
  margin-bottom: var(--space-3);
}

.example-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.status-badge {
  display: inline-block;
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.status-2xx { background: var(--color-success-alpha-08); color: var(--color-success); }
.status-3xx { background: var(--color-info-alpha-08); color: var(--color-info); }
.status-4xx { background: var(--color-warning-alpha-08); color: var(--color-warning); }
.status-5xx { background: var(--color-error-alpha-08); color: var(--color-error); }

/* ===== Try it out ===== */
.try-it-section {
  border-top: 2px solid var(--border-subtle);
  padding-top: var(--space-5);
}

.try-it-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.try-it-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.try-it-url {
  flex: 1;
}

.try-it-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.try-it-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

.try-it-result {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.status-ok { color: var(--color-success); font-weight: var(--weight-bold); }
.status-err { color: var(--color-error); font-weight: var(--weight-bold); }

/* ===== 暗色模式补充 ===== */
html.dark .api-md-desc {
  background: var(--surface-nested);
}

html.dark .api-md-desc :deep(code) {
  background: var(--surface-code);
}

html.dark .try-it-section {
  border-top-color: var(--border-subtle);
}

html.dark .example-label,
html.dark .try-it-label {
  color: var(--text-primary);
}

html.dark .doc-empty {
  color: var(--text-muted);
}

html.dark .doc-desc,
html.dark .doc-hero-note {
  color: var(--text-muted);
}

html.dark .status-2xx { background: var(--color-success-alpha-10); color: var(--success-dark); }
html.dark .status-3xx { background: var(--color-info-alpha-10); color: var(--info-dark); }
html.dark .status-4xx { background: var(--color-warning-alpha-10); color: var(--warning-dark); }
html.dark .status-5xx { background: var(--color-error-alpha-10); color: var(--error-dark); }

html.dark .opt {
  color: var(--text-muted);
}

html.dark .body-type {
  color: var(--text-muted);
}

html.dark .sidebar-title {
  color: var(--text-muted);
}

html.dark .cat-arrow {
  color: var(--text-muted);
}

html.dark .api-path {
  color: var(--text-primary);
}

/* ===== SharedDocs 暗色模式补全 ===== */
html.dark .doc-header h1 {
  color: var(--text-primary);
}
html.dark .doc-desc {
  color: var(--text-muted);
}
html.dark .doc-hero-note {
  color: var(--text-muted);
}
html.dark .doc-meta-pill {
  background: var(--surface-nested);
  color: var(--text-secondary);
}
html.dark .cat-label {
  color: var(--text-primary);
}
html.dark .cat-label:hover {
  background: var(--surface-hover);
}
html.dark .api-name {
  color: var(--text-primary);
}
html.dark .api-desc {
  color: var(--text-muted);
}
html.dark .section h3 {
  color: var(--text-primary);
}
html.dark .api-method {
  border-color: transparent;
}
html.dark .status-badge {
  border-color: transparent;
}
html.dark .try-it-label {
  color: var(--text-primary);
}
html.dark .example-label {
  color: var(--text-primary);
}
html.dark .doc-empty .empty-icon {
  opacity: 0.3;
}
html.dark .doc-body {
  background: var(--surface-card);
}
html.dark .doc-sidebar {
  background: var(--surface-card);
}
html.dark .doc-main {
  background: var(--surface-card);
}


</style>
