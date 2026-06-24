<template>
  <div>
    <Teleport to="body">
    <div v-if="visible" class="ep-overlay" @click.self="emit('minimize')">
      <div class="ep-panel" :class="{ completed: isCompleted, success: reportStatus === 'success', failed: reportStatus === 'failed' }">
        <!-- Header -->
        <div class="ep-header">
          <div class="ep-header-left">
            <span class="ep-icon" :class="statusClass">{{ statusIcon }}</span>
            <span class="ep-title">{{ isCompleted ? $t('exec.progressTitle') : $t('exec.running') }}: {{ sceneName }}</span>
          </div>
          <div class="ep-header-actions">
            <button v-if="!isCompleted" class="ep-btn-stop" @click="emit('cancel')">
              <Square :size="14" /> {{ $t('exec.stop') }}
            </button>
            <button class="ep-btn-icon" @click="emit('minimize')" :title="$t('exec.minimize')">_</button>
            <button class="ep-btn-icon" @click="emit('close')" :title="$t('common.close')">&times;</button>
          </div>
        </div>

        <!-- Progress bar: 渐变 + 光泽动画 + 百分比 -->
        <div class="ep-progress">
          <div class="ep-progress-bar">
            <div
              class="ep-progress-fill"
              :class="{ 'has-fail': failCount > 0, 'is-complete': isCompleted }"
              :style="{ width: totalSteps > 0 ? ((doneCount / totalSteps) * 100) + '%' : '0%' }"
            />
          </div>
          <div class="ep-progress-stats">
            <span class="ep-stat pass">
              <CheckCircle :size="12" /> {{ passCount }} {{ $t('exec.pass') }}
            </span>
            <span class="ep-stat fail">
              <XCircle :size="12" /> {{ failCount }} {{ $t('exec.fail') }}
            </span>
            <span v-if="skipCount > 0" class="ep-stat skip">
              <MinusCircle :size="12" /> {{ skipCount }} {{ $t('exec.skip') }}
            </span>
            <span class="ep-stat-progress-pct">{{ totalSteps > 0 ? Math.round((doneCount / totalSteps) * 100) : 0 }}%</span>
            <span class="ep-stat-time">
              <Clock :size="12" /> {{ formatDuration(duration) }}
            </span>
          </div>
        </div>

        <!-- Main content: split layout -->
        <div class="ep-content">
          <!-- Left: step list (timeline style) -->
          <div class="ep-steps-panel">
            <div class="ep-steps-header">
              <span>{{ $t('exec.steps') }}</span>
              <span class="ep-steps-count">{{ doneCount }}/{{ totalSteps }}</span>
              <button v-if="collapsedCount > 0 && !showAllSteps" class="ep-toggle-btn" @click="showAllSteps = true" :title="$t('exec.expandAll')">
                {{ $t('exec.moreSteps', { count: collapsedCount }) }}
              </button>
              <button v-else-if="showAllSteps && steps.length > STEP_COLLAPSE_THRESHOLD" class="ep-toggle-btn" @click="showAllSteps = false" :title="$t('exec.collapse')">
                {{ $t('exec.collapse') }}
              </button>
            </div>
            <div class="ep-steps-list">
              <div
                v-for="(step, i) in displaySteps"
                :key="'step-' + i + '-' + step.name"
                class="ep-step"
                :class="[
                  'ep-step--' + (step.status === 'error' ? 'failed' : step.status),
                  { active: currentStepIndex === i }
                ]"
              >
                <div class="ep-step-icon-col">
                  <span class="ep-step-icon">{{ stepIcon(step.status) }}</span>
                </div>
                <div class="ep-step-body">
                  <div class="ep-step-row">
                    <span class="ep-step-method-tag" :class="'method-' + (step.method || 'get').toLowerCase()">{{ step.method || 'GET' }}</span>
                    <span class="ep-step-name">{{ step.name }}</span>
                    <span class="ep-step-meta">
                      <template v-if="step.status === 'running'">
                        <span class="ep-step-spinner" />
                      </template>
                      <template v-else-if="step.status === 'success' || step.status === 'failed' || step.status === 'error'">
                        <span class="ep-step-duration">{{ step.duration_ms || 0 }}ms</span>
                      </template>
                    </span>
                  </div>
                  <div v-if="step.assertion_summary && step.assertion_summary.length > 0" class="ep-step-assertions">
                    <span
                      v-for="(a, ai) in step.assertion_summary"
                      :key="ai"
                      class="ep-assertion-chip"
                      :class="a.passed ? 'pass' : 'fail'"
                    >
                      {{ a.type }} {{ a.op }} {{ a.expected }}
                    </span>
                  </div>
                  <div v-if="step.error_message" class="ep-step-error">
                    {{ step.error_message }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: current step detail (enhanced) -->
          <div class="ep-detail-panel">
            <template v-if="currentStep">
              <div class="ep-detail-header">
                <span class="ep-detail-method" :class="'method-' + (currentStep.method || 'get').toLowerCase()">
                  {{ currentStep.method || 'GET' }}
                </span>
                <span class="ep-detail-name">{{ currentStep.name }}</span>
                <span v-if="currentStep.response_status" class="ep-status-badge"
                  :class="currentStep.response_status < 400 ? 'success' : 'fail'">
                  {{ currentStep.response_status }}
                </span>
              </div>

              <!-- Request section -->
              <div class="ep-detail-section">
                <div class="ep-section-label">
                  <ArrowUp :size="12" /> {{ $t('exec.request') }}
                  <span v-if="currentStep.duration_ms" class="ep-duration">{{ currentStep.duration_ms }}ms</span>
                </div>
                <div class="ep-section-content">
                  <div class="ep-url">{{ currentStep.request_url || '...' }}</div>
                  <div v-if="currentStep.request_headers" class="ep-req-headers">
                    <div v-for="(h, hi) in parseHeaders(currentStep.request_headers)" :key="hi" class="ep-req-header">
                      <span class="ep-h-key">{{ h.key }}:</span>
                      <span class="ep-h-val">{{ h.val }}</span>
                    </div>
                  </div>
                  <div v-if="currentStep.request_body" class="ep-code-block">
                    <pre>{{ truncateBody(currentStep.request_body) }}</pre>
                  </div>
                </div>
              </div>

              <!-- Response section -->
              <div class="ep-detail-section">
                <div class="ep-section-label">
                  <ArrowDown :size="12" /> {{ $t('exec.response') }}
                  <template v-if="currentStep.response_status">
                    <span class="ep-status-code" :class="currentStep.response_status < 400 ? 'success' : 'fail'">
                      {{ currentStep.response_status }}
                    </span>
                  </template>
                  <template v-else-if="currentStep.status === 'running'">
                    <span class="ep-waiting-badge">{{ $t('exec.waiting') }}</span>
                  </template>
                </div>
                <div class="ep-section-content">
                  <template v-if="currentStep.response_body">
                    <div class="ep-code-block">
                      <pre>{{ truncateBody(currentStep.response_body, 500) }}</pre>
                    </div>
                  </template>
                  <template v-else-if="currentStep.status === 'running'">
                    <div class="ep-waiting-msg">
                      <span class="ep-step-spinner" /> {{ $t('exec.waitingResponse') }}
                    </div>
                  </template>
                  <template v-else>
                    <div class="ep-empty-msg">{{ $t('exec.noResponse') }}</div>
                  </template>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="ep-detail-empty">
                <div class="ep-empty-icon">⚡</div>
                <div class="ep-empty-text">{{ $t('exec.waitingExecution') }}</div>
              </div>
            </template>
          </div>
        </div>

        <!-- Footer -->
        <div class="ep-footer">
          <button v-if="isCompleted" class="ep-btn ep-btn--primary" @click="emit('viewReport')">
            {{ $t('exec.viewReport') }}
          </button>
          <button v-if="isCompleted" class="ep-btn ep-btn--secondary" @click="emit('rerun')">
            <RefreshCw :size="14" /> {{ $t('exec.rerun') }}
          </button>
          <button class="ep-btn ep-btn--ghost" @click="emit('minimize')">{{ $t('exec.minimize') }}</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Square, CheckCircle, XCircle, MinusCircle, Clock, ArrowUp, ArrowDown, RefreshCw } from 'lucide-vue-next'

