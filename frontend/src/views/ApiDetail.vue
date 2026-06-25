<template>
  <div class="api-detail" @change="onApiEdit">
    <!-- 面包屑导航 -->
    <BreadcrumbNav :items="breadcrumbItems" />
    <!-- 页面头部 -->
    <div v-if="!pageLoading" class="page-head api-hero">
      <div class="page-head-content">
        <div class="api-hero-main compact">
          <h1 class="page-title">
            <span class="api-method-badge" :class="String(apiData.method).toLowerCase()">{{ apiData.method }}</span>
            <span
              v-if="!editingName"
              class="api-name-display"
              @click="startEditName"
              :title="$t('apiDetail.clickToEditName')"
            >
              {{ apiData.name || $t('api.newApi') }}
              <EditIcon :size="14" class="api-name-edit-icon" />
            </span>
            <input
              v-else
              ref="nameInputRef"
              v-model="editingNameValue"
              class="api-name-input"
              @blur="finishEditName"
              @keydown.enter="finishEditName"
              @keydown.escape="cancelEditName"
              :placeholder="$t('apiDetail.inputApiName')"
            />
          </h1>
          <div class="api-hero-summary-row">
            <code class="api-hero-path-code">{{ apiData.path || '/' }}</code>
            <span class="api-hero-meta-inline">
              <span v-if="apiData.status" class="api-status-badge" :class="apiData.status || 'draft'">{{ statusLabel }}</span>
              <span v-if="apiData.auth?.type && apiData.auth.type !== 'none'">{{ apiData.auth.type }}</span>
            </span>
            <span v-if="apiData.tags && apiData.tags.length > 0" class="api-hero-tags">
              <span v-for="tagName in apiData.tags" :key="tagName" class="api-hero-tag">{{ tagName }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
    <!-- 骨架屏 -->
    <div v-if="pageLoading" class="api-skeleton">
      <div class="skeleton-request-line">
        <div class="skeleton-block skeleton-method"></div>
        <div class="skeleton-block skeleton-path"></div>
        <div class="skeleton-block skeleton-send"></div>
      </div>
      <div class="skeleton-toolbar">
        <div class="skeleton-block skeleton-env"></div>
      </div>
      <div class="skeleton-tabs">
        <div class="skeleton-block skeleton-tab" v-for="i in 6" :key="i"></div>
      </div>
      <div class="skeleton-body">
        <div class="skeleton-panel">
          <div class="skeleton-block skeleton-param-row" v-for="i in 4" :key="i"></div>
        </div>
        <div class="skeleton-divider"></div>
        <div class="skeleton-panel">
          <div class="skeleton-block skeleton-response-header"></div>
          <div class="skeleton-block skeleton-response-body"></div>
        </div>
      </div>
    </div>
    <div v-else class="detail-body" ref="detailBodyRef">
      <div class="request-panel" ref="requestPanelRef" :style="{ flex: '0 0 ' + topHeight + '%' }">
        <!-- 请求行：URL + 操作按钮 -->
        <div class="request-line-row">
          <div class="env-quick-switch">
            <span class="env-switch-label">{{ $t('scene.envLabel') }}</span>
            <el-select
              :model-value="envStore.currentEnvId"
              @update:model-value="envStore.switchEnv($event)"
              size="small"
              :placeholder="$t('scene.envPlaceholder')"
              class="env-switch-select"
              :disabled="!envStore.environments.length"
            >
              <el-option
                v-for="env in envStore.environments"
                :key="env.id"
                :label="env.name"
                :value="env.id"
              />
            </el-select>
          </div>
          <Transition name="save-indicator-fade">
            <span v-if="showSaveIndicator" class="save-indicator">✓ 已保存</span>
          </Transition>
          <RequestLine
            :api="apiData"
            :loading="sending"
            :api-saved="!!apiData.id"
            :project-id="projectId"
            :can-edit="canEdit"
            @send="onSend"
            @save="onSave"
            @save-as-case="showSaveCaseDialog = true"
            @generate-code="showCodeSnippetDialog = true"
            @clone-api="onCloneApi"
            @import-curl="showCurlImportDialog = true"
            @update:name="apiData.name = $event"
          />
        </div>
        <div class="panel-header">
          <ParamTabs
            :api="apiData"
            :active-tab="activeParamTab"
            @update:active-tab="activeParamTab = $event"
          />
          <button class="var-preview-toggle" :class="{ active: showVarPreview }" @click="showVarPreview = !showVarPreview" :title="$t('apiDetail.varPreview')">
            <span class="var-icon">{}</span>
            <span>{{ $t('apiDetail.variables') }}</span>
          </button>
          <el-tooltip placement="top" :show-after="300" :content="$t('apiDetail.varHelpTooltip')">
            <button class="var-help-btn" :aria-label="$t('apiDetail.varHelpTooltip')">
              <HelpCircle :size="14" />
            </button>
          </el-tooltip>
        </div>
        <div class="panel-body">
          <ParamsTable v-if="activeParamTab === 'params'" v-model="apiData.params" />
          <component :is="BodyEditor" v-else-if="activeParamTab === 'body'" v-model="apiData.body" :method="apiData.method" />
          <HeadersTable
            ref="headersRef"
            v-else-if="activeParamTab === 'headers'"
            v-model="apiData.headers"
          />

          <AuthPanel v-else-if="activeParamTab === 'auth'" v-model="apiData.auth" />
          <ResponseExamplePanel
            v-else-if="activeParamTab === 'response-examples'"
            v-model:examples="apiData.response_examples"
          />
          <AssertionTab v-else-if="activeParamTab === 'assertions'" v-model="apiData.assertions" />
          <!-- 历史版本 → 使用 ApiHistoryPanel 组件 -->
          <ApiHistoryPanel
            v-else-if="activeParamTab === 'history'"
            :snapshots="snapshots"
            :loading="loadingSnapshots"
            :selected-id="selectedSnapshotId"
            :diff="snapshotDiff"
            @select="onSelectSnapshot"
            @restore="onRestoreSnapshot"
          />

          <CasesTab
            v-else-if="activeParamTab === 'cases'"
            :cases="apiCases"
            :selected-case-id="selectedCaseId"
            :loading="casesLoading"
            @create="createCase"
            @select="selectCase"
            @run="runCase"
            @copy="copyCase"
            @delete="deleteCase"
            @batch-delete="handleBatchDeleteCases"
          />
          <DocsPreview v-else-if="activeParamTab === 'docs-preview'" :api="apiData" />
          <DocEditorTab
            v-else-if="activeParamTab === 'docs'"
            :project-id="projectId"
            :api-id="apiData.id ?? 0"
          />
          <!-- 设置 → 使用 ApiSettingsPanel 组件 -->
          <ApiSettingsPanel
            v-else-if="activeParamTab === 'settings'"
            :description-md="apiData.description_md"
            :tags="apiData.tags"
            :project-tags="projectTags"
            :settings="apiData.settings"
            @update:description-md="apiData.description_md = $event"
            @update:tags="apiData.tags = $event"
            @update:setting="(key, value) => { apiData.settings = { ...apiData.settings, [key]: value } }"
          />
          <!-- 前置操作 -->
          <ApiScriptPanel
            v-else-if="activeParamTab === 'pre-script'"
            :model-value="apiData.pre_script"
            :title="t('apiDetail.preScript')"
            :description="t('apiDetail.preScriptDesc')"
            :placeholder="preScriptPlaceholder"
            :snippets="preScriptSnippets"
            :available-objects="['variables', 'request', 'environment']"
            :debug-open="preDebugOpen"
            :debug-logs="preDebugLogs"
            @update:model-value="apiData.pre_script = $event"
            @insert-snippet="(code: string) => preScriptEditorRef?.insertText(code)"
            @toggle-debug="preDebugOpen = !preDebugOpen"
          />
          <!-- 后置操作 -->
          <ApiScriptPanel
            v-else-if="activeParamTab === 'post-script'"
            :model-value="apiData.post_script"
            :title="t('apiDetail.postScript')"
            :description="t('apiDetail.postScriptDesc')"
            :placeholder="postScriptPlaceholder"
            :snippets="postScriptSnippets"
            :available-objects="['variables', 'response', 'environment']"
            :debug-open="postDebugOpen"
            :debug-logs="postDebugLogs"
            @update:model-value="apiData.post_script = $event"
            @insert-snippet="(code: string) => postScriptEditorRef?.insertText(code)"
            @toggle-debug="postDebugOpen = !postDebugOpen"
          />
          <div v-else-if="activeParamTab === 'extract-vars'" class="extract-vars-tab">
            <div class="extract-header-hint">
              {{ $t('apiDetail.extractVarsHint') }}
            </div>
            <VariableExtractTab v-model="apiData.extract_vars" />
          </div>
          <div v-else>
            <EmptyState illustration="empty" :title="$t('apiDetail.noContent')" :description="$t('apiDetail.noContentDesc')" />
          </div>
        </div>
      </div>
      <!-- 变量预览折叠面板 -->
      <div v-if="showVarPreview" class="var-preview-panel">
        <VariablePreview
          mode="api"
          :title="t('apiDetail.varPreview')"
          :request-expressions="_requestExpressions"
          :all-vars="envStore.allVariablesForPreview"
        />
      </div>
      <div class="resize-handle" ref="resizeHandleRef" @mousedown="startResize" @dblclick="startResize"></div>
      <div class="response-panel" :style="{ flex: '0 0 ' + (100 - topHeight) + '%' }">
        <ResponsePanel :response="responseData" :loading="sending" :project-id="projectId" @send="onSend" @add-extract-rule="onAddExtractRule" />
      </div>
    </div>
    <SaveCaseDialog
      v-model="showSaveCaseDialog"
      :project-id="projectId"
      :api-id="apiData.id ?? 0"
      :api-name="apiData.name"
      :request-body="apiData.body"
      :extract-rules="apiData.extract_vars"
      :request-headers="apiData.headers"
      :request-params="apiData.params"
      :assertions="apiData.assertions"
      :pre-script="apiData.pre_script"
      :post-script="apiData.post_script"
      :categories="apiStore.categories"
      @saved="handleCaseSaved($event)"
    />
    <CodeSnippetDialog
      :visible="showCodeSnippetDialog"
      :project-id="projectId"
      :api-id="apiData.id ?? 0"
      :env-id="envStore.currentEnvId"
      @update:visible="showCodeSnippetDialog = $event"
    />

    <!-- cURL 导入对话框 -->
    <el-dialog
      v-model="showCurlImportDialog"
      :title="t('apiDetail.curlImport')"
      width="640px"
      :close-on-click-modal="false"
      class="curl-import-dialog"
    >
      <div class="curl-import-hint">{{ $t('apiDetail.curlImportHint') }}</div>
      <el-input
        v-model="curlCommand"
        type="textarea"
        :rows="8"
        :aria-label="$t('apiDetail.curlImport')"
        placeholder="curl -X POST 'https://api.example.com/users' \
  -H 'Content-Type: application/json' \
  -d '{&quot;name&quot;: &quot;test&quot;}'"
        class="curl-input"
        spellcheck="false"
      />
      <template #footer>
        <el-button size="small" @click="showCurlImportDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="curlImporting" @click="onCurlImport">{{ $t('apiDetail.import') }}</el-button>
      </template>
    </el-dialog>

    <!-- 新建接口选择目录弹窗 -->
    <el-dialog
      v-model="showCategoryDialog"
      :title="t('apiDetail.selectCategory')"
      width="420px"
      :close-on-click-modal="false"
      class="category-dialog"
    >
      <div class="category-dialog-hint">{{ $t('apiDetail.selectCategoryHint') }}</div>
      <div class="category-tree-wrapper">
        <el-tree
          ref="categoryTreeRef"
          :data="categoryTree"
          :props="{ label: 'name', children: 'children' }"
          node-key="id"
          highlight-current
          :default-expanded-keys="defaultExpandedKeys"
          @current-change="onCategorySelect"
        />
      </div>
      <template #footer>
        <el-button size="small" @click="showCategoryDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button
          size="small"
          type="primary"
          :disabled="!selectedCategoryId"
          @click="selectedCategoryId && handleCategoryConfirm(selectedCategoryId)"
          >
{{ $t('apiDetail.saveToCategory') }}
</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useI18n } from "vue-i18n"
import { ElMessageBox, ElMessage } from "element-plus"
import { getApi, testApi, createApi, updateApi, listApiCases, duplicateApi, type ApiDetail, type ApiTestResult } from "../api/apis"
import { getCase, deleteCase as deleteCaseApi, runCase as runCaseApi, createApiCase } from "../api/cases"
import { runPreScript, runPostScript } from "../utils/scriptRunner"
import { useEditorStore } from "../stores/editorStore"
import { useEnvStore } from "../stores/envStore"
import { useApiStore } from "../stores/apiStore"
import { useTabsStore } from "../stores/tabsStore"
import { usePendingApiStore } from "../stores/pendingApiStore"
import { useProjectStore } from "../stores/projectStore"
import { MSG } from "../constants/messages"
import { msgSuccess, msgError } from "../utils/message"
import { logger, isSilentAuthError } from "../utils/logger"
import { useRequireLogin } from "../composables/useRequireLogin"
import { useProjectPermission } from "../composables/useProjectPermission"
import RequestLine from "../components/RequestLine.vue"
import ParamTabs from "../components/ParamTabs.vue"
import ParamsTable from "../components/ParamsTable.vue"
import HeadersTable from "../components/HeadersTable.vue"
import AuthPanel from "../components/AuthPanel.vue"
import ResponseExamplePanel from "../components/ResponseExamplePanel.vue"
import AssertionTab from "../components/AssertionTab.vue"
import CasesTab from "../components/CasesTab.vue"
import DocsPreview from "../components/DocsPreview.vue"
import DocEditorTab from "../components/DocEditorTab.vue"
import DiffViewer from "../components/common/DiffViewer.vue"
import SkeletonTable from "../components/SkeletonTable.vue"
import EmptyState from "../components/EmptyState.vue"
import BreadcrumbNav from "../components/common/BreadcrumbNav.vue"
import type { BreadcrumbItem } from "../components/common/BreadcrumbNav.vue"
import { listSnapshots, diffSnapshots, restoreSnapshot, type Snapshot, type SnapshotDiff } from "../api/snapshots"
import { importCurl } from "../api/import"
import VariablePreview from "../components/VariablePreview.vue"
import SaveCaseDialog from "../components/SaveCaseDialog.vue"
import CodeSnippetDialog from "../components/CodeSnippetDialog.vue"

