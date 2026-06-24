<template>
  <div class="dataset-manager">
    <div class="dm-header">
      <el-button type="primary" size="small" @click="openCreate">+ 新建数据集</el-button>
      <el-button size="small" @click="showCsvUpload = true">
        <el-icon><Upload /></el-icon>
        从 CSV 导入
      </el-button>
    </div>
    <SkeletonTable v-if="loading" :rows="5" />
    <template v-else>
      <el-table :data="datasets" border size="small">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="row_count" label="行数" width="80" align="center" />
        <el-table-column label="操作" width="280" align="center">
          <template #default="{ row }">
            <el-button link size="small" @click="editRow(row)">编辑</el-button>
            <el-button link size="small" @click="manageRows(row)">数据行</el-button>
            <el-button link size="small" @click="exportDataset(row)">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <el-dialog v-model="showCreate" :title="editingId ? '编辑数据集' : '新建数据集'" width="480px">
      <el-form :model="formData" label-width="80px">
        <el-form-item label="名称"><el-input v-model="formData.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="formData.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="save" :disabled="!formData.name">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRows" title="数据行管理" width="700px">
      <div class="rows-dialog-actions">
        <el-button size="small" @click="currentRows.push({data:'{}',is_enabled:true})">+ 添加数据行</el-button>
        <el-button size="small" @click="importJson">导入 JSON</el-button>
      </div>
      <el-table :data="currentRows" border size="small" max-height="400">
        <el-table-column label="#" width="50" type="index" />
        <el-table-column label="数据" min-width="300">
          <template #default="{ row }">
            <el-input v-model="row.data" type="textarea" :autosize="{minRows:1,maxRows:4}" />
          </template>
        </el-table-column>
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_enabled" size="small" />
          </template>
        </el-table-column>
        <el-table-column width="60" align="center">
          <template #default="{ $index }">
            <el-button link type="danger" size="small" @click="currentRows.splice($index,1)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showRows=false">取消</el-button>
        <el-button type="primary" @click="saveRows">保存</el-button>
      </template>
    </el-dialog>

    <!-- CSV Upload Dialog -->
    <el-dialog v-model="showCsvUpload" title="从 CSV 导入数据集" width="520px">
      <div class="csv-upload-area">
        <el-upload
          drag
          accept=".csv,.tsv,.txt"
          :auto-upload="false"
          :on-change="handleCsvFileChange"
          :file-list="csvFileList"
          :limit="1"
        >
          <div class="upload-content">
            <el-icon :size="40" style="color: var(--text-muted)"><UploadFilled /></el-icon>
            <p>将 CSV 文件拖到此处，或点击上传</p>
            <p class="upload-hint">支持 .csv / .tsv / .txt 格式，首行为表头</p>
          </div>
        </el-upload>
      </div>

      <div v-if="csvPreview.length" class="csv-preview">
        <h4>数据预览（前 {{ csvPreview.length }} 行）</h4>
        <el-table :data="csvPreview" border size="small" max-height="300">
          <el-table-column v-for="(header, idx) in csvHeaders" :key="idx"
            :prop="header" :label="header" min-width="120" />
        </el-table>
        <p class="preview-hint">共解析 {{ csvTotalRows }} 行数据</p>
      </div>

      <template #footer>
        <el-button @click="showCsvUpload = false">取消</el-button>
        <el-button type="primary" @click="confirmCsvImport" :disabled="!csvPreview.length">
          确认导入（{{ csvTotalRows }} 行）
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Delete, Download, Upload, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { getDatasets, createDataset, updateDataset, deleteDataset, getDatasetDetail, addDatasetRows, batchUpdateRows } from '@/api/dataset'
import SkeletonTable from '@/components/SkeletonTable.vue'
import request from '@/api/request'
import { useRequireLogin } from '@/composables/useRequireLogin'
import { msgSuccess, msgError, msgWarning } from '@/utils/message'
import { logger } from '@/utils/logger'

