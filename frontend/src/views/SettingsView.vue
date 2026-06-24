<template>
  <PageLayout
    class="settings-view"
    role="main"
    :aria-label="$t('settings.title')"
    :title="$t('settings.title')"
    :subtitle="$t('settings.subtitle')"
    :kicker="$t('settings.kicker')"
  >
    <template #hero-extra>
      <div class="settings-hero-panel">
        <div class="settings-hero-label">{{ $t('settings.configStatus') }}</div>
        <div class="settings-hero-value">{{ activeTabLabel }}</div>
        <div class="settings-hero-subtitle">{{ $t('settings.currentTab') }}</div>
      </div>
    </template>

    <div class="settings-tabs-wrap" role="tablist">
      <button
        v-for="tab in tabList"
        :key="tab.key"
        class="settings-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
        role="tab"
        :aria-selected="activeTab === tab.key"
        :aria-controls="'panel-' + tab.key"
        :id="'tab-' + tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="settings-summary-grid">
      <div v-if="canManageMembers" class="settings-summary-card clickable" @click="activeTab = 'member'">
        <div class="settings-summary-label">{{ $t('settings.memberLabel') }}</div>
        <div class="settings-summary-value">{{ activeTab === 'member' ? $t('settings.memberCollabPerm') : $t('settings.memberTeamConfig') }}</div>
        <div class="settings-summary-desc">{{ $t('settings.memberDesc') }}</div>
      </div>
      <div v-if="isLoggedIn" class="settings-summary-card clickable" @click="activeTab = 'env'">
        <div class="settings-summary-label">{{ $t('settings.envLabel') }}</div>
        <div class="settings-summary-value">{{ envStore.currentEnvId ? $t('settings.envSelected') : $t('settings.envNotSelected') }}</div>
        <div class="settings-summary-desc">{{ $t('settings.envDesc') }}</div>
      </div>
      <div v-if="canExport" class="settings-summary-card clickable" @click="activeTab = 'export'">
        <div class="settings-summary-label">{{ $t('settings.exportLabel') }}</div>
        <div class="settings-summary-value">{{ exportFormat.toUpperCase() }}</div>
        <div class="settings-summary-desc">{{ $t('settings.exportDesc') }}</div>
      </div>
    </div>

    <!-- 成员管理 -->
    <div
      v-if="activeTab === 'member'"
      class="settings-content"
      role="tabpanel"
      :aria-labelledby="'tab-member'"
    >
      <MemberManager :project-id="projectId" />
    </div>

    <!-- 环境管理 -->
    <div
      v-if="activeTab === 'env'"
      class="settings-content"
      role="tabpanel"
      :aria-labelledby="'tab-env'"
    >
      <EnvManager
        :project-id="projectId"
        :current-env-id="envStore.currentEnvId"
        @env-changed="onEnvChanged"
      />
    </div>

    <!-- 项目信息 -->
    <div
      v-if="activeTab === 'info'"
      class="settings-content"
      role="tabpanel"
      :aria-labelledby="'tab-info'"
      v-loading="pageLoading"
      :element-loading-text="$t('settings.loadingText')"
    >
      <div v-if="pageError" class="settings-error-bar">
        <span class="settings-error-text">{{ pageError }}</span>
        <el-button size="small" text class="settings-error-retry" @click="reloadProjectInfo()">{{ $t('settings.retry') }}</el-button>
      </div>
      <div class="settings-card">
        <div class="card-body">
          <div class="form-row">
            <label class="form-label">{{ $t('settings.nameField') }}</label>
            <el-input v-model="projectInfo.name" size="small" :aria-label="$t('settings.nameField')" :class="{ 'is-error': errors.name }" />
            <div v-if="errors.name" class="form-error">{{ errors.name }}</div>
          </div>
          <div class="form-row">
            <label class="form-label">{{ $t('settings.projectIdentifier') }}</label>
            <el-input
              :model-value="'proj_' + projectId"
              size="small"
              readonly
              :aria-label="$t('settings.projectIdentifier')"
              class="readonly-field"
            />
          </div>
          <div class="form-row">
            <label class="form-label">{{ $t('settings.descField') }}</label>
            <el-input v-model="projectInfo.description" type="textarea" :rows="3" :aria-label="$t('settings.descField')" />
          </div>
          <div class="form-row">
            <label class="form-label">{{ $t('settings.visibility') }}</label>
            <div class="visibility-row">
              <el-radio-group v-model="projectInfo.is_public" size="small">
                <el-radio-button :value="false">{{ $t('settings.private') }}</el-radio-button>
                <el-radio-button :value="true">{{ $t('settings.public') }}</el-radio-button>
              </el-radio-group>
              <span class="form-hint visibility-hint">{{ projectInfo.is_public ? $t('settings.publicDesc') : $t('settings.privateDesc') }}</span>
            </div>
          </div>
          <div class="settings-action-row">
            <el-button size="small" type="primary" :loading="saveLock.loading.value" :disabled="saveLock.disabled.value || !isValid" @click="saveProject">{{ $t('settings.save') }}</el-button>
            <span v-if="projectInfo.created_at" class="form-hint settings-created-at">{{ $t('settings.createdAt') }} {{ formatProjectCreatedAt(projectInfo.created_at) }}</span>
          </div>
          <!-- 危险操作区 -->
          <div class="danger-zone" v-if="userStore.isAdmin">
            <div class="danger-zone-header">
              <h3 class="danger-zone-title">{{ $t('settings.dataMaintenance') }}</h3>
              <p class="danger-zone-desc">{{ $t('settings.dataMaintenanceDesc') }}</p>
            </div>
            <el-button
              size="small"
              type="danger"
              plain
              @click="handleResetSeed"
              :loading="resetting"
            >
              <RotateCcw :size="14" class="btn-icon" />
              {{ resetting ? $t('settings.resetting') : $t('settings.resetDemoData') }}
            </el-button>
          </div>
        </div>
      </div>
    </div>


    <!-- 导出 -->
    <div
      v-if="activeTab === 'export'"
      class="settings-content"
      role="tabpanel"
      :aria-labelledby="'tab-export'"
      v-loading="pageLoading"
      :element-loading-text="$t('settings.loadingText')"
    >
      <div class="settings-card">
        <div class="card-head">
          <span class="card-title">{{ $t('settings.dataExportTitle') }}</span>
        </div>
        <div class="card-body">
          <p class="mock-desc">{{ $t('settings.dataExportDesc') }}</p>
          <div class="export-options">
            <label class="export-option" :class="{ active: exportFormat === 'pilot' }">
              <input type="radio" v-model="exportFormat" value="pilot" class="export-radio-hidden" />
              <div class="export-option-title">{{ $t('settings.pilotJson') }}</div>
              <div class="export-option-desc">{{ $t('settings.pilotJsonDesc') }}</div>
            </label>
            <label class="export-option" :class="{ active: exportFormat === 'postman' }">
              <input type="radio" v-model="exportFormat" value="postman" class="export-radio-hidden" />
              <div class="export-option-title">{{ $t('settings.postmanCollection') }}</div>
              <div class="export-option-desc">{{ $t('settings.postmanCollectionDesc') }}</div>
            </label>
            <label class="export-option" :class="{ active: exportFormat === 'openapi' }">
              <input type="radio" v-model="exportFormat" value="openapi" class="export-radio-hidden" />
              <div class="export-option-title">{{ $t('settings.openapiFormat') }}</div>
              <div class="export-option-desc">{{ $t('settings.openapiFormatDesc') }}</div>
            </label>
            <label class="export-option" :class="{ active: exportFormat === 'environments' }">
              <input type="radio" v-model="exportFormat" value="environments" class="export-radio-hidden" />
              <div class="export-option-title">{{ $t('settings.envVariablesOnly') }}</div>
              <div class="export-option-desc">{{ $t('settings.envVariablesOnlyDesc') }}</div>
            </label>
            <label class="export-option" :class="{ active: exportFormat === 'full_zip' }">
              <input type="radio" v-model="exportFormat" value="full_zip" class="export-radio-hidden" />
              <div class="export-option-title">{{ $t('settings.fullExport') }}</div>
              <div class="export-option-desc">{{ $t('settings.fullExportDesc') }}</div>
            </label>
          </div>
          <el-button
            size="small"
            type="primary"
            :loading="exporting"
            @click="handleExport"
            class="export-btn"
          >
            <Download :size="14" class="btn-icon" />
            {{ exporting ? $t('settings.exporting') : $t('settings.startExport') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 变量（5 层） -->
    <div v-if="activeTab === 'variables'" class="settings-content" v-loading="loadingVariables">
      <div class="settings-card">
        <div class="card-head">
          <span class="card-title">{{ $t('settings.varScopeTitle') }}</span>
          <el-button size="small" type="primary" @click="openAddVarDialog">
            <Plus :size="14" />{{ $t('settings.addVar') }}
          </el-button>
        </div>
        <div class="card-body">
          <el-table :data="variables" stripe size="small">
            <el-table-column prop="key" :label="$t('settings.varKeyCol')" min-width="160" />
            <el-table-column :label="$t('settings.varValueCol')" min-width="240">
              <template #default="{ row }">
                <div v-if="row.encrypted" class="var-value-cell">
                  <code v-if="revealedVarKeys[row.id]">{{ revealedVarKeys[row.id].value }}</code>
                  <span v-else class="var-masked">••••••••</span>
                  <span v-if="revealedVarKeys[row.id]" class="var-countdown">{{ revealedVarKeys[row.id].countdown }}s</span>
                  <el-button
                    v-if="!revealedVarKeys[row.id]"
                    link
                    size="small"
                    type="warning"
                    @click="handleRevealVar(row)"
                    :loading="revealingVarId === row.id"
                  >
                    <Eye :size="14" />{{ $t('settings.showPlaintext') }}
                  </el-button>
                </div>
                <code v-else>{{ row.value }}</code>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.varScopeCol')" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ scopeLabel(row.scope) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.encryptedCol')" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.encrypted" type="warning" size="small">{{ $t('settings.encryptedCol') }}</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.updatedCol')" width="180">
              <template #default="{ row }">
                <span class="muted">{{ formatTime(row.updated_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.actionCol')" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link size="small" @click="openEditVarDialog(row)">{{ $t('settings.editBtn') }}</el-button>
                <el-button link size="small" type="primary" @click="showVarReferences(row)">{{ $t('settings.refBtn') }}</el-button>
                <el-button link size="small" type="danger" @click="deleteVar(row)">{{ $t('settings.deleteBtn') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 变量编辑对话框 -->
      <el-dialog v-model="showVarDialog" :title="editingVar ? $t('settings.editVarTitle') : $t('settings.addVarTitle')" width="480px" destroy-on-close>
        <el-form v-if="editingVar" label-width="80px" size="small">
          <el-form-item label="Key">
            <el-input :model-value="editingVar.key" disabled />
          </el-form-item>
          <el-form-item :label="$t('settings.varValueCol')">
            <el-input v-model="editingVar.value" :type="editingVar.encrypted ? 'password' : 'text'" show-password />
          </el-form-item>
          <el-form-item :label="$t('settings.varScopeCol')">
            <el-select :model-value="scopeLabel(editingVar.scope)" disabled />
          </el-form-item>
          <el-form-item :label="$t('settings.encryptedCol')">
            <el-switch v-model="editingVar.encrypted" />
          </el-form-item>
        </el-form>
        <el-form v-else label-width="80px" size="small">
          <el-form-item label="Key">
            <el-input v-model="newVar.key" :placeholder="$t('settings.varNamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('settings.varValueCol')">
            <el-input v-model="newVar.value" :placeholder="$t('settings.varValuePlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('settings.varScopeCol')">
            <el-select v-model="newVar.scope">
              <el-option :label="$t('settings.scopeGlobal')" value="global" />
              <el-option :label="$t('settings.scopeProject')" value="project" />
              <el-option :label="$t('settings.scopeEnvironment')" value="environment" />
              <el-option :label="$t('settings.scopeScene')" value="scene" />
              <el-option :label="$t('settings.scopeCase')" value="case" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('settings.encryptedCol')">
            <el-checkbox v-model="newVar.encrypted" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showVarDialog = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="varLock.loading.value" :disabled="varLock.disabled.value" @click="saveVarDialog">{{ $t('settings.save') }}</el-button>
        </template>
      </el-dialog>

      <!-- 变量引用对话框 -->
      <el-dialog v-model="showRefDialog" :title="refDialogTitle" width="560px" destroy-on-close>
        <div v-loading="loadingRefs">
          <div v-if="varRefs.length === 0 && !loadingRefs" class="empty-hint">{{ $t('settings.noVarRefs') }}</div>
          <el-table v-else :data="varRefs" stripe size="small">
            <el-table-column :label="$t('settings.refTypeCol')" width="80">
              <template #default="{ row }">
                <el-tag :type="row.type === 'step' ? 'primary' : 'success'" size="small">
                  {{ row.type === 'step' ? $t('settings.refTypeStep') : $t('settings.refTypeCase') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" :label="$t('settings.refNameCol')" min-width="160" />
            <el-table-column :label="$t('settings.refSceneCol')" min-width="160">
              <template #default="{ row }">
                <span v-if="row.scene_name">{{ row.scene_name }}</span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('settings.refActionCol')" width="80">
              <template #default="{ row }">
                <el-button link size="small" type="primary" @click="navigateToRef(row)">{{ $t('settings.refGoBtn') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-dialog>
    </div>


  </PageLayout>
</template>
<script setup lang="ts">
defineOptions({ name: 'SettingsView' })
import { ref, reactive, computed, watch, onMounted, onUnmounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useI18n } from "vue-i18n"
import { useRequireLogin } from "../composables/useRequireLogin"
import { useSubmitLock } from "../composables/useSubmitLock"
import { formatProjectCreatedAt, useSettingsProjectInfo } from "../composables/useSettingsProjectInfo"
import { useFormValidation } from "@/composables/useFormValidation"
import { RoutePaths } from '../router/paths'
import { useEnvStore } from "../stores/envStore"
import { useUserStore } from "../stores/userStore"
import { useProjectStore } from "../stores/projectStore"
import { useProjectPermission } from "../composables/useProjectPermission"
import EnvManager from "../components/EnvManager.vue"
import MemberManager from "../components/MemberManager.vue"
import PageLayout from "../components/common/PageLayout.vue"
import { Download, RotateCcw, Plus, Eye } from "lucide-vue-next"
import { ElMessageBox } from "element-plus"
import { msgSuccess, msgError, msgWarning } from '@/utils/message'
import {
  listVariables, upsertVariable, deleteVariable, revealEncryptedVariable,
  getVariableReferences,
  type Variable, type VariableScope, type VariableReference,
} from "../api/variables"


const route = useRoute()
const router = useRouter()
const { t: $t } = useI18n()
const projectId = computed(() => Number(route.params.id))

const activeTab = ref("info")

const { requireLogin } = useRequireLogin()
const envStore = useEnvStore()
const userStore = useUserStore()
const projectStore = useProjectStore()
const { canManageMembers, canManageSettings, canExport, canEdit, isLoggedIn } = useProjectPermission()

const allTabs = [
  { key: "info", label: $t('settings.infoTab'), perm: 'settings' },
  { key: "member", label: $t('settings.memberTab'), perm: 'members' },
  { key: "env", label: $t('settings.envTab'), perm: 'env' },
  { key: "variables", label: $t('settings.varTab'), perm: 'edit' },
  { key: "export", label: $t('settings.exportTab'), perm: 'export' },
]

const tabList = computed(() => {
  return allTabs.filter((tab) => {
    switch (tab.perm) {
      case 'members':
        return canManageMembers.value
      case 'settings':
        return canManageSettings.value
      case 'edit':
        return canEdit.value
      case 'export':
        return canExport.value
      case 'env':
        return isLoggedIn.value
      default:
        return true
    }
  })
})

const activeTabLabel = computed(() => tabList.value.find((tab) => tab.key === activeTab.value)?.label ?? $t('settings.infoTab'))

watch(() => route.query.tab, (tab) => {
  if (typeof tab === 'string' && tabList.value.some((t) => t.key === tab)) {
    activeTab.value = tab
  }
}, { immediate: true })

watch(tabList, (tabs) => {
  if (tabs.length > 0 && !tabs.some((t) => t.key === activeTab.value)) {
    activeTab.value = tabs[0].key
  }
}, { immediate: true })

const {
  exportFormat,
  exporting,
  handleExport,
  handleResetSeed,
  pageError,
  pageLoading,
  projectInfo,
  reloadProjectInfo,
  resetting,
  saveProject: _saveProject,
} = useSettingsProjectInfo({
  projectId: projectId.value,
  requireLogin,
  refreshProjects: () => projectStore.fetchProjects(),
})

const saveLock = useSubmitLock()
const saveProject = () => saveLock.run(() => _saveProject())

const { errors, isValid } = useFormValidation(
  () => projectInfo,
  { name: { required: $t('settings.projectNameRequired'), maxLength: { value: 50, message: $t('settings.projectNameTooLong2') } } }
)

async function onEnvChanged() {
  await envStore.fetchEnvs(projectId.value)
  await envStore.fetchGlobalConfig(projectId.value)
}

// ── 变量管理 ──
const variables = ref<Variable[]>([])
const loadingVariables = ref(false)
const showVarDialog = ref(false)
const editingVar = ref<{
  id?: number
  key: string
  value: string
  scope: VariableScope
  scope_id?: number | null
  encrypted: boolean
  description?: string
} | null>(null)
const revealingVarId = ref<number | null>(null)
const revealedVarKeys = ref<Record<number, { value: string; countdown: number }>>({})
const revealTimers = ref<Record<number, ReturnType<typeof setInterval>>>({})

const varLock = useSubmitLock()

const newVar = reactive({ key: '', value: '', scope: 'project' as VariableScope, encrypted: false })

async function handleRevealVar(v: Variable) {
  try {
    await ElMessageBox.confirm(
      $t('settings.confirmPlaintext'),
      $t('settings.confirmPlaintextTitle'),
      { confirmButtonText: $t('common.confirm'), cancelButtonText: $t('common.cancel'), type: 'warning' },
    )
  } catch { return }
  revealingVarId.value = v.id
  try {
    const res = await revealEncryptedVariable(v.id)
    const plainValue = res.data.value
    revealedVarKeys.value[v.id] = { value: plainValue, countdown: 30 }
    // 倒计时
    if (revealTimers.value[v.id]) clearInterval(revealTimers.value[v.id])
    revealTimers.value[v.id] = setInterval(() => {
      const entry = revealedVarKeys.value[v.id]
      if (!entry) { clearInterval(revealTimers.value[v.id]); return }
      entry.countdown--
      if (entry.countdown <= 0) {
        clearInterval(revealTimers.value[v.id])
        delete revealedVarKeys.value[v.id]
        delete revealTimers.value[v.id]
      }
    }, 1000)
  } catch {
    msgError($t('settings.getPlaintextFailed'))
  } finally {
    revealingVarId.value = null
  }
}

async function loadVariables() {
  loadingVariables.value = true
  try {
    const res = await listVariables(projectId.value)
    variables.value = res.data.items
  } catch {
    variables.value = []
  } finally {
    loadingVariables.value = false
  }
}

function openAddVarDialog() {
  newVar.key = ''
  newVar.value = ''
  newVar.scope = 'project'
  newVar.encrypted = false
  showVarDialog.value = true
  editingVar.value = null
}

function openEditVarDialog(v: Variable) {
  editingVar.value = {
    id: v.id,
    key: v.key,
    value: v.value,
    scope: v.scope,
    scope_id: v.scope_id,
    encrypted: v.encrypted,
    description: v.description,
  }
  showVarDialog.value = true
}

const saveVarDialog = () => varLock.run(async () => {
  const data = editingVar.value
  if (!data) {
    // 新增模式
    const key = newVar.key.trim()
    if (!key) { msgWarning($t('settings.varKeyRequired')); return }
    try {
      await upsertVariable(projectId.value, {
        key,
        value: newVar.value,
        scope: newVar.scope,
        encrypted: newVar.encrypted,
      })
      msgSuccess($t('settings.varCreated'))
      showVarDialog.value = false
      await loadVariables()
    } catch {
      msgError($t('settings.varSaveFailed'))
    }
  } else {
    // 编辑模式
    try {
      await upsertVariable(projectId.value, {
        id: data.id,
        key: data.key,
        value: data.value,
        scope: data.scope,
        encrypted: data.encrypted,
        description: data.description,
      })
      msgSuccess($t('settings.varUpdated'))
      showVarDialog.value = false
      await loadVariables()
    } catch {
      msgError($t('settings.varSaveFailed'))
    }
  }
})

async function deleteVar(v: Variable) {
  try {
    await ElMessageBox.confirm($t('settings.deleteVarConfirm', { key: v.key }), $t('common.tip'), { type: 'warning' })
  } catch { return }
  try {
    await deleteVariable(projectId.value, v.id)
    msgSuccess($t('settings.varDeleted'))
    await loadVariables()
  } catch {
    msgError($t('settings.varDeleteFailed'))
  }
}

function scopeLabel(s: VariableScope): string {
  return ({ global: $t('settings.scopeGlobal'), project: $t('settings.scopeProject'), environment: $t('settings.scopeEnvironment'), scene: $t('settings.scopeScene'), case: $t('settings.scopeCase') } as Record<string, string>)[s] || s
}

// ── 变量引用追踪 ──
const showRefDialog = ref(false)
const refVarKey = ref('')
const varRefs = ref<VariableReference[]>([])
const loadingRefs = ref(false)
const refDialogTitle = computed(() => $t('settings.refDialogTitle', { key: refVarKey.value }))

async function showVarReferences(v: Variable) {
  refVarKey.value = v.key
  showRefDialog.value = true
  loadingRefs.value = true
  try {
    const res = await getVariableReferences(projectId.value, v.key)
    varRefs.value = (res as { data?: VariableReference[] }).data ?? (res as VariableReference[]) ?? []
  } catch {
    varRefs.value = []
  } finally {
    loadingRefs.value = false
  }
}

function navigateToRef(ref: VariableReference) {
  if (ref.type === 'step' && ref.scene_id) {
    void router.push(`/projects/${projectId.value}/scenes/${ref.scene_id}`)
  } else if (ref.type === 'case') {
    void router.push(RoutePaths.caseDetail(projectId.value, ref.id))
  }
}

function formatTime(iso: string): string {
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

// 监听 tab 变化
watch(activeTab, (v) => {
  if (v === 'variables') void loadVariables()
})

onMounted(reloadProjectInfo)

onUnmounted(() => {
  for (const timer of Object.values(revealTimers.value)) {
    clearInterval(timer)
  }
  revealTimers.value = {}
})
</script>

<style scoped>
.muted { color: var(--text-muted); font-size: var(--text-xs); }
.page-foot { display: flex; justify-content: flex-end; }

/* 变量明文显示 */
.var-value-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.var-countdown {
  color: var(--warning-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  min-width: 24px;
}
.form-error {
  font-size: var(--text-xs);
  color: var(--error-text);
  margin-top: var(--space-1);
}
</style>

<style src="./SettingsView.css"></style>
