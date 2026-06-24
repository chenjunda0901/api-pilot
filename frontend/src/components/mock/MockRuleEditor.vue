<template>
  <div class="mock-rule-editor">
    <div class="rule-header">
      <el-input v-model="rule.name" placeholder="Rule name" class="w-name" />
      <el-input-number v-model="rule.priority" :min="0" :max="100" size="small" controls-position="right" class="w-priority" />
      <span class="field-label">Priority</span>
      <el-input-number v-model="rule.response_delay" :min="0" :max="30000" :step="100" size="small" controls-position="right" class="w-delay" />
      <span class="field-label">Delay(ms)</span>
      <el-switch v-model="rule.enabled" active-text="Enabled" size="small" />
    </div>

    <!-- 匹配配置 -->
    <div class="match-section">
      <h4>Match Config</h4>
      <div class="match-row">
        <el-select v-model="rule.match_method" size="small" class="w-method">
          <el-option label="*" value="*" />
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
          <el-option label="DELETE" value="DELETE" />
          <el-option label="PATCH" value="PATCH" />
        </el-select>
        <el-input v-model="rule.match_path" placeholder="Path pattern, e.g. /users/{id}" size="small" class="flex-1" />
      </div>
    </div>

    <!-- 条件配置 -->
    <el-collapse v-model="activeCollapse">
      <el-collapse-item title="Match Conditions" name="conditions">
        <div v-for="(cond, i) in rule.conditions" :key="i" class="condition-row">
          <el-input v-model="cond.field" placeholder="e.g. query.user_id" size="small" class="w-cond-field" />
          <el-select v-model="cond.operator" size="small" class="w-cond-op">
            <el-option label="equals" value="equals" />
            <el-option label="not equals" value="not_equals" />
            <el-option label="contains" value="contains" />
            <el-option label="not contains" value="not_contains" />
            <el-option label="greater than" value="greater_than" />
            <el-option label="less than" value="less_than" />
            <el-option label="regex" value="regex" />
            <el-option label="in list" value="in" />
            <el-option label="exists" value="exists" />
          </el-select>
          <el-input v-model="cond.value" placeholder="Expected value" size="small" class="w-cond-val" />
          <el-button type="danger" link size="small" class="btn-delete" @click="rule.conditions!.splice(i, 1)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" class="btn-add" @click="addCondition" :icon="Plus">Add Condition</el-button>
      </el-collapse-item>

      <!-- 响应配置 -->
      <el-collapse-item title="Response Config" name="response">
        <div class="response-config">
          <div class="response-fields">
            <el-radio-group v-model="responseMode" size="small">
              <el-radio-button value="static">Static Response</el-radio-button>
              <el-radio-button value="script">Script Response</el-radio-button>
            </el-radio-group>
            <el-select v-model="rule.response_status" size="small" class="w-status">
              <el-option :value="200" label="200 OK" />
              <el-option :value="201" label="201 Created" />
              <el-option :value="204" label="204 No Content" />
              <el-option :value="400" label="400 Bad Request" />
              <el-option :value="401" label="401 Unauthorized" />
              <el-option :value="403" label="403 Forbidden" />
              <el-option :value="404" label="404 Not Found" />
              <el-option :value="500" label="500 Server Error" />
            </el-select>
          </div>
          <div v-if="responseMode === 'static'" class="response-body">
            <el-input
              v-model="rule.response_body"
              type="textarea"
              :rows="8"
              placeholder="Response body (JSON or plain text)"
              class="input-mono"
            />
          </div>
          <div v-else class="response-body">
            <el-input
              v-model="rule.script"
              type="textarea"
              :rows="8"
              placeholder="Script expression, return a response object. Available: request, headers, query, body"
              class="input-mono"
            />
            <p class="script-hint">Safe sandbox. Available variables: request, headers, query, body. Built-in: len, str, int, float, bool, list, dict, min, max, sum.</p>
          </div>
        </div>
      </el-collapse-item>

      <!-- 响应头 -->
      <el-collapse-item title="Response Headers" name="headers">
        <div v-for="(val, key, i) in rule.response_headers" :key="i" class="header-row">
          <el-input :model-value="key" size="small" class="w-header-key" disabled />
          <el-input :model-value="val" size="small" class="flex-1" @update:model-value="(v: string) => updateHeader(key as string, v)" />
          <el-button type="danger" link size="small" class="btn-delete" @click="removeHeader(key as string)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button size="small" class="btn-add" @click="addHeader" :icon="Plus">Add Header</el-button>
      </el-collapse-item>
    </el-collapse>

    <div class="rule-actions">
      <el-button type="primary" @click="$emit('save', rule)" :loading="saving">Save</el-button>
      <el-button @click="$emit('cancel')">Cancel</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'

