<template>
  <div class="env-manager">
    <!-- 环境选择器 -->
    <div class="env-selector">
      <div class="env-tabs">
        <div
          v-for="env in environments"
          :key="env.id"
          class="env-tab-wrapper"
        >
          <button
            class="env-tab"
            :class="{ active: currentEnvId === env.id }"
            @click="selectEnv(env)"
          >
            <Globe :size="14" />
            <span>{{ env.name }}</span>
          </button>
          <button class="env-tab-clone" title="克隆环境" aria-label="克隆环境" :disabled="cloningId === env.id" @click.stop="cloneEnv(env)">
            <CopyPlus :size="12" />
          </button>
        </div>
        <button class="env-tab add-btn" @click="showCreateDialog = true">
          <Plus :size="14" />
          <span>新增环境</span>
        </button>
      </div>
    </div>

    <!-- 当前环境编辑区 -->
    <template v-if="currentEnv">
      <SkeletonTable v-if="loading" :rows="5" />
      <div v-else class="env-detail">
      <!-- 基本信息头 -->
      <div class="env-header">
        <div class="env-name-row">
          <el-input
            v-model="editForm.name"
            size="small"
            class="env-name-input"
            aria-label="环境名称"
            placeholder="环境名称"
          />
          <el-button size="small" type="danger" text aria-label="删除环境" :loading="deleting" @click="deleteEnv">
            <Trash2 :size="14" />
          </el-button>
        </div>
      </div>

      <!-- 服务地址 -->
      <div class="env-section">
        <div class="section-header">
          <h4 class="section-title">
            <Server :size="14" />
            服务地址
          </h4>
          <el-button size="small" text @click="addService"> <Plus :size="14" /> 添加 </el-button>
        </div>
        <div class="service-list">
          <div v-for="(svc, idx) in editForm.services" :key="idx" class="service-row">
            <el-input v-model="svc.name" size="small" placeholder="服务名称" aria-label="服务名称" class="svc-name" />
            <el-input v-model="svc.module" size="small" placeholder="模块" aria-label="模块" class="svc-module" />
            <el-input
              v-model="svc.url"
              size="small"
              placeholder="基础URL (如 http://localhost:8080)"
              aria-label="基础URL"
              class="svc-url"
            />
            <span class="sync-hint">修改后将自动同步</span>
            <el-checkbox v-model="svc.is_base" size="small" title="设为默认基础URL">
              默认
            </el-checkbox>
            <el-button size="small" text type="danger" aria-label="删除服务" @click="editForm.services.splice(idx, 1)">
              <X :size="14" />
            </el-button>
          </div>
          <div v-if="editForm.services.length === 0" class="empty-hint">
            暂无服务地址，点击上方"添加"按钮
          </div>
        </div>
      </div>

      <!-- 全局变量 -->
      <div class="env-section">
        <div class="section-header">
          <h4 class="section-title">
            <Braces :size="14" />
            全局变量
          </h4>
          <el-button size="small" text @click="addVariable"> <Plus :size="14" /> 添加 </el-button>
        </div>
        <div class="variable-list">
          <!-- 冲突警告提示 -->
          <div v-if="hasAnyConflict" class="conflict-warning">
            <AlertTriangle :size="14" />
            <span>检测到变量名冲突，请检查同名变量</span>
          </div>
          <div v-for="(v, idx) in editForm.variables" :key="idx" class="variable-row" :class="{ conflict: v.key && (duplicateEnvVars.has(v.key) || crossEnvConflicts.has(v.key)) }">
            <el-checkbox v-model="v.enabled" size="small" />
            <span class="var-scope env">Env</span>
            <el-input v-model="v.key" size="small" placeholder="变量名" aria-label="变量名" class="var-key" />
            <span class="var-eq">=</span>
            <el-input v-model="v.value" size="small" placeholder="变量值" aria-label="变量值" class="var-value" />
            <span v-if="v.key && crossEnvConflicts.has(v.key)" class="conflict-badge" title="与项目全局变量冲突">
              <AlertTriangle :size="12" /> 全局
            </span>
            <button
              class="var-copy-btn"
              v-if="v.key"
              title="复制变量名"
              aria-label="复制变量名"
              @click="copyVariableName(v.key)"
            >
              <Copy :size="12" />
            </button>
            <el-button size="small" text type="danger" aria-label="删除变量" @click="editForm.variables.splice(idx, 1)">
              <X :size="14" />
            </el-button>
          </div>
          <div v-if="editForm.variables.length === 0" class="empty-hint">暂无全局变量</div>
        </div>
      </div>

      <!-- 项目全局变量 -->
      <div class="env-section">
        <div class="section-header">
          <h4 class="section-title">
            <Braces :size="14" />
            项目全局变量
          </h4>
          <el-button size="small" text @click="addGlobalVariable"> <Plus :size="14" /> 添加 </el-button>
        </div>
        <div class="variable-list">
          <div v-for="(v, idx) in globalForm.variables" :key="'g-' + idx" class="variable-row" :class="{ conflict: v.key && duplicateGlobalVars.has(v.key) }">
            <el-checkbox v-model="v.enabled" size="small" />
            <span class="var-scope global">Global</span>
            <el-input v-model="v.key" size="small" placeholder="变量名" aria-label="变量名" class="var-key" />
            <span class="var-eq">=</span>
            <el-input v-model="v.value" size="small" placeholder="变量值" aria-label="变量值" class="var-value" />
            <button
              class="var-copy-btn"
              v-if="v.key"
              title="复制变量名"
              aria-label="复制变量名"
              @click="copyVariableName(v.key)"
            >
              <Copy :size="12" />
            </button>
            <el-button size="small" text type="danger" aria-label="删除变量" @click="globalForm.variables.splice(idx, 1)">
              <X :size="14" />
            </el-button>
          </div>
          <div v-if="globalForm.variables.length === 0" class="empty-hint">暂无项目全局变量</div>
        </div>
      </div>

      <!-- 请求头 -->
      <div class="env-section">
        <div class="section-header">
          <h4 class="section-title">
            <FileText :size="14" />
            全局请求头
          </h4>
          <el-button size="small" text @click="addHeader"> <Plus :size="14" /> 添加 </el-button>
        </div>
        <div class="header-list">
          <div v-for="(h, idx) in editForm.headers" :key="idx" class="header-row">
            <el-checkbox v-model="h.enabled" size="small" />
            <el-input v-model="h.key" size="small" placeholder="Header 名" aria-label="Header 名" class="hdr-key" />
            <span class="var-eq">:</span>
            <el-input v-model="h.value" size="small" placeholder="Header 值" aria-label="Header 值" class="hdr-value" />
            <el-button size="small" text type="danger" aria-label="删除请求头" @click="editForm.headers.splice(idx, 1)">
              <X :size="14" />
            </el-button>
          </div>
          <div v-if="editForm.headers.length === 0" class="empty-hint">暂无全局请求头</div>
        </div>
      </div>

      <!-- 保存按钮 -->
      <div class="env-footer">
        <VariablePreview
          v-if="currentEnv"
          mode="envManager"
          title="变量预览"
          :services="editForm.services"
          :variables="editForm.variables"
          :headers="editForm.headers"
        />
        <el-button type="primary" size="small" @click="saveEnv" :loading="saving">
          保存配置
        </el-button>
      </div>
    </div>
    </template>

    <!-- 初始加载骨架 -->
    <SkeletonCard v-if="firstLoad" type="env" />
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <Globe :size="40" class="empty-icon" />
      <p class="empty-title">还没有环境配置</p>
      <p class="empty-desc">创建一个环境来管理不同场景的服务地址和全局变量</p>
      <el-button type="primary" size="small" @click="showCreateDialog = true">
        <Plus :size="14" style="margin-right: 4px" />创建环境
      </el-button>
    </div>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建环境"
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form @submit.prevent="createEnv">
        <el-form-item label="环境名称">
          <el-input v-model="newEnvName" placeholder="如：开发环境、测试环境、生产环境" autofocus />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createEnv" :disabled="!newEnvName.trim()" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue"
