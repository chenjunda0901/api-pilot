<template>
  <div class="category-node">
    <div
      class="cat-row"
      :class="{ 'is-expanded': isExpanded }"
      tabindex="0"
      @click="onToggle"
      @keydown.enter="onToggle"
      @contextmenu.prevent="showContextMenu($event)"
    >
      <ChevronRight v-if="!isEmpty" :size="14" class="chevron" :class="{ expanded: isExpanded }" />
      <Folder :size="16" class="cat-icon" />
      <span v-if="!renaming" class="cat-name" :title="category.name">{{ category.name }}</span>
      <el-input
        v-else
        v-model="renameValue"
        ref="renameInputRef"
        size="small"
        class="rename-input"
        placeholder="接口目录名称"
        aria-label="接口目录名称"
        @blur="confirmRename"
        @keyup.enter="confirmRename"
        @keyup.escape="cancelRename"
        @click.stop
      />
      <span class="cat-count">{{ category.api_count || 0 }}</span>
    </div>
    <transition name="tree-expand">
      <div class="cat-children" v-show="isExpanded">
        <!-- 待创建接口占位 -->
        <div v-if="pendingApi" class="pending-api-row">
          <span class="pending-method-badge" :class="pendingApi.method.toLowerCase()">{{ pendingApi.method }}</span>
          <span class="pending-api-name">{{ pendingApi.name }}</span>
          <span class="pending-hint">编辑中…</span>
        </div>
        <template v-if="loadedApis">
          <ApiNode v-for="api in loadedApis" :key="api.id" :api="api" :project-id="projectId" />
        </template>
        <template v-else>
          <SkeletonRow />
        </template>
        <!-- 行内创建子目录 -->
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
        <CategoryNode
          v-for="child in category.children"
          :key="child.id"
          :category="child"
          :depth="depth + 1"
          :project-id="projectId"
        />
      </div>
    </transition>
    <TreeContextMenu
      :visible="contextMenu.visible"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :items="contextMenuItems"
      @close="closeContextMenu"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useApiStore } from "../stores/apiStore"
import { useTabsStore } from "../stores/tabsStore"
import { usePendingApiStore } from "../stores/pendingApiStore"
import type { ApiCategory, ApiDefinition } from "../types"
import {
  ChevronRight,
  Folder,
  Edit,
  Trash2,
  Plus,
  Copy,
  ChevronDown,
  Download,
  FolderPlus,
  Check,
  X,
} from "lucide-vue-next"
import { ElMessageBox } from "element-plus"
import { MSG } from "../constants/messages"
import { msgSuccess, msgError, msgInfo, msgWarning } from "../utils/message"
import request from "../api/request"
import { useEventBus } from "../composables/useEventBus"
import { EVENTS } from "../constants/events"
import { useRequireLogin } from "../composables/useRequireLogin"
import { logger } from "@/utils/logger"
import ApiNode from "./ApiNode.vue"
import SkeletonRow from "./SkeletonRow.vue"
import TreeContextMenu from "./tree/TreeContextMenu.vue"

const props = defineProps<{ category: ApiCategory; depth: number; projectId: number }>()
const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()
const apiStore = useApiStore()

const isEmpty = computed(
  () =>
    props.category.api_count === 0 &&
    (!props.category.children || props.category.children.length === 0)
)
const isExpanded = computed(
  () => apiStore.expandedCategories.includes(props.category.id)
)
const loadedApis = computed(() => apiStore.apisByCategory[props.category.id])

// Context menu state
const contextMenu = ref({ visible: false, x: 0, y: 0 })

// Rename state
const renaming = ref(false)
const renameValue = ref("")
const renameInputRef = ref<{ focus: () => void } | null>(null)

// 行内创建子目录状态
const inlineCreating = ref(false)
const inlineInputValue = ref('')
const inlineInputRef = ref<HTMLInputElement | null>(null)
const _creating = ref(false)

/** 当前目录下的待创建接口占位 */
const { addPendingNewApi, getPendingApi } = usePendingApiStore()
const pendingApi = computed(() => getPendingApi(props.category.id))