interface AssertionSummary {
  type: string
  op: string
  expected: unknown
  actual?: unknown
  passed: boolean
}

interface Step {
  name: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'skipped' | 'error'
  duration_ms?: number
  method?: string
  request_url?: string
  request_headers?: string
  request_body?: string
  response_status?: number
  response_headers?: string
  response_body?: string
  assertion_summary?: AssertionSummary[]
  error_message?: string
}

interface Props {
  visible: boolean
  sceneName: string
  steps?: Step[]
  totalSteps?: number
  doneCount?: number
  passCount?: number
  failCount?: number
  skipCount?: number
  duration?: number
  reportStatus?: 'running' | 'success' | 'failed' | ''
  currentStepIndex?: number
}

const props = withDefaults(defineProps<Props>(), {
  steps: () => [],
  totalSteps: 0,
  doneCount: 0,
  passCount: 0,
  failCount: 0,
  skipCount: 0,
  duration: 0,
  reportStatus: '',
  currentStepIndex: -1,
})

const emit = defineEmits<{
  close: []
  cancel: []
  viewReport: []
  minimize: []
  rerun: []
}>()

const isCompleted = computed(() =>
  props.reportStatus === 'success' || props.reportStatus === 'failed'
)

// 大步骤量优化：当步骤数超过阈值时，优先显示失败/错误步骤
const STEP_COLLAPSE_THRESHOLD = 30
const showAllSteps = ref(false)

