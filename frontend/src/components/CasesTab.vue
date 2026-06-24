<template>
  <div class="cases-tab">
    <div class="cases-header">
      <span class="cases-title">{{ $t('cases.title', { count: cases.length }) }}</span>
      <div class="cases-header-actions">
        <!-- 导入用例 -->
        <el-button size="small" @click="triggerImportCase">
          <Upload :size="12" /> {{ $t('cases.importBtn') }}
        </el-button>
        <input ref="importFileInput" type="file" accept=".json" hidden @change="handleImportFile" />

        <!-- 导出用例 -->
        <el-dropdown v-if="selectedIds.length === 1" @command="handleExportCase" trigger="click">
          <el-button size="small">
            {{ $t('cases.exportBtn') }} <ArrowDown :size="12" />
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="json">{{ $t('cases.exportAsJson') }}</el-dropdown-item>
              <el-dropdown-item command="copy">{{ $t('cases.copyToClipboard') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button size="small" @click="selectAll" v-if="cases.length > 0">
          {{ allSelected ? $t('cases.deselectAll') : $t('cases.selectAll') }}
        </el-button>
        <el-button size="small" type="primary" @click="$emit('create')">
          <Plus :size="14" /> {{ $t('cases.create') }}
        </el-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.length > 0" class="batch-actions">
      <span class="batch-count">{{ $t('cases.selected', { count: selectedIds.length }) }}</span>
      <button class="batch-btn primary" @click="$emit('batchRun', [...selectedIds])">
        <Play :size="13" /> {{ $t('cases.runSelected') }}
      </button>
      <button class="batch-btn danger" @click="handleBatchDelete">
        <Trash2 :size="13" /> {{ $t('cases.deleteSelected') }}
      </button>
      <button class="batch-btn" @click="selectedIds = []">{{ $t('cases.clearSelection') }}</button>
    </div>

    <SkeletonTable v-if="loading" :rows="5" />

    <EmptyState
      v-else-if="cases.length === 0"
      illustration="empty"
      :title="$t('cases.empty')"
      :description="$t('cases.emptyDesc')"
    />

    <div v-else class="cases-table">
      <div class="cases-table-header">
        <span class="ct-col-check">
          <input type="checkbox" :checked="allSelected" @change="toggleSelectAll" class="case-checkbox" />
        </span>
        <span class="ct-col-name">{{ $t('cases.name') }}</span>
        <span class="ct-col-priority">{{ $t('cases.priority') }}</span>
        <span class="ct-col-status">{{ $t('cases.status') }}</span>
        <span class="ct-col-actions"></span>
      </div>
      <div
        v-for="c in cases"
        :key="c.id"
        class="cases-table-row"
        :class="{ active: selectedCaseId === c.id, checked: selectedIds.includes(c.id) }"
        tabindex="0"
        @click="$emit('select', c.id)"
        @keydown.enter="$emit('select', c.id)"
      >
        <span class="ct-col-check" @click.stop>
          <input type="checkbox" :checked="selectedIds.includes(c.id)" @change="toggleCase(c.id)" class="case-checkbox" />
        </span>
        <span class="ct-col-name">
          <span class="case-name">{{ c.name }}</span>
          <span class="case-type-dot" :class="'type-' + (c.case_type || 'other')" :title="caseTypeLabel(c.case_type)"></span>
        </span>
        <span class="ct-col-priority">
          <span class="priority-badge" :class="'p-' + c.priority">{{ c.priority }}</span>
        </span>
        <span class="ct-col-status">
          <span v-if="c.last_run_status" class="run-status" :class="'status-' + c.last_run_status">
            {{ statusText(c.last_run_status) }}
          </span>
          <span v-else class="run-status status-none">—</span>
        </span>
        <span class="ct-col-actions" @click.stop>
          <button class="case-action-btn" :title="$t('cases.runBtn')" :aria-label="$t('cases.runBtn')" @click="$emit('run', c.id)">
            <Play :size="13" />
          </button>
          <button class="case-action-btn" :title="$t('cases.copyBtn')" :aria-label="$t('cases.copyBtn')" @click="$emit('copy', c.id)">
            <Copy :size="13" />
          </button>
          <button class="case-action-btn action-danger" :title="$t('cases.deleteBtn')" :aria-label="$t('cases.deleteBtn')" @click="$emit('delete', c.id)">
            <Trash2 :size="13" />
          </button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Play, Copy, Trash2, Upload, ArrowDown } from 'lucide-vue-next'
import { exportCaseToJson, importCaseFromJson, type ExportedCase } from '../utils/caseExporter'
import { downloadJson } from '../utils/download'
import { msgSuccess, msgError } from '../utils/message'
import { ElMessageBox } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonTable from '@/components/SkeletonTable.vue'

const { t } = useI18n()

interface CaseItem {
  id: number
  name: string
  priority: string
  case_type?: string
  last_run_status?: string
}

const props = defineProps<{
  cases: CaseItem[]
  selectedCaseId?: number | null
  loading?: boolean
}>()

const emit = defineEmits<{
  create: []
  select: [caseId: number]
  run: [caseId: number]
  copy: [caseId: number]
  delete: [caseId: number]
  batchRun: [caseIds: number[]]
  batchDelete: [caseIds: number[]]
  importCase: [data: ExportedCase]
}>()

// 模板中使用 $emit，脚本中通过 emit() 调用（虽然当前只用在模板中）
const _emit = emit  // 保留供脚本中使用

const selectedIds = ref<number[]>([])
const importFileInput = ref<HTMLInputElement | null>(null)

const allSelected = computed(() => {
  return props.cases.length > 0 && selectedIds.value.length === props.cases.length
})

function toggleCase(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(id)
  }
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = props.cases.map(c => c.id)
  }
}

