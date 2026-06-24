<template>
  <div class="params-table" ref="tableRef" @keydown="onContainerKeydown">
    <div class="pt-header">
      <span class="pt-col-check">启用</span>
      <span class="pt-col-key">参数名</span>
      <span class="pt-col-value">参数值</span>
      <span v-if="showDesc" class="pt-col-desc">描述</span>
      <span v-if="showSampleCol" class="pt-col-sample">示例值</span>
      <span class="pt-col-type">类型</span>
      <span class="pt-col-action"></span>
    </div>
    <div v-if="modelValue && modelValue.length > 0" class="pt-rows">
      <div
        v-for="(row, index) in modelValue"
        :key="index"
        class="pt-row"
        :class="{ 'pt-row-disabled': !row.enabled }"
        :data-row-index="index"
      >
        <span class="pt-col-check"><el-checkbox v-model="row.enabled" size="small" /></span>
        <span class="pt-col-key"><el-input
            v-model="row.key"
            size="small"
            placeholder="参数名称"
            aria-label="参数名称"
            class="kv-input"
            @keydown.tab="onCellTab($event, index, 'key')"
            @keydown.enter="onCellEnter(index, 'key')"
        /></span>
        <span class="pt-col-value"><VarAwareInput
            v-model="row.value"
            size="small"
            placeholder="参数值"
            aria-label="参数值"
            class="kv-input"
            @keydown.tab="onCellTab($event, index, 'value')"
            @keydown.enter="onCellEnter(index, 'value')"
        /></span>
        <span v-if="showDesc" class="pt-col-desc">
          <el-input
            v-model="row.description"
            size="small"
            placeholder="参数描述"
            aria-label="参数描述"
            class="kv-input"
            @keydown.tab="onCellTab($event, index, 'desc')"
            @keydown.enter="onCellEnter(index, 'desc')"
          />
        </span>
        <span v-if="showSampleCol" class="pt-col-sample">
          <el-input
            v-model="row.sample"
            size="small"
            placeholder="示例值"
            class="sample-input kv-input"
          />
        </span>
        <span class="pt-col-type">
          <el-select v-model="row.type" size="small" class="type-select">
            <el-option label="string" value="string" />
            <el-option label="number" value="number" />
            <el-option label="boolean" value="boolean" />
          </el-select>
        </span>
        <span class="pt-col-action">
          <button class="pt-del" @click="remove(index)" title="删除" aria-label="删除参数"><X :size="13" /></button>
        </span>
      </div>
    </div>

    <div class="pt-toolbar">
      <button class="pt-add" @click="addRow">
        <Plus :size="13" />
        <span>添加参数</span>
      </button>
      <button class="pt-batch-btn" @click="showBatchImport = true" title="批量导入 JSON">
        <svg
          viewBox="0 0 24 24"
          width="13"
          height="13"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
        <span>批量导入</span>
      </button>
      <button
        class="pt-toggle-desc"
        @click="showDesc = !showDesc"
        :class="{ active: showDesc }"
        title="显示/隐藏描述列"
      >
        <svg
          viewBox="0 0 24 24"
          width="13"
          height="13"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="17" y1="10" x2="3" y2="10" />
          <line x1="21" y1="6" x2="3" y2="6" />
          <line x1="21" y1="14" x2="3" y2="14" />
          <line x1="17" y1="18" x2="3" y2="18" />
        </svg>
      </button>
      <button
        class="pt-toggle-desc"
        @click="showSampleCol = !showSampleCol"
        :class="{ active: showSampleCol }"
        title="显示/隐藏示例值列"
      >
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
      </button>
    </div>

    <!-- 批量 JSON 导入弹窗 -->
    <el-dialog
      v-model="showBatchImport"
      title="批量导入 JSON"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="batch-import-hint">粘贴 JSON 对象，每对键值将生成一行参数</div>
      <el-input
        v-model="batchJson"
        type="textarea"
        :rows="8"
        placeholder="{ &quot;page&quot;: 1, &quot;page_size&quot;: 20, &quot;keyword&quot;: &quot;test&quot; }"
        class="batch-textarea"
      />
      <template #footer>
        <el-button @click="showBatchImport = false">取消</el-button>
        <el-button type="primary" @click="executeBatchImport" :disabled="!batchJson.trim()">