import { ElMessageBox } from "element-plus"
import { Globe, Plus, Server, Braces, FileText, Trash2, X, Copy, AlertTriangle, CopyPlus } from "lucide-vue-next"
import VariablePreview from "./VariablePreview.vue"
import SkeletonTable from "./SkeletonTable.vue"
import request from "../api/request"
import { upsertEnvironmentVariable } from "../api/environments"
import { upsertGlobalVariable, updateGlobalConfig } from "../api/projects"
import { useRequireLogin } from "../composables/useRequireLogin"
import { msgSuccess, msgError } from '../utils/message'

interface ServiceItem {
  name: string
  module: string
  url: string
  is_base?: boolean
}

interface VariableItem {
  key: string
  value: string
  enabled: boolean
}

interface HeaderItem {
  key: string
  value: string
  enabled: boolean
}

interface EnvItem {
  id: number
  name: string
  services: ServiceItem[]
  variables: VariableItem[]
  headers: HeaderItem[]
}

const props = defineProps<{
  projectId: number
  currentEnvId?: number | null
}>()

const emit = defineEmits<{
  "env-changed": []
}>()

const { requireLogin } = useRequireLogin()

const environments = ref<EnvItem[]>([])
const envId = ref<number | null>(null)
const loading = ref(false)
const saving = ref(false)
const firstLoad = ref(true)
const creating = ref(false)
const deleting = ref(false)
const cloningId = ref<number | null>(null)

