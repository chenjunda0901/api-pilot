import request from './request'

export interface EnvironmentService {
  module?: string
  service_name?: string
  url: string
  is_base_url?: boolean
}

export interface EnvironmentVariable {
  key: string
  value: string
  initial_value?: string
  enabled?: boolean
}

export interface EnvironmentHeader {
  key: string
  value: string
  enabled?: boolean
}

export interface EnvironmentItem {
  id: number
  name: string
  project_id: number
  base_url?: string
  services: EnvironmentService[]
  variables: EnvironmentVariable[]
  headers: EnvironmentHeader[]
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface EnvironmentCreate {
  name: string
  services?: EnvironmentService[]
  variables?: EnvironmentVariable[]
  headers?: EnvironmentHeader[]
  is_default?: boolean
}

export type EnvironmentUpdate = Partial<EnvironmentCreate>

// ── 环境列表 ──
export function listEnvironments(projectId: number) {
  return request.get<EnvironmentItem[]>(`/projects/${projectId}/environments`)
}

// ── 环境详情 ──
export function getEnvironment(projectId: number, envId: number) {
  return request.get<EnvironmentItem>(`/projects/${projectId}/environments/${envId}`)
}

// ── 创建环境 ──
export function createEnvironment(projectId: number, data: EnvironmentCreate) {
  return request.post<EnvironmentItem>(`/projects/${projectId}/environments`, data)
}

// ── 更新环境 ──
export function updateEnvironment(projectId: number, envId: number, data: EnvironmentUpdate) {
  return request.put<EnvironmentItem>(`/projects/${projectId}/environments/${envId}`, data)
}

// ── 添加/更新单个环境变量（提取变量专用，仅需读权限）──
export function upsertEnvironmentVariable(projectId: number, envId: number, key: string, value: string) {
  return request.post<{ key: string; value: string; updated: boolean }>(
    `/projects/${projectId}/environments/${envId}/variables`,
    { key, value },
  )
}

// ── 删除环境 ──
export function deleteEnvironment(projectId: number, envId: number) {
  return request.delete(`/projects/${projectId}/environments/${envId}`)
}

// ── 导出环境为 JSON ──
export function exportEnvironment(projectId: number, envId: number) {
  return request.get<EnvironmentItem>(`/projects/${projectId}/environments/${envId}/export`)
}

// ── 克隆环境 ──
export function cloneEnvironment(projectId: number, envId: number) {
  return request.post<EnvironmentItem>(`/projects/${projectId}/environments/${envId}/clone`)
}

// ── 从 .env 文件导入变量 ──
export function importEnvFile(projectId: number, envId: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported_count: number }>(
    `/projects/${projectId}/environments/${envId}/import-env`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

// ── 导出为 .env 文件（返回文本）──
export function exportEnvFile(projectId: number, envId: number) {
  return request.get<string>(`/projects/${projectId}/environments/${envId}/export-env`, {
    responseType: 'text',
  })
}