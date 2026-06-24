<template>
  <div
    class="var-aware-input"
    :class="{
      'is-focused': isFocused,
      'is-hovering': isHovering,
      'has-value': hasValue,
      'has-error': hasError
    }"
    @mouseenter="isHovering = true"
    @mouseleave="isHovering = false"
  >
    <!-- 变量下拉提示（环境变量） -->
    <transition name="var-dropdown">
      <div
        v-if="showVarDropdown && filteredEnvVars.length > 0"
        class="var-dropdown"
      >
        <div
          v-for="(v, idx) in filteredEnvVars"
          :key="v.name"
          class="var-option"
          :class="{ 'is-active': idx === activeVarIndex }"
          @click="insertVariable(v)"
          @mouseenter="activeVarIndex = idx"
        >
          <span class="var-option-icon">&#123;&#123;</span>
          <span class="var-option-name">{{ v.name }}</span>
          <span v-if="v.desc" class="var-option-desc">{{ v.desc }}</span>
        </div>
      </div>
    </transition>

    <!-- 主输入框 -->
    <div class="input-wrapper">
      <input
        ref="inputRef"
        v-model="displayValue"
        class="native-input"
        :placeholder="placeholder"
        :disabled="disabled"
        @focus="onFocus"
        @blur="onBlur"
        @keydown="onKeyDown"
        @input="onInput"
      />

      <!-- 变量标签渲染区（覆盖在输入框上方，显示文字和变量高亮） -->
      <div
        v-if="renderedSegments.length > 0"
        class="var-overlay"
        aria-hidden="true"
      >
        <template v-for="(seg, idx) in renderedSegments" :key="idx">
          <mark
            v-if="seg.type === 'var'"
            class="var-tag"
            :title="getVariableTitle(seg.name)"
          >
            <span class="var-tag-brace">{{ LEFT }}</span>{{ seg.name }}<span class="var-tag-brace">{{ RIGHT }}</span>
          </mark>
          <span v-else class="var-text-plain">{{ seg.text }}</span>
        </template>
      </div>
    </div>

    <!-- 右侧按钮组 -->
    <div class="btn-group">
      <!-- 内置变量选择器 {{ }} -->
      <el-popover
        trigger="click"
        placement="bottom-end"
        :width="340"
        :offset="4"
        persistent
      >
        <template #reference>
          <button
            class="var-picker-btn"
            :class="{ 'is-active': showBuiltinPicker }"
            title="插入内置变量（$timestamp、$guid 等）"
            @click.stop="showBuiltinPicker = !showBuiltinPicker"
          >{{ }}</button>
        </template>

        <!-- 内置变量面板 -->
        <div class="var-picker-panel">
          <div v-for="(vars, cat) in categorizedBuiltinVars" :key="cat" class="var-category">
            <div class="cat-label">{{ categoryLabels[cat] || cat }}</div>
            <div
              v-for="v in vars"
              :key="v.name"
              class="var-item"
              @click="insertBuiltinVar(v.name)"
            >
              <span class="var-name">{{ v.name }}</span>
              <span class="var-desc">{{ v.label }}</span>
              <span class="var-example">{{ v.example }}</span>
            </div>
          </div>
        </div>
      </el-popover>

      <!-- 环境变量插入按钮（原有功能） -->
      <button
        v-if="variables && variables.length > 0"
        class="var-insert-btn"
        :class="{ 'is-active': showVarDropdown }"
        :title="'插入变量'"
        @click.stop="toggleVarDropdown"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v12M2 8h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- 解析预览提示 -->
    <div v-if="hasTemplateVars" class="var-preview-tooltip">
      <span class="preview-label">解析预览:</span>
      <code class="preview-value">{{ resolvedValue }}</code>
    </div>

    <!-- ${var} 格式警告提示 -->
    <div v-if="hasDollarVarSyntax" class="var-syntax-hint">
      变量请使用 {{ LEFT }}var{{ RIGHT }} 格式，{{ DOLLAR_VAR_EXAMPLE }} 格式后端无法识别
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import {
  resolveBuiltinVars,
  getBuiltinVarsByCategory,
  CATEGORY_LABELS,
} from '../../utils/builtinVars'