interface MockCondition {
  field: string
  operator: string
  value: string
}

interface MockRule {
  id?: number
  name: string
  enabled: boolean
  priority: number
  match_method: string
  match_path: string
  response_status: number
  response_headers: Record<string, string>
  response_body: string
  response_delay: number
  conditions: MockCondition[]
  script?: string
}

const props = withDefaults(defineProps<{
  modelValue: MockRule
  saving?: boolean
}>(), {
  saving: false,
})

const emit = defineEmits<{
  save: [rule: MockRule]
  cancel: []
  'update:modelValue': [rule: MockRule]
}>()

const rule = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const activeCollapse = ref(['conditions', 'response'])
const responseMode = computed(() => (rule.value.script ? 'script' : 'static'))

function addCondition() {
  if (!rule.value.conditions) {
    rule.value.conditions = []
  }
  rule.value.conditions.push({ field: '', operator: 'equals', value: '' })
}

function addHeader() {
  const key = prompt('Header name:')
  if (key) {
    rule.value.response_headers[key] = ''
  }
}

function updateHeader(key: string, value: string) {
  rule.value.response_headers[key] = value
}

function removeHeader(key: string) {
  delete rule.value.response_headers[key]
  rule.value.response_headers = { ...rule.value.response_headers }
}
</script>

<style scoped>
/* ==========================================
 * MockRuleEditor 组件样式
 * ==========================================
 * 使用 design tokens 确保主题一致性
 * 支持亮色/暗色模式自动适配
 *
 * 依赖系统：
 * - 间距：--spacing-*（4pt 基准）
 * - 圆角：--radius-*（4/6/8/10/12/16px）
 * - 阴影：--shadow-*（xs/sm/md/lg/xl）
 * - 色彩：--text-*, --border-*, --surface-*
 * - 动画：--duration-*, --ease-*
 * ========================================== */

/* 组件根容器：卡片风格，带边框与阴影 */
.mock-rule-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg); /* 16px — 主区块间距 */
  padding: var(--spacing-lg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); /* 8px */
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

/* 根容器 hover：增强边框与阴影 */
.mock-rule-editor:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

/* 规则头部：名称、优先级、延迟、启用开关 */
.rule-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md); /* 12px */
  flex-wrap: wrap;
}

/* 头部控件尺寸 */
.w-name { width: 200px; }
.w-priority { width: 120px; }
.w-delay { width: 140px; }

/* 字段标签：优先级、延迟等辅助文字 */
.field-label {
  font-size: var(--font-size-xs); /* 12px */
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  white-space: nowrap;
}

/* 匹配配置区域标题 */
.match-section h4 {
  margin: 0 0 var(--spacing-sm); /* 8px */
  font-size: var(--font-size-sm); /* 14px */
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}

/* 匹配行：方法选择 + 路径输入 */
.match-row {
  display: flex;
  gap: var(--spacing-sm); /* 8px */
}

/* 匹配行控件尺寸 */
.w-method { width: 100px; }
.flex-1 { flex: 1; }

