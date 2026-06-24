// frontend/src/stores/apiStore.ts
import { defineStore } from "pinia"
import { ref } from "vue"
import { getCategoryTree } from "@/api/categories"
import { listApis, listApiCases } from "@/api/apis"
import { logger } from "@/utils/logger"

const CACHE_TTL = 30_000 // 缓存有效期 30 秒
const EXPANDED_STORAGE_KEY = "api_pilot_expanded_categories"

function loadExpandedCategories(projectId: number | null): number[] {
  if (projectId === null) return []
  try {
    const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw) as Record<number, number[]>
      return data[projectId] || []
    }
  } catch {
    /* ignore */
  }
  return []
}

function saveExpandedCategories(projectId: number | null, ids: number[]) {
  if (projectId === null) return
  try {
    const raw = localStorage.getItem(EXPANDED_STORAGE_KEY)
    const data: Record<number, number[]> = raw ? JSON.parse(raw) : {}
    data[projectId] = ids
    localStorage.setItem(EXPANDED_STORAGE_KEY, JSON.stringify(data))
  } catch {
    /* ignore */
  }
}

export interface CategoryNode {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
  api_count: number
  children: CategoryNode[]
}

export interface ApiItem {
  id: number
  name: string
  method: string
  path: string
  category_id: number | null
  description: string
  headers: unknown[]
  params: unknown[]
  body: unknown
  auth_type: string
  case_count?: number
}

export interface CaseItem {
  id: number
  name: string
  api_id: number
  priority: string
  status: string
  description: string
  tags: string
  assertions: unknown[]
  extract_vars: unknown[]
  last_run_status?: string
}

