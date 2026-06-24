<template>
  <el-dialog
    :model-value="modelValue"
    :title="stepBreadcrumb || '步骤详情'"
    width="860px"
    top="4vh"
    :close-on-click-modal="false"
    destroy-on-close
    class="step-detail-dialog"
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="$emit('closed')"
  >
    <template #footer>
      <div class="step-detail-footer">
        <el-button size="small" :disabled="!hasPrevStep" @click="$emit('prev')">
          <template #icon><ChevronLeft :size="14" /></template>上一步
        </el-button>
        <el-button size="small" @click="$emit('update:modelValue', false)">
          <template #icon><X :size="14" /></template>关闭
        </el-button>
        <el-button size="small" :disabled="!hasNextStep" @click="$emit('next')">
          下一步<template #icon><ChevronRight :size="14" /></template>
        </el-button>
      </div>
    </template>

    <div v-if="step" class="step-detail-body">
      <!-- Request Bar: method + domain + path -->
      <div class="detail-request-bar">
        <el-dropdown size="small" trigger="click" @command="(m: string) => $emit('update:method', m)">
          <span class="detail-method-badge" :class="(step.method || 'GET').toLowerCase()">
            {{ step.method || "GET" }} <ChevronDown :size="12" />
          </span>
          <template #dropdown>
            <el-dropdown-item v-for="m in ['GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS']" :key="m" :command="m">
              <span class="method-option" :class="m.toLowerCase()">{{ m }}</span>
            </el-dropdown-item>
          </template>
        </el-dropdown>

        <el-dropdown v-if="currentServiceUrl" size="small" trigger="click" class="detail-domain-dropdown">
          <span class="detail-domain-badge">{{ currentServiceUrl }} <ChevronDown :size="12" /></span>
          <template #dropdown>
            <el-dropdown-item
              v-for="svc in currentEnvServices" :key="svc.url"
              :class="{ 'domain-active': svc.url === currentServiceUrl }"
              @click="$emit('switch-env', svc.url)"
            >{{ svc.url }}</el-dropdown-item>
          </template>
        </el-dropdown>

        <div class="detail-path-wrapper" @click="editingUrl = true">
          <span class="detail-url-display" v-if="!editingUrl">
            <span v-for="(seg, i) in stepUrlSegments" :key="i">
              <span v-if="seg.type === 'text'" class="detail-url-text">{{ seg.value }}</span>
              <el-tag v-else-if="seg.type === 'variable'" size="small" class="detail-url-variable-tag" @click.stop>{{ displayUrlVar(seg.value) }}</el-tag>
            </span>
          </span>
          <el-input
            v-else
            ref="urlInputRef"
            :model-value="step.path"
            size="small"
            class="detail-url-editor"
            @blur="editingUrl = false"
            @change="(v: string) => { $emit('update:path', v); editingUrl = false }"
            @keydown.enter="editingUrl = false"
          />
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="detail-tabs-bar">
        <button
          v-for="tab in stepDetailTabs"
          :key="tab.key"
          class="detail-tab"
          :class="{ active: stepDetailTab === tab.key }"
          @click="$emit('update:tab', tab.key)"
        >
          {{ tab.label }}<sup v-if="tab.count" class="detail-tab-badge">{{ tab.count }}</sup>
        </button>
      </div>

      <!-- Tab Content -->
      <div class="detail-tab-content">
        <ParamsTable v-if="stepDetailTab === 'params'" :model-value="step.query_params" @update:model-value="v => $emit('update:queryParams', v)" />
        <div v-else-if="stepDetailTab === 'body'" class="body-tab">
          <BodyEditor :model-value="bodyModel" @update:model-value="v => $emit('update:body', v)" />
        </div>
        <HeadersTable v-else-if="stepDetailTab === 'headers'" :model-value="step.headers" @update:model-value="v => $emit('update:headers', v)" />
        <div v-else-if="stepDetailTab === 'assertions'" class="assertions-tab">
          <AssertionTab :model-value="step.assertions" @update:model-value="v => $emit('update:assertions', v)" />
        </div>
        <div v-else-if="stepDetailTab === 'extract'" class="extract-tab">
          <div v-if="!step.extract_vars?.length" class="tab-empty-hint">暂无变量提取</div>
          <div v-else class="extract-list">
            <div v-for="(e, i) in step.extract_vars" :key="i" class="extract-row">
              <span class="extract-index">{{ i + 1 }}</span>
              <el-select v-model="e.source" size="small" class="extract-source-select">
                <el-option label="响应体" value="body" /><el-option label="响应头" value="header" />
              </el-select>
              <template v-if="e.source === 'body' || !e.source">
                <el-input v-model="e.path" size="small" placeholder="JSONPath 表达式，如 $.data.token" class="extract-input" />
              </template>
              <template v-else>
                <el-input v-model="e.header_name" size="small" placeholder="响应头名称，如 X-Token" class="extract-input" />
              </template>
              <span class="extract-eq">=</span>
              <el-input v-model="e.variable" size="small" placeholder="变量名" class="extract-input" :class="{ 'is-error': checkDuplicate(e.variable, i) }" />
              <span v-if="checkDuplicate(e.variable, i)" class="extract-dup-warning">变量名重复</span>
              <button class="extract-del" aria-label="删除提取变量" @click="$emit('remove-extract', i)"><X :size="13" /></button>
            </div>
            <div v-if="duplicateVariables.length > 0" class="extract-warning">以下变量名存在重复: {{ duplicateVariables.join(", ") }}</div>
          </div>
          <button class="tab-add-btn" @click="$emit('add-extract')">+ 添加提取</button>
        </div>
        <div v-else-if="stepDetailTab === 'more'" class="more-tab">
          <div class="more-grid">
            <!-- 条件分支可视化编辑器 -->
            <div class="config-section">
              <label class="section-label">条件控制</label>
              <div class="condition-mode-selector">
                <label class="mode-option" :class="{ active: conditionMode === 'always' }">
                  <input type="radio" value="always" v-model="conditionMode" @change="onConditionModeChange" />
                  <span class="mode-radio"></span>
                  <span class="mode-text">始终执行</span>
                </label>
                <label class="mode-option" :class="{ active: conditionMode === 'expression' }">
                  <input type="radio" value="expression" v-model="conditionMode" @change="onConditionModeChange" />
                  <span class="mode-radio"></span>
                  <span class="mode-text">满足表达式时执行</span>
                </label>
                <label class="mode-option" :class="{ active: conditionMode === 'variable' }">
                  <input type="radio" value="variable" v-model="conditionMode" @change="onConditionModeChange" />
                  <span class="mode-radio"></span>
                  <span class="mode-text">当变量等于某值时执行</span>
                </label>
              </div>

              <!-- 表达式模式 -->
              <div v-if="conditionMode === 'expression'" class="config-row">
                <el-input :model-value="step.condition_expression" size="default" placeholder="如 __loop_index == 0 或 response.status === 200" @change="v => $emit('update:condition', v)" />
              </div>

              <!-- 变量比较模式 -->
              <div v-if="conditionMode === 'variable'" class="variable-compare-form">
                <div class="compare-row">
                  <span class="compare-prefix">当</span>
                  <el-select v-model="condVarName" size="small" filterable allow-create default-first-option placeholder="选择或输入变量名" class="compare-input">
                    <el-option-group label="环境变量">
                      <el-option v-for="v in availableVariables" :key="v" :label="v" :value="v" />
                    </el-option-group>
                    <el-option-group label="提取变量">
                      <el-option v-for="v in extractedVarNames" :key="v" :label="v" :value="v" />
                    </el-option-group>
                  </el-select>
                  <el-select v-model="condOperator" size="small" class="compare-select">
                    <el-option label="==" value="==" />
                    <el-option label="!=" value="!=" />
                    <el-option label=">" value=">" />
                    <el-option label="<" value="<" />
                    <el-option label=">=" value=">=" />
                    <el-option label="<=" value="<=" />
                    <el-option label="contains" value="contains" />
                    <el-option label="startsWith" value="startsWith" />
                    <el-option label="endsWith" value="endsWith" />
                  </el-select>
                  <el-input v-model="condVarValue" size="small" placeholder="比较值" class="compare-input" />
                  <span class="compare-suffix">时执行</span>
                </div>
                <p class="var-hint">变量示例: __dataset_username、extracted_token、__loop_index</p>
              </div>

              <!-- 条件预览 -->
              <div v-if="conditionPreview" class="condition-preview">
                <span class="preview-icon">✓</span>{{ conditionPreview }}
              </div>
            </div>

            <!-- 循环执行 -->
            <div class="config-section">
              <label class="section-label">循环执行</label>
              <div class="config-row">
                <el-input-number :model-value="step.loop_count || 1" :min="1" :max="100" size="default" class="full-width" controls-position="right" @change="v => $emit('update:loop', v && v > 1 ? v : null)" />
                <span class="config-unit">次</span>
              </div>
              <div class="config-row" style="margin-top: var(--space-2)">
                <span class="config-label-inline">循环变量名</span>
                <el-input :model-value="step.loop_variable || ''" size="small" placeholder="如 item、row" class="full-width" @change="v => $emit('update:loopVariable', v)" />
              </div>
              <p class="config-hint">循环变量可在步骤中通过 {{ loopVarHint }} 引用当前迭代数据；引用数据集列名如 {{ datasetColHint }} 可遍历数据驱动行</p>
            </div>

            <!-- 等待时间 -->
            <div class="config-section">
              <label class="section-label">等待</label>
              <div class="wait-mode-selector">
                <label class="mode-option compact" :class="{ active: waitMode === 'fixed' }">
                  <input type="radio" value="fixed" v-model="waitMode" @change="onWaitModeChange" />
                  <span class="mode-radio"></span>
                  <span class="mode-text">固定延迟</span>
                </label>
                <label class="mode-option compact" :class="{ active: waitMode === 'random' }">
                  <input type="radio" value="random" v-model="waitMode" @change="onWaitModeChange" />
                  <span class="mode-radio"></span>
                  <span class="mode-text">随机延迟</span>
                </label>
              </div>
              <div v-if="waitMode === 'fixed'" class="wait-slider-row">
                <el-slider :model-value="step.wait_duration || 0" :min="0" :max="10000" :step="100" :format-tooltip="(v: number) => v + 'ms'" size="small" @change="v => $emit('update:wait', v)" />
                <el-input-number :model-value="step.wait_duration" :min="0" :max="60000" :step="100" size="small" style="width: 100px" controls-position="right" @change="v => $emit('update:wait', v)" />
              </div>
              <div v-if="waitMode === 'random'" class="wait-random-row">
                <div class="wait-random-field">
                  <span class="config-label-inline">最小 (ms)</span>
                  <el-input-number :model-value="step.wait_min || 0" :min="0" :max="60000" :step="100" size="small" controls-position="right" @change="v => $emit('update:waitMin', v)" />
                </div>
                <div class="wait-random-field">
                  <span class="config-label-inline">最大 (ms)</span>
                  <el-input-number :model-value="step.wait_max || 1000" :min="0" :max="60000" :step="100" size="small" controls-position="right" @change="v => $emit('update:waitMax', v)" />
                </div>
              </div>
            </div>

            <!-- 步骤依赖 -->
            <div class="config-section">
              <label class="section-label">步骤依赖</label>
              <el-select :model-value="step.depends_on_step_id" placeholder="无依赖（按顺序执行）" size="default" clearable class="full-width" @change="v => $emit('update:dependsOn', v)">
                <el-option v-for="ps in previousSteps" :key="ps.id || ps._key" :value="ps.id" :label="`等待「${ps.label}」成功后执行`" />
              </el-select>
              <p class="config-hint">仅当前置步骤执行成功后才执行此步骤</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ChevronLeft, ChevronRight, X, ChevronDown } from 'lucide-vue-next'
