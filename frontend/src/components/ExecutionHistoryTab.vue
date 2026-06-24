<template>
  <div class="history-tab">
    <div class="history-header">
      <span class="history-title">{{ $t('history.title') }}</span>
      <el-button size="small" text @click="refresh">{{ $t('common.refresh') }}</el-button>
    </div>
    <SkeletonTable v-if="loading" :rows="5" />
    <EmptyState
      v-else-if="!records.length"
      illustration="data"
      :title="$t('history.noRecords')"
      :description="$t('history.noRecordsDesc')"
    />
    <template v-else>
      <!-- 统计摘要 -->
      <div class="exec-stats-row">
        <div class="stat-item">
          <span class="stat-value">{{ records.length }}</span>
          <span class="stat-label">{{ $t('history.totalExecs') }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-value stat-pass">{{ passCount }}</span>
          <span class="stat-label">{{ $t('history.pass') }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-value stat-fail">{{ failCount }}</span>
          <span class="stat-label">{{ $t('history.fail') }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ avgTime }}ms</span>
          <span class="stat-label">{{ $t('history.avgTime') }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ passRate }}%</span>
          <span class="stat-label">{{ $t('history.passRate') }}</span>
        </div>
      </div>

      <!-- Diff 工具栏 -->
      <div v-if="selectedForDiff.length === 2" class="diff-toolbar">
        <span>{{ $t('history.compare', { id1: selectedForDiff[0].id, id2: selectedForDiff[1].id }) }}</span>
        <el-button size="small" type="primary" @click="showDiff = true">{{ $t('history.viewDiff') }}</el-button>
      </div>

      <div class="history-list">
        <div
          ref="scrollContainer"
          :style="enabled ? { overflowY: 'auto', maxHeight: '600px' } : undefined"
        >
          <div :style="totalHeightStyle">
            <div :style="offsetStyle">
              <div
                v-for="(r, i) in visibleItems"
                :key="r.id ?? 'record-' + i + '-' + r.created_at"
                class="history-item"
                :class="{ 'diff-selected': isSelectedForDiff(r) }"
              >
          <div class="history-item-header">
            <label class="diff-checkbox" :title="$t('history.selectForCompare')" @click.stop="toggleDiffSelect(r)">
              <input type="checkbox" :checked="isSelectedForDiff(r)" />
            </label>
            <span class="history-index">#{{ records.length - (visibleRange.start + i) }}</span>
            <span class="history-status" :class="r.status">{{ r.status === 'passed' ? $t('history.pass') : r.status === 'failed' ? $t('history.fail') : r.status }}</span>
            <span class="history-duration">{{ r.duration }}ms</span>
            <span class="history-time">{{ formatTime(r.created_at) }}</span>
          </div>
          <div v-if="r.response_status" class="history-meta">
            <span>{{ $t('history.statusCode') }} {{ r.response_status }}</span>
          </div>
          <div v-if="r.error" class="history-error">{{ r.error }}</div>
          <div class="history-actions">
            <el-button size="small" text type="primary" @click="replayExecution(r)">
              <RefreshCwIcon :size="12" /> {{ $t('history.rerun') }}
            </el-button>
          </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Diff 对话框 -->
      <el-dialog v-model="showDiff" :title="$t('history.compareTitle')" width="700px">
        <div class="diff-container">
          <div class="diff-side">
            <h4>#{{ diffLeft.id }} ({{ formatTime(diffLeft.created_at) }})</h4>
            <pre class="diff-json">{{ formatJson(diffLeft.response_body) }}</pre>
          </div>
          <div class="diff-vs">VS</div>
          <div class="diff-side">
            <h4>#{{ diffRight.id }} ({{ formatTime(diffRight.created_at) }})</h4>
            <pre class="diff-json">{{ formatJson(diffRight.response_body) }}</pre>
          </div>
        </div>
      </el-dialog>
    </template>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { RefreshCw as RefreshCwIcon } from 'lucide-vue-next'
import request from '../api/request'
import { msgSuccess, msgError } from '../utils/message'
import { logger, isSilentAuthError } from '@/utils/logger'
import { useVirtualScroll } from '@/composables/useVirtualScroll'
import EmptyState from '@/components/EmptyState.vue'
import SkeletonTable from '@/components/SkeletonTable.vue'

const { t } = useI18n()

interface HistoryRecord {
  id?: number
  status: string
  duration: number
  response_status?: number
  response_body?: string | Record<string, unknown> | null
  error?: string
  created_at: string
}

const props = defineProps<{ projectId: number; caseId: number }>()

const emit = defineEmits<{ replay: [record: HistoryRecord] }>()

const records = ref<HistoryRecord[]>([])
const loading = ref(false)
const selectedForDiff = ref<HistoryRecord[]>([])
const showDiff = ref(false)

const {
  visibleItems,
  totalHeightStyle,
  offsetStyle,
  scrollContainer,
  enabled,
  visibleRange,
  scrollToTop,
} = useVirtualScroll(records, {
  itemHeight: 60,
  threshold: 50,
  containerHeight: 600,
})

