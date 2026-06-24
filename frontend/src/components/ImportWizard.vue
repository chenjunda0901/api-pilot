<template>
  <el-dialog
    v-model="dialogVisible"
    title="导入接口文件"
    width="860px"
    :close-on-click-modal="false"
    @close="handleClose"
    destroy-on-close
    class="import-wizard-dialog"
  >
    <el-steps :active="step - 1" simple class="import-steps">
      <el-step title="选择文件" />
      <el-step title="预览确认" />
      <el-step title="导入结果" />
    </el-steps>

    <!-- Step 1: 选择文件 -->
    <div v-if="step === 1" class="step-content">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        accept=".json,.yaml,.yml,.txt,.apifox,.har,.openapi,.swagger,.postman,.collection"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
        :file-list="fileList"
      >
        <div class="upload-area">
          <Upload :size="48" class="upload-icon" />
          <p class="upload-text">将接口文件拖到此处</p>
          <p class="upload-hint">或 <em>点击选择文件</em></p>
          <p class="upload-format">支持: Apifox / Postman / OpenAPI (Swagger) / YAPI / Eolink / Apipost / Bruno / HAR</p>
        </div>
      </el-upload>

      <div v-if="readingFile" class="file-reading-hint">
        <el-icon class="is-loading"><svg viewBox="0 0 24 24" width="16" height="16"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" opacity=".25"/><path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/></svg></el-icon>
        <span>正在读取文件...</span>
      </div>

      <!-- cURL 粘贴区域 -->
      <div class="curl-section">
        <div class="curl-section-header" @click="showCurlInput = !showCurlInput">
          <span class="curl-section-title">或粘贴 cURL 命令</span>
          <el-icon :class="{ rotated: showCurlInput }"><svg viewBox="0 0 24 24" width="14" height="14"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" fill="none"/></svg></el-icon>
        </div>
        <Transition name="slide-fade">
          <div v-if="showCurlInput" class="curl-input-area">
            <textarea
              v-model="curlText"
              placeholder="从浏览器 DevTools 复制 cURL 命令粘贴到这里&#10;例如: curl -X POST https://api.example.com/login -H Content-Type: application/json -d {key:value}"
              class="curl-textarea"
              aria-label="cURL 命令"
              rows="4"
              spellcheck="false"
            ></textarea>
            <div class="curl-actions">
              <el-button size="small" type="primary" :disabled="!curlText.trim()" @click="previewCurl">解析 cURL</el-button>
              <el-button size="small" @click="showCurlInput = false; curlText = ''">清除</el-button>
            </div>
          </div>
        </Transition>
      </div>

      <div v-if="selectedFile" class="file-info">
        <FileText :size="18" />
        <span class="file-name">{{ selectedFile.name }}</span>
        <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
        <el-button link type="danger" @click="clearFile">清除</el-button>
      </div>

      <!-- 格式选择器 -->
      <div v-if="selectedFile && validationMsg?.type === 'success'" class="format-selector">
        <div class="format-selector-header">
          <span>文件格式</span>
          <el-button v-if="!showFormatSelector" size="small" text @click="showFormatSelector = true">切换格式</el-button>
        </div>
        <div v-if="showFormatSelector || !detectedFormat" class="format-options">
          <div
            v-for="fmt in formatOptions"
            :key="fmt.value"
            class="format-option"
            :class="{ active: manualFormat === fmt.value || (!manualFormat && detectedFormat === fmt.value) }"
            @click="selectFormat(fmt.value)"
          >
            <div class="format-option-header">
              <span class="format-option-name">{{ fmt.label }}</span>
              <el-tag v-if="detectedFormat === fmt.value && !manualFormat" size="small" type="success">自动检测</el-tag>
            </div>
            <p class="format-option-desc">{{ fmt.description }}</p>
          </div>
        </div>
        <div v-else class="format-detected">
          <span class="format-detected-label">{{ detectedFormatTitle }}</span>
        </div>
      </div>

      <el-alert
        v-if="validationMsg?.type === 'success' && detectedFormat"
        :title="`检测到格式: ${detectedFormatTitle} · ${previewData.project_name}`"
        type="success"
        show-icon
        :closable="false"
        class="parse-success-alert"
      />
      <el-alert
        v-if="validationMsg?.type === 'error'"
        :title="validationMsg.message"
        type="error"
        show-icon
        :closable="false"
        class="parse-error-alert"
      />
    </div>

    <!-- Step 2: 预览确认 -->
    <div v-if="step === 2" class="step-content">
      <div class="preview-stats">
        <div class="stat-card">
          <span class="stat-number primary">{{ previewData.stats?.total_apis || 0 }}</span>
          <span class="stat-label">接口</span>
        </div>
        <div class="stat-card">
          <span class="stat-number success">{{ previewData.stats?.total_categories || 0 }}</span>
          <span class="stat-label">接口目录</span>
        </div>
        <div class="stat-card" v-if="previewData.stats?.total_test_cases">
          <span class="stat-number" style="color: var(--warning)">{{ previewData.stats.total_test_cases }}</span>
          <span class="stat-label">测试用例</span>
        </div>
        <div class="stat-card" v-if="previewData.stats?.total_request_collections">
          <span class="stat-number primary">{{ previewData.stats.total_request_collections }}</span>
          <span class="stat-label">接口集合</span>
        </div>
        <div class="stat-card" v-if="previewData.stats?.total_test_case_collections">
          <span class="stat-number" style="color: var(--warning)">{{ previewData.stats.total_test_case_collections }}</span>
          <span class="stat-label">用例集合</span>
        </div>
        <div class="stat-card">
          <span class="stat-number info">{{ previewData.stats?.total_environments || 0 }}</span>
          <span class="stat-label">环境</span>
        </div>
        <div class="stat-card">
          <span class="stat-number info">{{ previewData.stats?.total_variables || 0 }}</span>
          <span class="stat-label">变量</span>
        </div>
      </div>

      <div v-if="previewData.categories?.length" class="preview-section">
        <h4>
          接口目录与接口
          <el-button size="small" text @click="toggleSelectAll" style="margin-left: 12px">
            {{ allApisSelected ? '取消全选' : '全选' }}
          </el-button>
          <el-button size="small" text @click="invertSelection">反选</el-button>
          <span class="selected-count">已选 {{ selectedApiNames.size }} / {{ totalApiCount }}</span>
        </h4>
        <div class="preview-tree-wrapper">
          <el-tree
            :data="previewData.categories"
            :props="{ label: 'name', children: 'children' }"
            default-expand-all
            class="preview-tree"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <el-checkbox
                  v-if="data.isApi"
                  :model-value="selectedApiNames.has(data.name)"
                  @change="(val: boolean) => toggleApiSelection(data.name, val)"
                  @click.stop
                  size="small"
                />
                <Plug v-if="data.isApi" :size="14" />
                <Folder v-else :size="14" />
                <span class="tree-node-name">{{ data.name }}</span>
                <el-tag v-if="data.method" size="small" :type="getMethodTagType(data.method)">
                  {{ data.method }}
                </el-tag>
                <span v-if="data.path && data.isApi" class="tree-node-path">{{ data.path }}</span>
                <el-tag v-if="data.exists" size="small" type="info">已存在</el-tag>
              </span>
            </template>
          </el-tree>
        </div>
      </div>

      <!-- 测试用例预览 -->
      <div v-if="previewData.test_cases?.length" class="preview-section">
        <h4>测试用例（{{ previewData.test_cases.length }} 个）</h4>
        <div class="tc-list">
          <div v-for="(tc, i) in previewData.test_cases.slice(0, 10)" :key="i" class="tc-item">
            <span class="tc-name">{{ tc.name }}</span>
            <el-tag size="small" type="warning">{{ tc.priority || 'P1' }}</el-tag>
            <span class="tc-assertions">{{ tc.assertions?.length || 0 }} 断言</span>
          </div>
          <p v-if="previewData.test_cases.length > 10" class="tc-more">
            ...还有 {{ previewData.test_cases.length - 10 }} 个用例
          </p>
        </div>
      </div>

      <div v-if="previewData.environments?.length" class="preview-section">
        <h4>环境</h4>
        <div v-for="env in previewData.environments" :key="env.name" class="env-card">
          <div class="env-header">
            <span class="env-name">{{ env.name }}</span>
            <el-tag size="small" :type="env.exists ? 'info' : 'success'">
              {{ env.exists ? '已存在' : '新建' }}
            </el-tag>
          </div>
          <div class="env-detail">
            <span>BaseURL: <code>{{ env.base_url || '未设置' }}</code></span>
            <span>变量: {{ env.variables?.length || 0 }} 个</span>
          </div>
        </div>
      </div>

      <div class="import-options">
        <h4>导入选项</h4>
        <div class="options-grid">
          <el-checkbox v-model="importOptions.importVariables">导入全局变量</el-checkbox>
          <el-checkbox v-model="importOptions.importHeaders">导入公共 Headers</el-checkbox>
          <el-checkbox v-model="importOptions.importEnvironments">导入环境配置</el-checkbox>
          <el-checkbox v-if="previewData.stats?.total_test_cases" v-model="importOptions.importTestCases">
            导入测试用例
          </el-checkbox>
        </div>
        <div class="conflict-strategy">
          <span>遇到同名接口时：</span>
          <el-radio-group v-model="importOptions.conflictStrategy">
            <el-radio value="skip">跳过</el-radio>
            <el-radio value="update">覆盖更新</el-radio>
            <el-radio value="rename">重命名导入</el-radio>
            <el-radio value="keep_both">保留两者</el-radio>
          </el-radio-group>
        </div>
      </div>
    </div>

    <!-- Step 3: 导入结果 -->
    <div v-if="step === 3" class="step-content">
      <!-- 导入中进度 -->
      <div v-if="importing" class="importing-progress">
        <el-progress
          type="circle"
          :percentage="importProgress"
          :status="importError ? 'exception' : importProgress < 100 ? undefined : 'success'"
          :width="120"
        />
        <p class="importing-text">{{ importProgressText }}</p>
        <button v-if="importError" class="btn btn-primary" @click="retryImport" style="margin-top:16px">
          重新导入
        </button>
        <button v-if="importError" class="btn btn-ghost" @click="step = 1" style="margin-top:8px">
          重新选择文件
        </button>
      </div>
      <el-result
        v-else
        :icon="resultStatus === 'error' ? 'error' : 'success'"
        :title="resultStatus === 'partial' ? '导入完成（部分数据有警告）' : resultStatus === 'error' ? '导入失败' : '导入完成'"
        :sub-title="resultStatus === 'partial' ? '大部分数据已成功导入，请查看下方的警告信息' : resultStatus === 'error' ? '请检查文件格式后重试' : '以下数据已成功导入到当前项目'"
      >
        <template #extra>
          <div class="result-grid">
            <div class="result-item success">
              <span class="result-num">{{ importResult.created_apis || 0 }}</span>
              <span class="result-label">新建接口</span>
            </div>
            <div class="result-item warning">
              <span class="result-num">{{ importResult.updated_apis || 0 }}</span>
              <span class="result-label">更新接口</span>
            </div>
            <div class="result-item info">
              <span class="result-num">{{ importResult.skipped_apis || 0 }}</span>
              <span class="result-label">跳过接口</span>
            </div>
            <div class="result-item success">
              <span class="result-num">{{ importResult.created_categories || 0 }}</span>
              <span class="result-label">新建目录</span>
            </div>
            <div class="result-item success">
              <span class="result-num">{{ importResult.created_environments || 0 }}</span>
              <span class="result-label">新建环境</span>
            </div>
            <div class="result-item info">
              <span class="result-num">{{ importResult.created_test_cases || 0 }}</span>
              <span class="result-label">新建用例</span>
            </div>
          </div>

          <!-- 失败详情（可展开） -->
          <div v-if="resultData.failed_count > 0" class="result-warnings">
            <el-alert type="warning" :closable="false" show-icon>
              <template #title>
                部分接口导入失败：{{ resultData.failed_count }} 个失败，{{ resultData.skipped_count || 0 }} 个跳过
              </template>
            </el-alert>

            <el-collapse v-if="resultData.errors?.length" class="errors-collapse">
              <el-collapse-item>
                <template #title>
                  <span class="errors-collapse-title">查看失败详情 ({{ resultData.errors.length }})</span>
                </template>
                <div class="error-list">
                  <div v-for="(err, idx) in resultData.errors" :key="idx" class="error-item">
                    <span class="error-name-detail">{{ err.name }}</span>
                    <span class="error-reason-detail">{{ err.reason }}</span>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <div v-if="importResult.errors?.length || structuredErrors.length" class="import-warnings">
            <!-- 结构化错误展示 -->
            <template v-if="structuredErrors.length">
              <div v-for="(err, i) in structuredErrors.slice(0, 10)" :key="i" class="structured-error-item">
                <span class="error-name">{{ err.name || err.method ? `${err.method || ''} ${err.path || err.name || ''}` : `第 ${err.index || i+1} 条` }}</span>
                <span class="error-reason">{{ err.reason }}</span>
              </div>
              <p v-if="structuredErrors.length > 10" class="more-errors">
                还有 {{ structuredErrors.length - 10 }} 条警告未显示
              </p>
            </template>
            <!-- 兼容旧版字符串错误 -->
            <el-alert
              v-for="(err, i) in importResult.errors.slice(0, 5)"
              :key="'str-' + i"
              :title="err"
              type="warning"
              show-icon
              :closable="false"
            />
            <p v-if="importResult.errors.length > 5 && !structuredErrors.length" class="more-errors">
              还有 {{ importResult.errors.length - 5 }} 条警告未显示
            </p>
          </div>

          <el-button type="primary" @click="handleFinish">完成</el-button>
        </template>
      </el-result>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="step > 1 && step < 3" @click="step--">上一步</el-button>
        <el-button @click="handleClose">取消</el-button>

        <el-button
          v-if="step < 3"
          :disabled="canProceed === false || loading"
          :loading="loading && step === 2"
          @click="handleNext"
        >
          {{ loading && step === 2 ? '导入中...' : step === 1 ? '解析文件' : '开始导入' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { Upload, FileText, Folder, Plug } from 'lucide-vue-next'
import { importPreviewV2, importExecuteV2 } from '../api/import'
import type { ImportPreviewResponse, ImportExecuteResult } from '../api/import'
import yaml from 'js-yaml'
import { msgWarning, msgError } from '../utils/message'
import { useRequireLogin } from '../composables/useRequireLogin'
import { detectFormatByContent } from '../composables/useSceneImport'

/** 解析 JSON/YAML 解析错误，提取行号等结构化信息 */
function parseImportError(rawError: string): { line?: number; reason: string } {
  const posMatch = rawError.match(/position (\d+)/)
  if (posMatch) {
    const pos = parseInt(posMatch[1])
    const lines = rawError.split('\n')
    return {
      line: lines.findIndex((l, i) => {
        let acc = 0
        for (let j = 0; j <= i; j++) acc += lines[j].length + 1
        return acc > pos
      }) + 1,
      reason: rawError
    }
  }
  return { reason: rawError }
}

const { requireLogin } = useRequireLogin()

const props = defineProps<{
  modelValue: boolean
  projectId: number
  defaultCategoryId?: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  imported: [result: ImportExecuteResult]
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

interface UploadFile {
  raw?: File
  name?: string
  size?: number
}

interface StructuredError {
  index?: number
  name?: string
  method?: string
  path?: string
  reason: string
}

const step = ref(1)
const loading = ref(false)
const readingFile = ref(false)
const importing = ref(false)
const importError = ref(false)
const importProgress = ref(0)
const importProgressText = ref('正在导入...')
let lastImportContent = '' // 用于重试
const fileList = ref<UploadFile[]>([])
const showCurlInput = ref(false)
const curlText = ref('')
const selectedFile = ref<File | null>(null)
const rawFileContent = ref('')
const detectedFormat = ref('')
const manualFormat = ref('')
const showFormatSelector = ref(false)
const validationMsg = ref<{ type: 'success' | 'error'; message: string } | null>(null)
const previewData = ref<ImportPreviewResponse>({
  format: '',
  project_name: '',
  stats: { total_categories: 0, total_apis: 0, total_environments: 0, total_variables: 0, total_headers: 0 },
  categories: [],
  environments: [],
  global_variables: [],
  global_headers: [],
  test_cases: [],
})
const importOptions = ref<{
  importVariables: boolean
  importHeaders: boolean
  importEnvironments: boolean
  importTestCases: boolean
  conflictStrategy: 'skip' | 'update' | 'rename' | 'keep_both'
}>({
  importVariables: true,
  importHeaders: true,
  importEnvironments: true,
  importTestCases: true,
  conflictStrategy: 'update',
})
const importResult = ref<ImportExecuteResult>({
  created_apis: 0, updated_apis: 0, skipped_apis: 0,
  created_categories: 0, skipped_categories: 0,
  created_environments: 0, updated_environments: 0,
  imported_variables: 0, imported_headers: 0,
  created_test_cases: 0, updated_test_cases: 0, skipped_test_cases: 0,
  errors: [],
})
const structuredErrors = ref<StructuredError[]>([])

// 选择性导入
const selectedApiNames = ref<Set<string>>(new Set())

const allApiNames = computed(() => {
  const names: string[] = []
  function walk(nodes: ImportPreviewCategory[]) {
    for (const node of nodes) {
      if (node.isApi && node.name) {
        names.push(node.name)
      }
      if (node.children) {
        walk(node.children)
      }
    }
  }
  walk(previewData.value.categories || [])
  return names
})

const totalApiCount = computed(() => allApiNames.value.length)
const allApisSelected = computed(() => totalApiCount.value > 0 && selectedApiNames.value.size === totalApiCount.value)

function toggleApiSelection(name: string, val: boolean) {
  const newSet = new Set(selectedApiNames.value)
  if (val) newSet.add(name)
  else newSet.delete(name)
  selectedApiNames.value = newSet
}

function toggleSelectAll() {
  if (allApisSelected.value) {
    selectedApiNames.value = new Set()
  } else {
    selectedApiNames.value = new Set(allApiNames.value)
  }
}

function invertSelection() {
  const newSet = new Set<string>()
  for (const name of allApiNames.value) {
    if (!selectedApiNames.value.has(name)) {
      newSet.add(name)
    }
  }
  selectedApiNames.value = newSet
}

const canProceed = computed(() => {
  if (step.value === 1) return !!selectedFile.value && validationMsg.value?.type === 'success' && !readingFile.value
  return true
})

const detectedFormatTitle = computed(() => {
  const map: Record<string, string> = {
    apifox_project: 'Apifox 项目导出',
    apifox_collection: 'Apifox 接口导出',
    postman: 'Postman Collection',
    openapi: 'OpenAPI 3.0',
    swagger: 'Swagger 2.0',
    har: 'HAR (HTTP Archive)',
    yapi: 'YAPI 导出',
    eolink: 'Eolink 导出',
    apipost: 'Apipost 导出',
    bruno: 'Bruno 导出',
    general_json: '通用 JSON 格式',
  }
  return map[detectedFormat.value] || detectedFormat.value || '未知'
})

const formatOptions = [
  { value: 'openapi', label: 'OpenAPI 3.0', description: '标准 REST API 描述格式，支持 JSON/YAML，自动解析 $ref 引用和 Schema' },
  { value: 'swagger', label: 'Swagger 2.0', description: '旧版 API 描述格式，支持 definitions/parameters 引用解析' },
  { value: 'har', label: 'HAR (HTTP Archive)', description: '浏览器网络请求录制格式，自动从请求/响应对生成测试用例' },
  { value: 'apifox_project', label: 'Apifox 项目', description: 'Apifox 完整项目导出，含接口、用例、环境、变量' },
  { value: 'postman', label: 'Postman Collection', description: 'Postman 集合导出格式 v2.0/v2.1' },
  { value: 'yapi', label: 'YAPI', description: 'YAPI 接口管理平台导出格式' },
  { value: 'eolink', label: 'Eolink', description: 'Eolink 接口管理平台导出格式' },
  { value: 'apipost', label: 'Apipost', description: 'Apipost 接口管理平台导出格式' },
  { value: 'bruno', label: 'Bruno', description: 'Bruno API 客户端导出格式' },
]

function selectFormat(fmt: string) {
  manualFormat.value = fmt
  detectedFormat.value = fmt
  showFormatSelector.value = false
  validationMsg.value = { type: 'success', message: `已选择格式: ${formatOptions.find(f => f.value === fmt)?.label || fmt}` }
}

const resultStatus = computed<'success' | 'partial' | 'error'>(() => {
  if (importError.value) return 'error'
  const hasWarnings = (importResult.value.errors?.length || 0) > 0
  const hasData = (importResult.value.created_apis || 0) > 0 || (importResult.value.updated_apis || 0) > 0
  if (hasWarnings && hasData) return 'partial'
  if (hasData) return 'success'
  return 'error'
})

/** 导入结果增强数据，统一错误展示格式 */
const resultData = computed(() => {
  const failedCount = importResult.value.failed_count ?? 0
  const skippedCount = importResult.value.skipped_count ?? 0
  const structuredErrs = importResult.value.structured_errors || structuredErrors.value
  // 合并结构化错误 + 字符串错误
  const allErrors: Array<{ name: string; reason: string }> = [
    ...structuredErrs.map(e => ({
      name: e.name || e.method ? `${e.method || ''} ${e.path || e.name || ''}`.trim() || `第 ${e.index || '?'} 条` : '',
      reason: e.reason,
    })),
    ...(importResult.value.errors || []).map((e: string) => ({
      name: '',
      reason: e,
    })),
  ]
  return {
    failed_count: failedCount,
    skipped_count: skippedCount,
    errors: allErrors,
  }
})

// 当打开弹窗时重置
watch(() => props.modelValue, (val) => {
  if (val) resetState()
})

function resetState() {
  step.value = 1
  selectedFile.value = null
  rawFileContent.value = ''
  detectedFormat.value = ''
  manualFormat.value = ''
  showFormatSelector.value = false
  validationMsg.value = null
  previewData.value = {
    format: '', project_name: '',
    stats: { total_categories: 0, total_apis: 0, total_environments: 0, total_variables: 0, total_headers: 0 },
    categories: [], environments: [], global_variables: [], global_headers: [], test_cases: [],
  }
  importResult.value = {
    created_apis: 0, updated_apis: 0, skipped_apis: 0,
    created_categories: 0, skipped_categories: 0,
    created_environments: 0, updated_environments: 0,
    imported_variables: 0, imported_headers: 0,
    errors: [],
  }
  structuredErrors.value = []
  fileList.value = []
  selectedApiNames.value = new Set()
}

async function previewCurl() {
  if (!curlText.value.trim()) return
  rawFileContent.value = JSON.stringify({ _raw_text: curlText.value, _is_curl: true })
  loading.value = true
  validationMsg.value = null
  try {
    const res = await importPreviewV2(props.projectId, { file_content: rawFileContent.value })
    previewData.value = res.data
    detectedFormat.value = res.data.format
    if (res.data.stats?.total_test_cases) {
      importOptions.value.importTestCases = true
    }
    step.value = 2
  } catch (e: unknown) {
    validationMsg.value = { type: 'error', message: (e as { response?: { data?: { message?: string } } }).response?.data?.message || '解析 cURL 失败' }
  } finally {
    loading.value = false
  }
}

async function handleFileChange(uploadFile: UploadFile) {
  validationMsg.value = null
  detectedFormat.value = ''
  selectedFile.value = uploadFile.raw as File || null

  if (!selectedFile.value) return

  // 文件大小检查 (20MB)
  const MAX_FILE_SIZE = 20 * 1024 * 1024
  if (selectedFile.value.size > MAX_FILE_SIZE) {
    validationMsg.value = { type: 'error', message: `文件过大 (${formatSize(selectedFile.value.size)})，最大支持 20MB` }
    return
  }

  // 空文件检查
  if (selectedFile.value.size === 0) {
    validationMsg.value = { type: 'error', message: '文件内容为空' }
    return
  }

  readingFile.value = true
  try {
    const text = await readFileContent(selectedFile.value)

    // 二进制文件检测: 如果前 512 字节中包含大量不可打印字符，可能是二进制文件
    const sample = text.slice(0, 512)
    const nullCount = (sample.match(/\0/g) || []).length
    if (nullCount > 5) {
      validationMsg.value = { type: 'error', message: '该文件似乎是二进制文件，请选择文本格式的接口文件' }
      return
    }

    rawFileContent.value = text

    const trimmed = text.trim()
    if (!trimmed) {
      validationMsg.value = { type: 'error', message: '文件内容为空' }
      return
    }

    // 尝试解析: 先 JSON，再 YAML
    let parsed = false
    let parseError = ''
    try {
      JSON.parse(trimmed)
      parsed = true
    } catch (jsonErr: unknown) {
      // JSON 解析失败，尝试 YAML
      try {
        const yamlResult = yaml.safeLoad(trimmed)
        if (yamlResult && typeof yamlResult === 'object') {
          parsed = true
        }
      } catch (yamlErr: unknown) {
        // YAML 也失败，收集详细结构化错误信息
        const jsonMsg = jsonErr instanceof Error ? jsonErr.message : '解析失败'
        const yamlMsg = yamlErr instanceof Error ? yamlErr.message : '解析失败'
        // 尝试解析 JSON 错误位置
        const jsonStructured = parseImportError(jsonMsg)
        const lineInfo = jsonStructured.line ? ` (第 ${jsonStructured.line} 行附近)` : ''
        parseError = `JSON: ${jsonMsg}${lineInfo}; YAML: ${yamlMsg}`
      }
    }

    if (parsed) {
      // 基于内容检测格式（优先于扩展名）
      const contentFormat = detectFormatByContent(text)
      if (contentFormat) {
        detectedFormat.value = contentFormat
      } else {
        // 基于扩展名回退检测
        const ext = (selectedFile.value.name || '').toLowerCase().split('.').pop() || ''
        const extFormatMap: Record<string, string> = {
          apifox: 'apifox_project',
          har: 'har',
          postman: 'postman',
          collection: 'postman',
        }
        if (extFormatMap[ext]) {
          detectedFormat.value = extFormatMap[ext]
        }
      }
      validationMsg.value = { type: 'success', message: detectedFormat.value ? `检测到格式: ${detectedFormatTitle.value}` : '文件格式有效' }
    } else {
      validationMsg.value = {
        type: 'error',
        message: `文件解析失败: 不是有效的 JSON 或 YAML 格式。${parseError ? `错误详情: ${parseError}` : '请确保文件是接口定义文件'}`,
      }
    }
  } catch {
    validationMsg.value = {
      type: 'error',
      message: '文件读取失败，请稍后重试',
    }
  } finally {
    readingFile.value = false
  }
}

function handleExceed() {
  msgWarning('一次只能选择 1 个文件')
}

function clearFile() {
  fileList.value = []
  selectedFile.value = null
  rawFileContent.value = ''
  validationMsg.value = null
  detectedFormat.value = ''
  manualFormat.value = ''
  showFormatSelector.value = false
}

function readFileContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onprogress = (e) => {
      if (e.lengthComputable) {
        importProgress.value = Math.round((e.loaded / e.total) * 100)
      }
    }
    reader.onload = (e) => {
      let text = (e.target?.result as string) || ''
      // 去除 BOM 头 (UTF-8 BOM: U+FEFF)
      if (text.charCodeAt(0) === 0xFEFF) {
        text = text.slice(1)
      }
      resolve(text)
    }
    reader.onerror = reject
    reader.readAsText(file)
  })
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1_048_576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1_048_576).toFixed(1) + ' MB'
}