import VariableExtractTab from "../components/VariableExtractTab.vue"
import CodeEditor from "../components/CodeEditor.vue"
import type CodeEditorType from "../components/CodeEditor.vue"

import BodyEditor from "../components/BodyEditor.vue"
import ResponsePanel from "../components/ResponsePanel.vue"
import { useKeyboardShortcut } from "../composables/useKeyboardShortcut"
import { Edit as EditIcon, ChevronDown, HelpCircle } from "lucide-vue-next"

import { MdEditor } from "md-editor-v3"
import "md-editor-v3/lib/style.css"
import { listTags, type TagItem } from "../api/tags"

const { canEdit } = useProjectPermission()

// 快捷键配置
useKeyboardShortcut([
  {
    key: "s",
    ctrl: true,
    handler: () => {
      void onSave()
    },
    preventDefault: true,
  },
  { key: "Escape", handler: onEscape },
])

// Ctrl+Enter 全局快捷键：在请求编辑区域触发发送
function handleGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    const el = document.activeElement
    if (el && (el.closest('.request-panel') || el.closest('.api-detail-request'))) {
      e.preventDefault()
      void onSend()
    }
  }
}

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = Number(route.params.id)
const apiIdParam = computed(() => route.params.apiId as string)
const isNewApi = computed(() => !route.params.apiId || route.params.apiId === "new")

const breadcrumbItems = computed<BreadcrumbItem[]>(() => [
  { label: t('nav.apis'), to: `/projects/${projectId}/apis` },
  { label: apiData.value.name || t('api.newApi') },
])

const isLoadingApi = ref(false)
interface ApiDetailFormData extends ApiDetail {
  assertions: Array<{ expression: string; expected: string; comparator: string; description?: string; enabled?: boolean }>
}
const apiData = ref<ApiDetailFormData>({
  id: 0,
  project_id: 0,
  name: t('api.newApi'),
  method: "GET",
  path: "",
  headers: [],
  params: [],
  body: { type: "none", content: "" },
  cookies: [],
  auth: { type: "none" },
  auth_type: "none",
  pre_script: "",
  post_script: "",
  assertions: [],
  extract_vars: [],
  description: "",
  description_md: "",
  tags: [],
  settings: { follow_redirects: true, verify_ssl: true, timeout: 30 },
  category_id: null,
  response_schema: "",
  response_examples: [],
  status: "draft",
  is_starred: false,
  sort_order: 0,
  case_count: 0,
  created_by: 0,
  created_at: "",
  updated_at: "",
})
const pageLoading = ref(true)
const responseData = ref<ApiTestResult | null>(null)
const sending = ref(false)
const editorStore = useEditorStore()
const envStore = useEnvStore()
const { requireLogin } = useRequireLogin()
const projectStore = useProjectStore()

