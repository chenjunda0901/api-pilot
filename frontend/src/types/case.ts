// ============================================================
// 测试用例类型
// ============================================================

export interface CaseListItem {
  id: number
  name: string
  api_id: number
  priority: string
  case_type?: string
  last_run_status?: string
  created_at?: string
  updated_at?: string
}

export interface TestCase {
  id: number
  project_id: number
  api_id: number
  name: string
  priority: string
  status: string
  headers: string
  params: string
  body: string
  assertions: string
  extract_vars: string
  created_at: string
  updated_at: string
}

export interface TestAssertion {
  type: 'status' | 'json' | 'body' | 'header' | 'response_time'
  passed: boolean
  operator?: string
  expected?: string
  actual?: string
  value?: string
}
