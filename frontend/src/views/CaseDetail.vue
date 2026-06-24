<template>
  <div class="case-detail" @change="onCaseEdit">
    <!-- 面包屑 -->
    <div v-if="!pageLoading" class="breadcrumb-bar">
      <BreadcrumbNav :items="breadcrumbItems" />
    </div>
    <!-- 页面头部 -->
    <div v-if="!pageLoading" class="page-head case-hero">
      <div class="case-hero-content">
        <h1 class="page-title">
          <span class="api-method-badge" :class="String(displayApi.method).toLowerCase()">{{ displayApi.method }}</span>
          <span class="case-name">{{ caseData.name || $t('caseDetail.caseName') }}</span>
          <span v-if="caseData.priority" class="case-priority-badge" :class="'p-' + (caseData.priority || 'P2')">{{ caseData.priority }}</span>
        </h1>
        <div class="case-hero-summary-row">
          <code class="case-hero-path-code">{{ displayApi.path || '/' }}</code>
        </div>
      </div>
    </div>

    <el-alert
      v-if="parentApiError && !pageLoading"
      :title="$t('caseDetail.parentApiDeleted')"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: var(--space-4)"
    >
      <template #default>
        <span>{{ $t('caseDetail.parentApiDeletedDesc') }}</span>
        <el-button size="small" type="warning" style="margin-left: var(--space-3)" @click="router.push(`/projects/${projectId}/apis`)">{{ $t('caseDetail.backToApiList') }}</el-button>
      </template>
    </el-alert>

    <!-- 骨架屏 -->
    <div v-if="pageLoading" class="case-skeleton">
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

    <EmptyState
      v-else-if="loadError"
      illustration="api"
      :title="$t('caseDetail.loadFailed')"
      :description="loadError"
    >
      <template #action>
        <el-button type="primary" size="small" @click="loadCaseData">{{ $t('caseDetail.reload') }}</el-button>
      </template>
    </EmptyState>

    <!-- 分栏主体 -->
    <div v-else class="detail-body" ref="detailBodyRef">
      <div class="request-panel" ref="requestPanelRef" :style="{ flex: '0 0 ' + topHeight + '%' }">
        <!-- 请求行：URL + 操作按钮 -->
        <div class="request-line-row">
          <RequestLine
            :api="displayApi"
            :loading="running"
            :api-saved="!!caseData.id"
            :project-id="projectId"
            :can-edit="canEdit"
            :show-add-to-scene="canEdit && !!caseData.id"
            @send="onRun"
            @save="onSave"
            @save-as-case="onSaveAsCase"
            @add-to-scene="openAddToSceneDialog"
            @update:name="onUpdateName"
          />
        </div>
        <div class="panel-header">
          <ParamTabs
            :api="displayApi"
            :active-tab="activeParamTab"
            @update:active-tab="activeParamTab = $event"
          />
          <button class="var-preview-toggle" :class="{ active: showVarPreview }" @click="showVarPreview = !showVarPreview" :title="$t('caseDetail.varPreviewTitle')">
            <span class="var-icon">{}</span>
            <span>{{ $t('caseDetail.varPreview') }}</span>
          </button>
        </div>
        <div class="panel-body">
          <ParamsTable v-if="activeParamTab === 'params'" v-model="displayApi.params" />
          <BodyEditor v-else-if="activeParamTab === 'body'" v-model="displayApi.body" :method="displayApi.method" />
          <HeadersTable v-else-if="activeParamTab === 'headers'" v-model="displayApi.headers" />
          <ParamsTable v-else-if="activeParamTab === 'cookies'" v-model="displayApi.cookies" />
          <AuthPanel v-else-if="activeParamTab === 'auth'" v-model="displayApi.auth" />
          <ResponseExamplePanel
            v-else-if="activeParamTab === 'response-examples'"
            :examples="displayApi.response_examples"
          />
          <AssertionTab v-else-if="activeParamTab === 'assertions'" v-model="caseData.assertions" />


          <!-- 前置/后置操作脚本 -->
          <div v-else-if="activeParamTab === 'pre-script'" class="script-tab">
            <div class="script-header">
              <div class="script-header-left">
                <span class="script-icon">JS</span>
                <span class="script-label">{{ $t('caseDetail.preScript') }}</span>
              </div>
              <span class="script-desc">{{ $t('caseDetail.preScriptDesc') }}</span>
            </div>
            <div class="script-editor-wrapper">
              <el-input
                v-model="displayApi.pre_script"
                type="textarea"
                :rows="12"
                placeholder="// 请求发送前执行&#10;console.log('pre request', pm.variables);"
                class="script-textarea"
              />
            </div>
          </div>
          <div v-else-if="activeParamTab === 'post-script'" class="script-tab">
            <div class="script-header">
              <div class="script-header-left">
                <span class="script-icon">JS</span>
                <span class="script-label">{{ $t('caseDetail.postScript') }}</span>
              </div>
              <span class="script-desc">{{ $t('caseDetail.postScriptDesc') }}</span>
            </div>
            <div class="script-editor-wrapper">
              <el-input
                v-model="displayApi.post_script"
                type="textarea"
                :rows="12"
                placeholder="// 请求发送后执行&#10;console.log('post request', pm.response);&#10;pm.variables.set('token', pm.response.json().token);"
                class="script-textarea"
              />
            </div>
          </div>

          <!-- 用例标签（当前页面，显示占位） -->
          <div v-else-if="activeParamTab === 'cases'" class="cases-tab-placeholder">
            <EmptyState
              illustration="api"
              :title="$t('caseDetail.currentCasePage')"
              :description="$t('caseDetail.caseListHint')"
            />
          </div>

          <!-- 设置（用例级只读提示） -->
          <div v-else-if="activeParamTab === 'settings'" class="advanced-tab">
            <div class="settings-group">
              <div class="settings-group-title">{{ $t('caseDetail.requestSettings') }}</div>
              <div class="setting-row">
                <div class="setting-info">
                  <span class="setting-label">{{ $t('caseDetail.followRedirects') }}</span>
                  <span class="setting-desc">{{ $t('caseDetail.followRedirectsDesc') }}</span>
                </div>
                <el-switch :model-value="displayApi.settings?.follow_redirects" disabled />
              </div>
              <div class="setting-row">
                <div class="setting-info">
                  <span class="setting-label">{{ $t('caseDetail.sslVerify') }}</span>
                  <span class="setting-desc">{{ $t('caseDetail.sslVerifyDesc') }}</span>
                </div>
                <el-switch :model-value="displayApi.settings?.verify_ssl" disabled />
              </div>
              <div class="setting-row">
                <div class="setting-info">
                  <span class="setting-label">{{ $t('caseDetail.requestTimeout') }}</span>
                  <span class="setting-desc">{{ $t('caseDetail.requestTimeoutDesc') }}</span>
                </div>
                <span class="setting-value">{{ displayApi.settings?.timeout || 30 }}s</span>
              </div>
            </div>
          </div>

          <!-- 提取变量 -->
          <div v-else-if="activeParamTab === 'extract-vars'" class="extract-vars-tab">
            <VariableExtractTab v-model="caseData.extract_vars" />
          </div>

          <!-- 文档预览（用例继承自父 API） -->
          <div v-else-if="activeParamTab === 'docs-preview'" class="advanced-tab">
            <EmptyState
              illustration="docs"
              :title="$t('caseDetail.docsPreview')"
              :description="$t('caseDetail.docsPreviewCaseDesc')"
            />
          </div>

          <!-- 请求历史 -->
          <RequestHistoryPanel
            v-else-if="activeParamTab === 'history' && caseData.api_id"
            :api-id="caseData.api_id"
            @restore="handleHistoryRestore"
          />
        </div>
      </div>

      <!-- 变量预览折叠面板 -->
      <div v-if="showVarPreview" class="var-preview-panel">
        <VariablePreview
          mode="api"
          :title="$t('caseDetail.varPreviewTitle')"
          :request-expressions="[]"
          :all-vars="envStore.allVariablesForPreview"
        />
      </div>

      <!-- 拖拽分隔条 -->
      <div class="resize-handle" ref="resizeHandleRef" @mousedown="startResize" @dblclick="startResize"></div>

      <!-- 响应面板 -->
      <div class="response-panel" :style="{ flex: '0 0 ' + (100 - topHeight) + '%' }">
        <ResponsePanel :response="lastResult" :loading="running" :project-id="projectId" />
      </div>
    </div>

    <!-- 保存为用例对话框（复用 ApiDetail 的 SaveCaseDialog） -->
    <SaveCaseDialog
      v-model="showSaveCaseDialog"
      :project-id="projectId"
      :api-id="caseData.api_id ?? 0"
      :api-name="displayApi.name"
      :request-body="displayApi.body"
      :extract-rules="caseData.extract_vars"
      :request-headers="displayApi.headers"
      :request-params="displayApi.params"
      :assertions="caseData.assertions"
      :pre-script="displayApi.pre_script"
      :post-script="displayApi.post_script"
      @saved="handleCaseSaved"
    />

    <!-- 添加到场景对话框 -->
    <el-dialog
      v-model="showAddToSceneDialog"
      title="添加到场景"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="add-to-scene-form">
        <el-form label-position="top">
          <el-form-item label="选择场景">
            <el-select
              v-model="selectedSceneId"
              filterable
              remote
              reserve-keyword
              placeholder="搜索并选择场景"
              :loading="sceneListLoading"
              :remote-method="loadSceneList"
              style="width: 100%"
              @focus="loadSceneList(sceneSearchKeyword)"
            >
              <el-option
                v-for="scene in sceneList"
                :key="scene.id"
                :label="scene.name"
                :value="scene.id"
              />
              <template #empty>
                <span v-if="sceneListLoading">加载中...</span>
                <span v-else-if="sceneList.length === 0">暂无场景</span>
              </template>
            </el-select>
          </el-form-item>
          <div class="scene-hint">
            <span>将当前用例作为步骤添加到所选场景</span>
          </div>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showAddToSceneDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="addToSceneLoading"
          :disabled="!selectedSceneId"
          @click="handleAddToScene"
        >
          确认添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 请求历史面板 -->
    <RequestHistoryPanel
      v-if="showHistoryPanel && caseData.id"
      :api-id="caseData.api_id"
      @restore="handleHistoryRestore"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, defineAsyncComponent } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useI18n } from "vue-i18n"