// 占位符消失后，如果目录为空则自动收起，避免留白
watch(pendingApi, (cur, prev) => {
  if (prev && !cur && isExpanded.value) {
    const apis = apiStore.apisByCategory[props.category.id]
    if (!apis || apis.length === 0) {
      apiStore.toggleCategory(props.category.id)
    }
  }
})

const eventBus = useEventBus()

interface ContextMenuItem {
  label?: string
  icon?: object
  action?: () => void | Promise<void>
  disabled?: boolean
  danger?: boolean
  divider?: boolean
}

const contextMenuItems = computed<ContextMenuItem[]>(() => [
  { label: "新建子接口目录", icon: Plus, action: createSubCategory },
  { label: "重命名", icon: Edit, action: startRename },
  { label: "新建接口", icon: Plus, action: createApiInCategory },
  { label: "导入接口", icon: Download, action: importToCategory },
  { divider: true },
  { label: "复制接口目录", icon: Copy, action: copyCategory, disabled: true },
  { label: "展开全部", icon: ChevronDown, action: expandAll },
  { label: "删除接口目录", icon: Trash2, danger: true, action: deleteCategory },
])

function showContextMenu(e: MouseEvent) {
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY }
}

function closeContextMenu() {
  contextMenu.value.visible = false
}

function onGlobalCtxClose() {
  if (contextMenu.value.visible) closeContextMenu()
}

onMounted(() => eventBus.on(EVENTS.CTX_CLOSE_ALL, onGlobalCtxClose))
onUnmounted(() => eventBus.off(EVENTS.CTX_CLOSE_ALL, onGlobalCtxClose))

async function onToggle() {
  if (renaming.value || isEmpty.value) return
  apiStore.toggleCategory(props.category.id)
  if (isExpanded.value && !loadedApis.value) {
    await apiStore.fetchApis(props.projectId, props.category.id)
  }
}

function createSubCategory() {
  inlineCreating.value = true
  inlineInputValue.value = ''
  void nextTick(() => {
    inlineInputRef.value?.focus()
    // 如果当前未展开，先展开以显示输入框
    if (!isExpanded.value) {
      apiStore.toggleCategory(props.category.id)
      void apiStore.fetchApis(props.projectId, props.category.id)
    }
  })
}

async function confirmInlineCreate() {
  const name = inlineInputValue.value.trim()
  if (!name) { inlineCreating.value = false; return }
  if (_creating.value) return
  _creating.value = true
  try {
    await request.post(`/projects/${props.projectId}/categories`, {
      name,
      parent_id: props.category.id,
    })
    msgSuccess("子接口目录已创建")
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
    if (!apiStore.expandedCategories.includes(props.category.id))
      apiStore.expandedCategories.push(props.category.id)
    if (isExpanded.value) await apiStore.fetchApis(props.projectId, props.category.id)
    inlineCreating.value = false
    inlineInputValue.value = ''
  } catch (err) {
    logger.error('[CategoryNode] inline create sub category failed:', err)
    msgError('创建目录失败，请重试')
    inlineCreating.value = true
    void nextTick(() => { inlineInputRef.value?.focus(); inlineInputRef.value?.select() })
  } finally {
    _creating.value = false
  }
}

function cancelInlineCreate() {
  inlineCreating.value = false
  inlineInputValue.value = ''
}

function startRename() {
  renaming.value = true
  renameValue.value = props.category.name
  void nextTick(() => {
    renameInputRef.value?.focus?.()
  })
}

async function confirmRename() {
  const name = (renameValue.value || "").trim()
  if (!name) {
    msgWarning("目录名不能为空")
    cancelRename()
    return
  }
  const oldName = props.category.name
  try {
    await request.put(`/projects/${props.projectId}/categories/${props.category.id}`, { name })
    renaming.value = false
    msgSuccess("重命名成功")
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
    // 如果当前接口目录展开，重载接口列表避免"加载中..."
    if (isExpanded.value) await apiStore.fetchApis(props.projectId, props.category.id)
  } catch (err) {
    logger.error('[CategoryNode] rename category failed:', err)
    renameValue.value = oldName
    // 保持 renaming=true，用户可以重试
  }
}

function cancelRename() {
  renaming.value = false
  renameValue.value = ""
}