import ParamsTable from './ParamsTable.vue'
import HeadersTable from './HeadersTable.vue'
import AssertionTab from './AssertionTab.vue'
import BodyEditor from './BodyEditor.vue'

interface ExtractVar { source: 'body' | 'header'; path?: string; header_name?: string; variable: string }
interface Step {
  method: string; path: string; query_params: Record<string, unknown>; headers: Record<string, string>; request_body: unknown
  assertions: unknown[]; extract_vars: ExtractVar[]; condition_expression: string; loop_count: number; wait_duration: number
  depends_on_step_id?: number | null; id?: number; _key?: string; label?: string
  loop_variable?: string; wait_mode?: string; wait_min?: number; wait_max?: number
}
interface EnvService { url: string }
interface UrlSegment { type: 'text' | 'variable'; value: string }
interface Tab { key: string; label: string; count?: number }
interface PrevStep { id?: number; _key?: string; label: string }

const props = defineProps<{
  modelValue: boolean
  step: Step | null
  stepBreadcrumb: string
  hasPrevStep: boolean
  hasNextStep: boolean
  currentServiceUrl: string
  currentEnvServices: EnvService[]
  stepUrlSegments: UrlSegment[]
  duplicateVariables: string[]
  stepDetailTabs: Tab[]
  stepDetailTab: string
  previousSteps?: PrevStep[]
}>()

