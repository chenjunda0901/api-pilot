<template>
  <PageLayout
    :title="reportTitle"
    :subtitle="reportSubtitle"
    :kicker="t('reportDetail.kicker')"
    :loading="loading && !report"
    :error="!loading && error ? error : null"
    @retry="retryLoadReport"
  >
    <template #hero-extra>
      <div v-if="report" class="report-hero-meta">
        <span class="report-meta-pill">{{ $t('reportDetail.caseCount', { count: report.total_count }) }}</span>
        <span class="report-meta-pill">{{ report.pass_count }} {{ $t('reportDetail.passed') }}</span>
        <span class="report-meta-pill">{{ report.fail_count }} {{ $t('reportDetail.failed') }}</span>
        <span class="report-meta-pill">{{ report.duration }}s</span>
      </div>
    </template>

    <template #filter>
      <div v-if="report" class="filter-bar">
        <div class="page-head-group">
          <el-button size="small" text @click="router.back()">
            <ChevronLeft :size="14" /> {{ $t('reportDetail.back') }}
          </el-button>
          <el-button size="small" type="primary" @click="rerunReport" :loading="rerunning">
            <Play :size="14" /> {{ $t('reportDetail.rerun') }}
          </el-button>
        </div>
        <el-divider direction="vertical" />
        <div class="page-head-group">
          <el-dropdown trigger="click" @command="handleExport">
            <el-button size="small" text>
              <Download :size="14" /> {{ $t('reportDetail.export') }}
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="html">{{ $t('reportDetail.exportHtml') }}</el-dropdown-item>
              <el-dropdown-item command="json">{{ $t('reportDetail.exportJson') }}</el-dropdown-item>
              <el-dropdown-item command="excel">{{ $t('reportDetail.exportExcel') }}</el-dropdown-item>
              <el-dropdown-item command="pdf">{{ $t('reportDetail.exportPdf') }}</el-dropdown-item>
              <el-dropdown-item command="markdown">{{ $t('reportDetail.exportMarkdown') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-divider direction="vertical" />
        <div class="page-head-group">
          <el-popconfirm :title="$t('reportDetail.confirmDeleteReport')" @confirm="deleteReport" :confirm-button-text="$t('reportDetail.delete')" :cancel-button-text="$t('common.cancel')" confirm-button-type="danger">
            <template #reference>
              <el-button size="small" type="danger" plain>{{ $t('reportDetail.delete') }}</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </template>

    <!-- 面包屑 -->
    <BreadcrumbNav :items="breadcrumbItems" />

      <!-- 概要区 -->
      <div v-if="report" class="summary-hero" :class="report.status === 'error' ? 'failed' : report.status">
        <div class="summary-layout">
          <!-- 左侧：环形进度 -->
          <div class="summary-ring">
            <svg viewBox="0 0 120 120" class="ring-svg">
              <circle cx="60" cy="60" r="52" fill="none" stroke="var(--surface-hover)" stroke-width="8"/>
              <circle cx="60" cy="60" r="52" fill="none"
                :stroke="report.status === 'success' ? 'var(--color-success)' : 'var(--color-error)'"
                stroke-width="8" stroke-linecap="round"
                :stroke-dasharray="ringCircumference"
                :stroke-dashoffset="ringDashOffset"
                transform="rotate(-90 60 60)"
                class="ring-fill"
              />
            </svg>
            <div class="ring-text">
              <span class="ring-pct">{{ report.total_count ? Math.round(report.pass_count / report.total_count * 100) : 0 }}%</span>
              <span class="ring-label">{{ $t('reportDetail.passRate') }}</span>
            </div>
          </div>
          <!-- 右侧：统计卡片 -->
          <div class="summary-stats">
            <div class="stat-card pass" role="button" tabindex="0" @click="onStatCardClick('pass')"><span class="stat-val">{{ report.pass_count }}</span><span class="stat-lbl">{{ $t('reportDetail.passLabel') }}</span></div>
            <div class="stat-card fail" role="button" tabindex="0" @click="onStatCardClick('failed')"><span class="stat-val">{{ report.fail_count }}</span><span class="stat-lbl">{{ $t('reportDetail.failLabel') }}</span></div>
            <div class="stat-card skip" role="button" tabindex="0" @click="onStatCardClick('skip')"><span class="stat-val">{{ report.skip_count || 0 }}</span><span class="stat-lbl">{{ $t('reportDetail.skipLabel') }}</span></div>
            <div class="stat-card total" role="button" tabindex="0" @click="onStatCardClick('all')"><span class="stat-val">{{ report.total_count }}</span><span class="stat-lbl">{{ $t('reportDetail.totalLabel') }}</span></div>
          </div>
        </div>
        <div class="summary-meta">
          <span>{{ report.scene_name || $t('reportDetail.unknownScene') }}</span>
          <span class="meta-dot">·</span>
          <span>{{ report.env_name || $t('reportDetail.testEnv') }}</span>
          <span class="meta-dot">·</span>
          <span>{{ report.duration }}s</span>
          <span class="meta-dot">·</span>
          <span>{{ formatTime(report.created_at) }}</span>
        </div>
        <div class="summary-note">
          <span class="summary-note-label">{{ $t('reportDetail.conclusion') }}</span>
          <span class="summary-note-text">{{ report.status === 'success' ? $t('reportDetail.conclusionStable') : $t('reportDetail.conclusionHasFailures') }}</span>
        </div>
      </div>

      <!-- 压测性能指标（stress 模式专用） -->
      <div class="stress-metrics-section" v-if="report?.stress_metrics">
      <div class="metrics-head"><h2>{{ $t('reportDetail.performanceMetrics') }}</h2></div>
      <div class="metrics-grid">
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.p50 ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.p50Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.p90 ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.p90Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.p95 ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.p95Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.p99 ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.p99Latency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.avg ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.avgLatency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.throughput ?? '-' }}/s</span>
          <span class="metrics-label">{{ $t('reportDetail.throughput') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value" :class="(report?.stress_metrics?.error_rate ?? 0) > 0 ? 'fail' : 'pass'">{{ report?.stress_metrics?.error_rate ?? '-' }}%</span>
          <span class="metrics-label">{{ $t('reportDetail.errorRate') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.min ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.minLatency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.max ?? '-' }}ms</span>
          <span class="metrics-label">{{ $t('reportDetail.maxLatency') }}</span>
        </div>
        <div class="metrics-card">
          <span class="metrics-value">{{ report?.stress_metrics?.total_requests ?? '-' }}</span>
          <span class="metrics-label">{{ $t('reportDetail.totalRequests') }}</span>
        </div>
      </div>
    </div>

    <!-- 步骤详情 -->
    <div v-if="report" class="steps-section" ref="stepsSectionRef">
      <div class="steps-head">
        <h2>{{ $t('reportDetail.stepDetails') }} ({{ filteredSteps.length }})</h2>
        <div class="steps-head-actions">
          <el-radio-group v-model="stepFilter" size="small">
            <el-radio-button value="all">{{ $t('reportDetail.allSteps') }}</el-radio-button>
            <el-radio-button value="failed">{{ $t('reportDetail.failedOnly') }}</el-radio-button>
          </el-radio-group>
          <el-button size="small" text @click="toggleAllSteps">
            {{ allExpanded ? $t('reportDetail.collapseAll') : $t('reportDetail.expandAll') }}
          </el-button>
        </div>
      </div>
      <div class="step-cards">
        <div v-for="(step, i) in filteredSteps" :key="(step as Record<string, unknown>).id ?? 'step-' + i + '-' + step.name" class="step-card" :class="{ expanded: isStepExpanded(i), failed: step.status === 'failed' || step.status === 'error' }">
          <!-- 步骤数据完整性校验 -->
          <template v-if="step && step.status">
            <div class="step-card-header" @click="toggleStep(i)">
              <span class="step-indicator" :class="step.status === 'error' ? 'failed' : step.status">
                <Check :size="12" v-if="step.status === 'success'" />
                <X :size="12" v-else-if="step.status === 'failed' || step.status === 'error'" />
                <span v-else style="opacity:0.5">−</span>
              </span>
              <span class="step-num">{{ step.label || `${$t('reportDetail.step')} ${step.sort_order || (i + 1)}` }}</span>
              <span class="method-badge" :class="(step.request_method || 'get').toLowerCase()">{{ step.request_method || '--' }}</span>
              <span class="step-url">{{ step.request_url || (step.label ? '' : $t('reportDetail.stepError')) }}</span>
              <div class="step-header-right">
                <span class="step-status-code">{{ step.response_status }}</span>
                <span class="step-duration">{{ step.duration ? Number(step.duration).toFixed(2) + 'ms' : '-' }}</span>
                <span v-if="step.error_message" class="step-error-msg" :title="step.error_message">{{ step.error_message }}</span>
                <a v-if="step.status === 'failed' && step.scene_step_id" class="step-jump-link" @click.stop.prevent="goToSceneStep(step.scene_step_id)" href="#">{{ $t('reportDetail.jumpToScene') }}</a>
                <span class="step-expand-icon">{{ isStepExpanded(i) ? '▼' : '▶' }}</span>
              </div>
            </div>
            <div class="step-card-body" :class="{ 'is-expanded': isStepExpanded(i) }">
              <!-- 请求信息 -->
              <div class="step-detail-section">
                <div class="step-detail-label">{{ $t('reportDetail.request') }}</div>
                <code v-if="step.request_method || step.request_url" class="step-detail-code">{{ step.request_method }} {{ step.request_url }}</code>
                <div v-if="step.error_message" class="step-detail-error">{{ step.error_message }}</div>
                <div v-if="step.request_headers && step.request_headers !== '{}' && step.request_headers !== 'null'" class="step-headers-list">
                  <div class="step-headers-title">Headers</div>
                  <table class="step-headers-table">
                    <thead><tr><th>Key</th><th>Value</th></tr></thead>
                    <tbody>
                      <tr v-for="(val, key) in parseJson(step.request_headers)" :key="key">
                        <td class="step-header-key">{{ key }}</td>
                        <td class="step-header-val">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="step.request_body && step.request_body !== 'null'" class="step-body-block">
                  <div class="step-headers-title">Body</div>
                  <pre class="step-body-pre">{{ formatJson(step.request_body) }}</pre>
                </div>
              </div>
              <!-- 响应信息 -->
              <div class="step-detail-section">
                <div class="step-detail-label">{{ $t('reportDetail.response') }}</div>
                <div class="step-response-meta">
                  <span class="step-meta-tag" :class="step.response_status >= 400 ? 'fail' : step.response_status >= 300 ? 'warn' : 'pass'">
                    {{ step.response_status || '-' }}
                  </span>
                  <span class="step-meta-duration">{{ step.duration ? Number(step.duration).toFixed(2) + 'ms' : '-' }}</span>
                </div>
                <div v-if="step.response_headers && step.response_headers !== '{}' && step.response_headers !== 'null'" class="step-headers-list">
                  <div class="step-headers-title">Headers</div>
                  <table class="step-headers-table">
                    <thead><tr><th>Key</th><th>Value</th></tr></thead>
                    <tbody>
                      <tr v-for="(val, key) in parseJson(step.response_headers)" :key="key">
                        <td class="step-header-key">{{ key }}</td>
                        <td class="step-header-val">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-if="step.response_body && step.response_body !== 'null'" class="step-body-block">
                  <div class="step-headers-title">Body</div>
                  <div class="response-body-wrapper">
                    <pre class="response-body">{{ formatJson(step.response_body) }}</pre>
                  </div>
                </div>
                <div v-if="(!step.response_body || step.response_body === 'null') && (!step.response_headers || step.response_headers === '{}' || step.response_headers === 'null')" class="step-detail-empty">~ {{ $t('reportDetail.noResponseData') }}</div>
              </div>
              <!-- 断言 -->
              <div class="step-detail-section">
                <div class="step-detail-label">{{ $t('reportDetail.assertion') }}</div>
                <div v-if="Array.isArray(step.assertions) && step.assertions.length">
                  <div v-for="(assert, ai) in step.assertions" :key="ai" class="assert-row" :class="assert.passed ? 'pass' : 'fail'">
                    <div class="assert-row-main">
                      <Check :size="12" v-if="assert.passed" class="assert-icon" />
                      <X :size="12" v-else class="assert-icon" />
                      <span class="assert-text">{{ assert.description || `${assert.type} ${assert.operator} ${assert.expected ?? assert.value ?? '?'}` }}</span>
                    </div>
                    <div v-if="!assert.passed && (assert.expected !== undefined || assert.actual !== undefined)" class="assert-compare">
                      <div class="diff-view">
                        <div class="diff-line diff-removed">
                          <span class="diff-prefix">-</span>
                          <span class="diff-label">{{ $t('reportDetail.expected') }}</span>
                          <code class="diff-value">{{ assert.expected ?? assert.value ?? '-' }}</code>
                        </div>
                        <div class="diff-line diff-added">
                          <span class="diff-prefix">+</span>
                          <span class="diff-label">{{ $t('reportDetail.actual') }}</span>
                          <code class="diff-value">{{ assert.actual ?? '-' }}</code>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-else class="step-detail-empty">~ {{ $t('reportDetail.none') }}</div>
              </div>
              <!-- 变量提取 -->
              <div class="step-detail-section">
                <div class="step-detail-label">{{ $t('reportDetail.variableExtract') }}</div>
                <div v-if="Array.isArray(step.extract_vars) && step.extract_vars.length">
                  <div v-for="(ev, ei) in step.extract_vars" :key="ei" class="extract-row">
                    <code>{{ ev.variable }}</code> = <code>{{ ev.value }}</code>
                  </div>
                </div>
                <div v-else class="step-detail-empty">~ {{ $t('reportDetail.none') }}</div>
              </div>
            </div>
          </template>
          <!-- 步骤数据异常提示 -->
          <div v-else class="step-card-error">
            <span class="step-error-icon">⚠</span>
            <span>{{ $t('reportDetail.stepDataError', { index: i + 1 }) }}</span>
          </div>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { msgSuccess, msgError } from '../utils/message'
import PageLayout from '../components/common/PageLayout.vue'

import { useRequireLogin } from '../composables/useRequireLogin'
import BreadcrumbNav from '../components/common/BreadcrumbNav.vue'
import type { BreadcrumbItem } from '../components/common/BreadcrumbNav.vue'
import { useProjectStore } from '../stores/projectStore'
import request from '../api/request'
import { getToken } from '../api/request'
import { downloadJson, downloadText } from '../utils/download'
import { exportRemoteFile as fetchRemoteFile, EmptyExportDataError } from '../utils/exporter'
import { ChevronLeft, Play, Download, Check, X } from 'lucide-vue-next'
import type { TestReport } from '../types'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { requireLogin } = useRequireLogin()
const projectStore = useProjectStore()
const projectId = Number(route.params.id)
const reportId = Number(route.params.reportId)
const report = ref<TestReport | null>(null)
const error = ref<string | null>(null)
const steps = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const rerunning = ref(false)
const deleting = ref(false)
const expandedStep = ref<number | null>(null)
const stepFilter = ref<'all' | 'failed'>('all')
const allExpanded = ref(false)

// 面包屑
const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
  const projectName = projectStore.projects.find((p) => p.id === projectId)?.name || t('reportDetail.project')
  return [
    { label: projectName, to: `/dashboard` },
    { label: t('reportDetail.testReport'), to: `/projects/${projectId}/reports` },
    { label: `${t('reportDetail.reportHash')}${reportId}` },
  ]
})

