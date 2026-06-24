import request from './request'

export type AssertionType = 'status' | 'jsonpath' | 'regex' | 'header' | 'response_time' | 'body_contains'

export interface Assertion {
  id?: number
  assertion_type: AssertionType
  expression: string
  operator: string
  expected_value: string
  enabled: boolean
  description?: string
}

export interface AssertionTestResult {
  passed: boolean
  actual: string
  expected: string
  message: string
}

export function testAssertion(projectId: number, apiId: number, data: Assertion & { response_body: string; response_status: number; response_headers?: Record<string, string>; response_time?: number }) {
  return request.post<AssertionTestResult>(`/projects/${projectId}/apis/${apiId}/assertions/test`, data)
}

export function listApiAssertions(projectId: number, apiId: number) {
  return request.get<{ items: Assertion[] }>(`/projects/${projectId}/apis/${apiId}/assertions`)
}

export function listCaseAssertions(projectId: number, caseId: number) {
  return request.get<{ items: Assertion[] }>(`/projects/${projectId}/cases/${caseId}/assertions`)
}

export function saveApiAssertions(projectId: number, apiId: number, assertions: Assertion[]) {
  return request.put(`/projects/${projectId}/apis/${apiId}/assertions`, { assertions })
}

export function saveCaseAssertions(projectId: number, caseId: number, assertions: Assertion[]) {
  return request.put(`/projects/${projectId}/cases/${caseId}/assertions`, { assertions })
}
