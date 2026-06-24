<template>
  <div class="json-viewer">
    <template v-if="Array.isArray(data) && data.length">
      <div v-for="(item, i) in data" :key="i" class="json-row">
        <span class="json-key">{{ item.key }}:</span>
        <span class="json-value">
          <HighlightText :text="String(item.value)" />
        </span>
      </div>
    </template>
    <span v-else class="json-empty">-</span>
  </div>
</template>

<script setup lang="ts">
import HighlightText from "./common/HighlightText.vue"
interface JsonViewItem {
  key: string
  value: string
}

defineProps<{ data: JsonViewItem[] }>()
</script>

<style scoped>
/* JsonViewer 容器 — 代码块背景 + 圆角边框 */
.json-viewer {
  font-size: var(--font-size-xs);
  line-height: 1.6;
  background: var(--surface-code);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  max-height: 200px;
  overflow-y: auto;
  font-family: var(--font-mono);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              border-color var(--duration-fast) var(--ease-smooth);
}

/* JSON 行：键值对布局 */
.json-row {
  display: flex;
  gap: var(--space-2);
  padding: 2px 0;
  border-bottom: 1px solid var(--border-subtle);
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

.json-row:hover {
  background: var(--surface-hover);
  border-radius: var(--radius-xs, 2px);
}

.json-row:last-child {
  border-bottom: none;
}

/* JSON 键：主色 + 加粗 */
.json-key {
  color: var(--info);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
  min-width: 120px;
  word-break: break-all;
}

/* JSON 值：正文色 */
.json-value {
  color: var(--text-primary);
  word-break: break-all;
}

/* 空状态 */
.json-empty {
  color: var(--text-muted);
  font-style: italic;
}

/* 暗色模式适配 */
html.dark .json-viewer {
  background: var(--surface-code);
  border-color: var(--border-subtle);
}
html.dark .json-key {
  color: var(--info);
}
html.dark .json-value {
  color: var(--text-primary);
}
</style>