async function handleNext() {
  if (step.value === 1) {
    await doPreview()
  } else if (step.value === 2) {
    await doExecute()
  }
}

async function doPreview() {
  loading.value = true
  try {
    const res = await importPreviewV2(props.projectId, {
      file_content: rawFileContent.value,
    })
    previewData.value = res.data
    detectedFormat.value = res.data.format
    // 如果导入的测试用例默认勾选
    if (res.data.stats?.total_test_cases) {
      importOptions.value.importTestCases = true
    }
    // 预览成功后默认全选所有接口
    selectedApiNames.value = new Set(allApiNames.value)
    step.value = 2
  } catch (e: unknown) {
    const rawMsg = (e as { response?: { data?: { message?: string } } }).response?.data?.message || ''
    let msg = '预览失败，请检查文件格式'
    if (rawMsg) msg = rawMsg.includes('预览') ? rawMsg : `预览失败: ${rawMsg}`
    validationMsg.value = { type: 'error', message: msg }
  } finally {
    loading.value = false
  }
}

async function doExecute() {
  if (!(await requireLogin('导入接口'))) return
  loading.value = true
  importing.value = true
  importError.value = false
  importProgress.value = 30
  importProgressText.value = '正在发送文件到服务器...'

  // 先切换到步骤 3，让进度圆环在导入过程中可见
  step.value = 3

  try {
    const opts = importOptions.value
    importProgress.value = 50
    importProgressText.value = '正在解析并导入接口...'
    lastImportContent = rawFileContent.value
    
    const res = await importExecuteV2(props.projectId, {
      file_content: rawFileContent.value,
      import_options: {
        import_variables: opts.importVariables,
        import_headers: opts.importHeaders,
        import_environments: opts.importEnvironments,
        import_test_cases: opts.importTestCases,
        conflict_strategy: opts.conflictStrategy,
        target_category_id: props.defaultCategoryId,
      },
      selected_items: selectedApiNames.value.size > 0 ? Array.from(selectedApiNames.value) : undefined,
    })
    
    importProgress.value = 100
    importProgressText.value = '导入完成！'
    importResult.value = res.data
    structuredErrors.value = res.data.structured_errors || []
    
    // 即使导入有部分错误，也显示结果（而非卡在错误页）
    if (res.data.errors?.length > 0) {
      importProgressText.value = `导入完成（${res.data.errors.length} 条警告）`
    }
    
    safeTimeout(() => { importing.value = false }, 1500)
  } catch (e: unknown) {
    importError.value = true
    importProgress.value = 100
    const rawMsg = (e as { response?: { data?: { message?: string } } }).response?.data?.message || ''
    // 将技术性错误转为友好中文提示
    let errMsg = '导入失败，请检查文件格式后重试'
    if (rawMsg.includes('JSON') || rawMsg.includes('json') || rawMsg.includes('parse')) {
      errMsg = '文件格式无法识别，请确保上传的是有效的接口定义文件（Apifox/Postman/OpenAPI 等）'
    } else if (rawMsg.includes('size') || rawMsg.includes('Size') || rawMsg.includes('too large')) {
      errMsg = '文件过大，请压缩后重试（最大支持 20MB）'
    } else if (rawMsg.includes('empty') || rawMsg.includes('Empty')) {
      errMsg = '文件内容为空，请重新选择文件'
    } else if (rawMsg) {
      errMsg = rawMsg
    }
    importProgressText.value = errMsg
    msgError(errMsg)
  } finally {
    loading.value = false
  }
}

