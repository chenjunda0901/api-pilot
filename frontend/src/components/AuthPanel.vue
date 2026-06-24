<template>
  <div class="auth-panel">
    <div class="auth-type-select">
      <label class="auth-label">认证方式</label>
      <el-radio-group v-model="authType" @change="onAuthChange">
        <el-radio value="none">无认证</el-radio>
        <el-radio value="bearer">Bearer Token</el-radio>
        <el-radio value="basic">Basic Auth</el-radio>
        <el-radio value="apikey">API Key</el-radio>
        <el-radio value="oauth2">OAuth 2.0</el-radio>
      </el-radio-group>
    </div>
    <div v-if="authType === 'bearer'" class="auth-fields">
      <VarAwareInput v-model="token" placeholder="输入 Token" size="small" @input="onAuthChange" />
    </div>
    <div v-else-if="authType === 'basic'" class="auth-fields">
      <VarAwareInput v-model="basicUsername" placeholder="用户名" size="small" class="auth-field" @input="onAuthChange" />
      <el-input v-model="basicPassword" type="password" placeholder="密码" size="small" class="auth-field" @input="onAuthChange" />
    </div>
    <div v-else-if="authType === 'apikey'" class="auth-fields">
      <div class="apikey-row">
        <el-input v-model="apiKeyName" placeholder="键" size="small" class="auth-field" @input="onAuthChange">
          <template #prepend>参数名</template>
        </el-input>
        <el-select v-model="apiKeyIn" size="small" class="auth-field" @change="onAuthChange">
          <el-option value="header">请求头</el-option>
          <el-option value="query">Query 参数</el-option>
        </el-select>
      </div>
      <VarAwareInput v-model="apiKeyValue" placeholder="值" size="small" @input="onAuthChange" />
    </div>
    <div v-else-if="authType === 'oauth2'" class="oauth2-config">
      <div class="config-row">
        <label>Grant Type</label>
        <el-select v-model="oauth2Config.grant_type" size="small">
          <el-option label="Authorization Code" value="authorization_code" />
          <el-option label="Client Credentials" value="client_credentials" />
          <el-option label="Implicit" value="implicit" />
          <el-option label="Password" value="password" />
        </el-select>
      </div>
      <div class="config-row">
        <label>Authorization URL</label>
        <el-input v-model="oauth2Config.auth_url" size="small" placeholder="https://example.com/oauth/authorize" />
      </div>
      <div class="config-row">
        <label>Token URL</label>
        <el-input v-model="oauth2Config.token_url" size="small" placeholder="https://example.com/oauth/token" />
      </div>
      <div class="config-row two-col">
        <div>
          <label>Client ID</label>
          <el-input v-model="oauth2Config.client_id" size="small" placeholder="your-client-id" />
        </div>
        <div>
          <label>Client Secret</label>
          <el-input v-model="oauth2Config.client_secret" size="small" type="password" show-password placeholder="your-client-secret" />
        </div>
      </div>
      <div class="config-row">
        <label>Scope</label>
        <el-input v-model="oauth2Config.scope" size="small" placeholder="read write (空格分隔)" />
      </div>
      <div class="oauth2-hint">
        <span>💡 提示：OAuth2 token 将在发送请求前自动获取并添加到 Authorization 头</span>
      </div>
    </div>
    <div v-else class="auth-empty">
      <p>此接口无需认证</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import VarAwareInput from './common/VarAwareInput.vue'

interface AuthConfig {
  type: 'none' | 'bearer' | 'basic' | 'apikey' | 'oauth2'
  token?: string
  username?: string
  password?: string
  keyName?: string
  keyIn?: string
  keyValue?: string
  oauth2?: {
    grant_type: string
    auth_url: string
    token_url: string
    client_id: string
    client_secret: string
    scope: string
  }
}

const props = defineProps<{ modelValue: AuthConfig }>()
const emit = defineEmits<{ 'update:modelValue': [value: AuthConfig] }>()

