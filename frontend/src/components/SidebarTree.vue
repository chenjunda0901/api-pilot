<template>
  <aside ref="treeEl" class="sidebar-tree sidebar-tree-panel">
    <!-- 批量选择工具栏 -->
    <div v-if="selectedCount > 0" class="batch-toolbar">
      <span class="batch-count">{{ selectedCount }} 项已选</span>
      <el-button size="small" type="danger" @click="batchDelete">
        <Trash2 :size="12" /> 删除
      </el-button>
      <el-button size="small" @click="showMoveDialog = true">
        <FolderInput :size="12" /> 移动
      </el-button>
      <el-button size="small" text @click="clearSelection">
        取消
      </el-button>
    </div>
    <div class="tree-search">
      <el-input v-model="keyword" placeholder="搜索接口..." aria-label="搜索接口" size="small" clearable class="tree-search-input">
        <template #append>
          <el-dropdown trigger="click" @command="handleToolbarCommand">
            <el-button :icon="Plus" size="small" aria-label="新建接口" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="new-api">
                  <span style="display:flex;align-items:center;gap:4px"><Plus :size="14" /> 新建接口</span>
                </el-dropdown-item>
                <el-dropdown-item command="new-category">
                  <span style="display:flex;align-items:center;gap:4px"><FolderPlus :size="14" /> 新建接口目录</span>
                </el-dropdown-item>
                <el-dropdown-item command="import" divided>
                  <span style="display:flex;align-items:center;gap:4px"><Download :size="14" /> 导入接口</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-input>
    </div>
    <div class="tree-divider"></div>
    <div class="tree-body" ref="scrollContainer">
      <template v-if="apiStore.loadingCategories">
        <div v-for="i in 5" :key="i" class="tree-skeleton" />
      </template>
      <template v-else-if="apiStore.categories.length === 0">
        <EmptyState :icon="FolderOpen" title="暂无接口目录" description="创建接口目录或导入接口"
          :actions="[{ text: '创建接口目录', type: 'primary', onClick: () => startInlineCreate() }]" />
      </template>
      <div v-else-if="enabled" :style="totalHeightStyle">
        <div :style="offsetStyle">
          <template v-for="item in visibleItems" :key="item.key">
            <div
              v-if="item.type === 'category'"
              class="flat-cat-row"
              :class="{ 'is-expanded': isCatExpanded(item.category!.id) }"
              :style="{ paddingLeft: `${item.depth * 16 + 12}px` }"
              tabindex="0"
              role="treeitem"
              :aria-expanded="isCatExpanded(item.category!.id)"
              @click="toggleFlatCat(item.category!)"
              @keydown.enter="toggleFlatCat(item.category!)"
              @keydown.space.prevent="toggleFlatCat(item.category!)"
            >
              <ChevronRight
                v-if="!isCatEmpty(item.category!)"
                :size="14"
                class="flat-chevron"
                :class="{ expanded: isCatExpanded(item.category!.id) }"
              />
              <Folder :size="16" class="flat-cat-icon" />
              <span class="flat-cat-name" :title="item.category!.name">{{ item.category!.name }}</span>
              <span class="flat-cat-count">{{ item.category!.api_count || 0 }}</span>
            </div>
            <div v-else class="flat-api-wrapper" :style="{ paddingLeft: `${item.depth * 16}px` }">
              <ApiNode :api="item.api!" :project-id="projectId" />
            </div>
          </template>
        </div>
      </div>
      <template v-else>
        <CategoryNode
          v-for="cat in filteredCategories"
          :key="cat.id"
          :category="cat"
          :depth="0"
          :project-id="projectId"
        />
      </template>
      <!-- 行内创建目录（追加到列表最后） -->
      <div v-if="inlineCreating" class="inline-create-node">
        <FolderPlus :size="14" style="color: var(--primary-500); flex-shrink: 0;" />
        <input
          ref="inlineInputRef"
          v-model="inlineInputValue"
          class="inline-create-input"
          placeholder="输入目录名称"
          aria-label="目录名称"
          @keydown.enter="confirmInlineCreate"
          @keydown.escape="cancelInlineCreate"
          @click.stop
        />
        <button class="inline-confirm-btn" :disabled="!inlineInputValue.trim()" aria-label="确认创建" @click="confirmInlineCreate">
          <Check :size="12" />
        </button>
        <button class="inline-cancel-btn" aria-label="取消创建" @click="cancelInlineCreate">
          <X :size="12" />
        </button>
      </div>
    </div>
    <!-- 拖拽调整宽度手柄 -->
  <div
    class="tree-resize-handle"
    @mousedown.prevent="startResize"
  ></div>
  </aside>
  <ImportWizard
    v-model="showImportDialog"
    :project-id="projectId"
    :default-category-id="importCategoryId"
    @imported="handleImportSuccess"
  />
  <!-- 移动到目录弹窗 -->
  <el-dialog v-model="showMoveDialog" title="移动到目录" width="320px">
    <div class="move-tree">
      <div
        v-for="cat in apiStore.categories"
        :key="cat.id"
        class="move-cat-item"
        :class="{ selected: moveTargetCategoryId === cat.id }"
        @click="moveTargetCategoryId = cat.id"
      >
        <Folder :size="14" />
        <span>{{ cat.name }}</span>
      </div>
    </div>
    <template #footer>
      <el-button @click="showMoveDialog = false">取消</el-button>
      <el-button type="primary" :disabled="!moveTargetCategoryId" @click="handleMoveToCategory(moveTargetCategoryId!)">
        确认移动
      </el-button>
    </template>
  </el-dialog>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApiStore } from '@/stores/apiStore'