const showCreateDialog = ref(false)
const newEnvName = ref("")

const currentEnv = ref<EnvItem | null>(null)

// 跟踪原始变量列表，用于保存时检测删除的变量
const originalEnvVarKeys = ref<Set<string>>(new Set())
const originalGlobalVarKeys = ref<Set<string>>(new Set())

// 跟踪已保存的表单快照，用于检测未保存修改
const savedSnapshot = ref('')

const editForm = reactive({
  name: "",
  services: [] as ServiceItem[],
  variables: [] as VariableItem[],
  headers: [] as HeaderItem[],
})

const globalForm = reactive({
  variables: [] as VariableItem[],
})

// ── 变量名冲突检测 ──
/** 检测重复的变量名，返回冲突的 key 集合 */
function findDuplicateKeys(items: VariableItem[]): Set<string> {
  const keyCount = new Map<string, number>()
  for (const v of items) {
    if (v.key) {
      keyCount.set(v.key, (keyCount.get(v.key) || 0) + 1)
    }
  }
  return new Set(
    Array.from(keyCount.entries())
      .filter(([, count]) => count > 1)
      .map(([key]) => key)
  )
}

/** 检测环境变量与全局变量之间的冲突 */
function findCrossEnvConflicts() {
  const envKeys = new Set(editForm.variables.filter(v => v.key).map(v => v.key))
  const globalKeys = new Set(globalForm.variables.filter(v => v.key).map(v => v.key))
  const conflicts = new Set<string>()
  for (const key of envKeys) {
    if (globalKeys.has(key)) {
      conflicts.add(key)
    }
  }
  return conflicts
}

const duplicateEnvVars = computed(() => findDuplicateKeys(editForm.variables))
const duplicateGlobalVars = computed(() => findDuplicateKeys(globalForm.variables))
const crossEnvConflicts = computed(() => findCrossEnvConflicts())

const hasAnyConflict = computed(
  () => duplicateEnvVars.value.size > 0 || duplicateGlobalVars.value.size > 0 || crossEnvConflicts.value.size > 0
)

const hasUnsavedChanges = computed(() => {
  if (!currentEnv.value) return false
  const snapshot = JSON.stringify({
    name: editForm.name,
    services: editForm.services,
    variables: editForm.variables,
    headers: editForm.headers,
    globalVariables: globalForm.variables,
  })
  return snapshot !== savedSnapshot.value
})

