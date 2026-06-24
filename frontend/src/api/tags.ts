import request from './request'

export interface TagItem {
  id: number
  project_id: number
  name: string
  color: string
  api_count: number
  created_at: string
}

export function listTags(projectId: number) {
  return request.get<TagItem[]>(`/projects/${projectId}/tags`)
}

export function createTag(projectId: number, data: { name: string; color?: string }) {
  return request.post<TagItem>(`/projects/${projectId}/tags`, data)
}

export function updateTag(projectId: number, tagId: number, data: { name?: string; color?: string }) {
  return request.put(`/projects/${projectId}/tags/${tagId}`, data)
}

export function deleteTag(projectId: number, tagId: number) {
  return request.delete(`/projects/${projectId}/tags/${tagId}`)
}

export function addApisToTag(projectId: number, tagId: number, apiIds: number[]) {
  return request.post(`/projects/${projectId}/tags/${tagId}/apis`, { api_ids: apiIds })
}

export function removeApisFromTag(projectId: number, tagId: number, apiIds: number[]) {
  return request.delete(`/projects/${projectId}/tags/${tagId}/apis`, { data: { api_ids: apiIds } })
}
