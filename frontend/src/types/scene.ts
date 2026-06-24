// ============================================================
// 测试场景类型
// ============================================================

export interface TestScene {
  id: number
  project_id: number
  name: string
  description: string
  thread_count: number
  on_failure: "continue" | "stop"
  var_persist_target: "environment" | "global" | "none"
  schedule_cron: string | null
  schedule_enabled: number
  env_id: number | null
  created_at: string
  updated_at: string
}

export interface SceneStep {
  id: number
  scene_id: number
  node_id: string
  node_type: "request" | "condition" | "loop" | "wait"
  label: string
  api_id: number | null
  test_case_id: number | null
  sort_order: number
  enabled: number
  headers?: string | null
  query_params?: string | null
  request_body?: string | null
  assertions?: string | null
  extract_vars?: string | null
  condition_expression?: string | null
  loop_count?: number | null
  wait_duration?: number | null
  _key?: string
  _selected?: boolean
}

export interface StressMetrics {
  p50?: number
  p90?: number
  p95?: number
  p99?: number
  avg?: number
  throughput?: number
  error_rate?: number
  total_requests?: number
}
