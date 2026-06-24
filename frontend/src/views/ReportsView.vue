<template>
  <PageLayout
    :title="$t('report.title')"
    compact
    :loading="loading"
    :empty="!loading && !error && filteredReports.length === 0"
    :empty-title="$t('report.noReports')"
    :empty-description="$t('report.noReportsDesc')"
    :empty-icon="BarChart3"
    :empty-illustration="'report'"
    :error="error"
    @retry="loadReports(currentPage)"
  >
    <template #hero-extra>
      <div class="reports-hero-summary" v-if="filteredReports.length > 0">
        {{ $t('report.totalPrefix') }} {{ total }} {{ $t('report.reportsMatchCondition') }} · {{ $t('report.passRate') }} <strong>{{ overallRate }}%</strong>
      </div>
    </template>

    <template #filter>
      <div class="page-head-left">
        <el-input
          v-model="searchQuery"
          :placeholder="$t('report.searchPlaceholder')"
          :aria-label="$t('report.searchPlaceholder')"
          clearable
          size="small"
          style="width: 220px"
          @keyup.enter.prevent
        >
          <template #prefix>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          </template>
        </el-input>
      </div>
      <div class="page-head-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          :start-placeholder="$t('report.startDate')"
          :end-placeholder="$t('report.endDate')"
          :shortcuts="dateShortcuts"
          size="small"
          style="width: 240px"
          value-format="YYYY-MM-DD"
          clearable
        />
        <el-select v-model="statusFilter" :placeholder="$t('report.statusFilterPlaceholder')" clearable size="small" style="width: 110px">
          <el-option :label="$t('report.success')" value="success" />
          <el-option :label="$t('report.failed')" value="failed" />
          <el-option :label="$t('report.running')" value="running" />
        </el-select>
        <el-button size="small" class="reset-btn" @click="resetFilters">
          {{ $t('report.resetFilters') }}
        </el-button>
      </div>
    </template>

    <template #empty-action>
      <el-button type="primary" size="small" @click="router.push(`/projects/${projectId}/scenes`)">
        {{ $t('report.goToScenes') }}
      </el-button>
    </template>

    <!-- 总览统计 -->
    <div class="report-summary" v-if="filteredReports.length > 0">
      <div class="summary-item">
        <span class="summary-value">{{ total }}</span>
        <span class="summary-label">{{ $t('report.totalReports') }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-value success">{{ successCount }}</span>
        <span class="summary-label">{{ $t('report.success') }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-value failed">{{ failedCount }}</span>
        <span class="summary-label">{{ $t('report.failed') }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-value skip">{{ skippedCount }}</span>
        <span class="summary-label">{{ $t('report.skipped') }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-value rate">{{ overallRate }}%</span>
        <span class="summary-label">{{ $t('report.passRate') }}</span>
      </div>
      <div class="summary-item trend-item">
        <div class="trend-chart" ref="trendChartRef"></div>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <Transition name="batch-actions-bar">
      <div v-if="selectedReports.size > 0" class="batch-actions-bar">
        <span class="batch-tips">{{ $t('report.selectedCount', { count: selectedReports.size }) }}</span>
        <div class="batch-buttons">
          <el-button size="small" type="danger" plain :loading="batchDeleting" @click="batchDelete">{{ $t('report.batchDelete') }}</el-button>
          <el-button size="small" @click="clearSelection">{{ $t('report.clearSelection') }}</el-button>
        </div>
      </div>
    </Transition>

    <div class="report-cards" :key="reportsKey">
      <div
        ref="scrollContainer"
        :style="enabled ? { overflowY: 'auto', maxHeight: '600px' } : undefined"
      >
        <div :style="totalHeightStyle">
          <div :style="offsetStyle">
            <div v-for="r in visibleItems" :key="r.id" class="report-card" :class="r.status">
        <div class="report-card-bar" :class="r.status"></div>
        <el-checkbox
          class="report-checkbox"
          :model-value="selectedReports.has(r.id)"
          @change="(val: boolean) => toggleSelect(r.id, val)"
          @click.stop
          :title="$t('report.selectReport')"
        />
        <div class="report-card-body" @click="goToDetail(r.id)">
          <div class="report-card-top">
            <span class="status-tag" :class="r.displayStatus === 'success' ? 'success' : r.displayStatus === 'failed' ? 'failed' : r.displayStatus === 'interrupted' ? 'warning' : r.displayStatus === 'running' ? 'warning' : ''">
              {{ statusLabel(r.displayStatus || r.status) }}
            </span>
          </div>
          <div class="report-card-meta">
            <span class="scene-name">{{ r.scene_name || $t('report.sceneLabel') }}</span>
            <div class="meta-row">
              <span class="env-name">{{ r.env_name || $t('report.testEnv') }}</span>
              <span class="meta-sep">·</span>
              <span class="create-time">{{ formatTime(r.created_at) }}</span>
              <span class="meta-sep">·</span>
              <span class="report-card-id">#{{ r.id }}</span>
            </div>
          </div>
          <div class="report-card-progress">
            <div class="progress-track">
              <div class="progress-pass" :style="{ width: (r.total_count ? (r.pass_count / r.total_count) * 100 : 0) + '%' }"></div>
              <div class="progress-fail" :style="{ width: (r.total_count ? (r.fail_count / r.total_count) * 100 : 0) + '%' }"></div>
            </div>
            <div class="progress-stats">
              <span class="stat-pass">{{ r.pass_count }}/{{ r.total_count }} {{ $t('report.passLabel') }}</span>
              <span class="stat-pct" :class="passRateClass(r)">{{ r.total_count ? Math.round(r.pass_count / r.total_count * 100) : 0 }}%</span>
              <span class="stat-duration" :class="durationColor(r.duration)">{{ r.duration ? Number(r.duration).toFixed(2) + 's' : '-' }}</span>
            </div>
          </div>
          <div class="report-card-actions" @click.stop>
            <el-tooltip :content="$t('report.exportReport')" placement="top">
              <el-dropdown trigger="click" @command="(cmd: string) => handleExport(r.id, cmd)" :disabled="exportingId !== null">
                <el-button link type="primary" size="small" :disabled="exportingId !== null && exportingId !== r.id" :aria-label="$t('report.exportReport')">
                  <Download :size="12" v-if="exportingId !== r.id" />
                  <el-icon v-else class="is-loading"><svg viewBox="0 0 1024 1024"><path d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/></svg></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="excel">{{ $t('report.exportExcel') }}</el-dropdown-item>
                    <el-dropdown-item command="pdf">{{ $t('report.exportPdf') }}</el-dropdown-item>
                    <el-dropdown-item command="csv" divided>{{ $t('report.exportCsvDetail') }}</el-dropdown-item>
                    <el-dropdown-item command="csv_summary">{{ $t('report.exportCsvSummary') }}</el-dropdown-item>
                    <el-dropdown-item command="junit" divided>{{ $t('report.exportJunit') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-tooltip>
            <el-tooltip :content="$t('report.rerun')" placement="top">
              <el-button link type="primary" size="small" @click="handleRerun(r.id)">{{ $t('report.rerunBtn') }}</el-button>
            </el-tooltip>
            <el-tooltip :content="r.share_token ? $t('report.shareViewEdit') : $t('report.shareDialogTitle')" placement="top">
              <el-button link type="primary" size="small" @click="handleShare(r.id)">{{ r.share_token ? $t('report.shared') : $t('report.share') }}</el-button>
            </el-tooltip>
            <el-tooltip :content="$t('report.compare')" placement="top">
              <el-button link type="primary" size="small" @click="handleCompare(r.id)">{{ $t('report.compare') }}</el-button>
            </el-tooltip>
            <el-tooltip :content="$t('report.delete')" placement="top">
              <el-button link type="danger" size="small" @click="confirmDelete(r.id)" aria-label="删除报告">{{ $t('report.delete') }}</el-button>
            </el-tooltip>
          </div>
        </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-pagination background layout="prev,pager,next" :total="total" :page-size="20" :current-page="currentPage" @current-change="loadReports" />
    </template>

    <!-- 分享弹窗 -->
    <el-dialog v-model="shareDialog.visible" :title="$t('report.shareDialogTitle')" width="440px">
      <div v-if="shareDialog.link" class="share-box">
        <p class="share-desc">
          {{ $t('report.shareLinkDesc') }}
        </p>
        <div class="share-link-row">
          <el-input :model-value="shareDialog.link" readonly size="small" :aria-label="$t('report.shareDialogTitle')" />
          <el-button type="primary" size="small" @click="copyReportShareLink" >{{ $t('report.copyLink') }}</el-button>
        </div>
        <div style="margin-top:var(--space-4);text-align:right">
          <el-button size="small" type="danger" text @click="cancelReportShare">{{ $t('report.cancelShare') }}</el-button>
        </div>
      </div>
      <div v-else>
        <p class="share-desc">
          {{ $t('report.generateLinkDesc') }}
        </p>
        <div class="share-options">
          <div class="share-option-row">
            <label class="share-option-label">{{ $t('reportDetail.expiryTime') }}</label>
            <el-radio-group v-model="shareDialog.expiresIn" size="small">
              <el-radio-button :value="1">{{ $t('reportDetail.oneDay') }}</el-radio-button>
              <el-radio-button :value="7">{{ $t('reportDetail.sevenDays') }}</el-radio-button>
              <el-radio-button :value="30">{{ $t('reportDetail.thirtyDays') }}</el-radio-button>
              <el-radio-button :value="0">{{ $t('reportDetail.neverExpire') }}</el-radio-button>
            </el-radio-group>
          </div>
          <div class="share-option-row">
            <label class="share-option-label">{{ $t('reportDetail.accessPassword') }}</label>
            <el-input
              v-model="shareDialog.password"
              size="small"
              :placeholder="$t('reportDetail.passwordPlaceholder')"
              :aria-label="$t('reportDetail.accessPassword')"
              clearable
              style="width: 220px"
              type="password"
              show-password
            />
          </div>
        </div>
        <el-button type="primary" size="small" :loading="shareLock.loading.value" :disabled="shareLock.disabled.value" @click="createReportShare" style="margin-top: var(--space-3)">{{ $t('report.generateLink') }}</el-button>
      </div>
    </el-dialog>

    <!-- 对比弹窗 -->
    <el-dialog v-model="compareDialog.visible" :title="$t('report.compareDialogTitle')" width="560px" @open="loadCompare">
      <template v-if="compareDialog.loading">
        <div style="text-align:center;padding:var(--space-6);color:var(--text-secondary)">
          <el-icon class="is-loading"><svg viewBox="0 0 1024 1024"><path d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32z"/></svg></el-icon>
          {{ $t('report.loading') }}
        </div>
      </template>
      <template v-else-if="compareDialog.error">
        <div style="text-align:center;padding:var(--space-6);color:var(--color-error)">
          <div style="margin-bottom:var(--space-3)">{{ compareDialog.error }}</div>
          <el-button type="primary" size="small" @click="loadCompare">{{ $t('report.reload') }}</el-button>
        </div>
      </template>
      <template v-else-if="compareDialog.data && compareDialog.data.previous">
        <div class="compare-grid">
          <div class="compare-side">
            <div class="compare-label">{{ $t('report.currentReport') }}{{ compareDialog.data.current.id }}</div>
            <div class="compare-time">{{ formatTime(compareDialog.data.current.created_at) }}</div>
            <div class="compare-stat" :class="compareDialog.data.current.status">
              {{ compareDialog.data.current.status === 'success' ? $t('report.passed') : $t('report.failed') }}
              {{ compareDialog.data.current.pass_count }}/{{ compareDialog.data.current.total_count }}
            </div>
            <div class="compare-duration">{{ compareDialog.data.current.duration }}s</div>
          </div>
          <div class="compare-vs">VS</div>
          <div class="compare-side">
            <div class="compare-label">{{ $t('report.compareReport') }}{{ compareDialog.data.previous.id }}</div>
            <div class="compare-time">{{ formatTime(compareDialog.data.previous.created_at) }}</div>
            <div class="compare-stat" :class="compareDialog.data.previous.status">
              {{ compareDialog.data.previous.status === 'success' ? $t('report.passed') : $t('report.failed') }}
              {{ compareDialog.data.previous.pass_count }}/{{ compareDialog.data.previous.total_count }}
            </div>
            <div class="compare-duration">{{ compareDialog.data.previous.duration }}s</div>
          </div>
        </div>
        <div class="compare-summary">
          <span v-if="compareDialog.data.current.total_count === compareDialog.data.previous.total_count">
            {{ $t('report.casesUnchanged', { count: compareDialog.data.current.total_count }) }}
          </span>
          <span v-else :class="compareDialog.data.current.total_count > compareDialog.data.previous.total_count ? 'up' : 'down'">
            {{ $t('report.caseCount') }} {{ compareDialog.data.current.total_count > compareDialog.data.previous.total_count ? '+' : '' }}{{ compareDialog.data.current.total_count - compareDialog.data.previous.total_count }}
          </span>
          <span class="compare-divider">|</span>
          <span :class="compareDialog.data.current.pass_count >= compareDialog.data.previous.pass_count ? 'up' : 'down'">
            {{ $t('report.passCount') }} {{ compareDialog.data.current.pass_count >= compareDialog.data.previous.pass_count ? '+' : '' }}{{ compareDialog.data.current.pass_count - compareDialog.data.previous.pass_count }}
          </span>
          <span class="compare-divider">|</span>
          <span :class="compareDialog.data.current.duration <= compareDialog.data.previous.duration ? 'up' : 'down'">
            {{ $t('report.durationLabel') }} {{ compareDialog.data.current.duration <= compareDialog.data.previous.duration ? '' : '+' }}{{ ((compareDialog.data.current.duration || 0) - (compareDialog.data.previous.duration || 0)).toFixed(1) }}s
          </span>
        </div>
      </template>
      <div v-else style="text-align:center;padding:var(--space-6);color:var(--text-secondary)">{{ $t('report.noHistory') }}</div>
    </el-dialog>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { msgSuccess, msgError } from '../utils/message'
import { ElMessageBox } from 'element-plus'
import request from '../api/request'
import { useRequireLogin } from '../composables/useRequireLogin'
import { useVirtualScroll } from '../composables/useVirtualScroll'
import { useSubmitLock } from '../composables/useSubmitLock'
import { useAsync } from '../composables/useAsync'
import { downloadBlob } from '../utils/download'
import PageLayout from '../components/common/PageLayout.vue'

import { BarChart3, Download } from 'lucide-vue-next'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { TestReport } from '../types'
import type { ApiError } from '../types/common'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => Number(route.params.id))
const reports = ref<TestReport[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref('')
const reportsKey = ref(0)
const searchQuery = ref('')
const dateRange = ref<[string, string] | null>(null)
const dateShortcuts = [
  { text: t('report.today'), value: () => { const s = new Date(); s.setHours(0,0,0,0); return [s.toLocaleDateString('sv-SE'), new Date().toLocaleDateString('sv-SE')] as [string, string] } },
  { text: t('report.last7Days'), value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 7); s.setHours(0,0,0,0); return [s.toLocaleDateString('sv-SE'), e.toISOString().slice(0,10)] as [string, string] } },
  { text: t('report.last30Days'), value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 30); s.setHours(0,0,0,0); return [s.toLocaleDateString('sv-SE'), e.toISOString().slice(0,10)] as [string, string] } },
]
const currentPage = ref(1)
const { requireLogin } = useRequireLogin()
const shareLock = useSubmitLock()
const selectedReports = ref<Set<number>>(new Set())
const batchDeleting = ref(false)
const trendChartRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
const trendData = ref<Array<{ date: string; total: number; passed: number; failed: number }>>([])

// running 状态超时检测（10分钟）
const REPORT_RUNNING_TIMEOUT_MS = 10 * 60 * 1000

function normalizeReportStatus(report: TestReport) {
  if (report.status === 'running') {
    const updatedAt = new Date(report.updated_at || report.created_at || '').getTime()
    if (!isNaN(updatedAt) && Date.now() - updatedAt > REPORT_RUNNING_TIMEOUT_MS) {
      return { ...report, displayStatus: 'interrupted' as const }
    }
  }
  return { ...report, displayStatus: report.status || '' }
}

const trendAsync = useAsync<{ date: string; total: number; passed: number; failed: number }[]>()

async function loadTrendData() {
  const result = await trendAsync.execute(async () => {
    const res = await request.get(`/projects/${projectId.value}/reports/trend`, { params: { days: 30 } })
    return res.data || []
  })
  trendData.value = result || []
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  if (trendChart) trendChart.dispose()
  const cssVar = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
  const isDark = document.documentElement.classList.contains('dark')
  trendChart = echarts.init(trendChartRef.value, isDark ? 'dark' : undefined)
  const _textColor = cssVar('--text-secondary', '#64748b')
  const _lineColor = cssVar('--border-default', '#d2d4dc')
  const _successColor = cssVar('--color-success', '#3dcb85')
  const _failColor = cssVar('--color-error', '#d95c5c')
  const primaryColor = cssVar('--primary-500', '#7488c8')

  const data = trendData.value
  if (!data.length) {
    // 无趋势数据时使用当前页报告数据兜底
    const passRates = filteredReports.value.slice().reverse().map((r) => {
      return r.total_count ? Math.round(r.pass_count / r.total_count * 100) : 0
    })
    const labels = filteredReports.value.slice().reverse().map((r) => {
      return r.created_at ? new Date(r.created_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) : ''
    })
    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: cssVar('--surface-card', '#fdfdff'),
        borderColor: cssVar('--border-default', '#d2d4dc'),
        textStyle: { color: cssVar('--text-primary', '#1f2533'), fontSize: 11 },
        formatter: (params: { name: string; value: number; dataIndex: number }[]) => {
          const p = params?.[0]
          if (!p) return ''
          return `${labels[p.dataIndex ?? 0]}<br/>${t('report.passRate')}: <b>${p.value ?? 0}%</b>`
        },
      },
      grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: false },
      xAxis: { type: 'category', data: labels, show: false },
      yAxis: { type: 'value', min: 0, max: 100, show: false },
      series: [{
        type: 'line',
        data: passRates,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: primaryColor },
        itemStyle: { color: primaryColor },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: primaryColor + '30' },
              { offset: 1, color: primaryColor + '00' },
            ],
          },
        },
      }],
    })
    return
  }

  const labels = data.map(d => {
    const dt = new Date(d.date)
    return dt.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  })
  const passRates = data.map(d => d.total > 0 ? Math.round(d.passed / d.total * 100) : 0)
  const failRates = data.map(d => d.total > 0 ? Math.round(d.failed / d.total * 100) : 0)

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: cssVar('--surface-card', '#fdfdff'),
      borderColor: cssVar('--border-default', '#d2d4dc'),
      textStyle: { color: cssVar('--text-primary', '#1f2533'), fontSize: 11 },
      formatter: (params: { seriesName: string; name: string; value: number; dataIndex: number }[]) => {
        if (!params?.length) return ''
        const di = params[0].dataIndex ?? 0
        const d = data[di]
        if (!d) return ''
        return `${d.date}<br/>${t('report.totalCases')}: <b>${d.total}</b><br/>${t('report.passCases')}: <b style="color:${_successColor}">${d.passed}</b><br/>${t('report.failCases')}: <b style="color:${_failColor}">${d.failed}</b><br/>${t('report.passRate')}: <b>${passRates[di]}%</b>`
      },
    },
    grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: false },
    xAxis: { type: 'category', data: labels, show: false },
    yAxis: { type: 'value', min: 0, max: 100, show: false },
    series: [
      {
        name: t('report.passRate'),
        type: 'line',
        data: passRates,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: _successColor },
        itemStyle: { color: _successColor },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: _successColor + '25' },
              { offset: 1, color: _successColor + '00' },
            ],
          },
        },
      },
      {
        name: t('report.failCases'),
        type: 'line',
        data: failRates,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: _failColor },
        itemStyle: { color: _failColor },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: _failColor + '15' },
              { offset: 1, color: _failColor + '00' },
            ],
          },
        },
      },
    ],
  })
}

