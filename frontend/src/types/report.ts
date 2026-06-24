// ============================================================
// 测试报告类型
// ============================================================

import type { TestAssertion, StressMetrics } from './scene'

export interface TestReport {
  id: number
  project_id: number
  scene_id: number
  environment_id: number
  status: "running" | "success" | "failed"
  displayStatus?: "running" | "success" | "failed" | "interrupted"
  pass_count: number
  fail_count: number
  skip_count?: number
  total_count: number
  duration: number
  executor_id: number
  scene_name?: string
  env_name?: string
  created_at: string
  updated_at: string
  stress_metrics?: StressMetrics
  steps?: ReportStep[]
}

export interface ReportStep {
  id: number
  name: string
  method: string
  request_method?: string
  request_url?: string
  url?: string
  status: number | string
  response_status?: number | string
  duration: number
  request_headers: Record<string, unknown>
  request_body: string
  response_headers: Record<string, unknown>
  response_body: string
  assertions: TestAssertion[]
  extract_vars: Record<string, unknown>
  passed: boolean
  error_message?: string
}