async function fetchEnvs() {
  loading.value = true
  try {
    const res = await request.get(`/projects/${props.projectId}/environments`)
    environments.value = (res as { data?: EnvItem[] }).data || []
    // 优先使用传入的 currentEnvId（从环境选择器跳转过来时）
    const targetId = props.currentEnvId || envId.value
    if (targetId) {
      const env = environments.value.find((e) => e.id === targetId)
      if (env) selectEnv(env)
      else if (environments.value.length > 0) selectEnv(environments.value[0] as EnvItem)
      else envId.value = null
    } else if (environments.value.length > 0) {
      selectEnv(environments.value[0] as EnvItem)
    }
  } catch {
    msgError("加载环境列表失败")
  } finally {
    loading.value = false
    firstLoad.value = false
  }
}

async function fetchGlobalConfig() {
  try {
    const res = await request.get(`/projects/${props.projectId}/global-config`)
    const config = (res as { data?: Record<string, unknown> }).data || {}
    const rawVars = typeof config.global_variables === 'string'
      ? JSON.parse(config.global_variables || '[]')
      : ((config.global_variables as Record<string, unknown>[]) || [])
    globalForm.variables = (rawVars as VariableItem[]).map((v: VariableItem) => ({
      key: v.key || '',
      value: v.value || '',
      enabled: v.enabled !== false,
    }))
    // 记录原始全局变量 keys，用于保存时检测删除
    originalGlobalVarKeys.value = new Set(globalForm.variables.filter(v => v.key?.trim()).map(v => v.key))
    // 全局变量加载后更新快照
    if (currentEnv.value) {
      savedSnapshot.value = JSON.stringify({
        name: editForm.name,
        services: editForm.services,
        variables: editForm.variables,
        headers: editForm.headers,
        globalVariables: globalForm.variables,
      })
    }
  } catch {
    globalForm.variables = []
  }
}

async function selectEnv(env: EnvItem) {
  if (hasUnsavedChanges.value) {
    try {
      await ElMessageBox.confirm('当前环境有未保存的修改，切换后将丢失。是否继续？', '未保存的修改', {
        confirmButtonText: '放弃修改',
        cancelButtonText: '取消',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  envId.value = env.id
  currentEnv.value = env
  editForm.name = env.name || ""
  editForm.services = JSON.parse(JSON.stringify(env.services || []))
  editForm.variables = JSON.parse(JSON.stringify(env.variables || []))
  editForm.headers = JSON.parse(JSON.stringify(env.headers || []))
  // 记录原始变量 keys，用于保存时检测删除
  originalEnvVarKeys.value = new Set((env.variables || []).filter((v: VariableItem) => v.key?.trim()).map((v: VariableItem) => v.key))
  // 保存快照用于未保存修改检测
  savedSnapshot.value = JSON.stringify({
    name: editForm.name,
    services: editForm.services,
    variables: editForm.variables,
    headers: editForm.headers,
    globalVariables: globalForm.variables,
  })
  void fetchGlobalConfig()
}

async function saveEnv() {
  if (!await requireLogin("保存环境配置")) return
  if (!currentEnv.value) return
  saving.value = true
  try {
    const envId = currentEnv.value.id
    // 1. 变量保存：使用仅需读权限的 upsert 端点
    const varPromises = editForm.variables
      .filter((v: VariableItem) => v.key?.trim())
      .map((v: VariableItem) => upsertEnvironmentVariable(props.projectId, envId, v.key, v.value || ''))
    await Promise.all(varPromises)

    // 2. 环境配置保存（名称、服务地址、请求头、变量）：需要写权限
    //    传入 variables 以便后端整体替换，从而删除已移除的变量
    try {
      await request.put(`/projects/${props.projectId}/environments/${envId}`, {
        name: editForm.name,
        services: editForm.services,
        variables: editForm.variables.filter((v: VariableItem) => v.key?.trim()),
        headers: editForm.headers,
      }, { _silent403: true })
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 403) {
        msgError('变量已保存，但环境名称/服务地址等配置需要写权限才能修改')
      } else {
        throw err
      }
    }

    // 3. 全局变量保存：使用仅需读权限的 upsert 端点
    const globalVarPromises = globalForm.variables
      .filter((v: VariableItem) => v.key?.trim())
      .map((v: VariableItem) => upsertGlobalVariable(props.projectId, v.key, v.value || ''))
    await Promise.all(globalVarPromises)

    // 4. 全局变量删除：通过整体更新全局配置来删除已移除的变量
    const currentGlobalKeys = new Set(globalForm.variables.filter((v: VariableItem) => v.key?.trim()).map((v: VariableItem) => v.key))
    const deletedGlobalKeys = [...originalGlobalVarKeys.value].filter(k => !currentGlobalKeys.has(k))
    if (deletedGlobalKeys.length > 0) {
      try {
        await updateGlobalConfig(props.projectId, {
          global_variables: globalForm.variables.filter((v: VariableItem) => v.key?.trim()),
        })
      } catch {
        // 写权限不足时忽略，upsert 已保存新增/修改的变量
      }
    }

    msgSuccess("已保存")
    // 保存成功后更新快照
    savedSnapshot.value = JSON.stringify({
      name: editForm.name,
      services: editForm.services,
      variables: editForm.variables,
      headers: editForm.headers,
      globalVariables: globalForm.variables,
    })
    emit("env-changed")
    await fetchEnvs()
    await fetchGlobalConfig()
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number; data?: { message?: string } } })?.response?.status
    const serverMsg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
    if (status === 403) {
      msgError(serverMsg || '您没有该项目的写权限，无法保存环境配置')
    } else {
      msgError("保存失败")
    }
  } finally {
    saving.value = false
  }
}