import { useTabsStore } from '@/stores/tabsStore'
import { useEnvStore } from '@/stores/envStore'
import { Plus, Download, FolderOpen, FolderPlus, Trash2, FolderInput, Folder, Check, X, ChevronRight } from 'lucide-vue-next'
import { useEventBus } from '@/composables/useEventBus'
import { useVirtualScroll } from '@/composables/useVirtualScroll'
import { EVENTS } from '@/constants/events'
import { useRequireLogin } from '@/composables/useRequireLogin'
import { useI18n } from 'vue-i18n'
import { MSG } from '@/constants/messages'
import { msgSuccess, msgError } from '@/utils/message'
import { logger, isSilentAuthError } from '@/utils/logger'
import { ElMessage } from 'element-plus'
import type { ApiCategory, ApiDefinition } from '@/types'

import request from '@/api/request'
import CategoryNode from './CategoryNode.vue'
import ApiNode from './ApiNode.vue'
import EmptyState from './EmptyState.vue'
import ImportWizard from './ImportWizard.vue'

const { requireLogin } = useRequireLogin()
const { t } = useI18n()
const props = defineProps<{ projectId: number }>()
const apiStore = useApiStore()
const keyword = ref('')
const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()
const envStore = useEnvStore()
const showImportDialog = ref(false)
const importCategoryId = ref<number | null>(null)

// ── 批量选择状态 ──
const selectedApiIds = ref<Set<number>>(new Set())
const showMoveDialog = ref(false)
const moveTargetCategoryId = ref<number | null>(null)

const selectedCount = computed(() => selectedApiIds.value.size)

function toggleApiSelection(apiId: number) {
  if (selectedApiIds.value.has(apiId)) {
    selectedApiIds.value.delete(apiId)
  } else {
    selectedApiIds.value.add(apiId)
  }
  // 触发响应式更新
  selectedApiIds.value = new Set(selectedApiIds.value)
}

function isApiSelected(apiId: number): boolean {
  return selectedApiIds.value.has(apiId)
}

function clearSelection() {
  selectedApiIds.value = new Set()
}

