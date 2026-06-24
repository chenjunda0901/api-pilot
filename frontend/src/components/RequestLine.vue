<template>
  <div class="request-line">
    <!-- ===== 统一操作栏 ===== -->
    <div class="unified-bar">
      <!-- 方法选择器 — 渐变背景 -->
      <el-dropdown size="small" trigger="click" class="method-selector">
        <span class="method-badge-g" :class="api.method.toLowerCase()">
          {{ api.method }}
          <ChevronDown :size="12" />
        </span>
        <template #dropdown>
          <el-dropdown-item v-for="m in httpMethods" :key="m" @click="api.method = m">
            <span class="method-option" :class="m.toLowerCase()">{{ m }}</span>
          </el-dropdown-item>
        </template>
      </el-dropdown>

      <span class="bar-sep"></span>

      <!-- Domain 前缀 -->
      <el-dropdown
        v-if="envStore.currentServiceUrl"
        size="small"
        trigger="click"
        class="domain-prefix"
      >
        <span class="domain-badge">
          {{ envStore.resolvedServiceUrl }}
          <ChevronDown :size="12" />
        </span>
        <template #dropdown>
          <el-dropdown-item
            v-for="svc in envStore.currentEnvServices"
            :key="svc.url"
            :class="{ 'domain-active': svc.url === envStore.currentServiceUrl }"
            @click="envStore.switchService(svc.url)"
          >
            <span class="domain-option">{{ envStore.resolveUrl(svc.url) }}</span>
          </el-dropdown-item>
        </template>
      </el-dropdown>
      <span
        v-else
        class="domain-empty"
        @click="$router.push(`/projects/${projectId}/settings`)"
        title="前往环境配置"
      >
        未配置服务地址
      </span>

      <span class="bar-sep"></span>

      <!-- URL 输入 — 增强样式 -->
      <div class="url-wrapper">
        <el-input
          :model-value="api.path"
          @update:model-value="onPathChange"
          size="small"
          placeholder="输入请求路径，如 /api/login"
          class="url-editor"
          :class="{ 'url-invalid': pathValidation.error }"
        />
        <span v-if="api.path && !pathValidation.valid" class="path-status-icon error" :title="pathValidation.error">
          <AlertCircle :size="14" />
        </span>
        <span v-else-if="api.path && pathValidation.valid" class="path-status-icon ok" title="路径格式正确">
          <CheckCircle :size="14" />
        </span>
      </div>

      <!-- 操作按钮组 -->
      <div class="action-group">
        <el-button
          type="primary"
          size="small"
          @click="$emit('send')"
          :loading="loading"
          class="btn-send-g"
          :class="{ sending: loading }"
          title="发送请求 (Ctrl+Enter)"
        >
          <Send :size="14" />
          <span>发送</span>
        </el-button>
        <div v-if="canEdit" class="btn-save-group">
          <el-button
            size="small"
            :loading="loading"
            class="btn-save-main"
            @click="$emit('save')"
            title="保存 (Ctrl+S)"
          >
            <Save :size="14" />
            <span>保存</span>
          </el-button>
          <el-dropdown trigger="click" @command="handleSaveCommand" class="btn-save-dropdown">
            <el-button size="small" class="btn-save-arrow" aria-label="保存选项">
              <ChevronDown :size="14" />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="save-as-case" :disabled="!apiSaved">
                  另存为用例
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <el-dropdown size="small" trigger="click">
          <el-button size="small" class="btn-more" aria-label="更多操作">
            <MoreHorizontal :size="14" />
          </el-button>
          <template #dropdown>
            <el-dropdown-item v-if="showAddToScene" @click="$emit('add-to-scene')">添加到场景</el-dropdown-item>
            <el-dropdown-item @click="$emit('generate-code')">生成代码</el-dropdown-item>
            <el-dropdown-item @click="$emit('clone-api')">克隆接口</el-dropdown-item>
            <el-dropdown-item @click="$emit('import-curl')">cURL 导入</el-dropdown-item>
          </template>
        </el-dropdown>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import { Send, Save, MoreHorizontal, ChevronDown, AlertCircle, CheckCircle } from "lucide-vue-next"
import { useEnvStore } from "../stores/envStore"

const envStore = useEnvStore()