const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'update:method': [m: string]
  'update:path': [v: string]
  'update:queryParams': [v: Record<string, unknown>]
  'update:body': [v: unknown]
  'update:headers': [v: Record<string, string>]
  'update:assertions': [v: unknown[]]
  'update:condition': [v: string]
  'update:loop': [v: number]
  'update:wait': [v: number]
  'update:dependsOn': [v: number | null]
  'update:loopVariable': [v: string]
  'update:waitMode': [v: string]
  'update:waitMin': [v: number]
  'update:waitMax': [v: number]
  'remove-extract': [i: number]
  'add-extract': []
  'update:tab': [k: string]
  prev: []
  next: []
  closed: []
  'switch-env': [url: string]
}>()

// Condition editor state
type ConditionMode = 'always' | 'expression' | 'variable'
const conditionMode = ref<ConditionMode>('always')
const condVarName = ref('')
const condOperator = ref('==')
const condVarValue = ref('')

// Wait mode state
type WaitMode = 'fixed' | 'random'
const waitMode = ref<WaitMode>('fixed')

// Available variables for condition builder
const availableVariables = computed(() => {
  const vars = new Set<string>()
  // Add common built-in variables
  vars.add('__loop_index')
  vars.add('__dataset_row_index')
  // Add dataset-prefixed variables from extract_vars
  if (props.step?.extract_vars) {
    for (const ev of props.step.extract_vars) {
      if (ev.variable) vars.add(ev.variable)
    }
  }
  return Array.from(vars).sort()
})