import request from "../api/request"
import { useEditorStore } from "../stores/editorStore"
import { useEnvStore } from "../stores/envStore"
import { useTabsStore } from "../stores/tabsStore"
import { MSG } from "../constants/messages"
import { msgSuccess, msgError, msgWarning } from "../utils/message"
import { logger } from "../utils/logger"
import { deepEqual } from "../utils/deepEqual"
import { useRequireLogin } from "../composables/useRequireLogin"
import { useProjectPermission } from "../composables/useProjectPermission"
import { useAutoSave } from "../composables/useAutoSave"
import BreadcrumbNav from "../components/common/BreadcrumbNav.vue"
import type { BreadcrumbItem } from "../components/common/BreadcrumbNav.vue"

import { useProjectStore } from "../stores/projectStore"
import EmptyState from "../components/EmptyState.vue"
import RequestLine from "../components/RequestLine.vue"
import ParamTabs from "../components/ParamTabs.vue"
import ParamsTable from "../components/ParamsTable.vue"
import HeadersTable from "../components/HeadersTable.vue"
import AuthPanel from "../components/AuthPanel.vue"
import ResponseExamplePanel from "../components/ResponseExamplePanel.vue"
import AssertionTab from "../components/AssertionTab.vue"
import SaveCaseDialog from "../components/SaveCaseDialog.vue"
import RequestHistoryPanel from "../components/RequestHistoryPanel.vue"
import VariableExtractTab from "../components/VariableExtractTab.vue"
import type { ApiDefinition } from "../types"
import { listScenes, getScene } from "../api/scenes"
import type { SceneItem } from "../api/scenes"