interface RequestLineApi {
  method: string
  path: string
  params?: { key: string; value: string; enabled?: boolean }[]
  headers?: { key: string; value: string; enabled?: boolean }[]
  body?: { type: string; content?: string | unknown[] }
}

const props = defineProps<{
  api: RequestLineApi
  loading?: boolean
  apiSaved?: boolean
  projectId?: number
  canEdit?: boolean
  showAddToScene?: boolean
}>()

const emit = defineEmits<{
  send: []
  save: []
  "save-as-case": []
  "generate-code": []
  "clone-api": []
  "import-curl": []
  "add-to-scene": []
  "update:name": [value: string]
}>()

const httpMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

// ── 路径格式实时验证 ──
interface PathValidation {
  valid: boolean
  error: string
}

const pathValidation = computed<PathValidation>(() => {
  const path = props.api?.path || ''
  if (!path) return { valid: false, error: '' }

  // 必须以 / 开头
  if (!path.startsWith('/')) {
    return { valid: false, error: '路径必须以 / 开头' }
  }

  // 检测非法字符：空格、?、#、& 等
  const illegalChars = /[\s?#&<>\\|^`"'$;,!()*]/
  if (illegalChars.test(path)) {
    const match = path.match(illegalChars)
    const char = match ? match[0] : ''
    const charDesc = char === ' ' ? '空格' : char
    return { valid: false, error: `路径包含非法字符 "${charDesc}"` }
  }

  // 检查是否只包含合法字符（字母、数字、-、_、/、{}、.、@、%、~、+、=、:）
  // 允许路径参数 {id} 和变量 {{var}}
  const validChars = /^\/[a-zA-Z0-9\-_/{}[\].@%~+=:]*$/
  if (!validChars.test(path)) {
    return { valid: false, error: '路径包含不支持的字符，仅允许字母、数字、-、_、/、{}、.、@、%、~、+、=:' }
  }

  // 检查 {} 参数标记是否闭合
  const openSingle = (path.match(/\{/g) || []).length
  const closeSingle = (path.match(/\}/g) || []).length
  // 排除 {{}} 变量标记后检查
  const openDouble = (path.match(/\{\{/g) || []).length
  const closeDouble = (path.match(/\}\}/g) || []).length
  const singleOpen = openSingle - openDouble * 2
  const singleClose = closeSingle - closeDouble * 2
  if (singleOpen !== singleClose) {
    return { valid: false, error: '{} 参数标记未闭合' }
  }

  // 检查 {{variable}} 格式是否闭合
  if (openDouble !== closeDouble) {
    return { valid: false, error: '{{}} 变量标记未闭合' }
  }

  return { valid: true, error: '' }
})

function onPathChange(value: string) {
  if (props.api) {
    props.api.path = value
  }
}

function handleSaveCommand(cmd: string) {
  if (cmd === "save-as-case") {
    emit("save-as-case")
  }
}
</script>

<style scoped>
.request-line {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0;
  background: transparent;
  flex-shrink: 0;
}

.unified-bar {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0;
  min-width: 0;
  min-height: 36px;
  overflow: hidden;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  transition: border-color var(--duration-fast) var(--ease-smooth), box-shadow var(--duration-fast) var(--ease-smooth);
}

/* ── 统一控件高度 36px ── */
.unified-bar :deep(.el-select),
.unified-bar :deep(.el-input),
.unified-bar :deep(.el-button) {
  height: 36px;
}
.unified-bar :deep(.el-select .el-input__wrapper),
.unified-bar :deep(.el-input .el-input__wrapper) {
  height: 36px;
  box-sizing: border-box;
}
.unified-bar :deep(.el-select .el-input__inner) {
  height: 34px;
  line-height: 34px;
}

.unified-bar:focus-within {
  border-color: var(--primary-400);
}

.unified-bar:hover {
  border-color: var(--border-strong);
}

/* ── 分隔线 ── */
.bar-sep {
  width: 1px;
  height: 20px;
  background: var(--border-subtle);
  flex-shrink: 0;
  align-self: center;
}

/* ── 方法选择器 — 增强样式 ── */
.method-selector {
  flex: 0 0 auto;
}

.method-selector :deep(.el-dropdown__trigger) {
  display: flex;
  align-items: center;
}

.method-badge-g {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 16px;
  height: 36px;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  cursor: pointer;
  white-space: nowrap;
  line-height: 1;
  transition: all var(--duration-fast) var(--ease-smooth);
  box-shadow: inset 0 1px 0 var(--color-white-alpha-10);
}

.method-badge-g.get {
  background: var(--method-get-bg);
  color: var(--method-get-text);
  border-right: 1px solid var(--method-get-border);
}

.method-badge-g.post {
  background: var(--method-post-bg);
  color: var(--method-post-text);
  border-right: 1px solid var(--method-post-border);
}

.method-badge-g.put {
  background: var(--method-put-bg);
  color: var(--method-put-text);
  border-right: 1px solid var(--method-put-border);
}

.method-badge-g.patch {
  background: var(--method-patch-bg);
  color: var(--method-patch-text);
  border-right: 1px solid var(--method-patch-border);
}

.method-badge-g.delete {
  background: var(--method-delete-bg);
  color: var(--method-delete-text);
  border-right: 1px solid var(--method-delete-border);
}

.method-badge-g.head {
  background: var(--method-head-bg);
  color: var(--method-head-text);
  border-right: 1px solid var(--method-head-border);
}

.method-badge-g.options {
  background: var(--method-options-bg);
  color: var(--method-options-text);
  border-right: 1px solid var(--method-options-border);
}

.method-badge-g:hover {
  filter: brightness(1.08);
  box-shadow: inset 0 1px 0 var(--color-white-alpha-15), 0 2px 8px var(--color-neutral-alpha-08);
}

.method-option {
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  font-size: var(--text-sm);
}

/* ── Domain 前缀 ── */
.domain-prefix {
  flex: 0 0 auto;
}
.domain-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  height: 36px;
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  font-family: var(--font-mono);
  color: var(--text-muted);
  cursor: pointer;
  line-height: 1;
  background: transparent;
  border-radius: 0;
  transition: color var(--duration-fast) var(--ease-smooth), background var(--duration-fast) var(--ease-smooth);
}
.domain-badge:hover {
  color: var(--text-secondary);
  background: var(--surface-hover);
}
.domain-empty {
  color: var(--text-disabled);
  font-style: italic;
  font-size: var(--text-xs);
}
:deep(.domain-active) {
  color: var(--primary-600);
}

