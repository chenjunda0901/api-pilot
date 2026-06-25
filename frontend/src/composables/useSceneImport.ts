// frontend/src/composables/useSceneImport.ts
import { ref, computed, type Ref } from 'vue'
import request from '../api/request'
import { getCase } from '../api/cases'
import { msgSuccess, msgError } from '../utils/message'
import { logger } from '../utils/logger'

function safeParseJson(str: string, fallback: unknown = null): unknown {
  if (!str) return fallback
  try { return JSON.parse(str) } catch { return fallback }
}

interface ImportApiItem {
  id: number
  name: string
  path: string
  method: string
  headers: unknown[]
  params: unknown[]
  body: { content?: string } | null
  assertions: unknown[]
}

interface ImportCaseItem {
  id: number
  name: string
  method: string
  path: string
  priority: string
  api_id: number
  request_body: string
  headers: string
  query_params: string
  assertions: string
  extract_vars: string
}

interface ImportTreeNode {
  id: number
  type: 'category' | 'api' | 'case'
  label: string
  name?: string
  method?: string
  path?: string
  priority?: string
  api_id?: number
  children?: ImportTreeNode[]
  _raw?: ImportApiNode | ImportCaseNode
}

interface ImportApiNode {
  id: number
  name: string
  method: string
  path: string
  cases?: ImportCaseNode[]
}

interface ImportCaseNode {
  id: number
  name: string
  priority: string
  api_id: number
}

interface ImportCategoryNode {
  id: number
  name: string
  type?: string
  children?: (ImportCategoryNode | ImportApiNode | ImportCaseNode)[]
}

interface ImportItemValue {
  id: number
  name?: string
  method?: string
  path?: string
  headers?: string
  request_body?: string
  query_params?: string
  assertions?: string
  extract_vars?: string
  _type: string
  [key: string]: unknown
}

export interface SceneImportOptions {
  projectId: number
  steps: Ref<Record<string, unknown>[]>
}

interface CheckedNode {
  type: string
  _raw: ImportApiNode | ImportCaseNode
}

