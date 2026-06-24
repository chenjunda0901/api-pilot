<template>
  <div class="headers-table" ref="tableRef" @keydown="onContainerKeydown">
    <div class="ht-header">
      <span class="ht-col-check">启用</span>
      <span class="ht-col-key">Header 名</span>
      <span class="ht-col-value">Header 值</span>
      <span class="ht-col-action"></span>
    </div>
    <div class="ht-rows">
      <div v-for="(row, index) in modelValue" :key="index" class="ht-row" :class="{ 'ht-row-error': row.enabled && (!row.key?.trim() || !row.value?.trim()) }" :data-row-index="index">
        <span class="ht-col-check"><el-checkbox v-model="row.enabled" size="small" /></span>
        <span class="ht-col-key">
          <el-autocomplete
            v-model="row.key"
            :fetch-suggestions="suggestHeaders"
            size="small"
            placeholder="名称"
            :class="{ 'ht-field-error': row.enabled && !row.key?.trim() }"
            @keydown.tab="onCellTab($event, index, 'key')"
            @keydown.enter="onCellEnter(index, 'key')"
          />
        </span>
        <span class="ht-col-value">
          <VarAwareInput
            v-model="row.value"
            size="small"
            placeholder="值"
            aria-label="Header值"
            :class="{ 'ht-field-error': row.enabled && !row.value?.trim() }"
            @keydown.tab="onCellTab($event, index, 'value')"
            @keydown.enter="onCellEnter(index, 'value')"
          />
        </span>
        <span class="ht-col-action">
          <button class="ht-del" aria-label="删除" @click="remove(index)"><X :size="13" /></button>
        </span>
      </div>
    </div>
    <div class="ht-footer">
      <button class="ht-add" @click="addRow">
        <Plus :size="13" />
        <span>添加请求头</span>
      </button>
      <el-dropdown @command="addCommonHeader" trigger="click">
        <button class="ht-quick-btn ht-common-dropdown">
          <Plus :size="12" /> 常用头
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-for="h in COMMON_HEADERS" :key="h.name" :command="h">
              {{ h.name }} <span class="common-header-value">{{ h.value }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <div class="ht-quick">
        <button class="ht-quick-btn" @click="quickAdd('Content-Type', 'application/json')">JSON</button>
        <button class="ht-quick-btn" @click="quickAdd('Content-Type', 'application/x-www-form-urlencoded')">Form</button>
        <button class="ht-quick-btn" @click="quickAdd('Authorization', 'Bearer ')">Bearer</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, onBeforeUnmount } from 'vue'
import { X, Plus } from 'lucide-vue-next'
import VarAwareInput from './common/VarAwareInput.vue'

interface HeaderRow {
  key: string
  value: string
  enabled: boolean
}

const modelValue = defineModel<HeaderRow[]>({ default: () => [] })
const tableRef = ref<HTMLElement | null>(null)

onMounted(() => {
  if (modelValue.value.length === 0) {
    modelValue.value.push({ key: '', value: '', enabled: false })
  }
})


const commonHeaders = [
  { value: 'Content-Type' },
  { value: 'Authorization' },
  { value: 'Accept' },
  { value: 'User-Agent' },
  { value: 'X-Requested-With' },
  { value: 'Cache-Control' },
  { value: 'Cookie' },
  { value: 'Origin' },
  { value: 'Referer' },
]

const COMMON_HEADERS = [
  { name: 'Accept', value: 'application/json' },
  { name: 'Accept-Language', value: 'zh-CN,zh;q=0.9' },
  { name: 'Content-Type', value: 'application/json; charset=utf-8' },
  { name: 'User-Agent', value: 'API-Pilot/1.0' },
  { name: 'Cache-Control', value: 'no-cache' },
  { name: 'Authorization', value: 'Bearer {{ token }}' },
  { name: 'X-Requested-With', value: 'XMLHttpRequest' },
  { name: 'X-Custom-Header', value: '' },
]

function suggestHeaders(query: string, cb: (items: { value: string }[]) => void) {
  const filtered = commonHeaders.filter(
    (h) => h.value.toLowerCase().includes(query.toLowerCase()),
  )
  cb(filtered)
}

function addRow() {
  modelValue.value.push({ key: '', value: '', enabled: false })
}

