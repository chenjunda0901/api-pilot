<template>
  <!-- 侧边栏导航组件
    - 展开宽度: 240px
    - 折叠宽度: 64px
    - 过渡动画: 250ms ease-in-out
  -->
  <div class="sidebar" :class="{ collapsed }" role="navigation" aria-label="主导航">
    <router-link :to="RoutePaths.dashboard" class="logo" :class="{ collapsed }">
      <div class="logo-mark">
        <svg viewBox="0 0 20 20" fill="none" width="20" height="20" aria-hidden="true">
          <defs>
            <linearGradient id="logo-grad" x1="0" y1="0" x2="20" y2="20">
              <stop offset="0%" stop-color="var(--primary-500)" />
              <stop offset="100%" stop-color="var(--color-info)" />
            </linearGradient>
          </defs>
          <rect x="2" y="2" width="16" height="16" rx="4" fill="url(#logo-grad)" transform="rotate(45, 10, 10)" opacity="0.9" />
          <rect x="5" y="5" width="10" height="10" rx="2" fill="white" transform="rotate(45, 10, 10)" opacity="0.3" />
        </svg>
      </div>
      <transition name="fade-text">
        <span class="logo-text" v-if="!collapsed">API Pilot</span>
      </transition>
    </router-link>

    <nav class="nav sidebar-nav" aria-label="导航菜单">
      <!-- 通用 -->
      <div class="nav-group">
        <div class="nav-group-label" v-show="!collapsed">{{ $t('nav.common') }}</div>
        <router-link :to="RoutePaths.dashboard" class="nav-item" :aria-current="route.path === '/dashboard' ? 'page' : undefined" :class="{ active: route.path === '/dashboard' }" :title="collapsed ? $t('nav.dashboard') : ''">
          <LayoutDashboard :size="20" class="nav-icon" aria-hidden="true" />
          <span class="nav-label" v-show="!collapsed">{{ $t('nav.dashboard') }}</span>
          <transition name="fade-text">
            <span class="nav-badge" v-if="!collapsed"></span>
          </transition>
        </router-link>
      </div>

      <!-- 项目专属 -->
      <template v-if="projectId">
        <div class="nav-divider"></div>
        <div class="nav-group">
          <div class="nav-group-label" v-show="!collapsed">{{ $t('nav.project') }}</div>
          <router-link :to="RoutePaths.apiList(projectId)" class="nav-item sidebar-item-apis" @click="clearClearedForApis" :aria-current="route.path.includes('/apis') ? 'page' : undefined" :class="{ active: route.path.includes('/apis') }" :title="collapsed ? $t('nav.apis') : ''">
            <Plug :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.apis') }}</span>
          </router-link>
          <router-link :to="RoutePaths.scenes(projectId)" class="nav-item sidebar-item-scenes" :aria-current="route.path.includes('/scenes') ? 'page' : undefined" :class="{ active: route.path.includes('/scenes') }" :title="collapsed ? $t('nav.scenes') : ''">
            <GitBranch :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.scenes') }}</span>
          </router-link>
          <router-link :to="RoutePaths.reports(projectId)" class="nav-item sidebar-item-reports" :aria-current="route.path.includes('/reports') ? 'page' : undefined" :class="{ active: route.path.includes('/reports') }" :title="collapsed ? $t('nav.reports') : ''">
            <BarChart3 :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.reports') }}</span>
          </router-link>
          <router-link :to="RoutePaths.mockRules(projectId)" class="nav-item" :class="{ active: route.path.includes('/mock-rules') }" :title="collapsed ? $t('nav.mockRules') : ''">
            <TestTube :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.mockRules') }}</span>
          </router-link>
          <div class="nav-divider"></div>
          <div class="nav-group-label" v-show="!collapsed">{{ $t('nav.settings') }}</div>
          <router-link
            :to="RoutePaths.settings(projectId)"
            class="nav-item"
            :class="{ active: route.path.includes('/settings') }"
            :title="collapsed ? $t('nav.projectSettings') : ''"
          >
            <Settings :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.projectSettings') }}</span>
          </router-link>
          <router-link
            v-if="canViewRecycleBin"
            :to="RoutePaths.recycleBin(projectId)"
            class="nav-item"
            :class="{ active: route.path.includes('/recycle-bin') }"
            :title="collapsed ? $t('nav.recycleBin') : ''"
          >
            <Trash2 :size="20" class="nav-icon" aria-hidden="true" />
            <span class="nav-label" v-show="!collapsed">{{ $t('nav.recycleBin') }}</span>
          </router-link>
        </div>
      </template>
    </nav>

    <!-- 底部收起按钮 -->
    <div class="sidebar-footer">
      <div class="sidebar-project-info" v-if="!collapsed && currentProjectName && isLoggedIn">
        <span class="sidebar-project-dot"></span>
        <span class="sidebar-project-name">{{ currentProjectName }}</span>
      </div>
      <button class="collapse-btn" @click="toggleCollapse" :aria-label="collapsed ? $t('nav.expandSidebar') : $t('nav.collapseSidebar')">
        <ChevronLeft :size="14" class="chevron-icon" :class="{ rotated: collapsed }" aria-hidden="true" />
        <transition name="fade-text">
          <span class="collapse-text" v-show="!collapsed">{{ $t('nav.collapseSidebar') }}</span>
        </transition>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/projectStore'