async function retryImport() {
  importError.value = false
  importProgress.value = 0
  rawFileContent.value = lastImportContent
  await doExecute()
}

function handleFinish() {
  handleClose()
  emit('imported', { ...importResult.value })
}

const cleanupTimers = new Set<ReturnType<typeof setTimeout>>()

function safeTimeout(fn: () => void, delay: number) {
  const timer = setTimeout(() => {
    fn()
    cleanupTimers.delete(timer)
  }, delay)
  cleanupTimers.add(timer)
  return timer
}

function handleClose() {
  dialogVisible.value = false
  safeTimeout(resetState, 300)
}

function getMethodTagType(method: string): string {
  const map: Record<string, string> = { GET: '', POST: 'success', PUT: 'warning', DELETE: 'danger', PATCH: 'info' }
  return map[method] || 'info'
}

onBeforeUnmount(() => {
  cleanupTimers.forEach(timer => clearTimeout(timer))
  cleanupTimers.clear()
})
</script>

<style scoped>
/* 导入向导 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角/阴影均使用 CSS 变量，确保暗色模式自动适配
 */
.import-steps { margin-bottom: var(--spacing-2xl); }
.step-content {
  min-height: 360px;
  max-height: calc(85vh - 160px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.upload-area { text-align: center; padding: var(--spacing-5xl) var(--spacing-lg); }
.upload-icon { color: var(--text-muted); margin: 0 auto; }
.upload-text { font-size: var(--font-size-lg); color: var(--text-secondary); margin-top: var(--spacing-md); }
.upload-hint { font-size: var(--font-size-sm); color: var(--text-muted); margin-top: var(--spacing-xs); }
.upload-hint em { color: var(--accent); font-style: normal; }
.upload-format { font-size: var(--font-size-xs); color: var(--text-muted); margin-top: var(--spacing-sm); }

.file-info {
  display: flex; align-items: center; gap: var(--spacing-sm); margin-top: var(--spacing-lg);
  padding: var(--spacing-sm) var(--spacing-md); background: var(--surface-nested); border-radius: var(--radius-md);
}
.file-name { font-weight: var(--weight-medium); color: var(--text-primary); }
.file-size { color: var(--text-muted); font-size: var(--font-size-xs); }

.parse-error-alert,
.parse-success-alert { margin-top: var(--spacing-lg); }

/* ── 格式选择器 ── */
.format-selector {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}
.format-selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}
.format-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--spacing-sm);
}
.format-option {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color var(--duration-fast) var(--ease-smooth),
              background var(--duration-fast) var(--ease-smooth);
}
.format-option:hover {
  border-color: var(--primary-300);
  background: var(--surface-hover);
}
.format-option.active {
  border-color: var(--primary-500);
  background: var(--color-primary-alpha-06);
}
.format-option-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}
.format-option-name {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}
.format-option-desc {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--spacing-xs);
  line-height: var(--leading-normal);
}
.format-detected {
  padding: var(--spacing-xs) 0;
}
.format-detected-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}
html.dark .format-option.active {
  background: var(--color-primary-alpha-12);
}

