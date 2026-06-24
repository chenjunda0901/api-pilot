<template>
  <div class="env-manager">
    <div class="env-switcher">
      <el-radio-group v-model="activeEnvId" size="small" @change="switchEnv">
        <el-radio-button v-for="env in environments" :key="env.id" :value="env.id">
          {{ env.name }}
          <el-tag v-if="env.is_default" size="small" type="success" style="margin-left:4px">Default</el-tag>
        </el-radio-button>
      </el-radio-group>
      <el-button size="small" @click="showCreate = true">+ New</el-button>
      <el-popconfirm v-if="activeEnv && !activeEnv.is_default" title="删除后不可恢复，确定要删除该环境吗？" confirm-button-text="确定删除" cancel-button-text="取消" @confirm="deleteEnv">
        <template #reference>
          <el-button size="small" type="danger" plain>删除环境</el-button>
        </template>
      </el-popconfirm>
    </div>

    <div v-if="activeEnv" class="variables-editor">
      <!-- Base URL -->
      <div class="env-section">
        <div class="env-section-title">Base URL</div>
        <el-input v-model="activeEnvForm.base_url" size="small" placeholder="https://api.example.com" :class="{ 'is-error': errors.base_url }" @blur="saveEnvField('base_url')" />
        <div v-if="errors.base_url" class="field-error">{{ errors.base_url }}</div>
      </div>

      <!-- 认证配置 -->
      <div class="env-section">
        <div class="env-section-title">认证配置</div>
        <el-radio-group v-model="authType" size="small" @change="onAuthTypeChange">
          <el-radio-button value="none">无认证</el-radio-button>
          <el-radio-button value="bearer">Bearer Token</el-radio-button>
          <el-radio-button value="basic">Basic Auth</el-radio-button>
          <el-radio-button value="apikey">API Key</el-radio-button>
        </el-radio-group>

        <div v-if="authType === 'bearer'" class="auth-form">
          <el-input v-model="authForm.token" size="small" placeholder="输入 Bearer Token" @blur="saveAuthConfig" />
        </div>

        <div v-if="authType === 'basic'" class="auth-form">
          <el-input v-model="authForm.username" size="small" placeholder="用户名" @blur="saveAuthConfig" />
          <el-input v-model="authForm.password" size="small" type="password" placeholder="密码" show-password @blur="saveAuthConfig" />
        </div>

        <div v-if="authType === 'apikey'" class="auth-form">
          <el-input v-model="authForm.key" size="small" placeholder="Key 名称（如 X-API-Key）" @blur="saveAuthConfig" />
          <el-input v-model="authForm.value" size="small" placeholder="Key 值" @blur="saveAuthConfig" />
          <el-select v-model="authForm.in_" size="small" placeholder="位置" @change="saveAuthConfig">
            <el-option label="Header" value="header" />
            <el-option label="Query" value="query" />
          </el-select>
        </div>
      </div>

      <div class="var-toolbar">
        <el-button size="small" @click="addVariable">+ Add Variable</el-button>
        <el-button size="small" @click="importDotenv">Import .env</el-button>
        <el-button size="small" @click="exportDotenv">Export .env</el-button>
      </div>
      <el-table :data="variables" border size="small">
        <el-table-column label="Key" width="200">
          <template #default="{ row }">
            <el-input v-if="row._editing" v-model="row.key" size="small" />
            <span v-else style="font-family:monospace">{{ row.key }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Value">
          <template #default="{ row }">
            <div v-if="row._editing" style="display:flex;gap:4px;align-items:center">
              <el-input v-model="row.value" size="small" :type="row._secret ? 'password' : 'text'" />
              <el-switch v-model="row._secret" size="small" />
            </div>
            <span v-else :style="{fontFamily:'monospace',color:row._secret?'var(--text-muted)':'inherit'}">
              {{ row._secret ? '••••••••' : row.value }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Description" width="200">
          <template #default="{ row }">
            <el-input v-if="row._editing" v-model="row.description" size="small" />
            <span v-else>{{ row.description }}</span>
          </template>
        </el-table-column>
        <el-table-column width="140" align="center">
          <template #default="{ row }">
            <el-button v-if="row._editing" size="small" type="success" link @click="saveVar(row)">Save</el-button>
            <el-button v-else size="small" link @click="row._editing = true">Edit</el-button>
            <el-button size="small" type="danger" link @click="removeVar(row)">Del</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showCreate" title="New Environment" width="400px">
      <el-form :model="newEnvForm" label-width="80px">
        <el-form-item label="Name"><el-input v-model="newEnvForm.name" /></el-form-item>
        <el-form-item label="Base URL"><el-input v-model="newEnvForm.base_url" placeholder="https://api.example.com" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">Cancel</el-button>
        <el-button type="primary" @click="createEnv" :disabled="!newEnvForm.name">Create</el-button>
      </template>
    </el-dialog>

    <input ref="fileInput" type="file" accept=".env" style="display:none" @change="handleFileImport" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { msgSuccess, msgError, msgWarning } from '@/utils/message'
import { logger } from '@/utils/logger'
import request from '@/api/request'
import { upsertEnvironmentVariable } from '@/api/environments'
import { useFormValidation } from '@/composables/useFormValidation'

const _props = defineProps<{ projectId: number }>()
const emit = defineEmits<{ select: [envId: number] }>()

interface EnvVariable {
  key: string
  value: string
  description?: string
  enabled?: boolean
  _editing?: boolean
  _secret?: boolean
}

interface EnvItem {
  id: number
  name: string
  base_url?: string
  auth_config?: {
    type?: string
    token?: string
    username?: string
    password?: string
    key?: string
    value?: string
    in?: string
  } | null
  variables?: EnvVariable[] | string
  is_default?: boolean
  [key: string]: unknown
}

const environments = ref<EnvItem[]>([])
const activeEnvId = ref<number>()
const variables = ref<EnvVariable[]>([])
const showCreate = ref(false)
const newEnvForm = ref({ name: '', base_url: '' })
const fileInput = ref<HTMLInputElement>()

// 认证配置
const authType = ref('none')
const authForm = reactive({
  token: '',
  username: '',
  password: '',
  key: '',
  value: '',
  in_: 'header',
})

// 环境编辑表单
const activeEnvForm = reactive({
  base_url: '',
})

const { errors, validate } = useFormValidation(
  () => activeEnvForm,
  { base_url: { url: '请输入合法的 URL' } }
)

const activeEnv = computed(() => environments.value.find(e => e.id === activeEnvId.value))

function switchEnv(id: number) {
  activeEnvId.value = id
  loadVariables()
  loadAuthConfig()
  emit('select', id)
}

function loadVariables() {
  if (!activeEnv.value) { variables.value = []; return }
  try {
    const vars = activeEnv.value.variables
    variables.value = (typeof vars === 'string' ? JSON.parse(vars) : (vars || [])).map((v: EnvVariable) => ({
      ...v, _editing: false, _secret: !!v._secret
    }))
  } catch (err) { logger.error('[EnvironmentManager] parse variables failed:', err); msgError('解析变量失败'); variables.value = [] }
}

function loadAuthConfig() {
  if (!activeEnv.value) return
  const config = activeEnv.value.auth_config
  activeEnvForm.base_url = activeEnv.value.base_url || ''

  if (!config || !config.type || config.type === 'none') {
    authType.value = 'none'
    Object.assign(authForm, { token: '', username: '', password: '', key: '', value: '', in_: 'header' })
  } else {
    authType.value = config.type
    authForm.token = config.token || ''
    authForm.username = config.username || ''
    authForm.password = config.password || ''
    authForm.key = config.key || ''
    authForm.value = config.value || ''
    authForm.in_ = config.in || 'header'
  }
}

function onAuthTypeChange() {
  void saveAuthConfig()
}

async function saveAuthConfig() {
  if (!activeEnv.value) return
  let config: EnvItem['auth_config'] = null
  if (authType.value === 'bearer') {
    config = { type: 'bearer', token: authForm.token }
  } else if (authType.value === 'basic') {
    config = { type: 'basic', username: authForm.username, password: authForm.password }
  } else if (authType.value === 'apikey') {
    config = { type: 'apikey', key: authForm.key, value: authForm.value, in: authForm.in_ }
  }
  try {
    await request.put(`/projects/${_props.projectId}/environments/${activeEnv.value.id}`, {
      auth_config: config,
    }, { _silent403: true })
    if (activeEnv.value) activeEnv.value.auth_config = config
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 403) {
      msgWarning('认证配置需要写权限才能修改')
    }
  }
}

async function saveEnvField(field: string) {
  if (!validate()) return
  if (!activeEnv.value) return
  try {
    await request.put(`/projects/${_props.projectId}/environments/${activeEnv.value.id}`, {
      [field]: (activeEnvForm as Record<string, unknown>)[field],
    }, { _silent403: true })
    if (activeEnv.value) (activeEnv.value as Record<string, unknown>)[field] = (activeEnvForm as Record<string, unknown>)[field]
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 403) {
      msgWarning('环境配置需要写权限才能修改')
    }
  }
}

