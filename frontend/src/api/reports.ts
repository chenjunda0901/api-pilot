import request from './request'

export interface ReportStepItem {
  id: number
  report_id: number
  scene_step_id: number
  step_name: string
  status: string
  request_url: string
  request_method: string
  request_headers: unknown
  request_body: string
  response_status: number
  response_headers: unknown
  response_body: string
  duration: number
  error: string | null
  assertions: unknown[]
  extract_vars: unknown[]
  created_at: string
}

export interface ReportItem {
  id: number
  name: string
  scene_id: number
  scene_name?: string
  project_id: number
  status: string
  total_count: number
  pass_count: number
  fail_count: number
  error_count: number
  duration: number
  executed_by?: number
  executor_name?: string
  created_at: string
}

export interface ReportListResponse {
  items: ReportItem[]
  total: number
  page: number
  page_size: number
}

export interface ReportDetail extends ReportItem {
  steps: ReportStepItem[]
}

export interface ReportTrendItem {
  report_id: number
  created_at: string
  pass_rate: number
  total_cases: number
  duration: number
}

export interface ReportTrendResponse {
  data: ReportTrendItem[]
}

export interface ReportCompareResult {
  current: ReportDetail
  previous: ReportDetail
  diff: {
    new_failures: ReportStepItem[]
    new_passes: ReportStepItem[]
    unchanged: ReportStepItem[]
  }
}

// ── 报告列表 ──
export function listReports(
  projectId: number,
  params?: {
    scene_id?: number
    status?: string
    start_date?: string
    end_date?: string
    keyword?: string
    page?: number
    page_size?: number
  },
) {
  return request.get<ReportListResponse>(`/projects/${projectId}/reports`, { params })
}

// ── 报告趋势 ──
export function getReportTrend(projectId: number, days?: number) {
  return request.get<ReportTrendResponse>(`/projects/${projectId}/reports/trend`, {
    params: { days },
  })
}

// ── 报告详情 ──
export function getReport(projectId: number, reportId: number) {
  return request.get<ReportDetail>(`/projects/${projectId}/reports/${reportId}`)
}

// ── 删除报告 ──
export function deleteReport(projectId: number, reportId: number) {
  return request.delete(`/projects/${projectId}/reports/${reportId}`)
}

// ── 报告对比 ──
export function compareReport(projectId: number, reportId: number, compareWith?: number) {
  return request.get<ReportCompareResult>(`/projects/${projectId}/reports/${reportId}/compare`, {
    params: { compare_with: compareWith },
  })
}

// ── 获取分享 Token ──
export function getShareToken(projectId: number, reportId: number) {
  return request.get<{ share_token: string | null }>(`/projects/${projectId}/reports/${reportId}/share`)
}

// ── 创建分享 ──
export function createShareReport(projectId: number, reportId: number, expiresInDays?: number) {
  return request.post<{ share_token: string }>(
    `/projects/${projectId}/reports/${reportId}/share`,
    null,
    { params: { expires_in_days: expiresInDays } },
  )
}

// ── 撤销分享 ──
export function revokeShareReport(projectId: number, reportId: number) {
  return request.delete(`/projects/${projectId}/reports/${reportId}/share`)
}

// ── 导出 Excel ──
export function exportReportExcel(projectId: number, reportId: number) {
  return request.get(`/projects/${projectId}/reports/${reportId}/export/excel`, {
    responseType: 'blob',
  })
}

// ── 导出 PDF ──
export function exportReportPdf(projectId: number, reportId: number) {
  return request.get(`/projects/${projectId}/reports/${reportId}/export/pdf`, {
    responseType: 'blob',
  })
}

// ── 导出 Markdown/HTML ──
export function exportReport(projectId: number, reportId: number, format: 'markdown' | 'html' = 'markdown') {
  return request.get<string>(`/projects/${projectId}/reports/${reportId}/export`, {
    params: { format },
    responseType: 'text',
  })
}

// ── 导出 CSV（步骤详情）──
export function exportReportCsv(projectId: number, reportId: number) {
  return request.get(`/projects/${projectId}/reports/${reportId}/export/csv`, {
    responseType: 'blob',
  })
}

// ── 导出 CSV 汇总 ──
export function exportReportCsvSummary(projectId: number, reportId: number) {
  return request.get(`/projects/${projectId}/reports/${reportId}/export/csv/summary`, {
    responseType: 'blob',
  })
}

// ── 导出 JUnit XML ──
export function exportReportJunit(projectId: number, reportId: number) {
  return request.get(`/projects/${projectId}/reports/${reportId}/export/junit`, {
    responseType: 'blob',
  })
}

// ── 获取分享报告数据 ──
export function getSharedReport(projectId: number, token: string) {
  return request.get<ReportDetail>(`/projects/${projectId}/reports/shared/${token}`)
}

// ── 公开分享报告（无需项目ID）──
export function getSharedReportPublic(token: string) {
  return request.get<ReportDetail>(`/reports/shared/${token}`)
}