const displaySteps = computed(() => {
  if (showAllSteps.value || props.steps.length <= STEP_COLLAPSE_THRESHOLD) {
    return props.steps
  }
  // 非全部显示时：优先展示失败/错误/运行中的步骤
  const important = props.steps.filter(s => s.status === 'failed' || s.status === 'error' || s.status === 'running')
  const pending = props.steps.filter(s => s.status === 'pending')
  // 显示重要步骤 + pending 的前后各3个（避免列表过长）
  const pendingToShow = pending.slice(0, 3).concat(pending.slice(-3))
  return [...important, ...pendingToShow]
})

const collapsedCount = computed(() => {
  if (showAllSteps.value || props.steps.length <= STEP_COLLAPSE_THRESHOLD) return 0
  return props.steps.length - displaySteps.value.length
})

const currentStep = computed(() => {
  if (props.currentStepIndex >= 0 && props.currentStepIndex < props.steps.length) {
    return props.steps[props.currentStepIndex]
  }
  return props.steps.find(s => s.status === 'running') || null
})

const statusClass = computed(() => {
  if (props.reportStatus === 'success') return 'success'
  if (props.reportStatus === 'failed') return 'failed'
  return 'running'
})

const statusIcon = computed(() => {
  if (props.reportStatus === 'success') return '✓'
  if (props.reportStatus === 'failed') return '✗'
  return '⚡'
})

function stepIcon(status: string) {
  if (status === 'success') return '✓'
  if (status === 'failed' || status === 'error') return '✗'
  if (status === 'running') return '⚡'
  if (status === 'skipped') return '⊘'
  return '○'
}

function formatDuration(sec: number) {
  if (!sec) return '0ms'
  if (sec < 1) return (sec * 1000).toFixed(0) + 'ms'
  return sec.toFixed(1) + 's'
}

function parseHeaders(headersStr: string) {
  try {
    const arr = JSON.parse(headersStr)
    return arr.map((h: { key?: string; name?: string; value?: string; val?: string }) => ({ key: h.key || h.name || '', val: h.value || h.val || '' }))
  } catch {
    return []
  }
}

function truncateBody(body: string, maxLen = 200) {
  if (!body) return ''
  const str = typeof body === 'string' ? body : JSON.stringify(body)
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen) + '...'
}
</script>

<style scoped>
/* ==========================================
 * ExecutionProgress 样式
 * 使用 design tokens 确保主题一致性
 * ========================================== */