async function createEnv() {
  if (!await requireLogin("创建环境")) return
  const name = newEnvName.value.trim()
  if (!name) return
  creating.value = true
  try {
    const res = await request.post(`/projects/${props.projectId}/environments`, {
      name,
      services: [
        { name: "默认服务", module: "default", url: "", is_base: true },
      ],
      variables: [],
      headers: [],
    })
    msgSuccess("环境创建成功")
    showCreateDialog.value = false
    newEnvName.value = ""
    emit("env-changed")
    await fetchEnvs()
    if ((res as { data?: { id: number } }).data?.id) {
      const newEnv = environments.value.find((e) => e.id === (res as { data?: { id: number } }).data!.id)
      if (newEnv) selectEnv(newEnv)
    }
  } catch {
    msgError("创建失败")
  } finally {
    creating.value = false
  }
}

async function deleteEnv() {
  if (!await requireLogin("删除环境")) return
  if (!currentEnv.value) return
  try {
    await ElMessageBox.confirm(`确定删除环境「${currentEnv.value.name}」？`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    })
    deleting.value = true
    await request.delete(`/projects/${props.projectId}/environments/${currentEnv.value.id}`)
    msgSuccess("已删除")
    currentEnv.value = null
    envId.value = null
    emit("env-changed")
    await fetchEnvs()
  } catch {
    /* user cancelled */
  } finally {
    deleting.value = false
  }
}

async function cloneEnv(env: EnvItem) {
  if (!await requireLogin("克隆环境")) return
  if (cloningId.value === env.id) return
  cloningId.value = env.id
  try {
    await request.post(`/projects/${props.projectId}/environments/${env.id}/clone`)
    msgSuccess("环境克隆成功")
    emit("env-changed")
    await fetchEnvs()
  } catch {
    msgError("克隆失败")
  } finally {
    cloningId.value = null
  }
}

function addService() {
  editForm.services.push({ name: "", module: "", url: "", is_base: editForm.services.length === 0 })
}

function copyVariableName(key: string) {
  navigator.clipboard.writeText(`{{${key}}}`).then(
    () => msgSuccess(`已复制 {{${key}}}`),
    () => msgError('复制失败')
  )
}

function addGlobalVariable() {
  globalForm.variables.push({ key: "", value: "", enabled: true })
}

