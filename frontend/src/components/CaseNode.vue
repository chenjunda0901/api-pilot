<template>
  <div
    class="case-node"
    :class="{ selected: isSelected }"
    tabindex="0"
    @click="onOpenCase"
    @keydown.enter="onOpenCase"
    @contextmenu.prevent="showContextMenu($event)"
  >
    <el-tag v-if="caseItem.priority" :type="priorityType" size="small" class="case-priority">
      {{ caseItem.priority }}
    </el-tag>
    <span class="case-name">{{ caseItem.name }}</span>
    <span v-if="caseItem.case_type && caseItem.case_type !== 'other'" class="case-type-badge" :class="'type-' + caseItem.case_type">{{ caseTypeLabel(caseItem.case_type) }}</span>
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
import { ref, computed, onMounted, onUnmounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useTabsStore } from "../stores/tabsStore"
import { CheckCircle, Play, Edit, Copy, Trash2, XCircle } from "lucide-vue-next"
import { ElMessageBox } from "element-plus"
import { msgSuccess, msgInfo } from "../utils/message"
import request from "../api/request"
import { useApiStore } from "../stores/apiStore"
import { useEventBus } from "../composables/useEventBus"
import { EVENTS } from "../constants/events"
import TreeContextMenu from "./tree/TreeContextMenu.vue"
import type { TestCase } from "../types"
import { useRequireLogin } from "../composables/useRequireLogin"
import { logger } from "@/utils/logger"

const { requireLogin } = useRequireLogin()

const props = defineProps<{ caseItem: TestCase; projectId: number }>()
const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()
const apiStore = useApiStore()
const eventBus = useEventBus()

const isSelected = computed(() => {
  const routeCaseId = Number(route.params.caseId)
  return !isNaN(routeCaseId) && routeCaseId === props.caseItem.id
})

const contextMenu = ref({ visible: false, x: 0, y: 0 })

const priorityType = computed(() => {
  const p = props.caseItem.priority
  if (p === "P0") return "danger"
  if (p === "P1") return "warning"
  return "info"
})

interface ContextMenuItem {
  label?: string
  icon?: object
  action?: () => void | Promise<void>
  divider?: boolean
  danger?: boolean
  disabled?: boolean
}