async function handleBatchDelete() {
  const count = selectedIds.value.length
  if (count === 0) return
  try {
    await ElMessageBox.confirm(
      t('cases.confirmBatchDelete', { count }),
      t('cases.batchDeleteTitle'),
      { type: 'warning', confirmButtonText: t('cases.confirmDelete'), cancelButtonText: t('common.cancel') }
    )
    emit('batchDelete', [...selectedIds.value])
    // 成功反馈由父组件在实际 API 调用完成后处理
    selectedIds.value = []
  } catch {
    // 用户取消，不删除也不清空选中
  }
}

function selectAll() {
  selectedIds.value = allSelected.value ? [] : props.cases.map(c => c.id)
}

// 当 cases 变化时，清除已不存在的选中项
watch(() => props.cases, () => {
  const validIds = new Set(props.cases.map(c => c.id))
  selectedIds.value = selectedIds.value.filter(id => validIds.has(id))
})

function statusText(status: string) {
  const map: Record<string, string> = {
    pass: t('cases.passStatus'),
    fail: t('cases.failStatus'),
    skipped: t('cases.skipStatus'),
    error: t('cases.errorStatus'),
  }
  return map[status] || status
}

function caseTypeLabel(type?: string) {
  const map: Record<string, string> = {
    positive: t('cases.positiveType'),
    negative: t('cases.negativeType'),
    boundary: t('cases.boundaryType'),
    security: t('cases.securityType'),
    other: t('cases.otherType'),
  }
  return map[type || 'other'] || type || t('cases.otherType')
}

// ── 导出用例 ──
async function handleExportCase(command: string) {
  const caseId = selectedIds.value[0]
  const caseItem = props.cases.find(c => c.id === caseId)
  if (!caseItem) return

  const json = exportCaseToJson({
    name: caseItem.name,
    priority: caseItem.priority,
    api_method: '',
    api_path: '',
    params_overrides: [],
    headers_overrides: [],
    assertions: [],
    variable_extractions: [],
    pre_script: '',
    post_script: '',
  })

  if (command === 'json') {
    downloadJson(JSON.parse(json), `case_${caseItem.name}_${Date.now()}.json`)
    msgSuccess(t('cases.exported'))
  } else if (command === 'copy') {
    try {
      await navigator.clipboard.writeText(json)
      msgSuccess(t('cases.copiedToClipboard'))
    } catch {
      msgError(t('cases.copyFailedManual'))
    }
  }
}

// ── 导入用例 ──
function triggerImportCase() {
  importFileInput.value?.click()
}

