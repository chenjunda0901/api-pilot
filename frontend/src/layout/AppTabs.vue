<template>
  <div class="tabs-bar" v-if="tabsStore.tabs.length > 0">
    <!-- Left scroll arrow -->
    <button class="scroll-btn left" @click="scrollTabs(-200)" v-if="showScrollLeft">
      &lsaquo;
    </button>

    <div class="tabs-container" ref="tabsContainerRef">
      <div
        v-for="tab in tabsStore.tabs"
        :key="tab.key"
        class="tab-item"
        tabindex="0"
        role="tab"
        :class="{
          active: tabsStore.activeTab === tab.key,
          'is-leaving': leavingKey === tab.key,
          'tab-api': tab.type === 'api',
          'tab-case': tab.type === 'case',
        }"
        @click="switchTab(tab)"
        @keydown.enter="switchTab(tab)"
        @contextmenu.prevent="onContextMenu($event, tab)"
      >
        <span v-if="tab.method" class="tab-method" :class="tab.method.toLowerCase()">{{
          tab.method
        }}</span>
        <span v-if="tabsStore.isDirty(tab.key)" class="tab-dirty-dot" title="未保存"></span>
        <template v-if="tab.editableName">
          <input
            class="tab-label-input"
            :value="tab.label"
            :placeholder="'新接口'"
            @input="onTabLabelInput(tab, ($event.target as HTMLInputElement).value)"
            @keydown.enter="(e) => (e.target as HTMLInputElement).blur()"
            @click.stop
          />
        </template>
        <template v-else>
          <span class="tab-label" :title="tab.label">{{ truncateLabel(tab.label) }}</span>
        </template>
        <span v-if="tab.closable && !tab.pinned" class="tab-close" @click.stop="closeTab(tab)">&times;</span>
      </div>
    </div>

    <!-- Right scroll arrow -->
    <button class="scroll-btn right" @click="scrollTabs(200)" v-if="showScrollRight">
      &rsaquo;
    </button>

    <!-- Context menu -->
    <Teleport to="body">
      <div
        class="tab-context-menu"
        v-if="contextMenu.visible"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      >
        <!-- prettier-ignore -->
        <div
          class="ctx-item"
          @click="closeTab(contextMenu.tab); contextMenu.visible = false"
          tabindex="0"
          role="menuitem"
          @keydown.enter="closeTab(contextMenu.tab)"
        >
          关闭当前
        </div>
        <!-- prettier-ignore -->
        <div
          class="ctx-item"
          @click="tabsStore.closeOthers(contextMenu.tab.key); contextMenu.visible = false"
          tabindex="0"
          role="menuitem"
          @keydown.enter="tabsStore.closeOthers(contextMenu.tab.key)"
        >
          关闭其他
        </div>
        <!-- prettier-ignore -->
        <div
          class="ctx-item"
          @click="tabsStore.closeRight(contextMenu.tab.key); contextMenu.visible = false"
          tabindex="0"
          role="menuitem"
          @keydown.enter="tabsStore.closeRight(contextMenu.tab.key)"
        >
          关闭右侧
        </div>
        <!-- prettier-ignore -->
        <div
          class="ctx-item"
          @click="closeAllTabs(); contextMenu.visible = false"
          tabindex="0"
          role="menuitem"
          @keydown.enter="closeAllTabs()"
        >
          关闭所有
        </div>
        <div class="ctx-divider"></div>
        <!-- prettier-ignore -->
        <div
          class="ctx-item"
          @click="copyApiUrl(contextMenu.tab); contextMenu.visible = false"
          tabindex="0"
          role="menuitem"
          @keydown.enter="copyApiUrl(contextMenu.tab)"
        >
          复制接口 URL
        </div>
        <div class="ctx-divider"></div>
        <div
          class="ctx-item"
          @click="togglePin(contextMenu.tab)"
          tabindex="0"
          role="menuitem"
          @keydown.enter="togglePin(contextMenu.tab)"
        >
          {{ contextMenu.tab.pinned ? "取消固定" : "固定标签" }}
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from "vue"
import { useEnvStore } from "../stores/envStore"
import { msgSuccess } from "../utils/message"
import { useRouter, useRoute } from "vue-router"
import { useTabsStore } from "../stores/tabsStore"
import { usePendingApiStore } from "../stores/pendingApiStore"
import type { TabItem } from "../types"

import { useEditorStore } from "../stores/editorStore"
import request from "../api/request"