/* 条件行 / 响应头行：通用行布局 */
.condition-row,
.header-row {
  display: flex;
  gap: var(--spacing-sm); /* 8px */
  margin-bottom: var(--spacing-sm);
  align-items: center;
  padding: var(--spacing-xs); /* 4px — 行内边距，扩大 hover 区域 */
  border-radius: var(--radius-sm); /* 4px */
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

/* 行 hover 高亮 */
.condition-row:hover,
.header-row:hover {
  background: var(--surface-hover);
}

/* 行 focus-within：输入框获焦时高亮整行 */
.condition-row:focus-within,
.header-row:focus-within {
  background: var(--surface-selected);
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}

/* 条件行控件尺寸 */
.w-cond-field { width: 28%; }
.w-cond-op { width: 18%; }
.w-cond-val { width: 22%; }

/* 响应头行控件尺寸 */
.w-header-key { width: 30%; }

/* 行内删除按钮：hover / focus / disabled 状态 */
.btn-delete {
  opacity: 0.5;
  transition: opacity var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
}

/* 行 hover 时显示删除按钮 */
.condition-row:hover .btn-delete,
.header-row:hover .btn-delete {
  opacity: 1;
}

/* 删除按钮 focus-visible：键盘导航可达 */
.btn-delete:focus-visible {
  opacity: 1;
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

/* 删除按钮 disabled 态 */
.btn-delete:disabled,
.btn-delete.is-disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* 添加按钮通用样式 */
.btn-add {
  margin-top: var(--spacing-sm); /* 8px */
}

/* 添加按钮 hover / active / focus / disabled 状态 */
.btn-add:hover {
  border-color: var(--border-strong);
  color: var(--text-link);
  background: var(--color-primary-alpha-04);
}

.btn-add:active {
  transform: scale(0.97);
  transition-duration: var(--duration-fast);
}

.btn-add:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.btn-add:disabled,
.btn-add.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* 响应配置区域 */
.response-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md); /* 12px */
}

/* 响应字段行：模式切换 + 状态码选择 */
.response-fields {
  display: flex;
  align-items: center;
  gap: var(--spacing-md); /* 12px */
}

/* 状态码选择器尺寸 */
.w-status {
  width: 140px;
  margin-left: var(--spacing-lg); /* 16px */
}

/* 响应体输入区域 */
.response-body {
  width: 100%;
}

/* 等宽字体输入框：代码/脚本编辑 */
.input-mono :deep(textarea) {
  font-family: var(--font-mono);
  font-size: var(--font-size-sm); /* 14px */
  line-height: var(--leading-relaxed); /* 1.65 */
}

/* 脚本提示文字：辅助说明 */
.script-hint {
  margin: var(--spacing-xs) 0 0; /* 4px */
  font-size: var(--font-size-xs); /* 12px */
  color: var(--text-muted);
  line-height: var(--leading-relaxed); /* 1.65 */
}

/* Collapse 面板 token 化覆盖 */
.mock-rule-editor :deep(.el-collapse) {
  border-color: var(--border-subtle);
}

.mock-rule-editor :deep(.el-collapse-item__header) {
  font-size: var(--font-size-sm); /* 14px */
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  background: transparent;
  border-bottom-color: var(--border-subtle);
  height: var(--height-row); /* 40px */
  transition: color var(--duration-fast) var(--ease-smooth);
}

.mock-rule-editor :deep(.el-collapse-item__header:hover) {
  color: var(--text-link);
}

.mock-rule-editor :deep(.el-collapse-item__header.is-active) {
  color: var(--text-link);
}

.mock-rule-editor :deep(.el-collapse-item__wrap) {
  background: transparent;
  border-bottom-color: var(--border-subtle);
}

.mock-rule-editor :deep(.el-collapse-item__content) {
  padding: var(--spacing-md) 0; /* 12px 0 */
  color: var(--text-primary);
}

/* 规则操作按钮区域：右对齐分隔线 */
.rule-actions {
  display: flex;
  gap: var(--spacing-sm); /* 8px */
  justify-content: flex-end;
  padding-top: var(--spacing-md); /* 12px */
  border-top: 1px solid var(--border-subtle);
}

/* ==========================================
 * 暗色模式适配
 * ========================================== */
html.dark .mock-rule-editor {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

html.dark .mock-rule-editor:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

html.dark .field-label {
  color: var(--text-secondary);
}

html.dark .script-hint {
  color: var(--text-muted);
}

/* 暗色下 collapse 面板文字色修正 */
html.dark .mock-rule-editor :deep(.el-collapse-item__header) {
  color: var(--text-primary);
  background: transparent;
}

html.dark .mock-rule-editor :deep(.el-collapse-item__content) {
  color: var(--text-primary);
}

/* 暗色下添加按钮 hover */
html.dark .btn-add:hover {
  border-color: var(--border-strong);
  color: var(--text-link);
  background: var(--color-primary-alpha-04);
}
</style>
