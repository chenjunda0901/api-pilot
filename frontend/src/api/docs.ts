import request from './request'

export interface DocPublishRequest {
  name?: string
  description?: string
  password?: string
  expires_in_days?: number
  include_categories?: number[]
  env_id?: number | null
}

export interface DocItem {
  id: number
  name: string
  description: string
  project_id: number
  share_token: string
  password_hash: string
  expires_at: string | null
  is_revoked: boolean
  created_by: number
  created_at: string
  updated_at: string
}

export interface DocPublishResponse extends DocItem {
  share_url: string
}

export interface SharedDocData {
  project_name: string
  description: string
  categories: unknown[]
  apis: unknown[]
  environment?: unknown
}

export interface ParamDoc {
  name: string
  type: string
  required: boolean
  description: string
}

export interface RequestExample {
  name: string
  body: string
}

export interface ResponseExample {
  name: string
  status_code: number | string
  body: string
}

export interface ApiDocData {
  api_id: number
  name: string
  method: string
  path: string
  description: string
  description_md: string
  param_docs: ParamDoc[]
  request_examples: RequestExample[]
  response_examples: ResponseExample[]
  is_draft: boolean
}

export interface ApiDocSaveRequest {
  description?: string
  param_docs?: ParamDoc[] | null
  request_examples?: RequestExample[] | null
  response_examples?: ResponseExample[] | null
  is_draft?: boolean
}

export interface DocVersionItem {
  id: number
  api_id: number
  change_summary: string
  changed_by: number | null
  created_at: string
}

// ── 发布 API 文档 ──
export function publishDocs(projectId: number, data: DocPublishRequest) {
  return request.post<DocPublishResponse>(`/projects/${projectId}/docs/publish`, data)
}

// ── 文档列表 ──
export function listDocs(projectId: number) {
  return request.get<DocItem[]>(`/projects/${projectId}/docs/list`)
}

// ── 撤销文档 ──
export function revokeDoc(projectId: number, docId: number) {
  return request.post(`/projects/${projectId}/docs/${docId}/revoke`)
}

// ── 删除文档 ──
export function deleteDoc(projectId: number, docId: number) {
  return request.delete(`/projects/${projectId}/docs/${docId}`)
}

// ── 通过分享令牌获取文档（公开）──
export function getSharedDoc(token: string, password?: string) {
  return request.get<SharedDocData>(`/shared/docs/${token}`, {
    params: { password },
  })
}

// ── 获取接口文档 ──
export function getApiDoc(projectId: number, apiId: number) {
  return request.get<ApiDocData>(`/projects/${projectId}/docs/api/${apiId}`)
}

// ── 保存接口文档 ──
export function saveApiDoc(projectId: number, apiId: number, data: ApiDocSaveRequest) {
  return request.put<ApiDocData>(`/projects/${projectId}/docs/api/${apiId}`, data)
}

// ── 获取文档版本历史 ──
export function listDocVersions(projectId: number, apiId: number) {
  return request.get<DocVersionItem[]>(`/projects/${projectId}/docs/api/${apiId}/versions`)
}

// ── 回滚文档版本 ──
export function rollbackDocVersion(projectId: number, apiId: number, versionId: number) {
  return request.post<ApiDocData>(`/projects/${projectId}/docs/api/${apiId}/versions/${versionId}/rollback`)
}