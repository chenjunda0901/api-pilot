import request from './request'

export interface ProjectItem {
  id: number
  name: string
  description: string
  is_public: boolean
  created_by: number
  created_at: string
  updated_at: string
  scene_count?: number
  api_count?: number
  case_count?: number
  member_count?: number
  role?: string
}

export interface ProjectDetail {
  id: number
  name: string
  description: string
  is_public: boolean
  global_demo?: number
  created_by: number
  role?: string
  api_count: number
  category_count: number
  case_count: number
  scene_count: number
  member_count: number
  environment_count: number
}

export interface ProjectCreate {
  name: string
  description?: string
  is_public?: boolean
}

export interface ProjectUpdate {
  name?: string
  description?: string
  is_public?: boolean
}

export interface GlobalVariable {
  key: string
  value: string
  enabled?: boolean
  description?: string
}

export interface GlobalConfig {
  global_variables: GlobalVariable[]
  global_params: { headers?: Array<{ key: string; value: string; enabled?: boolean }> }
}

export interface GlobalConfigUpdate {
  global_variables?: GlobalVariable[]
  global_params?: { headers?: Array<{ key: string; value: string }> }
}

export interface ProjectListResponse {
  items: ProjectItem[]
  total: number
  page: number
  page_size: number
}

// ── 项目列表 ──
export function listProjects(params?: { page?: number; page_size?: number }) {
  return request.get<ProjectListResponse>('/projects', { params })
}

// ── 项目详情 ──
export function getProject(projectId: number) {
  return request.get<ProjectDetail>(`/projects/${projectId}`)
}

// ── 创建项目 ──
export function createProject(data: ProjectCreate) {
  return request.post<ProjectDetail>('/projects', data)
}

// ── 更新项目 ──
export function updateProject(projectId: number, data: ProjectUpdate) {
  return request.put<ProjectDetail>(`/projects/${projectId}`, data)
}

// ── 删除项目 ──
export function deleteProject(projectId: number) {
  return request.delete(`/projects/${projectId}`)
}

// ── 获取全局配置 ──
export function getGlobalConfig(projectId: number) {
  return request.get<GlobalConfig>(`/projects/${projectId}/global-config`)
}

// ── 更新全局配置 ──
export function updateGlobalConfig(projectId: number, data: GlobalConfigUpdate) {
  return request.put(`/projects/${projectId}/global-config`, data)
}

// ── 添加/更新单个全局变量（仅需读权限）──
export function upsertGlobalVariable(projectId: number, key: string, value: string) {
  return request.post<{ key: string; value: string; updated: boolean }>(
    `/projects/${projectId}/global-variables`,
    { key, value },
  )
}

// ── Fork 种子演示项目 ──
export interface ForkSeedResult {
  id: number
  name: string
  is_new: boolean
  message: string
}

export function forkSeedProject() {
  return request.post<ForkSeedResult>('/projects/seed/fork')
}