async function batchDelete() {
  if (!await requireLogin('批量删除')) return
  const ids = Array.from(selectedApiIds.value)
  if (ids.length === 0) return

  try {
    const { ElMessageBox } = await import('element-plus')
    await ElMessageBox.confirm(
      t('apis.sidebarBatchDeleteConfirm', { count: ids.length }),
      t('apis.sidebarBatchDeleteTitle'),
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    const loadingMsg = ElMessage({
      message: t('apis.sidebarBatchDeleteCount', { count: ids.length }),
      type: 'info',
      duration: 0,
    })
    try {
      await Promise.all(ids.map(id => request.delete(`/projects/${props.projectId}/apis/${id}`)))
      loadingMsg.close()
      msgSuccess(t('apis.sidebarBatchDeleteDone', { count: ids.length }))
      clearSelection()
      // 关闭被删除接口的标签页
      ids.forEach(id => tabsStore.removeTab(`api-${id}`))
      apiStore.clearCache()
      await apiStore.fetchCategories(props.projectId)
    } catch (err) {
      loadingMsg.close()
      msgError(t('apis.sidebarBatchDeleteFailed'))
      logger.error('[SidebarTree] batch delete failed:', err)
    }
  } catch {
    // 用户取消确认，不做处理
  }
}

async function handleMoveToCategory(targetCategoryId: number) {
  if (!await requireLogin('移动接口')) return
  const ids = Array.from(selectedApiIds.value)
  if (ids.length === 0) return

  try {
    await Promise.all(ids.map(id =>
      request.put(`/projects/${props.projectId}/apis/${id}/move`, { category_id: targetCategoryId })
    ))
    msgSuccess(`已移动 ${ids.length} 个接口到目标目录`)
    clearSelection()
    showMoveDialog.value = false
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
  } catch (err) {
    logger.error('[SidebarTree] batch move failed:', err)
  }
}

// Provide selection state to child components
import { provide } from 'vue'
provide('apiSelection', {
  selectedApiIds,
  toggleApiSelection,
  isApiSelected,
  clearSelection,
})

const eventBus = useEventBus()

// ── 搜索防抖（300ms）──────────────
const keywordDebounced = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(keyword, (val) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { keywordDebounced.value = val }, 300)
})

const handleImportToCategory = (categoryId: number) => {
  importCategoryId.value = categoryId
  showImportDialog.value = true
}

// ── 事件委托：统一关闭右键菜单（避免每个节点注册 listener）──────────────
function onDocumentClick() {
  eventBus.emit(EVENTS.CTX_CLOSE_ALL)
}

const _creatingCategory = ref(false)

// 行内创建目录
const inlineCreating = ref(false)
const inlineInputValue = ref('')
const inlineInputRef = ref<HTMLInputElement | null>(null)

function startInlineCreate() {
  void requireLogin('新建接口目录').then((ok) => {
    if (!ok) return
    inlineCreating.value = true
    inlineInputValue.value = ''
    void nextTick(() => {
      inlineInputRef.value?.focus()
      // 滚动到树列表底部，确保新增输入框可见
      const treeBody = treeEl.value?.querySelector('.tree-body') as HTMLElement
      if (treeBody) treeBody.scrollTop = treeBody.scrollHeight
    })
  })
}

async function confirmInlineCreate() {
  const name = inlineInputValue.value.trim()
  if (!name) {
    inlineCreating.value = false
    return
  }
  if (_creatingCategory.value) return
  _creatingCategory.value = true
  try {
    await request.post(`/projects/${props.projectId}/categories`, { name })
    msgSuccess(MSG.SAVE_SUCCESS)
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
    inlineCreating.value = false
    inlineInputValue.value = ''
  } catch (err) {
    logger.error('[SidebarTree] create category failed:', err)
    msgError('创建目录失败，请重试')
    // 恢复输入状态，让用户可以修正
    inlineCreating.value = true
    void nextTick(() => {
      inlineInputRef.value?.focus()
      inlineInputRef.value?.select()
    })
  } finally {
    _creatingCategory.value = false
  }
}

function cancelInlineCreate() {
  inlineCreating.value = false
  inlineInputValue.value = ''
}

const handleNewApi = () => { void onNewApi() }
const handleImport = () => { void onImport() }
onMounted(() => {
  // 事件委托：全局单次监听
  document.addEventListener('click', onDocumentClick)
  eventBus.on(EVENTS.NEW_API, handleNewApi)
  eventBus.on(EVENTS.IMPORT_API, handleImport)
  eventBus.on(EVENTS.IMPORT_TO_CATEGORY, handleImportToCategory)

  // 非接口管理页不加载目录，避免深层页被侧栏初始化阻塞
  if (!route.path.match(/\/projects\/\d+\/apis(\/|$)/)) {
    return
  }

  void apiStore.fetchCategories(props.projectId)
    .then(() => {
      // 如果当前在接口详情页，自动展开该接口所属接口目录
      const apiIdMatch = route.path.match(/\/projects\/\d+\/apis\/detail\/(\d+)/)
      if (apiIdMatch) {
        const targetApiId = Number(apiIdMatch[1])
        function findCategoryForApi(categories: ApiCategory[]): number | null {
          for (const cat of categories) {
            if (cat.first_api && cat.first_api.id === targetApiId) return cat.id
            if (cat.children) {
              const found = findCategoryForApi(cat.children)
              if (found) return found
            }
          }
          return null
        }
        const catId = findCategoryForApi(apiStore.categories)
        if (catId && !apiStore.expandedCategories.includes(catId)) {
          apiStore.toggleCategory(catId)
        }
        if (catId && !apiStore.apisByCategory[catId]) {
          apiStore.fetchApis(props.projectId, catId).catch(() => { logger.warn('[SidebarTree] fetchApis failed') })
        }
      }
      // 不再自动打开第一个接口 - 用户应看到 API 列表页
    })
    .catch((err) => {
      logger.warn('[SidebarTree] fetchCategories failed on mount:', err)
    })
})



onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
  eventBus.off(EVENTS.NEW_API, handleNewApi)
  eventBus.off(EVENTS.IMPORT_API, handleImport)
  eventBus.off(EVENTS.IMPORT_TO_CATEGORY, handleImportToCategory)
  // ctx:close-all 没有在 onMounted 中绑定，不需要卸载
  if (searchTimer) clearTimeout(searchTimer)
})
watch(() => props.projectId, async (newId, _oldId) => {
  if (!newId) return
  apiStore.clearCache()
  try {
    await apiStore.fetchCategories(newId)
  } catch (err) {
    if (!isSilentAuthError(err)) logger.error('[SidebarTree] fetch categories failed:', err)
    /* 未登录时 401，静默处理 */
  }
  // 项目切换后不再自动打开第一个接口 - 用户应看到 API 列表页
  
})

// filteredCategories 使用防抖后的 keyword
const filteredCategories = computed(() => {
  const kw = keywordDebounced.value
  if (!kw) return apiStore.categories

  function matchCategory(cat: ApiCategory): boolean {
    // 目录名匹配
    if (cat.name.includes(kw)) return true
    // 检查已加载的接口是否匹配
    const apis = apiStore.apisByCategory[cat.id]
    if (apis && apis.some((a: ApiDefinition) => a.name.includes(kw))) return true
    // 递归检查子目录
    if (cat.children) {
      return cat.children.some((child: ApiCategory) => matchCategory(child))
    }
    return false
  }

  return apiStore.categories.filter(matchCategory)
})

interface FlatItem {
  type: 'category' | 'api'
  category?: ApiCategory
  api?: ApiDefinition
  depth: number
  key: string
}

const flatItems = computed<FlatItem[]>(() => {
  const result: FlatItem[] = []
  function flatten(categories: ApiCategory[], depth: number) {
    for (const cat of categories) {
      result.push({ type: 'category', category: cat, depth, key: `cat-${cat.id}` })
      if (apiStore.expandedCategories.includes(cat.id)) {
        const apis = apiStore.apisByCategory[cat.id]
        if (apis) {
          for (const api of apis) {
            result.push({ type: 'api', api, depth: depth + 1, key: `api-${api.id}` })
          }
        }
        if (cat.children) {
          flatten(cat.children, depth + 1)
        }
      }
    }
  }
  flatten(filteredCategories.value, 0)
  return result
})

const { visibleItems, totalHeightStyle, offsetStyle, scrollContainer, enabled } = useVirtualScroll<FlatItem>(flatItems, {
  threshold: 50,
  itemHeight: 36,
})

function isCatExpanded(catId: number): boolean {
  return apiStore.expandedCategories.includes(catId)
}

function isCatEmpty(cat: ApiCategory): boolean {
  return cat.api_count === 0 && (!cat.children || cat.children.length === 0)
}

async function toggleFlatCat(cat: ApiCategory) {
  if (isCatEmpty(cat)) return
  apiStore.toggleCategory(cat.id)
  if (isCatExpanded(cat.id) && !apiStore.apisByCategory[cat.id]) {
    await apiStore.fetchApis(props.projectId, cat.id)
  }
}

async function onNewApi() {
  if (!await requireLogin('新建接口')) return
  sessionStorage.removeItem('new_api_category')
  tabsStore.addTab({
    key: 'api-new',
    label: '新接口',
    type: 'api',
    method: 'GET',
    closable: true,
    editableName: true,
    projectId: props.projectId,
  })
  void router.push(`/projects/${props.projectId}/apis/detail/new`)
}