// 接口名称编辑
const editingName = ref(false)
const editingNameValue = ref("")
const nameInputRef = ref<HTMLInputElement | null>(null)

function startEditName() {
  editingNameValue.value = apiData.value.name || ""
  editingName.value = true
  void nextTick(() => {
    nameInputRef.value?.focus()
    nameInputRef.value?.select()
  })
}

function finishEditName() {
  if (editingNameValue.value.trim()) {
    apiData.value.name = editingNameValue.value.trim()
  }
  editingName.value = false
}

function cancelEditName() {
  editingName.value = false
}

const _requestExpressions = computed(() => {
  const exprs: string[] = []
  // 域名（base_url）中的变量
  const baseUrl = envStore.currentServiceUrl || ''
  if (baseUrl) {
    const matches = baseUrl.matchAll(/\{\{[^}]+\}\}/g)
    for (const m of matches) exprs.push(m[0])
  }
  // path 中的变量
  const api = apiData.value
  if (api?.path) {
    const matches = api.path.matchAll(/\{\{[^}]+\}\}/g)
    for (const m of matches) exprs.push(m[0])
  }
  if (api?.params) {
    try {
      const params = typeof api.params === "string" ? JSON.parse(api.params) : api.params
      Object.values(params).forEach((v: unknown) => {
        if (typeof v === "string" && v.includes("{{")) {
          const matches = v.matchAll(/\{\{[^}]+\}\}/g)
          for (const m of matches) exprs.push(m[0])
        }
      })
    } catch {
      /* ignore */
    }
  }
  if (api?.headers) {
    try {
      const headers = typeof api.headers === "string" ? JSON.parse(api.headers) : api.headers
      Object.values(headers).forEach((v: unknown) => {
        if (typeof v === "string" && v.includes("{{")) {
          const matches = v.matchAll(/\{\{[^}]+\}\}/g)
          for (const m of matches) exprs.push(m[0])
        }
      })
    } catch {
      /* ignore */
    }
  }
  if (api?.body?.content && typeof api.body.content === "string") {
    const matches = api.body.content.matchAll(/\{\{[^}]+\}\}/g)
    for (const m of matches) exprs.push(m[0])
  }
  return [...new Set(exprs)]
})

const statusLabel = computed(() => {
  const s = apiData.value.status || "draft"
  const map: Record<string, string> = {
    published: t('apiDetail.statusPublished'),
    draft: t('apiDetail.statusDraft'),
    deprecated: t('apiDetail.statusDeprecated'),
  }
  return map[s] || t('apiDetail.statusDraft')
})

const apiStore = useApiStore()
const tabsStore = useTabsStore()
const { removePendingNewApi } = usePendingApiStore()
const showSaveCaseDialog = ref(false)
const showCodeSnippetDialog = ref(false)
const showCurlImportDialog = ref(false)
const curlCommand = ref("")
const curlImporting = ref(false)
const activeParamTab = ref<string>("params")
const snapshots = ref<Snapshot[]>([])
const loadingSnapshots = ref(false)
const selectedSnapshotId = ref<number | null>(null)
const snapshotDiff = ref<SnapshotDiff | null>(null)
const redirectTimer = ref<ReturnType<typeof setTimeout> | null>(null)

// 调试控制台状态
const preDebugOpen = ref(false)
const postDebugOpen = ref(false)
const preDebugLogs = ref<{ time: string; level: string; message: string }[]>([])
const postDebugLogs = ref<{ time: string; level: string; message: string }[]>([])
const showVarPreview = ref(false)

// 脚本编辑器 ref（用于插入代码片段）
const preScriptEditorRef = ref<InstanceType<typeof CodeEditorType> | null>(null)
const postScriptEditorRef = ref<InstanceType<typeof CodeEditorType> | null>(null)

// 代码片段
const preScriptSnippets = [
  { label: t('apiDetail.snippetSetVar'), code: 'pm.variables.set("key", "value");\n' },
  { label: t('apiDetail.snippetGetVar'), code: 'var val = pm.variables.get("key");\n' },
  { label: t('apiDetail.snippetSetHeader'), code: 'pm.request.headers.push({ key: "X-Custom", value: "value" });\n' },
  { label: t('apiDetail.snippetModifyBody'), code: 'pm.request.body = { type: "json", content: JSON.stringify({ key: "value" }) };\n' },
  { label: t('apiDetail.snippetCondition'), code: 'if (pm.variables.get("token")) {\n  pm.request.headers.push({ key: "Authorization", value: "Bearer " + pm.variables.get("token") });\n}\n' },
]
const postScriptSnippets = [
  { label: t('apiDetail.snippetExtractJson'), code: 'var data = pm.response.json();\n' },
  { label: t('apiDetail.snippetGetStatus'), code: 'var status = pm.response.status;\n' },
  { label: t('apiDetail.snippetExtractToEnv'), code: 'pm.variables.set("key", pm.response.json().field);\n' },
  { label: t('apiDetail.snippetGetHeader'), code: 'var contentType = pm.response.headers["content-type"];\n' },
  { label: t('apiDetail.snippetConditionExtract'), code: 'if (pm.response.status === 200) {\n  pm.variables.set("token", pm.response.json().token);\n}\n' },
]

// 标签
const projectTags = ref<TagItem[]>([])

async function loadProjectTags() {
  try {
    const res = await listTags(projectId)
    projectTags.value = res.data || []
  } catch {
    projectTags.value = []
  }
}

// 脚本编辑器 placeholder
const preScriptPlaceholder = t('apiDetail.preScriptPlaceholder')
const postScriptPlaceholder = t('apiDetail.postScriptPlaceholder')

// 提取变量规则已迁移到 apiData.extract_vars（随 API 持久化到后端）
const apiCases = ref<{ id: number; name: string }[]>([])
const casesLoading = ref(false)
const selectedCaseId = ref<number | null>(null)

function detectDefaultTab(api: ApiDetailFormData): string {
  // 有 body 内容（JSON/form/text 等非 none）→ 优先显示 body
  if (api?.body && api.body.type !== "none") return "body"
  if (api?.params?.length > 0) return "params"
  if (api?.headers?.length > 0) return "headers"
  if (api?.assertions?.length > 0) return "assertions"
  return "params"
}
const topHeight = ref(40)
const resizeHandleRef = ref<HTMLElement | null>(null)
const detailBodyRef = ref<HTMLElement | null>(null)

// ── 新建接口接口目录选择 ──
const showCategoryDialog = ref(false)
const pendingSendAfterSave = ref(false)
const selectedCategoryId = ref<number | null>(null)
const pendingCategoryId = ref<string | null>(null) // 保存 sessionStorage 中的 new_api_category 值
const categoryTree = computed(() => apiStore.categories)
const defaultExpandedKeys = computed(() => apiStore.categories.map((c) => c.id))