function remove(index: number) {
  modelValue.value.splice(index, 1)
  if (modelValue.value.length === 0) {
    modelValue.value.push({ key: '', value: '', enabled: false })
  }
}

function quickAdd(key: string, value: string) {
  const existing = modelValue.value.find((h: HeaderRow) => h.key === key)
  if (existing) {
    existing.value = value
  } else {
    modelValue.value.push({ key, value, enabled: true })
  }
}

function addCommonHeader(header: { name: string; value: string }) {
  quickAdd(header.name, header.value)
}

// ── Tab 键导航 ──
const focusTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function scheduleFocus(fn: () => void, delay: number) {
  if (focusTimer.value) clearTimeout(focusTimer.value)
  focusTimer.value = setTimeout(fn, delay)
}

/** Tab 导航顺序：key → value → 下一行 key */
function onCellTab(e: KeyboardEvent, index: number, field: 'key' | 'value') {
  e.preventDefault()
  if (field === 'key') {
    // key → value
    scheduleFocus(() => focusRowField(index, 'value'), 30)
  } else {
    // value → 下一行 key
    const isLast = index === modelValue.value.length - 1
    if (isLast) {
      addRow()
      scheduleFocus(() => focusRowField(modelValue.value.length - 1, 'key'), 50)
    } else {
      scheduleFocus(() => focusRowField(index + 1, 'key'), 30)
    }
  }
}

/** Enter 换行 */
function onCellEnter(index: number, _field: 'key' | 'value') {
  const isLast = index === modelValue.value.length - 1
  if (isLast) addRow()
  scheduleFocus(() => focusRowField(Math.min(index + 1, modelValue.value.length - 1), 'key'), 50)
}

/** 上下箭头导航 */
function onContainerKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement
  if (!target) return
  const row = target.closest('[data-row-index]') as HTMLElement
  if (!row) return
  const index = Number(row.dataset.rowIndex)
  if (e.key === 'ArrowUp' && index > 0) {
    e.preventDefault()
    scheduleFocus(() => focusRowField(index - 1, 'key'), 30)
  }
  if (e.key === 'ArrowDown' && index < modelValue.value.length - 1) {
    e.preventDefault()
    scheduleFocus(() => focusRowField(index + 1, 'key'), 30)
  }
}

function focusRowField(rowIndex: number, field: 'key' | 'value') {
  const root = tableRef.value
  if (!root) return
  const row = root.querySelector(`[data-row-index="${rowIndex}"]`) as HTMLElement
  if (!row) return
  const selector = field === 'key' ? '.ht-col-key input' : '.ht-col-value input, .ht-col-value .vai-preview'
  const input = row.querySelector(selector) as HTMLElement
  if (input) {
    input.focus()
    if (input.tagName === 'INPUT') (input as HTMLInputElement).select()
  }
}

onBeforeUnmount(() => {
  if (focusTimer.value) clearTimeout(focusTimer.value)
})

/** 校验已启用的请求头是否完整，返回错误消息列表 */
defineExpose({
  validate(): string[] {
    const errors: string[] = []
    modelValue.value.forEach((row: HeaderRow, index: number) => {
      if (row.enabled) {
        const key = row.key?.trim() || ''
        const value = row.value?.trim() || ''
        // key 和 value 都为空：视为未填写的占位行，跳过
        if (key && !value) errors.push(`第 ${index + 1} 个请求头缺少值`)
        else if (!key && value) errors.push(`第 ${index + 1} 个请求头缺少名称`)
      }
    })
    return errors
  },
})

</script>

<style scoped>
/* ==========================================
 * HeadersTable — 请求头表格样式
 * ========================================== */

.headers-table {
  display: flex;
  flex-direction: column;
}

/* 表头 */
.ht-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-2);
  background: var(--surface-nested);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.ht-header .ht-col-check,
.ht-header .ht-col-key,
.ht-header .ht-col-value {
  display: flex;
  align-items: center;
}

.ht-header .ht-col-check { width: var(--min-w-col-check); flex-shrink: 0; gap: var(--space-1); }
.ht-header .ht-col-key { flex: 0 0 25%; min-width: var(--min-w-input-sm); }
.ht-header .ht-col-value { flex: 1; min-width: 180px; }
.ht-header .ht-col-action { width: 32px; flex-shrink: 0; justify-content: center; }

