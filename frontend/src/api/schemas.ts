import request from './request'

export interface DataSchema {
  id: number
  project_id: number
  name: string
  description: string
  schema: Record<string, unknown> | string
  sample: Record<string, unknown> | null
  mock_count: number
  created_at: string
  updated_at: string
}

export interface DataSchemaListResponse {
  items: DataSchema[]
  total: number
}

export interface DataSchemaCreate {
  name: string
  description?: string
  schema: Record<string, unknown> | string
}

export type DataSchemaUpdate = Partial<DataSchemaCreate>

export function listDataSchemas(projectId: number, params?: { keyword?: string; page?: number; page_size?: number }) {
  return request.get<DataSchemaListResponse>(`/projects/${projectId}/data-schemas`, { params })
}

export function getDataSchema(projectId: number, schemaId: number) {
  return request.get<DataSchema>(`/projects/${projectId}/data-schemas/${schemaId}`)
}

export function createDataSchema(projectId: number, data: DataSchemaCreate) {
  return request.post<DataSchema>(`/projects/${projectId}/data-schemas`, data)
}

export function updateDataSchema(projectId: number, schemaId: number, data: DataSchemaUpdate) {
  return request.patch<DataSchema>(`/projects/${projectId}/data-schemas/${schemaId}`, data)
}

export function deleteDataSchema(projectId: number, schemaId: number) {
  return request.delete(`/projects/${projectId}/data-schemas/${schemaId}`)
}

export function previewSchema(projectId: number, schemaId: number, count = 1) {
  return request.post<{ samples: Array<Record<string, unknown>> }>(`/projects/${projectId}/data-schemas/${schemaId}/preview`, { count })
}

export function importDataSchema(projectId: number, data: { name: string; description?: string; content: string }) {
  return request.post<DataSchema>(`/projects/${projectId}/data-schemas/import`, data)
}
