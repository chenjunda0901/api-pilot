<template>
  <div class="app-layout">
    <Sidebar :collapsed="sidebarCollapsed" :class="{ open: mobileSidebarOpen }" @update:collapsed="onSidebarCollapsed" />
    <SidebarTree v-if="showSidebarTree" :project-id="projectId ?? 0" :class="{ open: mobileSidebarOpen }" />
    <div v-if="mobileSidebarOpen" class="sidebar-overlay" @click="mobileSidebarOpen = false" />
    <div class="main-area" :class="{ 'with-tree': showSidebarTree }">
      <TopBar @search="openSearch" @toggle-sidebar="mobileSidebarOpen = !mobileSidebarOpen" />
      <div class="layout-banners">
        <LoginHintBar />
        <ReadOnlyBanner />
      </div>
      <AppTabs v-if="showAppTabs" />
      <div v-if="showEmptyTabState" class="tab-empty-state">
        <div class="tab-empty-icon text-disabled">
          <svg
            viewBox="0 0 24 24"
            width="48"
            height="48"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
        </div>
        <h3 class="tab-empty-title">打开接口开始调试</h3>
        <p class="tab-empty-desc">从左侧接口目录树中选择一个接口，或创建新接口</p>
      </div>
      <div id="main-content" class="content" :class="{ 'content-loading': pageLoading, 'content-hidden': showEmptyTabState }">
        <div class="content-inner" :class="{ 'no-padding': showSidebarTree }">
          <BreadcrumbNav v-if="breadcrumbItems.length > 1" :items="breadcrumbItems" />
          <router-view v-slot="{ Component, route: currentRoute }">
            <Transition :name="transitionName" mode="out-in">
              <!-- 外层 div 确保 Transition 始终有单一根节点可动画 -->
              <div :key="currentRoute.name ?? currentRoute.fullPath" class="route-transition-wrapper">
                <component :is="Component" />
              </div>
            </Transition>
          </router-view>
        </div>
      </div>
      <StatusBar :running-info="runningSceneInfo" :current-env="envStore.currentEnv?.name" @open-recycle="handleOpenRecycle" />
    </div>
    <SearchDialog v-model:visible="searchVisible" :project-id="projectId ?? 0" />
    <ShortcutHelp :visible="shortcutHelpVisible" @close="shortcutHelpVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, provide, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTabsStore } from '@/stores/tabsStore'
import Sidebar from './Sidebar.vue'
import TopBar from './TopBar.vue'
import AppTabs from './AppTabs.vue'
import StatusBar from './StatusBar.vue'
import SearchDialog from '@/components/SearchDialog.vue'
import ShortcutHelp from '@/components/ShortcutHelp.vue'
import LoginHintBar from '@/components/LoginHintBar.vue'
import ReadOnlyBanner from '@/components/common/ReadOnlyBanner.vue'
import { msgWarning } from '@/utils/message'
import { useEnvStore } from '@/stores/envStore'
import { useProjectStore } from '@/stores/projectStore'
import { useTheme } from '@/composables/useTheme'

import SidebarTree from "@/components/SidebarTree.vue"
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import { useBreadcrumb } from '@/composables/useBreadcrumb'
import { useAppLoading } from '@/composables/useAppLoading'
import { useAppEvents } from '@/composables/useAppEvents'
import { useAppProjectWatcher } from '@/composables/useAppProjectWatcher'

// ── 职责拆分 composable ────────────────────────────────────────────
const { pageLoading, showLoading, hideLoading } = useAppLoading()
const { eventBus: _eventBus, runningSceneInfo } = useAppEvents()
const { projectId } = useAppProjectWatcher()
const { items: breadcrumbItems } = useBreadcrumb()

// ── UI 状态（保留在 Layout 层） ──────────────────────────────────
const envStore = useEnvStore()
const projectStore = useProjectStore()
const route = useRoute()
const router = useRouter()
const tabsStore = useTabsStore()
const { isDark } = useTheme()
provide('isDark', isDark)

const searchVisible = ref(false)
const shortcutHelpVisible = ref(false)
const SIDEBAR_STORAGE_KEY = 'api_pilot_sidebar_collapsed'
function _initSidebar(): boolean {
  try { return localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true' } catch { return false }
}
const sidebarCollapsed = ref(_initSidebar())
const mobileSidebarOpen = ref(false)
const SIDEBAR_BREAKPOINT = 992

const showSidebarTree = computed(() => route.path.includes('/apis') && !sidebarCollapsed.value)
const showAppTabs = computed(() => showSidebarTree.value && /\/apis\/(detail|case)\//.test(route.path))
const showEmptyTabState = computed(() => {
  if (!showSidebarTree.value) return false
  if (route.path === "/projects/" + String(route.params.id) + "/apis")
    return tabsStore.tabs.length === 0
  return false
})

// 首次加载触发 loading
showLoading()

const transitionName = computed(() => {
  const path = route.path
  if (path === "/dashboard") return "route-dashboard"
  if (path.includes("/apis")) return "route-api"
  if (path.includes("/scenes")) return "route-scenes"
  if (path.includes("/reports")) return "route-reports"
  return "fade"
})

// 响应式：小屏自动折叠 Sidebar
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  try { localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed.value)) } catch { /* localStorage 不可用 */ }
}

