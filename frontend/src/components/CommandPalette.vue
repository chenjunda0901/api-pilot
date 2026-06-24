<template>
  <Teleport to="body">
    <Transition name="fade-scale">
      <div v-if="visible" class="cmd-palette-overlay" @click.self="close" @keydown.escape="close">
        <div class="cmd-palette" role="dialog" aria-label="命令面板" aria-modal="true">
          <!-- Search Input -->
          <div class="cmd-palette-header">
            <svg class="cmd-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              ref="searchInput"
              v-model="query"
              class="cmd-search-input"
              placeholder="搜索接口、场景、项目或输入命令..."
              aria-label="搜索"
              @keydown.up.prevent="moveUp"
              @keydown.down.prevent="moveDown"
              @keydown.enter.prevent="selectCurrent"
            />
            <kbd class="cmd-kbd">Esc</kbd>
          </div>

          <!-- Results -->
          <div class="cmd-palette-body">
            <template v-if="searchLoading">
              <div class="cmd-loading">
                <span class="cmd-loading-spinner" />
                <span>搜索中...</span>
              </div>
            </template>
            <template v-else-if="groupedResults.length">
              <div v-for="group in groupedResults" :key="group.label" class="cmd-group">
                <div class="cmd-group-label">{{ group.label }}</div>
                <button
                  v-for="(item, i) in group.items"
                  :key="item.id"
                  :ref="el => { if (el) itemRefs[group.label + '-' + i] = el }"
                  class="cmd-item"
                  :class="{ 'cmd-item-active': isActive(group.label, i) }"
                  role="option"
                  :aria-selected="isActive(group.label, i)"
                  @click="execute(item)"
                  @mouseenter="activeIndex = findGlobalIndex(group.label, i)"
                >
                  <span v-if="item.icon" class="cmd-item-icon" v-text="item.label[0].toUpperCase()" />
                  <span v-if="item.method" class="cmd-method-badge" :class="`method-${item.method.toLowerCase()}`">{{ item.method }}</span>
                  <span class="cmd-item-label">{{ item.label }}</span>
                  <span v-if="item.desc" class="cmd-item-desc">{{ item.desc }}</span>
                  <kbd v-if="item.shortcut" class="cmd-item-shortcut">{{ item.shortcut }}</kbd>
                </button>
              </div>
            </template>
            <div v-else class="cmd-empty">
              <span>未找到匹配结果</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="cmd-palette-footer">
            <span><kbd>↑↓</kbd> 导航</span>
            <span><kbd>Enter</kbd> 选择</span>
            <span><kbd>Esc</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/projectStore'
import { globalSearch, type SearchResponse } from '@/api/search'
import { RoutePaths } from '@/router/paths'

interface CommandItem {
  id: string
  label: string
  desc?: string
  icon?: string
  method?: string
  shortcut?: string
  action: () => void | Promise<void>
  group: string
  keywords?: string
}

const CMD_HISTORY_KEY = 'api-pilot:cmd-history'
const CMD_HISTORY_MAX = 10

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const router = useRouter()
const projectStore = useProjectStore()

const query = ref('')
const activeIndex = ref(0)
const searchInput = ref<HTMLInputElement | null>(null)
const itemRefs = ref<Record<string, HTMLElement>>({})
const searchResults = ref<SearchResponse | null>(null)
const searchLoading = ref(false)

const close = () => {
  query.value = ''
  activeIndex.value = 0
  searchResults.value = null
  searchLoading.value = false
  emit('close')
}

// ── 命令历史 ──
function loadHistory(): CommandItem[] {
  try {
    const raw = localStorage.getItem(CMD_HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw) as CommandItem[]
  } catch {
    return []
  }
}

function saveHistory(item: CommandItem) {
  const history = loadHistory().filter(h => h.id !== item.id)
  history.unshift(item)
  localStorage.setItem(CMD_HISTORY_KEY, JSON.stringify(history.slice(0, CMD_HISTORY_MAX)))
}