.ht-col-check { width: var(--min-w-col-check); flex-shrink: 0; display: flex; align-items: center; gap: var(--space-1); }
.ht-col-key { flex: 0 0 25%; min-width: var(--min-w-input-sm); display: flex; }
.ht-col-value { flex: 1; min-width: 180px; display: flex; }
.ht-col-action { width: 32px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }

/* 行容器 */
.ht-rows {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

/* 行样式 */
.ht-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  min-height: var(--height-input);
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.ht-row:hover {
  background: var(--surface-hover);
}

.ht-row-error {
  background: var(--color-error-alpha-04);
}

/* 单项必填校验红框 */
.ht-field-error :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--error) inset !important;
}

/* 输入框样式 */
/* 强制key/value列内部组件撑满 */
.ht-col-key > :deep(.el-autocomplete),
.ht-col-key > :deep(.el-input),
.ht-col-value > :deep(.var-aware-input),
.ht-col-value > :deep(.el-input) {
  width: 100%;
}
.ht-row .ht-col-value {
  align-items: center;
}
/* 强制值列 VarAwareInput 容器与名列 el-autocomplete 垂直对齐 */
.ht-row :deep(.var-aware-input) {
  display: flex;
  align-items: center;
  height: 35px;
  align-self: center;
}
.ht-row :deep(.var-aware-input .el-input) {
  height: 35px;
}
.ht-row :deep(.var-aware-input .el-input .el-input__wrapper) {
  height: 35px !important;
}
.ht-row :deep(.var-aware-input .el-input) {
  width: 100% !important;
  flex: 1 1 0% !important;
}

.ht-row :deep(.el-input__wrapper) {
  border-radius: var(--radius-sm);
  box-shadow: 0 0 0 1px var(--border-default) inset;
  background: var(--surface-card);
  transition: color, border-color, background-color, box-shadow var(--duration-fast);
  height: 35px;
}
.ht-row :deep(.el-autocomplete) {
  width: 100%;
}
.ht-row :deep(.el-autocomplete .el-input__wrapper) {
  height: 32px !important;
}
.ht-row :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--primary-300) inset;
}
.ht-row :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-400) inset;
  border-color: var(--primary-400);
}
.ht-row :deep(.el-input__inner) {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-primary);
}
.ht-row :deep(.el-checkbox) {
  height: 32px;
}

/* 值列 VarAwareInput 预览层增强 */
.ht-row :deep(.var-aware-input .vai-preview) {
  height: 32px;
  padding: 3px 8px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  transition: border-color var(--duration-fast), background-color var(--duration-fast);
}
.ht-row :deep(.var-aware-input .vai-preview:hover) {
  border-color: var(--primary-300);
  background: var(--surface-hover);
}
.ht-row :deep(.var-aware-input .vai-text) {
  font-size: var(--text-xs);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
.ht-row :deep(.var-aware-input .vai-var-tag) {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border: 1px solid var(--color-primary-alpha-16);
}
.ht-row :deep(.var-aware-input .vai-placeholder) {
  font-size: var(--text-xs);
  color: var(--text-disabled);
}

/* 必填校验红框 */
.ht-row-error :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--error) inset;
}
.ht-row-error :deep(.el-autocomplete .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--error) inset;
}

.ht-del {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-disabled);
  cursor: pointer;
  transition: color, border-color, background-color, box-shadow var(--duration-fast);
}
.ht-del:hover {
  background: var(--color-error-alpha-08);
  color: var(--color-error-text);
}

.ht-empty {
  text-align: center;
  padding: var(--space-10) 16px;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.ht-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-2);
}

.ht-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-2) 14px;
  min-height: 34px;
  background: none;
  border: 1.5px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: color, border-color, background-color, box-shadow var(--duration-fast);
}
.ht-add:hover {
  border-color: var(--primary-300);
  color: var(--primary-600);
  background: var(--color-primary-alpha-04);
  box-shadow: 0 1px 4px var(--color-primary-alpha-12);
}

.ht-quick {
  display: flex;
  gap: var(--space-1);
}
.ht-quick-btn {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface-nested);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: color, border-color, background-color, box-shadow var(--duration-fast);
}
.ht-quick-btn:hover {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border-color: var(--primary-300);
  box-shadow: 0 1px 4px var(--color-primary-alpha-12);
}
.ht-common-dropdown {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.common-header-value {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  margin-left: var(--space-2);
  font-family: var(--font-mono);
}
</style>