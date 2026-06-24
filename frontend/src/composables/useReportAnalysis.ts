/**
 * 测试报告分析工具
 * 提供报告查看、对比、导出功能
 */

import { ref, computed } from 'vue'
import { msgSuccess, msgError } from '@/utils/message'
import request from '../api/request'

// 报告列表响应接口
interface ReportsListResponse {
  data: {
    items: TestReport[]
    total: number
  }
}

// 报告详情响应接口
interface ReportDetailResponse {
  data: TestReport
}

// 分享响应接口
interface ShareResponse {
  data: {
    share_token: string
  }
}

// 报告类型
export interface TestReport {
  id: number
  project_id: number
  scene_id: number
  scene_name?: string
  environment_id: number
  status: 'running' | 'completed' | 'failed'
  total_count: number
  passed_count?: number
  failed_count?: number
  skipped_count?: number
  duration?: number
  executor_id: number
  executor_name?: string
  created_at: string
  finished_at?: string
  share_token?: string
  steps?: ReportStep[]
}

export interface ReportStep {
  id: number
  report_id: number
  scene_step_id?: number
  step_name?: string
  api_id?: number
  method?: string
  path?: string
  status: 'success' | 'failed' | 'skipped' | 'error'
  duration: number
  request_url?: string
  request_method?: string
  request_headers?: Record<string, string>
  request_body?: string
  response_status?: number
  response_headers?: Record<string, string>
  response_body?: string
  assertions?: AssertionResult[]
  extract_vars?: Record<string, unknown>
  error_message?: string
}

export interface AssertionResult {
  type: string
  path?: string
  operator?: string
  expected?: unknown  // JSONPath 提取结果，可能是各种类型
  actual?: unknown
  passed: boolean
}

/**
 * 报告分析 Hook
 */