async function handleImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  try {
    const imported = await importCaseFromJson(file)
    await ElMessageBox.confirm(
      t('cases.importConfirmMsg'),
      t('cases.importConfirmTitle'),
      { confirmButtonText: t('cases.confirmImport'), cancelButtonText: t('common.cancel'), type: 'info' }
    )
    emit('importCase', imported)
    msgSuccess(t('cases.importSuccess'))
  } catch (e: unknown) {
    if ((e as Error).message === 'cancel') return
    msgError(t('cases.importFailed'))
  }

  // 重置 input 以便重复选择同一文件
  input.value = ''
}
</script>

<style scoped>
.cases-tab { padding: var(--space-3); }

.cases-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.cases-header-actions {
  display: flex;
  gap: var(--space-2);
}

.cases-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
}

/* 批量操作栏 */
.batch-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-primary-alpha-06);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-3);
  border: 1px solid var(--color-primary-alpha-12);
}
.batch-count {
  font-size: var(--text-xs);
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
  margin-right: auto;
}
.batch-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.batch-btn:hover { background: var(--surface-hover); color: var(--text-primary); }
.batch-btn.primary { 
  background: var(--primary-500); color: var(--text-inverse); border-color: transparent;
}
.batch-btn.primary:hover { background: var(--primary-600); }
.batch-btn.danger { 
  color: var(--error-text); border-color: var(--error-border);
}
.batch-btn.danger:hover { background: var(--error-bg); }

/* 空状态 */
.cases-empty {
  text-align: center;
  padding: var(--space-8) var(--space-4);
  color: var(--text-muted);
}
.cases-empty-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--surface-hover);
  color: var(--text-disabled);
  margin: 0 auto var(--space-2);
  font-size: var(--text-lg2);
}
.cases-empty-text {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-muted);
  margin-bottom: var(--space-1);
}
.cases-empty-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--leading-normal);
}

/* 表格风格 */
.cases-table { display: flex; flex-direction: column; }

.cases-table-header {
  display: flex;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  font-size: 0.625rem;
  font-weight: var(--weight-medium);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--border-subtle);
}

.cases-table-row {
  display: flex;
  align-items: center;
  padding: var(--space-2-5) var(--space-3);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-smooth);
  border-bottom: 1px solid var(--border-default);
}
.cases-table-row:last-child { border-bottom: none; }
.cases-table-row:hover { background: var(--surface-hover); }
.cases-table-row.active { background: var(--color-primary-alpha-06); }
.cases-table-row.checked { background: var(--color-primary-alpha-04); }

.ct-col-check {
  width: 30px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.case-checkbox {
  accent-color: var(--primary-500);
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.ct-col-name {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.case-name {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-type-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.type-positive { background: var(--success); }
.type-negative { background: var(--error); }
.type-boundary { background: var(--info); }
.type-security { background: var(--purple); }
.type-other { background: var(--text-disabled); }

.ct-col-priority { width: 50px; flex-shrink: 0; }

.priority-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 16px;
  padding: 0 4px;
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  border-radius: var(--radius-2xs);
}
.p-P0 { color: var(--error-text); }
.p-P1 { color: var(--warning-text); }
.p-P2 { color: var(--success-text); }
.p-P3 { color: var(--text-muted); }

.ct-col-status { width: 60px; flex-shrink: 0; }

.run-status { font-size: var(--text-2xs); }
.status-pass { color: var(--success-text); }
.status-fail { color: var(--error-text); }
.status-skipped { color: var(--text-muted); }
.status-error { color: var(--warning-text); }
.status-none { color: var(--text-disabled); }

.ct-col-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-smooth);
}
.cases-table-row:hover .ct-col-actions { opacity: 1; }

.case-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.case-action-btn:hover {
  background: var(--surface-active);
  color: var(--text-primary);
}
.case-action-btn.action-danger:hover {
  background: var(--color-error-alpha-08);
  color: var(--error-text);
}

html.dark .cases-table-row { border-color: var(--border-default); }
html.dark .cases-table-header { border-color: var(--border-subtle); }
html.dark .batch-actions { background: var(--color-primary-alpha-12); border-color: var(--color-primary-alpha-16); }
</style>