function addVariable() {
  variables.value.push({ key: '', value: '', description: '', enabled: true, _editing: true, _secret: false })
}

function cleanVariables() {
  return variables.value.map(({ key, value, description, enabled, _secret }) => ({
    key, value, description: description ?? '', enabled: enabled ?? true, _secret: _secret ?? false,
  }))
}

async function persistVariables() {
  if (!activeEnv.value) return
  try {
    // 使用 upsert 端点（仅需读权限），逐个保存变量
    const envId = activeEnv.value.id
    const validVars = variables.value.filter(v => v.key?.trim())
    await Promise.all(
      validVars.map(v => upsertEnvironmentVariable(_props.projectId, envId, v.key, v.value || ''))
    )
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 403) {
      msgWarning('保存变量需要项目读权限')
    }
  }
}

function saveVar(row: EnvVariable) {
  row._editing = false
  void persistVariables()
  msgSuccess('Variable saved')
}

function removeVar(row: EnvVariable) {
  const idx = variables.value.indexOf(row)
  if (idx >= 0) {
    variables.value.splice(idx, 1)
    void persistVariables()
    msgSuccess('Variable deleted')
  }
}

function importDotenv() {
  fileInput.value?.click()
}

function handleFileImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  void file.text().then(text => {
    for (const line of text.trim().split('\n')) {
      if (line && !line.startsWith('#') && line.includes('=')) {
        const eqIdx = line.indexOf('=')
        variables.value.push({ key: line.slice(0, eqIdx).trim(), value: line.slice(eqIdx + 1).trim(), description: '', enabled: true, _editing: false, _secret: false })
      }
    }
    msgSuccess('Imported')
  })
}

