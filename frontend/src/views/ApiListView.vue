<template>
  <PageLayout
    :title="$t('apis.title')"
    :subtitle="$t('apis.subtitle')"
    :loading="loading"
    :error="error"
    :empty="apiList.length === 0 && !loading && !error"
    :empty-title="emptyTitle"
    :empty-description="emptyDescription"
    :empty-illustration="'api'"
    @retry="fetchApis"
  >
    <!-- hero-extra: 新建按钮 + 统计信息 -->
    <template #hero-extra>
      <el-button type="primary" size="small" @click="goToNewApi" aria-label="新建接口"><Plus :size="14" /> {{ $t('apis.newApi') }}</el-button>      <span class="hero-stat">{{ $t('apis.totalCount', { count: total }) }}</span>
    </template>

    <!-- filter: 搜索框 + 分类 + 方法筛选 + 状态筛选 + 标签筛选 -->
    <template #filter>
      <div class="filter-bar">
        <div class="filter-left">
          <el-select
            v-model="selectedCategoryId"
            :placeholder="$t('apis.categoryTree')"
            clearable
            size="small"
            style="width: 160px"
            @change="onCategoryChange"
          >
            <el-option
              v-for="cat in flatCategories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
          <div class="filter-divider"></div>
          <div class="method-filters">
            <button
              v-for="m in methods"
              :key="m"
              class="method-chip"
              :class="{ active: selectedMethod === m }"
              role="tab"
              :aria-pressed="selectedMethod === m"
              @click="toggleMethod(m)"
            >
              {{ m }}
            </button>
          </div>
          <div class="status-filters">
            <button
              v-for="s in statuses"
              :key="s.value"
              class="status-chip"
              :class="{ active: selectedStatus === s.value }"
              role="tab"
              :aria-pressed="selectedStatus === s.value"
              @click="toggleStatus(s.value)"
            >
              {{ s.label }}
            </button>
          </div>
          <div v-if="projectTags.length > 0" class="tag-filter">
            <el-select
              v-model="selectedTag"
              :placeholder="$t('apis.tagFilter')"
              clearable
              size="small"
              style="width: 140px"
              @change="onTagFilterChange"
            >
              <el-option
                v-for="t in projectTags"
                :key="t.id"
                :label="t.name"
                :value="t.name"
              />
            </el-select>
          </div>
        </div>
        <div class="filter-right">
          <el-button
            v-if="hasActiveFilters"
            size="small"
            class="reset-btn"
            @click="resetFilters"
          >
            {{ $t('apis.reset') }}
          </el-button>
          <div class="search-box">
            <Search :size="14" class="search-icon" />
            <input
              v-model="rawSearch"
              type="text"
              :placeholder="$t('apis.searchPlaceholder')"
              class="search-input"
            />
            <button v-if="keyword" class="search-clear" @click="rawSearch = ''">×</button>
          </div>
        </div>
      </div>
    </template>

    <!-- loading: 使用 SkeletonTable -->
    <template #loading>
      <SkeletonTable :rows="5" />
    </template>

    <!-- default: 批量操作栏 + 表格 -->
    <template #default>
      <!-- 批量操作栏 -->
      <Transition name="batch-bar">
        <div v-if="canEdit && selectedIds.size > 0" class="batch-bar">
          <span class="batch-info">{{ $t('apis.selectedCount', { count: selectedIds.size }) }}</span>
          <div class="batch-actions">
            <el-button size="small" type="danger" plain @click="batchDelete" aria-label="批量删除">{{ $t('apis.batchDelete') }}</el-button>
            <el-button size="small" @click="batchMoveCategory">{{ $t('apis.batchMoveCategory') }}</el-button>
          </div>
        </div>
      </Transition>

      <!-- API 列表表格 -->
      <div class="api-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th v-if="canEdit" class="col-check"><el-checkbox :model-value="isAllSelected" @change="onSelectAll" class="row-checkbox" /></th>
              <th class="col-star"></th>
              <th class="col-method">{{ $t('apis.methodCol') }}</th>
              <th class="col-name">{{ $t('apis.nameCol') }}</th>
              <th class="col-path">{{ $t('apis.pathCol') }}</th>
              <th class="col-status">{{ $t('apis.statusCol') }}</th>
              <th class="col-time">{{ $t('apis.modifiedCol') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="api in apiList"
              :key="api.id"
              class="api-row"
              @click="goToDetail(api.id)"
            >
              <td v-if="canEdit" class="col-check" @click.stop><el-checkbox :model-value="selectedIds.has(api.id)" @change="onSelectChange(api.id)" class="row-checkbox" /></td>
              <td class="col-star" @click.stop>
                <button
                  v-if="isLoggedIn"
                  class="star-btn"
                  :class="{ starred: api.is_starred }"
                  @click="toggleStar(api)"
                  :title="api.is_starred ? $t('apis.unstar') : $t('apis.star')"
                  :aria-label="api.is_starred ? $t('apis.unstar') : $t('apis.star')"
                >
                  <Star :size="16" :fill="api.is_starred ? 'currentColor' : 'none'" />
                </button>
              </td>
              <td class="col-method">
                <span class="method-badge" :class="api.method.toLowerCase()">{{ api.method }}</span>
              </td>
              <td class="col-name">
                <span class="api-name">{{ api.name }}</span>
              </td>
              <td class="col-path">
                <code class="api-path">{{ api.path }}</code>
              </td>
              <td class="col-status">
                <span class="status-tag" :class="api.status?.toLowerCase() || 'draft'">
                  {{ statusLabel(api.status) }}
                </span>
              </td>
              <td class="col-time">
                <span class="time-text">{{ formatTime(api.updated_at) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- empty-action: 新建接口按钮 -->
    <template #empty-action>
      <el-button type="primary" size="small" @click="goToNewApi" aria-label="新建接口"><Plus :size="14" /> {{ $t('apis.newApi') }}</el-button>    </template>

    <!-- footer: 分页 -->
    <template #footer>
      <div v-if="total > pageSize" class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchApis"
          size="small"
        />
      </div>
    </template>
  </PageLayout>
</template>

<script setup lang="ts">
defineOptions({ name: 'ApiListView' })
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { useDebounce } from '@/composables/useDebounce'
import { useFilterState } from '@/composables/useFilterState'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Plus, Search, Star } from 'lucide-vue-next'
import { listApis, starApi, unstarApi, batchDeleteApis, batchMoveApis } from '@/api/apis'
import { getCategoryTree } from '@/api/categories'
import { listTags, type TagItem } from '@/api/tags'
import { useProjectStore } from '@/stores/projectStore'
import { useUserStore } from '@/stores/userStore'
import { useProjectPermission } from '@/composables/useProjectPermission'
import { useRequireLogin } from '@/composables/useRequireLogin'
import { msgError, msgSuccess } from '@/utils/message'
import type { ApiError } from '@/types/common'
import { ElMessageBox } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonTable from '@/components/SkeletonTable.vue'
import PageLayout from '@/components/common/PageLayout.vue'


const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectStore = useProjectStore()
const userStore = useUserStore()
const { canEdit, isLoggedIn, requireWrite } = useProjectPermission()
const { requireLogin } = useRequireLogin()

const projectId = computed(() => {
  const id = route.params.id
  return id ? Number(id) : (projectStore.currentProjectId || null)
})

// 分类
const categoryTree = ref<CategoryNode[]>([])
const categoryLoading = ref(false)
const selectedCategoryId = ref<number | null>(null)

// 扁平化分类列表，用于下拉选择
const flatCategories = computed(() => {
  const result: { id: number; name: string }[] = []
  function walk(nodes: CategoryNode[], prefix: string = '') {
    for (const node of nodes) {
      result.push({ id: node.id, name: prefix + node.name })
      if (node.children?.length) walk(node.children, prefix + '  ')
    }
  }
  walk(categoryTree.value)
  return result
})

interface CategoryNode {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
  api_count: number
  children: CategoryNode[]
  first_api: {
    id: number
    name: string
    method: string
    category_id: number
    case_count: number
  } | null
}

// API 列表
const apiList = ref<ApiRow[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

interface ApiRow {
  id: number
  name: string
  method: string
  path: string
  status: string
  updated_at: string
  is_starred?: boolean
}

// 筛选
const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
const statuses = computed(() => [
  { value: '', label: t('apis.allStatus') },
  { value: 'draft', label: t('apis.draft') },
  { value: 'published', label: t('apis.published') },
  { value: 'deprecated', label: t('apis.deprecated') },
])
const filterState = useFilterState({
  method: '' as string,
  status: '' as string,
  search: '' as string,
})
const selectedMethod = computed({
  get: () => filterState.value.method || null,
  set: (v: string | null) => { filterState.value.method = v || '' },
})
const selectedStatus = computed({
  get: () => filterState.value.status,
  set: (v: string) => { filterState.value.status = v },
})
const rawSearch = computed({
  get: () => filterState.value.search,
  set: (v: string) => { filterState.value.search = v },
})
const keyword = useDebounce(() => rawSearch.value, 300)
const projectTags = ref<TagItem[]>([])
const selectedTag = ref<string>('')

// 空状态文案
const hasFilter = computed(() => !!(keyword.value || selectedMethod.value || selectedStatus.value))
const emptyTitle = computed(() => hasFilter.value ? t('apis.noMatch') : t('apis.noApis'))
const emptyDescription = computed(() => hasFilter.value ? t('apis.tryAdjust') : t('apis.createFirstCategory'))

const hasActiveFilters = computed(() => {
  return !!(
    selectedCategoryId.value ||
    selectedMethod.value ||
    selectedStatus.value ||
    selectedTag.value ||
    keyword.value
  )
})

function resetFilters() {
  selectedCategoryId.value = null
  selectedMethod.value = null
  selectedStatus.value = ''
  selectedTag.value = ''
  rawSearch.value = ''
  currentPage.value = 1
  void fetchApis()
}

function toggleMethod(m: string) {
  selectedMethod.value = selectedMethod.value === m ? null : m
  currentPage.value = 1
  void fetchApis()
}

function toggleStatus(s: string) {
  selectedStatus.value = selectedStatus.value === s ? '' : s
  currentPage.value = 1
  void fetchApis()
}

watch(keyword, () => {
  currentPage.value = 1
  void fetchApis()
})

function onTagFilterChange() {
  currentPage.value = 1
  void fetchApis()
}

function onCategoryChange() {
  currentPage.value = 1
  void fetchApis()
}

async function fetchCategories() {
  if (!projectId.value) return
  categoryLoading.value = true
  try {
    const res = await getCategoryTree(projectId.value)
    categoryTree.value = res.data?.tree ?? []
  } catch {
    categoryTree.value = []
  } finally {
    categoryLoading.value = false
  }
}

async function fetchTags() {
  if (!projectId.value) return
  try {
    const res = await listTags(projectId.value)
    projectTags.value = res.data || []
  } catch {
    projectTags.value = []
  }
}

async function fetchApis() {
  if (!projectId.value) return
  loading.value = true
  error.value = null
  try {
    const params: Record<string, string | number> = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (selectedCategoryId.value) {
      params.category_id = selectedCategoryId.value
    }
    if (selectedMethod.value) {
      params.method = selectedMethod.value
    }
    if (selectedStatus.value) {
      params.status = selectedStatus.value
    }
    if (keyword.value) {
      params.keyword = keyword.value
    }
    if (selectedTag.value) {
      params.tag = selectedTag.value
    }
    const res = await listApis(projectId.value, params)
    apiList.value = res.data?.items ?? []
    total.value = res.data?.total ?? 0
  } catch (e: unknown) {
    const err = e as ApiError
    // 401 由 request.ts 拦截器统一处理（refresh/forceLogout），此处不再静默吞错，
    // 统一走错误状态展示，让用户感知数据加载失败
    error.value = err?.response?.data?.message || err?.message || t('apis.networkFailed')
    apiList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function goToDetail(apiId: number) {
  void router.push(`/projects/${projectId.value}/apis/detail/${apiId}`)
}

// ── 批量选择 ──
const selectedIds = ref<Set<number>>(new Set())

const isAllSelected = computed(() => {
  return apiList.value.length > 0 && apiList.value.every(api => selectedIds.value.has(api.id))
})

function onSelectAll(val: boolean | string) {
  const newSet = new Set(selectedIds.value)
  if (val) {
    for (const api of apiList.value) {
      newSet.add(api.id)
    }
  } else {
    // 取消全选时仅移除当前页接口 ID，保留其他页选择
    apiList.value.forEach(api => newSet.delete(api.id))
  }
  selectedIds.value = newSet
}

function onSelectChange(apiId: number) {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(apiId)) {
    newSet.delete(apiId)
  } else {
    newSet.add(apiId)
  }
  selectedIds.value = newSet
}

async function batchDelete() {
  if (!projectId.value || selectedIds.value.size === 0) return
  if (!(await requireLogin(t('apis.batchDelete')))) return
  try {
    await ElMessageBox.confirm(
      t('apis.batchDeleteConfirm', { count: selectedIds.value.size }),
      t('apis.batchDelete'),
      { confirmButtonText: t('apis.confirm'), cancelButtonText: t('apis.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await batchDeleteApis(projectId.value, [...selectedIds.value])
    msgSuccess(t('apis.batchDeleteSuccess'))
    selectedIds.value.clear()
    void fetchApis()
  } catch {
    msgError(t('apis.operationFailed'))
  }
}

async function batchMoveCategory() {
  if (!projectId.value || selectedIds.value.size === 0) return
  if (!(await requireLogin(t('apis.batchMoveCategory')))) return
  let categoryId: string | number | null = null
  try {
    const result = await ElMessageBox.prompt(
      t('apis.selectTargetCategory'),
      t('apis.batchMoveCategory'),
      {
        confirmButtonText: t('apis.confirm'),
        cancelButtonText: t('apis.cancel'),
        inputPlaceholder: t('apis.categoryIdPlaceholder'),
        inputPattern: /^\d+$/,
        inputErrorMessage: t('apis.invalidCategoryId'),
      }
    )
    categoryId = result.value
  } catch {
    return // 用户取消
  }
  try {
    await batchMoveApis(projectId.value, { api_ids: [...selectedIds.value], target_category_id: Number(categoryId) })
    msgSuccess(t('apis.batchMoveSuccess'))
    selectedIds.value.clear()
    void fetchApis()
  } catch {
    msgError(t('apis.operationFailed'))
  }
}

async function toggleStar(api: ApiRow) {
  if (!projectId.value) return
  if (!(await requireLogin(t('apis.star')))) return
  const oldStarred = api.is_starred
  api.is_starred = !oldStarred  // optimistic update
  try {
    if (oldStarred) {
      await unstarApi(projectId.value, api.id)
    } else {
      await starApi(projectId.value, api.id)
    }
  } catch {
    api.is_starred = oldStarred  // rollback
    msgError(t('apis.operationFailed'))
  }
}

async function goToNewApi() {
  if (!(await requireWrite(t('apis.newApi')))) return
  void router.push(`/projects/${projectId.value}/apis/detail/new`)
}

function statusLabel(s: string): string {
  const key = s?.toLowerCase() || 'draft'
  const map: Record<string, string> = {
    draft: t('apis.draft'),
    published: t('apis.published'),
    deprecated: t('apis.deprecated'),
  }
  return map[key] ?? s
}

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '-'
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('apis.justNow')
  if (mins < 60) return `${mins} ${t('apis.minutesAgo')}`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ${t('apis.hoursAgo')}`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} ${t('apis.daysAgo')}`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

watch(() => projectId.value, (id) => {
  if (id) {
    void fetchCategories()
    void fetchApis()
    void fetchTags()
  }
})

onMounted(() => {
  if (projectId.value) {
    void fetchCategories()
    void fetchApis()
    void fetchTags()
  }
})

onBeforeUnmount(() => {
  selectedIds.value = new Set()
})
</script>

<style scoped>
/* ── hero 区域 ── */
.hero-stat {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  white-space: nowrap;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  gap: var(--space-3);
  flex-shrink: 0;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  flex: 1;
  min-width: 0;
}

.filter-divider {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
  flex-shrink: 0;
  align-self: center;
}

.method-filters,
.status-filters {
  display: flex;
  gap: var(--space-1);
  flex-shrink: 0;
}

.method-chip {
  padding: var(--space-0-5) var(--space-2-5);
  height: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.method-chip:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.method-chip:active {
  transform: scale(0.96);
  transition-duration: 80ms;
}

.method-chip:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 1px;
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
}

.method-chip.active {
  background: var(--color-primary-alpha-12);
  color: var(--primary-600);
  border-color: var(--primary-300);
}

.status-chip {
  padding: var(--space-0-5) var(--space-2-5);
  height: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.status-chip:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
}

.status-chip:active {
  transform: scale(0.96);
  transition-duration: 80ms;
}

.status-chip:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 1px;
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
}

.status-chip.active {
  background: var(--color-primary-alpha-12);
  color: var(--primary-600);
  border-color: var(--primary-300);
  font-weight: var(--weight-medium);
}

.filter-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.reset-btn {
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
  transition: color var(--duration-fast) var(--ease-smooth);
}

.search-input {
  width: 220px;
  height: 32px;
  padding: 0 var(--space-8) 0 var(--space-8);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--surface-input);
  color: var(--text-primary);
  font-size: var(--text-sm);
  outline: none;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.search-input:hover {
  border-color: var(--border-strong);
}

.search-input:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
  background: linear-gradient(180deg, var(--surface-input) 0%, var(--color-primary-alpha-04) 100%);
}

.search-box:focus-within .search-icon {
  color: var(--primary-500);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-clear {
  position: absolute;
  right: 4px;
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-lg2);
  padding: var(--space-1) var(--space-1-5);
  line-height: 1;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-smooth);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.search-clear:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.search-clear:active {
  transform: scale(0.92);
  transition-duration: 80ms;
}

.search-clear:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 1px;
  box-shadow: 0 0 0 3px var(--color-primary-alpha-12);
}

/* ── 表格 ── */
.api-table-wrap {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}

.api-row {
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

.api-row:hover {
  background-color: var(--surface-hover);
}

.api-row:active {
  background-color: var(--surface-active);
}

.data-table .col-check .el-checkbox {
  vertical-align: middle;
}

/* ── 批量操作栏 ── */
.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  margin-bottom: var(--space-3);
  box-shadow: var(--shadow-sm);
}

.batch-info {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}

.batch-actions {
  display: flex;
  gap: var(--space-2);
}

.batch-bar-enter-active,
.batch-bar-leave-active {
  transition: all var(--duration-fast) var(--ease-smooth);
}

.batch-bar-enter-from,
.batch-bar-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  margin-bottom: 0;
  padding-top: 0;
  padding-bottom: 0;
  max-height: 0;
  border-width: 0;
}

.col-method { width: 80px; }
.col-name { width: 200px; }
.col-path { width: auto; }
.col-status { width: 100px; }
.col-time { width: 140px; }

/* 收藏星标 */
.col-check {
  width: 48px;
  text-align: center;
}
/* 限制复选框点击区域，避免误触 */
.col-check :deep(.row-checkbox) {
  margin-right: 0;
}
.col-check :deep(.row-checkbox .el-checkbox__label) {
  display: none;
}
.col-check :deep(.row-checkbox .el-checkbox__input) {
  line-height: 1;
}

.col-star {
  width: 48px;
  text-align: center;
}

.star-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.star-btn:hover {
  color: var(--color-warning-500);
  background: var(--color-warning-alpha-10);
  transform: scale(1.1);
}

.star-btn:active {
  transform: scale(0.95);
  background: var(--color-warning-alpha-16);
}

.star-btn.starred {
  color: var(--color-warning-500);
}

.star-btn.starred:hover {
  color: var(--color-warning-600);
}

.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  min-width: 52px;
}

.method-badge.get {
  background: var(--method-get-bg);
  color: var(--method-get-text);
}

.method-badge.post {
  background: var(--method-post-bg);
  color: var(--method-post-text);
}

.method-badge.put {
  background: var(--method-put-bg);
  color: var(--method-put-text);
}

.method-badge.delete {
  background: var(--method-delete-bg);
  color: var(--method-delete-text);
}

.method-badge.patch {
  background: var(--method-patch-bg);
  color: var(--method-patch-text);
}

.method-badge.head {
  background: var(--method-head-bg);
  color: var(--method-head-text);
}

.method-badge.options {
  background: var(--method-options-bg);
  color: var(--method-options-text);
}

.api-name {
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.api-path {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  background: var(--surface-code);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  background: var(--color-neutral-alpha-06);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}

.status-tag.draft {
  background: var(--warning-bg);
  color: var(--warning-text);
  border: 1px solid var(--warning-border);
}

.status-tag.published {
  background: var(--success-bg);
  color: var(--success-text);
  border: 1px solid var(--success-border);
}

.status-tag.deprecated {
  background: var(--color-neutral-alpha-06);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

.time-text {
  color: var(--text-muted);
  font-size: var(--text-xs);
}

/* ── 分页 ── */
.pagination-bar {
  display: flex;
  justify-content: center;
  padding: var(--space-4);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

/* ── 暗色模式 ── */
html.dark .api-table thead {
  background: var(--surface-page);
}

html.dark .search-input {
  background: var(--surface-input);
}

html.dark .method-chip.active,
html.dark .status-chip.active {
  color: var(--primary-400);
  background: var(--color-primary-alpha-16);
  border-color: var(--primary-500);
}

/* ===== 窄屏响应式 ===== */
@media (max-width: 767px) {
  .filter-bar {
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .filter-left {
    flex-wrap: wrap;
    gap: var(--space-2);
    width: 100%;
  }

  .filter-right {
    width: 100%;
    justify-content: flex-end;
  }

  .search-box {
    flex: 1;
    min-width: 0;
  }

  .reset-btn {
    flex-shrink: 0;
  }

  /* 表格隐藏次要列 */
  .col-time {
    display: none;
  }

  .col-status {
    display: none;
  }
}
</style>
