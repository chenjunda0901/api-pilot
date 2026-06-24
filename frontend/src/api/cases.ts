import request from './request'

export interface TestCaseAssertion {
  type: string
  expression: string
  expected: string
  comparator: string
}

export interface TestCaseExtractVar {
  name: string
  expression: string
  type: string
}

export interface TestCaseItem {
  id: number
  name: string
  api_id: number
  project_id: number
  case_type: string
  priority: string
  status: string
  tags: string
  request_body: string
  headers: string
  params: string
  assertions: TestCaseAssertion[]
  extract_vars: TestCaseExtractVar[]
  created_by: number
  created_at: string
  updated_at: string
}

export interface TestCaseListResponse {
  items: TestCaseItem[]
  total: number
  page: number
  page_size: number
}

export interface CaseCreate {
  api_id: number
  name: string
  description?: string
  priority?: string
  case_type?: string
  status?: string
  tags?: string
  request_body?: string
  headers?: string
  params?: string
  assertions?: TestCaseAssertion[]
  extract_vars?: TestCaseExtractVar[]
}

export type CaseUpdate = Partial<CaseCreate>

// ── 用例列表 ──
export function listCases(
  projectId: number,
  params?: {
    api_id?: number
    status?: string
    case_type?: string
    page?: number
    page_size?: number
  },
) {
  return request.get<TestCaseListResponse>(`/projects/${projectId}/cases`, { params })
}

// ── 用例详情 ──
export function getCase(projectId: number, caseId: number) {
  return request.get<TestCaseItem>(`/projects/${projectId}/cases/${caseId}`)
}

// ── 创建用例 ──
export function createCase(projectId: number, data: CaseCreate) {
  return request.post<TestCaseItem>(`/projects/${projectId}/cases`, data)
}

// ── 更新用例 ──
export function updateCase(projectId: number, caseId: number, data: CaseUpdate) {
  return request.put<TestCaseItem>(`/projects/${projectId}/cases/${caseId}`, data)
}

// ── 删除用例（移至回收站）──
export function deleteCase(projectId: number, caseId: number) {
  return request.delete(`/projects/${projectId}/cases/${caseId}`)
}

// ── 回收站列表 ──
export function listDeletedCases(projectId: number) {
  return request.get<{ items: TestCaseItem[] }>(`/projects/${projectId}/cases/recycle/list`)
}

// ── 恢复用例 ──
export function restoreCase(projectId: number, caseId: number) {
  return request.post(`/projects/${projectId}/cases/${caseId}/restore`)
}

// ── 永久删除用例 ──
export function permanentDeleteCase(projectId: number, caseId: number) {
  return request.delete(`/projects/${projectId}/cases/${caseId}/permanent`)
}

// ── 批量更新用例（优先级/标签）──
export function batchUpdateCases(projectId: number, ids: number[], params?: { priority?: string; tags?: string }) {
  return request.put(
    `/projects/${projectId}/cases/batch/update`,
    { ids },
    { params },
  )
}

// ── 批量删除用例 ──
export function batchDeleteCases(projectId: number, ids: number[]) {
  return request.delete(`/projects/${projectId}/cases/batch`, { data: { ids } })
}

// ── 标记/取消标记种子 ──
export function markCaseAsSeed(projectId: number, caseId: number) {
  return request.put<{ is_seed: number; message: string }>(`/projects/${projectId}/cases/${caseId}/seed-mark`)
}

// ── 用例转场景 ──
export function casesToScene(
  projectId: number,
  data: {
    case_ids: number[]
    scene_name: string
    scene_description?: string
    target_scene_id?: number
  },
) {
  return request.post<{
    scene_id: number
    scene_name: string
    created_steps: number
    step_ids: number[]
  }>(`/projects/${projectId}/cases/batch/to-scene`, data)
}

// ── 运行单个用例 ──
export function runCase(projectId: number, caseId: number, envId: number) {
  return request.post(`/projects/${projectId}/run/case/${caseId}`, null, { params: { env_id: envId } })
}

// ── 通过 API 创建用例 ──
export function createApiCase(projectId: number, apiId: number, data: CaseCreate) {
  return request.post<TestCaseItem>(`/projects/${projectId}/apis/${apiId}/cases`, data)
}