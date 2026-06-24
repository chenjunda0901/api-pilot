// ============================================================
// API 接口定义类型
// ============================================================

export interface CategoryNode {
  id: number
  name: string
  parent_id: number | null
  sort_order?: number
  children: CategoryNode[]
  api_count?: number
  first_api?: { id: number; name: string; method: string; category_id: number } | null
}

export interface ApiListItem {
  id: number
  name: string
  method: string
  path: string
  description?: string
  category_id: number | null
  case_count?: number
  created_at?: string
  updated_at?: string
}

export interface ApiDefinition {
  id: number
  project_id: number
  category_id: number | null
  name: string
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "HEAD" | "OPTIONS"
  path: string
  description: string
  headers: Record<string, unknown>[]
  params: Record<string, unknown>[]
  body: Record<string, unknown>
  auth_type: string
  created_at: string
  updated_at: string
}

export interface ApiCategory {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
  api_count?: number
  children?: ApiCategory[]
  first_api?: { id: number; name: string; method: string; category_id: number }
}
