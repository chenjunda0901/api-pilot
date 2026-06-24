<template>
  <div class="assertion-tab">
    <div class="assertion-header">
      <span class="assertion-title">{{ $t('assertion.title', { count: rows.length }) }}</span>
      <el-button size="small" text @click="addAssertion">+ {{ $t('assertion.add') }}</el-button>
    </div>

    <!-- 匹配模式切换 -->
    <div class="assertion-mode-toggle">
      <span>{{ $t('assertion.matchMode') }}：</span>
      <el-radio-group v-model="assertionLogicMode" size="small">
        <el-radio-button value="all">{{ $t('assertion.allPass') }}</el-radio-button>
        <el-radio-button value="any">{{ $t('assertion.anyPass') }}</el-radio-button>
      </el-radio-group>
    </div>
    <p class="assertion-hint">{{ assertionLogicMode === 'all' ? $t('assertion.allMustPass') : $t('assertion.anyCanPass') }}</p>

    <!-- Assertion type selector when adding new -->
    <template v-if="rows.length === 0 && !showTypeSelector">
      <EmptyState
        illustration="empty"
        :title="$t('assertion.noRules')"
        :description="$t('assertion.noRulesDesc')"
      >
        <template #action>
          <div class="assertion-type-grid">
            <div class="assertion-type-card" tabindex="0" @click="showTypeSelector = true" @keydown.enter="showTypeSelector = true">
              <div class="atc-icon">✓</div>
              <div class="atc-name">{{ $t('assertion.cardTypes.statusCode') }}</div>
              <div class="atc-desc">{{ $t('assertion.cardDescs.statusCode') }}</div>
            </div>
            <div class="assertion-type-card" tabindex="0" @click="addAssertion('status')" @keydown.enter="addAssertion('status')">
              <div class="atc-icon" style="background:var(--assertion-status-bg);color:var(--assertion-status-text)">#</div>
              <div class="atc-name">{{ $t('assertion.cardTypes.jsonField') }}</div>
              <div class="atc-desc">{{ $t('assertion.cardDescs.jsonField') }}</div>
            </div>
            <div class="assertion-type-card" tabindex="0" @click="addAssertion('header')" @keydown.enter="addAssertion('header')">
              <div class="atc-icon" style="background:var(--assertion-header-bg);color:var(--assertion-header-text)">H</div>
              <div class="atc-name">{{ $t('assertion.cardTypes.responseHeader') }}</div>
              <div class="atc-desc">{{ $t('assertion.cardDescs.responseHeader') }}</div>
            </div>
            <div class="assertion-type-card" tabindex="0" @click="addAssertion('contains')" @keydown.enter="addAssertion('contains')">
              <div class="atc-icon" style="background:var(--assertion-contains-bg);color:var(--assertion-contains-text)">{ }</div>
              <div class="atc-name">{{ $t('assertion.cardTypes.bodyContains') }}</div>
              <div class="atc-desc">{{ $t('assertion.cardDescs.bodyContains') }}</div>
            </div>
            <div class="assertion-type-card" tabindex="0" @click="addAssertion('response_time')" @keydown.enter="addAssertion('response_time')">
              <div class="atc-icon" style="background:var(--assertion-time-bg);color:var(--assertion-time-text)">⚡</div>
              <div class="atc-name">{{ $t('assertion.cardTypes.responseTime') }}</div>
              <div class="atc-desc">{{ $t('assertion.cardDescs.responseTime') }}</div>
            </div>
          </div>
        </template>
      </EmptyState>
    </template>

    <div v-for="(a, i) in rows" :key="a.id" class="assertion-card" :class="a._passed ? 'passed' : a._passed === false ? 'failed' : ''">
      <!-- Left color indicator -->
      <div class="assertion-card-left" :class="a._passed ? 'passed' : a._passed === false ? 'failed' : ''"></div>

      <div class="assertion-card-body">
        <!-- Summary row -->
        <div class="assertion-summary" @click="toggleExpand(i)">
          <div class="assertion-card-header">
            <el-switch v-model="a.enabled" size="small" @click.stop />
            <span class="assertion-type-badge">{{ typeIcon(a.type) }}</span>
          </div>
          <div class="assertion-summary-text">
            {{ summaryText(a) }}
          </div>
          <div class="assertion-summary-result" v-if="a._passed !== undefined">
            <span v-if="a._passed" class="asr-pass">{{ $t('assertion.pass') }}</span>
            <span v-else class="asr-fail">
              {{ $t('assertion.fail') }}
              <span v-if="a._actual !== undefined" class="asr-actual">{{ $t('assertion.expected') }} {{ a._expected }}, {{ $t('assertion.actual') }} {{ a._actual }}</span>
            </span>
          </div>
          <div class="assertion-expand-icon">
            <ChevronDown :size="14" :class="{ 'rotated': expandedIndex === i }" />
          </div>
        </div>

        <!-- Expanded edit view -->
        <div v-if="expandedIndex === i" class="assertion-edit">
          <div class="assertion-type-row">
            <el-select v-model="a.type" size="small" style="width:140px" @change="onTypeChange(a)">
              <el-option :label="$t('assertion.statusCodeAssertion')" value="status" />
              <el-option :label="$t('assertion.jsonFieldAssertion')" value="body" />
              <el-option :label="$t('assertion.headerAssertion')" value="header" />
              <el-option :label="$t('assertion.bodyContainsAssertion')" value="contains" />
              <el-option :label="$t('assertion.responseTimeAssertion')" value="response_time" />
            </el-select>
            <el-button text size="small" type="danger" @click="remove(i)">{{ $t('assertion.deleteRule') }}</el-button>
          </div>

          <div class="assertion-fields">
            <!-- status -->
            <template v-if="a.type === 'status'">
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.expectedStatus') }}</span>
                <el-select v-model="a.operator" size="small" style="width:100px">
                  <el-option :label="$t('assertion.equals')" value="eq" />
                  <el-option :label="$t('assertion.notEquals')" value="neq" />
                  <el-option :label="$t('assertion.containedIn')" value="in" />
                </el-select>
                <el-input-number v-model="a.value" size="small" :min="100" :max="599" style="width:120px" />
              </div>
            </template>

            <!-- body (JSONPath) -->
            <template v-else-if="a.type === 'body'">
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.fieldPath') }}</span>
                <VarAwareInput v-model="a.path" size="small" placeholder="$.data.code" :aria-label="$t('assertion.fieldPath')" />
              </div>
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.types.jsonpath') }}</span>
                <el-select v-model="a.operator" size="small" style="width:100px">
                  <el-option :label="$t('assertion.equals')" value="eq" />
                  <el-option :label="$t('assertion.notEquals')" value="neq" />
                  <el-option :label="$t('assertion.contains')" value="contains" />
                  <el-option :label="$t('assertion.greaterThan')" value="gt" />
                  <el-option :label="$t('assertion.lessThan')" value="lt" />
                  <el-option :label="$t('assertion.isEmpty')" value="is_null" />
                  <el-option :label="$t('assertion.isNotEmpty')" value="is_not_null" />
                </el-select>
                <VarAwareInput v-model="a.value" size="small" :placeholder="$t('assertion.expectedValue')" :aria-label="$t('assertion.expectedValue')" />
              </div>
            </template>

            <!-- header -->
            <template v-else-if="a.type === 'header'">
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.headerName') }}</span>
                <VarAwareInput v-model="a.header" size="small" :placeholder="$t('assertion.headerNamePlaceholder')" :aria-label="$t('assertion.headerNamePlaceholder')" />
              </div>
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.types.jsonpath') }}</span>
                <el-select v-model="a.operator" size="small" style="width:100px">
                  <el-option :label="$t('assertion.equals')" value="eq" />
                  <el-option :label="$t('assertion.notEquals')" value="neq" />
                  <el-option :label="$t('assertion.contains')" value="contains" />
                  <el-option :label="$t('assertion.exists')" value="exists" />
                  <el-option :label="$t('assertion.notExists')" value="not_exists" />
                </el-select>
                <VarAwareInput v-model="a.value" size="small" :placeholder="$t('assertion.expectedValue')" :aria-label="$t('assertion.expectedValue')" />
              </div>
            </template>

            <!-- contains -->
            <template v-else-if="a.type === 'contains'">
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.expectedContains') }}</span>
                <VarAwareInput v-model="a.value" size="small" :placeholder="$t('assertion.checkBodyContains')" :aria-label="$t('assertion.expectedValue')" />
              </div>
            </template>

            <!-- response_time -->
            <template v-else-if="a.type === 'response_time'">
              <div class="af-row">
                <span class="af-label">{{ $t('assertion.responseTimeLabel') }}</span>
                <el-select v-model="a.operator" size="small" style="width:100px">
                  <el-option :label="$t('assertion.lessThan')" value="lt" />
                  <el-option :label="$t('assertion.lessThanOrEqual')" value="lte" />
                  <el-option :label="$t('assertion.greaterThan')" value="gt" />
                </el-select>
                <el-input-number v-model="a.value" size="small" :min="0" :max="300000" style="width:120px" />
                <span class="af-unit">ms</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div v-if="rows.length > 0" class="assertion-add-more">
      <el-button size="small" text @click="addAssertion()">+ {{ $t('assertion.addRule') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown } from 'lucide-vue-next'
import VarAwareInput from './common/VarAwareInput.vue'
import EmptyState from '@/components/EmptyState.vue'

interface AssertionRule {
  id: number
  type: 'status' | 'body' | 'header' | 'contains' | 'response_time'
  operator: string
  value: string | number
  path?: string
  header?: string
  enabled: boolean
  _passed?: boolean
  _actual?: string
  _expected?: string
}

const props = defineProps<{ modelValue: AssertionRule[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: AssertionRule[]] }>()

const showTypeSelector = ref(false)
const expandedIndex = ref<number | null>(0)
const assertionLogicMode = ref<'all' | 'any'>('all')
const { t } = useI18n()

const rows = computed({
  get: () => (props.modelValue || []).map((item, idx) => ({ ...item, id: item.id ?? idx })),
  set: (v) => emit('update:modelValue', v),
})

function addAssertion(type = 'status') {
  const arr = [...(props.modelValue || [])]
  const newItem: AssertionRule = { id: Date.now(), type: type as AssertionRule['type'], operator: 'eq', value: '', enabled: true }
  if (type === 'status') {
    newItem.value = 200
    newItem.operator = 'eq'
  } else if (type === 'body') {
    newItem.path = ''
    newItem.operator = 'eq'
  } else if (type === 'header') {
    newItem.header = ''
    newItem.operator = 'eq'
  } else if (type === 'response_time') {
    newItem.value = 2000
    newItem.operator = 'lt'
  }
  arr.push(newItem)
  emit('update:modelValue', arr)
  showTypeSelector.value = false
  expandedIndex.value = arr.length - 1
}

function remove(index: number) {
  const arr = [...(props.modelValue || [])]
  arr.splice(index, 1)
  emit('update:modelValue', arr)
}

function toggleExpand(index: number) {
  expandedIndex.value = expandedIndex.value === index ? null : index
}

function onTypeChange(a: AssertionRule) {
  const newArr = rows.value.map(r => {
    if (r === a) {
      const updated = { ...r, operator: 'eq', value: '', path: '', header: '', enabled: r.enabled ?? true }
      if (r.type === 'status') updated.value = 200
      if (r.type === 'response_time') { updated.value = 2000; updated.operator = 'lt' }
      return updated
    }
    return r
  })
  emit('update:modelValue', newArr)
}

function typeIcon(type: string) {
  const map: Record<string, string> = {
    status: '✓', body: '#', json: '#', header: 'H', contains: '{ }', response_time: '⚡',
  }
  return map[type] || '?'
}

function summaryText(a: AssertionRule) {
  const isJson = a.type === 'body' || a.type === 'json'
  switch (a.type) {
    case 'status':
      return `${t('assertion.statusCodeSummary')} ${operatorText(a.operator)} ${a.value}`
    case 'body':
    case 'json':
      if (a.operator === 'is_null' || a.operator === 'is_not_null') {
        return `${t('assertion.jsonSummary')} ${a.path || t('assertion.noPath')} ${operatorText(a.operator)}`
      }
      return `${t('assertion.jsonSummary')} ${a.path || t('assertion.noPath')} ${operatorText(a.operator)} ${a.value}`
    case 'header':
      return `${t('assertion.headerSummary')} ${a.header || t('assertion.notFilled')} ${operatorText(a.operator)} ${a.value}`
    case 'contains':
      return `${t('assertion.bodyContainsSummary')} "${a.value || t('assertion.notFilled')}" `
    case 'response_time':
      return `${t('assertion.responseTimeSummary')} ${operatorText(a.operator)} ${a.value}ms`
    default:
      return isJson ? `${t('assertion.jsonSummary')} ${a.path || t('assertion.noPath')} ${operatorText(a.operator)} ${a.value}` : `${a.type} ${a.operator} ${a.value}`
  }
}

function operatorText(op: string) {
  const map: Record<string, string> = {
    eq: '=', neq: '≠', gt: '>', lt: '<', gte: '≥', lte: '≤',
    contains: t('assertion.containsOp'), exists: t('assertion.existsOp'), not_exists: t('assertion.notExistsOp'), in: '∈',
  }
  return map[op] || op
}
</script>

<style scoped>
/* ==========================================
 * AssertionTab — 断言规则样式
 * ========================================== */

.assertion-tab {
  max-width: min(800px, 100%);
}

/* 头部 */
.assertion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.assertion-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 类型选择网格 */
.assertion-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.assertion-type-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-3);
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-smooth);
  text-align: center;
  background: var(--surface-card);
}