const BodyEditor = defineAsyncComponent(() => import("../components/BodyEditor.vue"))
const ResponsePanel = defineAsyncComponent(() => import("../components/ResponsePanel.vue"))

const route = useRoute()
const router = useRouter()
const { t: $t } = useI18n()
const projectId = computed(() => Number(route.params.id))
const caseId = computed(() => Number(route.params.caseId))

interface CaseData {
  id?: number
  api_id: number | null
  name: string
  project_id?: number
  assertions: Record<string, unknown>[]
  extract_vars: Record<string, unknown>[]
  request_body: string | null
  status: string
  priority: string
  headers?: string
  params?: string
  body?: string
  created_at?: string
  updated_at?: string
}

const pageLoading = ref(true)
const loadError = ref('')
const parentApiError = ref(false)
const caseData = ref<CaseData>({
  name: $t('caseDetail.unnamedCase'),
  api_id: null,
  assertions: [],
  extract_vars: [],
  request_body: null,
  status: "active",
  priority: "P2",
})
const apiData = ref<ApiDefinition | null>(null)
const lastResult = ref<Record<string, unknown> | null>(null)
const running = ref(false)
const saving = ref(false)
const editorStore = useEditorStore()
const envStore = useEnvStore()
const { requireLogin } = useRequireLogin()
const { canEdit } = useProjectPermission()
const projectStore = useProjectStore()
const tabsStore = useTabsStore()