function exportDotenv() {
  const content = variables.value.filter(v => v.key && v.enabled !== false).map(v => `${v.key}=${v.value}`).join('\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (activeEnv.value?.name || 'environment') + '.env'
  a.click()
  URL.revokeObjectURL(url)
}

async function createEnv() {
  if (!newEnvForm.value.name) return
  try {
    await request.post(`/projects/${_props.projectId}/environments`, {
      name: newEnvForm.value.name,
      base_url: newEnvForm.value.base_url || null,
    })
    msgSuccess('Environment created')
    showCreate.value = false
    newEnvForm.value = { name: '', base_url: '' }
    await loadEnvironments()
  } catch { /* ignore */ }
}

async function deleteEnv() {
  if (!activeEnv.value) return
  try {
    await request.delete(`/projects/${_props.projectId}/environments/${activeEnv.value.id}`)
    msgSuccess('Environment deleted')
    await loadEnvironments()
  } catch (err: unknown) {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '删除失败'
    msgError(detail)
  }
}

async function loadEnvironments() {
  try {
    const res = await request.get(`/projects/${_props.projectId}/environments`)
    environments.value = res.data || []
    if (environments.value.length && !activeEnvId.value) {
      switchEnv(environments.value[0]?.id ?? 0)
    }
  } catch { environments.value = [] }
}

// 监听 activeEnv 变化同步表单
watch(() => activeEnv.value, (env) => {
  if (env) {
    activeEnvForm.base_url = env.base_url || ''
  }
}, { immediate: true })

onMounted(() => {
  void loadEnvironments()
})
</script>

<style scoped>
/* ===== 环境管理器容器 ===== */
.env-manager {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

/* 环境切换器区域 */
.env-switcher {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  padding: var(--spacing-sm);
  background: var(--surface-nested);
  border-radius: var(--radius-sm);
}

/* 环境配置区域 */
.env-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--surface-nested);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

.env-section-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
}

/* 认证配置表单 */
.auth-form {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-top: var(--spacing-sm);
}
.auth-form .el-input,
.auth-form .el-select {
  flex: 1;
  min-width: 160px;
}

/* 变量编辑器区域 */
.variables-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* 变量工具栏 */
.var-toolbar {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
}

/* ===== 交互状态 ===== */
.env-manager:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-strong);
}

/* 按钮悬停效果 */
.var-toolbar :deep(.el-button:hover) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

/* 按钮激活效果 */
.var-toolbar :deep(.el-button:active) {
  transform: translateY(0);
  transition-duration: var(--duration-fast);
}

/* 按钮焦点状态 */
.var-toolbar :deep(.el-button:focus-visible) {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}

/* 禁用状态 */
.var-toolbar :deep(.el-button:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 字段错误提示 */
.field-error {
  font-size: 12px;
  color: var(--color-danger, #f56c6c);
  margin-top: 4px;
}

/* ===== 暗色模式适配 ===== */
html.dark .env-manager {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

html.dark .env-manager:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-strong);
}

html.dark .env-switcher {
  background: var(--surface-nested);
}

html.dark .env-section {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .var-toolbar {
  background: var(--surface-muted);
}

/* 暗色模式下按钮交互 */
html.dark .var-toolbar :deep(.el-button:hover) {
  box-shadow: var(--shadow-sm);
}
</style>