const { requireLogin } = useRequireLogin()

const props = defineProps<{ projectId: number }>()
interface DatasetRow {
  id?: number
  data: string | Record<string, unknown>
  is_enabled: boolean
}

interface DatasetItem {
  id: number
  name: string
  description?: string
  row_count?: number
}

const datasets = ref<DatasetItem[]>([])
const loading = ref(false)
const showCreate = ref(false)
const showRows = ref(false)
const editingId = ref<number|null>(null)
const currentDatasetId = ref<number|null>(null)
const currentRows = ref<DatasetRow[]>([])
const formData = ref({ name: '', description: '' })

// CSV upload state
const showCsvUpload = ref(false)
const csvFileList = ref<UploadFile[]>([])
const csvHeaders = ref<string[]>([])
const csvPreview = ref<Record<string, string>[]>([])
const csvTotalRows = ref(0)
const csvParsedRows = ref<DatasetRow[]>([])

function parseCsv(text: string): { headers: string[], rows: Record<string, string>[], totalRows: number } {
  const lines = text.split(/\r?\n/).filter(line => line.trim())
  if (lines.length === 0) return { headers: [], rows: [], totalRows: 0 }

  const firstLine = lines[0] ?? ''
  const delimiter = firstLine.includes('\t') ? '\t' : ','
  const headers = firstLine.split(delimiter).map(h => h.trim().replace(/^["']|["']$/g, ''))
  const rows: Record<string, string>[] = []

  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue
    const values = lines[i].split(delimiter).map(v => v.trim().replace(/^["']|["']$/g, ''))
    const row: Record<string, string> = {}
    headers.forEach((h, idx) => { row[h] = values[idx] || '' })
    rows.push(row)
  }

  return { headers, rows, totalRows: rows.length }
}

async function handleCsvFileChange(file: UploadFile) {
  if (!file.raw) return
  const text = await file.raw.text()
  const result = parseCsv(text)
  csvHeaders.value = result.headers
  csvPreview.value = result.rows.slice(0, 100)
  csvTotalRows.value = result.totalRows
  csvParsedRows.value = result.rows.map(row => ({
    data: JSON.stringify(row),
    is_enabled: true,
  }))
}

function confirmCsvImport() {
  if (csvParsedRows.value.length === 0) return
  currentRows.value.push(...csvParsedRows.value)
  if (!currentDatasetId.value) {
    msgWarning('请先选择数据集')
    return
  }
  msgSuccess(`已导入 ${csvParsedRows.value.length} 行 CSV 数据，请在下方编辑后保存`)
  // Reset CSV state and open rows dialog for editing
  showCsvUpload.value = false
  csvFileList.value = []
  csvHeaders.value = []
  csvPreview.value = []
  csvTotalRows.value = 0
  csvParsedRows.value = []
}

async function load() {
  loading.value = true
  try { const r = await getDatasets(props.projectId); datasets.value = r.data?.data||r.data||[] }
  finally { loading.value = false }
}

function openCreate() {
  editingId.value = null
  formData.value = { name: '', description: '' }
  showCreate.value = true
}

function editRow(row: DatasetItem) {
  editingId.value = row.id
  formData.value = { name: row.name, description: row.description||'' }
  showCreate.value = true
}

async function save() {
  if (!(await requireLogin('保存数据集'))) return
  if (editingId.value) {
    await updateDataset(props.projectId, editingId.value, formData.value)
  } else {
    await createDataset({ ...formData.value, project_id: props.projectId })
  }
  msgSuccess('已保存')
  showCreate.value = false
  void load()
}

async function handleDelete(row: DatasetItem) {
  if (!(await requireLogin('删除数据集'))) return
  await ElMessageBox.confirm('确认删除"' + row.name + '"？', '确认')
  await deleteDataset(props.projectId, row.id)
  msgSuccess('已删除')
  void load()
}

async function exportDataset(row: DatasetItem) {
  try {
    // 支持两种格式：JSON和CSV
    const format = 'json' // 默认导出JSON
    const response = await request.get(`/projects/${props.projectId}/datasets/${row.id}/export?format=${format}`, {
      responseType: 'blob',
    })

    // 创建下载链接
    const blob = new Blob([response.data], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${row.name}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    msgSuccess('数据集导出成功')
  } catch (err) {
    logger.error('Export failed:', err)
    msgError('导出失败')
  }
}

async function manageRows(row: DatasetItem) {
  currentDatasetId.value = row.id
  const r = await getDatasetDetail(props.projectId, row.id)
  const rawRows = (r.data as { data?: { rows?: unknown[] }; rows?: unknown[] })?.data?.rows || (r.data as { rows?: unknown[] }).rows || []
  currentRows.value = rawRows.map((x: Record<string, unknown>) => ({
    id: x.id as number, data: typeof x.data === 'string' ? x.data : JSON.stringify(x.data, null, 2), is_enabled: (x.is_enabled as boolean) ?? true }))
  showRows.value = true
}

function importJson() {
  const input = document.createElement('input')
  input.type = 'file'; input.accept = '.json'
  input.onchange = async (e: Event) => {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (!file) return
    const text = await file.text()
    try {
      const data = JSON.parse(text)
      if (Array.isArray(data)) {
        data.forEach(item => currentRows.value.push({ data: JSON.stringify(item,null,2), is_enabled: true }))
        msgSuccess('已导入 ' + data.length + ' 行')
      }
    } catch { msgError('JSON 格式无效') }
  }
  input.click()
}

async function saveRows() {
  if (!(await requireLogin('保存数据行'))) return
  if (!currentDatasetId.value) return
  const newRows = currentRows.value.filter(r => !r.id)
  const existing = currentRows.value.filter(r => r.id)
  if (newRows.length) await addDatasetRows(props.projectId, currentDatasetId.value, newRows)
  if (existing.length) await batchUpdateRows(props.projectId, currentDatasetId.value, existing)
  msgSuccess('数据行已保存')
  showRows.value = false
  void load()
}

onMounted(load)
</script>

<style scoped>
/* 数据集管理器容器 */
.dataset-manager {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 顶部操作栏 */
.dm-header {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

/* CSV 拖拽上传区域 */
.csv-upload-area {
  margin: var(--spacing-md) 0;
}

/* 上传区域内容 */
.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-2xl);
  color: var(--text-muted);
  transition: var(--transition-colors);
}

/* 上传区域悬停状态 */
.upload-content:hover {
  color: var(--text-secondary);
}

/* 上传提示文字 */
.upload-hint {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--spacing-xs);
}

/* CSV 预览标题 */
.csv-preview h4 {
  margin: var(--spacing-md) 0 var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 预览底部行数提示 */
.preview-hint {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin-top: var(--spacing-sm);
}

/* 数据行对话框操作栏 */
.rows-dialog-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

/* 表格操作按钮悬停状态 */
:deep(.el-button--text:hover) {
  color: var(--primary-500);
  background-color: var(--surface-hover);
}

/* 危险按钮悬停状态 */
:deep(.el-button--danger:hover) {
  color: var(--error-dark);
  background-color: var(--error-bg);
}

/* 禁用状态 */
:deep(.el-button.is-disabled) {
  color: var(--text-disabled);
  cursor: not-allowed;
}

/* 焦点状态 */
:deep(.el-button:focus-visible) {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
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

/* 加载遮罩 */
:deep(.el-loading-mask) {
  background-color: var(--color-primary-alpha-08);
}

/* 暗色模式 */
:global(html.dark) .upload-content { color: var(--text-muted); }
:global(html.dark) .upload-content:hover { color: var(--text-secondary); }
:global(html.dark) .csv-preview h4 { color: var(--text-primary); }
</style>