// Track setTimeout for cleanup
const leavingTimerRef = ref<ReturnType<typeof setTimeout> | null>(null)
import { ElMessageBox } from "element-plus"
import { CONFIRM } from "../constants/messages"
import { logger } from "@/utils/logger"

const router = useRouter()
const route = useRoute()
const tabsStore = useTabsStore()
const { updatePendingNewApiName, removePendingNewApi } = usePendingApiStore()
const editorStore = useEditorStore()
const envStore = useEnvStore()
const projectId = computed(() => Number(route.params.id))

const tabsContainerRef = ref<HTMLElement | null>(null)

const showScrollLeft = ref(false)
const showScrollRight = ref(false)

// 旧标签下沉动画：记录切换前 active key，给其打上 is-leaving 类
const prevActiveKey = ref<string | null>(null)
const leavingKey = ref<string | null>(null)
watch(
  () => tabsStore.activeTab,
  (newKey) => {
    if (prevActiveKey.value && prevActiveKey.value !== newKey) {
      const oldKey = prevActiveKey.value
      leavingKey.value = oldKey
      // 280ms 后清除 leaving 状态（与 tabSlideOut 时长对齐）
      if (leavingTimerRef.value) clearTimeout(leavingTimerRef.value)
      leavingTimerRef.value = setTimeout(() => {
        if (leavingKey.value === oldKey) leavingKey.value = null
      }, 280)
    }
    prevActiveKey.value = newKey
    void nextTick()
  }
)

const contextMenu = ref<{ visible: boolean; x: number; y: number; tab: TabItem }>({
  visible: false,
  x: 0,
  y: 0,
  tab: { key: "", label: "", type: "api", closable: true },
})



async function switchTab(tab: TabItem) {
  // Dirty check：如果有未保存编辑，确认后再切换
  if (editorStore.dirty) {
    try {
      await ElMessageBox.confirm(CONFIRM.DISCARD_CHANGES.message, CONFIRM.DISCARD_CHANGES.title, {
        type: "warning",
        confirmButtonText: CONFIRM.DISCARD_CHANGES.confirmText,
        cancelButtonText: CONFIRM.DISCARD_CHANGES.cancelText,
      })
      // 用户点击"放弃更改" → 清除脏标记继续切换
      editorStore.markSaved()
    } catch {
      return // 用户点击"取消" → 阻止切换
    }
  }

  tabsStore.activeTab = tab.key
  switch (tab.type) {
    case "api":
      if (tab.apiId) {
        void router.push(`/projects/${route.params.id}/apis/detail/${tab.apiId}`)
      } else {
        void router.push(`/projects/${route.params.id}/apis/detail/new`)
      }
      break
    case "case":
      void router.push(`/projects/${route.params.id}/apis/case/${tab.caseId}`)
      break
    default:
      void router.push(tab.key)
  }
}

function truncateLabel(label: string, max = 20) {
  return label.length > max ? label.slice(0, max) + "..." : label
}

function onTabLabelInput(tab: TabItem, value: string) {
  tabsStore.updateTabLabel(tab.key, value)
  if (tab.categoryId) {
    updatePendingNewApiName(tab.categoryId, value)
  }
}

function scrollTabs(offset: number) {
  if (tabsContainerRef.value) {
    tabsContainerRef.value.scrollBy({ left: offset, behavior: "smooth" })
  }
}

function updateScrollButtons() {
  const el = tabsContainerRef.value
  if (el) {
    showScrollLeft.value = el.scrollLeft > 4
    showScrollRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4
  }
}

// 节流：scroll 事件每秒最多更新 2 次，防止滚动时过度重渲染
let scrollRaf = false
function onTabsScroll() {
  if (!scrollRaf) {
    scrollRaf = true
    requestAnimationFrame(() => {
      updateScrollButtons()
      scrollRaf = false
    })
  }
}

function onContextMenu(e: MouseEvent, tab: TabItem) {
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, tab }
}

/** 所有标签关闭后导航到空路由，确保刷新不会恢复标签 */
function navigateToEmpty() {
  const projectId = route.params.id
  if (projectId) {
      router.push(`/projects/${projectId}/apis`).catch(() => { logger.warn('[AppTabs] navigateToEmpty failed') })
  }
}

/** 导航到当前活跃标签对应的路由 */
function navigateToActiveTab() {
  const active = tabsStore.tabs.find((t) => t.key === tabsStore.activeTab)
  if (!active) return
  const projectId = route.params.id
  if (!projectId) return
  if (active.type === "api" && active.apiId) {
    router.push(`/projects/${projectId}/apis/detail/${active.apiId}`).catch(() => { logger.warn('[AppTabs] navigateToActiveTab failed') })
  } else if (active.type === "case" && active.caseId) {
    router.push(`/projects/${projectId}/apis/case/${active.caseId}`).catch(() => {})
  }
}