// PageLayout 标题与副标题
const reportTitle = computed(() => t('reportDetail.reportHash') + (report.value?.id ?? reportId))
const reportSubtitle = computed(() => {
  if (!report.value) return ''
  return `${report.value.scene_name || t('reportDetail.unknownScene')} · ${report.value.env_name || t('reportDetail.testEnv')} · ${formatTime(report.value.created_at)}`
})

// 环形图计算属性（零除数保护）
const ringRadius = 52
const ringCircumference = computed(() => 2 * Math.PI * ringRadius)
const ringDashOffset = computed(() => {
  const total = report.value?.total_count || 0
  const passed = report.value?.pass_count || 0
  return total === 0 ? ringCircumference.value : ringCircumference.value * (1 - passed / total)
})

function formatTime(t: string) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    if (isNaN(d.getTime())) return t
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch { return t }
}

function parseJson(str: unknown): Record<string, string> {
  try { return typeof str === 'string' ? JSON.parse(str) : str as Record<string, string> }
  catch { return {} }
}

const filteredSteps = computed(() => {
  const list = steps.value
  if (stepFilter.value === 'failed') {
    return list.filter((s) => s.status === 'failed' || s.status === 'error')
  }
  return list
})

function isStepExpanded(i: number) {
  return expandedStep.value === -1 || expandedStep.value === i
}

