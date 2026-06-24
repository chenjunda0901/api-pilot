<template>
  <div class="docs-preview">
    <!-- 接口基本信息 -->
    <div class="doc-section">
      <div class="doc-api-header">
        <span class="doc-method" :class="'method-' + api.method.toLowerCase()">{{ api.method }}</span>
        <code class="doc-path">{{ api.path }}</code>
      </div>
      <div class="doc-api-name">{{ api.name }}</div>
      <p v-if="api.description && !api.description_md" class="doc-desc">{{ api.description }}</p>
      <div v-if="api.description_md" class="doc-md-desc">
        <MdPreview :model-value="sanitizedDescription" />
      </div>
    </div>

    <!-- 请求参数 -->
    <div class="doc-section" v-if="api.params && api.params.length > 0">
      <h3 class="doc-section-title">Query 参数</h3>
      <table class="doc-table">
        <thead>
          <tr><th>参数名</th><th>类型</th><th>必填</th><th>描述</th></tr>
        </thead>
        <tbody>
          <tr v-for="p in api.params" :key="p.name">
            <td><code>{{ p.name }}</code></td>
            <td>{{ p.type || 'string' }}</td>
            <td>{{ p.required ? '是' : '否' }}</td>
            <td>{{ p.description || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 请求头 -->
    <div class="doc-section" v-if="api.headers && api.headers.length > 0">
      <h3 class="doc-section-title">请求头</h3>
      <table class="doc-table">
        <thead>
          <tr><th>名称</th><th>值</th><th>描述</th></tr>
        </thead>
        <tbody>
          <tr v-for="h in api.headers" :key="h.name">
            <td><code>{{ h.name }}</code></td>
            <td><code>{{ h.value }}</code></td>
            <td>{{ h.description || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 请求体 -->
    <div class="doc-section" v-if="api.body && api.body.type && api.body.type !== 'none'">
      <h3 class="doc-section-title">请求体 ({{ bodyTypeLabel }})</h3>
      <div v-if="bodyTypeLabel === 'JSON'" class="doc-body-type">{{ api.body.type }}</div>
      <pre v-if="api.body.content" class="doc-code-block"><code>{{ api.body.content }}</code></pre>
      <div v-else class="doc-empty">无内容</div>
    </div>

    <!-- 认证信息 -->
    <div class="doc-section" v-if="api.auth && api.auth.type !== 'none'">
      <h3 class="doc-section-title">认证方式</h3>
      <div class="doc-auth-row">
        <span class="doc-auth-type">{{ authTypeLabel }}</span>
        <span v-if="api.auth.type === 'bearer'" class="doc-auth-value">
          Token: <code>{{ api.auth.token || '(已配置)' }}</code>
        </span>
        <span v-else-if="api.auth.type === 'basic'" class="doc-auth-value">
          用户名: <code>{{ api.auth.username || '' }}</code>
        </span>
      </div>
    </div>

    <!-- 响应示例 -->
    <div class="doc-section" v-if="api.response_examples && api.response_examples.length > 0">
      <h3 class="doc-section-title">响应示例</h3>
      <div v-for="(ex, i) in api.response_examples" :key="i" class="doc-response-example">
        <div class="doc-example-header">
          <span class="doc-example-name">{{ getExampleName(ex, i as number) }}</span>
          <span v-if="ex.status_code" class="doc-status-code" :class="statusClass(ex.status_code)">{{ ex.status_code }}</span>
        </div>
        <pre v-if="ex.content" class="doc-code-block"><code>{{ ex.content }}</code></pre>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="isEmpty" class="doc-empty-state">
      <div class="doc-empty-icon">📄</div>
      <div class="doc-empty-text">接口文档预览</div>
      <div class="doc-empty-desc">保存接口后，在此查看完整的接口文档信息</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import DOMPurify from 'dompurify'

interface DocParam {
  name: string
  type?: string
  required?: boolean
  description?: string
}

interface DocHeader {
  name: string
  value: string
  description?: string
}

interface DocBody {
  type?: string
  content?: string
}

interface DocAuth {
  type?: string
  token?: string
  username?: string
}

interface DocResponseExample {
  name?: string
  status_code?: string | number
  content?: string
}

interface DocApi {
  method: string
  path: string
  name: string
  description?: string
  description_md?: string
  params?: DocParam[]
  headers?: DocHeader[]
  body?: DocBody
  auth?: DocAuth
  response_examples?: DocResponseExample[]
}

const props = defineProps<{
  api: DocApi
}>()

const bodyTypeLabel = computed(() => {
  const type = props.api?.body?.type
  const map: Record<string, string> = {
    'none': '',
    'json': 'JSON',
    'form-data': 'Form-Data',
    'x-www-form-urlencoded': 'URL-Encoded',
    'xml': 'XML',
    'raw': 'Raw',
    'binary': 'Binary',
  }
  return map[type] || type || ''
})

const authTypeLabel = computed(() => {
  const type = props.api?.auth?.type
  const map: Record<string, string> = {
    'none': '无',
    'bearer': 'Bearer Token',
    'basic': 'Basic Auth',
    'apikey': 'API Key',
  }
  return map[type] || type || '无'
})

const sanitizedDescription = computed(() => {
  if (!props.api?.description_md) return ''
  return DOMPurify.sanitize(props.api.description_md, { ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'span', 'div'], ALLOWED_ATTR: ['href', 'target', 'src', 'alt', 'class'] })
})

const isEmpty = computed(() => {
  return !props.api?.path || props.api.path === '/'
})

function statusClass(code: number | string) {
  const n = Number(code)
  if (n >= 200 && n < 300) return 'status-2xx'
  if (n >= 300 && n < 400) return 'status-3xx'
  if (n >= 400 && n < 500) return 'status-4xx'
  if (n >= 500) return 'status-5xx'
  return ''
}

function getExampleName(ex: { name?: string; status_code?: string | number }, i: number): string {
  if (ex.name) return ex.name
  if (ex.status_code !== undefined && ex.status_code !== null) return String(ex.status_code)
  return '示例 ' + (i + 1)
}
</script>

<style scoped>
/* 文档预览 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角/阴影均使用 CSS 变量，确保暗色模式自动适配
 */
.docs-preview {
  padding: var(--spacing-xl);
  max-width: 900px;
  margin: 0 auto;
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  line-height: var(--leading-relaxed);
}

/* 章节区块 */
.doc-section {
  margin-bottom: var(--spacing-2xl);
  padding-bottom: var(--spacing-xl);
  border-bottom: 1px solid var(--border-subtle);
}

.doc-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

/* API 头部信息 */
.doc-api-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

/* HTTP 方法徽章 */
.doc-method {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-wide);
  min-width: 52px;
  text-align: center;
}

.method-get { background: var(--method-get-bg); color: var(--method-get-text); }
.method-post { background: var(--method-post-bg); color: var(--method-post-text); }
.method-put { background: var(--method-put-bg); color: var(--method-put-text); }
.method-delete { background: var(--method-delete-bg); color: var(--method-delete-text); }
.method-patch { background: var(--method-patch-bg); color: var(--method-patch-text); }
.method-head { background: var(--method-head-bg); color: var(--method-head-text); }
.method-options { background: var(--method-options-bg); color: var(--method-options-text); }

/* API 路径 */
.doc-path {
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  background: var(--surface-nested);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

/* API 名称和描述 */
.doc-api-name {
  font-size: var(--font-size-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.doc-desc {
  color: var(--text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
  line-height: var(--leading-relaxed);
}

.doc-md-desc {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  line-height: var(--leading-relaxed);
}

.doc-md-desc :deep(.md-editor-preview-wrapper) {
  padding: 0;
}

.doc-md-desc :deep(.md-editor-preview) {
  font-size: var(--font-size-sm);
}

/* 章节标题 */
.doc-section-title {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-md);
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--border-subtle);
}

/* 参数表格 */
.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm);
}

.doc-table th {
  text-align: left;
  padding: var(--spacing-sm) var(--spacing-md);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  font-size: var(--font-size-2xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-nested);
}

.doc-table td {
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.doc-table code {
  font-size: var(--font-size-xs);
  background: var(--surface-code);
  padding: var(--spacing-xs) var(--spacing-xs);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

/* 代码块 */
.doc-code-block {
  background: var(--surface-code);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  overflow-x: auto;
  font-size: var(--font-size-xs);
  line-height: var(--leading-normal);
  margin: 0;
}

.doc-code-block code {
  font-family: var(--font-mono);
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
}

/* 空状态 */
.doc-empty {
  color: var(--text-muted);
  font-style: italic;
  font-size: var(--font-size-xs);
}

/* 认证信息 */
.doc-auth-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
}

.doc-auth-type {
  font-weight: var(--weight-semibold);
  color: var(--primary-600);
  font-size: var(--font-size-sm);
}

.doc-auth-value {
  color: var(--text-muted);
  font-size: var(--font-size-xs);
}

.doc-auth-value code {
  font-family: var(--font-mono);
  background: var(--surface-code);
  padding: var(--spacing-xs) var(--spacing-xs);
  border-radius: var(--radius-sm);
}

/* 响应示例 */
.doc-response-example {
  margin-bottom: var(--spacing-md);
}

.doc-response-example:last-child {
  margin-bottom: 0;
}

.doc-example-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.doc-example-name {
  font-weight: var(--weight-semibold);
  font-size: var(--font-size-xs);
  color: var(--text-primary);
}

/* 状态码徽章 */
.doc-status-code {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-bold);
}

.status-2xx { background: var(--success-bg); color: var(--success-text); }
.status-3xx { background: var(--info-bg); color: var(--info-text); }
.status-4xx { background: var(--warning-bg); color: var(--warning-text); }
.status-5xx { background: var(--error-bg); color: var(--error-text); }

/* 空状态 */
.doc-empty-state {
  text-align: center;
  padding: var(--spacing-5xl) var(--spacing-lg);
  color: var(--text-muted);
}

.doc-empty-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-sm);
}

.doc-empty-text {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.doc-empty-desc {
  font-size: var(--font-size-xs);
}
</style>