<template>
  <div class="test-panel" :class="{ expanded }">
    <div class="test-panel-header" @click="toggle">
      <span class="test-panel-title">测试规则</span>
      <el-icon>
        <ArrowDown v-if="!expanded" />
        <ArrowUp v-else />
      </el-icon>
    </div>
    <div v-show="expanded" class="test-panel-body">
      <!-- MatchPreview -->
      <div class="match-preview">
        <div class="preview-title">匹配预览</div>
        <div class="preview-row">
          <el-input v-model="testPath" placeholder="请求路径" size="small" />
          <el-select v-model="testMethod" size="small" style="width: 100px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
            <el-option label="*" value="*" />
          </el-select>
          <el-button size="small" @click="previewMatch">预览匹配</el-button>
        </div>
        <div v-if="matchResult !== null" class="match-result">
          <span v-if="matchResult" class="match-success">✓ 匹配: {{ matchResult.name }}</span>
          <span v-else class="match-fail">✗ 未匹配到任何规则</span>
        </div>
      </div>
      <!-- HttpTester -->
      <div class="http-tester">
        <div class="tester-row">
          <span class="tester-label">查询参数</span>
          <el-input
            v-model="queryParams"
            placeholder="{&quot;key&quot;:&quot;value&quot;}"
            size="small"
            type="textarea"
            :rows="2"
          />
        </div>
        <div class="tester-row">
          <span class="tester-label">请求头</span>
          <el-input
            v-model="testHeaders"
            placeholder="{&quot;Authorization&quot;:&quot;Bearer xxx&quot;}"
            size="small"
            type="textarea"
            :rows="2"
          />
        </div>
        <div class="tester-actions">
          <el-button size="small" type="primary" :loading="testing" @click="sendTest">
            发送测试
          </el-button>
        </div>
        <div v-if="testResponse" class="test-response">
          <div class="response-status">
            <span :class="statusClass">{{ testResponse.status }}</span>
            <span class="response-time">{{ testResponse.duration_ms }}ms</span>
          </div>
          <div class="response-headers">
            <div class="response-section-title">响应头</div>
            <pre>{{ JSON.stringify(testResponse.headers, null, 2) }}</pre>
          </div>
          <div class="response-body">
            <div class="response-section-title">响应体</div>
            <pre>{{ formatJson(testResponse.body) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue"
import { ArrowDown, ArrowUp } from "lucide-vue-next"
import request from "../api/request"
import { msgError } from "../utils/message"
import type { MockRule } from "../types"

interface TestResponseData {
  status: number
  duration_ms: number
  headers: Record<string, unknown>
  body: string
}

const props = defineProps<{
  projectId: number
  rules: MockRule[]
  editingRule?: MockRule
}>()

const expanded = ref(false)
const testPath = ref("")
const testMethod = ref("GET")
const matchResult = ref<MockRule | null>(null)
const queryParams = ref("")
const testHeaders = ref("")
const testing = ref(false)
const testResponse = ref<TestResponseData | null>(null)

function toggle() {
  expanded.value = !expanded.value
}

function previewMatch() {
  const path = testPath.value
  const method = testMethod.value
  // 前端计算匹配规则
  matchResult.value =
    props.rules.find((r) => {
      const pathMatch = r.match_path === path || r.match_path === "*"
      const methodMatch = r.match_method === method || r.match_method === "*"
      return pathMatch && methodMatch
    }) || null
}

function statusClass() {
  if (!testResponse.value) return ""
  const s = testResponse.value.status
  if (s >= 200 && s < 300) return "status-success"
  if (s >= 400 && s < 500) return "status-warning"
  return "status-error"
}

function formatJson(str: string) {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

async function sendTest() {
  testing.value = true
  testResponse.value = null
  try {
    let parsedParams = {}
    let parsedHeaders = {}
    try { parsedParams = queryParams.value ? JSON.parse(queryParams.value) : {} } catch { msgError('查询参数 JSON 格式错误'); return }
    try { parsedHeaders = testHeaders.value ? JSON.parse(testHeaders.value) : {} } catch { msgError('请求头 JSON 格式错误'); return }
    const res = await request.post("/mock/test", {
      project_id: props.projectId,
      path: testPath.value,
      method: testMethod.value,
      query_params: parsedParams,
      headers: parsedHeaders,
    })
    testResponse.value = res.data
  } catch (e: unknown) {
    testResponse.value = { status: 500, headers: {}, body: e instanceof Error ? e.message : 'Unknown error', duration_ms: 0 }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
/* ==========================================
 * TestPanel 样式
 * 使用 design tokens 确保主题一致性
 * ========================================== */

.test-panel {
  border-top: 1px solid var(--border-subtle);
  margin-top: var(--spacing-lg);
}

.test-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  min-height: 44px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

.test-panel-header:hover {
  background: var(--surface-hover);
}

.test-panel-title {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
}

.test-panel-body {
  padding: var(--spacing-md) 0;
}

/* ===== 匹配预览区域 ===== */
.match-preview {
  margin-bottom: var(--spacing-lg);
}

.preview-title {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  margin-bottom: var(--spacing-sm);
}

.preview-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.match-result {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.match-success {
  color: var(--success);
  font-weight: var(--weight-medium);
}

.match-fail {
  color: var(--error);
  font-weight: var(--weight-medium);
}

/* ===== HTTP 测试器 ===== */
.tester-row {
  margin-bottom: var(--spacing-md);
}

.tester-label {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  display: block;
  margin-bottom: var(--spacing-xs);
}

.tester-actions {
  margin-bottom: var(--spacing-md);
}

/* ===== 测试响应区域 ===== */
.test-response {
  background: var(--surface-page);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  border: 1px solid var(--border-subtle);
}

.response-status {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  align-items: center;
}

/* 状态码颜色 */
.status-success {
  color: var(--success);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.status-warning {
  color: var(--warning);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.status-error {
  color: var(--error);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.response-time {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
}

.response-section-title {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  margin-bottom: var(--spacing-xs);
  font-weight: var(--weight-medium);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.test-response pre {
  font-size: var(--font-size-sm);
  white-space: pre-wrap;
  word-break: break-all;
  font-family: var(--font-mono);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
  background: var(--surface-code);
  padding: var(--spacing-sm);
  border-radius: var(--radius-sm);
  margin-top: var(--spacing-xs);
}

/* ===== 暗色模式适配 ===== */
html.dark .test-response {
  background: var(--surface-nested);
  border-color: var(--border-strong);
}

html.dark .test-response pre {
  background: var(--surface-code);
  color: var(--text-secondary);
}
</style>