async function createApiInCategory() {
  const { requireLogin } = useRequireLogin()
  if (!await requireLogin("新建接口")) return
  const catId = props.category.id
  sessionStorage.setItem("new_api_category", catId)

  // 立即添加到 store（先于任何 async 操作，确保 UI 及时更新）
  addPendingNewApi(catId, "新接口", "GET")

  // 立即展开目录并加载接口（如未展开）
  if (!apiStore.expandedCategories.includes(props.category.id)) {
    apiStore.expandedCategories.push(props.category.id)
  }
  // 有待创建占位时不加载（避免覆盖占位），仅在没有缓存时触发加载
  if (!apiStore.apisByCategory[props.category.id]) {
    // 不 await，让接口列表在后台加载
    void apiStore.fetchApis(props.projectId, props.category.id)
  }

  tabsStore.addTab({
    key: "api-new",
    label: "新接口",
    type: "api",
    method: "GET",
    closable: true,
    editableName: true,
    categoryId: catId,
    projectId: props.projectId,
  })
  void router.push(`/projects/${props.projectId}/apis/detail/new`)
}

function importToCategory() {
  eventBus.emit(EVENTS.IMPORT_TO_CATEGORY, props.category.id)
}

function copyCategory() {
  msgInfo("复制接口目录功能即将上线")
}

function expandAll() {
  function expandRecursive(cat: ApiCategory) {
    if (!apiStore.expandedCategories.includes(cat.id)) apiStore.expandedCategories.push(cat.id)
    if (!apiStore.apisByCategory[cat.id]) {
      apiStore.fetchApis(props.projectId, cat.id).catch(() => { logger.warn('[CategoryNode] fetchApis failed') })
    }
    if (cat.children) {
      cat.children.forEach(expandRecursive)
    }
  }
  expandRecursive(props.category)
}

async function deleteCategory() {
  // 快照当前展开状态，删除后恢复
  const expandedSnapshot = [...apiStore.expandedCategories]
  try {
    await ElMessageBox.confirm(MSG.DELETE_CATEGORY_CONFIRM(props.category.name), "确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
    await request.delete(`/projects/${props.projectId}/categories/${props.category.id}`)
    msgSuccess("接口目录已删除")

    // 收集该目录下所有接口 ID（递归）
    const apiIds: number[] = []
    function collectApiIds(cat: ApiCategory) {
      const apis = apiStore.apisByCategory[cat.id]
      if (apis) apis.forEach((a: ApiDefinition) => apiIds.push(a.id))
      if (cat.children) cat.children.forEach(collectApiIds)
    }
    collectApiIds(props.category)

    // 关闭所有相关标签页
    // 使用顶部已导入的 route 变量
    const currentApiId = Number(route.params.apiId)
    apiIds.forEach((id) => {
      tabsStore.removeTab(`api-${id}`)
      if (currentApiId === id) {
        void router.replace(`/projects/${props.projectId}/apis`)
      }
    })

    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)

    // 恢复展开状态（排除已删除的目录及其子目录）
    const deletedCatIds = new Set<number>([props.category.id])
    function collectDeletedIds(cat: ApiCategory): void {
      deletedCatIds.add(cat.id)
      if (cat.children) cat.children.forEach(collectDeletedIds)
    }
    collectDeletedIds(props.category)

    // 从快照中移除已删除的目录 ID，保留其余展开状态
    const restoredExpands = expandedSnapshot.filter(id => !deletedCatIds.has(id))
    apiStore.expandedCategories.length = 0
    apiStore.expandedCategories.push(...restoredExpands)
  } catch (err) {
    logger.error('[CategoryNode] delete category failed:', err)
    // cancelled or error handled by interceptor
  }
}
</script>

<style scoped>
/* ===== 目录节点容器 ===== */
.category-node {
  user-select: none;
}

/* ===== 目录行 - 扁平设计，强选中态，左侧 accent bar ===== */
.cat-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2-5) var(--space-2) var(--space-3);
  min-height: var(--height-row-compact);
  margin: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  background: transparent;
  border: none;
  transition: var(--transition-fast);
  position: relative;
}

/* 左侧展开指示条 */
.cat-row::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 18px;
  border-radius: 0 3px 3px 0;
  background: var(--primary-500);
  transition: transform var(--duration-fast) var(--ease-spring);
}