const extractedVarNames = computed(() => {
  const names: string[] = []
  if (props.step?.extract_vars) {
    for (const ev of props.step.extract_vars) {
      if (ev.variable) names.push(ev.variable)
    }
  }
  return names
})

const loopVarHint = computed(() => {
  const varName = props.step?.loop_variable || 'item'
  return `{{${varName}}}`
})

const datasetColHint = '{{__dataset_col1}}'

function detectConditionMode(expr: string | undefined): ConditionMode {
  if (!expr) return 'always'
  // Check if it looks like a simple variable comparison pattern
  const trimmed = expr.trim()
  if (/^\s*\w+[\w.[\]]*\s*(==|!=|>=|<=|>|<)\s*.+\s*$/.test(trimmed)) {
    // Try to parse as variable comparison
    const match = trimmed.match(/^\s*(\w+[\w.[\]]*)\s*(==|!=|>=|<=|>|<)\s*(.+)\s*$/)
    if (match) {
      condVarName.value = match[1].trim()
      condOperator.value = match[2].trim()
      condVarValue.value = match[3].trim().replace(/['"]/g, '')
      return 'variable'
    }
  }
  return 'expression'
}

watch(() => props.step?.condition_expression, (expr) => {
  conditionMode.value = detectConditionMode(expr)
}, { immediate: true })

function onConditionModeChange() {
  if (conditionMode.value === 'always') {
    emit('update:condition', '')
  } else if (conditionMode.value === 'expression') {
    // Keep existing expression or set empty
    if (!props.step?.condition_expression) {
      emit('update:condition', '')
    }
  } else if (conditionMode.value === 'variable') {
    emit('update:condition', buildConditionExpression())
  }
}

function buildConditionExpression(): string {
  if (!condVarName.value) return ''
  const op = condOperator.value
  const val = condVarValue.value
  // String operators need different syntax
  if (op === 'contains') return `'${val}' in ${condVarName.value}`
  if (op === 'startsWith') return `${condVarName.value}.startswith('${val}')`
  if (op === 'endsWith') return `${condVarName.value}.endswith('${val}')`
  return `${condVarName.value} ${op} ${val}`
}

// Watch variable compare fields and auto-update expression
watch([condVarName, condOperator, condVarValue], () => {
  if (conditionMode.value === 'variable') {
    const expr = buildConditionExpression()
    if (expr) emit('update:condition', expr)
  }
})

const conditionPreview = computed(() => {
  if (conditionMode.value === 'always') return ''
  if (conditionMode.value === 'expression') {
    return props.step?.condition_expression ? `当表达式为 true 时执行此步骤` : ''
  }
  if (conditionMode.value === 'variable' && condVarName.value) {
    const opLabels: Record<string, string> = {
      '==': '等于', '!=': '不等于', '>': '大于', '<': '小于',
      '>=': '大于等于', '<=': '小于等于',
      'contains': '包含', 'startsWith': '以...开头', 'endsWith': '以...结尾',
    }
    return `当 ${condVarName.value} ${opLabels[condOperator.value] || condOperator.value} ${condVarValue.value} 时执行此步骤`
  }
  return ''
})

const editingUrl = ref(false)
const urlInputRef = ref()

function onWaitModeChange() {
  if (waitMode.value === 'fixed') {
    // Fixed mode uses wait_duration
    emit('update:waitMode', 'fixed')
  } else {
    emit('update:waitMode', 'random')
  }
}

// Detect wait mode from step
watch(() => props.step?.wait_mode, (mode) => {
  waitMode.value = mode === 'random' ? 'random' : 'fixed'
}, { immediate: true })

const bodyModel = computed({
  get: () => {
    const str = props.step?.request_body
    if (!str || str === '{}') return { type: 'none', content: '' }
    if (typeof str === 'object' && str !== null && 'type' in (str as Record<string, unknown>)) {
      return str as { type: string; content: string }
    }
    const s = typeof str === 'string' ? str : JSON.stringify(str)
    try {
      JSON.parse(s)
      return { type: 'json', content: s }
    } catch {
      return { type: 'text', content: s }
    }
  },
  set: (v) => {
    if (!v || v.type === 'none') {
      emit('update:body', '')
    } else {
      emit('update:body', v.content || '')
    }
  },
})

function checkDuplicate(variable: string, index: number): boolean {
  return props.step?.extract_vars?.some((e, i) => e.variable === variable && i !== index) ?? false
}

function displayUrlVar(v: string) { return `{{${v}}}` }
</script>

<style scoped>
/* ===== 对话框主体 — 使用 Element Plus 全局覆盖 + 局部优化 ===== */
.step-detail-dialog :deep(.el-dialog) {
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.step-detail-dialog :deep(.el-dialog__header) {
  padding: var(--space-3) var(--space-5) var(--space-2);
  margin-right: 0;
  border-bottom: 1px solid var(--border-subtle);
}
.step-detail-dialog :deep(.el-dialog__title) {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}
.step-detail-dialog :deep(.el-dialog__body) {
  padding: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.step-detail-dialog :deep(.el-dialog__footer) {
  padding: var(--space-2) var(--space-5) var(--space-3);
  border-top: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

/* ===== 底部按钮区 ===== */
.step-detail-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

/* ===== 主体内容区 ===== */
.step-detail-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ===== 请求栏 — 方法 + 域名 + 路径 ===== */
.detail-request-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5) var(--space-2);
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-page);
}

/* HTTP 方法徽章 */
.detail-method-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: var(--space-1) var(--space-2);
  min-height: 34px;
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  cursor: pointer;
  border: 1px solid transparent;
}
.detail-method-badge.get { color: var(--method-get); background: var(--method-get-bg); }
.detail-method-badge.post { color: var(--method-post); background: var(--method-post-bg); }
.detail-method-badge.put { color: var(--method-put); background: var(--method-put-bg); }
.detail-method-badge.patch { color: var(--method-patch); background: var(--method-patch-bg); }
.detail-method-badge.delete { color: var(--method-delete); background: var(--method-delete-bg); }
.detail-method-badge.head,
.detail-method-badge.options { color: var(--text-muted); background: var(--surface-muted); }

.method-option {
  font-weight: var(--weight-bold);
}

/* 域名徽章 */
.detail-domain-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  min-height: 34px;
  border-radius: var(--radius-sm);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  color: var(--text-secondary);
  background: var(--surface-nested);
  border: 1px solid var(--border-default);
  cursor: pointer;
}
.domain-active {
  color: var(--color-primary);
  font-weight: var(--weight-semibold);
}