function addVariable() {
  editForm.variables.push({ key: "", value: "", enabled: true })
}

function addHeader() {
  editForm.headers.push({ key: "", value: "", enabled: true })
}

onMounted(() => {
  void fetchEnvs()
})
</script>

<style scoped>
.env-manager {
  padding: var(--space-4);
}

/* 环境选择器 */
.env-selector {
  margin-bottom: var(--space-4);
}
.env-selector :deep(.el-select .el-input__wrapper) {
  height: 35px !important;
}
.env-tabs {
  display: flex;
  gap: var(--space-1);
  flex-wrap: wrap;
  align-items: center;
}
.env-tab-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 0;
}
.env-tab-clone {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--border-subtle);
  border-left: none;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  background: var(--surface-bg);
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: all var(--duration-fast);
  flex-shrink: 0;
}
.env-tab-wrapper:hover .env-tab-clone {
  opacity: 1;
}
.env-tab-clone:hover {
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
  border-color: var(--primary-400);
}
.env-tab-wrapper .env-tab {
  border-radius: var(--radius-md) 0 0 var(--radius-md);
}
.env-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: calc(var(--space-2) - 2px) var(--space-3-5);
  background: var(--surface-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast);
  white-space: nowrap;
}
.env-tab:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--primary-300);
}
.env-tab.active {
  background: var(--color-primary-alpha-10);
  color: var(--primary-700);
  border-color: var(--primary-400);
  font-weight: var(--weight-semibold);
}
.env-tab.add-btn {
  color: var(--primary-600);
  border-color: var(--primary-300);
  border-style: solid;
  background: var(--primary-50);
}
.env-tab.add-btn:hover {
  color: var(--color-white);
  background: var(--primary-600);
  border-color: var(--primary-600);
}

/* 环境详情 */
.env-detail {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  overflow: hidden;
}
.env-header {
  margin-bottom: var(--space-5);
}
.env-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.env-name-input {
  max-width: 300px;
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

/* 区块 */
.env-section {
  margin-bottom: var(--space-5);
  overflow-x: auto;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

/* 列表行 */
.service-row,
.variable-row,
.header-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.service-row .svc-name {
  min-width: var(--min-w-input-md);
  flex: 0 0 auto;
  max-width: 150px;
  overflow: hidden;
}
.service-row .svc-name :deep(.el-input__inner) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.service-row .svc-module {
  min-width: var(--min-w-input-sm);
  flex: 0 0 auto;
  max-width: 150px;
  overflow: hidden;
}
.service-row .svc-module :deep(.el-input__inner) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.service-row .svc-url {
  min-width: 200px;
  flex: 1;
  overflow: hidden;
}
.service-row .svc-url :deep(.el-input__inner) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.variable-row .var-key {
  min-width: var(--min-w-input-md);
  flex: 0 0 auto;
  max-width: 200px;
}
.variable-row .var-value {
  min-width: 140px;
  flex: 1;
  max-width: 100%;
  overflow: hidden;
}
.variable-row .var-value :deep(.el-input__inner) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-row .hdr-key {
  min-width: var(--min-w-input-md);
  flex: 0 0 auto;
  max-width: 200px;
}
.header-row .hdr-value {
  min-width: 140px;
  flex: 1;
  max-width: 100%;
  overflow: hidden;
  max-width: 140px;
}
.service-row .svc-module {
  max-width: 120px;
}
.service-row .svc-url {
  flex: 1;
}
.variable-row .var-key {
  max-width: 200px;
}
.variable-row .var-value {
  flex: 1;
}
.header-row .hdr-key {
  max-width: 200px;
}
.header-row .hdr-value {
  flex: 1;

}
.var-scope {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-1-5);
  height: 20px;
  border-radius: var(--radius-xs);
  font-size: 9px;
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}
.var-scope.env {
  background: var(--method-get-bg);
  color: var(--method-get-text);
}
.var-scope.global {
  background: var(--method-put-bg);
  color: var(--method-put-text);
}
.var-copy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--space-6);
  height: var(--space-6);
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--duration-fast), background var(--duration-fast), color var(--duration-fast);
  flex-shrink: 0;
}
.variable-row:hover .var-copy-btn {
  opacity: 1;
}
.var-copy-btn:hover {
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
}

