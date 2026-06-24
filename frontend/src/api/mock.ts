import request from './request'
import type { MockRule } from '../types'

export function getMockRules(projectId: number, params?: { method?: string; page?: number; page_size?: number }) {
  return request.get(`/projects/${projectId}/mock-rules`, { params })
}

export function createMockRule(projectId: number, data: Partial<MockRule>) {
  return request.post(`/projects/${projectId}/mock-rules`, data)
}

export function updateMockRule(projectId: number, ruleId: number, data: Partial<MockRule>) {
  return request.put(`/projects/${projectId}/mock-rules/${ruleId}`, data)
}

export function deleteMockRule(projectId: number, ruleId: number) {
  return request.delete(`/projects/${projectId}/mock-rules/${ruleId}`)
}

export function getMockStatistics(projectId: number) {
  return request.get(`/projects/${projectId}/mock-rules/statistics`)
}

export function testMockRule(data: {
  project_id: number
  path: string
  method: string
  query_params?: Record<string, unknown>
  headers?: Record<string, unknown>
  body?: Record<string, unknown>
}) {
  return request.post('/mock/test', data)
}

export function generateFromSchema(projectId: number, schema: Record<string, unknown>) {
  return request.post(`/projects/${projectId}/mock-rules/generate-from-schema`, { json_schema: schema })
}

export interface MockCallLog {
  id: number
  project_id: number
  mock_rule_id: number | null
  request_method: string
  request_path: string
  request_headers: Record<string, unknown>
  request_query: Record<string, unknown>
  matched_rule_name: string | null
  response_status: number
  response_body_hash: string | null
  duration_ms: number
  created_at: string
}

export function getMockCallLogs(projectId: number, params?: {
  rule_id?: number
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}) {
  return request.get<{ items: MockCallLog[]; total: number; page: number; page_size: number }>(
    `/projects/${projectId}/mock-rules/call-logs`,
    { params }
  )
}

export function clearMockCallLogs(projectId: number) {
  return request.delete(`/projects/${projectId}/mock-rules/call-logs`)
}
