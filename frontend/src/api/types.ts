export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  detail?: string
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ListQueryParams {
  page?: number
  page_size?: number
  keyword?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface IdParam {
  id: string | number
}

export interface ProjectIdParam {
  project_id: string | number
}