/* ── URL 输入 — 增强样式（44px 高度） ── */
.url-wrapper {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  position: relative;
  background: transparent;
  border-radius: 0;
  margin: 0;
  overflow: hidden;
  transition: box-shadow var(--duration-base) var(--ease-smooth);
}

.unified-bar:focus-within .url-wrapper {
  box-shadow: none;
}

.url-editor {
  width: 100%;
  min-width: 0;
}

.url-editor :deep(.el-input) {
  width: 100%;
  min-width: 0;
}

.url-editor :deep(.el-input__wrapper) {
  border-radius: 0;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  height: 36px;
  box-shadow: none;
  background: transparent;
  border: none;
  min-width: 0;
  width: 100%;
  padding-left: var(--space-3);
  padding-right: 32px;
}

.url-editor :deep(.el-input__inner) {
  color: var(--text-primary);
  min-width: 0;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}

.url-editor :deep(.vai-preview) {
  min-height: 32px;
  padding: 4px var(--space-3);
  border: none;
  border-radius: 0;
  background: transparent;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}

.url-editor :deep(.vai-var-tag) {
  font-size: var(--text-xs);
  padding: 2px 6px;
  height: 22px;
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  border: 1px solid var(--color-primary-alpha-16);
  border-radius: var(--radius-xs);
}

/* ── 路径验证状态 ── */
.url-editor.url-invalid :deep(.el-input__wrapper) {
  border-color: var(--error) !important;
  box-shadow: 0 0 0 2px var(--color-error-alpha-08) !important;
}
.path-status-icon {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-smooth);
}
.path-status-icon.error {
  color: var(--error);
  cursor: help;
}
.path-status-icon.ok {
  color: var(--success);
}

/* ── 操作按钮组 ── */
.action-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 0 0 auto;
  flex-shrink: 0;
  padding: 0 var(--space-3);
  height: 100%;
  border-left: 1px solid var(--color-neutral-alpha-06);
  background: linear-gradient(90deg, var(--surface-hover) 0%, transparent 100%);
}