// 避免模板中 {{ '{{' }} 嵌套语法导致 vue 编译器解析错误
const LEFT = '{{'
const RIGHT = '}}'
const DOLLAR_VAR_EXAMPLE = '${var}'

interface EnvVar {
  name: string
  desc?: string
}

const props = withDefaults(defineProps<{
  modelValue?: string
  variables?: EnvVar[]
  placeholder?: string
  disabled?: boolean
  hasError?: boolean
}>(), {
  modelValue: '',
  variables: () => [],
  placeholder: '请输入参数值，支持 {{变量名}} 格式',
  disabled: false,
  hasError: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'var-insert': [variable: EnvVar]
  'focus': [event: FocusEvent]
  'blur': [event: FocusEvent]
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const isFocused = ref(false)
const isHovering = ref(false)
const showVarDropdown = ref(false)
const showBuiltinPicker = ref(false)
const activeVarIndex = ref(0)
const varFilterText = ref('')

const displayValue = computed({
  get: () => props.modelValue || '',
  set: (val) => emit('update:modelValue', val)
})

const hasValue = computed(() => !!displayValue.value)

// ===== 内置变量相关 =====
const categorizedBuiltinVars = getBuiltinVarsByCategory()
const categoryLabels = CATEGORY_LABELS

// 检测是否包含内置动态变量模板（{{ $xxx }}）
const hasTemplateVars = computed(() => {
  return /\{\{\s*\$\w+/.test(displayValue.value)
})

// 检测是否使用了 ${var}（Postman 风格）格式，后端无法识别
const hasDollarVarSyntax = computed(() => /\$\{[^}]+\}/.test(displayValue.value))

// 实时解析预览值
const resolvedValue = computed(() => {
  return resolveBuiltinVars(displayValue.value)
})

function insertBuiltinVar(varName: string) {
  const val = displayValue.value || ''
  const insertText = `${LEFT}${varName}${RIGHT}`
  // 替换当前正在输入的 {{xxx 部分
  const newVal = val.replace(/\{\{(\w*)$/, insertText)
  displayValue.value = newVal
  emit('update:modelValue', newVal)
  showBuiltinPicker.value = false
  void nextTick(() => inputRef.value?.focus())
}

// ===== 环境变量相关（原有逻辑） =====

// 是否包含环境变量（用于控制 overlay 显隐）
const _hasVariables = computed(() =>
  renderedSegments.value.some((s) => s.type === 'var'),
)

// 解析变量片段用于高亮展示（匹配 {{ xxx }} 格式，包括 $ 开头的内置变量）
const renderedSegments = computed(() => {
  const val = displayValue.value
  if (!val) return []
  const regex = /\{\{([^}]+)\}\}/g
  const segs = []
  let lastIdx = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(val)) !== null) {
    if (match.index > lastIdx) {
      segs.push({ type: 'text', text: val.slice(lastIdx, match.index) })
    }
    segs.push({ type: 'var', name: match[1] })
    lastIdx = regex.lastIndex
  }
  if (lastIdx < val.length) {
    segs.push({ type: 'text', text: val.slice(lastIdx) })
  }
  return segs
})

const filteredEnvVars = computed(() => {
  if (!varFilterText.value) return props.variables
  const filter = varFilterText.value.toLowerCase()
  return props.variables.filter(
    (v) =>
      v.name.toLowerCase().includes(filter) ||
      (v.desc && v.desc.toLowerCase().includes(filter)),
  )
})

function onFocus(e: FocusEvent) {
  isFocused.value = true
  showVarDropdown.value = true
  varFilterText.value = ''
  activeVarIndex.value = 0
  emit('focus', e)
}

const blurTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function onBlur(e: FocusEvent) {
  if (blurTimer.value) clearTimeout(blurTimer.value)
  blurTimer.value = setTimeout(() => {
    isFocused.value = false
    showVarDropdown.value = false
    emit('blur', e)
  }, 200)
}

function onInput(e: Event) {
  const target = e.target as HTMLInputElement
  const val = target.value || ''
  const cursorPos = target.selectionStart ?? 0
  const textBeforeCursor = val.slice(0, cursorPos)
  const varMatch = textBeforeCursor.match(/\{\{(\w*)$/)
  if (varMatch) {
    varFilterText.value = varMatch[1]
    showVarDropdown.value = true
  } else {
    varFilterText.value = ''
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (!showVarDropdown.value || filteredEnvVars.value.length === 0) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeVarIndex.value =
      (activeVarIndex.value + 1) % filteredEnvVars.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeVarIndex.value =
      (activeVarIndex.value - 1 + filteredEnvVars.value.length) %
      filteredEnvVars.value.length
  } else if (e.key === 'Enter' && showVarDropdown.value) {
    e.preventDefault()
    insertVariable(filteredEnvVars.value[activeVarIndex.value])
  } else if (e.key === 'Escape') {
    showVarDropdown.value = false
  }
}

function insertVariable(v: EnvVar) {
  const val = displayValue.value || ''
  const insertText = `${LEFT}${v.name}${RIGHT}`
  let newVal = val.replace(/\{\{(\w*)$/, insertText)
  if (newVal === val) newVal = val + insertText  // no match, append
  displayValue.value = newVal
  emit('update:modelValue', newVal)
  emit('var-insert', v)
  showVarDropdown.value = false
  void nextTick(() => inputRef.value?.focus())
}

function toggleVarDropdown() {
  showVarDropdown.value = !showVarDropdown.value
  if (showVarDropdown.value) {
    varFilterText.value = ''
    activeVarIndex.value = 0
    void nextTick(() => inputRef.value?.focus())
  }
}

function getVariableTitle(varName: string): string {
  const envVar = props.variables.find(v => v.name === varName)
  if (envVar) return `变量: ${varName} = ${envVar.desc || '(环境变量)'}`
  if (varName.startsWith('$')) return `内置变量: ${varName}`
  return `变量: ${varName} (未找到定义)`
}

// 点击外部关闭下拉
const handleClickOutside = (e: Event) => {
  const target = e.target as HTMLElement
  if (!target.closest?.('.var-aware-input')) {
    showVarDropdown.value = false
    showBuiltinPicker.value = false
  }
}

if (typeof window !== 'undefined') {
  document.addEventListener('click', handleClickOutside)
}

// 清理事件监听器
onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    document.removeEventListener('click', handleClickOutside)
  }
  if (blurTimer.value) clearTimeout(blurTimer.value)
})
</script>

<style scoped>
/* ===========================
   CSS 变量 - 设计规范
   =========================== */
.var-aware-input {
  --input-height: 36px;
  --transition: var(--duration-base) var(--ease-smooth);

  position: relative;
  display: inline-flex;
  align-items: center;
  width: 100%;
  min-width: 120px;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
}

/* ===========================
   输入框包裹层
   =========================== */
.input-wrapper {
  position: relative;
  flex: 1;
  min-width: 0;
}

/* ===========================
   原生输入框
   =========================== */
.native-input {
  width: 100%;
  height: var(--input-height);
  padding: 0 var(--space-3);
  font-size: var(--text-base);
  line-height: var(--input-height);
  color: transparent;
  caret-color: var(--text-primary);
  background-color: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  outline: none;
  -webkit-text-fill-color: transparent;
  transition:
    border-color var(--transition),
    box-shadow var(--transition),
    background-color var(--transition);
  box-sizing: border-box;
}

.native-input::placeholder {
  color: var(--text-muted);
  font-style: italic;
}

/* 悬停状态 */
.var-aware-input.is-hovering:not(.is-focused) .native-input {
  border-color: var(--border-strong);
}

/* 焦点状态 */
.var-aware-input.is-focused .native-input {
  border-color: var(--primary-500);
  background-color: var(--color-primary-alpha-04);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-15);
}

/* 错误状态 */
.var-aware-input.has-error .native-input {
  border-color: var(--error);
  background-color: var(--color-error-alpha-08);
}

.var-aware-input.has-error.is-focused .native-input {
  box-shadow: 0 0 0 3px var(--color-error-alpha-12);
}

/* 禁用状态 */
.native-input:disabled {
  background-color: var(--surface-hover);
  color: var(--text-disabled);
  cursor: not-allowed;
  border-color: var(--border-default);
}

/* ===========================
   变量标签叠加层（视觉高亮）
   =========================== */
.var-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  pointer-events: none;
  font-size: var(--text-base);
  line-height: var(--input-height);
  white-space: nowrap;
  overflow: hidden;
  background: transparent;
  font-family: inherit;
}

.var-tag {
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-1);
  margin: 0 1px;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--primary-500);
  background-color: var(--color-primary-alpha-08);
  border: 1px solid var(--color-primary-alpha-16);
  border-radius: var(--radius-xs);
  line-height: 1.4;
  pointer-events: auto;
  cursor: help;
  vertical-align: middle;
  text-decoration: underline;
  text-decoration-color: var(--color-primary-alpha-30);
  text-underline-offset: 2px;
  transition: background-color var(--transition);
}