export function useReportAnalysis() {
  const reports = ref<TestReport[]>([])
  const currentReport = ref<TestReport | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /**
   * 加载报告列表
   */
  async function loadReports(projectId: number, options?: {
    page?: number
    pageSize?: number
    status?: string
  }) {
    isLoading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      if (options?.page) params.append('page', String(options.page))
      if (options?.pageSize) params.append('page_size', String(options.pageSize))
      if (options?.status) params.append('status', options.status)

      const res = await request.get<ReportsListResponse>(
        `/projects/${projectId}/reports?${params.toString()}`
      )


      reports.value = res.data?.items || []
      return res.data
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载报告失败'
      error.value = message
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 加载报告详情
   */
  async function loadReportDetail(reportId: number, projectId?: number) {
    isLoading.value = true
    error.value = null

    try {
      const url = projectId ? `/projects/${projectId}/reports/${reportId}` : `/reports/${reportId}`
      const res = await request.get<ReportDetailResponse>(url)
      currentReport.value = res.data ?? null
      return currentReport.value
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载报告详情失败'
      error.value = message
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 获取通过率
   */
  const passRate = computed(() => {
    if (!currentReport.value || currentReport.value.total_count === 0) return 0
    const passed = currentReport.value.passed_count || 0
    return Math.round((passed / currentReport.value.total_count) * 100)
  })

  /**
   * 获取执行状态摘要
   */
  const summary = computed(() => {
    if (!currentReport.value) return null

    const report = currentReport.value
    const passed = report.passed_count || 0
    const failed = report.failed_count || 0
    const skipped = report.skipped_count || 0
    const total = report.total_count

    return {
      total,
      passed,
      failed,
      skipped,
      passRate: total > 0 ? Math.round((passed / total) * 100) : 0,
      failRate: total > 0 ? Math.round((failed / total) * 100) : 0,
      duration: report.duration || 0,
      status: report.status,
      executor: report.executor_name || '未知',
      startTime: report.created_at,
      endTime: report.finished_at,
    }
  })

  /**
   * 按状态分组步骤
   */
  const stepsByStatus = computed(() => {
    if (!currentReport.value?.steps) return { success: [], failed: [], skipped: [], error: [] }

    const steps = currentReport.value.steps
    return {
      success: steps.filter(s => s.status === 'success'),
      failed: steps.filter(s => s.status === 'failed' || s.status === 'error'),
      skipped: steps.filter(s => s.status === 'skipped'),
      error: steps.filter(s => s.status === 'error'),
    }
  })

  /**
   * 获取失败的断言详情
   */
  const failedAssertions = computed(() => {
    if (!currentReport.value?.steps) return []

    const results: Array<{
      step: ReportStep
      assertion: AssertionResult
    }> = []

    for (const step of currentReport.value.steps) {
      if (step.assertions) {
        for (const assertion of step.assertions) {
          if (!assertion.passed) {
            results.push({ step, assertion })
          }
        }
      }
    }

    return results
  })

  /**
   * 分享报告
   */
  async function shareReport(reportId: number, projectId?: number) {
    try {
      const url = projectId ? `/projects/${projectId}/reports/${reportId}/share` : `/reports/${reportId}/share`
      const res = await request.post<ShareResponse>(url)
      const shareToken = res.data?.share_token
      if (!shareToken) {
        throw new Error('分享链接生成失败')
      }
      const shareUrl = `${window.location.origin}/#/shared/${shareToken}`
      await navigator.clipboard.writeText(shareUrl)
      msgSuccess('报告链接已复制到剪贴板')
      return shareUrl
    } catch {
      msgError('分享失败')
      return null
    }
  }

  /**
   * 删除报告
   */
  async function deleteReport(reportId: number, projectId?: number) {
    try {
      const url = projectId ? `/projects/${projectId}/reports/${reportId}` : `/reports/${reportId}`
      await request.delete(url)
      reports.value = reports.value.filter(r => r.id !== reportId)
      if (currentReport.value?.id === reportId) {
        currentReport.value = null
      }
      msgSuccess('报告已删除')
      return true
    } catch {
      msgError('删除失败')
      return false
    }
  }

  /**
   * 导出报告为 JSON
   */
  /* ═══════════════════════════════════════
     死代码保留标记
     exportAsJSON / exportAsHTML / generateReportHTML
     当前无调用者，ReportDetailView.vue 使用内联逻辑
     如需要可取消以下注释启用
     ═══════════════════════════════════════ */
  /* function escapeHtml removed — unused */

/** 生成报告 HTML */
function generateReportHTML(report: TestReport): string {
    const steps = report.steps || []
    const passed = report.passed_count || 0
    const failed = report.failed_count || 0
    const duration = report.duration || 0

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>测试报告 - ${report.scene_name || report.id}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .title { font-size: 24px; font-weight: 600; }
    .meta { color: #666; font-size: 14px; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
    .stat { background: #f5f5f5; padding: 16px; border-radius: 8px; text-align: center; }
    .stat-value { font-size: 32px; font-weight: 600; }
    .stat-label { color: #666; font-size: 14px; }
    .stat.passed .stat-value { color: #22c55e; }
    .stat.failed .stat-value { color: #ef4444; }
    .step { border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 12px; padding: 16px; }
    .step-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .step-name { font-weight: 600; }
    .step-status { padding: 4px 12px; border-radius: 16px; font-size: 12px; }
    .step-status.passed { background: #dcfce7; color: #166534; }
    .step-status.failed { background: #fee2e2; color: #991b1b; }
    .step-details { font-size: 14px; color: #666; }
    .method { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .method.GET { background: #dcfce7; color: #166534; }
    .method.POST { background: #dbeafe; color: #1e40af; }
    .method.PUT { background: #fef3c7; color: #92400e; }
    .method.DELETE { background: #fee2e2; color: #991b1b; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 class="title">${report.scene_name || '测试报告'}</h1>
      <p class="meta">报告ID: ${report.id} | 执行时间: ${new Date(report.created_at).toLocaleString('zh-CN')}</p>
    </div>
  </div>
  
  <div class="stats">
    <div class="stat">
      <div class="stat-value">${report.total_count}</div>
      <div class="stat-label">总步骤</div>
    </div>
    <div class="stat passed">
      <div class="stat-value">${passed}</div>
      <div class="stat-label">通过</div>
    </div>
    <div class="stat failed">
      <div class="stat-value">${failed}</div>
      <div class="stat-label">失败</div>
    </div>
    <div class="stat">
      <div class="stat-value">${(duration / 1000).toFixed(2)}s</div>
      <div class="stat-label">耗时</div>
    </div>
  </div>
  
  <h2>执行详情</h2>
  ${steps.map(step => `
  <div class="step">
    <div class="step-header">
      <div>
        <span class="method ${step.request_method || 'GET'}">${step.request_method || 'GET'}</span>
        <span class="step-name">${step.step_name || step.request_url || '步骤'}</span>
      </div>
      <span class="step-status ${step.status === 'success' ? 'passed' : 'failed'}">${step.status === 'success' ? '通过' : step.status === 'skipped' ? '跳过' : '失败'}</span>
    </div>
    <div class="step-details">
      <p>URL: ${step.request_url || '-'}</p>
      <p>响应状态: ${step.response_status || '-'}</p>
      <p>耗时: ${(step.duration / 1000).toFixed(2)}s</p>
      ${step.error_message ? `<p style="color: #ef4444;">错误: ${step.error_message}</p>` : ''}
    </div>
  </div>
  `).join('')}
</body>
</html>`
  }

  return {
    // 状态
    reports,
    currentReport,
    isLoading,
    error,
    passRate,
    summary,
    stepsByStatus,
    failedAssertions,

    // 方法
    loadReports,
    loadReportDetail,
    shareReport,
    deleteReport,
    generateReportHTML,
  }
}

export default {
  useReportAnalysis
}