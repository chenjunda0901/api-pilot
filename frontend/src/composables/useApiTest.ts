/**
 * API 测试工作流工具
 * 提供便捷的 API 创建、测试、调试功能
 */

import { ref, shallowRef } from 'vue'
import { msgSuccess, msgError } from '@/utils/message'
import { logger } from '@/utils/logger'
import request from '../api/request'

// 辅助函数：转换 Axios 响应头为 Record<string, string>
function normalizeHeaders(headers: Record<string, string | string[] | number | undefined> | undefined): Record<string, string> {
  if (!headers) return {}
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(headers)) {
    if (typeof value === 'string') {
      result[key] = value
    } else if (Array.isArray(value)) {
      result[key] = value.join(', ')
    } else if (typeof value === 'number') {
      result[key] = String(value)
    }
  }
  return result
}

// API 定义类型
export interface ApiDefinition {
  id?: number
  name: string
  method: string
  path: string
  category_id?: number
  description?: string
  headers?: Array<{ key: string; value: string; enabled: boolean }>
  params?: Array<{ key: string; value: string; enabled: boolean }>
  body?: string
  body_type?: 'json' | 'form' | 'raw' | 'none'
}

// API 测试请求类型
export interface ApiTestRequest {
  url: string
  method: string
  headers?: Record<string, string>
  params?: Record<string, string>
  body?: string
  body_type?: string
}

// API 测试响应类型
export interface ApiTestResponse {
  status: number
  status_text: string
  headers: Record<string, string>
  body: string
  duration: number
  size: number
  error?: string
}

// 测试历史记录
export interface TestHistoryItem {
  id: string
  request: ApiTestRequest
  response?: ApiTestResponse
  timestamp: number
  name?: string
}

/**
 * API 测试 Hook
 */
