/**
 * 用例导入/导出工具
 * 支持 JSON/HAR/Postman 格式的用例序列化与反序列化
 */

import { msgSuccess, msgError, msgInfo } from './message'

export interface ExportedCase {
  version: string
  exported_at: string
  case: {
    name: string
    priority: string
    api_id?: number | null
    api_method: string
    api_path: string
    params_overrides: Array<{ name: string; value: string; enabled?: boolean }>
    headers_overrides: Array<{ name: string; value: string; enabled?: boolean }>
    body_overrides: unknown
    auth_overrides: unknown
    assertions: Array<{ type: string; [key: string]: unknown }>
    variable_extractions: Array<{ source: string; expression: string; variable_name: string }>
    pre_script: string
    post_script: string
  }
}

export function exportCaseToJson(caseData: Record<string, unknown>): string {
  const exported: ExportedCase = {
    version: '1.0',
    exported_at: new Date().toISOString(),
    case: {
      name: (caseData.name as string) || '',
      priority: (caseData.priority as string) || 'P1',
      api_id: (caseData.api_id as number) ?? null,
      api_method: (caseData.api_method as string) || '',
      api_path: (caseData.api_path as string) || '',
      params_overrides: (caseData.params_overrides as Array<{ name: string; value: string }>) || [],
      headers_overrides: (caseData.headers_overrides as Array<{ name: string; value: string }>) || [],
      body_overrides: caseData.body_overrides ?? null,
      auth_overrides: caseData.auth_overrides ?? null,
      assertions: (caseData.assertions as Array<Record<string, unknown>>) || [],
      variable_extractions: (caseData.variable_extractions as Array<Record<string, unknown>>) || [],
      pre_script: (caseData.pre_script as string) || '',
      post_script: (caseData.post_script as string) || '',
    },
  }
  return JSON.stringify(exported, null, 2)
}

export async function importCaseFromJson(file: File): Promise<ExportedCase> {
  const text = await file.text()
  const parsed = JSON.parse(text)
  if (!parsed.version || !parsed.case) {
    throw new Error('无效的用例文件格式：缺少 version 或 case 字段')
  }
  return parsed as ExportedCase
}

/**
 * 导出为 HAR (HTTP Archive) 格式
 */
export function exportCaseToHar(caseData: Record<string, unknown>): string {
  const method = (caseData.api_method as string) || 'GET'
  const url = (caseData.api_path as string) || ''
  const headers = (caseData.headers_overrides as Array<{ name: string; value: string; enabled?: boolean }>) || []
  const params = (caseData.params_overrides as Array<{ name: string; value: string; enabled?: boolean }>) || []
  const body = caseData.body_overrides as Record<string, unknown> | null

  const har = {
    log: {
      version: '1.2',
      creator: {
        name: 'API Pilot',
        version: '1.0',
      },
      entries: [
        {
          startedDateTime: new Date().toISOString(),
          time: 0,
          request: {
            method,
            url,
            httpVersion: 'HTTP/1.1',
            headers: headers
              .filter((h) => h.enabled !== false)
              .map((h) => ({ name: h.name, value: h.value })),
            queryString: params
              .filter((p) => p.enabled !== false)
              .map((p) => ({ name: p.name, value: p.value })),
            postData: body
              ? {
                  mimeType: 'application/json',
                  text: JSON.stringify(body),
                }
              : undefined,
            headersSize: -1,
            bodySize: body ? JSON.stringify(body).length : 0,
          },
          response: {
            status: 0,
            statusText: '',
            httpVersion: 'HTTP/1.1',
            headers: [],
            content: {
              size: 0,
              mimeType: 'application/json',
            },
            redirectURL: '',
            headersSize: -1,
            bodySize: -1,
          },
          cache: {},
          timings: {
            send: 0,
            wait: 0,
            receive: 0,
          },
        },
      ],
    },
  }
  return JSON.stringify(har, null, 2)
}

/**
 * 导出为 Postman Collection v2.1 格式
 */
export function exportCaseToPostman(caseData: Record<string, unknown>): string {
  const name = (caseData.name as string) || 'API Test Case'
  const method = (caseData.api_method as string) || 'GET'
  const url = (caseData.api_path as string) || ''
  const headers = (caseData.headers_overrides as Array<{ name: string; value: string; enabled?: boolean }>) || []
  const params = (caseData.params_overrides as Array<{ name: string; value: string; enabled?: boolean }>) || []
  const body = caseData.body_overrides as Record<string, unknown> | null

  // 解析 URL 和查询参数
  let urlObj: URL
  try {
    urlObj = new URL(url)
  } catch {
    urlObj = new URL('http://localhost' + (url.startsWith('/') ? url : '/' + url))
  }

  const query = params
    .filter((p) => p.enabled !== false)
    .map((p) => ({ key: p.name, value: p.value }))

  const postmanCollection = {
    info: {
      name,
      schema: 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    item: [
      {
        name,
        request: {
          method,
          header: headers
            .filter((h) => h.enabled !== false)
            .map((h) => ({ key: h.name, value: h.value })),
          url: {
            raw: url,
            protocol: urlObj.protocol.replace(':', ''),
            host: urlObj.hostname.split('.'),
            path: urlObj.pathname.split('/').filter(Boolean),
            query,
          },
          body: body
            ? {
                mode: 'raw',
                raw: JSON.stringify(body, null, 2),
                options: {
                  raw: {
                    language: 'json',
                  },
                },
              }
            : undefined,
        },
        response: [],
      },
    ],
  }
  return JSON.stringify(postmanCollection, null, 2)
}

/**
 * 触发浏览器下载文件
 */
export function downloadFile(content: string, filename: string, mimeType: string): void {
  try {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    msgError('导出失败，请重试')
    throw error
  }
}

/**
 * 统一的导出入口，支持多种格式
 */
export function exportCase(
  caseData: Record<string, unknown>,
  format: 'json' | 'har' | 'postman',
  filename?: string
): void {
  const caseName = (caseData.name as string) || 'api-test-case'
  const safeName = caseName.replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, '_')
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)

  try {
    msgInfo('正在导出...')

    let content: string
    let mimeType: string
    let ext: string

    switch (format) {
      case 'har':
        content = exportCaseToHar(caseData)
        mimeType = 'application/json'
        ext = 'har'
        break
      case 'postman':
        content = exportCaseToPostman(caseData)
        mimeType = 'application/json'
        ext = 'json'
        break
      case 'json':
      default:
        content = exportCaseToJson(caseData)
        mimeType = 'application/json'
        ext = 'json'
        break
    }

    const finalFilename = filename || `${safeName}_${timestamp}.${ext}`
    downloadFile(content, finalFilename, mimeType)

    msgSuccess('导出成功')
  } catch (error) {
    msgError('导出失败，请重试')
    throw error
  }
}