// 用例编辑时标记脏状态 + 自动保存
const caseTabKey = computed(() => `case-${caseId.value}`)
const isDirty = ref(false)
watch(isDirty, (dirty) => {
  if (dirty) {
    tabsStore.markDirty(caseTabKey.value)
  } else {
    tabsStore.markClean(caseTabKey.value)
  }
})

function onCaseEdit() {
  if (pageLoading.value) return
  isDirty.value = true
}

// 自动保存：用例数据变化后防抖保存
useAutoSave(caseData, {
  delay: 2000,
  enabled: computed(() => isDirty.value && !pageLoading.value && !!caseId.value),
  onSave: async () => {
    if (!caseData.value.name?.trim()) return
    try {
      const payload = {
        ...caseData.value,
        request_body: buildRequestBody(),
      }
      await request.put(`/projects/${projectId.value}/cases/${caseId.value}`, payload)
      editorStore.markSaved()
      tabsStore.markClean(caseTabKey.value)
      isDirty.value = false
    } catch (e) {
      logger.error("自动保存用例失败:", e)
    }
  },
})

// 面包屑
const breadcrumbItems = computed<BreadcrumbItem[]>(() => {
  const projectName = projectStore.projects.find((p) => p.id === projectId.value)?.name || $t('caseDetail.project')
  const apiName = (apiData.value?.name as string) || $t('caseDetail.api')
  return [
    { label: projectName, to: `/dashboard` },
    { label: $t('caseDetail.apiManagement'), to: `/projects/${projectId.value}/apis` },
    { label: apiName, to: caseData.value.api_id ? `/projects/${projectId.value}/apis/detail/${caseData.value.api_id}` : undefined },
    { label: caseData.value.name || $t('caseDetail.caseName') },
  ]
})
const showSaveCaseDialog = ref(false)
const showHistoryPanel = ref(false)
const showAddToSceneDialog = ref(false)
const addToSceneLoading = ref(false)
const sceneList = ref<SceneItem[]>([])
const sceneListLoading = ref(false)
const selectedSceneId = ref<number | null>(null)
const sceneSearchKeyword = ref('')
const activeParamTab = ref<string>("params")
const topHeight = ref(40)
const showVarPreview = ref(false)
const resizeHandleRef = ref<HTMLElement | null>(null)
const detailBodyRef = ref<HTMLElement | null>(null)

/**
 * 检测默认标签页：优先展示有内容的参数
 * 参考 ApiDetail 的 detectDefaultTab 逻辑
 */
function detectDefaultTab(api: ApiDefinition | null, caseData: CaseData | null): string {
  // 用例的断言有内容 → 优先展示断言
  if (caseData?.assertions?.length > 0) return "assertions"
  // 父 API 的 body 有内容 → 展示 body
  if (api?.body && api.body.type !== "none") return "body"
  // 父 API 的 headers 有内容 → 展示 headers
  if (api?.headers?.length > 0) return "headers"
  // 父 API 的 params 有内容 → 展示 params
  if (api?.params?.length > 0) return "params"
  return "params"
}

let isResizing = false

/**
 * displayApi computed 属性将父 API 数据与用例数据合并，
 * 使 ParamTabs 和各子组件（ParamsTable/BodyEditor/HeadersTable 等）
 * 能够以与 ApiDetail 完全相同的方式工作。
 */
const historyOverrides = ref<Record<string, unknown>>({})