导入
</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue"
import { X, Plus } from "lucide-vue-next"
import VarAwareInput from "./common/VarAwareInput.vue"
import { msgSuccess, msgError } from "@/utils/message"


// 参数行类型定义
interface ParamRow {
  key: string
  value: string
  type: 'string' | 'number' | 'boolean'
  enabled: boolean
  description: string
  sample: string
}

const modelValue = defineModel<ParamRow[]>({ default: () => [] })
const tableRef = ref<HTMLElement | null>(null)

const showDesc = ref(false)
const showSampleCol = ref(false)
const showBatchImport = ref(false)
const batchJson = ref("")

function addRow() {
  modelValue.value.push({ key: "", value: "", type: "string", enabled: true, description: "", sample: "" })
}

onMounted(() => {
  if (modelValue.value.length === 0) {
    modelValue.value.push({ key: "", value: "", type: "string", enabled: false, description: "", sample: "" })
  }
})

function remove(index: number) {
  modelValue.value.splice(index, 1)
  if (modelValue.value.length === 0) {
    modelValue.value.push({ key: "", value: "", type: "string", enabled: false, description: "", sample: "" })
  }
}

// ── Tab 键导航 ──
const focusTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function scheduleFocus(fn: () => void, delay: number) {
  if (focusTimer.value) clearTimeout(focusTimer.value)
  focusTimer.value = setTimeout(fn, delay)
}

/** Tab 导航顺序：key → value → desc(可选) → 下一行 key */
function onCellTab(e: KeyboardEvent, index: number, field: 'key' | 'value' | 'desc') {
  e.preventDefault()
  if (field === 'key') {
    // key → value
    scheduleFocus(() => focusRowField(index, 'value'), 30)
  } else if (field === 'value') {
    if (showDesc.value) {
      // value → desc
      scheduleFocus(() => focusRowField(index, 'desc'), 30)
    } else {
      // value → 下一行 key
      goToNextRow(index)
    }
  } else {
    // desc → 下一行 key
    goToNextRow(index)
  }
}

function goToNextRow(index: number) {
  const isLast = index === modelValue.value.length - 1
  if (isLast) {
    // 最后一行，自动新增
    addRow()
    scheduleFocus(() => focusRowField(modelValue.value.length - 1, 'key'), 50)
  } else {
    scheduleFocus(() => focusRowField(index + 1, 'key'), 30)
  }
}

/** Enter 换行 */
function onCellEnter(index: number, _field: 'key' | 'value' | 'desc') {
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

function focusRowField(rowIndex: number, field: 'key' | 'value' | 'desc') {
  const root = tableRef.value
  if (!root) return
  const row = root.querySelector(`[data-row-index="${rowIndex}"]`) as HTMLElement
  if (!row) return
  let selector: string
  if (field === 'key') selector = '.pt-col-key input'
  else if (field === 'value') selector = '.pt-col-value input, .pt-col-value .vai-preview'
  else selector = '.pt-col-desc input'
  const input = row.querySelector(selector) as HTMLElement
  if (input) {
    input.focus()
    if (input.tagName === 'INPUT') (input as HTMLInputElement).select()
  }
}

onBeforeUnmount(() => {
  if (focusTimer.value) clearTimeout(focusTimer.value)
})

function executeBatchImport() {
  try {
    const parsed = JSON.parse(batchJson.value)
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      msgError("请输入 JSON 对象（key-value 键值对）")
      return
    }
    let count = 0
    for (const [key, value] of Object.entries(parsed)) {
      modelValue.value.push({
        key,
        value: String(value),
        type:
          typeof value === "number" ? "number" : typeof value === "boolean" ? "boolean" : "string",
        enabled: true,
        description: "",
        sample: "",
      })
      count++
    }
    showBatchImport.value = false
    batchJson.value = ""
    msgSuccess(`已导入 ${count} 个参数`)
  } catch {
    msgError("JSON 格式错误，请检查输入")
  }
}
</script>

