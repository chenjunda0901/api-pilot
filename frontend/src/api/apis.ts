import request from './request'

export interface ApiListItem {
  id: number
  name: string
  method: string
  path: string
  category_id: number | null
  status: string
  created_by: number
  created_at: string
  updated_at: string
  case_count?: number
  is_starred?: boolean
  sort_order?: number
}

export interface ApiListResponse {
  items: ApiListItem[]
  total: number
  page: number
  page_size: number
}

export interface ApiDetail {
  id: number
  name: string
  method: string
  path: string
  description: string
  description_md: string
  category_id: number | null
  project_id: number
  headers: Array<{ key: string; value: string; enabled?: boolean; description?: string }>
  params: Array<{ key: string; value: string; enabled?: boolean; description?: string; type?: string }>
  body: {
    type?: string
    content?: string
    fields?: Array<{ key: string; value: string; enabled?: boolean; type?: string }>
  }
  auth: Record<string, unknown>
  settings: Record<string, unknown>
  tags: string[]
  created_by: number
  created_at: string
  updated_at: string
}

export interface ApiCreate {
  name: string
  method: string
  path: string
  description?: string
  description_md?: string
  category_id?: number | null
  headers?: Array<{ key: string; value: string }>
  params?: Array<{ key: string; value: string }>
  body?: Record<string, unknown>
  auth?: Record<string, unknown>
  settings?: Record<string, unknown>
  tags?: string[]
}

export type ApiUpdate = Partial<ApiCreate>

export interface ApiTestOverrides {
  headers?: Array<{ key: string; value: string }>
  params?: Array<{ key: string; value: string }>
  body?: Record<string, unknown>
}

export interface ApiTestResult {
  request_url: string
  request_method: string
  request_headers: Record<string, string>
  request_body: string
  response_status: number
  response_headers: Record<string, string>
  response_body: string
  duration: number
  error?: string
}

export interface ApiTestHistoryItem {
  id: number
  api_id: number
  environment_id: number | null
  executor_id: number
  request_url: string
  request_method: string
  request_headers: Array<{ key: string; value: string }>
  request_body: string
  response_status: number
  response_headers: Record<string, string>
  response_body: string
  duration: number
  error: string | null
  status: string
  created_at: string
}

export interface ApiTestHistoryResponse {
  items: ApiTestHistoryItem[]
  total: number
  page: number
  page_size: number
}

// ── API 列表 ──
export function listApis(projectId: number, params?: { category_id?: number; method?: string; status?: string; keyword?: string; tag?: string; page?: number; page_size?: number }) {
  return request.get<ApiListResponse>(`/projects/${projectId}/apis`, { params })
}

// ── API 详情 ──
export function getApi(projectId: number, apiId: number) {
  return request.get<ApiDetail>(`/projects/${projectId}/apis/${apiId}`)
}

// ── 创建 API ──
export function createApi(projectId: number, data: ApiCreate) {
  return request.post<ApiDetail>(`/projects/${projectId}/apis`, data)
}

// ── 更新 API ──
export function updateApi(projectId: number, apiId: number, data: ApiUpdate) {
  return request.put<ApiDetail>(`/projects/${projectId}/apis/${apiId}`, data)
}

// ── 删除 API（移至回收站）──
export function deleteApi(projectId: number, apiId: number) {
  return request.delete(`/projects/${projectId}/apis/${apiId}`)
}

// ── 回收站列表 ──
export function listDeletedApis(projectId: number) {
  return request.get<{ items: ApiListItem[] }>(`/projects/${projectId}/apis/recycle/list`)
}

// ── 恢复 API ──
export function restoreApi(projectId: number, apiId: number) {
  return request.post(`/projects/${projectId}/apis/${apiId}/restore`)
}

// ── 永久删除 API ──
export function permanentDeleteApi(projectId: number, apiId: number) {
  return request.delete(`/projects/${projectId}/apis/${apiId}/permanent`)
}

// ── 复制 API ──
export function duplicateApi(projectId: number, apiId: number) {
  return request.post<ApiDetail>(`/projects/${projectId}/apis/${apiId}/duplicate`)
}

// ── 标记/取消标记种子 ──
export function markApiAsSeed(projectId: number, apiId: number) {
  return request.put<{ is_seed: number; message: string }>(`/projects/${projectId}/apis/${apiId}/seed-mark`)
}

// ── 移动 API 到其他目录 ──
export function moveApi(projectId: number, apiId: number, data: { category_id: number }) {
  return request.put(`/projects/${projectId}/apis/${apiId}/move`, data)
}

// ── 测试 API ──
export function testApi(projectId: number, apiId: number, data: {
  env_id?: number
  overrides?: ApiTestOverrides
  extract_vars?: Array<{ name: string; expression: string; type: string }>
}) {
  return request.post<ApiTestResult>(`/projects/${projectId}/apis/${apiId}/test`, data)
}

// ── 获取 API 关联的用例 ──
export function listApiCases(projectId: number, apiId: number, params?: { page?: number; page_size?: number }) {
  return request.get<{ items: unknown[]; total: number; page: number; page_size: number }>(`/projects/${projectId}/apis/${apiId}/cases`, { params })
}

// ── 批量删除 API ──
export function batchDeleteApis(projectId: number, ids: number[]) {
  return request.delete(`/projects/${projectId}/apis/batch`, { data: { ids } })
}

// ── 批量移动 API ──
export function batchMoveApis(projectId: number, data: { api_ids: number[]; target_category_id: number }) {
  return request.post(`/projects/${projectId}/apis/batch/move`, data)
}

// ── 批量复制 API ──
export function batchCopyApis(projectId: number, data: { api_ids: number[]; target_category_id: number }) {
  return request.post(`/projects/${projectId}/apis/batch/copy`, data)
}

// ── 导出 API ──
export function exportApi(projectId: number, apiId: number, format: string = 'apifox') {
  return request.get(`/projects/${projectId}/apis/${apiId}/export`, { params: { format } })
}

// ── API 测试历史 ──
export function getApiTestHistory(
  projectId: number,
  apiId: number,
  params?: {
    status?: string
    env_id?: number
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  },
) {
  return request.get<ApiTestHistoryResponse>(`/projects/${projectId}/apis/${apiId}/test-history`, { params })
}

// ── 收藏接口 ──
export function starApi(projectId: number, apiId: number) {
  return request.post<{ is_starred: boolean; message: string }>(`/projects/${projectId}/apis/${apiId}/star`)
}

// ── 取消收藏 ──
export function unstarApi(projectId: number, apiId: number) {
  return request.post<{ is_starred: boolean; message: string }>(`/projects/${projectId}/apis/${apiId}/unstar`)
}