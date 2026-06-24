<template>
  <Teleport to="body">
    <transition name="search-fade">
      <div v-if="visible" class="search-overlay" @click.self="close">
        <div class="search-modal">
          <div class="search-input-wrap">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              ref="searchInputRef"
              v-model="query"
              class="search-input"
              :placeholder="t('search.placeholder')"
              @input="debouncedSearch"
              @focus="onInputFocus"
              @keydown.down.prevent="moveDown"
              @keydown.up.prevent="moveUp"
              @keydown.enter="selectItem"
              @keydown.esc="close"
            />
            <kbd class="esc-key">ESC</kbd>
          </div>

          <!-- 分类过滤 -->
          <div class="search-filters">
            <el-radio-group v-model="filterType" size="small" @change="debouncedSearch">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button value="api">接口</el-radio-button>
              <el-radio-button value="scene">场景</el-radio-button>
              <el-radio-button value="case">用例</el-radio-button>
              <el-radio-button value="report">报告</el-radio-button>
              <el-radio-button value="mock_rule">Mock</el-radio-button>
            </el-radio-group>
          </div>

          <div class="search-results" ref="resultsRef">
            <!-- 搜索历史（输入框为空且获得焦点时显示） -->
            <div v-if="showHistory && query.trim() === ''" class="history-section">
              <div class="group-header">
                <el-icon><Clock /></el-icon>
                <span>{{ t('search.recent') }}</span>
              </div>
              <div
                v-for="(item, i) in historyItems"
                :key="'h-' + item.id"
                :ref="el => { if (el) resultEls[i] = el as HTMLElement }"
                :class="['search-item', { active: i === activeIndex }]"
                @click="applyHistory(item.query)"
                @mouseenter="activeIndex = i"
              >
                <div class="item-icon history-icon">
                  <el-icon><Clock /></el-icon>
                </div>
                <div class="item-info">
                  <span class="item-title">{{ item.query }}</span>
                </div>
              </div>
              <div v-if="historyItems.length === 0" class="history-empty">
                {{ t('search.historyEmpty') }}
              </div>
              <div v-if="historyItems.length > 0" class="history-clear" @click="handleClearHistory">
                {{ t('search.clearHistory') }}
              </div>
            </div>

            <!-- 分组搜索结果 -->
            <template v-if="query.trim() !== ''">
              <div v-for="group in visibleGroups" :key="group.key" class="result-group">
                <div class="group-header">
                  <el-icon :color="group.color"><component :is="group.icon" /></el-icon>
                  <span>{{ group.label }}</span>
                  <span class="group-count">{{ results[group.key as keyof typeof results]?.length || 0 }}</span>
                </div>
                <div
                  v-for="(item, i) in results[group.key as keyof typeof results]"
                  :key="group.key + item.id"
                  :ref="el => { if (el) resultEls[flatIndex(group.key, i)] = el as HTMLElement }"
                  :class="['search-item', { active: flatIndex(group.key, i) === activeIndex }]"
                  @click="navigate(item)"
                  @mouseenter="activeIndex = flatIndex(group.key, i)"
                >
                  <div class="item-icon" :style="{ color: group.color }">
                    <el-icon><component :is="group.icon" /></el-icon>
                  </div>
                  <div class="item-info">
                    <span class="item-title">{{ item.title }}</span>
                    <span class="item-subtitle">{{ item.subtitle }}</span>
                  </div>
                  <el-tag size="small" :type="tagType(item.type)" effect="plain">{{ group.label }}</el-tag>
                </div>
                <div
                  v-if="results[group.key as keyof typeof results]?.length > 0"
                  class="view-more"
                  @click="viewMore(group.key)"
                >
                  {{ t('search.viewMore') }} →
                </div>
              </div>
              <EmptyState v-if="totalResults === 0 && query && !loading" illustration="search" :title="t('search.noResults')" />
              <div v-if="loading" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ t('search.searching') }}</span>
              </div>
            </template>
          </div>

          <div class="search-footer">
            <span><kbd>&uarr;</kbd><kbd>&darr;</kbd> 导航</span>
            <span><kbd>Enter</kbd> 选择</span>
            <span><kbd>Esc</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, shallowRef, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, Link, VideoPlay, Document, SetUp, Loading, Clock, DataAnalysis, MagicStick } from '@element-plus/icons-vue'
