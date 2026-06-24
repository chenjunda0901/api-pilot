import { computed, ref } from 'vue'
import request from '../api/request'
import type { Environment, TestReport } from '../types'
import { Globe, Shield, FlaskConical, ChartBar } from 'lucide-vue-next'
import { msgWarning } from '@/utils/message'

interface ProjectOverviewResponse {
  data: {
    api_count?: number
    case_count?: number
    scene_count?: number
  }
}

interface ReportsResponse {
  data: {
    items?: TestReport[]
    total?: number
  }
}

interface EnvironmentsResponse {
  data: {
    items?: Environment[]
  }
}

export interface DashboardStat {
  label: string
  value: number
  pctLabel: string
  color: string
  iconBg: string
  accent: string
  accentGradient: string
  iconComponent: typeof Globe
  trend: number | null
  pct: number
  link: string
  emptyHint: string
  trendLabel: string
}

const createDefaultStats = (): DashboardStat[] => [
  { label: '接口总数', value: 0, pctLabel: '相对占比', color: 'var(--primary-500)', iconBg: 'var(--color-primary-alpha-08)', accent: 'var(--primary-500)', accentGradient: 'linear-gradient(90deg, var(--primary-500), var(--color-info))', iconComponent: Globe, trend: null, pct: 0, link: 'apis', emptyHint: '还没有接口', trendLabel: '较上周' },
  { label: '用例总数', value: 0, pctLabel: '相对占比', color: 'var(--color-success)', iconBg: 'var(--color-success-alpha-08)', accent: 'var(--color-success)', accentGradient: 'var(--gradient-success)', iconComponent: Shield, trend: null, pct: 0, link: 'apis', emptyHint: '还没有用例', trendLabel: '较上周' },
  { label: '场景总数', value: 0, pctLabel: '相对占比', color: 'var(--color-warning)', iconBg: 'var(--color-warning-alpha-08)', accent: 'var(--color-warning)', accentGradient: 'linear-gradient(90deg, var(--color-warning), var(--color-warning))', iconComponent: FlaskConical, trend: null, pct: 0, link: 'scenes', emptyHint: '还没有场景', trendLabel: '较上周' },
  { label: '报告总数', value: 0, pctLabel: '相对占比', color: 'var(--color-info)', iconBg: 'var(--color-primary-alpha-08)', accent: 'var(--color-info)', accentGradient: 'linear-gradient(90deg, var(--color-info), var(--color-info-400))', iconComponent: ChartBar, trend: null, pct: 0, link: 'reports', emptyHint: '还没有报告', trendLabel: '较上周' },
]

function resetStats(stats: DashboardStat[]) {
  return stats.map((stat) => ({ ...stat, value: 0, pct: 0 }))
}

