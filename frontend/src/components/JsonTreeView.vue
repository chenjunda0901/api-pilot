<template>
  <div class="json-tree-view">
    <json-tree-node
      v-for="(item, index) in treeData"
      :key="index"
      :node="item"
      :depth="0"
      :is-last="index === treeData.length - 1"
      @extract-variable="onExtractVariable"
    />
    <div v-if="!treeData.length" class="json-empty">(空)</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import JsonTreeNode from './JsonTreeNode.vue'

interface TreeNode {
  key: string | null
  value: string | null
  type: 'string' | 'number' | 'boolean' | 'null' | 'object' | 'array'
  children: TreeNode[]
  size: number
}

const props = defineProps<{
  data: Record<string, unknown> | unknown[]
  projectId?: number
}>()

const emit = defineEmits<{
  (e: 'extract-variable', payload: { name: string; value: string; path: string }): void
}>()

function buildTree(value: unknown, key: string | null = null, seen: WeakSet<object> = new WeakSet()): TreeNode {
  if (value === null || value === undefined) {
    return { key, value: 'null', type: 'null', children: [], size: 0 }
  }
  const type = typeof value
  if (type === 'string') {
    return { key, value: JSON.stringify(value), type: 'string', children: [], size: 0 }
  }
  if (type === 'number') {
    const n = value as number
    return { key, value: String(n), type: 'number', children: [], size: 0 }
  }
  if (type === 'boolean') {
    const b = value as boolean
    return { key, value: String(b), type: 'boolean', children: [], size: 0 }
  }
  if (type === 'object' && value !== null) {
    if (seen.has(value)) {
      return { key, value: '[Circular]', type: 'string', children: [], size: 0 }
    }
    seen.add(value)
  }
  if (Array.isArray(value)) {
    const children = value.map((v, i) => buildTree(v, String(i), seen))
    return { key, value: null, type: 'array', children, size: children.length }
  }
  if (type === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    const children = entries.map(([k, v]) => buildTree(v, k, seen))
    return { key, value: null, type: 'object', children, size: children.length }
  }
  const s = value as string
  return { key, value: String(s), type: 'string', children: [], size: 0 }
}

const treeData = computed(() => {
  const node = buildTree(props.data)
  return node.children
})

async function onExtractVariable(payload: { path: string; value: string }) {
  // 根据 JSON 路径生成默认变量名
  const defaultName = payload.path
    .replace(/\./g, '_')
    .replace(/\[(\d+)\]/g, '_$1')
    .toUpperCase()

  try {
    const { value: name } = await ElMessageBox.prompt('请输入变量名称', '提取为变量', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputValue: defaultName,
      inputPattern: /^[a-zA-Z_$][a-zA-Z0-9_$]*$/,
      inputErrorMessage: '变量名只能包含字母、数字和下划线，且不能以数字开头',
    })
    emit('extract-variable', { name, value: payload.value, path: payload.path })
  } catch {
    // 取消操作
  }
}
</script>

<style scoped>
/* JsonTreeView 容器 — 等宽字体 + 内边距 */
.json-tree-view {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  line-height: 1.6;
  padding: var(--space-2) var(--space-1);
  overflow: auto;
  max-height: 100%;
  background: var(--surface-code);
  border-radius: var(--radius-md);
}

/* 空状态：居中显示 */
.json-empty {
  padding: var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--font-size-xs);
  font-style: italic;
}

/* 暗色模式适配 */
html.dark .json-tree-view {
  background: var(--surface-code);
}
</style>
