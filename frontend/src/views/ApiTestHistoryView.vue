<template>
  <div class="api-test-history-page">
    <div class="page-header history-hero">
      <div class="header-left">
        <div class="history-hero-kicker">{{ t('testHistory.kicker') }}</div>
        <h2 class="page-title">{{ t('testHistory.title') }}</h2>
        <span class="page-subtitle" v-if="apiInfo">
          {{ apiInfo.method }} {{ apiInfo.path }}
        </span>
        <div class="history-hero-note">{{ t('testHistory.note') }}</div>
        <div class="history-hero-chip-row">
          <span class="history-hero-chip">{{ t('testHistory.successResponseCount', { count: successResponseCount }) }}</span>
          <span class="history-hero-chip">{{ t('testHistory.slowRequestCount', { count: slowRequestCount }) }}</span>
          <span class="history-hero-chip">{{ t('testHistory.peakDuration', { duration: peakDuration }) }}</span>
        </div>
      </div>
      <div class="history-hero-stats">
        <div class="history-stat"><span class="history-stat-val">{{ historyList.length }}</span><span class="history-stat-lbl">{{ t('testHistory.totalRecords') }}</span></div>
        <div class="history-stat"><span class="history-stat-val">{{ successStatusCount }}</span><span class="history-stat-lbl">{{ t('testHistory.success') }}</span></div>
        <div class="history-stat"><span class="history-stat-val">{{ failedStatusCount }}</span><span class="history-stat-lbl">{{ t('testHistory.failed') }}</span></div>
      </div>
      <div class="header-right">
        <el-button size="small" text @click="refresh">
          <Refresh :size="14" /> {{ t('testHistory.refresh') }}
        </el-button>
        <el-button v-if="historyList.length > 0" size="small" text type="danger" @click="clearAllHistory">
          <Delete :size="14" /> {{ t('testHistory.clearAll') }}
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-group">
        <el-select v-model="filters.status" :placeholder="t('testHistory.status')" clearable size="small" class="filter-item">
          <el-option :label="t('testHistory.success')" value="success" />
          <el-option :label="t('testHistory.failed')" value="failed" />
          <el-option :label="t('testHistory.error')" value="error" />
        </el-select>

        <el-select
          v-if="environments.length > 0"
          v-model="filters.environment_id"
          :placeholder="t('testHistory.environment')"
          clearable
          size="small"
          class="filter-item"
        >
          <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          :range-separator="t('testHistory.to')"
          :start-placeholder="t('testHistory.startDate')"
          :end-placeholder="t('testHistory.endDate')"
          size="small"
          class="filter-item date-range-picker"
          value-format="YYYY-MM-DD"
        />

        <el-button type="primary" size="small" :loading="loading" @click="loadHistory">
          <Search :size="14" /> {{ t('testHistory.search') }}
        </el-button>

        <el-button v-if="hasActiveFilters" size="small" @click="resetFilters">
          {{ t('testHistory.reset') }}
        </el-button>
      </div>
    </div>

    <div class="history-content">
      <div v-if="loading" class="loading-state">
        <div class="skeleton-list">
          <div v-for="i in 10" :key="i" class="skeleton-item">
            <div class="skeleton-line"></div>
          </div>
        </div>
      </div>

      <EmptyState
        v-else-if="historyError"
        illustration="data"
        :title="t('testHistory.loadFailed')"
        :description="historyError"
      >
        <template #action>
          <el-button type="primary" size="small" @click="loadHistory">{{ t('testHistory.reload') }}</el-button>
        </template>
      </EmptyState>

      <EmptyState
        v-else-if="!historyList.length"
        illustration="data"
        :title="t('testHistory.noHistory')"
        :description="hasActiveFilters ? t('testHistory.noHistoryFiltered') : t('testHistory.noHistoryDesc')"
      >
        <template v-if="!hasActiveFilters" #action>
          <el-button type="primary" size="small" @click="goToApiDetail">{{ t('testHistory.goToTest') }}</el-button>
        </template>
      </EmptyState>

      <div v-else class="history-table-wrapper">
        <el-table :data="historyList" stripe size="small" class="history-table" @row-click="showDetail">
          <el-table-column prop="id" :label="t('testHistory.id')" width="80" class-name="hide-mobile" />

          <el-table-column :label="t('testHistory.status')" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small" effect="plain">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.requestMethod')" width="100" align="center">
            <template #default="{ row }">
              <el-tag :class="String(row.request_method || '').toLowerCase()" size="small" effect="plain">
                {{ row.request_method || '--' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.requestUrl')" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <code class="url-text">{{ row.request_url || '-' }}</code>
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.responseStatus')" width="100" align="center">
            <template #default="{ row }">
              <span
                v-if="row.response_status"
                :class="Number(row.response_status) < 400 ? 'status-success' : 'status-error'"
                class="status-code"
              >
                {{ row.response_status }}
              </span>
              <span v-else class="status-unknown">-</span>
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.duration')" width="100" align="right" class-name="hide-mobile">
            <template #default="{ row }">
              <code class="duration-text">{{ formatDuration(row.duration) }}</code>
            </template>
          </el-table-column>

          <el-table-column v-if="showEnvColumn" :label="t('testHistory.environment')" width="120" class-name="hide-mobile">
            <template #default="{ row }">
              {{ getEnvName(row.environment_id) }}
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.executionTime')" width="180" class-name="hide-mobile">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>

          <el-table-column :label="t('testHistory.action')" width="150" fixed="right" align="center">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click.stop="showDetail(row)">
                {{ t('testHistory.detail') }}
              </el-button>
              <el-button v-if="row.status === 'success'" size="small" text @click.stop="reuseRequest(row)">
                {{ t('testHistory.reuse') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="total > pageSize" class="pagination-bar">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            background
            size="small"
          />
        </div>
      </div>
    </div>

    <el-drawer v-model="showDetailDrawer" :title="t('testHistory.testDetail')" direction="rtl" size="600px" :destroy-on-close="true">
      <div v-if="selectedHistory" class="detail-content">
        <div class="detail-section">
          <h3 class="section-title">{{ t('testHistory.basicInfo') }}</h3>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="t('testHistory.status')">
              <el-tag :type="getStatusType(selectedHistory.status)" size="small">
                {{ getStatusText(selectedHistory.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('testHistory.duration')">
              {{ formatDuration(selectedHistory.duration) }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('testHistory.requestMethod')">
              <el-tag :class="String(selectedHistory.request_method || '').toLowerCase()" size="small">
                {{ selectedHistory.request_method || '--' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('testHistory.responseStatus')">
              <span
                v-if="selectedHistory.response_status"
                :class="Number(selectedHistory.response_status) < 400 ? 'status-success' : 'status-error'"
              >
                {{ selectedHistory.response_status }}
              </span>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('testHistory.executionTime')" :span="2">
              {{ formatTime(selectedHistory.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('testHistory.requestUrl')" :span="2">
              <code class="detail-url">{{ selectedHistory.request_url || '-' }}</code>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <h3 class="section-title">{{ t('testHistory.requestDetail') }}</h3>
          <el-collapse v-model="activeCollapse">
            <el-collapse-item :title="t('testHistory.requestHeaders')" name="headers">
              <pre class="code-block">{{ formatJson(selectedHistory.request_headers) }}</pre>
            </el-collapse-item>
            <el-collapse-item v-if="selectedHistory.request_body" :title="t('testHistory.requestBody')" name="body">
              <pre class="code-block">{{ formatJson(selectedHistory.request_body) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>

        <div class="detail-section">
          <h3 class="section-title">{{ t('testHistory.responseDetail') }}</h3>
          <el-collapse v-model="activeCollapse">
            <el-collapse-item :title="t('testHistory.responseHeaders')" name="resp-headers">
              <pre class="code-block">{{ formatJson(selectedHistory.response_headers) }}</pre>
            </el-collapse-item>
            <el-collapse-item :title="t('testHistory.responseBody')" name="resp-body">
              <pre class="code-block">{{ formatJson(selectedHistory.response_body || t('testHistory.noResponseBody')) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>

        <div v-if="selectedHistory.error" class="detail-section error-section">
          <h3 class="section-title error-title">
            <CircleCloseIcon :size="16" /> {{ t('testHistory.errorInfo') }}
          </h3>
          <el-alert :title="String(selectedHistory.error)" type="error" :closable="false" show-icon />
        </div>

        <div class="detail-actions">
          <el-button @click="showDetailDrawer = false">{{ t('testHistory.close') }}</el-button>
          <el-button v-if="selectedHistory.status === 'success'" type="primary" @click="reuseRequest(selectedHistory)">
            {{ t('testHistory.reuseRequest') }}
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { Refresh, Delete, Search, CircleClose as CircleCloseIcon } from '@element-plus/icons-vue'
import request from '../api/request'
import EmptyState from '../components/EmptyState.vue'
import { msgError, msgSuccess } from '../utils/message'
import { useRequireLogin } from '../composables/useRequireLogin'

const { requireLogin } = useRequireLogin()
const { t } = useI18n()

type HistoryItem = {
  id: number
  status: string
  request_method?: string
  request_url?: string
  response_status?: number | null
  duration?: number | null
  environment_id?: number | null
  created_at?: string
  request_headers?: string | Record<string, unknown> | null
  request_body?: string | Record<string, unknown> | null
  response_headers?: string | Record<string, unknown> | null
  response_body?: string | Record<string, unknown> | null
  error?: string | null
}

type EnvironmentOption = { id: number; name: string }
type ApiInfo = { method: string; path: string }

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))
const apiId = computed(() => Number(route.params.apiId))

const loading = ref(false)
const historyError = ref<string | null>(null)
const historyList = ref<HistoryItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  status: '',
  environment_id: undefined as number | undefined,
})
const dateRange = ref<[string, string] | undefined>()
const environments = ref<EnvironmentOption[]>([])
const apiInfo = ref<ApiInfo | null>(null)
const showDetailDrawer = ref(false)
const selectedHistory = ref<HistoryItem | null>(null)
const activeCollapse = ref(['headers', 'body'])

const hasActiveFilters = computed(() => Boolean(filters.status || filters.environment_id || dateRange.value?.length))
const showEnvColumn = computed(() => environments.value.length > 0)
const successResponseCount = computed(() => historyList.value.filter((item) => (item.response_status ?? 0) > 0 && (item.response_status ?? 0) < 400).length)
const successStatusCount = computed(() => historyList.value.filter((item) => item.status === 'success').length)
const failedStatusCount = computed(() => historyList.value.filter((item) => item.status !== 'success').length)
const slowRequestCount = computed(() => historyList.value.filter((item) => Number(item.duration ?? 0) > 1).length)
const peakDuration = computed(() => {
  if (!historyList.value.length) return '0.000'
  return historyList.value.reduce((max, item) => Math.max(max, Number(item.duration ?? 0)), 0).toFixed(3)
})

function formatDuration(duration: number | string | null | undefined) {
  const numeric = Number(duration ?? 0)
  return `${Number.isFinite(numeric) ? numeric.toFixed(3) : '0.000'}s`
}

function formatTime(time: string | undefined) {
  if (!time) return '-'
  const date = new Date(time)
  if (Number.isNaN(date.getTime())) return time
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function formatJson(value: string | Record<string, unknown> | null | undefined) {
  if (value == null || value === '') return t('testHistory.none')
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return JSON.stringify(value)
  }
}

function getStatusType(status: string | undefined) {
  if (status === 'success') return 'success'
  if (status === 'failed' || status === 'error') return 'danger'
  return 'info'
}

function getStatusText(status: string | undefined) {
  if (status === 'success') return t('testHistory.statusSuccess')
  if (status === 'failed') return t('testHistory.statusFailed')
  if (status === 'error') return t('testHistory.statusError')
  return status || t('testHistory.statusUnknown')
}

function getEnvName(environmentId: number | null | undefined) {
  if (!environmentId) return '-'
  return environments.value.find((env) => env.id === environmentId)?.name || t('testHistory.envLabel', { id: environmentId })
}

function showDetail(row: HistoryItem) {
  selectedHistory.value = row
  activeCollapse.value = ['headers', 'body']
  showDetailDrawer.value = true
}

function resetFilters() {
  filters.status = ''
  filters.environment_id = undefined
  dateRange.value = undefined
  page.value = 1
  void loadHistory()
}

function refresh() {
  page.value = 1
  void loadHistory()
}

function goToApiDetail() {
  void router.push(`/projects/${projectId.value}/apis/detail/${apiId.value}`)
}

function reuseRequest(row: HistoryItem) {
  void router.push({
    path: `/projects/${projectId.value}/apis/detail/${apiId.value}`,
    query: { historyId: String(row.id) },
  })
}

async function loadApiInfo() {
  try {
    const res = await request.get(`/projects/${projectId.value}/apis/${apiId.value}`)
    apiInfo.value = {
      method: res.data?.method || res.method || 'GET',
      path: res.data?.path || res.path || res.url || '/',
    }
  } catch {
    apiInfo.value = null
  }
}

async function loadEnvironments() {
  try {
    const res = await request.get(`/projects/${projectId.value}/environments`)
    environments.value = res.data?.items || res.items || []
  } catch {
    environments.value = []
  }
}

async function loadHistory() {
  loading.value = true
  historyError.value = null
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
    }

    if (filters.status) params.status = filters.status
    if (filters.environment_id) params.env_id = filters.environment_id
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0] ?? ''
      params.end_date = dateRange.value[1] ?? ''
    }

    const res = await request.get(`/projects/${projectId.value}/apis/${apiId.value}/test-history`, { params })
    historyList.value = res.data?.items || res.items || []
    total.value = res.data?.total || res.total || historyList.value.length
  } catch (err) {
    historyError.value = (err as Error).message || t('testHistory.loadHistoryFailed')
    historyList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function clearAllHistory() {
  if (!(await requireLogin(t('testHistory.clearHistoryTitle')))) return
  try {
    await ElMessageBox.confirm(t('testHistory.clearHistoryConfirm'), t('testHistory.clearHistoryTitle'), {
      confirmButtonText: t('testHistory.confirmClear'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    await request.delete(`/projects/${projectId.value}/apis/${apiId.value}/test-history`)
    msgSuccess(t('testHistory.historyCleared'))
    await loadHistory()
  } catch (err) {
    if (err instanceof Error) {
      msgError(err.message || t('testHistory.clearFailed'))
    }
  }
}

watch([page, pageSize], () => {
  void loadHistory()
})

onMounted(async () => {
  await Promise.all([loadApiInfo(), loadEnvironments(), loadHistory()])
})
</script>

<style scoped>
/* ===== 页面容器 ===== */
.api-test-history-page {
  padding: var(--space-4);
  background: var(--surface-page);
  min-height: 100%;
}

/* ===== Hero 区域（页面头部） ===== */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding: var(--space-4);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
}

.history-hero {
  background: linear-gradient(135deg, var(--color-primary-alpha-04) 0%, var(--surface-card) 60%, var(--color-primary-alpha-04) 100%);
}

.history-hero-kicker {
  margin-bottom: var(--space-2);
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.history-hero-note {
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

.history-hero-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.history-hero-chip {
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-full);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.history-hero-stats {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-left: auto;
}

.history-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 84px;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  transition: transform var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

.history-stat:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.history-stat-val {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1;
}

.history-stat-lbl {
  margin-top: var(--space-1);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
  font-family: var(--font-mono);
  word-break: break-all;
}

.header-right {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  margin-bottom: var(--space-4);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  transition: border-color var(--duration-fast) var(--ease-smooth);
}

.filter-bar:hover {
  border-color: var(--border-strong);
}

.filter-group {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.filter-item {
  min-width: 150px;
}

.date-range-picker {
  width: 280px;
}

/* ===== 历史内容区 ===== */
.history-content {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.loading-state {
  padding: var(--space-4);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.skeleton-item {
  height: 48px;
  background: linear-gradient(90deg, var(--surface-hover) 25%, var(--border-subtle) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  color: var(--text-muted);
}

.empty-icon {
  margin-bottom: var(--space-4);
  opacity: 0.4;
}

.empty-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin: 0 0 var(--space-2) 0;
}

.empty-description {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0 0 var(--space-4) 0;
  text-align: center;
  max-width: 400px;
}

.history-table-wrapper {
  padding: var(--space-4);
}

.history-table {
  border-radius: var(--radius-md);
  overflow: hidden;
}

.history-table :deep(.el-table__row:hover > td.el-table__cell) {
  background: var(--surface-hover) !important;
}

.history-table :deep(.el-table__body tr:hover > td.el-table__cell) {
  background-color: var(--surface-hover) !important;
}

.url-text {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  background: var(--color-info-alpha-06);
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  word-break: break-all;
}

.duration-text {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.history-table :deep(.el-table__cell:nth-last-child(2)) {
  font-family: var(--font-mono) !important;
  font-variant-numeric: tabular-nums;
}

.status-code {
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
}

.status-success {
  color: var(--success);
}

.status-error {
  color: var(--error);
}

.status-unknown {
  color: var(--text-muted);
}

.el-tag.get {
  background: var(--color-success-alpha-10);
  color: var(--success);
  border-color: var(--color-success-alpha-20);
}

.el-tag.post {
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
  border-color: var(--color-primary-alpha-20);
}

.el-tag.put {
  background: var(--color-warning-alpha-10);
  color: var(--warning);
  border-color: var(--color-warning-alpha-20);
}

.el-tag.delete {
  background: var(--color-error-alpha-10);
  color: var(--error);
  border-color: var(--color-error-alpha-20);
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}

.detail-content {
  padding: var(--space-4);
}

.detail-section {
  margin-bottom: var(--space-5);
}

.section-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-3) 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.error-section {
  margin-top: var(--space-4);
}

.error-title {
  color: var(--error);
}

.detail-url {
  font-size: var(--text-xs);
  word-break: break-all;
  color: var(--text-secondary);
}

.code-block {
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  line-height: var(--leading-relaxed);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
}

/* ===== 暗色模式适配 ===== */
html.dark .page-header,
html.dark .filter-bar,
html.dark .history-content {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-card);
}

html.dark .history-hero {
  background: linear-gradient(135deg, var(--color-primary-alpha-06) 0%, var(--surface-card) 60%, var(--color-primary-alpha-04) 100%);
}

html.dark .history-hero-kicker {
  color: var(--primary-400);
}

html.dark .history-hero-chip {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

html.dark .history-stat {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-xs);
}

html.dark .history-stat:hover {
  box-shadow: var(--shadow-sm);
}

html.dark .history-stat-val {
  color: var(--text-primary);
}

html.dark .history-stat-lbl {
  color: var(--text-muted);
}

html.dark .skeleton-item {
  background: linear-gradient(90deg, var(--surface-hover) 25%, var(--color-primary-alpha-08) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
}

html.dark .empty-state {
  color: var(--text-muted);
}

html.dark .empty-title {
  color: var(--text-secondary);
}

html.dark .url-text {
  background: var(--color-info-alpha-10);
  color: var(--text-secondary);
}

html.dark .section-title {
  color: var(--text-primary);
}

html.dark .detail-url {
  color: var(--text-secondary);
}

html.dark .code-block {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
  color: var(--text-primary);
}

html.dark .pagination-bar {
  border-top-color: var(--border-subtle);
}

html.dark .detail-actions {
  border-top-color: var(--border-subtle);
}

html.dark .el-tag.get {
  background: var(--color-success-alpha-10);
  color: var(--success-dark);
  border-color: var(--color-success-alpha-20);
}

html.dark .el-tag.post {
  background: var(--color-primary-alpha-10);
  color: var(--primary-400);
  border-color: var(--color-primary-alpha-20);
}

html.dark .el-tag.put {
  background: var(--color-warning-alpha-10);
  color: var(--warning-dark);
  border-color: var(--color-warning-alpha-20);
}

html.dark .el-tag.delete {
  background: var(--color-error-alpha-10);
  color: var(--error-dark);
  border-color: var(--color-error-alpha-20);
}

/* ===== ApiTestHistory 暗色模式补全 ===== */
html.dark .filter-bar:hover {
  border-color: var(--border-strong);
}
html.dark .empty-description {
  color: var(--text-muted);
}
html.dark .duration-text {
  color: var(--text-secondary);
}
html.dark .status-success {
  color: var(--success-400);
}
html.dark .status-error {
  color: var(--error-400);
}
html.dark .status-unknown {
  color: var(--text-muted);
}
html.dark .error-title {
  color: var(--error-400);
}
html.dark .detail-content {
  background: var(--surface-card);
}

/* ===== 响应式适配 ===== */
@media (max-width: 960px) {
  .page-header {
    flex-direction: column;
  }

  .history-hero-stats {
    margin-left: 0;
  }
}

@media (max-width: 768px) {
  .api-test-history-page {
    padding: var(--space-2);
  }

  .filter-group {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-item,
  .date-range-picker {
    width: 100%;
  }

  .history-table-wrapper {
    padding: var(--space-2);
    overflow-x: auto;
  }

  .header-right {
    width: 100%;
  }
}
</style>
