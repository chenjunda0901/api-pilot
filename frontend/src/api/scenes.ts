import request from './request'

export interface SceneStep {
  id: number
  scene_id: number
  test_case_id: number | null
  sort_order: number
  name?: string
  label?: string
  step_type?: string
  config?: Record<string, unknown>
  assertions?: unknown[]
  extract_vars?: unknown[]
  enabled: number | boolean
  created_at: string
  updated_at: string
}

export interface SceneItem {
  id: number
  name: string
  description: string
  project_id: number
  created_by: number
  status?: string
  steps_count?: number
  is_seed?: number
  created_at: string
  updated_at: string
}

export interface SceneListResponse {
  items: SceneItem[]
  total: number
  page: number
  page_size: number
}

export interface SceneDetail extends SceneItem {
  steps: SceneStep[]
  schedule?: {
    cron: string
    enabled: boolean
    env_id: number | null
  }
}

export interface SceneCreate {
  name: string
  description?: string
  var_persist_target?: 'environment' | 'global' | 'none'
  steps?: Array<{
    test_case_id?: number
    sort_order?: number
    enabled?: boolean
    label?: string
  }>
}

export type SceneUpdate = Partial<SceneCreate>

export interface SceneSchedule {
  cron: string
  enabled: boolean
  env_id: number | null
}

// ── 场景列表 ──
export function listScenes(
  projectId: number,
  params?: { keyword?: string; page?: number; page_size?: number },
) {
  return request.get<SceneListResponse>(`/projects/${projectId}/scenes`, { params })
}

// ── 场景详情 ──
export function getScene(projectId: number, sceneId: number) {
  return request.get<SceneDetail>(`/projects/${projectId}/scenes/${sceneId}`)
}

// ── 创建场景 ──
export function createScene(projectId: number, data: SceneCreate) {
  return request.post<SceneItem>(`/projects/${projectId}/scenes`, data)
}

// ── 更新场景 ──
export function updateScene(projectId: number, sceneId: number, data: SceneUpdate) {
  return request.put<SceneItem>(`/projects/${projectId}/scenes/${sceneId}`, data)
}

// ── 删除场景（移至回收站）──
export function deleteScene(projectId: number, sceneId: number) {
  return request.delete(`/projects/${projectId}/scenes/${sceneId}`)
}

// ── 回收站列表 ──
export function listDeletedScenes(projectId: number) {
  return request.get<{ items: SceneItem[] }>(`/projects/${projectId}/scenes/recycle/list`)
}

// ── 恢复场景 ──
export function restoreScene(projectId: number, sceneId: number) {
  return request.post(`/projects/${projectId}/scenes/${sceneId}/restore`)
}

// ── 永久删除场景 ──
export function permanentDeleteScene(projectId: number, sceneId: number) {
  return request.delete(`/projects/${projectId}/scenes/${sceneId}/permanent`)
}

// ── 标记/取消标记种子 ──
export function markSceneAsSeed(projectId: number, sceneId: number) {
  return request.put<{ is_seed: number; message: string }>(`/projects/${projectId}/scenes/${sceneId}/seed-mark`)
}

// ── 获取定时配置 ──
export function getSceneSchedule(projectId: number, sceneId: number) {
  return request.get<SceneSchedule>(`/projects/${projectId}/scenes/${sceneId}/schedule`)
}

// ── 更新定时配置 ──
export function updateSceneSchedule(
  projectId: number,
  sceneId: number,
  params: { cron: string; enabled: boolean; env_id?: number },
) {
  return request.put(`/projects/${projectId}/scenes/${sceneId}/schedule`, null, { params })
}

// ── 删除定时配置 ──
export function deleteSceneSchedule(projectId: number, sceneId: number) {
  return request.delete(`/projects/${projectId}/scenes/${sceneId}/schedule`)
}

// ── 获取步骤最近提取的变量 ──
export function getStepLastExtracted(projectId: number, sceneId: number, stepId: number) {
  return request.get<Record<string, { value: unknown; source_step: string; source_type: string }>>(
    `/projects/${projectId}/scenes/${sceneId}/steps/${stepId}/last-extracted`,
  )
}

// ── 批量复制步骤 ──
export function batchCopySteps(
  projectId: number,
  sceneId: number,
  data: { steps: Array<{ source_scene_id: number; step_ids: number[] }> },
) {
  return request.post(`/projects/${projectId}/scenes/${sceneId}/steps/batch`, data)
}

// ── 批量删除步骤 ──
export function batchDeleteSteps(projectId: number, sceneId: number, data: { step_ids: number[] }) {
  return request.delete(`/projects/${projectId}/scenes/${sceneId}/steps/batch`, { data })
}

// ── 批量启用/禁用步骤 ──
export function batchToggleSteps(
  projectId: number,
  sceneId: number,
  data: { step_ids: number[]; enabled: boolean },
) {
  return request.put(`/projects/${projectId}/scenes/${sceneId}/steps/batch/enable`, data)
}

// ── 导出场景 ──
export function exportScene(projectId: number, sceneId: number) {
  return request.post(`/projects/${projectId}/scenes/${sceneId}/export`)
}

// ── 导入场景 ──
export function importScene(
  projectId: number,
  data: { data: Record<string, unknown>; project_id: number; overwrite?: boolean },
) {
  return request.post(`/projects/${projectId}/scenes/import`, data)
}

// ── 运行场景 ──
export function runScene(projectId: number, sceneId: number, envId: number) {
  return request.post(`/projects/${projectId}/run/linear/scene/${sceneId}`, null, { params: { env_id: envId } })
}