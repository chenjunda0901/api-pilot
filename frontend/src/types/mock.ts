// ============================================================
// Mock 规则类型
// ============================================================

export interface MockCondition {
  field: string
  operator: string
  value: string
}

export interface MockRule {
  id: number
  project_id: number
  name: string
  enabled: boolean
  priority: number
  match_method: string
  match_path: string
  response_status: number
  response_headers: Record<string, unknown>
  response_body: string | null
  response_delay: number
  conditions?: MockCondition[]
  created_at: string
  updated_at: string
}
