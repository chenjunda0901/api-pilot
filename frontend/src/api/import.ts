import request from './request'

export interface ImportPreviewCategory {
  name: string
  apifox_id?: string
  exists?: boolean
  isApi?: boolean
  method?: string
  path?: string
  children?: ImportPreviewCategory[]
}

export interface ImportEnvironmentItem {
  name: string
  apifox_env_id?: string
  exists?: boolean
  base_url?: string
  services?: Array<{ module: string; service_name: string; url: string; is_base_url: boolean }>
  variables?: Array<{ key: string; value: string; initial_value?: string; enabled?: boolean }>
  headers?: Array<{ key: string; value: string }>
}

export interface ImportTestCaseItem {
  name: string
  api_id?: string | number
  description?: string
  priority?: string
  assertions?: Array<{ type: string; expression: string; expected: string; comparator: string }>
  extract_vars?: Array<{ name: string; expression: string; type: string }>
}

export interface ImportPreviewResponse {
  format: string
  project_name: string
  stats: {
    total_categories: number
    total_apis: number
    total_environments: number
    total_variables: number
    total_headers: number
    total_servers?: number
    total_test_cases?: number
    total_request_collections?: number
    total_test_case_collections?: number
  }
  categories: ImportPreviewCategory[]
  environments: ImportEnvironmentItem[]
  global_variables: Array<{ key: string; value: string; description?: string }>
  global_headers: Array<{ key: string; value: string; enabled?: boolean }>
  test_cases?: ImportTestCaseItem[]
}

export interface ImportExecuteResult {
  format?: string
  project_name?: string
  created_apis: number
  updated_apis: number
  skipped_apis: number
  created_categories: number
  skipped_categories: number
  created_environments: number
  updated_environments: number
  imported_variables: number
  imported_headers: number
  created_test_cases?: number
  updated_test_cases?: number
  skipped_test_cases?: number
  failed_count?: number
  skipped_count?: number
  errors: string[]
  structured_errors?: Array<{ index?: number; name?: string; method?: string; path?: string; reason: string }>
}

export interface ImportOptions {
  import_variables: boolean
  import_headers: boolean
  import_environments: boolean
  import_test_cases?: boolean
  conflict_strategy: 'skip' | 'update' | 'rename' | 'keep_both'
  target_category_id?: number | null
}

// ===== v2 统一导入接口 =====

export function importPreviewV2(projectId: number, data: { file_content: string }) {
  return request.post<ImportPreviewResponse>(`/projects/${projectId}/import/preview`, data)
}

export function importExecuteV2(
  projectId: number,
  data: {
    file_content: string
    import_options: ImportOptions
    target_category_id?: number | null
    selected_items?: string[] | undefined
  },
) {
  return request.post<ImportExecuteResult>(`/projects/${projectId}/import/execute`, data)
}

// ===== v1 兼容接口（废弃，保留向后兼容）=====

export function importPreview(projectId: number, data: { file_content: string }) {
  return request.post<ImportPreviewResponse>(`/projects/${projectId}/import/apifox/preview`, data)
}

export function importExecute(
  projectId: number,
  data: {
    file_content: string
    import_options: {
      import_variables: boolean
      import_headers: boolean
      import_environments: boolean
      conflict_strategy: 'skip' | 'update'
    }
  },
) {
  return request.post<ImportExecuteResult>(`/projects/${projectId}/import/apifox`, data)
}

// ===== cURL 导入 =====

export interface CurlImportResult {
  id: number
  name: string
  method: string
  path: string
  category_id: number | null
  headers: Array<{ key: string; value: string; enabled?: boolean }>
  params: Array<{ key: string; value: string; enabled?: boolean }>
  body: { type: string; content?: string }
  auth: Record<string, unknown>
  cookies: Array<{ key: string; value: string }>
}

export function importCurl(projectId: number, data: { curl_command: string; category_id?: number | null }) {
  return request.post<CurlImportResult>(`/projects/${projectId}/import/curl`, data)
}