export function useApiTest() {
  const isLoading = ref(false)
  const currentResponse = shallowRef<ApiTestResponse | null>(null)
  const testHistory = shallowRef<TestHistoryItem[]>([])
  const error = ref<string | null>(null)

  /**
   * 发送 API 测试请求
   */
  async function sendRequest(testRequest: ApiTestRequest): Promise<ApiTestResponse | null> {
    isLoading.value = true
    error.value = null
    
    const startTime = Date.now()
    
    try {
      // 构建请求头
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...testRequest.headers
      }
      
      // 构建 URL（合并已有查询参数）
      let url = testRequest.url
      if (testRequest.params && Object.keys(testRequest.params).length > 0) {
        // 使用 URL 构造函数安全地合并参数，避免覆盖已有 query string
        const separator = url.includes('?') ? '&' : '?'
        const searchParams = new URLSearchParams()
        Object.entries(testRequest.params).forEach(([key, value]) => {
          if (value) searchParams.append(key, value)
        })
        url = `${url}${separator}${searchParams.toString()}`
      }
      
      // 构建请求体
      let body = undefined
      if (['POST', 'PUT', 'PATCH'].includes(testRequest.method) && testRequest.body) {
        if (testRequest.body_type === 'json') {
          try {
            body = JSON.parse(testRequest.body)
          } catch {
            body = testRequest.body
          }
        } else {
          body = testRequest.body
        }
      }
      
      // 发送请求
      const response = await request({
        url,
        method: testRequest.method,
        headers,
        data: body,
        timeout: 30000,
      })
      
      const duration = Date.now() - startTime
      
      // 解析响应
      const result: ApiTestResponse = {
        status: response.status || 200,
        status_text: response.statusText || 'OK',
        headers: normalizeHeaders(response.headers as Parameters<typeof normalizeHeaders>[0]),
        body: typeof response.data === 'object' ? JSON.stringify(response.data, null, 2) : String(response.data || ''),
        duration,
        size: response.data ? JSON.stringify(response.data).length : 0
      }
      
      currentResponse.value = result
      
      // 添加到历史记录
      addToHistory(testRequest, result)
      
      return result
      
    } catch (err: unknown) {
      const duration = Date.now() - startTime
      const e = err as { message?: string; status?: number; statusText?: string }
      error.value = e.message || '请求失败'
      
      // 记录失败的请求
      const result: ApiTestResponse = {
        status: e.status || 0,
        status_text: e.statusText || 'Error',
        headers: {},
        body: '',
        duration,
        size: 0,
        error: e.message || '请求失败'
      }
      
      currentResponse.value = result
      addToHistory(testRequest, result)
      
      return result
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 脱敏敏感请求头，防止凭据泄漏到 localStorage/XSS
   */
  function sanitizeHeaders(headers: Record<string, string> | undefined): Record<string, string> | undefined {
    if (!headers) return headers
    const SENSITIVE_KEYS = ['authorization', 'x-api-key', 'cookie', 'set-cookie', 'proxy-authorization', 'x-auth-token']
    const result: Record<string, string> = {}
    for (const [key, value] of Object.entries(headers)) {
      if (SENSITIVE_KEYS.includes(key.toLowerCase())) {
        result[key] = '***'
      } else {
        result[key] = value
      }
    }
    return result
  }

  /**
   * 添加到历史记录
   */
  function addToHistory(request: ApiTestRequest, response?: ApiTestResponse) {
    // 脱敏敏感请求头后再存入历史
    const safeRequest: ApiTestRequest = {
      ...request,
      headers: sanitizeHeaders(request.headers),
    }
    const item: TestHistoryItem = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      request: safeRequest,
      response,
      timestamp: Date.now()
    }
    
    testHistory.value = [item, ...testHistory.value.slice(0, 49)]  // 保留最近50条
    
    // 持久化到 localStorage
    try {
      localStorage.setItem('api_test_history', JSON.stringify(testHistory.value))
    } catch {
      // 忽略存储错误
    }
  }

  /**
   * 加载历史记录
   */
  function loadHistory() {
    try {
      const saved = localStorage.getItem('api_test_history')
      if (saved) {
        testHistory.value = JSON.parse(saved)
      }
    } catch (e) {
      logger.warn('加载 API 测试历史失败:', e)
      testHistory.value = []
    }
  }

  /**
   * 清空历史记录
   */
  function clearHistory() {
    testHistory.value = []
    try {
      localStorage.removeItem('api_test_history')
    } catch (e) {
      logger.warn('清空历史记录失败:', e)
    }
  }

  /**
   * 从历史记录恢复
   */
  function restoreFromHistory(id: string) {
    const item = testHistory.value.find(h => h.id === id)
    if (item) {
      return item.request
    }
    return null
  }

  /**
   * 保存 API 定义
   */
  async function saveApi(projectId: number, api: Partial<ApiDefinition>): Promise<ApiDefinition | null> {
    try {
      const method = api.method?.toUpperCase() || 'GET'
      
      if (api.id) {
        // 更新
        const res = await request.put(`/projects/${projectId}/apis/${api.id}`, {
          name: api.name,
          method,
          path: api.path,
          category_id: api.category_id,
          description: api.description,
          headers: api.headers,
          params: api.params,
          body: api.body,
          body_type: api.body_type
        })
        msgSuccess('API 已更新')
        return res.data as ApiDefinition
      } else {
        // 创建
        const res = await request.post(`/projects/${projectId}/apis`, {
          name: api.name,
          method,
          path: api.path,
          category_id: api.category_id,
          description: api.description,
          headers: api.headers,
          params: api.params,
          body: api.body,
          body_type: api.body_type
        })
        msgSuccess('API 已创建')
        return res.data as ApiDefinition
      }
    } catch (err: unknown) {
      const e = err as { message?: string }
      msgError(e.message || '保存失败')
      return null
    }
  }

  /**
   * 从 curl 导入
   */
  function parseCurl(curlCommand: string): ApiTestRequest | null {
    try {
      // 移除换行符
      curlCommand = curlCommand.replace(/\\\n/g, ' ').trim()

      // 检查是否为 curl 命令
      if (!/^curl\s+/i.test(curlCommand)) return null

      // 提取 URL - 优先匹配 http/https URL
      const httpUrlMatch = curlCommand.match(/https?:\/\/[^\s'"]+/i)
      let url: string
      if (httpUrlMatch) {
        url = httpUrlMatch[0]
      } else {
        return null
      }
      
      // 提取方法
      let method = 'GET'
      if (curlCommand.match(/-X\s+POST/i) || curlCommand.match(/--request\s+POST/i)) {
        method = 'POST'
      } else if (curlCommand.match(/-X\s+PUT/i) || curlCommand.match(/--request\s+PUT/i)) {
        method = 'PUT'
      } else if (curlCommand.match(/-X\s+DELETE/i) || curlCommand.match(/--request\s+DELETE/i)) {
        method = 'DELETE'
      } else if (curlCommand.match(/-X\s+PATCH/i) || curlCommand.match(/--request\s+PATCH/i)) {
        method = 'PATCH'
      }
      
      // 提取请求头
      const headers: Record<string, string> = {}
      const headerMatches = curlCommand.matchAll(/(?:-H\s+|--header\s+)['"]([^'":]+):\s*([^'"]+)['"]/gi)
      for (const match of headerMatches) {
        headers[match[1]] = match[2]
      }
      
      // 提取请求体
      let body = ''
      const dataMatch = curlCommand.match(/(?:-d\s+|--data\s+|--data-raw\s+)(['"])(.*?)\1/is)
      if (dataMatch) {
        body = dataMatch[2]
        // 检测 JSON
        try {
          JSON.parse(body)
        } catch {
          // 不是 JSON
        }
      }
      
      // 清理 URL 中的多余参数
      if (url.includes('?')) {
        const [baseUrl, params] = url.split('?')
        url = baseUrl
        // 将查询参数添加到 headers
        params.split('&').forEach(p => {
          const [key] = p.split('=')
          if (key) {
            // 可以选择添加到 URL 或 params
          }
        })
      }
      
      return {
        url,
        method,
        headers,
        body
      }
    } catch (e) {
      logger.warn('curl 解析失败:', e)
      return null
    }
  }

  /**
   * 导出为 curl 命令
   */
  function toCurl(request: ApiTestRequest): string {
    let cmd = `curl -X ${request.method}`
    
    // 添加请求头
    if (request.headers) {
      Object.entries(request.headers).forEach(([key, value]) => {
        if (value) {
          cmd += ` \\\n  -H '${key}: ${value}'`
        }
      })
    }
    
    // 添加请求体
    if (request.body && ['POST', 'PUT', 'PATCH'].includes(request.method)) {
      cmd += ` \\\n  -d '${request.body.replace(/'/g, "\\'")}'`
    }
    
    // 添加 URL
    let url = request.url
    if (request.params) {
      const searchParams = new URLSearchParams()
      Object.entries(request.params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value)
      })
      const queryString = searchParams.toString()
      if (queryString) {
        url += `?${queryString}`
      }
    }
    
    cmd += ` \\\n  '${url}'`
    
    return cmd
  }

  // 加载历史记录
  loadHistory()

  return {
    // 状态
    isLoading,
    currentResponse,
    testHistory,
    error,
    
    // 方法
    sendRequest,
    saveApi,
    parseCurl,
    toCurl,
    loadHistory,
    clearHistory,
    restoreFromHistory
  }
}

/**
 * HTTP 方法对应的颜色
 */
export const METHOD_COLORS: Record<string, { bg: string; text: string }> = {
  GET: { bg: '#dcfce7', text: '#166534' },
  POST: { bg: '#dbeafe', text: '#1e40af' },
  PUT: { bg: '#fef3c7', text: '#92400e' },
  PATCH: { bg: '#fef3c7', text: '#92400e' },
  DELETE: { bg: '#fee2e2', text: '#991b1b' },
  HEAD: { bg: '#f3e8ff', text: '#6b21a8' },
  OPTIONS: { bg: '#f3e8ff', text: '#6b21a8' }
}

/**
 * HTTP 状态码对应的颜色
 */
export function getStatusColor(status: number): string {
  if (status >= 200 && status < 300) return '#22c55e'  // 绿色
  if (status >= 300 && status < 400) return '#f59e0b'  // 黄色
  if (status >= 400 && status < 500) return '#f97316'  // 橙色
  if (status >= 500) return '#ef4444'  // 红色
  return '#6b7280'  // 灰色
}

export default {
  useApiTest,
  METHOD_COLORS,
  getStatusColor
}