async function loadApiData() {
  const currentApiId = route.params.apiId as string
  const currentIsNew = !currentApiId || currentApiId === "new"

  // 加载期间标记，防止 deep watch 误触发 markDirty
  isLoadingApi.value = true
  // 检查是否从新建接口跳转过来（跳过骨架屏）
  const skipLoading = history.state?.skipLoading
  const stateApiData = history.state?.apiData
  // 重置状态
  pageLoading.value = !skipLoading
  activeParamTab.value = "params"
  topHeight.value = 40
  // 清除旧 API 的响应数据
  responseData.value = null
  // 从 sessionStorage 恢复上次响应（非新建接口时）
  if (!currentIsNew) {
    try {
      const cached = sessionStorage.getItem(`resp_${projectId}_${currentApiId}`)
      if (cached) responseData.value = JSON.parse(cached)
    } catch (e) {
      logger.warn('[ApiDetail] Failed to restore cached response:', e)
    }
  }

  if (currentIsNew) {
    apiData.value = {
      name: t('api.newApi'),
      method: "GET",
      path: "",
      headers: [],
      params: [],
      body: { type: "none", content: "" },
      cookies: [],
      auth: { type: "none" },
      pre_script: "",
      post_script: "",
      description_md: "",
      tags: [],
      settings: { follow_redirects: true, verify_ssl: true, timeout: 30 },
    }
    const draftName = sessionStorage.getItem("new_api_draft_name")
    if (draftName) {
      apiData.value.name = draftName
      sessionStorage.removeItem("new_api_draft_name")
    }
    // 新建接口时若未选目录且分类列表不为空，默认选中第一个分类
    if (!selectedCategoryId.value && apiStore.categories.length > 0) {
      selectedCategoryId.value = apiStore.categories[0].id
    }
  } else {
    const numericApiId = Number(currentApiId)
    if (!isNaN(numericApiId)) {
      try {
        // 如果有 state 数据（从新建接口跳转），直接使用，跳过网络请求
        const res = stateApiData
          ? { data: stateApiData }
          : await getApi(projectId, numericApiId)
        // 运行时类型守卫：确保 headers/params/body 字段是预期格式
        const d = res.data
        if (d) {
          if (d.headers && !Array.isArray(d.headers)) {
            d.headers = typeof d.headers === 'string' ? JSON.parse(d.headers) : []
            if (!Array.isArray(d.headers)) d.headers = []
          }
          if (d.params && !Array.isArray(d.params)) {
            d.params = typeof d.params === 'string' ? JSON.parse(d.params) : []
            if (!Array.isArray(d.params)) d.params = []
          }
          // 确保每个参数都有 type 字段
          if (Array.isArray(d.params)) {
            const validTypes = ['string', 'number', 'boolean']
            d.params = d.params.map((p) => ({
              enabled: p.enabled !== false,
              key: p.key || '',
              value: p.value || '',
              type: validTypes.includes(p.type as string) ? p.type : 'string',
              description: p.description || '',
              sample: p.sample || '',
            }))
          }
          if (d.body && typeof d.body === 'string') {
            try { d.body = JSON.parse(d.body) } catch { d.body = { type: 'none', content: '' } }
          }
          if (!d.body || d.body === null) {
            d.body = { type: 'none', content: '' }
          }
          if (d.assertions && !Array.isArray(d.assertions)) {
            d.assertions = typeof d.assertions === 'string' ? JSON.parse(d.assertions) : []
            if (!Array.isArray(d.assertions)) d.assertions = []
          }
          if (d.response_examples && !Array.isArray(d.response_examples)) {
            d.response_examples = typeof d.response_examples === 'string' ? JSON.parse(d.response_examples) : []
            if (!Array.isArray(d.response_examples)) d.response_examples = []
          }
          if (d.extract_vars && !Array.isArray(d.extract_vars)) {
            d.extract_vars = typeof d.extract_vars === 'string' ? JSON.parse(d.extract_vars) : []
            if (!Array.isArray(d.extract_vars)) d.extract_vars = []
          }
          // 确保必填字段有默认值
          if (!d.path) d.path = ''
          if (!d.method) d.method = 'GET'
          if (!d.name) d.name = ''
          if (!d.headers) d.headers = []
          if (!d.params) d.params = []
          if (!d.cookies) d.cookies = []
          if (!d.auth) d.auth = { type: 'none' }
          if (!d.pre_script) d.pre_script = ''
          if (!d.post_script) d.post_script = ''
          if (!d.description_md) d.description_md = ''
          if (!d.tags) d.tags = []
          if (!d.settings) d.settings = { follow_redirects: true, verify_ssl: true, timeout: 30 }
        }
        apiData.value = d
        editorStore.openApi(res.data)
        activeParamTab.value = detectDefaultTab(res.data)
        // 加载真实接口时，移除残留的"新接口"标签和目录占位
        if (pendingCategoryId.value) {
          removePendingNewApi(pendingCategoryId.value)
          pendingCategoryId.value = null
        }
        if (tabsStore.tabs.find((t) => t.key === "api-new")) {
          tabsStore.removeTab("api-new")
        }
        if (!tabsStore.tabs.find((t) => t.key === `api-${numericApiId}`)) {
          tabsStore.addTab({
            key: `api-${numericApiId}`,
            label: res.data.name || t('apiDetail.apiHash', { id: numericApiId }),
            type: "api",
            method: res.data.method,
            apiId: numericApiId,
            closable: true,
            projectId,
          })
        }
        void loadCases()
      } catch (e: unknown) {
        const err = e as { response?: { status?: number } }
        const status = err?.response?.status
        if (status === 400 || status === 404) {
          // 接口不存在或参数无效，静默跳转到列表页
          const staleKey = `api-${apiIdParam.value}`
          if (tabsStore.tabs.find((t) => t.key === staleKey)) {
            tabsStore.removeTab(staleKey)
          }
          void router.replace(`/projects/${projectId}/apis`)
          return
        }
        if (!isSilentAuthError(e)) logger.error("Failed to load API detail:", e)
      }
    }
  }

  pageLoading.value = false
  // 清理 history state，防止后续导航重复使用
  if (skipLoading) history.replaceState({}, '')
  // 加载完成，后续的 apiData 变更才是用户编辑
    void nextTick(() => {
    isLoadingApi.value = false
    tabsStore.markClean(`api-${apiIdParam.value}`)
  })
}



// 离开新接口页面时清理占位符（防止残留）
watch(
  () => route.path,
  (newPath) => {
    if (!newPath.includes('/apis/detail/new') && pendingCategoryId.value) {
      removePendingNewApi(pendingCategoryId.value)
      pendingCategoryId.value = null
      if (tabsStore.tabs.find((t) => t.key === "api-new")) {
        tabsStore.removeTab("api-new")
      }
    }
  }
)

// 路由参数变化时重新加载数据（同一组件复用时 onMounted 不会重新触发）
// 同时展开接口目录确保侧边树能看到接口
watch(
  () => route.params.apiId,
  async () => {
    await loadApiData()
    await loadSnapshots()
    // 加载完成后展开所属接口目录
    if (!isNewApi.value && apiData.value?.category_id) {
      const catId = apiData.value.category_id
      if (!apiStore.expandedCategories.includes(catId)) {
        apiStore.toggleCategory(catId)
      }
      if (!apiStore.apisByCategory[catId]) {
        apiStore.fetchApis(projectId, catId).catch((e) => logger.warn('[ApiDetail] Failed to fetch apis for category:', e))
      }
    }
  }
)

async function loadSnapshots() {
  const apiId = Number(route.params.apiId)
  if (!apiId) {
    snapshots.value = []
    return
  }
  loadingSnapshots.value = true
  try {
    const res = await listSnapshots('api', apiId, { page_size: 50, project_id: Number(projectId) })
    snapshots.value = res.data.items
  } catch {
    snapshots.value = []
  } finally {
    loadingSnapshots.value = false
  }
}

function changeTypeLabel(type: string): string {
  const map: Record<string, string> = { create: t('apiDetail.changeTypeCreate'), update: t('apiDetail.changeTypeUpdate'), delete: t('apiDetail.changeTypeDelete') }
  return map[type] || type
}

async function onSelectSnapshot(snap: Snapshot) {
  if (selectedSnapshotId.value === snap.id) {
    selectedSnapshotId.value = null
    snapshotDiff.value = null
    return
  }
  selectedSnapshotId.value = snap.id
  snapshotDiff.value = null
  // 与最新快照（列表第一条）对比
  if (snapshots.value.length > 0 && snapshots.value[0].id !== snap.id) {
    try {
      const res = await diffSnapshots(snap.id, snapshots.value[0].id, Number(projectId), Number(route.params.apiId))
      snapshotDiff.value = res.data
    } catch {
      snapshotDiff.value = null
    }
  }
}

