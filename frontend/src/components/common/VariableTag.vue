<template>
  <el-tooltip :content="tooltipContent" placement="top" :show-after="300" :disabled="!hasVariable">
    <span class="variable-tag">
      <span class="var-brace">{{ value }}</span>
    </span>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useEnvStore } from '../../stores/envStore'

const props = defineProps<{ value: string }>()
const envStore = useEnvStore()

const hasVariable = computed(() => {
  return /\{\{\s*[^}]+\s*\}\}/.test(props.value)
})

const tooltipContent = computed(() => {
  const match = props.value.match(/\{\{\s*([^}]+)\s*\}\}/)
  if (!match) return props.value
  const varName = match[1].trim()
  const env = envStore.currentEnv
  if (env) {
    const vars = (env as { variables: { key: string; value: string }[] }).variables || []
    const found = vars.find((v: { key: string; value: string }) => v.key === varName)
    if (found) {
      return `${varName} = ${found.value}`
    }
  }
  return `${varName} = (未定义)`
})
</script>

<style scoped>
/* ==========================================
 * VariableTag — 变量标签样式
 * ==========================================
 * 用于在输入框中显示变量占位符（如 {{token}}）
 * 悬停时显示变量值的 tooltip
 * ========================================== */

.variable-tag {
  background: var(--color-primary-alpha-08);
  color: var(--primary-700);
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-1);
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  cursor: pointer;
  transition: opacity var(--duration-fast) var(--ease-smooth),
              background var(--duration-fast) var(--ease-smooth);
  text-decoration: underline dotted var(--color-primary-alpha-30);
  text-underline-offset: 2px;
  line-height: 1.4;
  max-width: 100%;
}
.variable-tag:hover {
  opacity: 0.85;
  background: var(--color-primary-alpha-12);
}
.variable-tag:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 1px;
}

/* 变量占位符文字（如 {{token}}） */
.var-brace {
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