.assertion-type-card:hover {
  border-color: var(--primary-300);
  background: var(--color-primary-alpha-04);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}

.atc-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--grad-primary-subtle);
  color: var(--primary-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  margin: 0 auto var(--space-2);
}

.atc-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.atc-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
  line-height: var(--leading-relaxed);
}

.assertion-empty {
  text-align: center;
  padding: var(--space-3) 0;
}

.assertion-empty-text {
  color: var(--text-muted);
  font-size: var(--text-sm);
}

/* 断言卡片 */
.assertion-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-2);
  display: flex;
  overflow: hidden;
  transition: all var(--duration-base) var(--ease-smooth);
  background: var(--surface-card);
}

.assertion-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

.assertion-card.passed {
  border-color: var(--success-border);
}

.assertion-card.failed {
  border-color: var(--error-border);
  background: var(--grad-status-5xx);
}

.assertion-card-left {
  width: 3px;
  flex-shrink: 0;
  border-radius: 3px 0 0 3px;
  background: var(--border-subtle);
}
.assertion-card-left.passed { background: var(--assertion-pass-border); }
.assertion-card-left.failed { background: var(--assertion-fail-border); }

.assertion-card-body { flex: 1; padding: 10px var(--space-3); }

/* Summary row */
.assertion-summary {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  padding: var(--space-1) 0;
}
.assertion-summary:hover {
  background: var(--surface-hover);
  margin: 0 -12px;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
}