async function onRestoreSnapshot() {
  if (!selectedSnapshotId.value) return
  try {
    await ElMessageBox.confirm(
      t('apiDetail.rollbackConfirm', { id: selectedSnapshotId.value }),
      t('apiDetail.rollbackTitle'),
      { type: 'warning', confirmButtonText: t('apiDetail.rollback'), cancelButtonText: t('common.cancel') }
    )
  } catch { return }
  try {
    await restoreSnapshot(selectedSnapshotId.value, Number(projectId))
    msgSuccess(t('apiDetail.rollbackSuccess'))
    selectedSnapshotId.value = null
    snapshotDiff.value = null
    // 重新加载接口数据
    await loadApiData()
    await loadSnapshots()
  } catch {
    msgError(t('apiDetail.rollbackFailed'))
  }
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "--"
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

const isResizing = ref(false)
const resizeCleanups: (() => void)[] = []

function startResize(_e: MouseEvent) {
  if (isResizing.value) return
  isResizing.value = true
  resizeHandleRef.value?.classList.add("resizing")
  detailBodyRef.value?.classList.add("is-resizing")
  document.addEventListener("mousemove", onResize)
  document.addEventListener("mouseup", stopResize)
  resizeCleanups.push(() => document.removeEventListener("mousemove", onResize))
  resizeCleanups.push(() => document.removeEventListener("mouseup", stopResize))
}

function onResize(e: MouseEvent) {
  if (!isResizing.value) return
  const container = detailBodyRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const pct = ((e.clientY - rect.top) / rect.height) * 100
  topHeight.value = Math.max(25, Math.min(75, pct))
}

function stopResize() {
  isResizing.value = false
  resizeHandleRef.value?.classList.remove("resizing")
  detailBodyRef.value?.classList.remove("is-resizing")
  document.removeEventListener("mousemove", onResize)
  document.removeEventListener("mouseup", stopResize)
  localStorage.setItem("api-detail-split-v", String(topHeight.value))
}

async function applyExtractRules(respData: ApiTestResult) {
  try {
    const bodyRaw = respData?.response_body
    const bodyStr: string = typeof bodyRaw === 'string' ? bodyRaw : ""
    let bodyObj: unknown = null
    if (typeof bodyStr === "string") {
      try {
        bodyObj = JSON.parse(bodyStr)
      } catch {
        bodyObj = null
      }
    }
    const headers = respData?.response_headers || {}
    let updated = false
    // 获取当前环境已有的变量名集合（只更新已有变量，不新增已删除的）
    const rules = apiData.value.extract_vars || []
    for (const rule of rules) {
      if (!rule.variable || !rule.expression) continue
      let val: unknown = null
      if (rule.source === "header") {
        val = headers[rule.expression]
      } else if (rule.type === "regex") {
        try {
          const m = String(bodyStr).match(new RegExp(rule.expression))
          if (m) val = m[1] ?? m[0]
        } catch (e) {
          logger.warn('[ApiDetail] Invalid regex in extract rule:', e)
        }
      } else {
        // JSONPath extraction - skip if bodyObj is null (non-JSON response)
        if (bodyObj === null) continue
        val = jsonpathGet(bodyObj, rule.expression)
      }
      if (val !== null && val !== undefined) {
        const strVal = typeof val === "string" ? val : JSON.stringify(val)
        await envStore.addVariable(projectId, rule.variable, strVal)
        updated = true
        msgSuccess(
          t('apiDetail.variableExtracted', { var: `{{${rule.variable}}}`, value: strVal.length > 50 ? strVal.slice(0, 50) + "..." : strVal })
        )
      }
    }
    if (updated) await envStore.fetchGlobalConfig(projectId)
  } catch (e) {
    logger.warn('[ApiDetail] Failed to apply extract rules:', e)
  }
}

/** 用户从响应中手动提取变量时，自动创建提取规则，后续请求自动更新 */
function onAddExtractRule(rule: { variable: string; source: string; type: string; expression: string }) {
  const rules = apiData.value.extract_vars || []
  // 如果已有同名变量的规则，更新表达式；否则新增
  const idx = rules.findIndex((r) => r.variable === rule.variable)
  if (idx >= 0) {
    rules[idx] = { ...rules[idx], ...rule, scope: rules[idx].scope || 'env' }
  } else {
    rules.push({ ...rule, scope: 'env' })
  }
  apiData.value.extract_vars = [...rules]
}

function jsonpathGet(obj: unknown, path: string): unknown {
  if (!path) return null
  const searchPath = path.replace(/^\$\.?/, "")
  const parts = searchPath.split(/\.|\[/).map((s) => s.replace(/\]$/, ""))
  let cur = obj as Record<string, unknown>
  for (const p of parts) {
    if (!p) continue
    if (cur == null) return null
    if (Array.isArray(cur) && /^\d+$/.test(p)) {
      cur = cur[Number(p)]
    } else if (typeof cur === "object" && p in cur) {
      cur = cur[p]
    } else {
      return null
    }
  }
  return cur
}

// 发送前预解析 {{变量}} 为实际值（使用前端本地合并的变量字典）
function resolveTemplateVars(text: string | null | undefined): string {
  if (text == null) return ""
  const str = String(text)
  if (!str || !str.includes("{{")) return str
  return str.replace(/\{\{\s*(\w+(?:\.\w+)*)\s*\}\}/g, (match: string, key: string) => {
    const found = envStore.mergedVariables.find(
      (v: { key: string; value: string }) => v.key === key
    )
    return found ? found.value : match
  })
}

async function onSend() {
  // 发送前主动校验认证状态（解决已登录但 memoryToken 丢失导致 401 的问题）
  if (!(await requireLogin(t('apiDetail.sendTest')))) return

  // 发送前验证必填字段
  if (!validateApiFields()) {
    msgError(t('apiDetail.checkPathFormat'))
    return
  }
  if (isNewApi.value) {
    // 新接口：先保存再发送
    const targetCatId = selectedCategoryId.value || apiData.value?.category_id || null
    if (targetCatId) {
      await saveAndSend(targetCatId)
    } else if (apiStore.categories.length > 0) {
      // 有目录但没选：自动选第一个目录而不是弹窗
      const firstCat = apiStore.categories[0]
      if (firstCat?.id) {
        await saveAndSend(firstCat.id)
      } else {
        pendingSendAfterSave.value = true
        showCategoryDialog.value = true
      }
    } else {
      await saveAndSend(null)
    }
    return
  }
  sending.value = true
  try {
    // 预解析 {{变量}} 为实际值，确保变量即时生效（无需失焦）
    const resolvedHeaders = (apiData.value.headers || [])
      .filter((h: { enabled?: boolean; key?: string; value?: string }) => h.enabled && h.key?.trim() && h.value?.trim())
      .map((h: { enabled?: boolean; key?: string; value?: string }) => ({
        ...h,
        key: resolveTemplateVars(h.key || ""),
        value: resolveTemplateVars(h.value || ""),
      }))
    const resolvedParams = (apiData.value.params || []).map((p: { enabled?: boolean; key?: string; value?: string }) => ({
      ...p,
      key: p.enabled ? resolveTemplateVars(p.key) : p.key,
      value: p.enabled ? resolveTemplateVars(p.value || "") : p.value || "",
    }))
    let resolvedBody = apiData.value.body
      ? {
          ...apiData.value.body,
          content: resolveTemplateVars(apiData.value.body.content || ""),
        }
      : apiData.value.body

    // 根据请求体类型自动设置 Content-Type（POST/PUT/PATCH 请求）
    const method = String(typeof apiData.value.method === 'string' ? apiData.value.method : '').toUpperCase()
    if (['POST', 'PUT', 'PATCH'].includes(method) && resolvedBody) {
      const bodyType = resolvedBody.type
      // 检查是否已有 Content-Type header
      const hasContentType = resolvedHeaders.some(
        (h: { key?: string; enabled?: boolean }) =>
          h.enabled && h.key?.toLowerCase() === 'content-type'
      )
      if (!hasContentType) {
        let contentType = ''
        if (bodyType === 'json') {
          contentType = 'application/json'
          // JSON 对象转字符串
          if (typeof resolvedBody.content === 'object' && resolvedBody.content !== null) {
            try {
              resolvedBody = { ...resolvedBody, content: JSON.stringify(resolvedBody.content, null, 2) }
            } catch {
              // 序列化失败保持原样
            }
          }
        } else if (bodyType === 'form-data' || bodyType === 'multipart') {
          // 不设置 Content-Type，让浏览器自动生成 boundary
        } else if (bodyType === 'x-www-form-urlencoded' || bodyType === 'form') {
          contentType = 'application/x-www-form-urlencoded'
        } else if (bodyType === 'text' || bodyType === 'plain') {
          contentType = 'text/plain'
        } else if (bodyType === 'xml') {
          contentType = 'application/xml'
        }
        if (contentType) {
          resolvedHeaders.push({ key: 'Content-Type', value: contentType, enabled: true })
        }
      }
    }

    // 执行前置操作（可修改请求参数）
    if (apiData.value.pre_script?.trim()) {
      const preResult = await runPreScript(
        apiData.value.pre_script,
        {
          method: apiData.value.method,
          path: apiData.value.path,
          headers: resolvedHeaders,
          params: resolvedParams,
          body: resolvedBody,
          auth: apiData.value.auth,
        },
        (key: string) => {
          const found = envStore.mergedVariables.find((v: { key: string }) => v.key === key)
          return found?.value
        },
        (key: string, value: string) => {
          void envStore.addVariable(projectId, key, value)
        }
      )
      if (preResult) {
        apiData.value.method = preResult.method
        apiData.value.path = preResult.path
        resolvedHeaders.splice(0, resolvedHeaders.length, ...preResult.headers)
        resolvedParams.splice(0, resolvedParams.length, ...preResult.params)
        resolvedBody = preResult.body
      }
    }

    const res = await testApi(projectId, Number(apiIdParam.value), {
      env_id: envStore.currentEnvId || 0,
      overrides: {
        base_url: envStore.currentServiceUrl || undefined,
        method: apiData.value.method,
        path: apiData.value.path,
        headers: resolvedHeaders,
        params: resolvedParams,
        body: resolvedBody,
        auth: apiData.value.auth,
        pre_script: apiData.value.pre_script,
        post_script: apiData.value.post_script,
        settings: apiData.value.settings,
      },
    })
    responseData.value = res.data
    try {
      sessionStorage.setItem(`resp_${projectId}_${apiIdParam.value}`, JSON.stringify(res.data))
    } catch (e) {
      logger.warn('[ApiDetail] Failed to cache response:', e)
    }
    // 执行后置操作（可提取变量、做断言等）
    if (apiData.value.post_script?.trim()) {
      void runPostScript(
        apiData.value.post_script,
        res.data,
        (key: string) => {
          const found = envStore.mergedVariables.find((v: { key: string }) => v.key === key)
          return found?.value
        },
        (key: string, value: string) => {
          void envStore.addVariable(projectId, key, value)
        }
      )
    }
    // 自动提取变量：根据已保存的提取规则从响应中提取并更新
    if (apiData.value.extract_vars && apiData.value.extract_vars.length > 0) {
      await applyExtractRules(res.data)
    }
    // 域名不可达 → 重定向到项目设置页（仅在真正的连接失败时，如 DNS 解析失败、连接拒绝）
    if (res.data?.response_status === 0 && res.data?.error) {
      const errMsg = String(res.data.error).toLowerCase()
      const isConnectionFailure = errMsg.includes('connecterror') || errMsg.includes('connect_error')
        || errMsg.includes('connectionrefused') || errMsg.includes('connection refused')
        || errMsg.includes('nameresolution') || errMsg.includes('name_resolution')
        || errMsg.includes('nodename') || errMsg.includes('nodename_not_known')
        || errMsg.includes('getaddrinfo') || errMsg.includes('dns')
        || errMsg.includes('cannot connect') || errMsg.includes('目标主机拒绝')
      if (isConnectionFailure) {
        msgError(t('apiDetail.connectionFailed'))
        redirectTimer.value = setTimeout(() => void router.push(`/projects/${projectId}/settings`), 1500)
      } else {
        msgError(t('apiDetail.requestFailed', { error: res.data.error }))
      }
    }
  } catch (e: unknown) {
    // 区分不同类型的错误
    const err = e as { code?: string; message?: string; response?: { status?: number; data?: { detail?: string } } }
    let errorMessage = t('apiDetail.requestFailedShort')
    let errorStatus = 500

    if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
      // 请求超时
      errorMessage = t('apiDetail.requestTimeout')
      errorStatus = 408
    } else if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error')) {
      // 网络错误
      errorMessage = t('apiDetail.networkError')
      errorStatus = 0
    } else if (err?.response?.status) {
      // 服务器返回错误状态码
      errorStatus = err.response.status
      const detail = err.response.data?.detail
      if (errorStatus >= 500) {
        errorMessage = t('apiDetail.serverError', { status: errorStatus, detail: detail ? ': ' + detail : '' })
      } else if (errorStatus === 404) {
        errorMessage = t('apiDetail.apiNotFound')
      } else if (errorStatus === 401 || errorStatus === 403) {
        errorMessage = t('apiDetail.authFailed')
      } else if (errorStatus === 400) {
        errorMessage = detail || t('apiDetail.paramError')
      } else {
        errorMessage = detail || t('apiDetail.requestFailedStatus', { status: errorStatus })
      }
    } else if (err?.message) {
      errorMessage = err.message
    }

    responseData.value = {
      request_url: '',
      request_method: '',
      request_headers: {},
      request_body: '',
      response_status: errorStatus,
      response_headers: {},
      response_body: JSON.stringify({ error: errorMessage }),
      duration: 0,
    }
    try {
      sessionStorage.setItem(`resp_${projectId}_${apiIdParam.value}`, JSON.stringify(responseData.value))
    } catch (se) {
      logger.warn('[ApiDetail] Failed to cache error response:', se)
    }
  } finally {
    sending.value = false
  }
}