const contextMenuItems = computed<ContextMenuItem[]>(() => [
  { label: "运行", icon: Play, action: runCase },
  { label: "编辑", icon: Edit, action: onOpenCase },
  { label: "复制", icon: Copy, action: copyCase },
  { divider: true },
  {
    label: props.caseItem.status === "disabled" ? "启用" : "禁用",
    icon: props.caseItem.status === "disabled" ? CheckCircle : XCircle,
    action: toggleCaseStatus,
  },
  { divider: true },
  { label: "删除", icon: Trash2, danger: true, action: deleteCase },
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

function onOpenCase() {
  tabsStore.addTab({
    key: `case-${props.caseItem.id}`,
    label: props.caseItem.name,
    type: "case",
    caseId: props.caseItem.id,
    closable: true,
    projectId: props.projectId,
  })
  void router.push(`/projects/${props.projectId}/apis/case/${props.caseItem.id}`)
}

function runCase() {
  msgInfo("单用例执行功能开发中")
}

function copyCase() {
  msgInfo("复制功能开发中")
}

async function toggleCaseStatus() {
  const newStatus = props.caseItem.status === "disabled" ? "active" : "disabled"
  try {
    await request.put(`/projects/${props.projectId}/cases/${props.caseItem.id}`, {
      status: newStatus,
    })
    msgSuccess(newStatus === "disabled" ? "用例已禁用" : "用例已启用")
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
  } catch (err) {
    logger.error('[CaseNode] toggle case status failed:', err)
    // Error handled by interceptor
  }
}

async function deleteCase() {
  if (!(await requireLogin('删除用例'))) return
  try {
    await ElMessageBox.confirm(`确定要删除用例"${props.caseItem.name}"吗？`, "确认删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
    await request.delete(`/projects/${props.projectId}/cases/${props.caseItem.id}`)
    msgSuccess("用例已删除")
    apiStore.clearCache()
    await apiStore.fetchCategories(props.projectId)
  } catch (err) {
    logger.error('[CaseNode] delete case failed:', err)
    // cancelled or error handled by interceptor
  }
}

function caseTypeLabel(type?: string) {
  const map: Record<string, string> = {
    positive: "正向",
    negative: "负向",
    boundary: "边界值",
    security: "安全性",
    other: "其他",
  }
  return map[type || "other"] || type || "其他"
}
</script>

<style scoped>
/* ===== 用例节点容器 - 扁平设计，清晰层级 ===== */
.case-node {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  border-radius: var(--radius-md);
  margin: var(--space-0-5) var(--space-2);
  min-height: var(--height-row-compact);
  box-sizing: border-box;
  transition: var(--transition-fast);
  position: relative;
}

/* 左侧选中指示条 */
.case-node::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 16px;
  border-radius: 0 3px 3px 0;
  background: var(--primary-500);
  transition: transform var(--duration-fast) var(--ease-spring);
}

.case-node:hover {
  background: var(--surface-hover);
  transform: translateX(2px);
}

.case-node:hover .case-name {
  color: var(--text-primary);
}

.case-node:active {
  transform: translateX(0);
}

.case-node.selected {
  background: var(--color-primary-alpha-10);
}

.case-node.selected::before {
  transform: translateY(-50%) scaleY(1);
}

.case-node.selected .case-name {
  color: var(--primary-700);
  font-weight: var(--weight-semibold);
}

/* ===== 优先级标签 ===== */
.case-priority {
  flex-shrink: 0;
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  padding: 2px var(--space-1-5);
  border-radius: var(--radius-sm);
  line-height: 1.4;
  transition: var(--transition-fast);
}

.case-node:hover .case-priority {
  transform: scale(1.02);
}

/* ===== 用例名称 ===== */
.case-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: var(--transition-fast);
}

/* ===== 用例类型徽章 ===== */
.case-type-badge {
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  line-height: 1.4;
  transition: var(--transition-fast);
}

.case-node:hover .case-type-badge {
  transform: scale(1.02);
}

/* 类型颜色变体 */
.type-positive {
  background: var(--success-bg);
  color: var(--success-text);
  border: 1px solid var(--success-border);
}

.type-negative {
  background: var(--error-bg);
  color: var(--error-text);
  border: 1px solid var(--error-border);
}

.type-boundary {
  background: var(--info-bg);
  color: var(--info-text);
  border: 1px solid var(--info-border);
}

.type-security {
  background: var(--purple-bg);
  color: var(--purple-text);
  border: 1px solid var(--color-primary-alpha-18);
}

.type-other {
  background: var(--surface-hover);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

/* ===== 暗色模式适配 ===== */
html.dark .case-node:hover {
  background: var(--surface-hover);
}

html.dark .case-node:hover .case-name {
  color: var(--text-primary);
}

html.dark .case-node.selected {
  background: var(--color-primary-alpha-12);
}

html.dark .case-node.selected::before {
  background: var(--primary-400);
}

html.dark .case-node.selected .case-name {
  color: var(--primary-400);
}

html.dark .case-name {
  color: var(--text-secondary);
}

html.dark .type-positive {
  background: var(--success-bg);
  color: var(--success-text);
  border-color: var(--success-border);
}

html.dark .type-negative {
  background: var(--error-bg);
  color: var(--error-text);
  border-color: var(--error-border);
}

html.dark .type-boundary {
  background: var(--info-bg);
  color: var(--info-text);
  border-color: var(--info-border);
}

html.dark .type-security {
  background: var(--purple-bg);
  color: var(--purple-text);
  border-color: var(--color-purple-alpha-18);
}

html.dark .type-other {
  background: var(--surface-hover);
  color: var(--text-muted);
  border-color: var(--border-subtle);
}
</style>
