<template>
  <div class="doc-editor-tab">
    <!-- 顶部操作栏 -->
    <div class="doc-editor-toolbar">
      <span class="doc-editor-title">接口文档</span>
      <div class="doc-editor-actions">
        <el-button size="small" @click="loadDocVersions" :loading="loadingVersions">
          版本历史 ({{ versions.length }})
        </el-button>
        <el-button size="small" type="primary" @click="onPublish" :loading="saving">
          发布
        </el-button>
      </div>
    </div>

    <!-- Markdown 描述编辑 -->
    <div class="doc-section">
      <div class="doc-section-title">接口描述</div>
      <div class="md-editor-wrapper">
        <MdEditor
          :model-value="docData.description_md"
          @update:model-value="onDescriptionChange"
          language="zh-CN"
          :preview="true"
          :toolbarsExclude="['github', 'htmlPreview', 'catalog', 'save']"
          placeholder="使用 Markdown 编写接口描述文档..."
          :style="{ height: '280px' }"
        />
      </div>
    </div>

    <!-- 参数描述表 -->
    <div class="doc-section">
      <div class="doc-section-header">
        <span class="doc-section-title">参数说明</span>
        <el-button size="small" @click="addParamDoc">添加参数</el-button>
      </div>
      <el-table :data="docData.param_docs" size="small" stripe v-if="docData.param_docs.length > 0">
        <el-table-column prop="name" label="参数名" width="160">
          <template #default="{ row }">
            <el-input v-model="row.name" size="small" placeholder="参数名" @change="autoSaveDraft" />
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-select v-model="row.type" size="small" @change="autoSaveDraft">
              <el-option label="string" value="string" />
              <el-option label="integer" value="integer" />
              <el-option label="number" value="number" />
              <el-option label="boolean" value="boolean" />
              <el-option label="array" value="array" />
              <el-option label="object" value="object" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column prop="required" label="必填" width="70">
          <template #default="{ row }">
            <el-switch v-model="row.required" size="small" @change="autoSaveDraft" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述">
          <template #default="{ row }">
            <el-input v-model="row.description" size="small" placeholder="参数描述" @change="autoSaveDraft" />
          </template>
        </el-table-column>
        <el-table-column width="50">
          <template #default="{ $index }">
            <el-button size="small" type="danger" link @click="removeParamDoc($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="doc-empty-hint">暂无参数说明，点击"添加参数"开始编辑</div>
    </div>

    <!-- 请求示例 -->
    <div class="doc-section">
      <div class="doc-section-header">
        <span class="doc-section-title">请求示例</span>
        <el-button size="small" @click="addRequestExample">添加示例</el-button>
      </div>
      <div v-for="(ex, i) in docData.request_examples" :key="'req-' + i" class="doc-example-item">
        <div class="doc-example-head">
          <el-input v-model="ex.name" size="small" placeholder="示例名称" style="width: 200px" @change="autoSaveDraft" />
          <el-button size="small" type="danger" link @click="removeRequestExample(i)">删除</el-button>
        </div>
        <el-input
          v-model="ex.body"
          type="textarea"
          :rows="4"
          size="small"
          placeholder="请求体 JSON"
          @change="autoSaveDraft"
          class="doc-example-code"
        />
      </div>
      <div v-if="!docData.request_examples.length" class="doc-empty-hint">暂无请求示例</div>
    </div>

    <!-- 响应示例 -->
    <div class="doc-section">
      <div class="doc-section-header">
        <span class="doc-section-title">响应示例</span>
        <el-button size="small" @click="addResponseExample">添加示例</el-button>
      </div>
      <div v-for="(ex, i) in docData.response_examples" :key="'res-' + i" class="doc-example-item">
        <div class="doc-example-head">
          <el-input v-model="ex.name" size="small" placeholder="示例名称" style="width: 160px" @change="autoSaveDraft" />
          <el-input-number v-model="ex.status_code" size="small" :min="100" :max="599" placeholder="状态码" style="width: 120px" @change="autoSaveDraft" />
          <el-button size="small" type="danger" link @click="removeResponseExample(i)">删除</el-button>
        </div>
        <el-input
          v-model="ex.body"
          type="textarea"
          :rows="4"
          size="small"
          placeholder="响应体 JSON"
          @change="autoSaveDraft"
          class="doc-example-code"
        />
      </div>
      <div v-if="!docData.response_examples.length" class="doc-empty-hint">暂无响应示例</div>
    </div>

    <!-- 版本历史抽屉 -->
    <el-drawer v-model="showVersions" title="文档版本历史" size="400px">
      <div v-if="loadingVersions" style="text-align: center; padding: 20px">
        <el-skeleton :rows="4" animated />
      </div>
      <div v-else-if="versions.length === 0" class="doc-empty-hint">暂无版本历史</div>
      <div v-else class="version-list">
        <div v-for="v in versions" :key="v.id" class="version-item">
          <div class="version-item-head">
            <span class="version-summary">{{ v.change_summary || '无说明' }}</span>
            <span class="version-time">{{ formatTime(v.created_at) }}</span>
          </div>
          <el-button size="small" type="warning" @click="onRollback(v.id)">回滚到此版本</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'
import { getApiDoc, saveApiDoc, listDocVersions, rollbackDocVersion } from '../api/docs'
import type { ParamDoc, RequestExample, ResponseExample, DocVersionItem } from '../api/docs'
import { msgSuccess, msgError } from '../utils/message'

