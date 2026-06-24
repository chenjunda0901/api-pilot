<template>

  <div>

    <Teleport to="body">

    <div class="search-overlay" v-if="visible" @click.self="close">

      <div class="search-panel" ref="panelRef">

        <div class="search-input-wrap">

          <svg class="search-icon" viewBox="0 0 16 16" fill="none" width="15" height="15" aria-hidden="true">

            <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5"/>

            <path d="M11 11L15 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>

          </svg>

          <input

            ref="inputRef"

            v-model="keyword"

            class="search-input"

            :placeholder="$t('search.placeholder')"

            @keydown="onKeydown"

          />

          <kbd class="search-hint">ESC</kbd>

        </div>

        <!-- 类型过滤 Tab -->
        <div class="search-type-tabs" v-if="keyword">
          <button v-for="t in filterTabs" :key="t.key"
            :class="['search-type-tab', { active: activeType === t.key }]"
            @click="activeType = t.key">{{ t.label }}<span class="type-count" v-if="resultCountByType[t.key as keyof typeof resultCountByType]">{{ resultCountByType[t.key as keyof typeof resultCountByType] }}</span></button>
        </div>

        <div class="search-results">

          <div class="search-recent" v-if="!keyword && recentSearches.length">

            <div class="result-group-label">{{ $t('search.recent') }}</div>

            <div v-for="(item, i) in recentSearches" :key="i"

              class="result-item" tabindex="0"

              @click="keyword = item"

              @keydown.enter="keyword = item"

            >

              <svg viewBox="0 0 16 16" fill="none" width="13" height="13" style="color:var(--text-muted)" aria-hidden="true"><circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5"/><path d="M11 11L15 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>

              <span class="result-title">{{ item }}</span>

            </div>

          </div>

          <template v-if="keyword && !loading">

            <div v-if="filteredResults.apis.length" class="result-group">

              <div class="result-group-label">{{ $t('search.apis') }}</div>

              <div

                v-for="(item, i) in filteredResults.apis"

                :key="item.id"

                class="result-item" tabindex="0"

                :class="{ active: activeIndex === i }"

                @click="navigate(item)"

                @keydown.enter="navigate(item)"

                @mouseenter="activeIndex = i"

              >

                <el-tag :type="methodTag(item.subtitle?.split(' ')[0] ?? '')" size="small" style="width:44px;text-align:center">{{ item.subtitle?.split(' ')[0] ?? '' }}</el-tag>

                <span class="result-title">{{ item.title }}</span>

                <span class="result-path">{{ item.subtitle }}</span>

              </div>

            </div>

            <div v-if="filteredResults.cases.length" class="result-group">

              <div class="result-group-label">{{ $t('search.cases') }}</div>

              <div

                v-for="(item, i) in filteredResults.cases"

                :key="item.id"

                class="result-item" tabindex="0"

                :class="{ active: activeIndex === filteredResults.apis.length + i }"

                @click="navigate(item)"

                @keydown.enter="navigate(item)"

                @mouseenter="activeIndex = filteredResults.apis.length + i"

              >

                <el-tag size="small" type="warning">{{ item.subtitle }}</el-tag>

                <span class="result-title">{{ item.title }}</span>

              </div>

            </div>

            <div v-if="filteredResults.scenes.length" class="result-group">

              <div class="result-group-label">{{ $t('search.scenes') }}</div>

              <div

                v-for="(item, i) in filteredResults.scenes"

                :key="item.id"

                class="result-item" tabindex="0"

                :class="{ active: activeIndex === filteredResults.apis.length + filteredResults.cases.length + i }"

                @click="navigate(item)"

                @keydown.enter="navigate(item)"

                @mouseenter="activeIndex = filteredResults.apis.length + filteredResults.cases.length + i"

              >

                <span class="result-title">{{ item.title }}</span>

                <span class="result-path">{{ item.subtitle }}</span>

              </div>

            </div>

            <div v-if="totalCount === 0" class="result-empty">{{ $t('search.noResults') }}</div>

          </template>



          <div class="search-loading" v-if="loading">

            <div class="loading-dot"></div>

            <span>{{ $t('search.searching') }}</span>

          </div>

        </div>



        <div class="search-hints">

          <span><kbd>↑</kbd><kbd>↓</kbd> 导航</span>

          <span><kbd>Enter</kbd> 跳转</span>

          <span><kbd>Ctrl+Enter</kbd> 新标签页</span>

          <span><kbd>Esc</kbd> 关闭</span>

        </div>

      </div>

    </div>

    </Teleport>

  </div>