// Static commands
const staticCommands = computed<CommandItem[]>(() => {
  const pid = projectStore.currentProject?.id
  return [
    {
      id: 'nav-dashboard',
      label: '前往仪表盘',
      desc: '查看项目概览',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
      shortcut: '',
      action: () => router.push(RoutePaths.dashboard),
      group: '导航'
    },
    {
      id: 'nav-apis',
      label: '前往接口管理',
      desc: '管理 API 接口',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
      shortcut: '',
      action: () => pid ? router.push(RoutePaths.apiList(pid)) : router.push('/'),
      group: '导航'
    },
    {
      id: 'nav-scenes',
      label: '前往场景测试',
      desc: '管理测试场景',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
      shortcut: '',
      action: () => pid ? router.push(RoutePaths.scenes(pid)) : router.push('/'),
      group: '导航'
    },
    {
      id: 'nav-reports',
      label: '前往测试报告',
      desc: '查看测试报告',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
      shortcut: '',
      action: () => pid ? router.push(RoutePaths.reports(pid)) : router.push('/'),
      group: '导航'
    },
    {
      id: 'action-new-api',
      label: '新建接口',
      desc: '创建新的 API 接口',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
      shortcut: 'Ctrl+N',
      action: () => pid ? router.push(RoutePaths.apisNew(pid)) : undefined,
      group: '操作'
    },
    {
      id: 'action-new-scene',
      label: '新建场景',
      desc: '创建新的测试场景',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
      shortcut: '',
      action: () => pid ? router.push(`${RoutePaths.scenes(pid)}?action=create`) : undefined,
      group: '操作'
    },
    {
      id: 'action-new-project',
      label: '新建项目',
      desc: '创建新的测试项目',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
      shortcut: '',
      action: () => router.push('/?action=create-project'),
      group: '操作'
    },
    {
      id: 'action-settings',
      label: '系统设置',
      desc: '管理环境变量和配置',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
      shortcut: '',
      action: () => pid ? router.push(RoutePaths.settings(pid)) : router.push('/'),
      group: '操作'
    },
    {
      id: 'action-theme-toggle',
      label: '切换主题',
      desc: '亮色/暗色模式切换',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
      shortcut: 'Ctrl+D',
      action: () => document.documentElement.classList.toggle('dark'),
      group: '操作'
    },
  ]
})

// ── 搜索结果转 CommandItem ──
const apiIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>'
const sceneIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>'

const searchCommandItems = computed<CommandItem[]>(() => {
  if (!searchResults.value || !projectStore.currentProject?.id) return []
  const pid = projectStore.currentProject.id
  const items: CommandItem[] = []

  for (const api of searchResults.value.apis || []) {
    items.push({
      id: `api-${api.id}`,
      label: api.title,
      desc: api.subtitle,
      icon: apiIcon,
      method: api.subtitle?.split(' ')?.[0] || undefined,
      action: () => router.push(RoutePaths.apiDetail(pid, api.id)),
      group: '接口'
    })
  }
  for (const scene of searchResults.value.scenes || []) {
    items.push({
      id: `scene-${scene.id}`,
      label: scene.title,
      desc: scene.subtitle,
      icon: sceneIcon,
      action: () => router.push(`${RoutePaths.scenes(pid)}?highlight=${scene.id}`),
      group: '场景'
    })
  }
  // cases 作为接口用例归入接口组
  for (const c of searchResults.value.cases || []) {
    items.push({
      id: `case-${c.id}`,
      label: c.title,
      desc: c.subtitle,
      icon: apiIcon,
      action: () => router.push(RoutePaths.caseDetail(pid, c.id)),
      group: '接口'
    })
  }
  return items
})

// ── 历史记录 ──
const historyItems = computed<CommandItem[]>(() => {
  if (query.value.trim()) return [] // 搜索时不显示历史
  return loadHistory()
})

// ── 搜索触发 ──
let searchTimer: ReturnType<typeof setTimeout> | null = null