const authType = ref(props.modelValue?.type || 'none')
const token = ref(props.modelValue?.token || '')
const basicUsername = ref(props.modelValue?.username || '')
const basicPassword = ref(props.modelValue?.password || '')
const apiKeyName = ref(props.modelValue?.keyName || '')
const apiKeyIn = ref(props.modelValue?.keyIn || 'header')
const apiKeyValue = ref(props.modelValue?.keyValue || '')
const oauth2Config = ref({
  grant_type: props.modelValue?.oauth2?.grant_type || 'authorization_code',
  auth_url: props.modelValue?.oauth2?.auth_url || '',
  token_url: props.modelValue?.oauth2?.token_url || '',
  client_id: props.modelValue?.oauth2?.client_id || '',
  client_secret: props.modelValue?.oauth2?.client_secret || '',
  scope: props.modelValue?.oauth2?.scope || '',
})

watch(() => props.modelValue, (val) => {
  if (val) {
    authType.value = val.type || 'none'
    token.value = val.token || ''
    basicUsername.value = val.username || ''
    basicPassword.value = val.password || ''
    apiKeyName.value = val.keyName || ''
    apiKeyIn.value = val.keyIn || 'header'
    apiKeyValue.value = val.keyValue || ''
    if (val.oauth2) {
      oauth2Config.value.grant_type = val.oauth2.grant_type || 'authorization_code'
      oauth2Config.value.auth_url = val.oauth2.auth_url || ''
      oauth2Config.value.token_url = val.oauth2.token_url || ''
      oauth2Config.value.client_id = val.oauth2.client_id || ''
      oauth2Config.value.client_secret = val.oauth2.client_secret || ''
      oauth2Config.value.scope = val.oauth2.scope || ''
    }
  }
}, { deep: true })

function onAuthChange() {
  const val: AuthConfig = { type: authType.value }
  if (authType.value === 'bearer') {
    val.token = token.value
  } else if (authType.value === 'basic') {
    val.username = basicUsername.value
    val.password = basicPassword.value
  } else if (authType.value === 'apikey') {
    val.keyName = apiKeyName.value
    val.keyIn = apiKeyIn.value
    val.keyValue = apiKeyValue.value
  } else if (authType.value === 'oauth2') {
    val.oauth2 = { ...oauth2Config.value }
  }
  emit('update:modelValue', val)
}
</script>

<style scoped>
/* ==========================================
 * AuthPanel — 认证面板样式
 * ========================================== */

.auth-panel {
  padding: var(--space-2) 0;
}

/* 标签 */
.auth-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  margin-bottom: var(--space-2);
  color: var(--text-secondary);
}

/* 认证方式选择 */
.auth-type-select {
  margin-bottom: var(--space-4);
}

.auth-type-select :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.auth-type-select :deep(.el-radio-button__inner) {
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  transition: all var(--duration-fast) var(--ease-smooth);
}

.auth-type-select :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: var(--primary-500);
  border-color: var(--primary-500);
  color: var(--text-inverse);
  box-shadow: var(--shadow-sm);
}

/* 字段容器 */
.auth-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-width: 500px;
  padding: var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.apikey-row {
  display: flex;
  gap: var(--space-2);
}

.auth-field {
  flex: 1;
}

/* 空状态 */
.auth-empty p {
  color: var(--text-muted);
  font-size: var(--text-sm);
  padding: var(--space-6);
  text-align: center;
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-subtle);
}

/* OAuth2 配置 */
.oauth2-config {
  padding: var(--space-4);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  margin-top: var(--space-2);
  border: 1px solid var(--border-subtle);
}

.config-row {
  margin-bottom: var(--space-3);
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-row label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-1-5);
  font-weight: var(--weight-medium);
}

.config-row.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

/* OAuth2 提示 */
.oauth2-hint {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-info-alpha-08);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--info-text);
  border-left: 3px solid var(--info-500);
}

/* 暗色模式 */
html.dark .auth-fields {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .oauth2-config {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .oauth2-hint {
  background: var(--color-info-alpha-10);
  color: var(--info-text);
}
</style>