const displayApi = computed(() => {
  const api = apiData.value
  const c = caseData.value
  if (!api) {
    // 无父 API 时返回基础结构
    return {
      name: c?.name || $t('caseDetail.unnamedCase'),
      method: "GET",
      path: "/",
      headers: [],
      params: [],
      body: { type: "none", content: "" },
      cookies: [],
      auth: { type: "none" },
      pre_script: "",
      post_script: "",
      assertions: c?.assertions || [],
      settings: { follow_redirects: true, verify_ssl: true, timeout: 30 },
      response_examples: [],
    }
  }

  // 合并父 API 数据 + 用例特定数据
  // request_body 覆盖必须做类型校验，防止 JSON 对象覆盖数组字段导致 el-table 崩溃
  const overrides = c?.request_body
    ? (() => {
        try {
          const parsed = JSON.parse(c.request_body)
          return typeof parsed === 'object' && parsed !== null ? parsed : {}
        } catch {
          return {}
        }
      })()
    : {}

  // 守卫：确保覆盖的字段是预期类型，防止数组被对象替换
  if (overrides.headers && !Array.isArray(overrides.headers)) {
    delete overrides.headers
  }
  if (overrides.params && !Array.isArray(overrides.params)) {
    delete overrides.params
  }
  if (overrides.body && typeof overrides.body === 'object' && overrides.body !== null) {
    const b = overrides.body as Record<string, unknown>
    if (b.form && !Array.isArray(b.form)) {
      delete b.form
    }
    if (b.content && typeof b.content === 'string') {
      try {
        const parsed = JSON.parse(b.content)
        if (Array.isArray(parsed)) {
          b.content = parsed
        }
      } catch { /* keep as string */ }
    }
  }

  const merged = {
    ...api,
    // 用例名称替换 API 名称显示
    name: c?.name || api.name,
    // 断言来自用例
    assertions: c?.assertions || [],
    ...overrides,
    ...historyOverrides.value,
  }

  return merged
})

async function loadCaseData() {
  const currentCaseId = Number(route.params.caseId)
  pageLoading.value = true
  loadError.value = ''
  lastResult.value = null
  activeParamTab.value = "params"
  topHeight.value = 40

  try {
    const res = await request.get(`/projects/${projectId.value}/cases/${currentCaseId}`)
    caseData.value = res.data

    if (!tabsStore.tabs.find((t) => t.key === `case-${currentCaseId}`)) {
      tabsStore.addTab({
        key: `case-${currentCaseId}`,
        label: res.data.name || `用例 #${currentCaseId}`,
        type: "case",
        caseId: currentCaseId,
        closable: true,
        projectId: projectId.value,
      })
    }

    // 加载父 API
    if (res.data.api_id) {
      try {
        const apiRes = await request.get(`/projects/${projectId.value}/apis/${res.data.api_id}`)
        apiData.value = apiRes.data
      } catch (e) {
        logger.error("加载父 API 失败:", e)
        parentApiError.value = true
      }
    }

    // 加载最后一次运行结果
    try {
      const lastRes = await request.get(
        `/projects/${projectId.value}/run/cases/${currentCaseId}/last-run`
      )
      lastResult.value = lastRes.data
    } catch (e) {
      logger.warn('[CaseDetail] No execution history for case:', e)
    }

    // 检测默认标签页：优先展示有内容的参数（与 ApiDetail 行为一致）
    activeParamTab.value = detectDefaultTab(apiData.value, caseData.value)
  } catch (e) {
    logger.error("加载用例失败:", e)
    loadError.value = $t('caseDetail.loadCaseFailed')
    caseData.value = {
      name: $t('caseDetail.unnamedCase'),
      api_id: null,
      assertions: [],
      extract_vars: [],
      request_body: null,
      status: "active",
      priority: "P2",
    }
    apiData.value = null
  }

  pageLoading.value = false
}

onMounted(async () => {
  await envStore.fetchEnvs(projectId.value).catch((e: unknown) => logger.error("加载环境失败:", e))
  await loadCaseData()
})

watch(
  () => route.params.caseId,
  () => {
    void loadCaseData()
  }
)

function startResize(_e: MouseEvent) {
  isResizing = true
  resizeHandleRef.value?.classList.add("resizing")
  document.addEventListener("mousemove", onResize)
  document.addEventListener("mouseup", stopResize)
}

function onResize(e: MouseEvent) {
  if (!isResizing) return
  const container = detailBodyRef.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const pct = ((e.clientY - rect.top) / rect.height) * 100
  topHeight.value = Math.max(25, Math.min(75, pct))
}

