<template>
  <div class="response-body-viewer">
    <!-- Pretty: JSON Tree -->
    <div v-if="mode === 'pretty' && isJson" role="tabpanel" id="panel-pretty">
      <div class="resp-pretty-body">
        <JsonTreeView
          :data="jsonData"
          :project-id="projectId"
          :expand-all="expandAll"
          @extract-variable="$emit('extract-variable', $event)"
        />
      </div>
    </div>

    <!-- Pretty: Non-JSON -->
    <div v-if="mode === 'pretty' && !isJson" role="tabpanel" id="panel-pretty-nonjson">
      <!-- Binary -->
      <div v-if="isBinary" class="resp-binary-hint">
        <span class="resp-binary-icon">⬛</span>
        <div class="resp-binary-detail">
          <span>二进制响应 · {{ formattedSize }} · {{ contentTypeLabel || 'unknown' }}</span>
          <button class="resp-download-link" @click="$emit('download')">下载文件</button>
        </div>
      </div>

      <!-- HTML -->
      <div v-else-if="isHtml" class="resp-nonjson-view">
        <div class="resp-nonjson-hint">
          <span class="resp-nonjson-icon">i</span>
          <div class="resp-nonjson-detail">
            <span>HTML 响应</span>
            <span v-if="contentTypeLabel" class="resp-nonjson-ctype">Content-Type: {{ contentTypeLabel }}</span>
          </div>
        </div>
        <div class="resp-html-actions">
          <button class="resp-action-btn" @click="showPreview = !showPreview">
            {{ showPreview ? '显示源码' : '预览 HTML' }}
          </button>
        </div>
        <iframe v-if="showPreview" :srcdoc="bodyText" class="resp-html-preview" sandbox="allow-scripts" title="HTML Preview" />
        <pre v-else class="resp-text-pre"><code>{{ bodyText }}</code></pre>
      </div>

      <!-- XML -->
      <div v-else-if="isXml" class="resp-nonjson-view">
        <div class="resp-nonjson-hint">
          <span class="resp-nonjson-icon">i</span>
          <div class="resp-nonjson-detail">
            <span>XML 响应</span>
            <span v-if="contentTypeLabel" class="resp-nonjson-ctype">Content-Type: {{ contentTypeLabel }}</span>
          </div>
        </div>
        <pre class="resp-text-pre resp-xml-pre"><code>{{ bodyText }}</code></pre>
      </div>

      <!-- Plain text -->
      <div v-else-if="isText" class="resp-nonjson-view">
        <pre class="resp-text-pre"><code>{{ bodyText }}</code></pre>
      </div>

      <!-- Unknown -->
      <div v-else class="resp-nonjson-view">
        <div class="resp-nonjson-hint">
          <span class="resp-nonjson-icon">i</span>
          <div class="resp-nonjson-detail">
            <span>未知格式{{ contentTypeLabel ? ' (' + contentTypeLabel + ')' : '' }}，截取前 10KB</span>
          </div>
        </div>
        <pre class="resp-text-pre"><code>{{ truncatedText }}</code></pre>
      </div>
    </div>

    <!-- Raw mode -->
    <div v-if="mode === 'raw'" role="tabpanel" id="panel-raw">
      <div class="resp-raw-wrapper">
        <JsonEditor :model-value="bodyText" read-only :height="400" />
      </div>
    </div>

    <!-- Headers mode -->
    <div v-if="mode === 'headers'" role="tabpanel" id="panel-headers">
      <el-table :data="headers" size="small" max-height="400" stripe>
        <el-table-column prop="key" label="Header" min-width="200" />
        <el-table-column prop="value" label="Value" min-width="300" show-overflow-tooltip />
      </el-table>
      <div v-if="!headers.length" class="resp-empty">无响应头</div>
    </div>

    <!-- Cookies mode -->
    <div v-if="mode === 'cookies'" role="tabpanel" id="panel-cookies">
      <div v-if="cookies.length" class="response-cookies-table">
        <div v-for="cookie in cookies" :key="cookie.name" class="cookie-row">
          <span class="cookie-name">{{ cookie.name }}</span>
          <span class="cookie-value">{{ cookie.value }}</span>
          <span class="cookie-meta">{{ cookie.domain || '-' }} · {{ cookie.path || '/' }}</span>
        </div>
      </div>
      <div v-else class="resp-empty">本次响应无 Set-Cookie</div>
    </div>

    <!-- Schema mode -->
    <div v-if="mode === 'schema'" role="tabpanel" id="panel-schema">
      <div class="schema-panel">
        <div v-if="inferredSchema" class="schema-content">
          <pre class="schema-json">{{ formatJson(inferredSchema) }}</pre>
        </div>
        <div v-else class="resp-empty">
          <p>响应体结构推断</p>
          <el-button size="small" @click="$emit('infer-schema')">从响应推断 Schema</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import JsonTreeView from '@/components/JsonTreeView.vue'
import JsonEditor from '@/components/JsonEditor.vue'

export interface ResponseHeader {
  key: string
  value: string
}

export interface ResponseCookie {
  name: string
  value: string
  domain?: string
  path?: string
}

const props = defineProps<{
  mode: 'pretty' | 'raw' | 'headers' | 'cookies' | 'schema' | 'assertions'
  bodyText: string
  contentType?: string
  isJson: boolean
  isBinary: boolean
  isHtml: boolean
  isXml: boolean
  isText: boolean
  jsonData: unknown
  truncatedText: string
  formattedSize: string
  contentTypeLabel: string
  headers: ResponseHeader[]
  cookies: ResponseCookie[]
  inferredSchema: unknown | null
  expandAll: boolean
  projectId: number
}>()

defineEmits<{
  'extract-variable': [value: string]
  download: []
  'infer-schema': []
}>()

const showPreview = ref(false)

function formatJson(obj: unknown): string {
  try {
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(obj)
  }
}
</script>

<style scoped>
.response-body-viewer {
  flex: 1;
  overflow: auto;
}
.resp-pretty-body {
  padding: var(--space-2);
}
.resp-binary-hint {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  justify-content: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.resp-binary-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.resp-download-link {
  background: none;
  border: none;
  color: var(--primary-600);
  cursor: pointer;
  padding: 0;
  font-size: var(--text-xs);
  text-align: left;
}
.resp-nonjson-view { padding: var(--space-3); }
.resp-nonjson-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  margin-bottom: var(--space-3);
}
.resp-nonjson-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--primary-100);
  color: var(--primary-600);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}
.resp-nonjson-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.resp-nonjson-ctype {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.resp-html-actions { margin-bottom: var(--space-3); }
.resp-html-preview {
  width: 100%;
  min-height: 300px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: white;
}
.resp-text-pre {
  max-height: 500px;
  overflow: auto;
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin: 0;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}
.resp-xml-pre { background: var(--surface-card); }
.resp-raw-wrapper { padding: var(--space-2); }
.resp-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.resp-action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-soft);
}
.resp-action-btn:hover { background: var(--surface-hover); color: var(--text-primary); }
.schema-content { padding: var(--space-3); }
.schema-json {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: 1.6;
  white-space: pre-wrap;
  margin: 0;
}
.response-cookies-table {
  display: flex;
  flex-direction: column;
}
.cookie-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  font-size: var(--text-sm);
}
.cookie-row:last-child { border-bottom: none; }
.cookie-name { font-weight: var(--weight-semibold); color: var(--text-primary); min-width: 120px; }
.cookie-value { color: var(--text-secondary); flex: 1; word-break: break-all; }
.cookie-meta { color: var(--text-muted); font-size: var(--text-xs); flex-shrink: 0; }
</style>
