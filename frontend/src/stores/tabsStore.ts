import { defineStore } from "pinia"
import { ref, watch } from "vue"
import type { TabItem } from "../types"
import { usePendingApiStore } from "./pendingApiStore"

const STORAGE_KEYS = {
  TABS: "api_pilot_tabs",
  ACTIVE: "api_pilot_tabs_active",
  CLEARED: "api_pilot_tabs_cleared",  // 用户主动关闭所有标签的标记
} as const

function loadPersisted<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export const useTabsStore = defineStore("tabs", () => {
  const initialTabs = loadPersisted<TabItem[]>(STORAGE_KEYS.TABS, []).filter(
    t => t.key !== 'api-new' && t.key !== 'case-new' && (t.type === 'api' || t.type === 'case')
  )
  const tabs = ref<TabItem[]>(initialTabs)
  const activeTab = ref(initialTabs.some(t => t.key === loadPersisted<string>(STORAGE_KEYS.ACTIVE, "")) ? loadPersisted<string>(STORAGE_KEYS.ACTIVE, "") : "")
  const dirtyTabs = ref<Set<string>>(new Set())

  /* pendingNewApis 已迁移至 usePendingApiStore，此处不再维护重复状态 */

  watch(activeTab, (val) => {
    try { localStorage.setItem(STORAGE_KEYS.ACTIVE, val) } catch { /* localStorage unavailable */ }
  })

  function persistTabs() {
    try { localStorage.setItem(STORAGE_KEYS.TABS, JSON.stringify(tabs.value)) } catch { /* localStorage unavailable */ }
  }

  function addTab(tab: TabItem) {
    // 打开新标签时清除"已全部关闭"标记
    localStorage.removeItem(STORAGE_KEYS.CLEARED)
    // 注意：projectId 应由调用方在组件中传入，不再在此处调用 useRoute
    const existing = tabs.value.find((t) => t.key === tab.key)
    if (existing) {
      Object.assign(existing, tab)
      activeTab.value = tab.key
      persistTabs()
      return
    }
    tabs.value.push(tab)
    activeTab.value = tab.key
    persistTabs()
  }

  /** 关闭标签时同步清理目录内占位接口（委托 pendingApiStore 管理） */
  function cleanupPendingApi(tab: TabItem) {
    if (tab.key === "api-new" && tab.categoryId) {
      usePendingApiStore().removePendingNewApi(tab.categoryId)
    }
  }

  /** 返回 true 表示所有可关闭标签已关闭，调用方应导航到空状态路由 */
  function removeTab(key: string): boolean {
    const idx = tabs.value.findIndex((t) => t.key === key)
    if (idx === -1 || !tabs.value[idx].closable) return false
    cleanupPendingApi(tabs.value[idx])
    tabs.value.splice(idx, 1)
    dirtyTabs.value.delete(key)
    if (activeTab.value === key) {
      activeTab.value = tabs.value[Math.min(idx, tabs.value.length - 1)]?.key || ""
    }
    const empty = tabs.value.length === 0
    if (empty) localStorage.setItem(STORAGE_KEYS.CLEARED, '1')
    persistTabs()
    return empty
  }

  function updateTabKey(oldKey: string, newKey: string, updates: Partial<TabItem>) {
    const tab = tabs.value.find((t) => t.key === oldKey)
    if (tab) {
      const wasDirty = dirtyTabs.value.has(oldKey)
      if (wasDirty) {
        dirtyTabs.value.delete(oldKey)
        dirtyTabs.value.add(newKey)
      }
      Object.assign(tab, updates, { key: newKey })
      if (activeTab.value === oldKey) activeTab.value = newKey
      persistTabs()
    }
  }

  function updateTabLabel(key: string, label: string) {
    const tab = tabs.value.find((t) => t.key === key)
    if (tab) { tab.label = label; persistTabs() }
  }

  /** 返回 true 表示仅剩指定标签（或 pinned 标签） */
  function closeOthers(key: string): boolean {
    // 关闭前清理所有被关闭标签的占位接口
    tabs.value.filter((t) => t.key !== key && !t.pinned).forEach(cleanupPendingApi)
    tabs.value = tabs.value.filter((t) => t.key === key || t.pinned)
    dirtyTabs.value = new Set([...dirtyTabs.value].filter(k => k === key))
    activeTab.value = key
    const empty = tabs.value.length === 0
    if (empty) localStorage.setItem(STORAGE_KEYS.CLEARED, '1')
    persistTabs()
    return empty
  }

  function closeRight(key: string) {
    const idx = tabs.value.findIndex((t) => t.key === key)
    if (idx > -1) {
      const removed = tabs.value.slice(idx + 1).filter((t) => !t.pinned)
      removed.forEach(t => dirtyTabs.value.delete(t.key))
      tabs.value = tabs.value
        .slice(0, idx + 1)
        .concat(tabs.value.slice(idx + 1).filter((t) => t.pinned))
      persistTabs()
    }
  }

  /** 返回 true 表示所有可关闭标签已关闭 */
  function closeAll(): boolean {
    // 关闭前清理所有被关闭标签的占位接口
    tabs.value.filter(t => !t.pinned).forEach(cleanupPendingApi)
    tabs.value = tabs.value.filter(t => t.pinned)
    activeTab.value = tabs.value.length > 0 ? tabs.value[0].key : ""
    const empty = tabs.value.length === 0
    if (empty) localStorage.setItem(STORAGE_KEYS.CLEARED, '1')
    persistTabs()
    return empty
  }

  function reorderTabs(newOrder: TabItem[]) {
    tabs.value = newOrder
    persistTabs()
  }

  function markDirty(key: string) {
    dirtyTabs.value.add(key)
  }

  function markClean(key: string) {
    dirtyTabs.value.delete(key)
  }

  function isDirty(key: string) {
    return dirtyTabs.value.has(key)
  }

  /** 检查用户是否主动关闭了所有标签（用于刷新时判断是否恢复标签页） */
  function isCleared() {
    try { return localStorage.getItem(STORAGE_KEYS.CLEARED) === '1' } catch { return false }
  }

  function resetState() {
    tabs.value = []
    activeTab.value = ""
    dirtyTabs.value = new Set()
    try {
      localStorage.removeItem(STORAGE_KEYS.TABS)
      localStorage.removeItem(STORAGE_KEYS.ACTIVE)
      localStorage.setItem(STORAGE_KEYS.CLEARED, '1')
    } catch { /* localStorage unavailable */ }
  }

  return {
    tabs,
    activeTab,
    dirtyTabs,
    addTab,
    removeTab,
    updateTabKey,
    closeOthers,
    closeRight,
    closeAll,
    reorderTabs,
    markDirty,
    markClean,
    isDirty,
    isCleared,
    updateTabLabel,
    resetState,
  }
})