.file-reading-hint {
  display: flex; align-items: center; gap: var(--spacing-sm);
  margin-top: var(--spacing-md); font-size: var(--font-size-xs); color: var(--text-muted);
}
.file-reading-hint .el-icon { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.preview-stats { display: flex; gap: var(--spacing-md); margin-bottom: var(--spacing-lg); flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 90px; text-align: center; padding: var(--spacing-md) var(--spacing-sm);
  background: var(--surface-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm); border: 1px solid var(--border-subtle);
  transition: transform var(--duration-base) var(--ease-out),
              box-shadow var(--duration-base) var(--ease-out);
}
.stat-card:hover { box-shadow: var(--shadow-card-hover); transform: translateY(-2px); }
.stat-number { display: block; font-size: 2.75rem; font-weight: var(--weight-bold); font-family: var(--font-mono); }
.stat-number.primary { color: var(--primary-500); }
.stat-number.success { color: var(--success); }
.stat-number.warning { color: var(--warning); }
.stat-number.info { color: var(--info); }
.stat-label { font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs); }

.preview-section { margin-bottom: var(--spacing-lg); }
.preview-section h4 {
  margin-bottom: var(--spacing-sm); font-size: var(--font-size-sm); font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 预览树：固定高度 + 垂直滚动 */
.preview-tree-wrapper {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) 0;
  background: var(--surface-nested);
  flex-shrink: 0;
}
.preview-tree-wrapper::-webkit-scrollbar,
.step-content::-webkit-scrollbar,
.tc-list::-webkit-scrollbar { width: 6px; }
.preview-tree-wrapper::-webkit-scrollbar-track,
.step-content::-webkit-scrollbar-track,
.tc-list::-webkit-scrollbar-track { background: transparent; }
.preview-tree-wrapper::-webkit-scrollbar-thumb,
.step-content::-webkit-scrollbar-thumb,
.tc-list::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: var(--radius-2xs); }
.preview-tree-wrapper::-webkit-scrollbar-thumb:hover,
.step-content::-webkit-scrollbar-thumb:hover,
.tc-list::-webkit-scrollbar-thumb:hover { background: var(--scrollbar-thumb-hover); }