.action-group :deep(.el-button) {
  height: 36px !important;
  padding: 0 var(--space-2-5) !important;
  border-radius: var(--radius-sm);
}

/* 发送按钮 — 主色背景，悬停效果增强 */
:deep(.btn-send-g) {
  background: var(--primary-500);
  border: none;
  border-radius: var(--radius-md);
  font-weight: var(--weight-bold);
  font-size: var(--text-sm);
  padding: 0 20px !important;
  min-width: 80px;
  height: 36px !important;
  color: var(--text-inverse);
  box-shadow:
    0 2px 8px var(--color-primary-alpha-30),
    0 1px 3px var(--color-neutral-alpha-08);
  transition: all var(--duration-fast) var(--ease-smooth);
  position: relative;
  overflow: hidden;
}

:deep(.btn-send-g)::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, var(--color-white-alpha-20) 0%, transparent 60%);
  opacity: 0;
  transition: opacity var(--duration-base);
  border-radius: inherit;
}

:deep(.btn-send-g:hover)::before {
  opacity: 1;
}

:deep(.btn-send-g:hover) {
  background: var(--primary-400);
  box-shadow:
    0 4px 14px var(--color-primary-alpha-35),
    0 2px 6px var(--color-neutral-alpha-10);
  transform: translateY(-1px);
}

:deep(.btn-send-g:active) {
  transform: translateY(0) scale(0.98);
  box-shadow: 0 2px 6px var(--color-primary-alpha-20);
}

:deep(.btn-send-g.sending) {
  animation: send-pulse 1.2s ease-in-out infinite;
}

@keyframes send-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}

/* 保存按钮组 */
.btn-save-group {
  display: flex;
  align-items: center;
}
:deep(.btn-save-main) {
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-right: none;
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  font-size: var(--text-sm);
  transition: all var(--duration-fast) var(--ease-smooth);
}
:deep(.btn-save-main:hover) {
  background: var(--surface-selected);
  color: var(--text-primary);
  border-color: var(--primary-300);
}
:deep(.btn-save-main span) {
  font-weight: var(--weight-medium);
  font-size: var(--text-xs);
}
:deep(.btn-save-arrow) {
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  padding: 0 calc(var(--space-2) - 2px);
  min-width: unset;
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-left: none;
  color: var(--text-secondary);
  transition: all var(--duration-fast) var(--ease-smooth);
}
:deep(.btn-save-arrow:hover) {
  background: var(--surface-selected);
  color: var(--text-primary);
  border-color: var(--primary-300);
}

/* 更多按钮 */
:deep(.btn-more) {
  background: transparent;
  border: none;
  color: var(--text-muted);
  padding: 0 var(--space-1-5);
  transition: all var(--duration-fast) var(--ease-smooth);
}
:deep(.btn-more:hover) {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

/* ── 暗色模式 ── */
html.dark .request-line {
  background: var(--surface-card);
}
html.dark .method-badge-g {
  color: var(--text-on-primary);
}
html.dark .unified-bar:focus-within {
  border-color: var(--primary-400);
  box-shadow: var(--shadow-xs), 0 0 0 3px var(--color-success-alpha-10);
}
html.dark .unified-bar:hover {
  border-color: var(--primary-500);
}
html.dark .domain-badge {
  background: transparent;
  color: var(--text-muted);
}
html.dark .domain-empty {
  color: var(--text-disabled);
}
html.dark .domain-empty:hover {
  color: var(--primary-400);
}
html.dark .action-group {
  border-left-color: var(--color-white-alpha-06);
  background: linear-gradient(90deg, var(--color-neutral-alpha-60) 0%, transparent 100%);
}
html.dark :deep(.btn-send-g) {
  background: var(--primary-500);
  box-shadow:
    0 2px 10px var(--color-primary-alpha-24),
    inset 0 1px 0 var(--color-white-alpha-08);
}
html.dark :deep(.btn-send-g:hover) {
  background: var(--primary-400);
  box-shadow:
    0 4px 18px var(--color-primary-alpha-30),
    0 2px 6px var(--color-black-alpha-16);
}
</style>