watch(query, (q) => {
  if (searchTimer) clearTimeout(searchTimer)
  const pid = projectStore.currentProject?.id
  const keyword = q.trim()
  if (!pid || !keyword) {
    searchResults.value = null
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  searchTimer = setTimeout(async () => {
    try {
      const res = await globalSearch(pid, keyword)
      searchResults.value = res.data ?? res as unknown as SearchResponse
    } catch {
      searchResults.value = null
    } finally {
      searchLoading.value = false
    }
  }, 250)
})

// Search & filter
const filteredItems = computed<CommandItem[]>(() => {
  const q = query.value.toLowerCase().trim()
  if (!q) return staticCommands.value

  const staticFiltered = staticCommands.value.filter(item => {
    const searchable = `${item.label} ${item.desc || ''} ${item.keywords || ''} ${item.method || ''}`.toLowerCase()
    return searchable.includes(q)
  })

  // 合并搜索结果（去重）
  const staticIds = new Set(staticFiltered.map(i => i.id))
  const dedupedSearch = searchCommandItems.value.filter(i => !staticIds.has(i.id))

  return [...staticFiltered, ...dedupedSearch]
})

const groupedResults = computed(() => {
  const groups: Record<string, CommandItem[]> = {}

  // 历史记录组（仅无搜索词时显示）
  if (historyItems.value.length > 0) {
    groups['最近使用'] = historyItems.value
  }

  for (const item of filteredItems.value) {
    if (!groups[item.group]) groups[item.group] = []
    groups[item.group].push(item)
  }
  return Object.entries(groups).map(([label, items]) => ({ label, items }))
})

// Navigation
const findGlobalIndex = (groupLabel: string, localIndex: number) => {
  let idx = 0
  for (const group of groupedResults.value) {
    if (group.label === groupLabel) return idx + localIndex
    idx += group.items.length
  }
  return 0
}

const isActive = (groupLabel: string, localIndex: number) => {
  return activeIndex.value === findGlobalIndex(groupLabel, localIndex)
}

const moveUp = () => {
  activeIndex.value = Math.max(0, activeIndex.value - 1)
  scrollToActive()
}

const moveDown = () => {
  activeIndex.value = Math.min(filteredItems.value.length + historyItems.value.length - 1, activeIndex.value + 1)
  scrollToActive()
}

const scrollToActive = () => {
  void nextTick(() => {
    const key = Object.keys(itemRefs.value)[activeIndex.value]
    if (key) itemRefs.value[key]?.scrollIntoView({ block: 'nearest' })
  })
}

const selectCurrent = () => {
  // 合并列表中取当前项
  const allItems = [...historyItems.value, ...filteredItems.value]
  if (allItems[activeIndex.value]) {
    void execute(allItems[activeIndex.value])
  }
}

const execute = async (item: CommandItem) => {
  saveHistory(item)
  await item.action()
  close()
}

// Focus on open
watch(() => props.visible, (v) => {
  if (v) {
    void nextTick(() => searchInput.value?.focus())
  }
})
</script>

<style scoped>
/* ===== 遮罩层 — 使用 z-max 层级 + 品牌化模糊 ===== */
.cmd-palette-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-max);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  background: var(--color-black-alpha-45, rgba(0, 0, 0, 0.45));
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

/* ===== 命令面板容器 — 多层阴影 + 品牌化圆角 ===== */
.cmd-palette {
  width: 560px;
  max-width: 90vw;
  max-height: 440px;
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  /* 使用 shadow-float token 替代硬编码阴影 */
  box-shadow: var(--shadow-float);
  overflow: hidden;
}

/* ===== 头部搜索区域 ===== */
.cmd-palette-header {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  padding: var(--space-3-5) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}

/* 搜索图标 */
.cmd-search-icon {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 搜索输入框 */
.cmd-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--text-base);
  color: var(--text-primary);
  line-height: var(--leading-normal);
  font-family: inherit;
}
.cmd-search-input::placeholder {
  color: var(--text-muted);
}
/* 键盘焦点可见环 */
.cmd-search-input:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* ESC 提示标签 */
.cmd-kbd {
  font-family: inherit;
  font-size: var(--text-2xs);
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  background: var(--surface-hover);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
  line-height: 1.4;
  font-weight: var(--weight-semibold);
}