</template>



<script setup lang="ts">

import { ref, watch, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import request from '../api/request'
import { msgError } from '../utils/message'
import { logger } from '../utils/logger'

import { useProjectStore } from '../stores/projectStore'
import type { SearchItem } from '../types'

const { t } = useI18n()



const props = defineProps<{ visible: boolean; projectId?: number }>()

const emit = defineEmits<{ 'update:visible': [v: boolean] }>()



const router = useRouter()

const projectStore = useProjectStore()

const keyword = ref('')

const loading = ref(false)

const activeIndex = ref(0)

const results = ref<{ apis: SearchItem[]; cases: SearchItem[]; scenes: SearchItem[] }>({ apis: [], cases: [], scenes: [] })

const panelRef = ref<HTMLDivElement>()
const inputRef = ref<HTMLInputElement>()

const recentSearches = ref<string[]>([])

const activeType = ref('all')
const filterTabs = computed(() => [
  { key: 'all', label: t('common.all') },
  { key: 'api', label: t('search.apis') },
  { key: 'case', label: t('search.cases') },
  { key: 'scene', label: t('search.scenes') },
])
const resultCountByType = computed(() => ({
  all: results.value.apis.length + results.value.cases.length + results.value.scenes.length,
  api: results.value.apis.length,
  case: results.value.cases.length,
  scene: results.value.scenes.length,
}))
const filteredResults = computed(() => {
  if (activeType.value === 'all') return results.value
  return {
    apis: activeType.value === 'api' ? results.value.apis : [],
    cases: activeType.value === 'case' ? results.value.cases : [],
    scenes: activeType.value === 'scene' ? results.value.scenes : [],
  }
})



const totalCount = computed(() => resultCountByType.value.all)



const RECENT_KEY = 'api_pilot_search_recent'



function loadRecent() {

  try {

    const raw = localStorage.getItem(RECENT_KEY)

    if (raw) recentSearches.value = JSON.parse(raw)

  } catch { /* noop */ }

}



function saveRecent(kw: string) {

  const arr = [kw, ...recentSearches.value.filter(s => s !== kw)].slice(0, 5)

  recentSearches.value = arr

  try { localStorage.setItem(RECENT_KEY, JSON.stringify(arr)) } catch { /* noop */ }

}



let _searchTimer: ReturnType<typeof setTimeout> | null = null

function doSearch(val: string) {
  activeType.value = 'all'
  loading.value = true
  activeIndex.value = 0

  request.get(`/projects/${props.projectId || projectStore.currentProjectId}/search`, {
    params: { keyword: val },
  }).then((res: { data: { results?: { apis?: unknown[]; cases?: unknown[]; scenes?: unknown[] }; apis?: unknown[]; cases?: unknown[]; scenes?: unknown[] } }) => {
    // 防御性解析：后端返回 { code: 0, data: { results: { apis:[], cases:[], scenes:[] }, total:N } }
    const raw = res?.data?.results ?? res?.data ?? res ?? {}
    results.value = {
      apis: Array.isArray(raw.apis) ? raw.apis : [],
      cases: Array.isArray(raw.cases) ? raw.cases : [],
      scenes: Array.isArray(raw.scenes) ? raw.scenes : [],
    }
  }).catch((err: unknown) => {
    logger.error('[SearchDialog] search failed:', err)
    msgError('搜索失败，请重试')
    results.value = { apis: [], cases: [], scenes: [] }
  }).finally(() => {
    loading.value = false
  })
}

watch(keyword, (val) => {
  // 清除上一个定时器
  if (_searchTimer) clearTimeout(_searchTimer)

  if (!val) {
    results.value = { apis: [], cases: [], scenes: [] }
    return
  }

  // 300ms 防抖
  _searchTimer = setTimeout(() => {
    doSearch(val)
  }, 300)
})

// 组件卸载时清理定时器
onBeforeUnmount(() => {
  if (_searchTimer) clearTimeout(_searchTimer)
})

function close() {

  emit('update:visible', false)

}



function onKeydown(e: KeyboardEvent) {

  if (e.key === 'Escape') close()

  else if (e.key === 'ArrowDown') {

    e.preventDefault()

    activeIndex.value = Math.min(activeIndex.value + 1, totalCount.value - 1)

    scrollIntoView()

  } else if (e.key === 'ArrowUp') {

    e.preventDefault()

    activeIndex.value = Math.max(activeIndex.value - 1, 0)

    scrollIntoView()

  } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {

    e.preventDefault()

    const allItems = getAllItems()

    if (allItems[activeIndex.value]) {

      const item = allItems[activeIndex.value]

      close()

      if (!props.projectId) return

      const url = item.type === 'api' ? `/projects/${props.projectId}/apis/detail/${item.id}`
        : item.type === 'case' ? `/projects/${props.projectId}/apis/case/${item.id}`
        : `/projects/${props.projectId}/scenes`
      window.open(`#${url}`, '_blank')

    }

  } else if (e.key === 'Enter') {

    e.preventDefault()

    const allItems = getAllItems()

    if (allItems[activeIndex.value]) navigate(allItems[activeIndex.value])

  }

}



function getAllItems() {

  return [...filteredResults.value.apis, ...filteredResults.value.cases, ...filteredResults.value.scenes]

}



function scrollIntoView() {

  const el = panelRef.value?.querySelector('.result-item.active') as HTMLElement

  el?.scrollIntoView({ block: 'nearest' })

}



function navigate(item: SearchItem) {

  close()

  if (!props.projectId) return

  saveRecent(keyword.value)

  if (item.type === 'api') {

    void router.push(`/projects/${props.projectId}/apis/detail/${item.id}`)

  } else if (item.type === 'case') {

    void router.push(`/projects/${props.projectId}/apis/case/${item.id}`)

  } else if (item.type === 'scene') {

    void router.push(`/projects/${props.projectId}/scenes`)

  }

}



function methodTag(m: string) {

  const map: Record<string, string> = { GET: 'success', POST: 'primary', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }

  return map[m?.toUpperCase()] || 'info'

}



onMounted(loadRecent)

watch(() => props.visible, (val) => {
  if (val) {
    void nextTick(() => { inputRef.value?.focus() })
  } else {
    keyword.value = ''
    results.value = { apis: [], cases: [], scenes: [] }
  }
})

</script>



<style scoped>
/* ===== 遮罩层 — 使用 z-popover 层级 + 品牌化模糊 ===== */
.search-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-black-alpha-45, rgba(0, 0, 0, 0.45));
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: var(--z-popover);
  animation: searchFadeIn var(--duration-fast) var(--ease-out);
}