// ── 统计计算属性 ──
const passCount = computed(() => records.value.filter(r => r.status === 'passed').length)
const failCount = computed(() => records.value.filter(r => r.status === 'failed').length)
const avgTime = computed(() => {
  if (!records.value.length) return 0
  const total = records.value.reduce((sum, r) => sum + (r.duration || 0), 0)
  return Math.round(total / records.value.length)
})
const passRate = computed(() => {
  if (!records.value.length) return 0
  return Math.round((passCount.value / records.value.length) * 100)
})

// ── Diff 选择逻辑 ──
function isSelectedForDiff(record: HistoryRecord): boolean {
  return selectedForDiff.value.some(r => r.id === record.id && r.created_at === record.created_at)
}

function toggleDiffSelect(record: HistoryRecord) {
  const idx = selectedForDiff.value.findIndex(r => r.id === record.id && r.created_at === record.created_at)
  if (idx >= 0) {
    selectedForDiff.value.splice(idx, 1)
  } else if (selectedForDiff.value.length < 2) {
    selectedForDiff.value.push(record)
  }
}

const diffLeft = computed(() => selectedForDiff.value[0] || {} as HistoryRecord)
const diffRight = computed(() => selectedForDiff.value[1] || {} as HistoryRecord)

// ── 重跑执行 ──
function replayExecution(record: HistoryRecord) {
  try {
    emit('replay', record)
    msgSuccess(t('history.rerunning'))
  } catch {
    msgError(t('history.rerunFailed'))
  }
}

// ── 格式化工具函数 ──
function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  if (isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  const isYesterday = new Date(now.getTime() - 86400000).toDateString() === d.toDateString()

  if (isToday) {
    return `${t('history.today')} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
  if (isYesterday) {
    return `${t('history.yesterday')} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }

  // 显示完整日期时间：YYYY-MM-DD HH:MM
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatJson(data: string | Record<string, unknown> | null | undefined): string {
  if (!data) return t('history.empty')
  if (typeof data === 'string') {
    try { return JSON.stringify(JSON.parse(data), null, 2) }
    catch { return data }
  }
  return JSON.stringify(data, null, 2)
}

// ── 数据加载 ──
async function refresh() {
  loading.value = true
  try {
    const res = await request.get(`/projects/${props.projectId}/run/cases/${props.caseId}/history`)
    records.value = res.data || []
    void nextTick(() => scrollToTop())
  } catch (err) { if (!isSilentAuthError(err)) logger.error('[ExecutionHistoryTab] refresh failed:', err); records.value = [] }
  finally { loading.value = false }
}

onMounted(refresh)
</script>
<style scoped>
/* ==========================================
 * ExecutionHistoryTab 样式
 * 使用 design tokens 确保主题一致性
 * ========================================== */

.history-tab { padding: var(--spacing-sm) 0; }

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.history-title {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

.history-loading,
.history-empty {
  color: var(--text-muted);
  font-size: var(--font-size-sm);
  padding: var(--spacing-xl);
  text-align: center;
}

/* ===== 统计摘要区域 ===== */
.exec-stats-row {
  display: flex;
  gap: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-nested);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-md);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.stat-value.stat-pass { color: var(--success-dark); }
.stat-value.stat-fail { color: var(--method-delete-text); }

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
}

/* ===== Diff 工具栏 ===== */
.diff-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary-alpha-08);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--primary-600);
}

/* ===== 历史记录列表 ===== */
.history-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  transition: border-color var(--duration-fast) var(--ease-smooth),
              background-color var(--duration-fast) var(--ease-smooth);
}

.history-item:hover {
  background: var(--surface-hover);
}

.history-item.diff-selected {
  border-color: var(--primary-400);
  background: var(--color-primary-alpha-04);
}

.history-item-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* Diff 复选框 */
.diff-checkbox {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.diff-checkbox input[type="checkbox"] {
  accent-color: var(--primary-500);
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.history-index {
  font-weight: var(--weight-semibold);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* 状态标签 */
.history-status {
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  padding: 0 var(--spacing-sm);
  border-radius: var(--radius-sm);
}

.history-status.passed {
  background: var(--color-success-alpha-10);
  color: var(--success);
}

.history-status.failed {
  background: var(--color-error-alpha-10);
  color: var(--error);
}

.history-duration {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.history-time {
  font-size: var(--font-size-xs);
  color: var(--text-muted);
  margin-left: auto;
}

.history-meta {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin-top: var(--spacing-xs);
}

.history-error {
  font-size: var(--font-size-xs);
  color: var(--error);
  margin-top: var(--spacing-xs);
}

.history-actions {
  margin-top: var(--spacing-xs);
  display: flex;
  justify-content: flex-end;
}

/* ===== Diff 对话框 ===== */
.diff-container {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--spacing-md);
  align-items: start;
}

.diff-vs {
  writing-mode: vertical-lr;
  text-align: center;
  padding: var(--spacing-lg) var(--spacing-xs);
  color: var(--text-muted);
  font-weight: var(--weight-bold);
  letter-spacing: 2px;
}

.diff-json {
  background: var(--surface-code);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  max-height: 400px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: var(--leading-relaxed);
}

/* ===== 暗色模式适配 ===== */
html.dark .history-item {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}

html.dark .history-item:hover {
  background: var(--surface-hover);
}

html.dark .history-meta {
  color: var(--text-muted);
}
</style>