export function formatDashboardRelativeTime(dateStr: string): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffDays === 0) {
    return `今天 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  if (diffDays === 1) {
    return `昨天 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  if (diffDays < 4) {
    const weekDays = ['日', '一', '二', '三', '四', '五', '六']
    return `周${weekDays[date.getDay()]} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}

export function useDashboardData(projectCount: () => number, projectId: () => number | null) {
  const loading = ref(false)
  const noProject = ref(false)
  const reportsKey = ref(0)
  const stats = ref<DashboardStat[]>(createDefaultStats())
  const reports = ref<TestReport[]>([])
  const trendData = ref<number[]>([])
  const trendLabels = ref<string[]>([])
  const envList = ref<Environment[]>([])

  const filteredRecentItems = computed(() => {
    if (reports.value.length === 0) return []
    const seen = new Set<string>()
    return reports.value
      .slice(0, 5)
      .filter((report) => {
        const key = report.scene_name || ''
        if (!key || seen.has(key)) return false
        seen.add(key)
        return true
      })
      .map((report) => ({
        id: report.id,
        name: report.scene_name || '未命名场景',
        type: 'scene' as const,
        typeLabel: '场景',
        updated_at: report.created_at,
      }))
  })

  const totalStats = computed(() => stats.value.reduce((sum, item) => sum + item.value, 0))
  const projectHealthScore = computed(() => {
    if (totalStats.value === 0) return 0
    return Math.min(99, Math.round((stats.value[3].value * 3 + stats.value[2].value * 2 + stats.value[1].value) / totalStats.value * 12 + 68))
  })
  const todayReportCount = computed(() => reports.value.filter((report) => {
    const created = new Date(report.created_at)
    const today = new Date()
    return created.toDateString() === today.toDateString()
  }).length)
  const averagePassRate = computed(() => {
    if (trendData.value.length === 0) return 0
    return Math.round(trendData.value.reduce((sum, value) => sum + value, 0) / trendData.value.length)
  })
  const latestPassRate = computed(() => trendData.value.at(-1) ?? 0)
  const latestReportLabel = computed(() => {
    const latest = reports.value[0]
    if (!latest) return '暂无最近报告'
    return `${latest.scene_name || '未命名场景'} · ${formatDashboardRelativeTime(latest.created_at)}`
  })
  const apiDensity = computed(() => {
    const s0 = stats.value[0]?.value || 0
    return Math.min(100, Math.round((s0 / Math.max(totalStats.value, 1)) * 100))
  })
  const caseDensity = computed(() => {
    const s1 = stats.value[1]?.value || 0
    return Math.min(100, Math.round((s1 / Math.max(totalStats.value, 1)) * 100))
  })
  const sceneDensity = computed(() => {
    const s2 = stats.value[2]?.value || 0
    return Math.min(100, Math.round((s2 / Math.max(totalStats.value, 1)) * 100))
  })

  async function fetchData() {
    const pid = projectId()
    if (!pid) {
      loading.value = false
      noProject.value = projectCount() === 0
      return
    }

    loading.value = true
    noProject.value = false

    try {
      const [projRes, repRes, envRes] = await Promise.all([
        request.get(`/projects/${pid}`),
        request.get(`/projects/${pid}/reports?page=1&page_size=10`),
        request.get(`/projects/${pid}/environments?page_size=100`),
      ])

      const projectData = projRes as ProjectOverviewResponse
      const reportsResponse = repRes as ReportsResponse
      const environmentsResponse = envRes as EnvironmentsResponse
      const values = [
        projectData.data.api_count || 0,
        projectData.data.case_count || 0,
        projectData.data.scene_count || 0,
        reportsResponse.data.total || 0,
      ]
      const maxValue = Math.max(...values, 1)
      const percentageList = values.map((value) => Math.min((value / maxValue) * 100, 100))
      const defaultStats = createDefaultStats()

      stats.value = defaultStats.map((stat, index) => ({
        ...stat,
        value: values[index],
        pct: percentageList[index],
      }))

      reports.value = (reportsResponse.data.items || []).sort(
        (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      )
      reportsKey.value += 1

      const recentReports = reports.value.slice(0, 7).reverse()
      trendData.value = recentReports.map((report) => (
        report.total_count ? Math.round(((report.pass_count || 0) / report.total_count) * 100) : 0
      ))
      trendLabels.value = recentReports.map((report) => {
        const dt = new Date(report.created_at)
        if (isNaN(dt.getTime())) return ''
        return `${dt.getMonth() + 1}/${dt.getDate()}`
      })

      envList.value = environmentsResponse.data.items || []
    } catch (error: unknown) {
      const status = (error as { response?: { status?: number } })?.response?.status
      stats.value = resetStats(stats.value)
      reports.value = []
      trendData.value = []
      trendLabels.value = []
      envList.value = []

      if (status !== 403 && status !== 404 && status !== 500) {
        const message = (error as { message?: string })?.message || ''
        if (message.includes('timeout') || message.includes('Network Error')) {
          msgWarning('网络异常，请检查连接后刷新')
        }
      }
    } finally {
      loading.value = false
    }
  }

  return {
    apiDensity,
    averagePassRate,
    caseDensity,
    envList,
    fetchData,
    filteredRecentItems,
    latestPassRate,
    latestReportLabel,
    loading,
    noProject,
    projectHealthScore,
    reports,
    reportsKey,
    sceneDensity,
    stats,
    todayReportCount,
    totalStats,
    trendData,
    trendLabels,
  }
}