.tree-node { display: flex; align-items: center; gap: var(--spacing-xs); font-size: var(--font-size-sm); }
.tree-node-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
.tree-node-path {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
}

.selected-count {
  margin-left: auto;
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  font-weight: var(--weight-normal);
}

.tc-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  max-height: 280px;
  overflow-y: auto;
}
.tc-item { display: flex; align-items: center; gap: var(--spacing-sm); padding: var(--spacing-xs) var(--spacing-sm); font-size: var(--font-size-sm); }
.tc-name { font-weight: var(--weight-medium); color: var(--text-primary); flex: 1; }
.tc-assertions { color: var(--text-muted); font-size: var(--font-size-xs); }
.tc-more { color: var(--text-muted); font-size: var(--font-size-xs); text-align: center; padding-top: var(--spacing-xs); }

.env-card {
  padding: var(--spacing-sm) var(--spacing-md); background: var(--surface-nested);
  border-radius: var(--radius-md); margin-bottom: var(--spacing-sm);
}
.env-header { display: flex; justify-content: space-between; align-items: center; }
.env-name { font-weight: var(--weight-medium); color: var(--text-primary); font-size: var(--font-size-sm); }
.env-detail { display: flex; gap: var(--spacing-lg); margin-top: var(--spacing-xs); font-size: var(--font-size-xs); color: var(--text-secondary); }
.env-detail code {
  background: var(--surface-code); padding: 0 var(--spacing-xs); border-radius: var(--radius-sm); font-family: var(--font-mono);
}