import { useUserStore } from '../stores/userStore'
import { useProjectPermission } from '../composables/useProjectPermission'
import { RoutePaths } from '../router/paths'
import {
  LayoutDashboard, Plug, GitBranch, BarChart3,
  ChevronLeft, TestTube, Settings, Trash2,
} from 'lucide-vue-next'

const route = useRoute()
const projectStore = useProjectStore()
const userStore = useUserStore()
const { canViewRecycleBin } = useProjectPermission()
const isLoggedIn = computed(() => !!userStore.user && userStore.isTokenReady)

const props = defineProps<{
  collapsed: boolean
}>()

// 优先使用路由中的项目 ID，回退到 store 中的当前项目 ID
// 确保用户通过 URL 直接访问 /projects/5/apis 时，侧边栏链接也指向项目 5
const projectId = computed(() => {
  const routeId = route.params.id
  if (routeId) return Number(routeId)
  return projectStore.currentProjectId
})

// 当路由包含项目 ID 时，同步到 store 以保持全局一致
watch(
  () => route.params.id,
  (newId) => {
    if (newId && Number(newId) !== projectStore.currentProjectId) {
      projectStore.setCurrentProject(Number(newId))
    }
  },
)

const currentProjectName = computed(() => {
  return projectStore.projects.find((p: { id: number; name: string }) => p.id === projectId.value)?.name || ''
})

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

function clearClearedForApis() {
  try { localStorage.removeItem('api_pilot_tabs_cleared') } catch { /* localStorage 可能不可用 */ }
}

function toggleCollapse() {
  emit('update:collapsed', !props.collapsed)
}
</script>

<style scoped>
/* ── 侧边栏容器 — 统一宽度与过渡 ── */
.sidebar {
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border-right: 1px solid var(--border-subtle);
  transition: width 250ms cubic-bezier(0.22, 1, 0.36, 1);
  flex-shrink: 0;
  overflow: hidden;
  will-change: width;
  position: relative;
  isolation: isolate;
  width: var(--width-sidebar);
}

.sidebar.collapsed {
  width: var(--width-sidebar-collapsed);
}

