// ============================================================
// 环境管理类型
// ============================================================

export interface Environment {
  id: number
  project_id: number
  name: string
  services: ServiceEntry[]
  variables: VariableEntry[]
  headers: HeaderEntry[]
  created_at: string
  updated_at: string
}

export interface ServiceEntry {
  url?: string
  name?: string
}

export interface VariableEntry {
  key: string
  value: string
  enabled?: boolean
}

export interface HeaderEntry {
  key: string
  value: string
  enabled?: boolean
}