.import-options {
  padding: var(--spacing-lg); background: var(--surface-nested); border-radius: var(--radius-md); margin-top: var(--spacing-lg);
}
.import-options h4 {
  margin-bottom: var(--spacing-md); font-size: var(--font-size-sm); font-weight: var(--weight-semibold); color: var(--text-primary);
}
.options-grid { display: flex; flex-wrap: wrap; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.import-options .el-checkbox { margin-right: 0; }
.conflict-strategy {
  margin-top: var(--spacing-md); display: flex; align-items: center; gap: var(--spacing-sm);
  font-size: var(--font-size-sm); color: var(--text-secondary); flex-wrap: wrap;
}

.result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--spacing-md); margin-bottom: var(--spacing-lg); }
.result-item { text-align: center; padding: var(--spacing-md); border-radius: var(--radius-md); }
.result-item.success { background: var(--success-bg); }
.result-item.warning { background: var(--warning-bg); }
.result-item.info { background: var(--info-bg); }
.result-num { display: block; font-size: 2.75rem; font-weight: var(--weight-bold); font-family: var(--font-mono); }
.result-label { font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs); }

.import-warnings { margin-bottom: var(--spacing-lg); }
.import-warnings .el-alert { margin-bottom: var(--spacing-sm); }
.more-errors { text-align: center; font-size: var(--font-size-xs); color: var(--text-muted); }

