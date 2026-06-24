<template>
  <div class="script-tab">
    <div class="script-header">
      <div class="script-header-left">
        <span class="script-icon">JS</span>
        <span class="script-label">{{ title }}</span>
      </div>
      <div class="script-header-right">
        <el-dropdown trigger="click" @command="(code: string) => $emit('insert-snippet', code)">
          <el-button size="small" class="snippet-btn">
            代码片段 <ChevronDown :size="12" />
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="s in snippets" :key="s.label" :command="s.code">
                {{ s.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <span class="script-desc">{{ description }}</span>
      </div>
    </div>
    <div class="script-editor-wrapper">
      <slot name="editor">
        <CodeEditor
          :model-value="modelValue"
          language="javascript"
          :placeholder="placeholder"
          height="220px"
          @update:model-value="$emit('update:modelValue', $event)"
        />
      </slot>
    </div>
    <div class="script-tips">
      <span class="script-tip">
        可用对象:
        <code v-for="obj in availableObjects" :key="obj">pm.{{ obj }}</code>
      </span>
    </div>
    <!-- 调试控制台 -->
    <div class="script-debug-panel">
      <div class="script-debug-header" @click="$emit('toggle-debug')">
        <span>调试控制台</span>
        <ChevronDown :size="14" :class="{ rotated: debugOpen }" />
      </div>
      <div v-if="debugOpen" class="script-debug-body">
        <EmptyState
          v-if="!debugLogs.length"
          illustration="empty"
          title="暂无日志"
          description="执行后在此显示 console.log 输出"
        />
        <div v-else class="script-debug-logs">
          <div v-for="(log, i) in debugLogs" :key="i" class="script-debug-log-line">
            <span class="log-time">{{ log.time }}</span>
            <span :class="['log-level', log.level]">{{ log.level }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next'
import CodeEditor from '@/components/CodeEditor.vue'
import EmptyState from '@/components/EmptyState.vue'

export interface DebugLog {
  time: string
  level: string
  message: string
}

export interface ScriptSnippet {
  label: string
  code: string
}

defineProps<{
  modelValue: string
  title: string
  description: string
  placeholder: string
  snippets: ScriptSnippet[]
  availableObjects: string[]
  debugOpen: boolean
  debugLogs: DebugLog[]
}>()

defineEmits<{
  'update:modelValue': [value: string]
  'insert-snippet': [code: string]
  'toggle-debug': []
}>()
</script>

<style scoped>
/* 脚本标签页布局 — 直接从 ApiDetail.vue 提取 */
.script-tab {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.script-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.script-header-left,
.script-header-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.script-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-xs);
  background: var(--color-warning-100);
  color: var(--color-warning-700);
  font-size: 11px;
  font-weight: var(--weight-bold);
}
.script-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}
.script-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.snippet-btn {
  font-size: var(--text-xs);
}
.script-editor-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.script-tips {
  padding: var(--space-2) 0;
}
.script-tip {
  font-size: var(--text-xs);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.script-tip code {
  font-size: var(--text-xs);
  background: var(--surface-nested);
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  color: var(--primary-600);
}
.script-debug-panel {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.script-debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  cursor: pointer;
  background: var(--surface-nested);
  user-select: none;
}
.script-debug-header:hover {
  background: var(--surface-hover);
}
.script-debug-header svg {
  transition: transform var(--duration-fast) var(--ease-soft);
}
.script-debug-header svg.rotated {
  transform: rotate(180deg);
}
.script-debug-body {
  padding: var(--space-3);
  max-height: 200px;
  overflow-y: auto;
}
.script-debug-logs {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.script-debug-log-line {
  display: flex;
  gap: var(--space-2);
  padding: 2px 0;
}
.log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}
.log-level {
  flex-shrink: 0;
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
}
.log-level.info { color: var(--color-info-600); }
.log-level.warn { color: var(--color-warning-600); }
.log-level.error { color: var(--color-error-600); }
.log-message {
  color: var(--text-secondary);
  word-break: break-all;
}
</style>
