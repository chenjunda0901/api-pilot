import request from './request'

export function getDatasets(projectId: number) {
  return request.get(`/projects/${projectId}/datasets`)
}

export function createDataset(data: { name: string; description?: string; project_id: number }) {
  return request.post(`/projects/${data.project_id}/datasets`, data)
}

export function getDatasetDetail(projectId: number, datasetId: number) {
  return request.get(`/projects/${projectId}/datasets/${datasetId}`)
}

export function updateDataset(projectId: number, datasetId: number, data: { name?: string; description?: string }) {
  return request.put(`/projects/${projectId}/datasets/${datasetId}`, data)
}

export function deleteDataset(projectId: number, datasetId: number) {
  return request.delete(`/projects/${projectId}/datasets/${datasetId}`)
}

export function addDatasetRows(projectId: number, datasetId: number, rows: { data: string; is_enabled?: boolean }[]) {
  return request.post(`/projects/${projectId}/datasets/${datasetId}/rows`, { rows })
}

export function batchUpdateRows(projectId: number, datasetId: number, rows: { data: string; is_enabled?: boolean }[]) {
  return request.put(`/projects/${projectId}/datasets/${datasetId}/rows/batch`, { rows })
}

export function deleteDatasetRow(projectId: number, datasetId: number, rowId: number) {
  return request.delete(`/projects/${projectId}/datasets/${datasetId}/rows/${rowId}`)
}