import { globalSearch, saveSearchHistory, getSearchHistory, clearSearchHistory, type SearchResult, type SearchHistoryItem } from '@/api/search'
import { msgError } from '@/utils/message'
import { logger } from '@/utils/logger'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()
const router = useRouter()

const props = defineProps<{
  visible: boolean
  projectId: number
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  select: [item: SearchResult]
}>()

const query = ref('')
const filterType = ref('')
const loading = ref(false)
const activeIndex = ref(0)
const searchInputRef = ref<HTMLInputElement>()
const resultsRef = ref<HTMLDivElement>()
const resultEls = ref<HTMLElement[]>([])
const showHistory = ref(false)
const historyItems = ref<SearchHistoryItem[]>([])

const results = shallowRef<{
  apis: SearchResult[]
  scenes: SearchResult[]
  cases: SearchResult[]
  reports: SearchResult[]
  mock_rules: SearchResult[]
  environments: SearchResult[]
}>({ apis: [], scenes: [], cases: [], reports: [], mock_rules: [], environments: [] })

let debounceTimer: ReturnType<typeof setTimeout>

const groupDefs = [
  { key: 'apis', label: () => t('search.apis'), icon: Link, color: 'var(--primary-500)' },
  { key: 'scenes', label: () => t('search.scenes'), icon: VideoPlay, color: 'var(--info)' },
  { key: 'cases', label: () => t('search.cases'), icon: Document, color: 'var(--warning)' },
  { key: 'reports', label: () => t('search.reports'), icon: DataAnalysis, color: 'var(--danger)' },
  { key: 'mock_rules', label: () => t('search.mockRules'), icon: MagicStick, color: 'var(--purple)' },
  { key: 'environments', label: () => t('search.environments'), icon: SetUp, color: 'var(--success)' },
] as const

const visibleGroups = computed(() =>
  groupDefs.filter(g => (results.value[g.key]?.length ?? 0) > 0)
)

const totalResults = computed(() =>
  Object.values(results.value).reduce((sum, arr) => sum + arr.length, 0)
)

// 将分组结果展平为一维索引，用于键盘导航
const flatList = computed(() => {
  const list: (SearchResult & { type: string; _groupKey: string })[] = []
  for (const g of groupDefs) {
    const items = results.value[g.key] || []
    for (const item of items) {
      list.push({ ...item, _groupKey: g.key })
    }
  }
  return list
})

function flatIndex(groupKey: string, itemIndex: number): number {
  let offset = 0
  for (const g of groupDefs) {
    if (g.key === groupKey) return offset + itemIndex
    offset += (results.value[g.key]?.length ?? 0)
  }
  return offset + itemIndex
}

watch(() => results.value, () => {
  activeIndex.value = 0
}, { deep: true })

watch(() => props.visible, (val) => {
  if (val) {
    query.value = ''
    filterType.value = ''
    results.value = { apis: [], scenes: [], cases: [], reports: [], mock_rules: [], environments: [] }
    resultEls.value = []
    showHistory.value = true
    void loadHistory()
    void nextTick(() => {
      requestAnimationFrame(() => {
        searchInputRef.value?.focus()
      })
    })
  }
})

function onInputFocus() {
  if (query.value.trim() === '') {
    showHistory.value = true
    void loadHistory()
  }
}

async function loadHistory() {
  try {
    const res = await getSearchHistory(props.projectId)
    historyItems.value = res.data || []
  } catch {
    historyItems.value = []
  }
}

function applyHistory(q: string) {
  query.value = q
  showHistory.value = false
  void doSearch()
}

async function handleClearHistory() {
  try {
    await clearSearchHistory(props.projectId)
    historyItems.value = []
  } catch { /* ignore */ }
}

function debouncedSearch() {
  clearTimeout(debounceTimer)
  showHistory.value = false
  if (!query.value.trim()) {
    results.value = { apis: [], scenes: [], cases: [], reports: [], mock_rules: [], environments: [] }
    showHistory.value = true
    void loadHistory()
    return
  }
  debounceTimer = setTimeout(doSearch, 200)
}