export function useSceneImport(options: SceneImportOptions) {
  const { projectId, steps } = options

  const showImportDialog = ref(false)
  const importSearch = ref('')
  const importApis = ref<ImportApiItem[]>([])
  const importCases = ref<ImportCaseItem[]>([])
  const importSelected = ref(new Set<string>())
  const importItems = ref(new Map<string, ImportItemValue>())
  const importCategories = ref<ImportTreeNode[]>([])
  const importLoading = ref(false)
  const importTreeRef = ref<unknown>(null)

  const importTreeData = computed(() => {
    const cats = importCategories.value
    if (!cats || cats.length === 0) return []

    function walk(nodes: ImportTreeNode[]): ImportTreeNode[] {
      return nodes.map((n: ImportTreeNode) => {
        const item: ImportTreeNode = { id: n.id, type: n.type, label: n.name || '未命名' }
        if (n.type === 'api') {
          item.method = n.method
          item.path = n.path
          item._raw = n as ImportApiNode
          if (n.children?.length) {
            item.children = walk(n.children)
          }
        } else if (n.type === 'case') {
          item.priority = n.priority
          item.api_id = n.api_id
          item._raw = n as ImportCaseNode
        } else {
          item.children = walk(n.children || [])
        }
        return item
      })
    }

    let tree = walk(cats)
    const q = importSearch.value?.toLowerCase().trim()
    if (q) {
      function filterInTree(nodes: ImportTreeNode[]): ImportTreeNode[] {
        const result: ImportTreeNode[] = []
        for (const node of nodes) {
          if (node.label?.toLowerCase().includes(q)) {
            result.push(node)
          } else if (node.children?.length) {
            const filtered = filterInTree(node.children)
            if (filtered.length) {
              result.push({ ...node, children: filtered })
            }
          }
        }
        return result
      }
      tree = filterInTree(tree)
    }
    return tree
  })

  const filteredImportApis = computed(() => {
    if (!importSearch.value) return importApis.value
    const q = importSearch.value.toLowerCase()
    return importApis.value.filter(
      (a: ImportApiItem) =>
        (a.name && a.name.toLowerCase().includes(q)) ||
        (a.path && a.path.toLowerCase().includes(q))
    )
  })

  const filteredImportCases = computed(() => {
    if (!importSearch.value) return importCases.value
    const q = importSearch.value.toLowerCase()
    return importCases.value.filter((c: ImportCaseItem) => c.name && c.name.toLowerCase().includes(q))
  })

  function openImport() {
    importSearch.value = ''
    importSelected.value.clear()
    importItems.value.clear()
    showImportDialog.value = true
    void loadImportTree()
  }

  async function loadImportApis() {
    try {
      const items: ImportApiItem[] = []
      let page = 1
      const pageSize = 100
      while (true) {
        const res: { data: { items: ImportApiItem[]; total: number } } = await request.get(`/projects/${projectId}/apis`, {
          params: { page, page_size: pageSize },
        })
        const batch = res.data.items || []
        if (batch.length === 0) break
        items.push(...batch)
        if (items.length >= (res.data.total || 0) || batch.length < pageSize) break
        page++
      }
      importApis.value = items
    } catch (err) {
      logger.error('[useSceneImport] loadImportApis failed:', err)
      msgError('加载接口列表失败')
      /* 由 request 拦截器处理 */
    }
  }

  async function loadImportCases() {
    try {
      const res: { data: { items: ImportCaseItem[] } } = await request.get(`/projects/${projectId}/cases`, {
        params: { page_size: 100 },
      })
      importCases.value = res.data.items || []
    } catch (err) {
      logger.error('[useSceneImport] loadImportCases failed:', err)
      msgError('加载用例列表失败')
      /* 由 request 拦截器处理 */
    }
  }

  function toggleImport(type: string, item: ImportApiItem | ImportCaseItem) {
    const key = `${type}-${item.id}`
    if (importSelected.value.has(key)) {
      importSelected.value.delete(key)
      importItems.value.delete(key)
    } else {
      importSelected.value.add(key)
      importItems.value.set(key, { ...item, _type: type } as unknown as ImportItemValue)
    }
  }

  async function loadImportTree() {
    importLoading.value = true
    try {
      const res: { data: { categories: ImportCategoryNode[] } } = await request.get('/projects/' + projectId + '/import-tree')
      importCategories.value = (res.data?.categories || []) as unknown as ImportTreeNode[]
    } catch (err) {
      logger.error('[useSceneImport] loadImportTree failed:', err)
      msgError('加载导入树失败')
      importCategories.value = []
    } finally {
      importLoading.value = false
    }
  }

  function onTreeCheck(_data: unknown, { checkedNodes }: { checkedNodes: CheckedNode[] }) {
    importSelected.value.clear()
    importItems.value.clear()
    checkedNodes.forEach((node: CheckedNode) => {
      if (node.type === 'api') {
        const raw = node._raw as ImportApiNode
        const key = 'api-' + raw.id
        importSelected.value.add(key)
        importItems.value.set(key, { ...raw, _type: 'api' })
      } else if (node.type === 'case') {
        const raw = node._raw as ImportCaseNode
        const key = 'case-' + raw.id
        importSelected.value.add(key)
        importItems.value.set(key, { ...raw, _type: 'case' })
      }
    })
  }

  function filterNode(value: string, data: ImportTreeNode) {
    if (!value) return true
    const q = value.toLowerCase()
    if (data.type === 'category') return true
    if (data.type === 'api') {
      return (
        (data.label && data.label.toLowerCase().includes(q)) ||
        (data.path && data.path.toLowerCase().includes(q))
      )
    }
    return data.label && data.label.toLowerCase().includes(q)
  }

  async function doImport() {
    const pending: Promise<void>[] = []
    const toArray = (v: unknown): unknown[] =>
      Array.isArray(v) ? v : (safeParseJson(typeof v === 'string' ? v : '', []) as unknown[])

    importItems.value.forEach((item, key) => {
      const [type] = key.split('-')

      if (type === 'api') {
        const apiId = String(item.id).replace(/^api-/, '')
        const p = request.get(`/projects/${projectId}/apis/${apiId}`).then((res: { data: Record<string, unknown> }) => {
          const d = res.data
          steps.value.push({
            _key: `imported-${key}`,
            method: d.method || 'GET',
            label: d.name || '未命名接口',
            api_id: d.id,
            test_case_id: null,
            enabled: true,
            node_type: 'ref_api',
            path: d.path || '',
            request_body: d.body?.content || d.request_body || '',
            headers: Array.isArray(d.headers) ? d.headers : [],
            query_params: Array.isArray(d.params) ? d.params : [],
            assertions: Array.isArray(d.assertions) ? d.assertions : [],
            extract_vars: [],
            assertion_count: Array.isArray(d.assertions) ? d.assertions.length : 0,
            extract_count: 0,
          })
        })
        pending.push(p)
      } else {
        const caseId = item.id as number
        const p = getCase(projectId, caseId).then((res) => {
          const d = (res.data ?? {}) as {
            name?: string
            method?: string
            path?: string
            request_body?: string
            headers?: string | unknown[]
            query_params?: string | unknown[]
            assertions?: unknown[] | string
            extract_vars?: unknown[] | string
          }
          const assertions = toArray(d.assertions ?? item.assertions)
          const extractVars = toArray(d.extract_vars ?? item.extract_vars)
          const headers = toArray(d.headers ?? item.headers)
          const queryParams = toArray(d.query_params ?? item.query_params)
          steps.value.push({
            _key: `imported-${key}`,
            method: d.method || item.method || 'GET',
            label: d.name || item.name || '未命名用例',
            api_id: null,
            test_case_id: caseId,
            enabled: true,
            node_type: 'ref_case',
            path: d.path || item.path || '',
            request_body: d.request_body || item.request_body || '',
            headers,
            query_params: queryParams,
            assertions,
            extract_vars: extractVars,
            assertion_count: assertions.length,
            extract_count: extractVars.length,
          })
        })
        pending.push(p)
      }
    })

    const results = await Promise.allSettled(pending)
    const failedCount = results.filter(r => r.status === 'rejected').length
    const importedCount = importItems.value.size - failedCount
    showImportDialog.value = false
    importSelected.value.clear()
    importItems.value.clear()
    if (failedCount > 0) {
      msgError(`导入完成，${failedCount} 项导入失败`)
    } else {
      msgSuccess(`已导入 ${importedCount} 个步骤`)
    }
  }

  return {
    showImportDialog,
    importSearch,
    importApis,
    importCases,
    importSelected,
    importItems,
    importCategories,
    importLoading,
    importTreeRef,
    importTreeData,
    filteredImportApis,
    filteredImportCases,
    openImport,
    loadImportApis,
    loadImportCases,
    toggleImport,
    loadImportTree,
    onTreeCheck,
    filterNode,
    doImport,
  }
}