.var-tag:hover {
  background-color: var(--color-primary-alpha-12);
  text-decoration-color: var(--primary-500);
}

.var-tag-brace {
  opacity: 0.75;
  font-weight: var(--weight-semibold);
}

/* 普通文字段：显示正常颜色（input 已透明，overlay 全权负责显示） */
.var-text-plain {
  color: var(--text-primary);
}

/* ===========================
   变量下拉面板（环境变量）
   =========================== */
.var-dropdown {
  position: absolute;
  top: calc(100% + var(--space-1));
  left: 0;
  min-width: 220px;
  max-height: 240px;
  overflow-y: auto;
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card-hover);
  z-index: var(--z-toast);
  padding: var(--space-1) 0;
}

.var-dropdown-enter-active,
.var-dropdown-leave-active {
  transition: opacity var(--duration-fast) var(--ease-smooth), transform var(--duration-fast) var(--ease-smooth);
}

.var-dropdown-enter-from,
.var-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-1px);
}

.var-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  transition: background-color var(--transition);
}

.var-option:hover,
.var-option.is-active {
  background-color: var(--surface-hover);
}

.var-option.is-active {
  background-color: var(--color-primary-alpha-08);
}

.var-option-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 0.625rem;
  font-family: var(--font-mono);
  color: var(--primary-500);
  background-color: var(--color-primary-alpha-08);
  border-radius: var(--radius-xs);
  flex-shrink: 0;
}

