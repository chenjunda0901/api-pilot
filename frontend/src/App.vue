<template>
  <el-config-provider :locale="elementLocale">
    <LoadingBar />
    <a href="#main-content" class="skip-link">跳到主要内容</a>
    <ErrorBoundary>
      <Suspense>
        <template #default>
          <router-view v-slot="{ Component, route }">
            <KeepAlive :include="keepAliveRoutes" :max="5">
              <Transition :name="route.meta.transition || 'fade'" mode="out-in">
                <component :is="Component" :key="route.path" />
              </Transition>
            </KeepAlive>
          </router-view>
        </template>
        <template #fallback>
          <div class="route-skeleton-wrapper">
            <RouteSkeleton />
          </div>
        </template>
      </Suspense>
    </ErrorBoundary>
    <CommandPalette :visible="showCommandPalette" @close="showCommandPalette = false" />
    <HotkeyHelp v-model:visible="showHotkeyHelp" />

  </el-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import en from 'element-plus/dist/locale/en.mjs'
import { useI18n } from 'vue-i18n'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import LoadingBar from './components/LoadingBar.vue'
import CommandPalette from './components/CommandPalette.vue'
import HotkeyHelp from './components/common/HotkeyHelp.vue'
import RouteSkeleton from '@/components/common/RouteSkeleton.vue'

import { useGlobalShortcuts } from './composables/useShortcuts'
import { useKeyboardShortcuts } from './composables/useKeyboardShortcuts'
import { useTabsStore } from './stores/tabsStore'
import { useEditorStore } from './stores/editorStore'

const showCommandPalette = ref(false)
const showHotkeyHelp = ref(false)
const tabsStore = useTabsStore()
const editorStore = useEditorStore()

/** 高频访问路由列表（KeepAlive 缓存） */
const keepAliveRoutes = ['Dashboard', 'Apis', 'Scenes', 'Reports', 'MockRules']

const { locale: i18nLocale } = useI18n()
const elementLocale = computed(() => {
  return i18nLocale.value === 'en' ? en : zhCn
})

/** Global keyboard shortcuts */
const handleKeydown = (e: KeyboardEvent) => {
  const mod = e.ctrlKey || e.metaKey
  // Ctrl+K → Command Palette
  if (mod && !e.shiftKey && e.key === 'k') {
    e.preventDefault()
    showCommandPalette.value = !showCommandPalette.value
  }
  // Ctrl+Shift+K → Quick Search (also opens command palette with focus on search)
  if (mod && e.shiftKey && e.key === 'K') {
    e.preventDefault()
    showCommandPalette.value = true
  }
  // Ctrl+Shift+F → Global Search (opens command palette)
  if (mod && e.shiftKey && e.key === 'F') {
    e.preventDefault()
    showCommandPalette.value = true
  }
}

// 监听自定义事件
const handleAppEvents = (e: Event) => {
  const ce = e as CustomEvent
  switch (ce.type) {
    case 'app:quick-jump':
      showCommandPalette.value = !showCommandPalette.value
      break
    case 'app:quick-search':
    case 'app:global-search':
      showCommandPalette.value = true
      break
    case 'app:shortcut-help':
      showHotkeyHelp.value = !showHotkeyHelp.value
      break
    case 'app:escape':
      if (showCommandPalette.value) showCommandPalette.value = false
      if (showHotkeyHelp.value) showHotkeyHelp.value = false
      break
  }
}

/** 会话即将过期提示（带防抖，5 分钟内只提示一次） */
let _sessionExpiringShown = false
const handleSessionExpiring = () => {
  if (_sessionExpiringShown) return
  _sessionExpiringShown = true
  setTimeout(() => { _sessionExpiringShown = false }, 5 * 60 * 1000)
  import("element-plus").then(mod => {
    mod.ElMessage.warning("会话即将过期")
  }).catch(() => { /* ignore dynamic import failure */ })
}
useGlobalShortcuts()
useKeyboardShortcuts()

/** Warn user before closing browser if there are unsaved changes */
const handleBeforeUnload = (e: BeforeUnloadEvent) => {
  const hasDirtyTabs = Array.from(tabsStore.dirtyTabs).length > 0
  const hasEditorChanges = editorStore.dirty

  if (hasDirtyTabs || hasEditorChanges) {
    e.preventDefault()
    e.returnValue = '您有未保存的更改，确定要离开吗？'
    return e.returnValue
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('beforeunload', handleBeforeUnload)
  // 监听自定义事件
  window.addEventListener('app:quick-jump', handleAppEvents)
  window.addEventListener('app:quick-search', handleAppEvents)
  window.addEventListener('app:global-search', handleAppEvents)
  window.addEventListener('app:shortcut-help', handleAppEvents)
  window.addEventListener('app:escape', handleAppEvents)
  window.addEventListener('session-expiring', handleSessionExpiring)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  window.removeEventListener('app:quick-jump', handleAppEvents)
  window.removeEventListener('app:quick-search', handleAppEvents)
  window.removeEventListener('app:global-search', handleAppEvents)
  window.removeEventListener('app:shortcut-help', handleAppEvents)
  window.removeEventListener('app:escape', handleAppEvents)
  window.removeEventListener('session-expiring', handleSessionExpiring)
})
</script>