async function closeTab(tab: TabItem) {
  // 未保存检查
  if (editorStore.dirty) {
    try {
      await ElMessageBox.confirm(CONFIRM.DISCARD_CHANGES.message, CONFIRM.DISCARD_CHANGES.title, {
        type: "warning",
        confirmButtonText: CONFIRM.DISCARD_CHANGES.confirmText,
        cancelButtonText: CONFIRM.DISCARD_CHANGES.cancelText,
      })
      editorStore.markSaved()
    } catch {
      return
    }
  }
  // 关闭新接口标签时，同步删除目录内占位
  if (tab.key === "api-new" && tab.categoryId) {
    removePendingNewApi(tab.categoryId)
  }
  const allClosed = tabsStore.removeTab(tab.key)
  contextMenu.value.visible = false
  if (allClosed) {
    navigateToEmpty()
  } else {
    // 导航到新活跃标签对应的路由，保持左侧选中态同步
    navigateToActiveTab()
  }
}

async function closeAllTabs() {
  const hasDirty = editorStore.dirty
  if (hasDirty && editorStore.dirty) {
    try {
      await ElMessageBox.confirm(CONFIRM.DISCARD_CHANGES.message, CONFIRM.DISCARD_CHANGES.title, {
        type: "warning",
        confirmButtonText: CONFIRM.DISCARD_CHANGES.confirmText,
        cancelButtonText: CONFIRM.DISCARD_CHANGES.cancelText,
      })
      editorStore.markSaved()
    } catch {
      return
    }
  }
  const allClosed = tabsStore.closeAll()
  contextMenu.value.visible = false
  if (allClosed) navigateToEmpty()
}

async function copyApiUrl(tab: TabItem) {
  if (tab.type === "api" && tab.apiId) {
    try {
      const res = await request.get(`/projects/${route.params.id}/apis/${tab.apiId}`)
      const api = res.data
      void navigator.clipboard
        .writeText(`${api.method} ${api.path}`)
        .then(() => msgSuccess("接口 URL 已复制"))
    } catch (err) {
      logger.warn('[AppTabs] copyApiUrl failed:', err)
    }
  }
}

function togglePin(tab: TabItem) {
  if (tab.pinned)
    (
      tabsStore as unknown as { unpinTab: (k: string) => void; pinTab: (k: string) => void }
    ).unpinTab(tab.key)
  else
    (tabsStore as unknown as { unpinTab: (k: string) => void; pinTab: (k: string) => void }).pinTab(
      tab.key
    )
  contextMenu.value.visible = false
}

// Sync route → tabs (API/Case only)
watch(
  () => route.path,
  (path) => {
    const isDetailOrCase = /\/apis\/(detail|case)\//.test(path)
    if (!isDetailOrCase) return

    if (tabsStore.isCleared() && tabsStore.tabs.length === 0) {
      const projectId = route.params.id
      if (projectId) router.replace(`/projects/${projectId}/apis`).catch(() => {})
      return
    }

    const newApiMatch = path.match(/\/apis\/detail\/new$/)
    if (newApiMatch) {
      if (!tabsStore.tabs.find((t) => t.key === "api-new")) {
        tabsStore.addTab({
          key: "api-new",
          label: "新接口",
          type: "api",
          method: "GET",
          closable: true,
          editableName: true,
          projectId,
        })
      } else {
        tabsStore.activeTab = "api-new"
      }
      return
    }

    const apiMatch = path.match(/\/apis\/detail\/(\d+)$/)
    if (apiMatch) {
      const apiId = Number(apiMatch[1])
      const key = `api-${apiId}`
      if (tabsStore.tabs.find((t) => t.key === key)) {
        tabsStore.activeTab = key
      }
      return
    }

    const caseMatch = path.match(/\/apis\/case\/(\d+)$/)
    if (caseMatch) {
      const caseId = Number(caseMatch[1])
      const key = `case-${caseId}`
      if (tabsStore.tabs.find((t) => t.key === key)) {
        tabsStore.activeTab = key
      }
    }
  },
  { immediate: true }
)

function onGlobalClick() {
  contextMenu.value.visible = false
}

onMounted(async () => {
  window.addEventListener("click", onGlobalClick as EventListener)
  tabsContainerRef.value?.addEventListener("scroll", onTabsScroll, { passive: true })
  updateScrollButtons()
  await reloadEnvData()
})
onUnmounted(() => {
  window.removeEventListener("click", onGlobalClick as EventListener)
  tabsContainerRef.value?.removeEventListener("scroll", onTabsScroll)
  if (leavingTimerRef.value) clearTimeout(leavingTimerRef.value)
})