/* 路径编辑区 */
.detail-path-wrapper {
  flex: 1;
  min-width: 0;
  position: relative;
}
.detail-url-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
.detail-url-text {
  color: var(--text-primary);
}
.detail-url-variable-tag {
  cursor: default;
}
.detail-url-editor {
  width: 100%;
}

/* ===== 标签页导航 ===== */
.detail-tabs-bar {
  display: flex;
  padding: 0 var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.detail-tab {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  transition: color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth);
  margin-bottom: -1px;
}
.detail-tab:hover {
  color: var(--text-primary);
}
.detail-tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: var(--weight-medium);
}
.detail-tab-badge {
  margin-left: 4px;
  color: var(--color-primary);
}

/* ===== 标签页内容区 ===== */
.detail-tab-content {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

/* 空状态提示 */
.tab-empty-hint {
  padding: var(--space-8);
  text-align: center;
  color: var(--text-placeholder);
  font-size: var(--text-sm);
}

/* ===== 变量提取列表 ===== */
.extract-list {
  padding: var(--space-3) var(--space-5);
}
.extract-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  flex-wrap: wrap;
}
.extract-index {
  width: 20px;
  color: var(--text-placeholder);
  font-size: var(--text-xs);
  flex-shrink: 0;
  text-align: right;
}
.extract-source-select {
  width: 110px;
  flex-shrink: 0;
}
.extract-input {
  flex: 1;
  min-width: 120px;
}
.extract-eq {
  color: var(--text-placeholder);
  flex-shrink: 0;
}
.extract-dup-warning {
  color: var(--error);
  font-size: var(--text-xs);
  flex-shrink: 0;
}
.extract-del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--text-placeholder);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  transition: color var(--duration-fast) var(--ease-smooth),
    background var(--duration-fast) var(--ease-smooth);
}
.extract-del:hover {
  color: var(--error);
  background: var(--error-bg);
}
.extract-warning {
  margin-top: var(--space-2);
  padding: var(--space-2);
  background: var(--error-bg);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--error);
}

