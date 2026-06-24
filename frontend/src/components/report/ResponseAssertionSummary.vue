<template>
  <div class="assertion-list">
    <!-- 摘要统计 -->
    <div class="assertion-summary">
      <span class="assertion-summary-total">共 {{ total }} 项</span>
      <span v-if="passedCount" class="assertion-summary-pass">{{ passedCount }} 通过</span>
      <span v-if="failedCount" class="assertion-summary-fail">{{ failedCount }} 失败</span>
      <button
        v-if="passedCount > 0"
        class="assertion-collapse-toggle"
        @click="collapsed = !collapsed"
      >
        {{ collapsed ? '展开全部' : '折叠通过的' }}
      </button>
    </div>

    <!-- 失败断言（始终展开） -->
    <div
      v-for="(a, i) in failedAssertions"
      :key="'fail-' + i"
      class="assertion-item failed"
    >
      <div class="assertion-row">
        <X :size="14" class="assertion-icon fail-icon" />
        <span class="assertion-type-badge">{{ typeLabel(a.type) || a.type }}</span>
        <span v-if="a.message" class="assertion-message">{{ a.message }}</span>
      </div>
      <div class="assertion-detail">
        <div class="assertion-compare">
          <span class="compare-label">期望</span>
          <span class="compare-value expected">{{ formatValue(a.expected) }}</span>
        </div>
        <div class="assertion-compare">
          <span class="compare-label">实际</span>
          <span class="compare-value actual">{{ formatValue(a.actual) }}</span>
        </div>
      </div>
    </div>

    <!-- 通过断言（可折叠） -->
    <template v-if="!collapsed">
      <div
        v-for="(a, i) in passedAssertions"
        :key="'pass-' + i"
        class="assertion-item passed"
      >
        <div class="assertion-row">
          <Check :size="14" class="assertion-icon pass-icon" />
          <span class="assertion-type-badge">{{ typeLabel(a.type) || a.type }}</span>
          <span v-if="a.message" class="assertion-message">{{ a.message }}</span>
        </div>
      </div>
    </template>

    <EmptyState
      v-if="!total"
      illustration="empty"
      title="暂无断言"
      description="响应中没有断言结果"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, Check } from 'lucide-vue-next'
import EmptyState from '@/components/EmptyState.vue'

export interface AssertionResult {
  type: string
  passed: boolean
  message?: string
  expected?: string
  actual?: string
  value?: string
  operator?: string
}

const props = defineProps<{
  results: AssertionResult[]
}>()

const collapsed = ref(true)

const total = computed(() => props.results.length)
const passedAssertions = computed(() => props.results.filter(a => a.passed))
const failedAssertions = computed(() => props.results.filter(a => !a.passed))
const passedCount = computed(() => passedAssertions.value.length)
const failedCount = computed(() => failedAssertions.value.length)

const assertionTypeLabel: Record<string, string> = {
  status: '状态码',
  json: 'JSON',
  body: '响应体',
  header: '响应头',
  response_time: '响应时间',
}

function typeLabel(type: string): string {
  return assertionTypeLabel[type] || type
}

function formatValue(val: string | undefined | null): string {
  if (val === undefined || val === null) return '—'
  return String(val)
}
</script>

<style scoped>
.assertion-list {
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.assertion-summary {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}
.assertion-summary-total { color: var(--text-secondary); }
.assertion-summary-pass { color: var(--success-text); font-weight: var(--weight-semibold); }
.assertion-summary-fail { color: var(--error-text); font-weight: var(--weight-semibold); }
.assertion-collapse-toggle {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--primary-600);
  cursor: pointer;
  font-size: var(--text-xs);
}
.assertion-collapse-toggle:hover { color: var(--primary-500); text-decoration: underline; }
.assertion-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.assertion-item.failed { border-color: var(--color-error-200); background: var(--color-error-50); }
html.dark .assertion-item.failed { background: rgba(217, 107, 107, 0.06); }
.assertion-item.passed { border-color: var(--color-success-200); }
.assertion-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
}
.assertion-icon { flex-shrink: 0; }
.fail-icon { color: var(--color-error-500); }
.pass-icon { color: var(--color-success-500); }
.assertion-type-badge {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  padding: 1px 8px;
  border-radius: var(--radius-full);
  background: var(--surface-card);
  color: var(--text-secondary);
}
.assertion-message {
  color: var(--text-primary);
  word-break: break-word;
}
.assertion-detail {
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-size: var(--text-xs);
}
.assertion-compare {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
}
.compare-label {
  flex-shrink: 0;
  color: var(--text-muted);
  min-width: 2em;
}
.compare-value {
  font-family: var(--font-mono);
  word-break: break-all;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
}
.compare-value.expected { background: var(--color-primary-50); color: var(--color-primary-700); }
.compare-value.actual { background: var(--color-error-50); color: var(--color-error-700); }
html.dark .compare-value.expected { background: rgba(93, 117, 175, 0.12); color: var(--color-primary-300); }
html.dark .compare-value.actual { background: rgba(217, 107, 107, 0.12); color: var(--color-error-300); }
</style>