/* ── Logo ── */
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  text-decoration: none;
  transition: background var(--duration-base) var(--ease-smooth);
  position: relative;
  overflow: hidden;
  z-index: 1;
}
.logo:hover::before { display: none; }
.logo.collapsed { justify-content: center; padding: 0; }
.logo-mark {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--duration-base) var(--ease-smooth);
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 2px 6px var(--color-primary-alpha-16));
}
.logo:hover .logo-mark {
  transform: rotate(8deg) scale(1.08);
  filter: drop-shadow(0 4px 12px var(--color-primary-alpha-24));
}
.logo-text {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, var(--primary-600), var(--primary-500));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── 导航区域 ── */
.nav {
  flex: 1;
  padding: var(--space-1-5) var(--space-2-5);
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  z-index: 1;
}

/* ── 分组标签 ── */
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.nav-group-label {
  position: relative;
  padding: var(--space-5) var(--space-3-5) var(--space-2);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.10em;
  user-select: none;
  animation: fadeInUp var(--duration-base) var(--ease-soft) both;
}
/* 父项下划线：在标签下方显示柔和的主色微线，标识父项区域 */
.nav-group-label::after {
  content: '';
  position: absolute;
  left: var(--space-3-5);
  right: var(--space-3-5);
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--color-primary-alpha-30) 0%, transparent 80%);
  opacity: 0.7;
  transition: opacity 280ms var(--ease-smooth);
}
.nav-group:hover .nav-group-label::after {
  opacity: 1;
}
.nav-divider {
  height: 1px;
  background: var(--border-subtle);
  margin: var(--space-2-5) var(--space-3-5);
  opacity: 0.65;
}

/* ── 导航项 — 统一高度与间距 ── */
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  height: 40px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  border-radius: var(--radius-md);
  transition: background 200ms var(--ease-smooth), color 200ms var(--ease-smooth), transform 200ms var(--ease-spring), box-shadow 200ms var(--ease-soft);
  margin: 0 var(--space-2);
  letter-spacing: 0.005em;
  animation: staggerItem var(--duration-base) var(--ease-soft) both;
}
.nav-item:nth-child(1) { animation-delay: 0ms; }
.nav-item:nth-child(2) { animation-delay: 30ms; }
.nav-item:nth-child(3) { animation-delay: 60ms; }
.nav-item:nth-child(4) { animation-delay: 90ms; }
.nav-item:nth-child(5) { animation-delay: 120ms; }
.nav-item:nth-child(6) { animation-delay: 150ms; }
.nav-item:nth-child(7) { animation-delay: 180ms; }
.nav-item:nth-child(8) { animation-delay: 210ms; }
.nav-item:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  transform: translateX(3px);
  box-shadow: inset 2px 0 0 var(--primary-500);
}
.nav-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--primary-400);
  outline-offset: -2px;
}

/* 选中态 — primary 色高亮 + 左侧 3px 蓝紫指示条 */
.nav-item.active {
  background: linear-gradient(90deg, var(--color-primary-alpha-08), transparent);
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
  box-shadow: inset 3px 0 0 var(--primary-500);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--primary-500);
  border-radius: 0 3px 3px 0;
  box-shadow: 0 0 12px var(--color-primary-alpha-35);
  transition: box-shadow 280ms var(--ease-smooth), height 200ms var(--ease-smooth);
}
.nav-item.active:hover {
  background: var(--color-primary-alpha-12);
}
.nav-item.active:hover::before {
  height: 28px;
  box-shadow: 0 0 18px var(--color-primary-alpha-45);
}

.nav-icon {
  flex-shrink: 0;
  opacity: 0.7;
  transition: opacity 200ms var(--ease-smooth), transform 200ms var(--ease-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  line-height: 1;
}
.nav-item.active .nav-icon { opacity: 1; }
.nav-item:hover .nav-icon { transform: scale(1.05); }
.nav-label { white-space: nowrap; overflow: hidden; }

/* ── 底部 ── */
.sidebar-footer {
  padding: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.sidebar-project-info {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin-bottom: 4px;
  border-radius: var(--radius-lg);
  background: var(--surface-hover);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  overflow: hidden;
  cursor: default;
  transition: background 200ms var(--ease-smooth), transform 200ms var(--ease-smooth);
}
.sidebar-project-info:hover {
  background: var(--color-primary-alpha-08);
  transform: translateX(1px);
}
.sidebar-project-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--primary-500);
  flex-shrink: 0;
}
.sidebar-project-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: var(--weight-semibold);
}