.var-option-name {
  font-weight: var(--weight-medium);
  color: var(--primary-500);
}

.var-option-desc {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--text-disabled);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

/* ===========================
   右侧按钮组
   =========================== */
.btn-group {
  display: flex;
  align-items: center;
  margin-left: var(--space-1);
  flex-shrink: 0;
  gap: 2px;
}

/* ===========================
   内置变量选择按钮 {{ }}
   =========================== */
.var-picker-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--input-height);
  padding: 0 6px;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1;
  letter-spacing: -0.5px;
  transition:
    background-color var(--transition),
    border-color var(--transition),
    color var(--transition);
  flex-shrink: 0;
  white-space: nowrap;
}

.var-picker-btn:hover {
  background-color: var(--surface-hover);
  border-color: var(--primary-400);
  color: var(--primary-600);
}

.var-picker-btn.is-active {
  border-color: var(--primary-500);
  color: var(--primary-600);
  background-color: var(--color-primary-alpha-06);
}

/* ===========================
   环境变量插入按钮（原有）
   =========================== */
.var-insert-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--input-height);
  height: var(--input-height);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  color: var(--text-muted);
  cursor: pointer;
  transition:
    background-color var(--transition),
    border-color var(--transition),
    color var(--transition);
  flex-shrink: 0;
}

