import request from './request'

export interface CategoryNode {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
  api_count: number
  children: CategoryNode[]
  first_api: {
    id: number
    name: string
    method: string
    category_id: number
    case_count: number
  } | null
}

export interface CategoryTreeResponse {
  tree: CategoryNode[]
  first_api: {
    id: number
    name: string
    method: string
    category_id: number
    case_count: number
  } | null
}

export interface CategoryCreate {
  name: string
  parent_id?: number | null
  sort_order?: number
}

export interface CategoryUpdate {
  name?: string
  parent_id?: number | null
  sort_order?: number
}

// ── 接口目录树 ──
export function getCategoryTree(projectId: number) {
  return request.get<CategoryTreeResponse>(`/projects/${projectId}/categories`)
}

// ── 创建接口目录 ──
export function createCategory(projectId: number, data: CategoryCreate) {
  return request.post<{ id: number; name: string }>(`/projects/${projectId}/categories`, data)
}

// ── 标记/取消标记种子 ──
export function markCategoryAsSeed(projectId: number, catId: number) {
  return request.put<{ is_seed: number; message: string }>(`/projects/${projectId}/categories/${catId}/seed-mark`)
}

// ── 更新接口目录 ──
export function updateCategory(projectId: number, catId: number, data: CategoryUpdate) {
  return request.put<{ id: number; name: string }>(`/projects/${projectId}/categories/${catId}`, data)
}

// ── 删除接口目录 ──
export function deleteCategory(projectId: number, catId: number) {
  return request.delete(`/projects/${projectId}/categories/${catId}`)
}