// ── 文件格式检测工具函数 ──

/** 基于内容检测 Apifox 格式 */
export function detectApifoxByContent(content: string): boolean {
  try {
    const data = JSON.parse(content)
    if (data.apifoxProject) return true
    if (data.$schema?.app === 'apifox' || data.$schema?.type === 'project') return true
    if (data.apiCollection || data.requestCollection) return true
    return false
  } catch {
    return false
  }
}

/** 基于内容检测 Postman 格式 */
export function detectPostmanByContent(content: string): boolean {
  try {
    const data = JSON.parse(content)
    if (data.info?.schema?.includes('collection')) return true // postman v2.1
    if (data.item && Array.isArray(data.item)) return true
    return false
  } catch {
    return false
  }
}

/** 基于内容检测 OpenAPI / Swagger 格式 */
export function detectOpenApiByContent(content: string): boolean {
  try {
    const data = JSON.parse(content)
    if (data.openapi && typeof data.openapi === 'string') return true // OpenAPI 3.x
    if (data.swagger && typeof data.swagger === 'string') return true // Swagger 2.x
    if (data.paths && typeof data.paths === 'object') return true
    return false
  } catch {
    return false
  }
}

/** 基于内容检测 HAR 格式 */
export function detectHarByContent(content: string): boolean {
  try {
    const data = JSON.parse(content)
    if (data.log?.entries && Array.isArray(data.log.entries)) return true
    if (data.log?.version && data.log?.creator) return true
    return false
  } catch {
    return false
  }
}

/** 基于内容检测 Bruno 格式 */
export function detectBrunoByContent(content: string): boolean {
  try {
    const data = JSON.parse(content)
    if (data.bruno && typeof data.bruno === 'object') return true
    if (data.items && Array.isArray(data.items) && data.name && data.type === 'collection') return true
    return false
  } catch {
    return false
  }
}

/** 综合格式检测：基于文件内容推断格式，返回格式标识符或 null */
export function detectFormatByContent(content: string): string | null {
  if (detectApifoxByContent(content)) return 'apifox_project'
  if (detectPostmanByContent(content)) return 'postman'
  if (detectOpenApiByContent(content)) return 'openapi'
  if (detectHarByContent(content)) return 'har'
  if (detectBrunoByContent(content)) return 'bruno'
  return null
}
