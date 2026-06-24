<template>
  <div class="api-node">
    <div
      class="api-row"
      :class="{ selected: isSelected }"
      @click="onOpenApi"
      @contextmenu.prevent="showContextMenu($event)"
    >
      <el-checkbox
        :model-value="isSelected"
        @change="toggleSelection"
        @click.stop
        size="small"
        class="api-checkbox"
      />
      <span v-if="!canExpand" class="chevron-placeholder"></span>
      <ChevronRight
        v-else
        :size="14"
        class="chevron"
        :class="{ expanded: showCases }"
        @click.stop="onToggleCases"
      />
      <span class="method-badge" :class="api.method.toLowerCase()">{{ api.method }}</span>
      <span class="api-name" :title="api.name">{{ api.name }}</span>
      <span class="case-count" :class="{ 'no-cases': !caseCount }">{{ caseCount || 0 }}</span>
    </div>
    <transition name="tree-expand">
      <div v-if="canExpand && showCases" class="api-cases">
        <template v-if="realCases.length || loadingCases">
          <CaseNode v-for="c in sortedCases" :key="c.id" :case-item="c" :project-id="projectId" />
          <SkeletonRow v-if="loadingCases && !realCases.length" />
        </template>
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
import { ref, computed, onMounted, onUnmounted, inject } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useApiStore } from "../stores/apiStore"
import { useTabsStore } from "../stores/tabsStore"
import { Edit, Copy, Trash2, ChevronRight } from "lucide-vue-next"
import { ElMessageBox } from "element-plus"
import { MSG, CONFIRM } from "../constants/messages"
import { msgSuccess } from "../utils/message"
import request from "../api/request"
import { useEventBus } from "../composables/useEventBus"
import { EVENTS } from "../constants/events"
import CaseNode from "./CaseNode.vue"
import SkeletonRow from "./SkeletonRow.vue"
import TreeContextMenu from "./tree/TreeContextMenu.vue"
import { useRequireLogin } from "../composables/useRequireLogin"
import { logger } from "@/utils/logger"
import type { ApiDefinition } from "../types"

const props = defineProps<{ api: ApiDefinition; projectId: number }>()
const route = useRoute()
const router = useRouter()
const apiStore = useApiStore()
const tabsStore = useTabsStore()
const eventBus = useEventBus()
const { requireLogin } = useRequireLogin()

const isSelected = computed(() => {
  const routeApiId = Number(route.params.apiId)
  const routeCaseId = Number(route.params.caseId)
  // 直接选中接口 或 用例属于此接口时均高亮
  if (!isNaN(routeApiId) && routeApiId === props.api.id) return true
  if (!isNaN(routeCaseId)) {
    const cases = apiStore.casesByApi[props.api.id] || []
    return cases.some(c => c.id === routeCaseId)
  }
  return false
})

const showCases = ref(false)
const hasExpanded = ref(false)
const loadingCases = ref(false)

// 直接取 store 数据，不依赖缓存状态
const realCases = computed(() => apiStore.casesByApi[props.api.id] || [])
const sortedCases = computed(() => {
  const priorityOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 }
  return [...realCases.value].sort((a, b) => {
    const pa = priorityOrder[a.priority] ?? 99
    const pb = priorityOrder[b.priority] ?? 99
    return pa - pb
  })
})
const caseCount = computed(() => props.api.case_count || 0)
const canExpand = computed(() => (props.api.case_count || 0) > 0 || realCases.value.length > 0)

const contextMenu = ref({ visible: false, x: 0, y: 0 })

// ── 批量选择 ──
interface ApiSelection {
  selectedApiIds: { value: Set<number> }
  toggleApiSelection: (id: number) => void
  isApiSelected: (id: number) => boolean
  clearSelection: () => void
}
const selection = inject<ApiSelection | null>('apiSelection', null)

function toggleSelection() {
  if (selection) {
    selection.toggleApiSelection(props.api.id)
  }
}

interface ContextMenuItem {
  label?: string
  icon?: object
  action?: () => void | Promise<void>
  divider?: boolean
  danger?: boolean
}

