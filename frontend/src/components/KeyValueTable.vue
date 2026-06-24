<template>
  <div class="kvt" ref="containerRef" @keydown="onContainerKeydown">
    <div class="kvt-header">
      <span class="kvt-col-check">启用</span>
      <span class="kvt-col-key">{{ keyLabel }}</span>
      <span class="kvt-col-value">{{ valueLabel }}</span>
      <span class="kvt-col-action"></span>
    </div>
    <div v-if="items.length > 0" class="kvt-rows">
      <div
        v-for="(item, index) in items"
        :key="index"
        class="kvt-row"
        :ref="(el: HTMLElement | null) => setRowRef(el, index)"
        :class="{
          'kvt-row-disabled': !item.enabled,
          'kvt-row-placeholder': index === items.length - 1 && !item.key && !item.value,
          'kvt-row-focused': focusedRowIndex === index
        }"
        :data-row-index="index"
        @click="focusedRowIndex = index"
      >
        <span class="kvt-col-check"><el-checkbox v-model="item.enabled" size="small" /></span>
        <span class="kvt-col-key">
          <el-input
            v-model="item.key"
            size="small"
            :placeholder="keyPlaceholder"
            class="kvt-input"
            @input="onKeyInput(index)"
            @keydown.tab="onCellTab($event, index, 'key')"
            @keydown.enter="onCellEnter(index, 'key')"
          />
        </span>
        <span class="kvt-col-value">
          <VarAwareInput
            v-model="item.value"
            size="small"
            :placeholder="valuePlaceholder"
            class="kvt-input"
            @input="onValueInput(index)"
            @keydown.tab="onCellTab($event, index, 'value')"
            @keydown.enter="onCellEnter(index, 'value')"
            @keydown.delete="onCellDelete($event, index)"
          />
        </span>
        <span class="kvt-col-action">
          <button class="kvt-del" @click="remove(index)" title="删除" aria-label="删除"><X :size="13" /></button>
        </span>
      </div>
    </div>
    <div class="kvt-toolbar">
      <button class="kvt-add" @click="addRow">
        <Plus :size="13" />
        <span>{{ addText }}</span>
      </button>
      <span class="kvt-hint" v-if="items.length > 1">Tab 切换单元格 · Enter 换行 · Delete 删除空行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { X, Plus } from 'lucide-vue-next'
import VarAwareInput from './common/VarAwareInput.vue'

interface KVPair {
  key: string
  value: string
  enabled: boolean
}

const props = withDefaults(defineProps<{
  modelValue?: KVPair[]
  keyLabel?: string
  valueLabel?: string
  keyPlaceholder?: string
  valuePlaceholder?: string
  addText?: string
}>(), {
  modelValue: () => [],
  keyLabel: '',
  valueLabel: '',
  keyPlaceholder: '',
  valuePlaceholder: '',
  addText: '',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: KVPair[]): void
}>()

const items = ref<KVPair[]>([])
const containerRef = ref<HTMLElement | null>(null)
const focusedRowIndex = ref(0)
const rowRefs = ref<Record<number, HTMLElement>>({})

function setRowRef(el: HTMLElement | null, index: number) {
  if (el) rowRefs.value[index] = el
}

watch(() => props.modelValue, (val) => {
  const arr = val || []
  if (arr.length > 0) {
    items.value = arr.map((v: KVPair) => ({ ...v }))
  } else {
    items.value = []
  }
}, { immediate: true })

watch(items, (val) => {
  emit('update:modelValue', val.map(v => ({ ...v })))
}, { deep: true })

onMounted(() => {
  if (items.value.length === 0) {
    items.value.push({ key: '', value: '', enabled: false })
  }
})

// 自动增行：key 或 value 输入内容时最后一行自动新增
function onKeyInput(index: number) {
  autoAddRow(index)
}
function onValueInput(index: number) {
  autoAddRow(index)
}

function autoAddRow(index: number) {
  const isLast = index === items.value.length - 1
  if (isLast && (items.value[index].key?.trim() || items.value[index].value?.trim())) {
    items.value.push({ key: '', value: '', enabled: true })
  }
}

function addRow() {
  items.value.push({ key: '', value: '', enabled: true })
  focusedRowIndex.value = items.value.length - 1
}

function remove(index: number) {
  if (items.value.length === 1 && !items.value[0].key && !items.value[0].value) return
  items.value.splice(index, 1)
  focusedRowIndex.value = Math.min(focusedRowIndex.value, items.value.length - 1)
  if (items.value.length === 0) {
    items.value.push({ key: '', value: '', enabled: false })
    focusedRowIndex.value = 0
  }
}

// 键盘导航
const focusTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function scheduleFocus(fn: () => void, delay: number) {
  if (focusTimer.value) clearTimeout(focusTimer.value)
  focusTimer.value = setTimeout(fn, delay)
}

function onCellTab(e: KeyboardEvent, index: number, _field: 'key' | 'value') {
  e.preventDefault()
  const isLast = index === items.value.length - 1
  if (isLast) {
    // 最后一行，Tab 新增行
    autoAddRow(index)
    focusedRowIndex.value = items.value.length - 1
    // 聚焦新行的 key
    scheduleFocus(() => focusRowField(items.value.length - 1, 'key'), 50)
  } else {
    focusedRowIndex.value = index + 1
    scheduleFocus(() => focusRowField(index + 1, 'key'), 50)
  }
}

function onCellEnter(index: number, _field: 'key' | 'value') {
  // Enter 新增一行并跳到新行
  autoAddRow(index)
  focusedRowIndex.value = items.value.length - 1
  scheduleFocus(() => focusRowField(items.value.length - 1, 'key'), 50)
}