function stopResize() {
  isResizing = false
  resizeHandleRef.value?.classList.remove("resizing")
  document.removeEventListener("mousemove", onResize)
  document.removeEventListener("mouseup", stopResize)
}

async function onRun() {
  if (!(await requireLogin($t('caseDetail.runCase')))) return
  if (!envStore.currentEnvId) {
    msgWarning($t('caseDetail.selectEnv'))
    return
  }
  // 执行前先保存未保存的修改，确保后端使用最新数据
  if (isDirty.value) {
    try {
      const payload = {
        ...caseData.value,
        request_body: buildRequestBody(),
      }
      await request.put(`/projects/${projectId.value}/cases/${caseId.value}`, payload)
      isDirty.value = false
      tabsStore.markClean(caseTabKey.value)
    } catch (e) {
      logger.error("执行前自动保存失败:", e)
    }
  }
  running.value = true
  try {
    const res = await request.post(
      `/projects/${projectId.value}/run/case/${caseId.value}?env_id=${envStore.currentEnvId}`
    )
    lastResult.value = res.data
    if (res.data?.response_status === 0 && res.data?.error) {
      msgError($t('caseDetail.connectionFailed'))
    }
  } catch (e: unknown) {
    lastResult.value = {
      response_status: 500,
      response_body: JSON.stringify({ error: $t('caseDetail.requestFailed') }),
    }
  } finally {
    running.value = false
  }
}

async function onSave() {
  if (!(await requireLogin($t('caseDetail.saveCase')))) return
  if (saving.value) return  // 防止重复提交
  if (!caseData.value.name?.trim()) {
    msgError($t('caseDetail.inputCaseName'))
    return
  }
  saving.value = true
  try {
    const payload = {
      ...caseData.value,
      // 将 displayApi 中的请求覆盖写入 request_body
      request_body: buildRequestBody(),
    }
    await request.put(`/projects/${projectId.value}/cases/${caseId.value}`, payload)
    editorStore.markSaved()
    tabsStore.markClean(`case-${caseId.value}`)
    isDirty.value = false
    msgSuccess(MSG.SAVE_SUCCESS)
  } catch (e) {
    logger.error("保存用例失败:", e)
    msgError($t('caseDetail.saveFailed'))
  } finally {
    saving.value = false
  }
}

function buildRequestBody(): string | null {
  // 检查是否有与父 API 不同的请求参数
  if (!apiData.value) return null
  const diffs: Record<string, unknown> = {}
  const api = apiData.value
  const dp = displayApi.value

  // 使用 deepEqual 进行深度比较，避免 JSON.stringify 的键顺序问题
  // 对比 params
  if (!deepEqual(dp.params, api.params)) {
    diffs.params = dp.params
  }
  // 对比 headers
  if (!deepEqual(dp.headers, api.headers)) {
    diffs.headers = dp.headers
  }
  // 对比 body
  if (!deepEqual(dp.body, api.body)) {
    diffs.body = dp.body
  }
  // 对比 cookies
  if (!deepEqual(dp.cookies, api.cookies)) {
    diffs.cookies = dp.cookies
  }
  // 对比 auth
  if (!deepEqual(dp.auth, api.auth)) {
    diffs.auth = dp.auth
  }
  // 对比 pre_script / post_script
  if (dp.pre_script !== api.pre_script) {
    diffs.pre_script = dp.pre_script
  }
  if (dp.post_script !== api.post_script) {
    diffs.post_script = dp.post_script
  }

  return Object.keys(diffs).length > 0 ? JSON.stringify(diffs) : null
}

function onSaveAsCase() {
  // 已经是用例页面，复制当前用例
  showSaveCaseDialog.value = true
}

function onUpdateName(val: string) {
  caseData.value.name = val
}

function handleCaseSaved() {
  msgSuccess($t('caseDetail.caseSaved'))
}

function handleHistoryRestore(data: { url?: string; headers?: string; body?: string }) {
  const overrides: Record<string, unknown> = {}
  if (data.url && apiData.value) {
    overrides.path = data.url.replace(/^https?:\/\/[^/]+/, "")
  }
  if (data.headers) {
    try {
      const parsed = JSON.parse(data.headers)
      overrides.headers = Array.isArray(parsed)
        ? parsed
        : Object.entries(parsed).map(([k, v]) => ({ key: k, value: String(v), enabled: true }))
    } catch (e) {
      logger.warn('[CaseDetail] Failed to parse history headers:', e)
    }
  }
  if (data.body) {
    overrides.body = data.body
  }
  historyOverrides.value = overrides
}

