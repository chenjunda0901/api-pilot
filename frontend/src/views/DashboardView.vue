<template>
  <PageLayout
    :title="$t('nav.dashboard')"
    :subtitle="currentProjectName"
    :kicker="$t('dashboard.kicker')"
    :loading="loading && !noProject"
  >
    <template #hero-extra>
      <div class="dashboard-hero-metrics-inline">
        <span class="inline-metric"><span class="inline-metric-label">{{ $t('dashboard.healthScore') }}</span><strong>{{ projectHealthScore }}%</strong></span>
        <span class="inline-metric-divider"></span>
        <span class="inline-metric"><span class="inline-metric-label">{{ $t('dashboard.todayReports') }}</span><strong>{{ todayReportCount }}</strong></span>
        <span class="inline-metric-divider"></span>
        <span class="inline-metric"><span class="inline-metric-label accent">{{ $t('dashboard.avgPassRate') }}</span><strong class="accent">{{ averagePassRate }}%</strong></span>
      </div>
    </template>

    <!-- 新用户引导向导 -->
    <OnboardingWizard
      :visible="showOnboarding"
      @close="showOnboarding = false"
      @finish="showOnboarding = false"
    />

    <!-- 无项目空状态 -->
    <EmptyState
      v-if="noProject"
      illustration="api"
      :title="isGuest ? t('dashboard.guestWelcome') : $t('dashboard.noProject')"
      :description="isGuest ? t('dashboard.guestWelcomeDesc') : $t('dashboard.noProjectDesc')"
    >
      <template #action>
        <el-button v-if="isGuest" type="primary" size="small" @click="goLogin">{{ t('dashboard.loginNow') }}</el-button>
        <el-button v-else type="primary" size="small" :loading="createLock.loading.value" :disabled="createLock.disabled.value" @click="handleCreateProject">{{ $t('dashboard.createProject') }}</el-button>
      </template>
    </EmptyState>

    <!-- Stats row -->
    <div v-if="!noProject" class="stats-row">
      <div v-for="card in stats" :key="card.label" class="stat-card" tabindex="0" @click="goTo(card.link)"
        @keydown.enter="goTo(card.link)"
>
        <div class="stat-card-body">
          <div class="stat-card-top">
            <div class="stat-icon-circle" :style="{ background: card.iconBg }">
              <component :is="card.iconComponent" :size="20" :style="{ color: card.color }" />
            </div>
            <div class="stat-trend-row" :class="card.trend != null ? (card.trend > 0 ? 'up' : card.trend < 0 ? 'down' : 'flat') : ''" v-if="card.trend != null">
              <span class="stat-trend-value" :class="card.trend > 0 ? 'up' : card.trend < 0 ? 'down' : 'flat'">
                {{ card.trend > 0 ? '+' : '' }}{{ card.trend }}%{{ $t('dashboard.comparedToLastWeek') }}
                <span v-if="card.trend > 0" class="trend-arrow up">▲</span>
                <span v-else-if="card.trend < 0" class="trend-arrow down">▼</span>
              </span>
            </div>
          </div>
          <div class="stat-num-wrap">
            <AnimatedCounter v-if="card.value > 0" :value="card.value" :duration="800" :label="card.label" />
            <span v-else class="stat-zero">0</span>
          </div>
          <div class="stat-card-foot">
            <div class="stat-bar-row">
              <div class="stat-mini-bar"><div class="stat-mini-bar-fill" :style="{ width: Math.min(card.pct, 100).toFixed(1) + '%', background: card.accentGradient }"></div></div>
            </div>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Content split: left report list + right quick actions -->
    <div class="content-split">
      <section class="split-section left-section">
        <div class="section-head">
          <div class="section-head-left">
            <h2 class="section-title">{{ $t('dashboard.recentExec') }}</h2>
            <div class="filter-tabs">
              <button
                v-for="tab in [{key:'all',label:$t('common.all')},{key:'success',label:$t('report.passCases')},{key:'failed',label:$t('report.failCases')}]"
                :key="tab.key"
                class="filter-tab"
                :class="{ active: reportFilter === tab.key }"
                @click="reportFilter = tab.key as 'success' | 'failed' | 'all'"
              >
{{ tab.label }}
</button>
            </div>
          </div>
          <button class="section-link" @click="goTo('reports')">{{ $t('common.details') }} →</button>
        </div>
        <div class="report-list" :key="reportsKey + reportFilter">
          <div v-for="r in filteredReports" :key="r.id" class="report-item" :class="r.status" @click="router.push(`/projects/${projectStore.currentProjectId}/reports/${r.id}`)"
            tabindex="0"
            @keydown.enter="router.push(`/projects/${projectStore.currentProjectId}/reports/${r.id}`)"