/* 遮罩层：使用语义化 alpha 和 z-index tokens */
.ep-overlay {
  position: fixed;
  inset: 0;
  background: var(--alpha-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
  animation: fadeIn var(--duration-fast) var(--ease-out);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 主面板：使用卡片表面和阴影 tokens */
.ep-panel {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  width: 960px;
  max-width: min(960px, 95vw);
  height: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  animation: fadeIn var(--duration-slow) var(--ease-out);
  overflow: hidden;
}

/* ===== 头部区域 ===== */
.ep-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-nested);
}

.ep-header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.ep-title {
  font-size: var(--font-size-base);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
}

/* 状态图标：圆形背景 + 语义色 */
.ep-icon {
  width: 32px;
  height: 32px;
  min-width: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-bold);
}
.ep-icon.success { background: var(--color-success-alpha-10); color: var(--success); }
.ep-icon.failed { background: var(--color-error-alpha-10); color: var(--error); }
.ep-icon.running { background: var(--color-primary-alpha-10); color: var(--primary-500); }

.ep-header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* 停止按钮：危险色 + 悬停动效 */
.ep-btn-stop {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--error);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-smooth);
}
.ep-btn-stop:hover {
  background: var(--error-dark);
  transform: translateY(-1px);
}

/* 图标按钮：透明背景 + 悬停高亮 */
.ep-btn-icon {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
}
.ep-btn-icon:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

/* ===== 进度条区域 ===== */
.ep-progress {
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--border-subtle);
}

.ep-progress-bar {
  height: 6px;
  background: var(--surface-hover);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

/* 进度填充：主色渐变 + 光泽动画 */
.ep-progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--primary-500);
  transition: width 200ms var(--ease-out);
  position: relative;
  overflow: hidden;
}

/* 完成时短暂高光闪烁 */
.ep-progress-fill.is-complete::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, var(--color-white-alpha-50) 50%, transparent 100%);
  animation: progressShine 700ms ease-out;
  pointer-events: none;
}

/* 光泽动画伪元素 */
.ep-progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, var(--color-white-alpha-30), transparent);
  animation: progressShine 2s infinite;
}

/* 有失败步骤时使用成功→失败渐变 */
.ep-progress-fill.has-fail {
  background: linear-gradient(90deg, var(--success), var(--error));
}

@keyframes progressShine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 进度统计：等宽数字防止抖动 */
.ep-progress-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-sm);
}

.ep-stat {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
}

.ep-stat.pass { color: var(--success); }
.ep-stat.fail { color: var(--error); }
.ep-stat.skip { color: var(--text-muted); }
.ep-stat-time { color: var(--text-secondary); margin-left: auto; }

.ep-stat-progress-pct {
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  letter-spacing: var(--tracking-tight);
}

/* ===== 内容分栏布局 ===== */
.ep-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ===== 左侧：时间线步骤面板 ===== */
.ep-steps-panel {
  width: 40%;
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ep-steps-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-nested);
}

.ep-steps-count {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* 展开/折叠按钮 */
.ep-toggle-btn {
  font-size: var(--font-size-2xs);
  color: var(--primary-600);
  background: none;
  border: 1px solid var(--primary-200);
  border-radius: var(--radius-sm);
  padding: 2px var(--spacing-sm);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth);
}
.ep-toggle-btn:hover {
  background: var(--color-primary-alpha-08);
}

.ep-steps-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm) 0;
  position: relative;
  padding-left: 0;
}

/* 时间线竖直连接线 */
.ep-steps-list::before {
  content: '';
  position: absolute;
  left: 24px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--border-subtle);
  z-index: 0;
}

/* 步骤项 */
.ep-step {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-lg);
  transition: background-color var(--duration-fast) var(--ease-smooth);
  position: relative;
  min-height: 40px;
}
.ep-step:hover { background: var(--surface-hover); }
.ep-step.active { background: var(--color-primary-alpha-04); }

/* 图标列：包含圆点和连接线 */
.ep-step-icon-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  padding-top: 4px;
}

/* 步骤图标：圆形边框 + 状态色 */
.ep-step-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-bold);
  border: 2px solid var(--border-subtle);
  background: var(--surface-card);
  position: relative;
  z-index: 1;
  transition: border-color var(--duration-base) var(--ease-smooth),
              background-color var(--duration-base) var(--ease-smooth);
}