function onCellDelete(_e: KeyboardEvent, index: number) {
  const item = items.value[index]
  if (!item.key?.trim() && !item.value?.trim() && items.value.length > 1) {
    remove(index)
  }
}

function onContainerKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowUp' && focusedRowIndex.value > 0) {
    e.preventDefault()
    focusedRowIndex.value--
    scheduleFocus(() => focusRowField(focusedRowIndex.value, 'key'), 30)
  }
  if (e.key === 'ArrowDown' && focusedRowIndex.value < items.value.length - 1) {
    e.preventDefault()
    focusedRowIndex.value++
    scheduleFocus(() => focusRowField(focusedRowIndex.value, 'key'), 30)
  }
}

function focusRowField(rowIndex: number, field: 'key' | 'value') {
  const row = rowRefs.value[rowIndex]
  if (!row) return
  const cellSelector = field === 'key' ? '.kvt-col-key input' : '.kvt-col-value input, .kvt-col-value .vai-preview'
  const input = row.querySelector(cellSelector) as HTMLElement
  if (input) {
    input.focus()
    if (input.tagName === 'INPUT') {
      (input as HTMLInputElement).select()
    }
  }
}

onBeforeUnmount(() => {
  if (focusTimer.value) clearTimeout(focusTimer.value)
})
</script>

<style scoped>
/* ==========================================
 * KeyValueTable — 通用键值对表格样式
 * ========================================== */

.kvt {
  display: flex;
  flex-direction: column;
}

/* 表头 */
.kvt-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.kvt-col-check { width: var(--min-w-col-check); flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
.kvt-col-key { flex: 2; min-width: var(--min-w-input-sm); display: flex; }
.kvt-col-value { flex: 3; min-width: 180px; display: flex; }
.kvt-col-action { width: var(--size-icon-lg); flex-shrink: 0; }

/* 行容器 */
.kvt-rows {
  display: flex;
  flex-direction: column;
}

/* 行样式 */
.kvt-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-3);
  min-height: var(--height-input);
  border-bottom: 1px solid var(--border-default);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.kvt-row:last-child { border-bottom: none; }
.kvt-row:hover { background: var(--surface-hover); }
.kvt-row.kvt-row-disabled { opacity: 0.45; }

.kvt-row-disabled .kvt-col-key .kvt-input :deep(.el-input__inner),
.kvt-row-disabled .kvt-col-value .kvt-input :deep(.el-input__inner) {
  text-decoration: line-through;
}

.kvt-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-xs);
  box-shadow: none;
  background: transparent;
  padding: 0 calc(var(--space-2) - 2px);
}
.kvt-input :deep(.el-input__wrapper:hover) {
  background: var(--surface-hover);
}
.kvt-input :deep(.el-input__wrapper.is-focus) {
  background: var(--surface-card);
  box-shadow: 0 0 0 1px var(--primary-300) inset;
}
.kvt-input :deep(.el-input__inner) {
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-primary);
}
.kvt-row :deep(.el-checkbox__inner) {
  border-radius: var(--radius-2xs);
}

/* 值列 VarAwareInput 预览层增强 */
.kvt-row :deep(.var-aware-input) {
  display: flex;
  align-items: center;
  height: 32px;
  align-self: center;
}
.kvt-row :deep(.var-aware-input .el-input .el-input__wrapper) {
  height: 32px !important;
}
.kvt-row :deep(.var-aware-input .el-input) {
  width: 100% !important;
  flex: 1 1 0% !important;
}

.kvt-row :deep(.var-aware-input .vai-preview) {
  min-height: 28px;
  padding: 3px var(--space-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xs);
  background: transparent;
  transition: border-color var(--duration-fast), background-color var(--duration-fast);
}
.kvt-row :deep(.var-aware-input .vai-preview:hover) {
  border-color: var(--primary-300);
  background: var(--surface-hover);
}
.kvt-row :deep(.var-aware-input .vai-text) {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
.kvt-row :deep(.var-aware-input .vai-var-tag) {
  font-size: var(--text-xs);
  padding: 1px 6px;
  background: var(--color-primary-alpha-08);
  color: var(--primary-700);
  border: 1px solid var(--color-primary-alpha-15);
}

.kvt-del {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--size-icon-md);
  height: 32px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-disabled);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--duration-fast), background-color var(--duration-fast), color var(--duration-fast);
}
.kvt-row:hover .kvt-del { opacity: 1; }
/* 触控设备始终显示删除按钮 */
@media (hover: none) {
  .kvt-del { opacity: 1; }
}
/* Focus 状态始终显示 */
.kvt-del:focus { opacity: 1; }
.kvt-row:has(.kvt-del:focus) .kvt-del { opacity: 1; }
.kvt-del:hover {
  background: var(--color-error-alpha-08);
  color: var(--color-error-text);
}

.kvt-row-placeholder { opacity: 0.5; transition: opacity var(--duration-fast); }
.kvt-row-placeholder:focus-within { opacity: 1; }
.kvt-row-focused {
  background: var(--color-primary-alpha-06) !important;
  border-color: var(--primary-200);
  border-radius: var(--radius-xs);
}
.kvt-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-4);
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
}

.kvt-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  flex: 0 1 auto;
  min-width: 120px;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition:
    color var(--duration-fast),
    border-color var(--duration-fast),
    background-color var(--duration-fast);
}
.kvt-add:hover {
  border-color: var(--primary-300);
  color: var(--primary-600);
  background: var(--primary-50);
}

.kvt-hint {
  font-size: var(--text-2xs);
  color: var(--text-disabled);
  margin-left: var(--space-2);
}
</style>