<style scoped>
/* ==========================================
 * ParamsTable — 参数表格样式
 * ========================================== */

/* ── 入场动画 ── */
@keyframes pt-btn-appear {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.params-table {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--space-2);
}

/* 表头 */
.pt-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  height: 32px;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--surface-nested);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  border-bottom: 1px solid var(--border-subtle);
}

.pt-col-check {
  width: var(--min-w-col-check);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pt-col-key {
  flex: 1;
  min-width: var(--min-w-input-sm);
  display: flex;
}
.pt-col-value {
  flex: 2;
  min-width: 160px;
  display: flex;
}
.pt-col-desc {
  flex: 1;
  min-width: var(--min-w-input-sm);
  display: flex;
}
.pt-col-sample {
  flex: 1;
  min-width: 120px;
  display: flex;
}
.pt-col-type {
  width: 96px;
  flex-shrink: 0;
}
.pt-col-action {
  width: var(--size-icon-lg);
  flex-shrink: 0;
}

.pt-rows {
  display: flex;
  flex-direction: column;
}

/* 行样式 */
.pt-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-3);
  min-height: 36px;
  border-bottom: 1px solid var(--border-default);
  transition: background var(--duration-fast) var(--ease-smooth);
}

.pt-row:last-child {
  border-bottom: none;
}

.pt-row:hover {
  background: var(--surface-hover);
}

.pt-row.pt-row-disabled {
  opacity: 0.45;
}

.pt-row.pt-row-disabled .pt-col-key,
.pt-row.pt-row-disabled .pt-col-value {
  text-decoration: line-through;
}

.pt-row.selected {
  background: var(--color-primary-alpha-08);
}

/* 输入框：无边框融入行，聚焦时浮现边框 */
.pt-row :deep(.kv-input) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.pt-row :deep(.el-input) {
  width: 100%;
  min-width: 0;
}
.pt-row :deep(.el-input__wrapper) {
  border-radius: var(--radius-xs);
  box-shadow: none;
  background: transparent;
  padding: 0 calc(var(--space-2) - 2px);
  border: 1px solid transparent;
  height: 28px;
  transition:
    color,
    border-color,
    background-color,
    opacity var(--duration-fast);
  min-width: 0;
}
.pt-row :deep(.el-input__wrapper:hover) {
  background: var(--surface-hover);
  border-color: var(--border-default);
}
.pt-row :deep(.el-input__wrapper.is-focus) {
  background: var(--surface-card);
  box-shadow: 0 0 0 1px var(--primary-400);
  border-color: var(--primary-400);
  border-radius: var(--radius-sm);
}
.pt-row :deep(.el-input__inner) {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--text-primary);
}
.pt-row :deep(.el-select .el-input__wrapper) {
  border-radius: var(--radius-xs);
  border: 1px solid transparent;
  transition: border-color var(--duration-fast), background-color var(--duration-fast);
}
.pt-row:hover :deep(.el-select .el-input__wrapper) {
  border-color: var(--border-default);
  background: var(--surface-hover);
}
.pt-row :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: var(--primary-400);
  background: var(--surface-card);
  box-shadow: 0 0 0 1px var(--primary-400);
}
.pt-row :deep(.el-select .el-select__placeholder) {
  color: var(--text-disabled);
  font-size: var(--text-xs);
  padding-left: 2px;
}
.pt-row :deep(.el-select .el-input__suffix) {
  margin-left: 2px;
}
.pt-row :deep(.el-checkbox__inner) {
  border-radius: var(--radius-2xs);
}