async function doSearch() {
  if (!query.value.trim()) return
  loading.value = true
  try {
    const res = await globalSearch(props.projectId, query.value, filterType.value || undefined)
    results.value = res.data?.results || { apis: [], scenes: [], cases: [], reports: [], mock_rules: [], environments: [] }
    // 异步保存搜索历史（不阻塞 UI）
    saveSearchHistory(props.projectId, query.value).catch(() => {})
  } catch (err) {
    logger.error('[GlobalSearch] search failed:', err)
    msgError('搜索失败，请重试')
    results.value = { apis: [], scenes: [], cases: [], reports: [], mock_rules: [], environments: [] }
  } finally {
    loading.value = false
  }
}

function moveDown() {
  const total = query.value.trim() ? flatList.value.length : historyItems.value.length
  if (total === 0) return
  activeIndex.value = (activeIndex.value + 1) % total
  scrollToActive()
}

function moveUp() {
  const total = query.value.trim() ? flatList.value.length : historyItems.value.length
  if (total === 0) return
  activeIndex.value = (activeIndex.value - 1 + total) % total
  scrollToActive()
}

function scrollToActive() {
  void nextTick(() => {
    resultEls.value[activeIndex.value]?.scrollIntoView({ block: 'nearest' })
  })
}

function selectItem() {
  if (query.value.trim() === '') {
    // 在历史中选择
    const item = historyItems.value[activeIndex.value]
    if (item) applyHistory(item.query)
    return
  }
  const item = flatList.value[activeIndex.value]
  if (item) navigate(item)
}

function navigate(item: SearchResult & { _groupKey?: string }) {
  emit('select', item)
  close()
}

function viewMore(groupKey: string) {
  const routeMap: Record<string, string> = {
    apis: 'Apis',
    scenes: 'Scenes',
    cases: 'Apis', // 用例在接口页面的 tab 中
    reports: 'Reports',
    mock_rules: 'MockRules',
    environments: 'Settings',
  }
  const routeName = routeMap[groupKey]
  if (routeName) {
    void router.push({ name: routeName, params: { id: props.projectId } })
  }
  close()
}

function close() {
  emit('update:visible', false)
}

function tagType(type: string): string {
  const map: Record<string, string> = { api: 'success', scene: '', case: 'warning', report: 'danger', mock_rule: 'info', environment: 'info' }
  return map[type] || 'info'
}

onBeforeUnmount(() => {
  clearTimeout(debounceTimer)
})
</script>

<style scoped>
/* ── GlobalSearch v8：分组结果 + 搜索历史 + 视觉优化
   搜索对话框，Cmd+K / Ctrl+K 触发。
   ─────────────────────────────── */

/* 遮罩层 */
.search-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal-backdrop);
  background: var(--color-black-alpha-30);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  padding-top: 15vh;
}

/* 模态框主体 */
.search-modal {
  width: 600px;
  max-height: 520px;
  background: var(--surface-card);
  border-radius: 16px;
  box-shadow: var(--shadow-float);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

/* ── 顶部搜索栏 ── */
.search-input-wrap {
  display: flex;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--border-subtle);
  gap: var(--spacing-sm);
}

.search-icon {
  color: var(--text-muted);
  font-size: var(--font-size-lg);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 16px;
  background: transparent;
  color: var(--text-primary);
  min-width: 0;
  font-family: var(--font-sans);
  height: 48px;
  padding: 0 var(--spacing-sm);
  border-bottom: 2px solid var(--border-default);
  border-radius: 0;
  transition: background-color var(--duration-fast), border-color var(--duration-fast);
}

.search-input:focus {
  background-color: var(--surface-hover);
  border-bottom-color: var(--primary-500);
}

.search-input::placeholder {
  color: var(--text-placeholder);
}

/* ESC 快捷键提示 */
.esc-key {
  font-size: var(--font-size-2xs);
  padding: 2px 8px;
  background: var(--surface-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-disabled);
  font-family: var(--font-mono, monospace);
  line-height: 1.6;
  flex-shrink: 0;
  box-shadow: 0 1px 0 var(--border-subtle);
  letter-spacing: 0.02em;
}

/* ── 分类过滤 ── */
.search-filters {
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.search-filters :deep(.el-radio-button__inner) {
  border-radius: var(--radius-sm) !important;
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  color: var(--text-secondary) !important;
  font-weight: var(--weight-medium);
  transition: all var(--duration-fast);
}

.search-filters :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--color-primary-alpha-08) !important;
  color: var(--primary-500) !important;
}