.var-eq {
  color: var(--text-muted);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

/* 空提示 */
.empty-hint {
  padding: var(--space-6) var(--space-4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface-hover);
}
html.dark .empty-hint {
  border-color: var(--border-subtle);
  background: var(--surface-hover);
}

/* 底部保存 */
.env-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) 0 var(--space-10);
  border-top: 1px solid var(--border-subtle);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-15) var(--space-4);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.empty-state .empty-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
}
.empty-state .empty-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}
.empty-icon {
  opacity: 0.4;
}

/* ===== Dark Mode ===== */
html.dark .env-detail {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
html.dark .env-tab {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  color: var(--text-secondary);
}
html.dark .env-tab:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
html.dark .env-tab.active {
  background: var(--color-primary-alpha-15);
  color: var(--primary-400);
  border-color: var(--primary-500);
}
html.dark .section-title {
  color: var(--text-secondary) !important;
  font-weight: var(--weight-bold) !important;
  font-size: var(--text-sm) !important;
}
html.dark .empty-state {
  color: var(--text-muted) !important;
}
html.dark .env-footer {
  border-color: var(--border-subtle) !important;
}
html.dark .env-tab {
  color: var(--text-secondary) !important;
}
html.dark .env-tab:hover {
  color: var(--text-primary) !important;
  border-color: var(--primary-400) !important;
}
html.dark .env-tab.active {
  background: var(--color-primary-alpha-12) !important;
  color: var(--primary-400) !important;
  border-color: var(--primary-500) !important;
}
html.dark .env-tab.add-btn {
  color: var(--primary-400) !important;
  background: var(--color-primary-alpha-10) !important;
  border-color: var(--primary-700) !important;
}
html.dark .env-tab.add-btn:hover {
  color: var(--color-white) !important;
  background: var(--primary-600) !important;
  border-color: var(--primary-600) !important;
}
html.dark .env-detail {
  background: var(--surface-card) !important;
  border-color: var(--border-subtle) !important;
}
html.dark .service-row .svc-name :deep(.el-input__inner),
html.dark .variable-row .var-key :deep(.el-input__inner),
html.dark .header-row .hdr-key :deep(.el-input__inner) {
  color: var(--text-secondary) !important;
}
html.dark .var-scope.env {
  background: var(--color-primary-alpha-20);
  color: var(--primary-400);
}
html.dark .var-scope.global {
  background: var(--color-warning-alpha-20);
  color: var(--color-warning);
}
html.dark .var-copy-btn {
  color: var(--text-muted);
}
html.dark .var-copy-btn:hover {
  background: var(--color-primary-alpha-15);
  color: var(--primary-400);
}
html.dark .var-eq {
  color: var(--text-muted) !important;
}

/* ===== v3 暗色对比度全面修复 ===== */
html.dark .env-manager {
  background: transparent !important;
}
html.dark .env-detail {
  background: var(--surface-card) !important;
  border-color: var(--border-subtle) !important;
  padding: var(--space-5) !important;
}
html.dark .env-section {
  margin-bottom: var(--space-5) !important;
}
html.dark .section-header {
  margin-bottom: var(--space-3) !important;
}
html.dark .section-title {
  color: var(--text-primary) !important;
  font-weight: var(--weight-bold) !important;
  font-size: var(--text-sm) !important;
}

/* 服务地址行 */
html.dark .service-row {
  margin-bottom: var(--space-3) !important;
}
html.dark .svc-name {
  color: var(--text-secondary) !important;
  font-weight: var(--weight-semibold) !important;
  font-size: var(--text-xs) !important;
}
html.dark .svc-module {
  color: var(--text-secondary) !important;
  font-size: var(--text-xs) !important;
}
html.dark .svc-name :deep(.el-input__wrapper),
html.dark .svc-url :deep(.el-input__wrapper) {
  background: var(--border-default) !important;
  border-color: var(--border-strong) !important;
  box-shadow: none !important;
}
html.dark .svc-name :deep(.el-input__inner),
html.dark .svc-url :deep(.el-input__inner) {
  color: var(--text-primary) !important;
}
html.dark .svc-name :deep(.el-input__inner::placeholder),
html.dark .svc-url :deep(.el-input__inner::placeholder) {
  color: var(--text-muted) !important;
}

/* 变量行 */
html.dark .variable-row {
  margin-bottom: var(--space-2) !important;
}
html.dark .var-key {
  color: var(--text-secondary) !important;
}
html.dark .var-value {
  color: var(--text-secondary) !important;
}
html.dark .var-key :deep(.el-input__wrapper),
html.dark .var-value :deep(.el-input__wrapper) {
  background: var(--border-default) !important;
  border-color: var(--border-strong) !important;
  box-shadow: none !important;
}
html.dark .var-key :deep(.el-input__inner),
html.dark .var-value :deep(.el-input__inner) {
  color: var(--text-primary) !important;
}
html.dark .var-key :deep(.el-input__inner::placeholder),
html.dark .var-value :deep(.el-input__inner::placeholder) {
  color: var(--text-muted) !important;
}

/* 请求头行 */
html.dark .header-row {
  margin-bottom: var(--space-2) !important;
}
html.dark .hdr-key {
  color: var(--text-secondary) !important;
}
html.dark .hdr-value {
  color: var(--text-secondary) !important;
}
html.dark .hdr-key :deep(.el-input__wrapper),
html.dark .hdr-value :deep(.el-input__wrapper) {
  background: var(--border-default) !important;
  border-color: var(--border-strong) !important;
  box-shadow: none !important;
}
html.dark .hdr-key :deep(.el-input__inner),
html.dark .hdr-value :deep(.el-input__inner) {
  color: var(--text-primary) !important;
}

/* 环境名输入 */
html.dark .env-name-input :deep(.el-input__wrapper) {
  background: var(--border-default) !important;
  border-color: var(--border-strong) !important;
  box-shadow: none !important;
}
html.dark .env-name-input :deep(.el-input__inner) {
  color: var(--text-primary) !important;
}

/* 删除按钮 */
html.dark .env-footer .el-button--danger {
  color: var(--error-light) !important;
}
html.dark .service-row .el-button--danger,
html.dark .variable-row .el-button--danger,
html.dark .header-row .el-button--danger {
  color: var(--text-secondary) !important;
}
html.dark .service-row .el-button--danger:hover,
html.dark .variable-row .el-button--danger:hover,
html.dark .header-row .el-button--danger:hover {
  color: var(--error-light) !important;
}

/* ===== 响应式 ===== */
@media (max-width: 768px) {
  .service-row {
    flex-wrap: wrap;
  }
  .service-row .svc-name,
  .service-row .svc-module {
    max-width: 100%;
    flex: 1;
  }
  .service-row .svc-url {
    flex-basis: 100%;
  }
}

/* ===== 变量名冲突警告 ===== */
.conflict-warning {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-2);
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  color: var(--color-warning-text);
  font-size: var(--text-xs);
}
.conflict-warning svg {
  flex-shrink: 0;
}

.variable-row.conflict {
  background: var(--color-warning-bg);
  border-color: var(--color-warning-border);
}

.conflict-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 1px 6px;
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-sm);
  color: var(--color-warning-text);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
}

html.dark .conflict-warning {
  background: var(--warning-bg);
  border-color: var(--warning-border);
  color: var(--warning-light);
}
html.dark .variable-row.conflict {
  background: var(--warning-bg);
  border-color: var(--warning-border);
}
html.dark .conflict-badge {
  background: var(--warning-bg);
  border-color: var(--warning-border);
  color: var(--warning-light);
}

.sync-hint {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 2px;
}
</style>