function toggleSelect(id: number, val: boolean) {
  if (val) selectedReports.value.add(id)
  else selectedReports.value.delete(id)
  selectedReports.value = new Set(selectedReports.value)
}

function clearSelection() {
  selectedReports.value = new Set()
}

async function batchDelete() {
  if (!(await requireLogin(t('report.batchDelete')))) return
  const ids = Array.from(selectedReports.value)
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(
      t('report.batchDeleteConfirm', { count: ids.length }),
      t('report.batchDelete'),
      { confirmButtonText: t('report.deleteBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    await Promise.all(ids.map(id => request.delete(`/projects/${projectId.value}/reports/${id}`)))
    msgSuccess(t('report.deleted'))
    clearSelection()
    await loadReports()
  } catch { msgError(t('report.batchDeleteFailed')) }
  finally { batchDeleting.value = false }
}

const exportingId = ref<number | null>(null)
async function handleExport(id: number, type: string) {
  if (exportingId.value !== null) return
  exportingId.value = id
  try {
    const url = `/projects/${projectId.value}/reports/${id}/export/${type}`
    let filename = `report_${id}`
    switch (type) {
      case 'excel': filename += '.xlsx'; break
      case 'pdf': filename += '.pdf'; break
      case 'csv': filename += '_detail.csv'; break
      case 'csv_summary': filename += '_summary.csv'; break
      case 'junit': filename += '.xml'; break
      default: filename += '.bin'
    }

    const blob = await request.get(url, { responseType: 'blob' }) as unknown as Blob
    downloadBlob({ blob, filename })
    msgSuccess(t('report.exportSuccess'))
  } catch (e: unknown) {
    // 错误响应也是 Blob，需转为 JSON 后解析错误信息
    const err = e as ApiError & { response?: { data?: Blob } }
    const blobData = err?.response?.data
    if (blobData instanceof Blob) {
      try {
        const text = await blobData.text()
        const json = JSON.parse(text)
        msgError(json.message || t('report.exportFailed'))
      } catch {
        msgError(t('report.exportFailed'))
      }
    } else {
      msgError(t('report.exportFailed'))
    }
  } finally {
    exportingId.value = null
  }
}

const shareDialog = reactive({ visible: false, reportId: null as number | null, link: '', expiresIn: 7, password: '' })

async function handleShare(id: number) {
  shareDialog.reportId = id
  shareDialog.visible = true
  shareDialog.link = ''
  shareDialog.expiresIn = 7
  shareDialog.password = ''
  try {
    const res = await request.get(`/projects/${projectId.value}/reports/${id}/share`)
    const shareToken = res.data?.share_token ?? res.data?.data?.share_token
    shareDialog.link = shareToken ? location.origin + location.pathname + '#/shared/' + shareToken : ''
  } catch { msgError(t('report.generateFailed')) }
}

const createReportShare = () => shareLock.run(async () => {
  try {
    const params: Record<string, string | number> = { expires_in_days: shareDialog.expiresIn }
    if (shareDialog.password) params.password = shareDialog.password
    const res = await request.post(`/projects/${projectId.value}/reports/${shareDialog.reportId}/share`, null, { params })
    const shareToken = res.data?.share_token ?? res.data?.data?.share_token
    shareDialog.link = shareToken ? location.origin + location.pathname + '#/shared/' + shareToken : ''
    msgSuccess(t('report.shareLinkGenerated'))
  } catch { msgError(t('report.generateFailed')) }
})

async function cancelReportShare() {
  try {
    await request.delete(`/projects/${projectId.value}/reports/${shareDialog.reportId}/share`)
    shareDialog.link = ''
    msgSuccess(t('report.shareCancelled'))
  } catch { msgError(t('report.cancelShareFailed')) }
}

function copyReportShareLink() {
  navigator.clipboard.writeText(shareDialog.link).then(
    () => msgSuccess(t('report.linkCopied')),
    () => msgError(t('report.copyFailed'))
  )
}

const compareDialog = reactive({
  visible: false,
  reportId: null as number | null,
  data: null as { current: TestReport; previous: TestReport } | null,
  loading: false,
  error: null as string | null,
})

function handleCompare(id: number) {
  compareDialog.reportId = id
  compareDialog.data = null
  compareDialog.error = null
  compareDialog.visible = true
}

const compareAsync = useAsync<{ current: TestReport; previous: TestReport }>()

async function loadCompare() {
  compareDialog.loading = true
  compareDialog.error = null
  const result = await compareAsync.execute(async () => {
    const res = await request.get(`/projects/${projectId.value}/reports/${compareDialog.reportId}/compare`)
    return res.data
  })
  if (result) {
    compareDialog.data = result
    // 后端返回 message 表示无对比报告，展示为提示而非错误
    if ((result as Record<string, unknown>).message) {
      compareDialog.error = String((result as Record<string, unknown>).message)
    }
  } else {
    compareDialog.data = null
    compareDialog.error = compareAsync.error.value || t('report.loadFailedMsg')
  }
  compareDialog.loading = false
}

function formatTime(t: string) {
  if (!t) return '-'
  try {
    const d = new Date(t)
    if (isNaN(d.getTime())) return t
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch { return t }
}

function statusLabel(s: string) {
  if (s === 'interrupted') return t('report.interrupted')
  if (s === 'empty') return t('report.noSteps')
  if (s === 'timeout') return t('report.timeout')
  return s === 'success' ? t('report.success') : s === 'failed' ? t('report.failed') : s === 'running' ? t('report.running') : s
}

function passRateClass(row: TestReport) {
  if (!row.total_count) return ''
  const pct = row.pass_count / row.total_count
  if (pct >= 0.8) return 'high'
  if (pct >= 0.5) return 'medium'
  return 'low'
}

function durationColor(d: string) {
  if (!d) return ''
  const sec = parseFloat(d)
  if (isNaN(sec)) return ''
  if (sec < 2) return 'fast'
  if (sec < 5) return 'ok'
  return 'slow'
}

async function loadReports(page = currentPage.value) {
  currentPage.value = page
  loading.value = true
  try {
    const params: Record<string, string | number> = { page, page_size: 20 }
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value.trim()) params.keyword = searchQuery.value.trim()
    if (dateRange.value?.[0]) params.start_date = dateRange.value[0]
    if (dateRange.value?.[1]) params.end_date = dateRange.value[1]
    const res = await request.get(`/projects/${projectId.value}/reports`, { params })
    const totalItems = res.data?.total || 0
    const totalPages = Math.ceil(totalItems / 20) || 1
    // 如果当前页超出总页数，修正到最后一页并重新加载
    if (page > totalPages && page > 1) {
      loading.value = false
      return loadReports(totalPages)
    }
    reports.value = (res.data?.items || []).map(normalizeReportStatus)
    total.value = totalItems
    reportsKey.value++
    void nextTick(() => scrollToTop())
  } catch (e: unknown) {
    const err = e as ApiError
    if (err?.response?.status !== 401) {
      error.value = t('report.loadFailedMsg')
    }
  } finally { loading.value = false }
}

function resetFilters() {
  searchQuery.value = ''
  dateRange.value = null
  statusFilter.value = ''
  void loadReports(1)
}

async function handleRerun(id: number) {
  const report = reports.value.find((r) => r.id === id)
  if (!report?.scene_id) { msgError(t('report.noSceneRerun')); return }
  try {
    const res = await request.post(`/projects/${projectId.value}/run/scene/${report.scene_id}?env_id=${report.environment_id || 1}`)
    if (res.data?.report_id) {
      msgSuccess(t('report.rerunStartedMsg'))
      // 直接跳转到新报告详情页
      void router.push(`/projects/${projectId.value}/reports/${res.data.report_id}`)
    }
  } catch { msgError(t('report.rerunFailedMsg')) }
}

function goToDetail(id: number) {
  void router.push(`/projects/${projectId.value}/reports/${id}`)
}

async function confirmDelete(id: number) {
  try {
    await ElMessageBox.confirm(
      t('report.deleteConfirmMsg'),
      t('report.deleteDialogTitle'),
      { confirmButtonText: t('report.deleteBtn'), cancelButtonText: t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  if (!(await requireLogin(t('report.delete')))) return
  try {
    await request.delete(`/projects/${projectId.value}/reports/${id}`)
    msgSuccess(t('report.deleted'))
    void loadReports()
  } catch { msgError(t('report.deleteFailed')) }
}

watch([statusFilter], () => { currentPage.value = 1; void loadReports(1) })

// searchQuery 防抖：300ms 内连续输入只触发一次请求
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 1
    void loadReports()
  }, 300)
})

watch([dateRange], () => { currentPage.value = 1; void loadReports() })

// 服务端已按 keyword/dateRange/status 过滤，客户端直接使用服务端返回数据
const filteredReports = computed(() => reports.value)

const paginatedReports = computed(() => reports.value)

const {
  visibleItems,
  totalHeightStyle,
  offsetStyle,
  scrollContainer,
  enabled,
  scrollToTop,
} = useVirtualScroll(paginatedReports, {
  itemHeight: 120,
  threshold: 50,
  containerHeight: 600,
})

const successCount = computed(() => filteredReports.value.filter((r) => r.status === 'success').length)
const failedCount = computed(() => filteredReports.value.filter((r) => r.status === 'failed').length)
const skippedCount = computed(() => filteredReports.value.reduce((sum: number, r) => sum + (r.skip_count || 0), 0))
const overallRate = computed(() => {
  if (!filteredReports.value.length) return 0
  const totalPass = filteredReports.value.reduce((sum: number, r) => sum + (r.pass_count || 0), 0)
  const totalCount = filteredReports.value.reduce((sum: number, r) => sum + (r.total_count || 0), 0)
  return totalCount ? Math.round(totalPass / totalCount * 100) : 0
})

onMounted(() => {
  void loadReports(); void loadTrendData().then(() => nextTick(() => renderTrendChart()))
  // 监听场景执行完成事件，自动刷新报告列表
  window.addEventListener('scene:complete', _onSceneComplete)
})

watch(() => route.params.id, () => {
  void loadReports()
  void loadTrendData().then(() => nextTick(() => renderTrendChart()))
})
let _sceneCompleteTimer: ReturnType<typeof setTimeout> | null = null
function _onSceneComplete() {
  // 执行完成后自动刷新列表（带 500ms 延迟等待后端写入）
  _sceneCompleteTimer = setTimeout(() => { void loadReports() }, 500)
}
onUnmounted(() => {
  try {
    window.removeEventListener('scene:complete', _onSceneComplete)
    if (_sceneCompleteTimer) clearTimeout(_sceneCompleteTimer)
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  } catch { /* ignore cleanup error */ }
  try {
    trendChart?.dispose()
    trendChart = null
  } catch { /* ignore dispose error */ }
})

watch([statusFilter, filteredReports], () => { void nextTick(() => renderTrendChart()) })
import "./ReportsView.css"
</script>



<style scoped>
</style>