@keyframes searchFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ===== 搜索面板 — 多层阴影 + 品牌化圆角 ===== */
.search-panel {
  width: 520px;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  /* 使用 shadow-lg token 替代多层阴影叠加 */
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: searchFadeIn var(--duration-slow) var(--ease-out);
}

/* ===== 搜索输入区域 ===== */
.search-input-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-4-5, 18px);
  /* 移除底部边框，改为更 subtle 的分隔 */
  border-bottom: 1px solid var(--border-subtle);
}

/* 搜索图标 */
.search-icon {
  width: 15px;
  height: 15px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 搜索输入框 */
.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: var(--text-md);
  color: var(--text-primary);
  background: transparent;
  font-family: inherit;
}
.search-input::placeholder {
  color: var(--text-muted);
}
/* 键盘焦点可见环 */
.search-input:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* ESC 提示标签 */
.search-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--surface-hover);
  padding: 2px var(--space-2);
  border-radius: var(--radius-xs);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
  border: 1px solid var(--border-subtle);
}

/* ===== 类型过滤 Tab ===== */
.search-type-tabs {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-4-5, 18px) var(--space-2-5, 10px);
  flex-shrink: 0;
}
.search-type-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2-5, 10px);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.search-type-tab:hover {
  border-color: var(--primary-300);
  color: var(--text-secondary);
  background: var(--surface-hover);
}
.search-type-tab.active {
  border-color: var(--primary-400);
  color: var(--primary-600);
  background: var(--color-primary-alpha-06);
  font-weight: var(--weight-bold);
}
/* 类型计数徽章 */
.type-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 14px;
  height: 14px;
  padding: 0 var(--space-1-5);
  border-radius: var(--radius-full);
  background: var(--color-neutral-alpha-08);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  line-height: 1;
}
.search-type-tab.active .type-count {
  background: var(--color-primary-alpha-12);
  color: var(--primary-600);
}