function toggleStep(i: number) {
  if (allExpanded.value) {
    allExpanded.value = false
    expandedStep.value = expandedStep.value === i ? null : i
  } else {
    expandedStep.value = expandedStep.value === i ? null : i
  }
}

function toggleAllSteps() {
  allExpanded.value = !allExpanded.value
  if (allExpanded.value) {
    expandedStep.value = -1
  } else {
    expandedStep.value = null
  }
}

function onStatCardClick(type: 'pass' | 'failed' | 'skip' | 'all') {
  if (type === 'failed' && report.value && report.value.fail_count > 0) {
    stepFilter.value = 'failed'
  } else {
    stepFilter.value = 'all'
  }
  void nextTick(() => {
    if (stepsSectionRef.value) {
      stepsSectionRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

const stepsSectionRef = ref<HTMLElement | null>(null)

async function loadReport() {
  loading.value = true
  error.value = null
  try {
    const res = await request.get(`/projects/${projectId}/reports/${reportId}`)
    report.value = res.data
    steps.value = res.data.steps || []
  } catch {
    error.value = t('reportDetail.loadReportFailed')
  } finally { loading.value = false }
}

function retryLoadReport() {
  msgSuccess(t('reportDetail.reloading'))
  void loadReport()
}

async function deleteReport() {
  if (!(await requireLogin(t('reportDetail.deleteReport')))) return
  if (deleting.value) return  // 防止重复提交
  deleting.value = true
  try {
    await request.delete(`/projects/${projectId}/reports/${reportId}`)
    msgSuccess(t('reportDetail.reportDeleted'))
    router.back()
  } catch {
    msgError(t('reportDetail.deleteFailed'))
  } finally {
    deleting.value = false
  }
}

// 默认展开第一个失败步骤或第一个步骤
watch(steps, (newSteps) => {
  if (newSteps.length) {
    const failedIdx = newSteps.findIndex((s) => s.status === 'failed')
    if (failedIdx >= 0) {
      stepFilter.value = 'failed'
      expandedStep.value = failedIdx
      // 自动滚动到失败步骤
      void nextTick(() => {
        if (stepsSectionRef.value) {
          stepsSectionRef.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      })
    } else {
      expandedStep.value = 0
    }
  }
}, { immediate: true })

function formatJson(str: string): string {
  try {
    const obj = JSON.parse(str)
    return JSON.stringify(obj, null, 2)
  } catch { return str }
}

async function rerunReport() {
  if (!(await requireLogin(t('reportDetail.rerun')))) return
  if (!report.value?.scene_id) { msgError(t('reportDetail.noSceneRerun')); return }
  rerunning.value = true
  try {
    const res = await request.post(`/projects/${projectId}/run/scene/${report.value.scene_id}?env_id=${report.value.environment_id || 1}`)
    msgSuccess(t('reportDetail.rerunStarted'))
    if (res.data?.report_id) {
      void router.push(`/projects/${projectId}/reports/${res.data.report_id}`)
    }
  } catch { msgError(t('reportDetail.rerunFailed')) }
  finally { rerunning.value = false }
}

/** 从报告步骤跳转到场景编辑，定位到指定步骤 */
function goToSceneStep(sceneStepId: number) {
  if (!report.value?.scene_id) return
  void router.push(`/projects/${projectId}/scenes?sceneId=${report.value.scene_id}&stepId=${sceneStepId}`)
}

async function exportRemoteFile(endpoint: string, filename: string, successMessage: string) {
  try {
    await fetchRemoteFile(endpoint, filename)
    msgSuccess(successMessage)
  } catch (e: unknown) {
    if (e instanceof EmptyExportDataError) {
      msgError(t('reportDetail.noExportData'))
      return
    }
    const err = e as { message?: string; code?: string }
    if (err.message?.includes('Network Error') || err.code === 'ERR_NETWORK' || err.message?.includes('ERR_')) {
      msgError(t('reportDetail.networkFailed'))
    } else {
      msgError(`${t('reportDetail.exportFailed')}：${err.message || ''}`)
    }
  }
}

async function handleExport(cmd: string) {
  if (cmd === 'json') {
    if (!report.value && steps.value.length === 0) {
      msgError(t('reportDetail.noExportData'))
      return
    }
    try {
      downloadJson({ report: report.value, steps: steps.value }, `report-${reportId}.json`)
      msgSuccess(t('reportDetail.jsonExported'))
    } catch (e: unknown) {
      const err = e as Error
      if (err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        msgError(t('reportDetail.networkFailed'))
      } else {
        msgError(`${t('reportDetail.exportFailed')}：${err.message || ''}`)
      }
    }
    return
  }

  if (cmd === 'html') {
    if (!report.value) {
      msgError(t('reportDetail.noExportData'))
      return
    }
    try {
      downloadText(generateHtmlReport(), `report-${reportId}.html`, 'text/html')
      msgSuccess(t('reportDetail.htmlExported'))
    } catch (e: unknown) {
      const err = e as Error
      if (err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        msgError(t('reportDetail.networkFailed'))
      } else {
        msgError(`${t('reportDetail.exportFailed')}：${err.message || ''}`)
      }
    }
    return
  }

  if (cmd === 'excel') {
    await exportRemoteFile(`/projects/${projectId}/reports/${reportId}/export/excel`, `report-${reportId}.xlsx`, t('reportDetail.excelExported'))
    return
  }

  if (cmd === 'pdf') {
    await exportRemoteFile(`/projects/${projectId}/reports/${reportId}/export/pdf`, `report-${reportId}.pdf`, t('reportDetail.pdfExported'))
    return
  }

  if (cmd === 'markdown') {
    try {
      const token = getToken('access_token')
      const headers: Record<string, string> = {}
      if (token) {
        headers['Authorization'] = 'Bearer ' + token
      }
      const res = await fetch(`/api/v1/projects/${projectId}/reports/${reportId}/export?format=markdown`, { headers })
      if (!res.ok) {
        const errorText = await res.text().catch(() => '')
        throw new Error(errorText || `HTTP ${res.status}`)
      }
      const text = await res.text()
      if (!text) {
        msgError(t('reportDetail.noExportData'))
        return
      }
      downloadText(text, `report-${reportId}.md`, 'text/markdown')
      msgSuccess(t('reportDetail.markdownExported'))
    } catch (e: unknown) {
      const err = e as Error
      if (err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError') || err.message?.includes('net::')) {
        msgError(t('reportDetail.networkFailed'))
      } else if (err.message?.includes('报告数据为空')) {
        msgError(err.message)
      } else {
        msgError(`${t('reportDetail.exportFailed')}：${err.message || ''}`)
      }
    }
  }
}

function generateHtmlReport(): string {
  const r = report.value
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${t('reportDetail.testReport')} ${reportId}</title>
</head><body>
<h1>${t('reportDetail.testReport')} #${reportId}</h1>
<div class="summary">
  <div class="card pass-card"><div style="font-size:30px;font-weight:700">${r?.pass_count ?? 0}</div><div>${t('reportDetail.passLabel')}</div></div>
  <div class="card fail-card"><div style="font-size:30px;font-weight:700">${r?.fail_count ?? 0}</div><div>${t('reportDetail.failLabel')}</div></div>
  <div class="card"><div style="font-size:30px;font-weight:700">${r?.total_count ?? 0}</div><div>${t('reportDetail.totalLabel')}</div></div>
</div>
<p>${t('reportDetail.conclusion')}: ${r?.status ?? '-'} | ${t('reportDetail.durationLabel')} ${r?.duration ?? 0}s | ${t('reportDetail.testEnv')}: ${r?.env_name || '-'} | ${t('reportDetail.stepDetails')}: ${r?.created_at ? formatTime(r.created_at) : '-'}</p>
<h2>${t('reportDetail.stepDetails')}</h2>
${steps.value.map((s, i: number) => {
  const dur = s.duration as number | undefined
  const durationStr = dur != null ? String(dur)+'ms' : ''
  return `
<div class="step">
  <div class="step-header">${i+1}. ${s.request_method} ${String(s.request_url)} — ${s.status} ${durationStr}</div>
  ${(s.assertions || []).map((a) => `<div class="assertion ${a.passed ? 'pass' : 'fail'}">${a.passed ? '✓' : '✗'} ${a.type} ${a.operator} ${a.value} ${a.passed ? '' : `(${t('reportDetail.expected')} ${a.expected}, ${t('reportDetail.actual')} ${a.actual})`}</div>`).join('')}
</div>`}).join('')}
</body></html>`
}

onMounted(loadReport)
</script>

<style scoped>
@import './ReportDetailView.css';

.filter-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.page-head-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.filter-bar :deep(.el-divider--vertical) {
  height: 1.2em;
  margin: 0 var(--space-1);
  border-color: var(--border-subtle);
}
</style>