function openAddToSceneDialog() {
  selectedSceneId.value = null
  sceneSearchKeyword.value = ''
  showAddToSceneDialog.value = true
}

let sceneSearchTimer: ReturnType<typeof setTimeout> | null = null

async function loadSceneList(keyword?: string) {
  if (sceneSearchTimer) {
    clearTimeout(sceneSearchTimer)
  }
  sceneSearchTimer = setTimeout(async () => {
    sceneListLoading.value = true
    try {
      const res = await listScenes(projectId.value, {
        keyword: keyword || '',
        page_size: 50,
      })
      sceneList.value = res.data.items || []
    } catch (e) {
      logger.error('[CaseDetail] 加载场景列表失败:', e)
      sceneList.value = []
    } finally {
      sceneListLoading.value = false
    }
  }, 200)
}

async function handleAddToScene() {
  if (!selectedSceneId.value || !caseData.value.id) return
  if (!(await requireLogin('添加到场景'))) return

  addToSceneLoading.value = true
  try {
    const sceneRes = await getScene(projectId.value, selectedSceneId.value)
    const scene = sceneRes.data
    const currentSteps = scene.steps || []

    const newStep = {
      node_id: `ref_case_${Date.now()}`,
      node_type: 'ref_case',
      label: caseData.value.name || '未命名用例',
      api_id: null,
      test_case_id: caseData.value.id,
      sort_order: currentSteps.length + 1,
      enabled: 1,
      headers: '[]',
      query_params: '[]',
      request_body: '',
      assertions: '[]',
      extract_vars: '[]',
      condition_expression: null,
      loop_count: null,
      loop_variable: null,
      wait_duration: null,
      wait_mode: 'fixed',
      wait_min: null,
      wait_max: null,
      depends_on_step_id: null,
    }

    const updatedSteps = [
      ...currentSteps.map((s, i) => ({
        id: s.id,
        node_id: (s as Record<string, unknown>).node_id || `step_${s.id}`,
        node_type: (s as Record<string, unknown>).node_type || 'request',
        label: s.name || s.label || '',
        api_id: (s as Record<string, unknown>).api_id ?? null,
        test_case_id: s.test_case_id ?? null,
        sort_order: i + 1,
        enabled: s.enabled ? 1 : 0,
        headers: (s as Record<string, unknown>).headers || '[]',
        query_params: (s as Record<string, unknown>).query_params || '[]',
        request_body: (s as Record<string, unknown>).request_body || '',
        assertions: (s as Record<string, unknown>).assertions || '[]',
        extract_vars: (s as Record<string, unknown>).extract_vars || '[]',
        condition_expression: (s as Record<string, unknown>).condition_expression ?? null,
        loop_count: (s as Record<string, unknown>).loop_count ?? null,
        loop_variable: (s as Record<string, unknown>).loop_variable ?? null,
        wait_duration: (s as Record<string, unknown>).wait_duration ?? null,
        wait_mode: (s as Record<string, unknown>).wait_mode || 'fixed',
        wait_min: (s as Record<string, unknown>).wait_min ?? null,
        wait_max: (s as Record<string, unknown>).wait_max ?? null,
        depends_on_step_id: (s as Record<string, unknown>).depends_on_step_id ?? null,
      })),
      newStep,
    ]

    await request.put(`/projects/${projectId.value}/scenes/${selectedSceneId.value}`, {
      steps: updatedSteps,
    })

    showAddToSceneDialog.value = false
    msgSuccess('已添加到场景')
  } catch (e) {
    logger.error('[CaseDetail] 添加到场景失败:', e)
    msgError('添加到场景失败')
  } finally {
    addToSceneLoading.value = false
  }
}

onUnmounted(() => {
  document.removeEventListener("mousemove", onResize)
  document.removeEventListener("mouseup", stopResize)
})
</script>



<style scoped>
@import './CaseDetail.css';

.breadcrumb-bar {
  padding: var(--space-2) var(--space-4);
  background: var(--surface-card);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
</style>