/** 保存新接口并自动发送测试请求 */
async function saveAndSend(categoryId: number | null) {
  sending.value = true
  try {
    const res = await createApi(projectId, {
      ...apiData.value,
      category_id: categoryId,
    })
    if (res.data?.id) {
      const newId = res.data.id
      // 发送测试请求
      const testRes = await testApi(projectId, newId, {
        env_id: envStore.currentEnvId || 0,
        overrides: {
          base_url: envStore.currentServiceUrl || undefined,
        },
      })
      responseData.value = testRes.data
      try {
        sessionStorage.setItem(`resp_${projectId}_${newId}`, JSON.stringify(testRes.data))
      } catch (e) {
        logger.warn('[ApiDetail] Failed to cache response in saveAndSend:', e)
      }
      if (testRes.data?.response_status === 0 && testRes.data?.error) {
        msgError(t('apiDetail.connectionFailed'))
      }
      // 导航到接口详情页
      msgSuccess(t('apiDetail.apiCreated'))
      // 清理 pending 占位符
      const pendingCatId = pendingCategoryId.value
      if (pendingCatId) {
        removePendingNewApi(pendingCatId)
        pendingCategoryId.value = null
      }
      // 增量更新：将新接口加入目录列表（不刷新树）
      if (categoryId) {
        apiStore.addApiToCategory(categoryId, {
          id: newId,
          name: res.data.name || t('api.newApi'),
          method: res.data.method || "GET",
          path: res.data.path || "/",
          category_id: categoryId,
          description: "",
          headers: [],
          params: [],
          body: { type: "none", content: "" },
          auth_type: "none",
          case_count: 0,
        })
      }
      tabsStore.removeTab("api-new")
      tabsStore.addTab({
        key: `api-${newId}`,
        label: res.data.name || t('api.newApi'),
        type: "api",
        method: res.data.method || "GET",
        apiId: newId,
        closable: true,
        projectId,
      })
      void router.replace({
        path: `/projects/${projectId}/apis/detail/${newId}`,
        state: { skipLoading: true, apiData: res.data },
      })
    }
  } catch (e) {
    logger.warn('[ApiDetail] Failed to save and send:', e)
    // 保存失败时降级：如果已有有效 apiId，直接发送测试请求
    const currentApiId = Number(apiIdParam.value)
    if (!isNaN(currentApiId) && currentApiId > 0 && apiIdParam.value !== 'new') {
      logger.info('[ApiDetail] Fallback to direct send request for API:', currentApiId)
      try {
        const resolvedHeaders = (apiData.value.headers || [])
          .filter((h: { enabled?: boolean; key?: string; value?: string }) => h.enabled && h.key?.trim() && h.value?.trim())
          .map((h: { enabled?: boolean; key?: string; value?: string }) => ({
            ...h,
            key: resolveTemplateVars(h.key || ""),
            value: resolveTemplateVars(h.value || ""),
          }))
        const resolvedParams = (apiData.value.params || []).map((p: { enabled?: boolean; key?: string; value?: string }) => ({
          ...p,
          key: p.enabled ? resolveTemplateVars(p.key) : p.key,
          value: p.enabled ? resolveTemplateVars(p.value || "") : p.value || "",
        }))
        let resolvedBody = apiData.value.body
          ? { ...apiData.value.body, content: resolveTemplateVars(apiData.value.body.content || "") }
          : apiData.value.body

        const testRes = await testApi(projectId, currentApiId, {
          env_id: envStore.currentEnvId || 0,
          overrides: {
            base_url: envStore.currentServiceUrl || undefined,
            method: apiData.value.method,
            path: apiData.value.path,
            headers: resolvedHeaders,
            params: resolvedParams,
            body: resolvedBody,
            auth: apiData.value.auth,
            pre_script: apiData.value.pre_script,
            post_script: apiData.value.post_script,
            settings: apiData.value.settings,
          },
        })
        responseData.value = testRes.data
        try {
          sessionStorage.setItem(`resp_${projectId}_${currentApiId}`, JSON.stringify(testRes.data))
        } catch (cacheErr) {
          logger.warn('[ApiDetail] Failed to cache fallback response:', cacheErr)
        }
        if (testRes.data?.response_status === 0 && testRes.data?.error) {
          msgError(t('apiDetail.connectionFailed'))
        }
        return // 降级成功，不显示错误消息
      } catch (fallbackErr) {
        logger.error('[ApiDetail] Fallback send also failed:', fallbackErr)
      }
    }
    msgError(t('apiDetail.saveAndSendFailed'))
  } finally {
    sending.value = false
    pendingSendAfterSave.value = false
  }
}