/* ── 搜索结果列表 ── */
.search-results {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xs) 0;
}

/* ── 分组标题 ── */
.group-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-xl) var(--space-0-5);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.group-header .el-icon {
  font-size: var(--font-size-sm);
}

.group-count {
  margin-left: auto;
  background: var(--surface-hover);
  padding: 0 var(--spacing-sm);
  border-radius: var(--radius-full);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  line-height: 1.8;
}

/* ── 每个结果项 ── */
.search-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: 0 var(--spacing-xl);
  cursor: pointer;
  transition: background var(--duration-fast);
  min-height: 44px;
  line-height: 44px;
  border-left: 3px solid transparent;
}

.search-item:hover {
  background: var(--surface-hover);
}

.search-item.active {
  background: var(--color-primary-alpha-08);
  border-left-color: var(--primary-500);
}

/* 类型图标 */
.item-icon {
  font-size: var(--font-size-lg);
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--surface-hover);
  transition: background var(--duration-fast);
}

.search-item:hover .item-icon {
  background: var(--surface-card);
}

.history-icon {
  color: var(--text-muted);
}

/* 信息区 */
.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
}

.item-title {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: var(--leading-tight);
}

.item-subtitle {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

/* 类型标签：覆盖 el-tag 样式 */
.search-item :deep(.el-tag) {
  height: 22px;
  line-height: 22px;
  padding: 0 var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
  letter-spacing: var(--tracking-wide);
  border: none;
}

.search-item :deep(.el-tag.el-tag--success) {
  background: var(--color-success-alpha-12);
  color: var(--success-text);
}

.search-item :deep(.el-tag.el-tag--warning) {
  background: var(--color-warning-alpha-12);
  color: var(--warning-text);
}

.search-item :deep(.el-tag.el-tag--danger) {
  background: var(--color-danger-alpha-12);
  color: var(--danger-text);
}

.search-item :deep(.el-tag.el-tag--info) {
  background: var(--color-primary-alpha-10);
  color: var(--text-secondary);
}

.search-item :deep(.el-tag--plain) {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

/* ── 查看更多 ── */
.view-more {
  padding: var(--space-1) var(--spacing-xl) var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--primary-500);
  cursor: pointer;
  transition: color var(--duration-fast);
}

.view-more:hover {
  color: var(--primary-600);
  text-decoration: underline;
}

/* ── 搜索历史 ── */
.history-section {
  padding-bottom: var(--spacing-xs);
}

.history-empty {
  padding: var(--spacing-lg) var(--spacing-xl);
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

.history-clear {
  padding: var(--spacing-sm) var(--spacing-xl);
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  cursor: pointer;
  transition: color var(--duration-fast);
}

.history-clear:hover {
  color: var(--danger-text);
}

/* 空状态 / 加载中 */
.empty-state,
.loading-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-5xl) var(--spacing-xl);
  gap: var(--spacing-sm);
  color: var(--text-muted);
}

.loading-state {
  flex-direction: row;
  gap: var(--spacing-sm);
  padding: var(--spacing-3xl);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

/* ── 底部快捷键提示 ── */
.search-footer {
  display: flex;
  gap: var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-xl);
  border-top: 1px solid var(--border-subtle);
  font-size: var(--font-size-2xs);
  color: var(--text-disabled);
  flex-shrink: 0;
  justify-content: flex-end;
  background: var(--surface-nested);
}

.search-footer span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-0-5);
}

.search-footer kbd {
  font-size: var(--font-size-2xs);
  padding: 1px 5px;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: 3px;
  font-family: inherit;
  line-height: 1.5;
  color: var(--text-muted);
  min-width: 18px;
  text-align: center;
}

/* ── 入场动画 ── */
.search-fade-enter-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-fade-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 1, 1);
}

.search-fade-enter-active .search-modal {
  animation: search-pop-in 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.search-fade-enter-from,
.search-fade-leave-to {
  opacity: 0;
}

@keyframes search-pop-in {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── 降级：减少动画偏好 ── */
@media (prefers-reduced-motion: reduce) {
  .search-fade-enter-active .search-modal {
    animation: none;
  }
}
</style>