function handleToolbarCommand(cmd: string) {
  if (cmd === 'new-api') void onNewApi()
  else if (cmd === 'new-category') startInlineCreate()
  else if (cmd === 'import') void onImport()
}

async function onImport() {
  if (!await requireLogin('导入接口')) return
  showImportDialog.value = true
}

async function handleImportSuccess(result: { created_apis?: number }) {
  msgSuccess(MSG.IMPORT_EXECUTE_DONE(result.created_apis || 0))
  apiStore.clearCache()
  await apiStore.fetchCategories(props.projectId)
  // 重新获取环境变量和全局配置，确保 VarAwareInput 能识别最新变量
  await envStore.fetchEnvs(props.projectId)
  await envStore.fetchGlobalConfig(props.projectId)
  // 导入后留在列表页，不自动跳转到接口详情（与注释一致）
}

// ── 拖拽调整面板宽度 ──
const MIN_WIDTH = 180
const MAX_WIDTH = 600
const TREE_WIDTH_KEY = 'api_pilot_tree_width'

const treeEl = ref<HTMLElement | null>(null)
let isResizing = false

function startResize(e: MouseEvent) {
  isResizing = true
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  treeEl.value?.classList.add('is-resizing')

  const startX = e.clientX
  const startWidth = treeEl.value?.offsetWidth || 240

  function onMouseMove(ev: MouseEvent) {
    if (!isResizing) return
    const diff = ev.clientX - startX
    const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + diff))
    if (treeEl.value) {
      treeEl.value.style.width = newWidth + 'px'
    }
  }

  function onMouseUp() {
    isResizing = false
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
    treeEl.value?.classList.remove('is-resizing')
    if (treeEl.value) {
      try {
        localStorage.setItem(TREE_WIDTH_KEY, String(treeEl.value.offsetWidth))
      } catch { /* localStorage 可能不可用 */ }
    }
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
  }

  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

// 恢复保存的宽度
onMounted(() => {
  try {
    const saved = localStorage.getItem(TREE_WIDTH_KEY)
    if (saved) {
      const w = parseInt(saved, 10)
      if (w >= MIN_WIDTH && w <= MAX_WIDTH && treeEl.value) {
        treeEl.value.style.width = w + 'px'
      }
    }
  } catch { /* localStorage 可能不可用 */ }
})

</script>
<style scoped>
/* ===== 侧边树面板布局 ===== */
.sidebar-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-bg);
  border-right: 1px solid var(--border-subtle);
  overflow: hidden;
  transition: border-color var(--duration-base) var(--ease-smooth);
}

/* ===== 搜索框 ===== */
.tree-search {
  padding: var(--space-3) var(--space-3) var(--space-2);
}
.tree-search :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: none;
  border: 1px solid var(--border-subtle);
  background: var(--surface-hover);
  transition: var(--transition-fast);
  padding: 0 var(--space-2-5);
}
.tree-search :deep(.el-input__wrapper:hover) {
  border-color: var(--primary-300);
  background: var(--surface-card);
}
.tree-search :deep(.el-input__wrapper:focus-within) {
  border-color: var(--primary-500);
  background: var(--surface-card);
  box-shadow: var(--shadow-focus);
}
.tree-search :deep(.el-input__inner) {
  font-size: var(--text-sm);
  height: var(--height-row-compact);
}

