<template>
  <div class="dataset-panel">
    <div class="dataset-header">
      <span class="dataset-title">数据集 (Data-Driven Testing)</span>
      <div class="dataset-actions">
        <el-upload
          accept=".csv,.json"
          :show-file-list="false"
          :auto-upload="false"
          :on-change="(fileObj) => $emit('file-upload', fileObj.raw)"
        >
          <el-button size="small">
            <Upload :size="14" /> 导入 CSV/JSON
          </el-button>
        </el-upload>
      </div>
    </div>

    <div v-if="datasets.length === 0" class="dataset-empty">
      <EmptyState
        illustration="data"
        title="暂无数据集"
        description="导入 CSV/JSON 文件或手动添加数据来驱动场景执行"
      />
    </div>

    <div v-for="(ds, idx) in datasets" :key="ds.id || idx" class="dataset-card">
      <div class="ds-card-header">
        <span class="ds-card-title">{{ ds.name || `数据集 ${idx + 1}` }}</span>
        <div class="ds-card-actions">
          <el-button size="small" text @click="$emit('add-column', ds)">+ 添加列</el-button>
          <el-button size="small" text @click="$emit('add-row', ds)">+ 添加行</el-button>
        </div>
      </div>
      <div class="ds-table-wrapper">
        <table v-if="ds.columns && ds.columns.length > 0" class="ds-table">
          <thead>
            <tr>
              <th class="ds-row-num">#</th>
              <th v-for="col in ds.columns" :key="col" class="ds-th">
                <el-input
                  :model-value="col"
                  size="small"
                  placeholder="列名"
                  @update:model-value="(v: string) => $emit('update-column', ds, idx, v)"
                />
              </th>
              <th class="ds-th-action">
                <el-button size="small" text @click="$emit('add-column', ds)">+</el-button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in ds.rows" :key="ri">
              <td class="ds-row-num">{{ ri + 1 }}</td>
              <td v-for="col in ds.columns" :key="col" class="ds-td">
                <el-input
                  :model-value="row[col] ?? ''"
                  size="small"
                  placeholder="值"
                  @update:model-value="(v: string) => $emit('update-cell', ds, ri, col, v)"
                />
              </td>
              <td class="ds-td-action">
                <el-button size="small" text aria-label="删除数据行" @click="$emit('remove-row', ds, ri)">
                  <Trash2 :size="14" class="text-error" />
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
        <EmptyState
          v-else
          illustration="empty"
          title="暂无列定义"
          description="点击「添加列」开始创建数据集结构"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Upload, Trash2 } from 'lucide-vue-next'
import EmptyState from '@/components/EmptyState.vue'

export interface DatasetItem {
  id?: number
  name?: string
  columns?: string[]
  rows?: Record<string, string>[]
}

defineProps<{
  datasets: DatasetItem[]
}>()

defineEmits<{
  'file-upload': [file: File | null]
  'add-column': [ds: DatasetItem]
  'add-row': [ds: DatasetItem]
  'update-column': [ds: DatasetItem, colIndex: number, value: string]
  'update-cell': [ds: DatasetItem, rowIndex: number, col: string, value: string]
  'remove-row': [ds: DatasetItem, rowIndex: number]
}>()
</script>

<style scoped>
.dataset-panel {
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.dataset-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dataset-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}
.dataset-actions {
  display: flex;
  gap: var(--space-2);
}
.dataset-empty {
  padding: var(--space-6) 0;
}
.dataset-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.ds-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-bottom: 1px solid var(--border-subtle);
}
.ds-card-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}
.ds-card-actions {
  display: flex;
  gap: var(--space-1);
}
.ds-table-wrapper {
  overflow-x: auto;
  padding: var(--space-2);
}
.ds-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
}
.ds-table th, .ds-table td {
  padding: 2px 4px;
  border: 1px solid var(--border-default);
}
.ds-row-num {
  width: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-xs);
  background: var(--surface-nested);
}
.ds-th {
  min-width: 100px;
}
.ds-th-action {
  width: 40px;
}
.ds-td-action {
  width: 40px;
  text-align: center;
}
.text-error {
  color: var(--color-error-500);
}
</style>
