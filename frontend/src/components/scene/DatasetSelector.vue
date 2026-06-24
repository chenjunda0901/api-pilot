<template>
  <div class="dataset-selector">
    <el-select :model-value="modelValue" placeholder="Select dataset (optional)" clearable filterable style="width:100%"
      @update:model-value="$emit('update:modelValue', $event)">
      <el-option v-for="ds in datasets" :key="ds.id" :label="ds.name" :value="ds.id">
        <span>{{ ds.name }}</span>
        <span class="dataset-count">({{ ds.row_count }} rows)</span>
      </el-option>
    </el-select>
    <div v-if="selectedDataset" class="dataset-preview-inline">
      <span>已选：{{ selectedDataset.name }}（{{ selectedDataset.row_count || '?' }} 行）</span>
      <el-button size="small" text @click="showDatasetPreview = true">预览数据</el-button>
    </div>

    <!-- Dataset Preview Dialog -->
    <el-dialog v-model="showDatasetPreview" :title="'数据集预览 - ' + (selectedDataset?.name || '')" width="640px">
      <SkeletonCard v-if="previewLoading" :count="3" />
      <template v-else>
        <div v-if="previewRows.length" class="dataset-preview-table">
          <el-table :data="previewRows" border size="small" max-height="400">
            <el-table-column v-for="(header, idx) in previewHeaders" :key="idx"
              :prop="header" :label="header" min-width="120" show-overflow-tooltip />
          </el-table>
          <p class="preview-hint">共 {{ previewTotalRows }} 行数据（预览前 100 行）</p>
        </div>
        <EmptyState v-else illustration="empty" title="暂无数据" />
      </template>
      <template #footer>
        <el-button @click="showDatasetPreview = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { getDatasets, getDatasetDetail } from '@/api/dataset'
import { msgError } from '@/utils/message'
import { logger } from '@/utils/logger'
import SkeletonCard from '@/components/SkeletonCard.vue'
import EmptyState from '@/components/EmptyState.vue'

interface DatasetRow {
  id: number
  name: string
  row_count?: number
  [key: string]: unknown
}

const props = defineProps<{ modelValue?: number; projectId: number }>()
defineEmits<{ 'update:modelValue': [val: number | undefined] }>()
const datasets = ref<DatasetRow[]>([])

// Preview state
const showDatasetPreview = ref(false)
const previewLoading = ref(false)
const previewHeaders = ref<string[]>([])
const previewRows = ref<Record<string, string>[]>([])
const previewTotalRows = ref(0)

const selectedDataset = computed(() => {
  if (!props.modelValue) return null
  return datasets.value.find(ds => ds.id === props.modelValue) || null
})

async function load() {
  if (!props.projectId) return
  try {
    const res = await getDatasets(props.projectId)
    datasets.value = res.data || []
  } catch (err) { logger.error('[DatasetSelector] load datasets failed:', err); msgError('加载数据集失败'); datasets.value = [] }
}

async function loadPreviewData() {
  if (!props.modelValue || !props.projectId) return
  previewLoading.value = true
  previewHeaders.value = []
  previewRows.value = []
  previewTotalRows.value = 0
  try {
    const res = await getDatasetDetail(props.projectId, props.modelValue)
    const data = res.data as { data?: { rows?: unknown[] }; rows?: unknown[] }
    const rawRows = (data?.data?.rows || data?.rows || []) as Array<{ id?: number; data: string | object; is_enabled?: boolean }>
    if (rawRows.length === 0) return

    // Parse first row to get headers
    const firstRow = rawRows[0]
    if (!firstRow) return
    const firstData = typeof firstRow.data === 'string' ? JSON.parse(firstRow.data) : firstRow.data
    if (firstData && typeof firstData === 'object' && !Array.isArray(firstData)) {
      previewHeaders.value = Object.keys(firstData as Record<string, unknown>)
    }

    // Parse all rows (limit to 100 for preview)
    const parsedRows: Record<string, string>[] = []
    for (let i = 0; i < Math.min(rawRows.length, 100); i++) {
      const row = rawRows[i]
      const parsed = typeof row.data === 'string' ? JSON.parse(row.data) : row.data
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        parsedRows.push(parsed as Record<string, string>)
      }
    }
    previewRows.value = parsedRows
    previewTotalRows.value = rawRows.length
  } catch (err) {
    logger.error('[DatasetSelector] loadPreviewData failed:', err)
    msgError('加载预览数据失败')
  } finally {
    previewLoading.value = false
  }
}

watch(() => props.modelValue, () => {
  if (showDatasetPreview.value) {
    void loadPreviewData()
  }
})

// Load preview when dialog opens
watch(showDatasetPreview, (val) => {
  if (val) void loadPreviewData()
})

watch(() => props.projectId, load, { immediate: true })
onMounted(load)
</script>

<style scoped>
/* 数据集选择器容器 */
.dataset-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* 下拉选项中的行数统计 */
.dataset-count {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-left: var(--spacing-xs);
}

/* 已选数据集的内联预览条 */
.dataset-preview-inline {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  transition: var(--transition-colors);
}

/* 预览条悬停状态 */
.dataset-preview-inline:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

/* 预览条内按钮样式 */
.dataset-preview-inline .el-button {
  color: var(--primary-500);
  transition: var(--transition-colors);
}

/* 预览条按钮悬停 */
.dataset-preview-inline .el-button:hover {
  color: var(--primary-600);
  background-color: var(--color-primary-alpha-08);
}

/* 预览条按钮焦点 */
.dataset-preview-inline .el-button:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

/* 弹窗内数据表格容器 */
.dataset-preview-table {
  margin-top: var(--spacing-sm);
}

/* 弹窗内行数提示 */
.preview-hint {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--spacing-sm);
}

/* 对话框样式增强 */
:deep(.el-dialog) {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}

/* 表格样式增强 */
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
}

/* 表头样式 */
:deep(.el-table th) {
  background-color: var(--surface-muted);
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}

/* 表格行悬停 */
:deep(.el-table tr:hover > td) {
  background-color: var(--surface-hover);
}

/* 下拉选项悬停 */
:deep(.el-select-dropdown__item:hover) {
  background-color: var(--surface-hover);
}

/* 下拉选项选中状态 */
:deep(.el-select-dropdown__item.selected) {
  color: var(--primary-600);
  background-color: var(--surface-selected);
}

/* 空状态样式 */
:deep(.el-empty__description) {
  color: var(--text-muted);
}

/* 加载遮罩 */
:deep(.el-loading-mask) {
  background-color: var(--color-primary-alpha-08);
}

/* 暗色模式 */
:global(html.dark) .dataset-preview-inline { background: var(--surface-nested); color: var(--text-secondary); }
:global(html.dark) .dataset-preview-inline:hover { background: var(--surface-hover); color: var(--text-primary); }
:global(html.dark) .dataset-preview-inline .el-button { color: var(--primary-400); }
:global(html.dark) .dataset-preview-inline .el-button:hover { color: var(--primary-300); }
</style>