/* ===== 操作按钮栏 ===== */
.tree-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: 0 var(--space-3) var(--space-2-5);
}
.tree-toolbar :deep(.el-button) {
  height: var(--height-row-compact);
  padding: 0 var(--space-2-5);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-md);
  flex: 1;
  min-width: 0;
  transition: var(--transition-fast);
}
.tree-toolbar :deep(.el-button span) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.tree-toolbar :deep(.el-button--primary) {
  background: var(--grad-primary);
  border: none;
  box-shadow: var(--shadow-sm);
  color: var(--text-inverse);
}
.tree-toolbar :deep(.el-button--primary:hover) {
  background: var(--grad-primary-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.tree-toolbar :deep(.el-button--primary:active) {
  transform: translateY(0) scale(var(--press-scale));
  box-shadow: var(--shadow-xs);
}
.tree-toolbar :deep(.el-button--default) {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}
.tree-toolbar :deep(.el-button--default:hover) {
  border-color: var(--primary-300);
  color: var(--primary-600);
  background: var(--color-primary-alpha-06);
  box-shadow: var(--shadow-xs);
}
.tree-toolbar :deep(.el-button--default:active) {
  transform: scale(var(--press-scale));
}

/* ===== 下拉菜单项增强 ===== */
:deep(.el-dropdown-menu-item) {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  transition: var(--transition-fast);
}
:deep(.el-dropdown-menu-item:hover) {
  background: var(--color-primary-alpha-06);
  color: var(--text-primary);
}

/* ===== 二级工具栏（新建接口目录 - 圆角按钮风格） ===== */
.tree-toolbar-secondary {
  padding: 0 var(--space-3) var(--space-2-5);
}
.tree-toolbar-secondary :deep(.el-button) {
  width: 100%;
  justify-content: center;
  gap: var(--space-1-5);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--primary-600);
  padding: var(--space-1) var(--space-2);
  height: auto;
  border: 1px solid var(--primary-200);
  border-radius: var(--radius-md);
  background: var(--color-primary-alpha-06);
  transition: var(--transition-fast);
}
.tree-toolbar-secondary :deep(.el-button:hover) {
  color: var(--text-inverse);
  border-color: var(--primary-500);
  background: var(--primary-500);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.tree-toolbar-secondary :deep(.el-button:active) {
  transform: translateY(0) scale(var(--press-scale));
}

/* ===== 分隔线 ===== */
.tree-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-subtle), transparent);
  margin: 0 var(--space-3) var(--space-1);
}

/* ===== 树主体 ===== */
.tree-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}
.tree-body::-webkit-scrollbar {
  width: 4px;
}
.tree-body::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
}
.tree-body::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}
.tree-body::-webkit-scrollbar-thumb:active {
  background: var(--scrollbar-thumb-active);
}
.tree-body::-webkit-scrollbar-track {
  background: transparent;
}

/* ===== 骨架屏 ===== */
.tree-skeleton {
  height: var(--height-row-compact);
  margin: var(--space-2) var(--space-2);
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, var(--surface-hover) 25%, var(--border-default) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
  animation: tree-skeleton-shimmer 1.5s ease-in-out infinite;
}
@keyframes tree-skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== 行内创建目录（追加到列表底部） ===== */
.inline-create-node {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-2-5) var(--space-3);
  margin: var(--space-2) var(--space-2) var(--space-2);
  border-radius: var(--radius-md);
  background: var(--color-primary-alpha-04);
  border: 1px dashed var(--primary-300);
  animation: fadeIn var(--duration-fast) var(--ease-out);
}
.inline-create-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--text-sm);
  color: var(--text-primary);
  outline: none;
  min-width: 0;
  transition: var(--transition-fast);
}
.inline-create-input::placeholder {
  color: var(--text-muted);
}
.inline-create-input:focus {
  color: var(--text-primary);
}
.inline-confirm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--primary-500);
  color: var(--text-inverse);
  cursor: pointer;
  flex-shrink: 0;
  transition: var(--transition-fast);
}
.inline-confirm-btn:hover:not(:disabled) {
  background: var(--primary-600);
  transform: scale(1.05);
  box-shadow: var(--shadow-sm);
}
.inline-confirm-btn:active:not(:disabled) {
  transform: scale(var(--press-scale));
}
.inline-confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.inline-cancel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  transition: var(--transition-fast);
}
.inline-cancel-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--surface-hover);
}

/* ===== 底部栏 ===== */
.sidebar-footer {
  padding: calc(var(--space-2) - 2px) var(--space-3) var(--space-2);
  border-top: 1px solid var(--border-subtle);
}
.footer-link {
  width: 100%;
  justify-content: flex-start;
  gap: var(--space-1-5);
  color: var(--text-muted);
  font-size: var(--text-xs);
  border: none;
  background: transparent;
  padding: var(--space-1-5) var(--space-2);
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}
.footer-link:hover {
  color: var(--error-text);
  background: var(--color-error-alpha-06);
}

/* 拖拽调整宽度手柄 */
.tree-resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 5px;
  cursor: col-resize;
  z-index: var(--z-dropdown);
  transition: background var(--duration-fast) var(--ease-smooth),
              width var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}