const props = defineProps<{
  projectId: number
  apiId: number
}>()

const docData = ref<{
  description_md: string
  param_docs: ParamDoc[]
  request_examples: RequestExample[]
  response_examples: ResponseExample[]
  is_draft: boolean
}>({
  description_md: '',
  param_docs: [],
  request_examples: [],
  response_examples: [],
  is_draft: true,
})

const saving = ref(false)
const loadingVersions = ref(false)
const showVersions = ref(false)
const versions = ref<DocVersionItem[]>([])

let draftTimer: ReturnType<typeof setTimeout> | null = null

async function loadDoc() {
  if (!props.apiId) return
  try {
    const res = await getApiDoc(props.projectId, props.apiId)
    if (res.data) {
      docData.value = {
        description_md: res.data.description_md || '',
        param_docs: res.data.param_docs || [],
        request_examples: res.data.request_examples || [],
        response_examples: res.data.response_examples || [],
        is_draft: res.data.is_draft ?? true,
      }
    }
  } catch {
    // 接口文档不存在时使用默认空值
  }
}

function onDescriptionChange(val: string) {
  docData.value.description_md = val
  autoSaveDraft()
}

function addParamDoc() {
  docData.value.param_docs.push({ name: '', type: 'string', required: false, description: '' })
}

function removeParamDoc(index: number) {
  docData.value.param_docs.splice(index, 1)
  autoSaveDraft()
}

function addRequestExample() {
  docData.value.request_examples.push({ name: '', body: '' })
}

function removeRequestExample(index: number) {
  docData.value.request_examples.splice(index, 1)
  autoSaveDraft()
}

function addResponseExample() {
  docData.value.response_examples.push({ name: '', status_code: 200, body: '' })
}

function removeResponseExample(index: number) {
  docData.value.response_examples.splice(index, 1)
  autoSaveDraft()
}

function autoSaveDraft() {
  if (draftTimer) clearTimeout(draftTimer)
  draftTimer = setTimeout(() => {
    void doSave(true)
  }, 1500)
}

async function onPublish() {
  await doSave(false)
}

async function doSave(isDraft: boolean) {
  if (!props.apiId || saving.value) return
  saving.value = true
  try {
    const res = await saveApiDoc(props.projectId, props.apiId, {
      description: docData.value.description_md,
      param_docs: docData.value.param_docs,
      request_examples: docData.value.request_examples,
      response_examples: docData.value.response_examples,
      is_draft: isDraft,
    })
    if (res.data) {
      docData.value.is_draft = res.data.is_draft
    }
    if (!isDraft) msgSuccess('文档已发布')
  } catch {
    if (!isDraft) msgError('保存失败')
  } finally {
    saving.value = false
  }
}

async function loadDocVersions() {
  showVersions.value = true
  if (!props.apiId) return
  loadingVersions.value = true
  try {
    const res = await listDocVersions(props.projectId, props.apiId)
    versions.value = res.data || []
  } catch {
    versions.value = []
  } finally {
    loadingVersions.value = false
  }
}

async function onRollback(versionId: number) {
  try {
    await ElMessageBox.confirm('确认回滚到此版本？当前未发布的修改将丢失。', '回滚确认', {
      confirmButtonText: '回滚',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }

  try {
    const res = await rollbackDocVersion(props.projectId, props.apiId, versionId)
    if (res.data) {
      docData.value = {
        description_md: res.data.description_md || '',
        param_docs: res.data.param_docs || [],
        request_examples: res.data.request_examples || [],
        response_examples: res.data.response_examples || [],
        is_draft: res.data.is_draft ?? true,
      }
    }
    msgSuccess('已回滚到指定版本')
    await loadDocVersions()
  } catch {
    msgError('回滚失败')
  }
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return '--'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

watch(() => props.apiId, () => {
  void loadDoc()
})

onMounted(() => {
  void loadDoc()
})
</script>

<style scoped>
.doc-editor-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
  padding: var(--space-4, 16px);
  height: 100%;
  overflow-y: auto;
}

.doc-editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--space-3, 12px);
  border-bottom: 1px solid var(--border-subtle);
}

.doc-editor-title {
  font-weight: var(--weight-semibold, 600);
  font-size: var(--text-base, 14px);
  color: var(--text-primary);
}

.doc-editor-actions {
  display: flex;
  gap: var(--space-2, 8px);
}

.doc-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.doc-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.doc-section-title {
  font-weight: var(--weight-semibold, 600);
  font-size: var(--text-sm, 13px);
  color: var(--text-primary);
}

.md-editor-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 6px);
  overflow: hidden;
}

.doc-example-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 6px);
  padding: var(--space-3, 12px);
  margin-bottom: var(--space-2, 8px);
}

.doc-example-head {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}

.doc-example-code :deep(.el-textarea__inner) {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--text-sm, 13px);
}

.doc-empty-hint {
  color: var(--text-muted);
  font-size: var(--text-sm, 13px);
  padding: var(--space-3, 12px) 0;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}

.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3, 12px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 6px);
}

.version-item-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.version-summary {
  font-size: var(--text-sm, 13px);
  color: var(--text-primary);
}

.version-time {
  font-size: var(--text-xs, 12px);
  color: var(--text-muted);
}
</style>
