// ============================================================
// 通用类型 — API 响应封装、分页、通用工具类型
// ============================================================

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** API 包裹的分页响应 (res.data 的类型) */
export type PaginatedResponse<T> = PaginatedData<T>

/** 通用列表 API 响应快捷类型 */
export type ListResponse<T> = ApiResponse<PaginatedData<T>>
/** 通用单条数据 API 响应快捷类型 */
export type ItemResponse<T> = ApiResponse<T>

/** catch 块中常见的 Axios 错误类型，替代重复的 as 断言 */
export interface ApiError {
  response?: {
    status?: number
    data?: {
      message?: string
      code?: string
      detail?: string
      errors?: Record<string, string>
    }
  }
  message?: string
  code?: string
}

/** 从 catch 的 unknown 错误中安全提取后端错误消息 */
export function getApiErrorMessage(err: unknown, fallback = '操作失败'): string {
  const e = err as ApiError
  return e?.response?.data?.message || e?.response?.data?.detail || e?.message || fallback
}
