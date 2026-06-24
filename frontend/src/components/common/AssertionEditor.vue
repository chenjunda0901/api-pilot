<template>
  <div class="assertion-editor">
    <div class="assertion-list">
      <EmptyState
        v-if="!modelValue.length"
        illustration="empty"
        title="尚无断言"
        description="点击下方新增按钮添加断言规则"
      />
      <div
        v-for="(a, idx) in modelValue"
        :key="idx"
        class="assertion-row"
        :class="{ disabled: !a.enabled }"
      >
        <el-switch v-model="a.enabled" size="small" />
        <el-select v-model="a.assertion_type" size="small" style="width: 130px" @change="emitChange">
          <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-input
          v-model="a.expression"
          size="small"
          :placeholder="expressionPlaceholder(a.assertion_type)"
          class="assertion-expr-input"
          @input="emitChange"
        />
        <el-select v-model="a.operator" size="small" style="width: 100px" @change="emitChange">
          <el-option v-for="op in operatorsForType(a.assertion_type)" :key="op.value" :label="op.label" :value="op.value" />
        </el-select>
        <el-input
          v-model="a.expected_value"
          size="small"
          placeholder="期望值"
          class="assertion-value-input"
          @input="emitChange"
        />
        <el-button-group size="small">
          <el-button size="small" :loading="testing === idx" @click="testOne(a, idx)">测试</el-button>
          <el-button size="small" type="danger" @click="remove(idx)">删除</el-button>
        </el-button-group>
        <div v-if="testResults[idx]" class="assertion-result" :class="testResults[idx].passed ? 'pass' : 'fail'">
          <span class="result-icon">{{ testResults[idx].passed ? '✓' : '✗' }}</span>
          <span class="result-msg">{{ testResults[idx].message }}</span>
          <span class="result-actual">实际: {{ truncate(testResults[idx].actual) }}</span>
        </div>
      </div>
    </div>

    <div class="assertion-add-row">
      <el-button size="small" @click="add">
        <Plus :size="14" />添加断言
      </el-button>
      <el-button v-if="modelValue.length" size="small" type="primary" :loading="testingAll" @click="testAll">
        全部测试
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus } from 'lucide-vue-next'
import { msgError } from '@/utils/message'
import EmptyState from '@/components/EmptyState.vue'
import {
  testAssertion, type Assertion, type AssertionTestResult,
} from '@/api/assertions'

const props = defineProps<{
  modelValue: Assertion[]
  projectId: number
  apiId: number
  // 用于在没有真实响应时进行测试的虚拟响应
  testResponse?: {
    body: string
    status: number
    headers?: Record<string, string>
    duration_ms?: number
  }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Assertion[]]
}>()

const typeOptions = [
  { label: '状态码', value: 'status' },
  { label: 'JSONPath', value: 'jsonpath' },
  { label: '正则', value: 'regex' },
  { label: '响应头', value: 'header' },
  { label: '响应时间', value: 'response_time' },
  { label: 'Body 包含', value: 'body_contains' },
]

const operatorMap: Record<string, Array<{ label: string; value: string }>> = {
  status: [
    { label: '=', value: 'eq' },
    { label: '≠', value: 'ne' },
    { label: '>', value: 'gt' },
    { label: '<', value: 'lt' },
    { label: '≥', value: 'gte' },
    { label: '≤', value: 'lte' },
  ],
  jsonpath: [
    { label: '=', value: 'eq' },
    { label: '≠', value: 'ne' },
    { label: '存在', value: 'exists' },
    { label: '不存在', value: 'not_exists' },
    { label: '包含', value: 'contains' },
  ],
  regex: [
    { label: '匹配', value: 'matches' },
    { label: '不匹配', value: 'not_matches' },
  ],
  header: [
    { label: '=', value: 'eq' },
    { label: '≠', value: 'ne' },
    { label: '包含', value: 'contains' },
    { label: '存在', value: 'exists' },
  ],
  response_time: [
    { label: '<', value: 'lt' },
    { label: '≤', value: 'lte' },
  ],
  body_contains: [
    { label: '包含', value: 'contains' },
    { label: '不包含', value: 'not_contains' },
  ],
}

function operatorsForType(t: string) {
  return operatorMap[t] || operatorMap.status
}

function expressionPlaceholder(t: string): string {
  switch (t) {
    case 'jsonpath': return '$.data.id'
    case 'header': return 'Content-Type'
    case 'regex': return 'token=(.+)'
    case 'body_contains': return 'error'
    case 'response_time': return 'ms'
    default: return '200'
  }
}

const testResults = ref<Record<number, AssertionTestResult>>({})
const testing = ref<number | null>(null)
const testingAll = ref(false)

function emitChange() {
  emit('update:modelValue', [...props.modelValue])
}

function add() {
  emit('update:modelValue', [
    ...props.modelValue,
    {
      assertion_type: 'status',
      expression: 'status',
      operator: 'eq',
      expected_value: '200',
      enabled: true,
    },
  ])
}

function remove(idx: number) {
  const next = [...props.modelValue]
  next.splice(idx, 1)
  emit('update:modelValue', next)
  delete testResults.value[idx]
}

async function testOne(a: Assertion, idx: number) {
  testing.value = idx
  try {
    const resp = props.testResponse || {
      body: '{"code":200,"data":{"id":1,"token":"abc123"}}',
      status: 200,
      headers: { 'content-type': 'application/json' },
      duration_ms: 120,
    }
    const res = await testAssertion(props.projectId, props.apiId, {
      ...a,
      response_body: resp.body,
      response_status: resp.status,
      response_headers: resp.headers,
      response_time: resp.duration_ms,
    })
    testResults.value[idx] = res.data
  } catch {
    testResults.value[idx] = {
      passed: false,
      actual: '-',
      expected: a.expected_value,
      message: '测试执行失败',
    }
    msgError('测试失败')
  } finally {
    testing.value = null
  }
}

async function testAll() {
  testingAll.value = true
  try {
    for (let i = 0; i < props.modelValue.length; i++) {
      if (props.modelValue[i].enabled) {
        await testOne(props.modelValue[i], i)
      }
    }
  } finally {
    testingAll.value = false
  }
}

function truncate(s: string, n = 40): string {
  if (!s) return ''
  return s.length > n ? s.slice(0, n) + '...' : s
}
</script>

<style scoped>
.assertion-editor { display: flex; flex-direction: column; gap: var(--space-3); }

.assertion-list { display: flex; flex-direction: column; gap: var(--space-2); }

.assertion-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}
.assertion-row.disabled { opacity: 0.55; }

.assertion-expr-input { width: 200px; }
.assertion-value-input { width: 160px; }

.assertion-result {
  flex-basis: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}
.assertion-result.pass { background: var(--color-success-alpha-12); color: var(--color-success); }
.assertion-result.fail { background: var(--color-error-alpha-12); color: var(--color-error); }
.result-icon { font-weight: var(--weight-bold); }
.result-msg { flex: 1; }
.result-actual { color: var(--text-muted); font-family: var(--font-mono); }

.assertion-add-row { display: flex; gap: var(--space-2); }

/* 暗色模式 */
:global(html.dark) .assertion-row { background: var(--surface-card); border-color: var(--border-subtle); }
:global(html.dark) .assertion-result.pass { background: var(--color-success-alpha-15); }
:global(html.dark) .assertion-result.fail { background: var(--color-error-alpha-15); }
</style>
