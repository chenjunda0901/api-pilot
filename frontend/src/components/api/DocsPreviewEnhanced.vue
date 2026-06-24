<template>
  <div class="docs-preview">
    <div v-if="parsedParams.length" class="docs-section">
      <h4>Request Parameters</h4>
      <el-table :data="parsedParams" border size="small">
        <el-table-column prop="name" label="Name" min-width="120" />
        <el-table-column prop="type" label="Type" width="80" />
        <el-table-column prop="required" label="Required" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.required ? 'danger' : 'info'" size="small">{{ row.required ? 'Yes' : 'No' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="Description" min-width="150" show-overflow-tooltip />
      </el-table>
    </div>
    <div class="docs-section">
      <h4>Response Example</h4>
      <pre v-if="responseExample" class="code-block"><code>{{ formatted }}</code></pre>
      <EmptyState v-else illustration="empty" title="No response example" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps<{ params?: Record<string, unknown>[]; responseExample?: string|null }>()

const parsedParams = computed(() =>
  (props.params || []).map((p: Record<string, unknown>) => ({
    name: p.name || p.key || '',
    type: p.type || 'string',
    required: p.required !== false,
    description: p.description || p.value || '',
  }))
)

const formatted = computed(() => {
  if (!props.responseExample) return ''
  try { return JSON.stringify(JSON.parse(props.responseExample), null, 2) }
  catch { return props.responseExample }
})
</script>

<style scoped>
/* 增强文档预览 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角均使用 CSS 变量，确保暗色模式自动适配
 */
.docs-preview {
  padding: var(--spacing-sm) 0;
}

.docs-section {
  margin-bottom: var(--spacing-lg);
}

.docs-section h4 {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

/* 代码块 */
.code-block {
  background: var(--surface-code);
  color: var(--text-secondary);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  line-height: var(--leading-normal);
  overflow-x: auto;
  white-space: pre;
  border: 1px solid var(--border-subtle);
}

/* 滚动条美化 */
.code-block::-webkit-scrollbar {
  height: 8px;
}

.code-block::-webkit-scrollbar-track {
  background: transparent;
}

.code-block::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-2xs);
}

.code-block::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}
</style>