/* 添加按钮 */
.tab-add-btn {
  display: block;
  width: calc(100% - var(--space-10));
  margin: var(--space-3) auto;
  padding: var(--space-2);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm);
  background: none;
  cursor: pointer;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  transition: all var(--duration-fast) var(--ease-smooth);
}
.tab-add-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* ===== 更多配置区 ===== */
.more-grid {
  padding: var(--space-4) var(--space-5);
}
.more-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.more-row label {
  width: 80px;
  flex-shrink: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
}
.more-row .el-input,
.more-row .el-input-number {
  flex: 1;
}
.full-width {
  width: 100%;
}
.wait-slider-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}
.wait-slider-row .el-slider {
  flex: 1;
}
.body-tab,
.assertions-tab,
.headers-tab {
  height: 100%;
}

/* ===== 条件编辑器 ===== */
.config-section {
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}
.config-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.section-label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}
.condition-mode-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.mode-option {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  background: var(--surface-card);
}
.mode-option:hover {
  border-color: var(--primary-300);
  background: var(--color-primary-alpha-03);
}
.mode-option.active {
  border-color: var(--primary-400);
  background: var(--color-primary-alpha-06);
}
.mode-option input[type="radio"] {
  display: none;
}
.mode-radio {
  width: 16px;
  height: 16px;
  border-radius: var(--radius-full);
  border: 2px solid var(--border-default);
  position: relative;
  flex-shrink: 0;
  transition: border-color var(--duration-fast) var(--ease-smooth);
}
.mode-option.active .mode-radio {
  border-color: var(--primary-500);
}
.mode-option.active .mode-radio::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  right: 2px;
  bottom: 2px;
  border-radius: var(--radius-full);
  background: var(--primary-500);
}
.mode-text {
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
}
.config-row {
  margin-bottom: var(--space-2);
}
.config-unit {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-left: var(--space-1);
  flex-shrink: 0;
}
.config-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

/* ===== 等待模式选择器 ===== */
.wait-mode-selector {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.mode-option.compact {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-xs);
}
.config-label-inline {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  white-space: nowrap;
  min-width: 60px;
}
.wait-random-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}
.wait-random-field {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex: 1;
}
.wait-random-field .el-input-number {
  flex: 1;
}

/* ===== 变量比较表单 ===== */
.variable-compare-form {
  margin-top: var(--space-2);
}
.compare-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-wrap: wrap;
}
.compare-prefix,
.compare-suffix {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  white-space: nowrap;
}
.compare-input {
  flex: 1;
  min-width: 120px;
}
.compare-select {
  width: 80px;
  flex-shrink: 0;
}
.var-hint {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
  font-family: var(--font-mono);
}

/* ===== 条件预览 ===== */
.condition-preview {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  margin-top: var(--space-2);
  background: var(--color-primary-alpha-04);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  color: var(--primary-700);
}
.preview-icon {
  color: var(--color-success);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  :deep(.el-dialog),
  :deep(.el-input__wrapper),
  :deep(.el-button),
  .detail-tab,
  .mode-option,
  .mode-radio,
  .extract-del,
  .tab-add-btn {
    transition-duration: 0.01ms !important;
  }
}
</style>