// 监听项目 ID 变化，切换项目后重新加载环境
watch(
  () => route.params.id,
  async (newId) => {
    if (newId) await reloadEnvData()
  }
)

async function reloadEnvData() {
  const pid = projectId.value
  if (!pid) return
  try {
    await envStore.fetchEnvs(pid)
    await envStore.fetchGlobalConfig(pid)
  } catch (err) {
    logger.warn('[AppTabs] reloadEnvData failed:', err)
  }
}
</script>

<style scoped>
/* 全局定位样式（右键菜单 fixed 定位） */
:global(.tab-context-menu) {
  position: fixed;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-drag);
  padding: var(--space-1-5);
  z-index: var(--z-max);
  min-width: 160px;
  animation: ctx-menu-in var(--duration-fast) var(--ease-out-expo);
}

@keyframes ctx-menu-in {
  from {
    opacity: 0;
    transform: translateY(-1px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

:global(.ctx-item) {
  display: flex;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition:
    background var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
}
:global(.ctx-item:hover) {
  background: var(--color-primary-alpha-06);
  color: var(--text-primary);
}
:global(.ctx-divider) {
  height: 1px;
  background: var(--border-subtle);
  margin: var(--space-1-5) var(--space-1-5);
}

.tabs-bar {
  display: flex;
  align-items: center;
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  position: relative;
  height: var(--height-tabs);
  padding: 0 var(--space-2);
}

.scroll-btn {
  flex-shrink: 0;
  width: 20px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: var(--text-lg);
  cursor: pointer;
  z-index: var(--z-base);
  transition:
    color 160ms var(--ease-smooth),
    background-color 160ms var(--ease-smooth),
    opacity 160ms var(--ease-smooth),
    box-shadow 160ms var(--ease-smooth),
    transform 160ms var(--ease-smooth);
}
.scroll-btn:hover {
  color: var(--primary-600);
  background: color-mix(in srgb, var(--primary-500) 6%, var(--surface-hover) 94%);
  box-shadow: inset 0 1px 0 var(--color-white-alpha-18);
}
.scroll-btn.left {
  border-right: 1px solid var(--border-subtle);
}
.scroll-btn.right {
  border-left: 1px solid var(--border-subtle);
}

.tabs-container {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  flex: 1;
  min-width: 0;
  scrollbar-width: none;
  contain: layout style;
  will-change: scroll-position;
}
.tabs-container::-webkit-scrollbar {
  display: none;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  height: var(--height-tabs);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  position: relative;
  margin: 0 1px;
  transition: color var(--duration-fast) var(--ease-smooth), background-color var(--duration-fast) var(--ease-smooth);
  user-select: none;
}

.tab-item:hover {
  color: var(--text-secondary);
  background: var(--surface-hover);
}

.tab-item.active {
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
  background: var(--surface-selected);
  animation: tabSlideIn 250ms var(--ease-spring) both;
}
/* 底部激活指示条 */
.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: var(--space-2);
  right: var(--space-2);
  height: 2px;
  background: var(--grad-primary);
  border-radius: var(--radius-full) var(--radius-full) 0 0;
  animation: tabIndicatorIn 250ms var(--ease-out-expo) both;
}
@keyframes tabIndicatorIn {
  from { transform: scaleX(0); opacity: 0; }
  to { transform: scaleX(1); opacity: 1; }
}
.tab-item.active .tab-method {
  box-shadow: 0 1px 2px var(--color-black-alpha-06);
}

/* 旧标签下沉淡出 */
.tab-item.is-leaving {
  animation: tabSlideOut 240ms var(--ease-soft) both;
  pointer-events: none;
}

.tab-item.active .tab-label {
  color: var(--primary-600);
}
.tab-browsing {
  font-weight: var(--weight-normal);
}
.tab-editing {
  font-style: normal;
  font-weight: var(--weight-semibold);
}

.tab-close {
  font-size: var(--text-base);
  line-height: 1;
  color: var(--text-disabled);
  transition: all var(--duration-fast) var(--ease-smooth);
  border-radius: var(--radius-2xs);
  padding: 4px;
  margin-left: 4px;
  visibility: hidden;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tab-item:hover .tab-close,
.tab-item.active .tab-close {
  visibility: visible;
}
.tab-close:hover {
  color: var(--color-error);
  background: var(--color-error-alpha-08);
}

.tab-method {
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  padding: 2px var(--space-1-5);
  border-radius: var(--radius-2xs);
  line-height: 1.3;
  letter-spacing: 0.03em;
}
.tab-method.get {
  background: var(--method-get-bg);
  color: var(--method-get-text);
}
.tab-method.post {
  background: var(--method-post-bg);
  color: var(--method-post-text);
}
.tab-method.put {
  background: var(--method-put-bg);
  color: var(--method-put-text);
}
.tab-method.delete {
  background: var(--method-delete-bg);
  color: var(--method-delete-text);
}
.tab-method.patch {
  background: var(--method-patch-bg);
  color: var(--method-patch-text);
}

.tab-dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-warning);
  flex-shrink: 0;
  animation: dirtyPulse 2s ease-in-out infinite;
}
@keyframes dirtyPulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.tab-label {
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tab-label-input {
  width: 100px;
  border: none;
  border-bottom: 1px solid var(--primary-400);
  background: transparent;
  color: var(--text-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  padding: 1px 2px;
  outline: none;
  border-radius: 0;
  box-shadow: none;
  transition: border-color var(--duration-fast);
}
.tab-label-input:focus {
  border-bottom-color: var(--primary-500);
}

.env-switcher {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  padding-right: 6px;
  height: 100%;
}

.env-refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition:
    color var(--duration-fast) var(--ease-smooth),
    background var(--duration-fast) var(--ease-smooth);
}
.env-refresh-btn:hover {
  color: var(--primary-500);
  background: var(--surface-selected);
}

.env-trigger {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 var(--space-2-5);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition:
    background var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth);
  height: 100%;
}
.env-trigger:hover {
  background: var(--surface-selected);
  color: var(--text-primary);
}
.env-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.env-trigger svg {
  color: var(--text-muted);
  transition: color var(--duration-fast) var(--ease-smooth);
}
.env-trigger:hover svg {
  color: var(--primary-500);
}

.env-dropdown-menu {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float), 0 0 0 1px var(--border-subtle);
  min-width: 180px;
  padding: var(--sp-2);
  animation: env-menu-in 0.15s var(--ease-out-expo);
  max-height: 260px;
  overflow-y: auto;
}
@keyframes env-menu-in {
  from {
    opacity: 0;
    transform: translateY(-1px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.env-list-scroll {
  max-height: 200px;
  overflow-y: auto;
}

.env-item {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-2) var(--space-2-5);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition:
    background var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth);
}
.env-item:hover {
  background: var(--color-primary-alpha-06);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
}
.env-item.active {
  background: var(--color-primary-alpha-08);
  color: var(--primary-700);
  font-weight: var(--weight-semibold);
}
.env-item.active::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-500);
  flex-shrink: 0;
  box-shadow: 0 0 0 2px var(--color-primary-alpha-15);
}
.env-manage {
  color: var(--text-muted);
  justify-content: center;
  margin-top: 2px;
  font-size: var(--text-xs);
}
.env-manage:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.env-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: var(--space-1-5) var(--space-1);
}