.collapse-btn {
  width: 100%;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1-5);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-muted);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  font-family: inherit;
  transition:
    background var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth),
    transform var(--duration-base) var(--ease-spring);
}
.collapse-btn:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
  transform: scale(1.03);
}
.collapse-btn:active {
  transform: scale(0.95);
}
.collapse-btn:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: -2px;
  border-radius: var(--radius-sm);
}
.collapse-text {
  opacity: 0.85;
}
.chevron-icon {
  transition: transform var(--duration-slow) cubic-bezier(0.34, 1.56, 0.64, 1);
}
.chevron-icon.rotated {
  transform: rotate(180deg);
}

/* ── 过渡 ── */
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 200ms var(--ease-smooth);
}
.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}

/* ── 自定义滚动条 — 品牌化 ── */
.nav::-webkit-scrollbar {
  width: 4px;
}
.nav::-webkit-scrollbar-track {
  background: transparent;
}
.nav::-webkit-scrollbar-thumb {
  background: var(--border-subtle);
  border-radius: var(--radius-full);
  transition: background var(--duration-fast) var(--ease-smooth);
}
.nav::-webkit-scrollbar-thumb:hover {
  background: var(--color-neutral-alpha-20);
}

/* ── 暗色模式 ── */
html.dark .sidebar {
  background: var(--surface-card);
  border-right-color: var(--border-subtle);
}
html.dark .logo {
  border-bottom-color: var(--border-subtle);
}
html.dark .logo-text {
  background: linear-gradient(135deg, var(--primary-400), var(--primary-300));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
html.dark .nav-group-label {
  color: var(--text-muted);
}
html.dark .nav-group-label::after {
  background: linear-gradient(90deg, var(--color-primary-alpha-20) 0%, transparent 80%);
}
html.dark .nav-item {
  color: var(--text-secondary);
}
html.dark .nav-item:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  box-shadow: inset 2px 0 0 var(--primary-400);
}
html.dark .nav-item.active {
  background: linear-gradient(90deg, var(--color-primary-alpha-12), transparent);
  color: var(--primary-400);
  box-shadow: inset 3px 0 0 var(--primary-400);
}
html.dark .nav-item.active::before {
  background: var(--primary-400);
  box-shadow: 0 0 12px var(--color-primary-alpha-25);
}
html.dark .nav-item.active:hover {
  background: var(--color-primary-alpha-16);
}
html.dark .nav-item.active:hover::before {
  box-shadow: 0 0 18px var(--color-primary-alpha-35);
}
html.dark .nav-icon {
  opacity: 0.65;
}
html.dark .nav-item.active .nav-icon {
  opacity: 1;
}
html.dark .nav-divider {
  background: var(--border-subtle);
}
html.dark .sidebar-footer {
  border-top-color: var(--border-subtle);
}
html.dark .sidebar-project-info {
  background: var(--surface-hover);
  color: var(--text-secondary);
}
html.dark .sidebar-project-info:hover {
  background: var(--color-primary-alpha-10);
}
html.dark .sidebar-project-dot {
  background: var(--primary-400);
}
html.dark .collapse-btn {
  color: var(--text-muted);
}
html.dark .collapse-btn:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}
html.dark .collapse-btn:focus-visible {
  outline-color: var(--primary-400);
}
html.dark .nav::-webkit-scrollbar-thumb {
  background: var(--color-neutral-alpha-14);
}
html.dark .nav::-webkit-scrollbar-thumb:hover {
  background: var(--color-neutral-alpha-24);
}

</style>