function onSidebarCollapsed(val: boolean) {
  sidebarCollapsed.value = val
  try { localStorage.setItem(SIDEBAR_STORAGE_KEY, String(val)) } catch {}
}

let autoCollapsed = false
let loadingTimer: ReturnType<typeof setTimeout> | null = null
function checkWindowWidth() {
  const width = window.innerWidth
  if (width < SIDEBAR_BREAKPOINT && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
    autoCollapsed = true
  } else if (width >= SIDEBAR_BREAKPOINT && autoCollapsed) {
    sidebarCollapsed.value = false
    autoCollapsed = false
  }
}

function handleOpenRecycle() {
  const pid = route.params.id || projectId.value
  if (pid) {
    void router.push(`/projects/${pid}/recycle-bin`)
  } else {
    msgWarning("请先选择一个项目")
  }
}

function openSearch() {
  searchVisible.value = true
}

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === "/") {
    e.preventDefault()
    shortcutHelpVisible.value = !shortcutHelpVisible.value
  }
}

onMounted(() => {
  window.addEventListener("keydown", onGlobalKeydown)
  window.addEventListener("resize", checkWindowWidth)
  checkWindowWidth()
  void projectStore.fetchProjects()
  loadingTimer = window.setTimeout(() => {
    hideLoading()
  }, 0)
})

const stopRouteTransition = router.afterEach((to) => {
  mobileSidebarOpen.value = false
  const appEl = document.getElementById("app")
  if (appEl) {
    appEl.style.viewTransitionName = (to.meta?.transition as string) || ""
  }
})

onUnmounted(() => {
  window.removeEventListener("keydown", onGlobalKeydown)
  window.removeEventListener("resize", checkWindowWidth)
  stopRouteTransition()
  if (loadingTimer) clearTimeout(loadingTimer)
})
</script>

<style scoped>
/* ── 应用整体布局 — Flex 横向布局 ──
 * 结构：Sidebar (240px/64px) | main-area (flex: 1)
 * main-area 内部：TopBar | LoginHintBar | AppTabs | content | StatusBar
 */
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--surface-page);
  color: var(--text-primary);
  position: relative;
  isolation: isolate;
  gap: 0;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--surface-bg);
  transition: background var(--duration-base) var(--ease-smooth),
    width 250ms ease-in-out;
  position: relative;
  z-index: 1;
}

.layout-banners {
  flex-shrink: 0;
  padding: 0 var(--space-4);
  padding-top: var(--space-3);
}
.main-area.with-tree {
}

.content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--surface-bg);
  scroll-behavior: smooth;
  position: relative;
}
.content-inner {
  width: 100%;
  margin: 0 auto;
  padding: var(--space-page) var(--space-page);
  background: var(--surface-bg);
  position: relative;
  min-height: 0;
  transition: opacity var(--duration-base) var(--ease-out);
}
.content-inner.no-padding {
  padding: 0;
}
.content-loading {
  opacity: 0.6;
  filter: blur(1px);
  pointer-events: none;
}
.content-hidden {
  display: none;
}

/* 空 tab 状态 */
.tab-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-4);
  padding: var(--space-10);
}
.tab-empty-icon {
  color: var(--text-disabled);
  opacity: 0.65;
}
.tab-empty-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0;
}
.tab-empty-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin: 0;
  text-align: center;
  max-width: 320px;
  line-height: 1.7;
}

html.dark .tab-empty-icon {
  color: var(--text-muted);
}
html.dark .tab-empty-title {
  color: var(--text-primary);
}
html.dark .tab-empty-desc {
  color: var(--text-muted);
}

/* ===== 响应式布局 ===== */
@media (max-width: 767px) {
  .content-inner {
    padding: var(--space-4) var(--space-3) var(--space-6);
  }
}

@media (max-width: 480px) {
  .content-inner {
    padding: var(--space-3) var(--space-2) var(--space-5);
  }
}

@media (max-width: 991px) {
  .sidebar-tree-panel {
    position: fixed;
    z-index: var(--z-dropdown);
    box-shadow: var(--shadow-xl);
  }
}
</style>