/* 值列 VarAwareInput 预览层增强 */
.pt-row :deep(.var-aware-input) {
  display: flex;
  align-items: center;
  height: 35px;
  align-self: center;
}
.pt-row :deep(.var-aware-input .el-input .el-input__wrapper) {
  height: 35px !important;
}
.pt-row :deep(.var-aware-input .el-input) {
  width: 100% !important;
  flex: 1 1 0% !important;
}

.pt-row :deep(.var-aware-input .vai-preview) {
  min-height: 28px;
  padding: 3px var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  transition:
    border-color var(--duration-fast),
    background-color var(--duration-fast),
    box-shadow var(--duration-fast);
}
.pt-row :deep(.var-aware-input .vai-preview:hover) {
  border-color: var(--primary-200);
  background: var(--surface-hover);
}
.pt-row :deep(.var-aware-input .vai-preview:focus-within) {
  border-color: var(--primary-400);
  background: var(--surface-card);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-08);
}
.pt-row :deep(.var-aware-input .vai-text) {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
.pt-row :deep(.var-aware-input .vai-var-tag) {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-primary-alpha-08);
  color: var(--primary-700);
  border: 1px solid var(--color-primary-alpha-15);
}
.pt-row :deep(.var-aware-input .vai-placeholder) {
  font-size: var(--text-sm);
  color: var(--text-disabled);
}

.pt-del {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-disabled);
  cursor: pointer;
  transition:
    color,
    border-color,
    background-color,
    opacity var(--duration-fast);
  opacity: 0;
}
.pt-row:hover .pt-del {
  opacity: 1;
}
.pt-del:hover {
  background: var(--color-error-alpha-08);
  color: var(--color-error-text);
}

.pt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-9) 16px;
  color: var(--text-muted);
}
.pt-empty-icon {
  font-size: var(--text-3xl);
  opacity: 0.35;
}
.pt-empty-text {
  font-size: var(--text-sm);
}

/* 底部工具栏 */
.pt-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-2);
  margin-top: var(--space-4);
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
}

.pt-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  flex: 0 1 auto;
  min-width: 120px;
  min-height: 34px;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition:
    color var(--duration-base) var(--ease-spring),
    border-color var(--duration-base) var(--ease-spring),
    background-color var(--duration-base) var(--ease-spring),
    transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-base);
  animation: pt-btn-appear 0.3s var(--ease-spring) backwards;
}
.pt-add:hover {
  border-color: var(--primary-400);
  color: var(--primary-600);
  background: var(--color-primary-alpha-06);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--color-primary-alpha-12);
}
.pt-add:active {
  transform: translateY(0px);
  box-shadow: none;
}

.pt-add:active {
  transform: translateY(0px);
  box-shadow: none;
}

.pt-batch-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  flex: 0 1 auto;
  min-width: 120px;
  min-height: 34px;
  padding: var(--space-2) var(--space-3);
  background: none;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition:
    color var(--duration-base) var(--ease-spring),
    border-color var(--duration-base) var(--ease-spring),
    background-color var(--duration-base) var(--ease-spring),
    transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-base);
  animation: pt-btn-appear 0.4s 80ms var(--ease-spring) backwards;
}
.pt-batch-btn:hover {
  border-color: var(--primary-400);
  color: var(--primary-600);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--color-primary-alpha-12);
}
.pt-batch-btn:active {
  transform: translateY(0);
  box-shadow: none;
}

.pt-toggle-desc {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: var(--height-row-compact);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition:
    color,
    border-color,
    background-color,
    opacity var(--duration-fast);
  flex-shrink: 0;
}
.pt-toggle-desc:hover {
  border-color: var(--primary-300);
  color: var(--primary-600);
}
.pt-toggle-desc.active {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border-color: var(--primary-300);
}

/* 批量导入弹窗 */
.batch-import-hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}
.batch-textarea :deep(.el-textarea__inner) {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
</style>