const saving = ref(false)
const showSaveIndicator = ref(false)
const fieldErrors = ref<Record<string, string>>({})

/** 验证接口必填字段和路径格式 */
function validateApiFields(): boolean {
  const errors: Record<string, string> = {}
  const api = apiData.value

  // 必填字段验证
  if (!api.method?.trim()) {
    errors.method = t('apiDetail.selectMethod')
  }
  if (!api.path?.trim()) {
    errors.path = t('common.pathRequired')
  } else {
    // 路径格式验证
    const path = api.path.trim()
    if (!path.startsWith('/')) {
      errors.path = t('apiDetail.pathMustStartWithSlash')
    } else {
      // 检测非法字符
      const illegalChars = /[\s?#&<>\\|^`"'$;,!()*]/
      if (illegalChars.test(path)) {
        const match = path.match(illegalChars)
        const char = match ? match[0] : ''
        const charDesc = char === ' ' ? t('apiDetail.space') : char
        errors.path = t('apiDetail.pathIllegalChar', { char: charDesc })
      } else {
        // 检查合法字符范围
        const validChars = /^\/[a-zA-Z0-9\-_/{}[\].@%~+=:]*$/
        if (!validChars.test(path)) {
          errors.path = t('apiDetail.pathUnsupportedChar')
        }
      }
    }
  }

  fieldErrors.value = errors
  return Object.keys(errors).length === 0
}

async function onSave() {
  if (saving.value) return
  if (!validateApiFields()) {
    // 切换到有错误的字段所在标签页
    if (fieldErrors.value.path) {
      // 路径错误在请求行，无需切换标签
    }
    msgError(t('apiDetail.checkInputFields'))
    return
  }
  saving.value = true
  if (isNewApi.value) {
    let targetCatId = selectedCategoryId.value || apiData.value?.category_id || null
    if (!targetCatId && apiStore.categories.length > 0) {
      targetCatId = apiStore.categories[0].id
      selectedCategoryId.value = targetCatId
    }
    await doCreateApi(targetCatId)
    return
  }
  try {
    const res = await updateApi(
      projectId,
      Number(apiIdParam.value),
      apiData.value
    )
    editorStore.markSaved()
    tabsStore.markClean(`api-${apiIdParam.value}`)
    // 更新标签页名称和请求方法
    tabsStore.updateTabKey(`api-${apiIdParam.value}`, `api-${apiIdParam.value}`, {
      label: res.data?.name || apiData.value.name,
      method: apiData.value.method,
    })
    // 刷新侧边栏树，确保目录结构同步
    apiStore.invalidateCategoryCache()
    void apiStore.fetchCategories(projectId)
    msgSuccess(MSG.SAVE_SUCCESS)
    // 显示短暂的保存成功指示器
    showSaveIndicator.value = true
    setTimeout(() => { showSaveIndicator.value = false }, 2000)
  } catch (e: unknown) {
    logger.error("Failed to save:", e)
    // 从后端错误响应中提取字段级错误
    const err = e as { response?: { data?: { detail?: string; errors?: Record<string, string> } } }
    const detail = err?.response?.data?.detail
    const fieldErrs = err?.response?.data?.errors
    if (fieldErrs && typeof fieldErrs === 'object') {
      fieldErrors.value = fieldErrs
      const firstErr = Object.values(fieldErrs)[0]
      msgError(firstErr || t('apiDetail.saveFailed'))
    } else if (detail) {
      msgError(detail)
    } else {
      msgError(t('apiDetail.saveFailed'))
    }
  } finally {
    saving.value = false
  }
}

function onEscape() {
  if (isNewApi.value) {
    void router.replace(`/projects/${projectId}/apis`)
  }
}

function onCategorySelect(category: { id?: number } | null) {
  selectedCategoryId.value = category?.id || null
}

function handleCategoryConfirm(categoryId: number) {
  if (pendingSendAfterSave.value) {
    showCategoryDialog.value = false
    void saveAndSend(categoryId)
  } else {
    void doCreateApi(categoryId)
  }
}

async function doCreateApi(categoryId: number | null) {
  const draftName = sessionStorage.getItem("new_api_draft_name")
  if (draftName) {
    apiData.value.name = draftName
    sessionStorage.removeItem("new_api_draft_name")
  }
  showCategoryDialog.value = false
  try {
    const res = await createApi(projectId, {
      ...apiData.value,
      category_id: categoryId,
    })
    if (res.data?.id) {
      msgSuccess(t('apiDetail.apiCreated'))
      // 清理 pending 占位符
      const pendingCatId = pendingCategoryId.value
      if (pendingCatId) {
        removePendingNewApi(pendingCatId)
        pendingCategoryId.value = null
      }
      // 增量更新：将新接口加入目录列表（不刷新树）
      if (categoryId) {
        apiStore.addApiToCategory(categoryId, {
          id: res.data.id,
          name: res.data.name || t('api.newApi'),
          method: res.data.method || "GET",
          path: res.data.path || "/",
          category_id: categoryId,
          description: "",
          headers: [],
          params: [],
          body: { type: "none", content: "" },
          auth_type: "none",
          case_count: 0,
        })
      }
      tabsStore.removeTab("api-new")
      tabsStore.addTab({
        key: `api-${res.data.id}`,
        label: res.data.name || t('api.newApi'),
        type: "api",
        method: res.data.method || "GET",
        apiId: res.data.id,
        closable: true,
        projectId,
      })
      void router.replace({
        path: `/projects/${projectId}/apis/detail/${res.data.id}`,
        state: { skipLoading: true, apiData: res.data },
      })
    }
  } catch (e) {
    logger.warn('[ApiDetail] Failed to create API:', e)
    msgError(t('apiDetail.createApiFailed'))
  }
}

function handleCaseSaved(created: { id?: number; name?: string }) {
  if (!created?.id) return
  // 直接更新 store，确保箭头立即出现
  if (apiData.value?.id && apiData.value?.category_id) {
    const catId = apiData.value.category_id
    const apis = apiStore.apisByCategory[catId]
    if (apis) {
      const target = apis.find((a) => a.id === apiData.value.id)
      if (target) target.case_count = (target.case_count || 0) + 1
    }
    // 将新建用例加入侧边树 store
    if (!apiStore.casesByApi[apiData.value.id]) {
      apiStore.casesByApi[apiData.value.id] = []
    }
    apiStore.casesByApi[apiData.value.id].push(created)
  }
  // 失效相关缓存，后台刷新数据
  apiStore.invalidateCategoryCache()
  void apiStore.fetchCategories(projectId)
  if (apiData.value?.id) {
    apiStore.invalidateApiCache(apiData.value.id)
  }
  // 打开用例标签页
  tabsStore.addTab({
    key: `case-${created.id}`,
    label: created.name || t('apiDetail.newCase'),
    type: "case",
    caseId: created.id,
    closable: true,
    projectId,
  })
  void router.push(`/projects/${projectId}/apis/case/${created.id}`)
}

async function loadCases() {
  if (!apiData.value?.id) return
  casesLoading.value = true
  try {
    // eslint-disable-next-line @typescript-eslint/no-base-to-string
    const res = await listApiCases(projectId, apiData.value.id, { page_size: 9999 })
    apiCases.value = res.data.items || []
    // 同步更新侧边树 store，使树节点感知到有用例，展开箭头出现
    apiStore.casesByApi[apiData.value.id] = apiCases.value
    apiStore.casesCachedAt[`${projectId}_${apiData.value.id}`] = Date.now()
  } catch {
    apiCases.value = []
  } finally {
    casesLoading.value = false
  }
}

function selectCase(caseId: number) {
  selectedCaseId.value = caseId
}

function createCase() {
  showSaveCaseDialog.value = true
}

async function runCase(caseId: number) {
  if (!(await requireLogin(t('apiDetail.runTestCase')))) return
  try {
    const env = envStore.currentEnvId || 1
    await runCaseApi(projectId, caseId, env)
    msgSuccess(t('apiDetail.execCompleted'))
    void loadCases()
  } catch (e) {
    logger.warn('[ApiDetail] Failed to run case:', e)
    msgError(t('apiDetail.runCaseFailed'))
  }
}

async function copyCase(caseId: number) {
  try {
    const res = await getCase(projectId, caseId)
    const c = res.data || {}
    await createApiCase(projectId, apiData.value.id!, {
      name: (c.name || t('apiDetail.unnamedCase')) + t('apiDetail.copySuffix'),
      priority: c.priority ?? "P1",
      description: c.description || "",
      status: c.status || "active",
      case_type: c.case_type || "other",
      tags: c.tags || [],
      request_body: c.request_body,
      assertions: c.assertions || [],
      extract_vars: c.extract_vars || [],
    })
    msgSuccess(t('apiDetail.caseCopied'))
    void loadCases()
  } catch {
    msgError(t('apiDetail.copyFailed'))
  }
}

async function deleteCase(caseId: number) {
  try {
    await ElMessageBox.confirm(t('common.confirmDeleteCase'), t('apiDetail.deleteCase'), {
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    })
    await deleteCaseApi(projectId, caseId)
    msgSuccess(t('common.deleteSuccess'))
    if (selectedCaseId.value === caseId) selectedCaseId.value = null
    void loadCases()
  } catch {
    // User cancelled or deletion failed
  }
}

async function handleBatchDeleteCases(ids: number[]) {
  try {
    await Promise.all(ids.map((id: number) => deleteCaseApi(projectId, id)))
    msgSuccess(t('apiDetail.casesDeleted', { count: ids.length }))
    if (selectedCaseId.value && ids.includes(selectedCaseId.value)) {
      selectedCaseId.value = null
    }
    void loadCases()
  } catch {
    msgError(t('apiDetail.batchDeleteFailed'))
  }
}

async function onCloneApi() {
  if (!apiData.value?.id) return
  try {
    // eslint-disable-next-line @typescript-eslint/no-base-to-string
    const res = await duplicateApi(projectId, apiData.value.id)
    msgSuccess(t('apiDetail.apiCloned'))
    apiStore.clearCache()
    await apiStore.fetchCategories(projectId)
    if (res.data?.id) {
      tabsStore.addTab({
        key: `api-${res.data.id}`,
        label: res.data.name || t('apiDetail.apiCopy'),
        type: "api",
        method: res.data.method || "GET",
        apiId: res.data.id,
        closable: true,
      })
      void router.push(`/projects/${projectId}/apis/detail/${res.data.id}`)
    }
  } catch {
    msgError(t('apiDetail.cloneFailed'))
  }
}

async function onCurlImport() {
  if (!curlCommand.value.trim()) {
    msgError(t('apiDetail.inputCurlCommand'))
    return
  }
  curlImporting.value = true
  try {
    const categoryId = selectedCategoryId.value || apiData.value?.category_id || null
    const res = await importCurl(projectId, {
      curl_command: curlCommand.value,
      category_id: categoryId,
    })
    if (res.data?.id) {
      msgSuccess(t('apiDetail.curlImportSuccess'))
      showCurlImportDialog.value = false
      curlCommand.value = ""
      // 增量更新侧边栏
      if (categoryId) {
        apiStore.addApiToCategory(categoryId, {
          id: res.data.id,
          name: res.data.name || t('api.newApi'),
          method: res.data.method || "GET",
          path: res.data.path || "/",
          category_id: categoryId,
          description: "",
          headers: [],
          params: [],
          body: { type: "none", content: "" },
          auth_type: "none",
          case_count: 0,
        })
      }
      // 导航到新接口
      void router.push({
        path: `/projects/${projectId}/apis/detail/${res.data.id}`,
        state: { skipLoading: true, apiData: res.data },
      })
    }
  } catch (e) {
    const err = e as { response?: { data?: { detail?: string } } }
    msgError(err?.response?.data?.detail || t('apiDetail.curlImportFailed'))
  } finally {
    curlImporting.value = false
  }
}


// 用户编辑接口数据时标记脏状态
function onApiEdit() {
  if (isLoadingApi.value || isNewApi.value) return
  tabsStore.markDirty(`api-${apiIdParam.value}`)
}

onMounted(async () => {
  document.addEventListener('keydown', handleGlobalKeydown)
  // 恢复拖拽分割比例（上限 45%，确保响应区可见）
  const savedSplit = localStorage.getItem("api-detail-split-v")
  if (savedSplit) {
    const rawParsed = parseFloat(savedSplit)
    topHeight.value = isNaN(rawParsed) ? 40 : Math.min(45, Math.max(15, rawParsed))
  }
  // 并行发起所有独立请求，减少串行等待
  const apiPromise = loadApiData()
  const envPromise = envStore
    .fetchEnvs(projectId)
    .catch((e) => { if (!isSilentAuthError(e)) logger.error("Failed to load environments:", e) })
  const globalConfigPromise = envStore
    .fetchGlobalConfig(projectId)
    .catch((e) => { if (!isSilentAuthError(e)) logger.error("Failed to load global config:", e) })
  // 接口目录数据由 SidebarTree 负责加载，此处仅在无缓存时补充
  const catPromise =
    apiStore.categories.length === 0
      ? apiStore
          .fetchCategories(projectId)
          .catch((e) => { if (!isSilentAuthError(e)) logger.error("Failed to load categories:", e) })
      : Promise.resolve()
  await apiPromise
  await Promise.all([envPromise, globalConfigPromise, catPromise, loadSnapshots()])
  // 加载项目标签
  void loadProjectTags()
  // 自动展开当前接口所属接口目录，确保左侧树能看到接口位置
  if (!isNewApi.value && apiData.value?.category_id) {
    const catId = apiData.value.category_id
    if (!apiStore.expandedCategories.includes(catId)) {
      apiStore.toggleCategory(catId)
    }
    if (!apiStore.apisByCategory[catId]) {
      apiStore.fetchApis(projectId, catId).catch((e) => logger.warn('[ApiDetail] Failed to fetch apis for category:', e))
    }
  }
  // 从右键菜单带入预选接口目录
  const stored = sessionStorage.getItem("new_api_category")
  if (stored) {
    selectedCategoryId.value = Number(stored)
    pendingCategoryId.value = stored // 保留给 doCreateApi / saveAndSend 使用
    sessionStorage.removeItem("new_api_category")
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
  resizeCleanups.forEach(fn => fn())
  if (redirectTimer.value) {
    clearTimeout(redirectTimer.value)
    redirectTimer.value = null
  }
})
</script>



<style scoped>
@import './ApiDetail.css';

.breadcrumb-bar {
  padding: var(--space-2) var(--space-4);
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* cURL 导入对话框 */
.curl-import-hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.curl-input :deep(.el-textarea__inner) {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: var(--text-sm);
  line-height: 1.6;
}

/* 保存成功指示器 */
.save-indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-success);
  background: var(--color-success-alpha-08);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  user-select: none;
}
.save-indicator-fade-enter-active {
  transition: all var(--duration-fast) var(--ease-out);
}
.save-indicator-fade-leave-active {
  transition: all var(--duration-slow) var(--ease-in);
}
.save-indicator-fade-enter-from {
  opacity: 0;
  transform: scale(0.8);
}
.save-indicator-fade-leave-to {
  opacity: 0;
}

/* 变量帮助按钮 */
.var-help-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  font-family: inherit;
  flex-shrink: 0;
}
.var-help-btn:hover {
  color: var(--primary-500);
  border-color: var(--primary-300);
  background: var(--color-primary-alpha-06);
}

/* 历史版本 tab */
.history-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
}
.history-tab-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
  max-height: 240px;
  overflow-y: auto;
}
.history-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-smooth);
}
.history-item:hover {
  background: var(--surface-hover);
}
.history-item.active {
  background: var(--surface-selected);
  border-left: 3px solid var(--primary-500);
}
.history-item-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
}
.history-change-type {
  display: inline-block;
  padding: var(--space-0-5) var(--space-1-5);
  border-radius: var(--radius-xs);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.history-change-type.create {
  background: var(--color-success-alpha-08);
  color: var(--color-success);
}
.history-change-type.update {
  background: var(--color-warning-alpha-08);
  color: var(--color-warning);
}
.history-change-type.delete {
  background: var(--color-error-alpha-08);
  color: var(--color-error);
}
.history-msg {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: var(--text-muted);
}
.history-diff-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
}
.history-diff-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}
</style>