<style>
/* ===== 全局页面过渡动画 ===== */

/* 统一 fade 过渡（默认路由切换） */
.fade-enter-active {
  transition: opacity var(--duration-fast) var(--ease-out),
              transform var(--duration-fast) var(--ease-out);
  will-change: transform, opacity;
}
.fade-leave-active {
  transition: opacity calc(var(--duration-fast) * 0.6) var(--ease-in),
              transform calc(var(--duration-fast) * 0.6) var(--ease-in);
  will-change: transform, opacity;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(3px);
}
.fade-leave-to {
  opacity: 0;
}

/* page-fade 页面级淡入淡出 */
.page-fade-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out);
  will-change: transform, opacity;
}
.page-fade-leave-active {
  transition: opacity calc(var(--duration-base) * 0.6) var(--ease-in),
              transform calc(var(--duration-base) * 0.6) var(--ease-in);
  will-change: transform, opacity;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 路由切换动画 — 幻灯片式 */
.slide-fade-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out);
  will-change: transform, opacity;
}
.slide-fade-leave-active {
  transition: opacity calc(var(--duration-base) * 0.6) var(--ease-in),
              transform calc(var(--duration-base) * 0.6) var(--ease-in);
  will-change: transform, opacity;
}
.slide-fade-enter-from {
  opacity: 0;
  transform: translateX(12px);
}
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

/* Dashboard 专用过渡 */
.route-dashboard-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out),
              filter var(--duration-base) var(--ease-out);
  will-change: transform, opacity, filter;
}
.route-dashboard-leave-active {
  transition: opacity calc(var(--duration-base) * 0.6) var(--ease-in),
              transform calc(var(--duration-base) * 0.6) var(--ease-in);
  will-change: transform, opacity;
}
.route-dashboard-enter-from {
  opacity: 0;
  transform: scale(0.97);
  filter: blur(1px);
}
.route-dashboard-leave-to {
  opacity: 0;
  transform: scale(1.02);
}

/* API/场景 页面过渡 */
.route-api-enter-active,
.route-scenes-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out);
  will-change: transform, opacity;
}
.route-api-leave-active,
.route-scenes-leave-active {
  transition: opacity calc(var(--duration-base) * 0.6) var(--ease-in),
              transform calc(var(--duration-base) * 0.6) var(--ease-in);
  will-change: transform, opacity;
}
.route-api-enter-from,
.route-scenes-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.route-api-leave-to,
.route-scenes-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* Reports 页面过渡 */
.route-reports-enter-active {
  transition: opacity var(--duration-base) var(--ease-out),
              transform var(--duration-base) var(--ease-out);
  will-change: transform, opacity;
}
.route-reports-leave-active {
  transition: opacity calc(var(--duration-base) * 0.6) var(--ease-in);
  will-change: opacity;
}
.route-reports-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.route-reports-leave-to {
  opacity: 0;
}

/* 减弱动效 */
@media (prefers-reduced-motion: reduce) {
  .fade-enter-active,
  .fade-leave-active,
  .fade-enter-from,
  .fade-leave-to,
  .page-fade-enter-active,
  .page-fade-leave-active,
  .page-fade-enter-from,
  .page-fade-leave-to,
  .slide-fade-enter-active,
  .slide-fade-leave-active,
  .slide-fade-enter-from,
  .slide-fade-leave-to,
  .route-dashboard-enter-active,
  .route-dashboard-leave-active,
  .route-dashboard-enter-from,
  .route-dashboard-leave-to,
  .route-api-enter-active,
  .route-api-leave-active,
  .route-api-enter-from,
  .route-api-leave-to,
  .route-scenes-enter-active,
  .route-scenes-leave-active,
  .route-scenes-enter-from,
  .route-scenes-leave-to,
  .route-reports-enter-active,
  .route-reports-leave-active,
  .route-reports-enter-from,
  .route-reports-leave-to {
    transition: none !important;
    transform: none !important;
    filter: none !important;
    will-change: auto !important;
  }
}
</style>

<style scoped>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--primary-600);
  color: white;
  padding: var(--space-2) var(--space-4);
  z-index: var(--z-toast);
  font-size: var(--text-sm);
  text-decoration: none;
  border-radius: 0 0 8px 0;
  transition: top var(--duration-base);
}
.skip-link:focus {
  top: 0;
}
</style>