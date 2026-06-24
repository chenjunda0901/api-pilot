<template>
  <SkeletonCard v-if="loading" type="report" :count="3" />
  <div v-else-if="error" class="shared-error">
    <EmptyState illustration="report" :title="t('sharedReport.cannotAccess')" :description="error">
      <template #action>
        <el-button type="primary" size="small" @click="loadReport">{{ t('sharedReport.retry') }}</el-button>
      </template>
    </EmptyState>
  </div>
  <div v-else-if="report" class="shared-report">
    <!-- 分享报告标识 -->
    <div class="shared-banner">
      <span class="shared-banner-chip">{{ t('sharedReport.sharedChip') }}</span>
      <span class="shared-banner-meta">{{ report.scene_name || t('sharedReport.unknownScene') }} · {{ report.env_name || t('sharedReport.testEnv') }}</span>
      <span class="shared-banner-chip secondary">{{ t('sharedReport.caseCount', { count: report.total_count }) }}</span>
    </div>

    <!-- 概要区 -->
    <div class="summary-hero" :class="report.status">
      <div class="summary-layout">
        <div class="summary-ring">
          <svg viewBox="0 0 120 120" class="ring-svg">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--surface-hover)" stroke-width="8"/>
            <circle cx="60" cy="60" r="52" fill="none"
              :stroke="report.status === 'success' ? 'var(--success)' : 'var(--error)'"
              stroke-width="8" stroke-linecap="round"
              :stroke-dasharray="2 * Math.PI * 52"
              :stroke-dashoffset="2 * Math.PI * 52 * (1 - (report.total_count ? report.pass_count / report.total_count : 0))"
              transform="rotate(-90 60 60)"
              class="ring-fill"
            />
          </svg>
          <div class="ring-text">
            <span class="ring-pct">{{ report.total_count ? Math.round(report.pass_count / report.total_count * 100) : 0 }}%</span>
            <span class="ring-label">{{ t('sharedReport.passRate') }}</span>
          </div>
        </div>
        <div class="summary-stats">
          <div class="stat-card pass"><span class="stat-val">{{ report.pass_count }}</span><span class="stat-lbl">{{ t('sharedReport.pass') }}</span></div>
          <div class="stat-card fail"><span class="stat-val">{{ report.fail_count }}</span><span class="stat-lbl">{{ t('sharedReport.fail') }}</span></div>
          <div class="stat-card skip"><span class="stat-val">{{ report.skip_count || 0 }}</span><span class="stat-lbl">{{ t('sharedReport.skip') }}</span></div>
          <div class="stat-card total"><span class="stat-val">{{ report.total_count }}</span><span class="stat-lbl">{{ t('sharedReport.total') }}</span></div>
        </div>
      </div>
      <div class="summary-meta">
        <span>{{ report.scene_name || t('sharedReport.unknownScene') }}</span>
        <span class="meta-dot">·</span>
        <span>{{ report.env_name || t('sharedReport.testEnv') }}</span>
        <span class="meta-dot">·</span>
        <span>{{ report.duration }}s</span>
        <span class="meta-dot">·</span>
        <span>{{ formatTime(report.created_at) }}</span>
      </div>
    </div>

    <!-- 压测性能指标 -->
    <div class="stress-metrics-section" v-if="report.stress_metrics && Object.keys(report.stress_metrics).length > 0">
      <div class="metrics-head"><h2>{{ t('sharedReport.performanceMetrics') }}</h2></div>
      <div class="metrics-grid">
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.p50 ?? '-' }}ms</span>
          <span class="metrics-label">{{ t('sharedReport.p50Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.p90 ?? '-' }}ms</span>
          <span class="metrics-label">{{ t('sharedReport.p90Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.p95 ?? '-' }}ms</span>
          <span class="metrics-label">{{ t('sharedReport.p95Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.p99 ?? '-' }}ms</span>
          <span class="metrics-label">{{ t('sharedReport.p99Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.avg ?? '-' }}ms</span>
          <span class="metrics-label">{{ t('sharedReport.avgLatency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.throughput ?? '-' }}</span>
          <span class="metrics-label">{{ t('sharedReport.throughput') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.error_rate ?? '-' }}%</span>
          <span class="metrics-label">{{ t('sharedReport.errorRate') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report.stress_metrics?.total_requests ?? '-' }}</span>
          <span class="metrics-label">{{ t('sharedReport.totalRequests') }}</span>
        </div>
      </div>
    </div>

    <!-- 步骤列表 -->
    <div class="steps-section">
      <div class="steps-head">
        <h2>{{ t('sharedReport.executionSteps') }}</h2>
        <div class="steps-filter">
          <button :class="{ active: stepFilter === 'all' }" @click="stepFilter = 'all'">{{ t('sharedReport.all') }}</button>
          <button :class="{ active: stepFilter === 'failed' }" @click="stepFilter = 'failed'">{{ t('sharedReport.failedOnly') }}</button>
        </div>
      </div>
      <div class="steps-list">
        <div
          v-for="(step, i) in filteredSteps"
          :key="step.id"
          class="step-card"
          :class="String(step.status)"
        >
          <div class="step-header" @click="toggleStep(i)">
            <div class="step-status-icon">
              <span v-if="step.status === 'success'" class="status-icon success">&#10003;</span>
              <span v-else-if="step.status === 'failed'" class="status-icon fail">&#10007;</span>
              <span v-else class="status-icon skip">&#8722;</span>
            </div>
            <div class="step-info">
              <span class="step-method" :class="step.request_method?.toLowerCase()">{{ step.request_method || 'N/A' }}</span>
              <span class="step-url">{{ truncateUrl(step.request_url || "") }}</span>
            </div>
            <div class="step-meta">
              <span class="step-duration">{{ step.duration ? step.duration + 'ms' : '-' }}</span>
              <span class="step-status-text">{{ step.status === 'success' ? t('sharedReport.stepPassed') : step.status === 'failed' ? t('sharedReport.stepFailed') : t('sharedReport.stepSkipped') }}</span>
              <span class="expand-icon" :class="{ expanded: isStepExpanded(i) }">&#9658;</span>
            </div>
          </div>
          <div class="step-details" v-if="isStepExpanded(i)">
            <!-- 请求信息 -->
            <div class="detail-section">
              <h4>{{ t('sharedReport.requestInfo') }}</h4>
              <div class="detail-row"><span class="detail-label">{{ t('sharedReport.url') }}</span><span class="detail-value">{{ step.request_url }}</span></div>
              <div class="detail-row" v-if="step.request_method"><span class="detail-label">{{ t('sharedReport.method') }}</span><span class="detail-value">{{ step.request_method }}</span></div>
              <div class="detail-row" v-if="step.request_headers"><span class="detail-label">{{ t('sharedReport.requestHeaders') }}</span><pre class="detail-pre">{{ sanitizeHeaders(step.request_headers) }}</pre></div>
              <div class="detail-row" v-if="step.request_body"><span class="detail-label">{{ t('sharedReport.requestBody') }}</span><pre class="detail-pre">{{ sanitizeBody(step.request_body) }}</pre></div>
            </div>
            <!-- 响应信息 -->
            <div class="detail-section" v-if="step.response_status">
              <h4>{{ t('sharedReport.responseInfo') }}</h4>
              <div class="detail-row"><span class="detail-label">{{ t('sharedReport.statusCode') }}</span><span class="detail-value" :class="getStatusClass(Number(step.response_status))">{{ step.response_status }}</span></div>
              <div class="detail-row" v-if="step.response_headers"><span class="detail-label">{{ t('sharedReport.responseHeaders') }}</span><pre class="detail-pre">{{ sanitizeHeaders(step.response_headers) }}</pre></div>
              <div class="detail-row" v-if="step.response_body"><span class="detail-label">{{ t('sharedReport.responseBody') }}</span><pre class="detail-pre">{{ truncateBody(step.response_body || "") }}</pre></div>
            </div>
            <!-- 断言结果 -->
            <div class="detail-section" v-if="step.assertions && step.assertions.length > 0">
              <h4>{{ t('sharedReport.assertionResult') }}</h4>
              <div v-for="(assertion, ai) in step.assertions" :key="ai" class="assertion-item" :class="assertion.passed ? 'pass' : 'fail'">
                <span class="assertion-icon">{{ assertion.passed ? '&#10003;' : '&#10007;' }}</span>
                <span class="assertion-expr">{{ assertion.type }} {{ assertion.operator }} {{ assertion.value }}</span>
                <span v-if="!assertion.passed" class="assertion-detail">{{ t('sharedReport.expected') }} {{ assertion.expected }}, {{ t('sharedReport.actual') }} {{ assertion.actual }}</span>
              </div>
            </div>
            <!-- 错误信息 -->
            <div class="detail-section" v-if="step.error_message">
              <h4>{{ t('sharedReport.errorMessage') }}</h4>
              <pre class="error-message">{{ step.error_message }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 密码输入对话框（分享报告设置密码时） -->
  <el-dialog v-model="passwordDialog.visible" title="输入访问密码" width="400px" :close-on-click-modal="false">
    <el-input
      v-model="passwordDialog.password"
      type="password"
      placeholder="请输入访问密码"
      show-password
      @keyup.enter="submitPassword"
    />
    <template #footer>
      <el-button @click="passwordDialog.visible = false">取消</el-button>
      <el-button type="primary" @click="submitPassword">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import request from '../api/request'
import type { TestReport, ReportStep } from '../types'
import EmptyState from '../components/EmptyState.vue'
import SkeletonCard from '../components/SkeletonCard.vue'

const route = useRoute()
const { t } = useI18n()
const token = computed(() => route.params.token as string)
const report = ref<TestReport | null>(null)
const steps = ref<ReportStep[]>([])
const loading = ref(true)
const error = ref('')
const expandedStep = ref<number | null>(null)
const stepFilter = ref<'all' | 'failed'>('all')
const passwordDialog = reactive({ visible: false, password: '' })

function formatTime(t: string) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    if (isNaN(d.getTime())) return t
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch { return t }
}

const filteredSteps = computed(() => {
  if (stepFilter.value === 'failed') {
    return steps.value.filter((s: ReportStep) => s.status === 'failed')
  }
  return steps.value
})

function isStepExpanded(i: number) {
  return expandedStep.value === i
}

function toggleStep(i: number) {
  expandedStep.value = expandedStep.value === i ? null : i
}

function truncateUrl(url: string) {
  if (!url) return '-'
  try {
    const u = new URL(url)
    return u.pathname + u.search
  } catch {
    return url.length > 60 ? url.substring(0, 60) + '...' : url
  }
}

function truncateBody(body: string) {
  if (!body) return ''
  try {
    const obj = JSON.parse(body)
    const str = JSON.stringify(obj, null, 2)
    return str.length > 500 ? str.substring(0, 500) + '...\n(truncated)' : str
  } catch {
    return body.length > 500 ? body.substring(0, 500) + '...\n(truncated)' : body
  }
}

/** 敏感 Header 名称列表（不区分大小写） */
const SENSITIVE_HEADERS = new Set([
  'authorization', 'cookie', 'set-cookie', 'proxy-authorization',
  'x-api-key', 'x-auth-token', 'x-csrf-token',
  'access-control-request-headers', 'www-authenticate',
])

/**
 * 过滤请求/响应头中的敏感字段
 * 输入可能是 JSON 字符串或对象，输出格式化的 JSON 字符串
 */
function sanitizeHeaders(raw: string | Record<string, unknown> | undefined): string {
  if (!raw) return ''
  try {
    const obj = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
      return typeof raw === 'string' ? raw : JSON.stringify(raw)
    }
    const filtered: Record<string, unknown> = {}
    for (const [key, value] of Object.entries(obj)) {
      if (SENSITIVE_HEADERS.has(key.toLowerCase())) {
        filtered[key] = t('sharedReport.hidden')
      } else {
        filtered[key] = value
      }
    }
    return JSON.stringify(filtered, null, 2)
  } catch {
    return typeof raw === 'string' ? raw : JSON.stringify(raw)
  }
}

/** 敏感 body 字段名 */
const SENSITIVE_BODY_FIELDS = new Set([
  'password', 'passwd', 'secret', 'token', 'access_token',
  'refresh_token', 'api_key', 'apikey', 'private_key',
  'authorization', 'credential', 'auth',
])

function sanitizeBody(raw: string | undefined): string {
  if (!raw) return ''
  try {
    const obj = JSON.parse(raw)
    if (typeof obj === 'object' && obj !== null && !Array.isArray(obj)) {
      const filtered: Record<string, unknown> = {}
      for (const [key, value] of Object.entries(obj)) {
        if (SENSITIVE_BODY_FIELDS.has(key.toLowerCase())) {
          filtered[key] = t('sharedReport.hidden')
        } else {
          filtered[key] = value
        }
      }
      return JSON.stringify(filtered, null, 2)
    }
    return raw
  } catch { return raw }
}

function getStatusClass(status: number | string | undefined): string {
  if (status === undefined || status === null) return ''
  const s = typeof status === 'string' ? parseInt(status, 10) : status
  if (isNaN(s)) return ''
  if (s >= 200 && s < 300) return 'status-2xx'
  if (s >= 400 && s < 500) return 'status-4xx'
  if (s >= 500) return 'status-5xx'
  return ''
}

async function loadReport(password?: string) {
  loading.value = true
  error.value = ''
  try {
    const url = password
      ? `/reports/shared/${token.value}?password=${encodeURIComponent(password)}`
      : `/reports/shared/${token.value}`
    const res = await request.get(url)
    const payload = res.data
    if (payload) {
      const stepsData = Array.isArray(payload.steps) ? payload.steps : []
      report.value = {
        ...payload,
        total_count: payload.total_count ?? payload.total ?? stepsData.length ?? 0,
        pass_count: payload.pass_count ?? payload.passed ?? 0,
        fail_count: payload.fail_count ?? payload.failed ?? 0,
        skip_count: payload.skip_count ?? 0,
      }
      steps.value = stepsData
    } else {
      error.value = t('sharedReport.unknownError')
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string; code?: string } } }
    const msg = err?.response?.data?.message || ''
    const code = err?.response?.data?.code || ''
    // 仅在明确需要密码时显示密码输入对话框
    // 后端返回 "此分享链接需要输入密码" 或 code 为 PASSWORD_REQUIRED 时才弹窗
    if (msg.includes('需要输入密码') || msg.includes('password required') || code === 'PASSWORD_REQUIRED') {
      passwordDialog.visible = true
      passwordDialog.password = ''
      error.value = ''
    } else if (msg.includes('密码错误') || msg.includes('password incorrect') || code === 'PASSWORD_INCORRECT') {
      passwordDialog.visible = true
      passwordDialog.password = ''
      error.value = ''
    } else {
      error.value = t('sharedReport.loadFailedMsg')
    }
  } finally {
    loading.value = false
  }
}

async function submitPassword() {
  if (!passwordDialog.password) return
  passwordDialog.visible = false
  await loadReport(passwordDialog.password)
}

onMounted(loadReport)
</script>

<style scoped>
/* ===== 加载状态 ===== */
.shared-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  color: var(--text-secondary);
}

/* 加载旋转动画 */
.loading-spinner {
  width: var(--space-10);
  height: var(--space-10);
  border: 3px solid var(--surface-hover);
  border-top-color: var(--primary-500);
  border-radius: var(--radius-full);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 错误状态 ===== */
.shared-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  color: var(--text-secondary);
}

.error-icon {
  width: var(--space-16);
  height: var(--space-16);
  border-radius: var(--radius-full);
  background: var(--error);
  color: var(--surface-card);
  font-size: var(--text-4xl);
  font-weight: var(--weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-4);
}

.shared-error h2 {
  margin: 0 0 var(--space-2);
  color: var(--text-primary);
}

.shared-error p {
  margin: var(--space-1) 0;
}

/* ===== 分享报告主容器 ===== */
.shared-report {
  max-width: var(--layout-max-width);
  margin: 0 auto;
  padding: var(--space-5);
}

/* 顶部标识横幅 */
.shared-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  margin-bottom: var(--space-5);
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--surface-nested) 0%, var(--color-primary-alpha-04) 100%);
  color: var(--text-muted);
  font-size: var(--text-xs);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

.shared-banner-meta {
  color: var(--text-secondary);
}

/* ===== 概要 Hero 区域 ===== */
.summary-hero {
  background: var(--surface-card);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  margin-bottom: var(--space-4);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
}

.summary-hero.success {
  border-left: var(--space-1) solid var(--success);
}

.summary-hero.failed {
  border-left: var(--space-1) solid var(--error);
}

.summary-layout {
  display: flex;
  gap: var(--space-8);
  align-items: center;
}

/* 通过率环形图 */
.summary-ring {
  position: relative;
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.ring-svg {
  width: 120px;
  height: 120px;
}

.ring-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-pct {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}

.ring-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* 统计卡片网格 */
.summary-stats {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-md);
  background: var(--surface-nested);
  min-width: 70px;
  border: 1px solid var(--border-subtle);
  transition: transform var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.stat-card.pass { border-top: 3px solid var(--success); }
.stat-card.fail { border-top: 3px solid var(--error); }
.stat-card.skip { border-top: 3px solid var(--warning); }
.stat-card.total { border-top: 3px solid var(--primary-500); }

.stat-val {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}

.stat-lbl {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

/* 元数据行 */
.summary-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
  color: var(--text-secondary);
  font-size: var(--text-sm);
}

.meta-dot { opacity: 0.65; }

/* ===== 压测性能指标区 ===== */
.stress-metrics-section {
  background: var(--surface-card);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

.metrics-head h2,
.steps-head h2 {
  margin: 0 0 var(--space-3);
  font-size: var(--text-lg);
  color: var(--text-primary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--space-3);
}

.metrics-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  transition: transform var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

.metrics-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.metrics-value {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--primary-500);
}

.metrics-label {
  font-size: var(--font-size-2xs);
  color: var(--text-secondary);
  margin-top: var(--space-1);
}

/* ===== 执行步骤列表 ===== */
.steps-section {
  background: var(--surface-card);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

.steps-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.steps-filter {
  display: flex;
  gap: var(--space-2);
}

.steps-filter button {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--text-sm);
  font-family: inherit;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.steps-filter button:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.steps-filter button.active {
  background: var(--primary-500);
  color: var(--surface-card);
  border-color: var(--primary-500);
}

.steps-filter button:focus-visible {
  outline: var(--focus-ring-width) solid var(--primary-500);
  outline-offset: 2px;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* 步骤卡片 */
.step-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: box-shadow var(--duration-fast) var(--ease-smooth);
}

.step-card:hover {
  box-shadow: var(--shadow-sm);
}

.step-card.success { border-left: 3px solid var(--success); }
.step-card.failed { border-left: 3px solid var(--error); }
.step-card.skipped { border-left: 3px solid var(--warning); }

.step-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  cursor: pointer;
  background: var(--surface-nested);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.step-header:hover {
  background: var(--surface-hover);
}

.step-status-icon {
  width: var(--space-6);
  height: var(--space-6);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-base);
}

.status-icon.success { background: var(--success); color: var(--surface-card); }
.status-icon.fail { background: var(--error); color: var(--surface-card); }
.status-icon.skip { background: var(--warning); color: var(--surface-card); }

.step-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.step-method {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-xs);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  flex-shrink: 0;
}

.step-method.get    { background: var(--method-get-bg);    color: var(--method-get-text); }
.step-method.post   { background: var(--method-post-bg);   color: var(--method-post-text); }
.step-method.put    { background: var(--method-put-bg);    color: var(--method-put-text); }
.step-method.patch  { background: var(--method-patch-bg);  color: var(--method-patch-text); }
.step-method.delete { background: var(--method-delete-bg); color: var(--method-delete-text); }

.step-url {
  font-size: var(--text-base);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.step-duration {
  font-weight: var(--weight-semibold);
}

.expand-icon {
  transition: transform var(--duration-base) var(--ease-smooth);
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

/* 步骤详情展开区 */
.step-details {
  padding: var(--space-3);
  background: var(--surface-card);
  border-top: 1px solid var(--border-subtle);
}

.detail-section {
  margin-bottom: var(--space-4);
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  margin: 0 0 var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.detail-row {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  font-size: var(--text-xs);
}

.detail-label {
  color: var(--text-secondary);
  flex-shrink: 0;
  width: 70px;
}

.detail-value {
  color: var(--text-primary);
  word-break: break-all;
}

.detail-pre {
  margin: var(--space-1) 0 0;
  padding: var(--space-2);
  background: var(--surface-nested);
  border-radius: var(--radius-xs);
  border: 1px solid var(--border-subtle);
  font-size: var(--font-size-2xs);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
}

.status-2xx { color: var(--success); }
.status-4xx { color: var(--warning); }
.status-5xx { color: var(--error); }

/* 断言结果项 */
.assertion-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  margin-bottom: var(--space-1);
}

.assertion-item.pass {
  background: var(--color-success-alpha-10);
  color: var(--success);
}

.assertion-item.fail {
  background: var(--color-error-alpha-10);
  color: var(--error);
}

.assertion-icon { font-weight: var(--weight-bold); }
.assertion-expr { flex: 1; }
.assertion-detail { font-size: var(--text-xs); color: var(--text-secondary); }

.error-message {
  margin: 0;
  padding: var(--space-2);
  background: var(--color-error-alpha-10);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  color: var(--error);
  white-space: pre-wrap;
}

/* ===== 暗色模式适配 ===== */
html.dark .shared-loading,
html.dark .shared-error {
  color: var(--text-secondary);
}

html.dark .error-icon {
  background: var(--error);
}

html.dark .summary-hero {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .summary-hero.success { border-left-color: var(--success); }
html.dark .summary-hero.failed { border-left-color: var(--error); }

html.dark .ring-pct { color: var(--text-primary); }
html.dark .ring-label { color: var(--text-muted); }

html.dark .stat-card {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .stat-val { color: var(--text-primary); }
html.dark .stat-lbl { color: var(--text-muted); }
html.dark .summary-meta { color: var(--text-muted); }

html.dark .stress-metrics-section,
html.dark .steps-section {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .metrics-head h2,
html.dark .steps-head h2 {
  color: var(--text-primary);
}

html.dark .metrics-card {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .metrics-value { color: var(--primary-500); }
html.dark .metrics-label { color: var(--text-muted); }

html.dark .step-card {
  border-color: var(--border-subtle);
}

html.dark .step-card.success { border-left-color: var(--success); }
html.dark .step-card.failed { border-left-color: var(--error); }
html.dark .step-card.skipped { border-left-color: var(--warning); }

html.dark .step-header {
  background: var(--surface-nested);
}

html.dark .step-header:hover {
  background: var(--surface-hover);
}

html.dark .step-url { color: var(--text-primary); }
html.dark .step-meta { color: var(--text-muted); }

html.dark .step-details {
  background: var(--surface-card);
  border-top-color: var(--border-subtle);
}

html.dark .detail-section h4 { color: var(--text-muted); }
html.dark .detail-label { color: var(--text-muted); }
html.dark .detail-value { color: var(--text-primary); }

html.dark .detail-pre {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

html.dark .steps-filter button {
  border-color: var(--border-default);
  color: var(--text-muted);
}

html.dark .steps-filter button:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
  border-color: var(--border-strong);
}

html.dark .steps-filter button.active {
  background: var(--primary-500);
  border-color: var(--primary-500);
}

html.dark .assertion-item.pass {
  background: var(--color-success-alpha-15);
}

html.dark .assertion-item.fail {
  background: var(--color-error-alpha-15);
}

html.dark .error-message {
  background: var(--color-error-alpha-15);
  color: var(--error);
}

html.dark .shared-error h2 {
  color: var(--text-primary);
}

/* ===== SharedReport 暗色模式补全 ===== */
html.dark .summary-hero {
  box-shadow: var(--shadow-card), 0 0 0 1px var(--color-white-alpha-04);
}
html.dark .stat-card {
  box-shadow: var(--shadow-sm), 0 0 0 1px var(--color-white-alpha-04);
}
html.dark .stat-card:hover {
  border-color: var(--color-primary-alpha-12);
  box-shadow: var(--shadow-card-hover), 0 0 0 1px var(--color-primary-alpha-08);
}
html.dark .stress-metrics-section,
html.dark .steps-section {
  box-shadow: var(--shadow-card), 0 0 0 1px var(--color-white-alpha-04);
}
html.dark .metrics-card {
  box-shadow: var(--shadow-xs), 0 0 0 1px var(--color-white-alpha-04);
}
html.dark .metrics-card:hover {
  border-color: var(--color-primary-alpha-12);
  box-shadow: var(--shadow-sm), 0 0 0 1px var(--color-primary-alpha-08);
}
html.dark .step-method.get { background: var(--method-get-bg); color: var(--method-get-text); }
html.dark .step-method.post { background: var(--method-post-bg); color: var(--method-post-text); }
html.dark .step-method.put { background: var(--method-put-bg); color: var(--method-put-text); }
html.dark .step-method.patch { background: var(--method-patch-bg); color: var(--method-patch-text); }
html.dark .step-method.delete { background: var(--method-delete-bg); color: var(--method-delete-text); }
html.dark .status-2xx { color: var(--success-400); }
html.dark .status-4xx { color: var(--warning-400); }
html.dark .status-5xx { color: var(--error-400); }
html.dark .assertion-detail { color: var(--text-muted); }
html.dark .shared-loading {
  color: var(--text-secondary);
}

/* ===== 响应式适配 ===== */
@media (max-width: 768px) {
  .shared-report {
    padding: var(--space-3);
  }
  .summary-layout {
    flex-direction: column;
    gap: var(--space-4);
  }
  .summary-ring {
    width: 100px;
    height: 100px;
  }
  .ring-svg {
    width: 100px;
    height: 100px;
  }
  .ring-pct { font-size: var(--text-xl); }
  .summary-stats {
    justify-content: center;
  }
  .summary-meta {
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .metrics-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  }
  .step-info {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
  }
  .step-header {
    gap: var(--space-2);
    padding: var(--space-3);
  }
  .step-meta {
    gap: var(--space-2);
    font-size: var(--font-size-2xs);
  }
}

@media (max-width: 480px) {
  .stat-card {
    padding: var(--space-2) var(--space-3);
    min-width: 60px;
  }
  .stat-val { font-size: var(--text-xl); }
  .steps-head {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }
}


</style>