.structured-error-item {
  display: flex; align-items: center; gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--surface-nested); border-radius: var(--radius-sm);
  margin-bottom: var(--spacing-xs);
  font-size: var(--font-size-xs);
}
.error-name {
  font-weight: var(--weight-medium); color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 200px;
}
.error-reason { color: var(--warning-text); }

/* 对话框高度约束：防止内容过多时超出屏幕 */
:deep(.import-wizard-dialog) {
  max-height: 88vh !important;
  margin-top: 4vh !important;
  display: flex !important;
  flex-direction: column !important;
}
:deep(.import-wizard-dialog .el-dialog__body) {
  flex: 1 !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

.dialog-footer { display: flex; justify-content: flex-end; gap: var(--spacing-sm); }

html.dark .stat-card { background: var(--surface-card); border-color: var(--border-subtle); }
html.dark .env-card { background: var(--surface-nested); }
html.dark .import-options { background: var(--surface-nested); }
html.dark .preview-tree-wrapper { border-color: var(--border-subtle); background: var(--surface-nested); }

/* ── cURL 粘贴区域 ── */
.curl-section {
  margin-top: var(--spacing-lg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.curl-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer;
  background: var(--surface-hover);
  user-select: none;
  transition: background var(--duration-fast) var(--ease-smooth);
}
.curl-section-header:hover {
  background: var(--surface-active);
}
.curl-section-title {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
}
.curl-section-header .el-icon { transition: transform var(--duration-base) var(--ease-smooth); }
.curl-section-header .el-icon.rotated { transform: rotate(180deg); }
.curl-input-area {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--border-subtle);
}
.curl-textarea {
  width: 100%;
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: var(--leading-normal);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  background: var(--surface-input);
  resize: vertical;
  outline: none;
  transition: border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}
.curl-textarea:focus {
  border-color: var(--primary-500);
  box-shadow: var(--shadow-focus);
}
.curl-textarea::placeholder {
  color: var(--text-placeholder);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
}
.curl-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all var(--duration-base) var(--ease-smooth);
}
.slide-fade-enter-from, .slide-fade-leave-to {
  opacity: 0;
  max-height: 0;
}
html.dark .curl-section { border-color: var(--border-subtle); }
html.dark .curl-section-header { background: var(--surface-nested); }
html.dark .curl-input-area { border-color: var(--border-subtle); }