/* ===== 搜索结果区域 ===== */
.search-results {
  max-height: 340px;
  overflow-y: auto;
  padding: var(--space-1);
}

/* 结果分组标签 */
.result-group-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-2) var(--space-3) var(--space-1);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* 结果项 */
.result-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  min-height: 44px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth);
}
.result-item:hover {
  background: var(--surface-hover);
}
/* 激活状态 — 左侧主色指示条 */
.result-item.active {
  background: var(--color-primary-alpha-08);
  border-left: 2px solid var(--primary-500);
  padding-left: calc(var(--space-3) - 2px);
}
/* 键盘焦点可见环 */
.result-item:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: -2px;
}

/* 结果标题 */
.result-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

/* 结果路径 */
.result-path {
  font-size: var(--text-xs);
  color: var(--text-muted);
  flex-shrink: 0;
}

/* 空状态 */
.result-empty {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

/* 加载状态 */
.search-loading {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}
.loading-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-400);
}

/* ===== 底部快捷键提示 ===== */
.search-hints {
  padding: var(--space-2-5) var(--space-4-5, 18px);
  font-size: var(--text-xs);
  color: var(--text-muted);
  display: flex;
  gap: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-bg);
}
.search-hints kbd {
  background: var(--surface-hover);
  padding: 1px var(--space-2);
  border-radius: var(--radius-2xs);
  font-weight: var(--weight-semibold);
  border: 1px solid var(--border-subtle);
  font-family: inherit;
}

/* ===== 暗色模式适配 ===== */
html.dark .search-overlay {
  background: var(--color-black-alpha-60);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
html.dark .search-panel {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-lg);
}
html.dark .search-input-wrap {
  background: transparent;
  border-bottom-color: var(--border-subtle);
}
html.dark .search-input {
  color: var(--text-primary);
}
html.dark .search-input::placeholder {
  color: var(--text-muted);
}
html.dark .result-item:hover,
html.dark .result-item.active {
  background: var(--surface-hover);
}
html.dark .result-item.active {
  background: var(--color-primary-alpha-08);
  border-left-color: var(--primary-400);
}
html.dark .result-title {
  color: var(--text-primary);
}
html.dark .result-path {
  color: var(--text-muted);
}
html.dark .result-empty {
  color: var(--text-muted);
}
html.dark .search-loading {
  color: var(--text-muted);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  .search-overlay,
  .search-panel,
  .result-item,
  .loading-dot {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>