.cat-row:hover {
  background: var(--surface-hover);
  transform: translateX(2px);
}

.cat-row:hover .cat-icon {
  color: var(--primary-600);
  transform: scale(1.05);
}

.cat-row:hover .cat-name {
  color: var(--primary-700);
}

.cat-row:hover .chevron {
  color: var(--text-secondary);
}

.cat-row.is-expanded::before {
  transform: translateY(-50%) scaleY(1);
}

.cat-row.is-expanded {
  background: var(--color-primary-alpha-10);
}

.cat-row.is-expanded .cat-name {
  color: var(--primary-700);
}

/* ===== 展开/折叠箭头 - 动画优化 ===== */
.chevron {
  transition: transform var(--duration-base) var(--ease-spring),
              color var(--duration-fast) var(--ease-smooth);
  flex-shrink: 0;
  color: var(--text-muted);
  padding: 2px;
  border-radius: var(--radius-sm);
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
}

.chevron:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

.chevron:active {
  transform: scale(var(--press-scale));
}

.chevron.expanded {
  transform: rotate(90deg);
}

/* ===== 目录图标 - 大小和颜色优化 ===== */
.cat-icon {
  flex-shrink: 0;
  color: var(--primary-500);
  width: var(--size-icon-md);
  height: var(--size-icon-md);
  transition: var(--transition-fast);
}

.cat-row.is-expanded .cat-icon {
  color: var(--primary-600);
}

/* ===== 目录名称 ===== */
.cat-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  letter-spacing: var(--tracking-tight);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: var(--transition-fast);
}

/* ===== 接口计数徽章 ===== */
.cat-count {
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
  transition: var(--transition-fast);
}

.cat-row:hover .cat-count {
  background: var(--color-primary-alpha-12);
  color: var(--primary-700);
  transform: scale(1.05);
}

.cat-row.is-expanded .cat-count {
  background: var(--color-primary-alpha-15);
  color: var(--primary-700);
}

/* ===== 展开/折叠动画 ===== */
.tree-expand-enter-active {
  transition: opacity var(--duration-base) var(--ease-smooth),
              transform var(--duration-base) var(--ease-smooth),
              max-height var(--duration-slow) var(--ease-smooth);
  overflow: hidden;
  max-height: 800px;
}

.tree-expand-leave-active {
  transition: opacity var(--duration-fast) var(--ease-smooth),
              max-height var(--duration-fast) var(--ease-smooth);
  overflow: hidden;
}

.tree-expand-enter-from {
  opacity: 0;
  transform: translateY(-4px);
  max-height: 0;
}

.tree-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.tree-expand-enter-to {
  opacity: 1;
  transform: translateY(0);
  max-height: 800px;
}

.tree-expand-leave-from {
  opacity: 1;
  max-height: 800px;
}

/* ===== 子节点容器 ===== */
.cat-children {
  padding: var(--space-0-5) 0 var(--space-1-5) 0;
  margin: 0;
  background: transparent;
  border-radius: 0;
  border: none;
  position: relative;
}

/* 子节点左侧连接线 */
.cat-children::before {
  content: "";
  position: absolute;
  left: 20px;
  top: 0;
  bottom: 8px;
  width: 1px;
  background: linear-gradient(180deg, var(--border-subtle) 0%, transparent 100%);
}

/* ===== 加载提示 ===== */
.loading-hint {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* ===== 待创建接口占位行 ===== */
.pending-api-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: var(--height-row-compact);
  padding: 0 var(--space-2-5) 0 var(--space-3);
  border-radius: var(--radius-md);
  margin: var(--space-0-5) var(--space-2);
  background: var(--color-primary-alpha-04);
  border: 1px dashed var(--primary-300);
  cursor: default;
  animation: pending-pulse var(--duration-slow) var(--ease-smooth) infinite;
}

@keyframes pending-pulse {
  0%, 100% {
    border-color: var(--primary-300);
    opacity: 1;
  }
  50% {
    border-color: var(--primary-400);
    opacity: 0.85;
  }
}

/* 待创建接口方法徽章 */
.pending-method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-2);
  height: 22px;
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  min-width: 48px;
  flex-shrink: 0;
  box-shadow: var(--shadow-xs);
}