.assertion-summary-icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}

.assertion-summary-text {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.assertion-summary-result { flex-shrink: 0; }
.asr-pass {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 20px;
  border-radius: var(--radius-sm);
  background: var(--assertion-pass-bg);
  color: var(--assertion-pass-text);
  font-size: 0.625rem;
  font-weight: var(--weight-bold);
  border: 1px solid var(--assertion-pass-border);
}
.asr-fail {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  height: 20px;
  border-radius: var(--radius-sm);
  background: var(--assertion-fail-bg);
  color: var(--assertion-fail-text);
  font-size: 0.625rem;
  font-weight: var(--weight-bold);
  border: 1px solid var(--assertion-fail-border);
}
.asr-actual { font-weight: var(--weight-normal); font-size: 0.625rem; }

.assertion-expand-icon { color: var(--text-muted); transition: transform var(--duration-base) var(--ease-smooth); }
.assertion-expand-icon .rotated { transform: rotate(180deg); }

/* 展开编辑区 */
.assertion-edit {
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--surface-inset);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.assertion-type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.assertion-fields { display: flex; flex-direction: column; gap: var(--space-2); }

.af-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.af-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  min-width: 60px;
}

.af-unit {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.assertion-add-more {
  margin-top: var(--space-2);
  text-align: center;
}

/* 暗色模式 */
html.dark .assertion-type-card { background: var(--surface-card); }
html.dark .assertion-card { background: var(--surface-card); }
html.dark .assertion-card.failed { background: var(--assertion-fail-bg); }

/* 断言逻辑模式 */
.assertion-mode-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
}
.assertion-hint {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-top: var(--space-1);
}

/* 断言启用开关 */
.assertion-card-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.assertion-card-header .el-switch { --el-switch-on-color: var(--primary-500); }
.assertion-type-badge {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-alpha-10);
  color: var(--primary-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  flex-shrink: 0;
}
</style>