/* 步骤状态图标样式 */
.ep-step--success .ep-step-icon {
  border-color: var(--success);
  background: var(--color-success-alpha-10);
  color: var(--success);
}
.ep-step--failed .ep-step-icon {
  border-color: var(--error);
  background: var(--color-error-alpha-10);
  color: var(--error);
}
.ep-step--running .ep-step-icon {
  border-color: var(--primary-400);
  background: var(--color-primary-alpha-06);
  color: var(--primary-500);
}
.ep-step--skipped .ep-step-icon {
  border-color: var(--text-disabled);
  color: var(--text-muted);
}

/* 步骤主体 */
.ep-step-body {
  flex: 1;
  min-width: 0;
}

.ep-step-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* HTTP 方法标签：等宽字体 + 语义色 */
.ep-step-method-tag {
  display: inline-flex;
  align-items: center;
  font-size: 9px;
  font-weight: var(--weight-bold);
  padding: 1px var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  flex-shrink: 0;
  line-height: 1.4;
}

.ep-step-name {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ep-step--running .ep-step-name { color: var(--primary-600); }

.ep-step-meta {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.ep-step-duration {
  color: var(--text-secondary);
}

/* 加载动画旋转图标 */
.ep-step-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--color-primary-alpha-16);
  border-top-color: var(--primary-500);
  border-radius: 50%;
  animation: spin var(--duration-slow) linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 断言摘要标签 */
.ep-step-assertions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
}

.ep-assertion-chip {
  font-size: var(--font-size-2xs);
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}
.ep-assertion-chip.pass { background: var(--color-success-alpha-10); color: var(--success); }
.ep-assertion-chip.fail { background: var(--color-error-alpha-10); color: var(--error); }

/* 步骤错误信息 */
.ep-step-error {
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--error);
  opacity: 0.85;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 右侧：详情面板 ===== */
.ep-detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-nested);
}

.ep-detail-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-subtle);
}

/* 详情面板方法标签 */
.ep-detail-method {
  font-size: var(--font-size-xs);
  font-weight: var(--weight-bold);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

.ep-detail-name {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 状态码徽章 */
.ep-status-badge {
  font-size: var(--font-size-base);
  font-weight: var(--weight-semibold);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.ep-status-badge.success { background: var(--color-success-alpha-10); color: var(--success); }
.ep-status-badge.fail { background: var(--color-error-alpha-10); color: var(--error); }

.ep-detail-section {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-bottom: 1px solid var(--border-subtle);
}

.ep-section-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.ep-duration {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.ep-status-code {
  margin-left: auto;
  font-size: var(--font-size-base);
  font-weight: var(--weight-semibold);
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.ep-status-code.success { background: var(--color-success-alpha-10); color: var(--success); }
.ep-status-code.fail { background: var(--color-error-alpha-10); color: var(--error); }

.ep-waiting-badge {
  margin-left: auto;
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
}

/* 内容区域：卡片表面 */
.ep-section-content {
  background: var(--surface-card);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.ep-url {
  padding: var(--spacing-sm) var(--spacing-md);
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
  word-break: break-all;
}

.ep-req-headers {
  padding: var(--spacing-xs) var(--spacing-md);
  border-bottom: 1px solid var(--border-subtle);
}

.ep-req-header {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-xs);
}
.ep-h-key { color: var(--primary-600); }
.ep-h-val { color: var(--text-secondary); margin-left: var(--spacing-xs); }

/* 代码块：等宽字体 + 滚动 */
.ep-code-block {
  padding: var(--spacing-md);
  max-height: 140px;
  overflow-y: auto;
}

.ep-code-block pre {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
  line-height: var(--leading-relaxed);
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  tab-size: 2;
}

.ep-waiting-msg,
.ep-empty-msg {
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--font-size-sm);
}

.ep-waiting-msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
}

.ep-empty-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-sm);
}

.ep-detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* ===== 底部按钮区域 ===== */
.ep-footer {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: flex-end;
  padding: var(--spacing-md) var(--spacing-xl);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
}

/* 通用按钮样式 */
.ep-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  border: 1px solid var(--border-default);
  background: var(--surface-card);
  color: var(--text-secondary);
  transition: background-color var(--duration-base) var(--ease-smooth),
              color var(--duration-base) var(--ease-smooth),
              transform var(--duration-base) var(--ease-smooth),
              box-shadow var(--duration-base) var(--ease-smooth);
}
.ep-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