.pending-method-badge.get {
  background: var(--method-get-bg);
  color: var(--method-get-text);
  border: 1px solid var(--method-get-border);
}

.pending-method-badge.post {
  background: var(--method-post-bg);
  color: var(--method-post-text);
  border: 1px solid var(--method-post-border);
}

.pending-method-badge.put {
  background: var(--method-put-bg);
  color: var(--method-put-text);
  border: 1px solid var(--method-put-border);
}

.pending-method-badge.delete {
  background: var(--method-delete-bg);
  color: var(--method-delete-text);
  border: 1px solid var(--method-delete-border);
}

.pending-method-badge.patch {
  background: var(--method-patch-bg);
  color: var(--method-patch-text);
  border: 1px solid var(--method-patch-border);
}

/* 待创建接口名称 */
.pending-api-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 待创建接口提示文字 */
.pending-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  flex-shrink: 0;
  animation: pending-blink var(--duration-base) var(--ease-smooth) infinite;
}

@keyframes pending-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ===== 重命名输入框 ===== */
.rename-input {
  min-width: 100px;
  max-width: 220px;
  width: auto;
}

.rename-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: none;
  border: 1px solid var(--primary-300);
  background: var(--surface-card);
  transition: var(--transition-fast);
}

.rename-input :deep(.el-input__wrapper:hover) {
  border-color: var(--primary-400);
}

.rename-input :deep(.el-input__wrapper:focus-within) {
  border-color: var(--primary-500);
  box-shadow: var(--shadow-focus);
}

.rename-input :deep(.el-input__inner) {
  height: var(--height-row-compact);
  font-size: var(--text-sm);
  padding: 0 var(--space-2);
}

/* ===== 行内创建子目录 ===== */
.inline-create-node {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin: var(--space-1) var(--space-2);
  margin-left: calc(var(--space-3) + v-bind('(props.depth + 1) * 16') px);
  border-radius: var(--radius-md);
  background: var(--color-primary-alpha-04);
  border: 1px dashed var(--primary-300);
  animation: fadeIn var(--duration-fast) var(--ease-out);
  min-height: var(--height-row-compact);
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

/* 行内创建确认按钮 */
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
  box-shadow: var(--shadow-xs);
}

.inline-confirm-btn:active:not(:disabled) {
  transform: scale(var(--press-scale));
}

.inline-confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 行内创建取消按钮 */
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

.inline-cancel-btn:active {
  transform: scale(var(--press-scale));
}

/* ===== 暗色模式适配 ===== */
html.dark .cat-row:hover {
  background: var(--surface-hover);
}

html.dark .cat-icon {
  color: var(--primary-400);
}

html.dark .cat-row:hover .cat-icon {
  color: var(--primary-300);
}

html.dark .cat-row.is-expanded .cat-icon {
  color: var(--primary-300);
}

html.dark .cat-name {
  color: var(--text-primary);
}

html.dark .cat-row:hover .cat-name {
  color: var(--primary-300);
}

html.dark .cat-row.is-expanded .cat-name {
  color: var(--primary-400);
}

html.dark .cat-count {
  color: var(--text-secondary);
  background: var(--surface-hover);
}

html.dark .cat-row:hover .cat-count,
html.dark .cat-row.is-expanded .cat-count {
  color: var(--primary-300);
  background: var(--color-primary-alpha-20);
}

html.dark .pending-api-row {
  background: var(--color-primary-alpha-06);
  border-color: var(--primary-400);
}

html.dark .pending-api-name {
  color: var(--text-primary);
}

html.dark .pending-hint {
  color: var(--text-muted);
}

html.dark .rename-input :deep(.el-input__wrapper) {
  background: var(--surface-input);
  border-color: var(--primary-400);
}

html.dark .rename-input :deep(.el-input__wrapper:focus-within) {
  border-color: var(--primary-300);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-20);
}

html.dark .inline-create-node {
  background: var(--color-primary-alpha-06);
  border-color: var(--primary-400);
}

html.dark .inline-confirm-btn {
  background: var(--primary-400);
}

html.dark .inline-confirm-btn:hover:not(:disabled) {
  background: var(--primary-300);
}

html.dark .inline-cancel-btn {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}

html.dark .inline-cancel-btn:hover {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--surface-hover);
}
</style>