.tree-resize-handle:hover {
  background: var(--primary-300);
  width: 6px;
  box-shadow: -2px 0 8px var(--color-primary-alpha-16);
}
.tree-resize-handle:active {
  background: var(--primary-500);
  width: 7px;
  box-shadow: -3px 0 12px var(--color-primary-alpha-24);
}

/* 拖拽中状态 — 通过 JS 动态添加 .is-resizing 类 */
.sidebar-tree.is-resizing {
  user-select: none;
}
.sidebar-tree.is-resizing .tree-resize-handle {
  background: var(--primary-400);
  width: 7px;
  box-shadow: -3px 0 16px var(--color-primary-alpha-30);
}

html.dark .sidebar-tree { background: var(--surface-card); border-color: var(--border-subtle); }
html.dark .tree-header { background: var(--surface-hover); border-color: var(--border-default); }
html.dark .tree-search { background: var(--surface-input); border-color: var(--border-default); color: var(--text-primary); }
html.dark .tree-search::placeholder { color: var(--text-muted); }
html.dark .tree-node { color: var(--text-secondary); }
html.dark .tree-node:hover { background: var(--surface-hover); color: var(--text-primary); }
html.dark .tree-node.active { background: var(--surface-selected); color: var(--primary-400); }
html.dark .tree-node-icon { color: var(--text-muted); }
html.dark .tree-node-count { background: var(--surface-hover); color: var(--text-muted); }
html.dark .tree-group-label { color: var(--text-muted); }
html.dark .tree-empty { color: var(--text-muted); }
html.dark .tree-resize-handle:hover { background: var(--primary-400); box-shadow: -2px 0 8px var(--color-primary-alpha-20); }
html.dark .tree-resize-handle:active { background: var(--primary-500); box-shadow: -3px 0 12px var(--color-primary-alpha-30); }
html.dark .sidebar-tree.is-resizing .tree-resize-handle { background: var(--primary-500); box-shadow: -3px 0 16px var(--color-primary-alpha-35); }

/* ===== 批量选择工具栏 ===== */
.batch-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary-alpha-08);
  border-bottom: 1px solid var(--color-primary-alpha-15);
  animation: slideDown var(--duration-fast) var(--ease-out);
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}
.batch-count {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
}
.batch-toolbar :deep(.el-button) {
  height: 28px;
  padding: 0 var(--space-2-5);
  font-size: var(--text-xs);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

/* ===== 移动目录弹窗 ===== */
.move-tree {
  max-height: 300px;
  overflow-y: auto;
}
.move-cat-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
  color: var(--text-secondary);
}
.move-cat-item:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
.move-cat-item.selected {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
}

html.dark .batch-toolbar {
  background: var(--color-primary-alpha-12);
  border-color: var(--color-primary-alpha-20);
}
html.dark .batch-count {
  color: var(--primary-400);
}

/* ===== 虚拟滚动扁平化目录行 ===== */
.flat-cat-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: var(--height-row-compact);
  padding: var(--space-2) var(--space-2-5) var(--space-2) var(--space-3);
  margin: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  background: transparent;
  border: none;
  transition: var(--transition-fast);
  position: relative;
}
.flat-cat-row:hover {
  background: var(--surface-hover);
}
.flat-cat-row:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: -2px;
  background: var(--surface-hover);
}
.flat-cat-row.is-expanded {
  background: var(--color-primary-alpha-10);
}
.flat-chevron {
  transition: transform var(--duration-base) var(--ease-spring);
  flex-shrink: 0;
  color: var(--text-muted);
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
}
.flat-chevron.expanded {
  transform: rotate(90deg);
}
.flat-cat-icon {
  flex-shrink: 0;
  color: var(--primary-500);
  width: var(--size-icon-md);
  height: var(--size-icon-md);
}
.flat-cat-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.flat-cat-count {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  padding: 2px var(--space-2);
  min-width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  border-radius: var(--radius-full);
  background: var(--surface-hover);
  color: var(--text-secondary);
  white-space: nowrap;
}
.flat-api-wrapper {
  min-height: var(--height-row-compact);
}

html.dark .flat-cat-icon { color: var(--primary-400); }
html.dark .flat-cat-name { color: var(--text-primary); }
html.dark .flat-cat-count { color: var(--text-secondary); background: var(--surface-hover); }
html.dark .flat-cat-row:hover { background: var(--surface-hover); }
html.dark .flat-cat-row.is-expanded { background: var(--color-primary-alpha-12); }

</style>