const contextMenuItems = computed<ContextMenuItem[]>(() => [
  { label: "编辑", icon: Edit, action: onOpenApi },
  { label: "复制接口", icon: Copy, action: copyApi },
  { divider: true },
  { label: "删除", icon: Trash2, danger: true, action: deleteApi },
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

function onOpenApi() {
  tabsStore.addTab({
    key: `api-${props.api.id}`,
    label: props.api.name,
    type: "api",
    method: props.api.method,
    apiId: props.api.id,
    closable: true,
    projectId: props.projectId,
  })
  void router.push(`/projects/${props.projectId}/apis/detail/${props.api.id}`)
}

async function onToggleCases() {
  if (!canExpand.value) return
  showCases.value = !showCases.value
  if (showCases.value) {
    hasExpanded.value = true
    if (!realCases.value.length) {
      loadingCases.value = true
      await apiStore.fetchCases(props.projectId, props.api.id)
      loadingCases.value = false
    }
  }
}

async function copyApi() {
  if (!await requireLogin("复制接口")) return
  try {
    const res = await request.post<
      unknown,
      { data?: { id?: number; name?: string } }
    >(`/projects/${props.projectId}/apis/${props.api.id}/duplicate`)
    msgSuccess(MSG.COPY_SUCCESS)
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
    // 如果后端返回了新接口 ID，自动导航
    if (res.data?.id) {
      const newId = res.data.id
      tabsStore.addTab({
        key: `api-${newId}`,
        label: res.data.name || props.api.name + " (副本)",
        type: "api",
        method: props.api.method,
        apiId: newId,
        closable: true,
        projectId: props.projectId,
      })
      void router.push(`/projects/${props.projectId}/apis/detail/${newId}`)
    }
  } catch (err) {
    logger.error('[ApiNode] copy API failed:', err)
    // Error handled by interceptor
  }
}

async function deleteApi() {
  if (!await requireLogin("删除接口")) return
  try {
    await ElMessageBox.confirm(
      CONFIRM.DELETE_API.message(props.api.name),
      CONFIRM.DELETE_API.title,
      {
        type: "warning",
        confirmButtonText: CONFIRM.DELETE_API.confirmText,
        cancelButtonText: CONFIRM.DELETE_API.cancelText,
      }
    )
    await request.delete(`/projects/${props.projectId}/apis/${props.api.id}`)
    msgSuccess("接口已删除")
    // 关闭该接口的标签页
    tabsStore.removeTab(`api-${props.api.id}`)
    // 如果当前正在查看被删除的接口，跳转到接口管理首页
    const currentApiId = Number(route.params.apiId)
    if (currentApiId === props.api.id) {
      void router.replace(`/projects/${props.projectId}/apis`)
    }
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
  } catch (err) {
    logger.error('[ApiNode] delete API failed:', err)
    // cancelled or error handled by interceptor
  }
}
</script>

<style scoped>
/* ===== 接口节点行布局 - 扁平设计，强选中态，左侧 accent bar ===== */
.api-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2-5) var(--space-2) var(--space-3);
  min-height: var(--height-row-compact);
  margin: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-primary);
  position: relative;
  transition: var(--transition-fast);
}

/* 左侧选中指示条 */
.api-row::before {
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

.api-row:hover {
  background: var(--surface-hover);
}

.api-row:hover .api-name {
  color: var(--primary-700);
}

.api-row.selected {
  background: var(--color-primary-alpha-10);
}

.api-row.selected::before {
  transform: translateY(-50%) scaleY(1);
}

.api-row.selected .api-name {
  color: var(--primary-700);
  font-weight: var(--weight-semibold);
}

/* ===== 展开/折叠箭头 - 动画优化 ===== */
.api-row .chevron {
  flex-shrink: 0;
  transition: transform var(--duration-base) var(--ease-spring);
  color: var(--text-muted);
  padding: 2px;
  border-radius: var(--radius-sm);
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
}

.api-row .chevron-placeholder {
  flex-shrink: 0;
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
}

.api-row .chevron:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
  transform: scale(1.05);
}

.api-row .chevron:active {
  transform: scale(var(--press-scale));
}

.api-row .chevron.expanded {
  transform: rotate(90deg);
}

/* ===== HTTP 方法徽章 - 柔和扁平风格 ===== */
.method-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  height: 22px;
  padding: 0 var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
  transition: opacity var(--duration-fast) var(--ease-smooth);
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

/* ===== API 名称 ===== */
.api-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: var(--transition-fast);
}

/* ===== 用例计数徽章 ===== */
.case-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 var(--space-1-5);
  border-radius: var(--radius-full);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  background: var(--surface-hover);
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
  transition: var(--transition-fast);
}

.api-row:hover .case-count:not(.no-cases) {
  background: var(--color-primary-alpha-15);
  color: var(--primary-700);
}

.case-count.no-cases {
  background: transparent;
  color: var(--text-disabled);
  font-weight: var(--weight-medium);
}

/* ===== 用例列表容器 ===== */
.api-cases {
  padding: var(--space-0-5) 0 var(--space-1-5) var(--space-9);
  margin: 0 var(--space-2) var(--space-1);
  background: transparent;
  border-radius: 0;
  border: none;
  position: relative;
}

/* 用例列表左侧连接线 */
.api-cases::before {
  content: "";
  position: absolute;
  left: 18px;
  top: 0;
  bottom: 6px;
  width: 1px;
  background: linear-gradient(180deg, var(--border-subtle) 0%, transparent 100%);
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

/* ===== 批量选择复选框 ===== */
.api-checkbox {
  margin-right: 2px;
  flex-shrink: 0;
}

.api-checkbox :deep(.el-checkbox__inner) {
  width: 14px;
  height: 14px;
}

.api-row:hover .api-checkbox {
  opacity: 1;
}

/* ===== 加载提示 ===== */
.loading-hint {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

/* ===== 暗色模式适配 ===== */
html.dark .api-name {
  color: var(--text-primary);
}

html.dark .api-row:hover {
  background: var(--surface-hover);
}

html.dark .api-row:hover .api-name {
  color: var(--primary-400);
}

html.dark .api-row.selected {
  background: var(--color-primary-alpha-12);
}

html.dark .api-row.selected::before {
  background: var(--primary-400);
}

html.dark .api-row.selected .api-name {
  color: var(--primary-400);
}

html.dark .case-count {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

html.dark .case-count.no-cases {
  color: var(--text-muted);
  background: transparent;
}

html.dark .api-row:hover .case-count:not(.no-cases) {
  background: var(--color-primary-alpha-20);
  color: var(--primary-400);
}
</style>