/* ===== 结果列表区域 ===== */
.cmd-palette-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

/* 分组标签 */
.cmd-group-label {
  padding: var(--space-1-5) var(--space-2-5) var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* 命令项 */
.cmd-item {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-primary);
  text-align: left;
  transition: background var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth);
}
.cmd-item:hover {
  background: var(--surface-hover);
}
/* 激活状态 — 左侧主色指示条 */
.cmd-item-active {
  background: var(--color-primary-alpha-08);
  border-left: 2px solid var(--primary-500);
  padding-left: calc(var(--space-3) - 2px);
}
/* 键盘焦点可见环 */
.cmd-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: -2px;
}

/* 命令图标 */
.cmd-item-icon {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
  flex-shrink: 0;
  display: flex;
}
.cmd-item-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

/* HTTP 方法徽章 */
.cmd-method-badge {
  font-size: var(--text-3xs);
  font-weight: var(--weight-bold);
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.cmd-method-badge.method-get { background: var(--method-get-bg); color: var(--method-get-text); }
.cmd-method-badge.method-post { background: var(--method-post-bg); color: var(--method-post-text); }
.cmd-method-badge.method-put { background: var(--method-put-bg); color: var(--method-put-text); }
.cmd-method-badge.method-delete { background: var(--method-delete-bg); color: var(--method-delete-text); }
.cmd-method-badge.method-patch { background: var(--method-patch-bg); color: var(--method-patch-text); }

/* 命令标签 */
.cmd-item-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 命令描述 */
.cmd-item-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 快捷键标签 */
.cmd-item-shortcut {
  font-family: inherit;
  font-size: var(--text-2xs);
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  background: var(--surface-hover);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
  font-weight: var(--weight-semibold);
}

/* 空状态 */
.cmd-empty {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* 搜索加载 */
.cmd-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-8);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.cmd-loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--primary-500);
  border-radius: 50%;
  animation: cmd-spin 0.6s linear infinite;
}
@keyframes cmd-spin {
  to { transform: rotate(360deg); }
}

/* ===== 底部快捷键提示 ===== */
.cmd-palette-footer {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.cmd-palette-footer kbd {
  font-family: inherit;
  font-size: var(--text-3xs);
  padding: var(--space-0-5) var(--space-1);
  border-radius: var(--radius-2xs);
  background: var(--surface-hover);
  border: 1px solid var(--border-subtle);
  margin: 0 var(--space-0-5);
  font-weight: var(--weight-semibold);
}

/* ===== 暗色模式适配 ===== */
html.dark .cmd-palette-overlay {
  background: var(--color-black-alpha-60);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
html.dark .cmd-palette {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  /* 暗色模式使用 shadow-float token */
  box-shadow: var(--shadow-float);
}
html.dark .cmd-item:hover,
html.dark .cmd-item-active {
  background: var(--surface-hover);
}
html.dark .cmd-item-active {
  background: var(--color-primary-alpha-08);
  border-left-color: var(--primary-400);
}

/* ===== 过渡动画 ===== */
.fade-scale-enter-active {
  transition: all var(--duration-base) var(--ease-out);
}
.fade-scale-leave-active {
  transition: all var(--duration-fast) var(--ease-in);
}
.fade-scale-enter-from {
  opacity: 0;
  transform: scale(0.96) translateY(-8px);
}
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.98) translateY(-4px);
}

/* ===== 搜索结果高亮 ===== */
:deep(.cmd-highlight) {
  background: var(--warning-bg);
  color: var(--warning-text);
  padding: 0 var(--space-0-5);
  border-radius: var(--radius-2xs);
  font-weight: var(--weight-semibold);
}
html.dark :deep(.cmd-highlight) {
  background: var(--warning-bg);
  color: var(--warning-light);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  .cmd-palette,
  .cmd-item,
  .fade-scale-enter-active,
  .fade-scale-leave-active {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