>
            <div class="report-item-body">
              <div class="report-item-top">
                <span class="report-id">#{{ r.id }}</span>
                <span class="report-passrate" :class="r.status === 'success' ? 'passed' : 'failed'">
                  {{ r.total_count ? Math.round(r.pass_count / r.total_count * 100) : 0 }}%
                </span>
                <span class="report-duration">{{ r.duration ? Number(r.duration).toFixed(2) + 's' : '-' }}</span>
              </div>
              <div class="report-item-bottom">
                <span class="report-scene-name"><span :class="{ 'unnamed-hint': !r.scene_name }">{{ r.scene_name || $t('scene.unnamed') }}</span></span>
                <span class="report-sep">·</span>
                <span class="report-env">{{ r.env_name || $t('scene.environment') }}</span>
                <span class="report-sep">·</span>
                <span class="report-time">{{ formatDashboardRelativeTime(r.created_at) }}</span>
              </div>
            </div>
            <button
              class="report-rerun-btn"
              :class="{ loading: rerunLoading === r.id }"
              @click.stop="rerunReport(r)"
              :title="$t('report.rerun')"
            >
              <Play :size="13" v-if="rerunLoading !== r.id" />
              <span v-else class="rerun-spinner"></span>
              <span>{{ $t('report.rerun') }}</span>
            </button>
          </div>
          <div v-if="filteredReports.length === 0 && !loading" class="report-empty">
            <div class="report-empty-visual">
              <FileText :size="32" class="report-empty-icon" />
            </div>
            <p class="report-empty-title">
              <template v-if="reportFilter === 'all'">{{ $t('dashboard.noRecords') }}</template>
              <template v-else-if="reportFilter === 'success'">{{ $t('dashboard.noPassedRecords') }}</template>
              <template v-else>{{ $t('dashboard.noFailedRecords') }}</template>
            </p>
            <p v-if="reportFilter === 'all'" class="report-empty-desc">{{ $t('dashboard.noRecordsDesc') }}</p>
            <el-button v-if="reportFilter === 'all'" type="primary" size="small" @click="goTo('scenes')">
              <Play :size="14" style="margin-right: 4px" />{{ $t('dashboard.goRunScene') }}
            </el-button>
          </div>
        </div>
      </section>

      <section class="split-section right-section">
        <div class="section-head">
          <h2 class="section-title">{{ $t('dashboard.quickActions') }}</h2>
        </div>
        <div class="quick-grid">
          <div class="quick-section-label">{{ $t('dashboard.commonActions') }}</div>
          <button class="quick-action-item primary" @click="goTo('newApi')">
            <PlusCircle :size="20" />
            <span>{{ $t('dashboard.newApi') }}</span>
          </button>
          <button class="quick-action-item" :disabled="importLock.disabled.value" @click="importOpenAPI">
            <Download :size="20" />
            <span>{{ $t('dashboard.importApi') }}</span>
          </button>
          <button v-if="canManageSettings" class="quick-action-item" @click="goTo('settings')">
            <Settings :size="20" />
            <span>{{ $t('dashboard.envConfig') }}</span>
          </button>
          <button v-if="isLoggedIn" class="quick-action-item" @click="openBatchRunDialog">
            <Zap :size="20" />
            <span>{{ $t('dashboard.batchRun') }}</span>
          </button>
        </div>

        <!-- 最近访问 -->
        <div class="quick-divider"></div>
        <div class="quick-section-label">{{ $t('dashboard.recentVisits') }}</div>
        <div class="recent-list" v-if="recentItems.length > 0">
          <div v-for="item in recentItems" :key="item.id" class="recent-item" @click="goToRecent(item)">
            <span class="recent-icon">{{ item.type === 'scene' ? '📄' : '🔗' }}</span>
            <div class="recent-info">
              <span class="recent-name">{{ item.name }}</span>
              <span class="recent-meta">{{ item.typeLabel }} · {{ formatDashboardRelativeTime(item.updated_at) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="recent-empty">
          <div class="recent-empty-icon">📋</div>
          <span class="recent-empty-text">{{ $t('dashboard.noRecentVisits') }}</span>
          <span class="recent-empty-hint">{{ $t('dashboard.startTestHint') }}</span>
          <el-button type="primary" size="small" class="recent-empty-btn" @click="goTo('scenes')">
            <Play :size="14" style="margin-right: 4px" />{{ $t('dashboard.goRunScene') }}
          </el-button>
        </div>
      </section>
    </div>

    <!-- Trend chart -->
    <section class="trend-section" v-if="trendData.length > 0">
      <div class="trend-head">
        <h2 class="section-title">{{ $t('dashboard.trendTitle') }}</h2>
          <span class="trend-period">{{ $t('dashboard.last7Days') }}</span>
      </div>
      <div class="trend-stats" v-if="trendData.length > 0">
        <div class="trend-stat-item">
          <span class="trend-stat-label">{{ $t('dashboard.trendAvgPassRate') }}</span>
          <span class="trend-stat-value">{{ Math.round(trendData.reduce((a,b) => a+b, 0) / trendData.length) }}%</span>
        </div>
        <div class="trend-stat-divider"></div>
        <div class="trend-stat-item">
          <span class="trend-stat-label">{{ $t('dashboard.trendHighest') }}</span>
          <span class="trend-stat-value">{{ Math.max(...trendData) }}%</span>
        </div>
        <div class="trend-stat-divider"></div>
        <div class="trend-stat-item">
          <span class="trend-stat-label">{{ $t('dashboard.trendLowest') }}</span>
          <span class="trend-stat-value">{{ Math.min(...trendData) }}%</span>
        </div>
      </div>
      <div class="trend-chart" ref="chartRef" role="img" :aria-label="t('dashboard.trendChartAriaLabel')"></div>
    </section>

    <!-- 导入弹窗 -->
    <ImportWizard
      v-if="showImportWizard"
      v-model="showImportWizard"
      :project-id="projectStore.currentProjectId ?? 0"
      @imported="onImported"
    />

    <!-- 批量执行弹窗 -->
    <BatchRunDialog v-model:visible="showBatchRunDialog" :project-id="projectStore.currentProjectId ?? 0" :env-list="envList" @execute="onBatchRunExecute" />

    <!-- 新建项目对话框 -->
    <el-dialog v-model="showNewProjectDialog" :title="$t('common.newProjectTitle')" width="420px" :close-on-click-modal="false" destroy-on-close>
      <el-form label-position="top" size="small">
        <el-form-item :label="$t('settings.nameField')">
          <el-input v-model="newProjectForm.name" :placeholder="$t('common.newProjectPlaceholder')" maxlength="50" @keyup.enter="confirmCreateProject" />
        </el-form-item>
        <el-form-item :label="$t('dashboard.projectVisibility')">
          <el-radio-group v-model="newProjectForm.is_public" size="small">
            <el-radio-button :value="false">{{ $t('settings.private') }}</el-radio-button>
            <el-radio-button :value="true">{{ $t('settings.public') }}</el-radio-button>
          </el-radio-group>
          <p class="new-project-hint">{{ newProjectForm.is_public ? $t('dashboard.publicProjectHint') : $t('dashboard.privateProjectHint') }}</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewProjectDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="creatingProject" :disabled="!newProjectForm.name.trim()" @click="confirmCreateProject">{{ $t('dashboard.createBtn') }}</el-button>
      </template>
    </el-dialog>
  </PageLayout>
</template>

<script setup lang="ts">
defineOptions({ name: 'DashboardView' })

import "./dashboard-view.css"
import { ref, computed, reactive, onMounted, onActivated, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import { msgSuccess, msgError, msgInfo } from '../utils/message'
import { useRequireLogin } from '../composables/useRequireLogin'
import { useProjectPermission } from '../composables/useProjectPermission'
import { useSubmitLock } from '../composables/useSubmitLock'
import { useTheme } from '../composables/useTheme'
import { useUserStore } from '../stores/userStore'
import { formatDashboardRelativeTime, useDashboardData } from '../composables/useDashboardData'
import EmptyState from '../components/EmptyState.vue'
import AnimatedCounter from '../components/AnimatedCounter.vue'
import OnboardingWizard from '../components/OnboardingWizard.vue'
import PageLayout from '../components/common/PageLayout.vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { TestReport } from '../types'
import type { ApiError } from '../types/common'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

import { runScene } from '../api/scenes'
import { createProject } from '../api/projects'
import { useProjectStore } from '../stores/projectStore'
import ImportWizard from '../components/ImportWizard.vue'
import BatchRunDialog from '../components/dashboard/BatchRunDialog.vue'
import { Play, PlusCircle, Download, Settings, FileText, Zap } from 'lucide-vue-next'


const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const projectStore = useProjectStore()
const userStore = useUserStore()
const isGuest = computed(() => !userStore.user)
const { requireLogin } = useRequireLogin()
const { canEdit, canManageSettings, isLoggedIn, requireWrite } = useProjectPermission()
const { isDark } = useTheme()
const showImportWizard = ref(false)
const createLock = useSubmitLock()
const importLock = useSubmitLock()
const reportFilter = ref<'all' | 'success' | 'failed'>('all')

const showOnboarding = ref(false)
const refreshTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const {
  averagePassRate,
  envList,
  fetchData,
  filteredRecentItems: recentItems,
  loading,
  noProject,
  projectHealthScore,
  reports,
  reportsKey,
  stats,
  todayReportCount,
  trendData,
  trendLabels,
} = useDashboardData(
  () => projectStore.projects.length,
  () => projectStore.currentProjectId ?? null,
)

const filteredReports = computed(() => {
  if (reportFilter.value === 'all') return reports.value
  return reports.value.filter((report) => report.status === reportFilter.value)
})

function goToRecent(item: { id: number; name: string; type: string }) {
  const pid = projectStore.currentProjectId
  if (!pid) return
  if (item.type === 'scene') {
    void router.push(`/projects/${pid}/scenes`)
  } else {
    void router.push(`/projects/${pid}/apis/detail/${item.id}`)
  }
}

const currentProjectName = computed(() => {
  const found = projectStore.projects.find((project) => project.id === projectStore.currentProjectId)
  return found?.name || t('dashboard.noProjectSelected')
})

// ECharts
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

watch(chartRef, (el) => {
  if (!el) {
    chartInstance?.dispose()
    chartInstance = null
    return
  }
  chartInstance = echarts.init(el)
  updateChart()
})

// trendData 变化时自动更新图表
watch([trendData, trendLabels], () => {
  if (chartInstance) updateChart()
})

// 主题切换时更新图表
watch(isDark, () => {
  if (chartInstance) updateChart()
})

function resolveCyan(alpha: string): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--color-cyan-alpha-${alpha}`).trim()
  return raw || `rgba(43, 160, 175, ${parseFloat(alpha) / 100})`
}

function updateChart() {
  if (!chartInstance) return
  const dark = isDark.value
  const data = trendData.value
  const days = trendLabels.value

  chartInstance.setOption({
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: days,
      axisLine: { lineStyle: { color: dark ? 'rgba(100, 108, 128, 0.20)' : 'var(--border-subtle)' } },
      axisLabel: { color: dark ? 'rgba(214, 220, 233, 0.48)' : 'var(--text-muted)', fontSize: 12 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: dark ? 'rgba(100, 108, 128, 0.10)' : 'var(--border-subtle)' } },
      axisLabel: { color: dark ? 'rgba(214, 220, 233, 0.48)' : 'var(--text-muted)', fontSize: 11, formatter: '{value}%' },
    },
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: 'var(--primary-500)', width: 2.5 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: resolveCyan('15') },
          { offset: 1, color: resolveCyan('03') },
        ]),
      },
      itemStyle: { color: 'var(--primary-500)' },
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params: { name: string; value: number }[]) => {
        const p = params?.[0]
        if (!p) return ''
        return `${p.name ?? ''}<br/>${t('dashboard.trendTooltipPassRate')}: <strong>${p.value ?? 0}%</strong>`
      },
    },
  })
}

onUnmounted(() => {
  chartInstance?.dispose()
  if (refreshTimer.value) {
    clearTimeout(refreshTimer.value)
    refreshTimer.value = null
  }
})


const showBatchRunDialog = ref(false)

async function openBatchRunDialog() {
  if (!(await requireLogin(t('dashboard.batchRun')))) return
  showBatchRunDialog.value = true
}

function onBatchRunExecute(_payload: { count: number }) {
  refreshTimer.value = setTimeout(() => fetchData(), 2000)
}

async function _importOpenAPI() {
  if (!(await requireWrite(t('dashboard.importApi')))) return
  if (!projectStore.currentProjectId) {
    msgInfo(t('dashboard.selectProjectFirst'))
    return
  }
  showImportWizard.value = true
}

const importOpenAPI = () => importLock.run(_importOpenAPI)

function onImported(result: { created_apis?: number; created_categories?: number }) {
  msgSuccess(t('dashboard.importComplete', { apis: result.created_apis || 0, categories: result.created_categories || 0 }))
  void fetchData()
}

const rerunLoading = ref<number | null>(null)

async function rerunReport(r: TestReport) {
  const pid = projectStore.currentProjectId
  if (!pid || !r.scene_id) return
  if (!(await requireLogin(t('dashboard.rerun')))) return
  rerunLoading.value = r.id
  try {
    const env = r.env_id
    if (!env) {
      msgError(t('dashboard.missingEnvInfo'))
      return
    }
    await runScene(pid, r.scene_id, env)
    msgSuccess(t('dashboard.rerunTriggered'))
    refreshTimer.value = setTimeout(() => fetchData(), 2000)
  } catch (e) {
    const msg = (e as ApiError).response?.data?.message || t('dashboard.rerunFailed')
    msgError(msg)
  } finally {
    rerunLoading.value = null
  }
}

// ── 新建项目对话框 ──
const showNewProjectDialog = ref(false)
const creatingProject = ref(false)
const newProjectForm = reactive({ name: '', is_public: false })

async function confirmCreateProject() {
  const name = newProjectForm.name.trim()
  if (!name) return
  creatingProject.value = true
  try {
    const res = await createProject({ name, is_public: newProjectForm.is_public })
    const newId = res.data.id
    projectStore.setCurrentProject(newId)
    await projectStore.fetchProjects()
    msgSuccess(t('dashboard.projectCreated'))
    showNewProjectDialog.value = false
    void router.push(`/projects/${newId}/apis`)
  } catch (e: unknown) {
    const msg = (e as ApiError)?.response?.data?.message || t('dashboard.createProjectFailed')
    msgError(msg)
  } finally {
    creatingProject.value = false
  }
}

async function _handleCreateProject() {
  if (!(await requireLogin(t('dashboard.createProjectAction')))) return
  newProjectForm.name = ''
  newProjectForm.is_public = false
  showNewProjectDialog.value = true
}

const handleCreateProject = () => createLock.run(_handleCreateProject)

async function goTo(page: string) {
  const writeOps = ['newApi', 'settings']
  if (writeOps.includes(page) && !(await requireWrite(t('dashboard.' + (page === 'newApi' ? 'newApi' : 'envConfig'))))) return

  const pid = projectStore.currentProjectId
  if (!pid) return

  const routes: Record<string, string> = {
    apis: `/projects/${pid}/apis`,
    newApi: `/projects/${pid}/apis/detail/new`,
    scenes: `/projects/${pid}/scenes`,
    reports: `/projects/${pid}/reports`,
    settings: `/projects/${pid}/settings`,
  }
  void router.push(routes[page] || `/projects/${pid}/${page}`)
}

function goLogin() {
  void router.push('/login')
}

onMounted(() => {
  if (projectStore.currentProjectId) { void fetchData() }
  // 新注册用户：URL 带 newuser=1 且无项目时自动触发引导向导
  if (route.query.newuser === '1' && noProject.value) {
    showOnboarding.value = true
  }
})

// Keep-Alive 缓存激活时刷新数据
onActivated(() => {
  if (projectStore.currentProjectId) { void fetchData() }
})

// 监听 currentProjectId 变化，AppLayout 的 fetchProjects 异步完成后能再次触发数据拉取
watch(() => projectStore.currentProjectId, (pid) => {
  if (pid) { void fetchData() }
})

// 新用户引导：无项目且未完成引导时显示
watch(noProject, (val) => {
  if (val && localStorage.getItem('api_pilot_onboarding_done') !== '1') {
    showOnboarding.value = true
  }
}, { immediate: true })
</script>

<style scoped>
.new-project-hint {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: var(--space-1) 0 0 0;
  line-height: var(--leading-normal);
}
</style>