export const useApiStore = defineStore("api", () => {
  const categories = ref<CategoryNode[]>([])
  const apisByCategory = ref<Record<number, ApiItem[]>>({})
  const casesByApi = ref<Record<number, CaseItem[]>>({})
  const firstApi = ref<{ id: number; name: string; method: string; category_id: number } | null>(
    null
  )
  const expandedCategories = ref<number[]>([])
  const expandedApis = ref<number[]>([])
  const selectedCategoryId = ref<number | null>(null)
  const selectedApiId = ref<number | null>(null)
  const loadingCategories = ref(false)
  const loadingApis = ref(false)
  const loadingCases = ref(false)

  // 当前缓存所属项目 ID，切换项目时强制失效所有缓存
  const currentProjectId = ref<number | null>(null)

  // 缓存时间戳（按 projectId 复合 key，防止切换项目读脏缓存）
  const categoriesCachedAt = ref<Record<number, number>>({})
  const apisCachedAt = ref<Record<string, number>>({})
  const casesCachedAt = ref<Record<string, number>>({})

  function isCacheFresh(timestamp: number): boolean {
    return timestamp > 0 && Date.now() - timestamp < CACHE_TTL
  }

  /** 切换项目时强制清空缓存，避免项目间数据泄漏 */
  function ensureProject(projectId: number) {
    if (currentProjectId.value !== projectId) {
      clearCache()
      currentProjectId.value = projectId
      // 加载该项目的分类展开状态
      expandedCategories.value = loadExpandedCategories(projectId)
    }
  }

  async function fetchCategories(projectId: number) {
    ensureProject(projectId)
    if (isCacheFresh(categoriesCachedAt.value[projectId]) && categories.value.length > 0) {
      return
    }
    loadingCategories.value = true
    try {
      const res = await getCategoryTree(projectId)
      const payload = res.data
      categories.value = Array.isArray(payload) ? payload : payload?.tree || []
      firstApi.value = payload?.first_api || null
      categoriesCachedAt.value[projectId] = Date.now()
    } catch (error) {
      logger.warn('[apiStore] fetchCategories failed:', error)
      categories.value = []
      firstApi.value = null
    } finally {
      loadingCategories.value = false
    }
  }

  async function fetchApis(projectId: number, categoryId: number) {
    ensureProject(projectId)
    const cacheKey = `${projectId}_${categoryId}`
    if (isCacheFresh(apisCachedAt.value[cacheKey])) {
      return // 缓存未过期
    }
    loadingApis.value = true
    try {
      const res = await listApis(projectId, { category_id: categoryId, page_size: 100 })
      apisByCategory.value[categoryId] = res.data.items || []
      apisCachedAt.value[cacheKey] = Date.now()
    } catch (err) {
      logger.error('[apiStore] fetchApis failed:', err)
      apisByCategory.value[categoryId] = []
    } finally {
      loadingApis.value = false
    }
  }

  async function fetchCases(projectId: number, apiId: number) {
    ensureProject(projectId)
    const cacheKey = `${projectId}_${apiId}`
    if (isCacheFresh(casesCachedAt.value[cacheKey])) {
      return // 缓存未过期
    }
    loadingCases.value = true
    try {
      const res = await listApiCases(projectId, apiId, { page_size: 9999 })
      casesByApi.value[apiId] = res.data.items || []
      casesCachedAt.value[cacheKey] = Date.now()
    } catch (err) {
      logger.error('[apiStore] fetchCases failed:', err)
      casesByApi.value[apiId] = []
    } finally {
      loadingCases.value = false
    }
  }

  function toggleCategory(id: number) {
    if (expandedCategories.value.includes(id)) {
      expandedCategories.value = expandedCategories.value.filter((v) => v !== id)
    } else {
      expandedCategories.value.push(id)
    }
    // 保存到 localStorage
    saveExpandedCategories(currentProjectId.value, expandedCategories.value)
  }

  function toggleApi(id: number) {
    if (expandedApis.value.includes(id)) {
      expandedApis.value = expandedApis.value.filter((v) => v !== id)
    } else {
      expandedApis.value.push(id)
    }
  }

  function clearCache() {
    apisByCategory.value = {}
    casesByApi.value = {}
    expandedCategories.value = []
    expandedApis.value = []
    categoriesCachedAt.value = {}
    apisCachedAt.value = {}
    casesCachedAt.value = {}
    // 切换项目时清除目录树和 firstApi
    categories.value = []
    firstApi.value = null
    selectedCategoryId.value = null
    selectedApiId.value = null
    currentProjectId.value = null
  }

  function resetState() {
    categories.value = []
    firstApi.value = null
    apisByCategory.value = {}
    casesByApi.value = {}
    expandedCategories.value = []
    expandedApis.value = []
    selectedCategoryId.value = null
    selectedApiId.value = null
    loadingCategories.value = false
    loadingApis.value = false
    loadingCases.value = false
    currentProjectId.value = null
    categoriesCachedAt.value = {}
    apisCachedAt.value = {}
    casesCachedAt.value = {}
  }

  /** 主动失效特定接口目录或接口的缓存（增删改后调用） */
  function invalidateCategoryCache(categoryId?: number) {
    if (categoryId !== undefined) {
      delete apisByCategory.value[categoryId]
      if (currentProjectId.value !== null) {
        apisCachedAt.value[`${currentProjectId.value}_${categoryId}`] = 0
      }
    } else {
      // 未指定目录时，失效所有 API 缓存但保留分类树缓存
      apisByCategory.value = {}
      apisCachedAt.value = {}
    }
  }

  /** 增量添加新接口到目录（不刷新树） */
  function addApiToCategory(categoryId: number, api: ApiItem) {
    const list = apisByCategory.value[categoryId] || []
    apisByCategory.value = { ...apisByCategory.value, [categoryId]: [...list, api] }
    // 更新目录的 api_count
    const cat = categories.value.find((c) => c.id === categoryId)
    if (cat) cat.api_count = (cat.api_count || 0) + 1
  }

  function invalidateApiCache(apiId: number) {
    if (currentProjectId.value !== null) {
      casesCachedAt.value[`${currentProjectId.value}_${apiId}`] = 0
    }
  }

  return {
    categories,
    firstApi,
    apisByCategory,
    casesByApi,
    expandedCategories,
    expandedApis,
    selectedCategoryId,
    selectedApiId,
    loadingCategories,
    loadingApis,
    loadingCases,
    categoriesCachedAt,
    apisCachedAt,
    casesCachedAt,
    fetchCategories,
    fetchApis,
    fetchCases,
    toggleCategory,
    toggleApi,
    clearCache,
    resetState,
    invalidateCategoryCache,
    invalidateApiCache,
    addApiToCategory,
  }
})
