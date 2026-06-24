<template>
  <div class="param-tabs">
    <div class="tab-group tab-group-core">
      <button
        v-for="tab in coreTabs"
        :key="tab.key"
        class="param-tab"
        :class="{ active: activeTab === tab.key }"
        tabindex="0"
        @click="emit('update:activeTab', tab.key)"
        @keydown.enter="emit('update:activeTab', tab.key)"
      >
        {{ tab.label }}
        <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
      </button>
    </div>

    <div class="tab-divider"></div>

    <div class="tab-group tab-group-secondary">
      <button
        v-for="tab in secondaryTabs"
        :key="tab.key"
        class="param-tab"
        :class="{ active: activeTab === tab.key }"
        tabindex="0"
        @click="emit('update:activeTab', tab.key)"
        @keydown.enter="emit('update:activeTab', tab.key)"
      >
        {{ tab.label }}
        <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
      </button>
    </div>

    <div class="tab-group tab-group-advanced">
      <el-dropdown trigger="click" @command="handleAdvancedTab">
        <button class="param-tab param-tab-more">
          <MoreHorizontal :size="14" />
          <span>更多</span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="tab in advancedTabs"
              :key="tab.key"
              :command="tab.key"
              :class="{ 'is-active': activeTab === tab.key }"
            >
              {{ tab.label }}
              <span v-if="tab.count > 0" class="dropdown-badge">{{ tab.count }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MoreHorizontal } from 'lucide-vue-next'

interface ParamTabApi {
  method?: string
  path?: string
  body?: {
    type: string
    content?: string | unknown[]
    enabled?: boolean
  }
  params?: { key: string; value: string; enabled?: boolean }[]
  headers?: { key: string; value: string; enabled?: boolean }[]
  pre_script?: string
  post_script?: string
  assertions?: unknown[]
  case_count?: number
}

const props = defineProps<{
  api: ParamTabApi
  activeTab: string
}>()

const emit = defineEmits<{
  'update:activeTab': [key: string]
}>()

const bodyCount = computed(() => {
  const body = props.api?.body
  if (!body || body.type === 'none') return 0
  if (body.type === 'form-data' || body.type === 'x-www-form-urlencoded') {
    let items: { enabled?: boolean }[] = []
    if (Array.isArray(body.content)) {
      items = body.content
    } else if (typeof body.content === 'string') {
      try { items = JSON.parse(body.content) } catch { items = [] }
    }
    return items.filter((item: { enabled?: boolean }) => item.enabled !== false).length
  }
  return body.content ? 1 : 0
})

const coreTabs = computed(() => [
  { key: 'params', label: '参数', count: Array.isArray(props.api.params) ? props.api.params.length : 0 },
  { key: 'body', label: '请求体', count: bodyCount.value },
  { key: 'headers', label: '请求头', count: Array.isArray(props.api.headers) ? props.api.headers.filter((h: { enabled?: boolean }) => h.enabled !== false).length : 0 },
  { key: 'auth', label: '认证', count: 0 },
])

const secondaryTabs = computed(() => [
  { key: 'cases', label: '用例', count: props.api.case_count || 0 },
  { key: 'assertions', label: '断言', count: Array.isArray(props.api.assertions) ? props.api.assertions.length : 0 },
  { key: 'docs', label: '文档', count: 0 },
])

const advancedTabs = computed(() => [
  { key: 'response-examples', label: '响应示例', count: 0 },
  { key: 'extract-vars', label: '提取变量', count: 0 },
  { key: 'pre-script', label: '前置操作', count: props.api.pre_script ? 1 : 0 },
  { key: 'post-script', label: '后置操作', count: props.api.post_script ? 1 : 0 },
  { key: 'settings', label: '设置', count: 0 },
  { key: 'docs-preview', label: '文档预览', count: 0 },
  { key: 'history', label: '历史版本', count: 0 },
])

function handleAdvancedTab(key: string) {
  emit('update:activeTab', key)
}
</script>

<style scoped>
/* 参数标签页 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角均使用 CSS 变量，确保暗色模式自动适配
 */
.param-tabs {
  display: flex;
  align-items: center;
  gap: 0;
  min-height: 36px;
  padding: 0 var(--spacing-lg) var(--spacing-sm);
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--surface-card);
}

.param-tabs::-webkit-scrollbar { display: none; }

.tab-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.tab-group-secondary { margin-left: var(--spacing-md); }
.tab-group-advanced { margin-left: auto; }

/* 标签分隔线 */
.tab-divider {
  width: 1px;
  height: 20px;
  margin: 0 var(--spacing-md);
  background: var(--border-subtle);
  flex-shrink: 0;
}

/* 标签按钮 */
.param-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 var(--spacing-md);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast) var(--ease-smooth);
}

.param-tab:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

/* 焦点态：主色环 */
.param-tab:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

/* 激活态：主色背景 + 底部指示条 */
.param-tab.active {
  background: var(--color-primary-alpha-08);
  border-bottom: 2px solid var(--primary-500);
  border-color: var(--primary-500) var(--color-primary-alpha-16) var(--primary-500) var(--color-primary-alpha-16);
  color: var(--primary-700);
  font-weight: var(--weight-semibold);
}

.param-tab-more {
  color: var(--text-muted);
  padding: 0 var(--spacing-md);
}

/* 计数徽章 */
.tab-badge,
.dropdown-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--surface-nested);
  color: var(--text-muted);
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  line-height: 1;
}

.param-tab.active .tab-badge {
  background: var(--color-primary-alpha-12);
  color: var(--primary-700);
}

:deep(.el-dropdown-menu-item.is-active) {
  color: var(--primary-600);
  background: var(--color-primary-alpha-06);
}

html.dark .param-tabs {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
html.dark .param-tab:hover { background: var(--surface-hover); }
html.dark .param-tab.active {
  background: var(--color-primary-alpha-10);
  border-color: var(--color-primary-alpha-18);
  color: var(--primary-300);
}
html.dark .tab-divider { background: var(--border-subtle); }
</style>