/* ===== ImportWizard 暗色模式补全 ===== */
html.dark .format-option {
  background: var(--surface-card);
  border-color: var(--border-default);
}
html.dark .format-option:hover {
  background: var(--surface-hover);
  border-color: var(--border-strong);
}
html.dark .format-name { color: var(--text-primary); }
html.dark .format-desc { color: var(--text-muted); }
html.dark .format-detected-label { color: var(--text-secondary); }
html.dark .file-reading-hint { color: var(--text-muted); }

html.dark .stat-number.primary { color: var(--primary-400); }
html.dark .stat-number.success { color: var(--success-400); }
html.dark .stat-number.warning { color: var(--warning-400); }
html.dark .stat-number.info { color: var(--info-400); }
html.dark .stat-label { color: var(--text-muted); }

html.dark .preview-section h4 { color: var(--text-primary); }
html.dark .tree-node-name { color: var(--text-primary); }
html.dark .tree-node-path { color: var(--text-muted); }
html.dark .selected-count { color: var(--text-muted); }
html.dark .tc-name { color: var(--text-primary); }
html.dark .tc-assertions { color: var(--text-muted); }
html.dark .tc-more { color: var(--text-muted); }

html.dark .env-name { color: var(--text-primary); }
html.dark .env-detail { color: var(--text-secondary); }
html.dark .env-detail code { background: var(--surface-code); }

html.dark .import-options h4 { color: var(--text-primary); }
html.dark .conflict-strategy { color: var(--text-secondary); }

html.dark .result-item.success { background: var(--success-bg); }
html.dark .result-item.warning { background: var(--warning-bg); }
html.dark .result-item.info { background: var(--info-bg); }
html.dark .result-label { color: var(--text-muted); }

html.dark .more-errors { color: var(--text-muted); }
html.dark .structured-error-item { background: var(--surface-nested); }
html.dark .error-name { color: var(--text-primary); }
html.dark .error-reason { color: var(--warning-text); }

html.dark .curl-section-title { color: var(--text-secondary); }
html.dark .curl-textarea {
  background: var(--surface-input);
  border-color: var(--border-default);
  color: var(--text-primary);
}
html.dark .curl-textarea:focus {
  border-color: var(--primary-400);
  box-shadow: var(--shadow-focus);
}
html.dark .curl-textarea::placeholder { color: var(--text-placeholder); }

html.dark .errors-collapse { border-color: var(--border-subtle); }
html.dark .errors-collapse-title { color: var(--text-secondary); }
html.dark .error-list .error-item { border-bottom-color: var(--border-default); }
html.dark .error-name-detail { color: var(--text-primary); }
html.dark .error-reason-detail { color: var(--text-muted); }
html.dark .importing-text { color: var(--text-secondary); }

/* ── 导入失败详情（可展开）── */
.result-warnings {
  margin-top: var(--space-4);
}

.errors-collapse {
  margin-top: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.errors-collapse-title {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.error-list {
  max-height: 300px;
  overflow-y: auto;
  padding: var(--space-2) 0;
}

.error-list .error-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}

.error-list .error-item:last-child {
  border-bottom: none;
}

.error-name-detail {
  flex-shrink: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  min-width: 120px;
}

.error-reason-detail {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--leading-normal);
  word-break: break-all;
}

/* ── 导入进度动画 ── */
.importing-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  gap: var(--spacing-lg);
}
.importing-text {
  font-size: var(--font-size-lg);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}
</style>

<!-- 非scoped：el-dialog teleport 到 body，需要全局选择器 -->
<style>
.import-wizard-dialog {
  max-height: 88vh !important;
  margin-top: 4vh !important;
  display: flex !important;
  flex-direction: column !important;
}
.import-wizard-dialog .el-dialog__header {
  flex-shrink: 0 !important;
}
.import-wizard-dialog .el-dialog__body {
  flex: 1 !important;
  min-height: 0 !important;
  overflow-y: auto !important;
}
.import-wizard-dialog .el-dialog__footer {
  flex-shrink: 0 !important;
  padding-top: var(--space-4) !important;
  border-top: 1px solid var(--border-subtle);
}
/* 暗色模式对话框适配 */
html.dark .import-wizard-dialog .el-dialog__body {
  background: var(--surface-card);
  color: var(--text-primary);
}
html.dark .import-wizard-dialog .el-dialog__footer {
  border-top-color: var(--border-subtle);
}
</style>