.var-insert-btn:hover {
  background-color: var(--surface-hover);
  border-color: var(--border-strong);
  color: var(--primary-500);
}

.var-insert-btn.is-active {
  border-color: var(--primary-500);
  color: var(--primary-500);
  background-color: var(--color-primary-alpha-04);
}

/* ===========================
   解析预览提示
   =========================== */
.var-preview-tooltip {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  margin-top: 2px;
  padding: 2px var(--space-2);
  background: var(--surface-nested, var(--color-neutral-alpha-04));
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs, 11px);
  width: 100%;
  box-sizing: border-box;
}

.preview-label {
  color: var(--text-muted);
  flex-shrink: 0;
}

.preview-value {
  color: var(--primary-600);
  font-family: var(--font-mono);
  background: var(--color-primary-alpha-08);
  padding: 0 4px;
  border-radius: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.var-syntax-hint {
  margin-top: 2px;
  padding: 2px var(--space-2);
  background: var(--color-warning-alpha-16, rgba(230, 162, 60, 0.16));
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs, 11px);
  color: var(--color-warning-text, #b88230);
  width: 100%;
  box-sizing: border-box;
}

/* ===========================
   内置变量选择面板
   =========================== */
.var-picker-panel {
  max-height: 280px;
  overflow-y: auto;
}

.var-category {
  margin-bottom: var(--space-3);
}

.var-category:last-child {
  margin-bottom: 0;
}

.cat-label {
  font-size: var(--font-size-xs, 11px);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-1-5);
  padding-bottom: var(--space-1);
  border-bottom: 1px solid var(--border-subtle, var(--border-default));
}

.var-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: var(--text-xs, 12px);
  transition: background-color 120ms ease;
}

.var-item:hover {
  background: var(--surface-hover);
}

.var-name {
  font-family: var(--font-mono);
  color: var(--primary-600);
  font-weight: var(--weight-medium);
  min-width: 90px;
  flex-shrink: 0;
}

.var-desc {
  color: var(--text-secondary);
}

.var-example {
  margin-left: auto;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  flex-shrink: 0;
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Dark Mode Overrides ===== */
html.dark .native-input {
  background-color: var(--surface-card);
  border-color: var(--border-default);
}

html.dark .var-aware-input.is-hovering:not(.is-focused) .native-input {
  border-color: var(--border-strong);
}

html.dark .var-aware-input.is-focused .native-input {
  border-color: var(--primary-400);
  background-color: var(--color-primary-alpha-06);
}

html.dark .var-aware-input.has-error .native-input {
  border-color: var(--error);
  background-color: var(--color-error-alpha-10);
}

html.dark .native-input:disabled {
  background-color: var(--surface-hover);
  color: var(--text-disabled);
  border-color: var(--border-default);
}

html.dark .var-dropdown {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .var-option:hover,
html.dark .var-option.is-active {
  background-color: var(--surface-hover);
}

html.dark .var-insert-btn {
  background-color: var(--surface-card);
  border-color: var(--border-default);
}

html.dark .var-insert-btn:hover {
  background-color: var(--surface-hover);
  border-color: var(--border-strong);
}

html.dark .var-insert-btn.is-active {
  border-color: var(--primary-400);
  color: var(--primary-400);
  background-color: var(--color-primary-alpha-06);
}

html.dark .var-picker-btn {
  background-color: var(--surface-card);
  border-color: var(--border-default);
}

html.dark .var-picker-btn:hover {
  background-color: var(--surface-hover);
  border-color: var(--primary-400);
}

html.dark .var-picker-btn.is-active {
  border-color: var(--primary-400);
  color: var(--primary-400);
  background-color: var(--color-primary-alpha-06);
}
</style>