/* 主要按钮：主色背景 + 阴影 */
.ep-btn--primary {
  background: var(--primary-600);
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-primary-alpha-25);
}
.ep-btn--primary:hover {
  background: var(--primary-700);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px var(--color-primary-alpha-30);
}

/* 次要按钮：主色边框 */
.ep-btn--secondary {
  border-color: var(--primary-200);
  color: var(--primary-600);
}
.ep-btn--secondary:hover {
  background: var(--color-primary-alpha-06);
  color: var(--primary-700);
}

/* 幽灵按钮：透明背景 */
.ep-btn--ghost {
  background: transparent;
  border: none;
  color: var(--text-muted);
}
.ep-btn--ghost:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

/* ===== HTTP 方法颜色（统一使用 tokens）===== */
.method-get { background: var(--method-get-bg); color: var(--method-get-text); }
.method-post { background: var(--method-post-bg); color: var(--method-post-text); }
.method-put { background: var(--method-put-bg); color: var(--method-put-text); }
.method-delete { background: var(--method-delete-bg); color: var(--method-delete-text); }
.method-patch { background: var(--method-patch-bg); color: var(--method-patch-text); }
.method-head { background: var(--method-head-bg); color: var(--method-head-text); }
.method-options { background: var(--method-options-bg); color: var(--method-options-text); }

/* ===== 暗色模式适配 ===== */
html.dark .ep-panel {
  background: var(--surface-card);
  border-color: var(--border-strong);
}
html.dark .ep-header {
  background: var(--surface-nested);
  border-bottom-color: var(--border-strong);
}
html.dark .ep-title { color: var(--text-primary); }
html.dark .ep-steps-panel { border-right-color: var(--border-strong); }
html.dark .ep-steps-header {
  background: var(--surface-nested);
  color: var(--text-muted);
}
html.dark .ep-steps-list::before { background: var(--border-strong); }
html.dark .ep-step:hover { background: var(--surface-hover); }
html.dark .ep-step.active { background: var(--color-primary-alpha-08); }
html.dark .ep-step-name { color: var(--text-primary); }
html.dark .ep-step--running .ep-step-name { color: var(--primary-400); }
html.dark .ep-step-icon {
  background: var(--surface-card);
  border-color: var(--border-strong);
}
html.dark .ep-detail-panel { background: var(--surface-nested); }
html.dark .ep-detail-header { border-bottom-color: var(--border-strong); }
html.dark .ep-detail-name { color: var(--text-primary); }
html.dark .ep-detail-section { border-bottom-color: var(--border-strong); }
html.dark .ep-section-content { background: var(--surface-card); }
html.dark .ep-url {
  color: var(--text-primary);
  border-bottom-color: var(--border-strong);
}
html.dark .ep-code-block pre { color: var(--text-secondary); }
html.dark .ep-footer {
  background: var(--surface-card);
  border-top-color: var(--border-strong);
}
html.dark .ep-btn {
  background: var(--surface-nested);
  border-color: var(--border-strong);
  color: var(--text-secondary);
}
html.dark .ep-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
html.dark .ep-btn--primary {
  background: var(--primary-500);
  color: var(--text-inverse);
  border: none;
}
html.dark .ep-btn--primary:hover { background: var(--primary-400); }
html.dark .ep-btn--secondary {
  border-color: var(--primary-400);
  color: var(--primary-400);
}
html.dark .ep-btn--secondary:hover {
  background: var(--color-primary-alpha-10);
  color: var(--primary-300);
}
html.dark .ep-btn--ghost {
  background: transparent;
  color: var(--text-muted);
}
html.dark .ep-btn--ghost:hover {
  background: var(--surface-hover);
  color: var(--text-secondary);
}
html.dark .ep-btn-stop { background: var(--error-dark); }
html.dark .ep-btn-stop:hover { background: var(--error); }
</style>