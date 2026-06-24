import request from './request'

/** 快照列表项（匹配后端 ApiSnapshot._to_dict） */
export interface Snapshot {
  id: number
  api_id: number
  change_type: string  // create / update / delete
  change_summary: string
  changed_by: number | null
  created_at: string | null
  snapshot_data?: Record<string, unknown>
}

export interface SnapshotListResponse {
  items: Snapshot[]
  total: number
  page: number
  page_size: number
}

/** 快照 diff 结果（匹配后端 diff_api_versions 返回） */
export interface SnapshotDiff {
  api_id: number
  from_snapshot_id: number
  to_snapshot_id: number
  ops: Array<{
    op: string  // add / remove / replace / type_change
    path: string
    old: unknown
    new: unknown
  }>
  summary: string
  breaking: boolean
}

/**
 * 获取接口快照列表
 * 后端路由: GET /projects/{project_id}/apis/{api_id}/history
 */
export function listSnapshots(
  _resourceType: string,
  resourceId: number,
  params?: { page?: number; page_size?: number; project_id?: number }
) {
  const projectId = params?.project_id
  if (!projectId) {
    return Promise.reject(new Error('project_id is required for listSnapshots'))
  }
  return request.get<SnapshotListResponse>(
    `/projects/${projectId}/apis/${resourceId}/history`,
    { params: { page: params?.page ?? 1, page_size: params?.page_size ?? 20 } }
  )
}

/**
 * 对比两个快照
 * 后端路由: GET /projects/{project_id}/apis/{api_id}/diff?v1=&v2=
 */
export function diffSnapshots(
  snapshotAId: number,
  snapshotBId: number,
  projectId: number,
  apiId?: number
) {
  // apiId 可选：如果调用方未传，尝试从快照列表上下文获取
  // 但后端需要 api_id 在路径中，所以这里需要 apiId
  if (!apiId) {
    // 降级：使用旧的 /snapshots/diff 路径（后端可能未实现）
    return request.get<SnapshotDiff>(
      `/projects/${projectId}/apis/0/diff`,
      { params: { v1: snapshotAId, v2: snapshotBId } }
    )
  }
  return request.get<SnapshotDiff>(
    `/projects/${projectId}/apis/${apiId}/diff`,
    { params: { v1: snapshotAId, v2: snapshotBId } }
  )
}

/**
 * 手动写入一条快照
 * 后端路由: POST /projects/{project_id}/apis/{api_id}/snapshot
 */
export function createSnapshot(projectId: number, apiId: number) {
  return request.post<{ message: string }>(
    `/projects/${projectId}/apis/${apiId}/snapshot`
  )
}

/**
 * 从快照恢复接口
 * 注意：后端尚未实现快照恢复端点，此函数保留兼容性
 */
export function restoreSnapshot(snapshotId: number, projectId?: number) {
  // 后端暂无此端点，保留接口兼容
  return request.post<{ api_id: number; snapshot_id: number; message: string }>(
    `/snapshots/restore`,
    null,
    { params: { snapshot_id: snapshotId, ...(projectId ? { project_id: projectId } : {}) } }
  )
}

/**
 * 回滚到指定快照版本
 * 注意：后端尚未实现快照回滚端点，此函数保留兼容性
 */
export function rollbackToSnapshot(snapshotId: number, projectId?: number) {
  return request.post<{ api_id: number; snapshot_id: number; message: string }>(
    `/snapshots/${snapshotId}/restore`,
    null,
    { params: projectId ? { project_id: projectId } : {} }
  )
}