html.dark .tabs-bar {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}
html.dark .tab-item {
  color: var(--text-muted);
}
html.dark .tab-item:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}
html.dark .tab-item.active {
  background: var(--surface-selected);
  color: var(--primary-400);
}
html.dark .scroll-btn {
  color: var(--text-muted);
}
html.dark .scroll-btn:hover {
  background: color-mix(in srgb, var(--surface-hover) 92%, var(--primary-500) 8%);
  color: var(--text-primary);
}

/* ===== 移动端 (< 768px)：Tab 栏从顶部切换到底部 ===== */
@media (max-width: 767px) {
  .tabs-bar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    top: auto;
    height: 48px;
    border-top: 1px solid var(--border-subtle);
    border-bottom: none;
    padding: 0 var(--space-1);
    z-index: var(--z-fixed, 100);
    background: var(--surface-card);
    box-shadow: 0 -2px 12px var(--color-black-alpha-04);
  }
  .tabs-container {
    gap: 1px;
  }
  .tab-item {
    height: 40px;
    padding: 0 var(--space-2);
    font-size: var(--text-xs);
    flex: 1 1 auto;
    min-width: 0;
    justify-content: center;
  }
  .scroll-btn {
    display: none;
  }
  .tab-label {
    max-width: 80px;
  }
  /* 暗色下边框颜色修正 */
  html.dark .tabs-bar {
    border-top-color: var(--border-subtle);
  }
}
</style>

<!-- Unscoped styles for context menu (teleported to body) -->
