import request from './request'

/** 兼容前端旧 scope 值（environment/scene）；后端使用 env/case */
export type VariableScope = 'global' | 'project' | 'environment' | 'env' | 'scene' | 'case'

const SCOPE_TO_API: Record<string, string> = {
  global: 'global',
  project: 'project',
  environment: 'env',
  env: 'env',
  scene: 'case',  // 旧 "scene" 兜底映射到 case
  case: 'case',
}

const SCOPE_FROM_API: Record<string, VariableScope> = {
  global: 'global',
  project: 'project',
  env: 'environment',
  case: 'case',
}

export interface Variable {
  id: number
  key: string
  value: string
  scope: VariableScope
  scope_id: number | null
  scope_name: string
  encrypted: boolean
  description?: string
  masked?: boolean
  updated_at: string
}

export interface VariableLayer {
  scope: VariableScope
  scope_id: number | null
  scope_name: string
  variables: Variable[]
}

export interface EffectiveVariablesResponse {
  layers: VariableLayer[]
  effective: Record<string, string>
}

/** 后端 _to_dict 输出 → 前端 Variable（字段名映射） */
function _fromApi(item: Record<string, unknown>): Variable {
  return {
    id: Number(item.id),
    key: String(item.name ?? ''),
    value: String(item.value ?? ''),
    scope: (SCOPE_FROM_API[String(item.scope ?? 'project')] ?? 'project') as VariableScope,
    scope_id: (item.scope_id as number | null) ?? null,
    scope_name: String(item.scope ?? ''),
    encrypted: Boolean(item.is_secret),
    description: (item.description as string) || undefined,
    masked: Boolean(item.is_secret),
    updated_at: String(item.created_at ?? ''),
  }
}

export interface ListVariablesResult {
  items: Variable[]
  total: number
  page: number
  page_size: number
}

export function listVariables(projectId: number, scope?: VariableScope) {
  return request.get<{ items: Variable[]; total: number; page: number; page_size: number }>(
    '/variables',
    { params: { project_id: projectId, scope: scope ? SCOPE_TO_API[scope] : undefined } }
  ).then((res) => ({
    ...res,
    data: {
      items: (res.data?.items || []).map((it) => _fromApi(it as Record<string, unknown>)),
      total: res.data?.total ?? 0,
      page: res.data?.page ?? 1,
      page_size: res.data?.page_size ?? 50,
    } as ListVariablesResult,
  }))
}

export interface UpsertVariableInput {
  id?: number
  key: string
  value: string
  scope: VariableScope
  scope_id?: number | null
  encrypted?: boolean
  description?: string
}

export function upsertVariable(projectId: number, data: UpsertVariableInput) {
  const body = {
    name: data.key,
    value: data.value,
    scope: SCOPE_TO_API[data.scope] || 'project',
    scope_id: data.scope_id ?? (SCOPE_TO_API[data.scope] === 'project' ? projectId : null),
    is_secret: !!data.encrypted,
    description: data.description ?? '',
  }
  if (data.id) {
    return request.patch<Variable>(`/variables/${data.id}`, body).then((res) => ({
      ...res,
      data: res.data ? _fromApi(res.data as Record<string, unknown>) : (res.data as unknown as Variable),
    }))
  }
  return request.post<Variable>('/variables', body).then((res) => ({
    ...res,
    data: res.data ? _fromApi(res.data as Record<string, unknown>) : (res.data as unknown as Variable),
  }))
}

export function deleteVariable(_projectId: number, variableId: number) {
  return request.delete(`/variables/${variableId}`)
}

export function revealEncryptedVariable(variableId: number) {
  return request.get<{ id: number; name: string; value: string; is_secret: boolean }>(`/variables/${variableId}/reveal`)
}

export interface VariableReference {
  type: 'step' | 'case'
  id: number
  name: string
  scene_name: string
  scene_id: number | null
}

/** 引用追踪路由挂在 projects router 下（不是 variables router） */
export function getVariableReferences(projectId: number, variableKey: string) {
  return request.get<VariableReference[]>(`/projects/${projectId}/variables/${encodeURIComponent(variableKey)}/references`)
}

/**
 * 当前请求生效值聚合：后端暂无独立 endpoint，构造空响应以保证调用方不报错。
 * 5 层作用域解析由后端 VariableResolver 在 /variables/resolve 中处理。
 */
export function getEffectiveVariables(_projectId: number, _params?: { environment_id?: number; scene_id?: number; case_id?: number }) {
  return Promise.resolve({ data: { layers: [], effective: {} } as EffectiveVariablesResponse })
}
