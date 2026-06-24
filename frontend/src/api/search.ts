import request from './request'

export interface SearchResult {
  type: string
  id: number
  title: string
  subtitle: string
}

export interface SearchResponse {
  apis: SearchResult[]
  cases: SearchResult[]
  scenes: SearchResult[]
  reports: SearchResult[]
  mock_rules: SearchResult[]
  environments: SearchResult[]
}

export interface SearchHistoryItem {
  id: number
  query: string
  created_at: string | null
}

export function globalSearch(projectId: number, keyword: string, type?: string) {
  return request.get<SearchResponse>(`/projects/${projectId}/search`, {
    params: { keyword, type },
  })
}

export function saveSearchHistory(projectId: number, query: string) {
  return request.post(`/projects/${projectId}/search/history`, { query })
}

export function getSearchHistory(projectId: number) {
  return request.get<SearchHistoryItem[]>(`/projects/${projectId}/search/history`)
}

export function clearSearchHistory(projectId: number) {
  return request.delete(`/projects/${projectId}/search/history`)
}
