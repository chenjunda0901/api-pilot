<template>
  <!-- 统一根元素，消除 Vue 多根片段导致的 Extraneous attrs 警告 -->
  <div v-bind="$attrs" role="alert" aria-live="assertive">
    <slot v-if="!error" />
    <div v-else class="error-boundary">
    <div class="error-boundary-card">
      <div class="error-icon-wrap" aria-hidden="true">
        <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
          <circle cx="28" cy="28" r="26" stroke="var(--warning)" stroke-width="1.5" fill="var(--warning-bg)" opacity="0.6" />
          <circle cx="28" cy="28" r="20" stroke="var(--warning)" stroke-width="1" fill="none" opacity="0.3" />
          <path d="M28 18v12" stroke="var(--warning)" stroke-width="2.5" stroke-linecap="round" />
          <circle cx="28" cy="36" r="2" fill="var(--warning)" />
        </svg>
      </div>
      <h3 class="error-title" id="error-boundary-title">{{ $t('error.title') }}</h3>
      <p class="error-desc" id="error-boundary-desc">{{ error.message || $t('error.unknownError') }}</p>
      <div class="error-actions">
        <button class="error-btn error-btn-primary" @click="retry" :aria-label="$t('error.retry')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M1 4v6h6" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
          </svg>
          {{ $t('error.retry') }}
        </button>
        <button class="error-btn error-btn-ghost" @click="goHome" :aria-label="$t('error.goHome')">{{ $t('error.goHome') }}</button>
        <button class="error-btn error-btn-text" @click="copyError" v-if="copied !== true" :aria-label="$t('error.copyError')">{{ $t('error.copyError') }}</button>
        <span v-else class="copied-hint" role="status">{{ $t('error.copied') }} ✓</span>
      </div>
      <details class="error-details" v-if="error.stack">
        <summary class="error-details-toggle">{{ $t('error.techDetails') }}</summary>
        <pre class="error-stack" tabindex="0">{{ error.stack }}</pre>
      </details>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { logger } from '@/utils/logger'

defineOptions({ inheritAttrs: false })

const error = ref<Error | null>(null)
const copied = ref<boolean | null>(null)
const router = useRouter()
const retryCount = ref(0)
const retryTimers: ReturnType<typeof setTimeout>[] = []
const copyTimer = ref<ReturnType<typeof setTimeout> | null>(null)

onErrorCaptured((err: Error) => {
  // 自动重试机制（解决懒加载大 chunk 时的模块加载竞态问题）
  if (retryCount.value < 3) {
    retryCount.value++
    logger.warn(`[ErrorBoundary] 重试 #${retryCount.value}:`, err.message)
    err.preventDefault?.()
    // 渐进延迟：150ms → 300ms → 500ms，给 Vue 足够的 setup 时间
    const delay = retryCount.value * 150 + (retryCount.value > 1 ? 100 : 0)
    const timer = setTimeout(() => { error.value = null }, Math.min(delay, 600))
    retryTimers.push(timer)
    return false
  }
  error.value = err
  logger.error('[ErrorBoundary] 最终失败（已重试 3 次）:', err)
  return false
})

function retry() {
  error.value = null
  retryCount.value = 0
}

function goHome() {
  error.value = null
  void router.push('/dashboard')
}

async function copyError() {
  if (!error.value) return
  const lines = [
    '[ErrorBoundary] ' + (error.value.message || ''),
    '',
    error.value.stack || '',
  ]
  const text = lines.join('\n')
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    if (copyTimer.value) clearTimeout(copyTimer.value)
    copyTimer.value = setTimeout(() => { copied.value = null }, 2000)
  } catch {
    // clipboard API 不可用时静默失败
  }
}

onBeforeUnmount(() => {
  retryTimers.forEach(timer => clearTimeout(timer))
  if (copyTimer.value) clearTimeout(copyTimer.value)
})
</script>

<style scoped>
/* ── ErrorBoundary v2：专业、友好的错误兜底界面
   设计要点：
   - 居中卡片布局，视觉焦点集中
   - 警告图标使用 SVG 绘制，避免依赖外部图标库
   - 三级操作按钮：主按钮（重试）、次按钮（返回首页）、文字按钮（复制错误）
   - 可折叠的技术详情，方便开发者排查问题
   - 全部使用 design tokens，暗色模式自动适配
   ─────────────────────────────── */

/* 容器：全屏居中 */
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--spacing-2xl);
  background: var(--surface-bg);
}

/* 卡片主体 */
.error-boundary-card {
  text-align: center;
  max-width: 420px;
  padding: var(--spacing-5xl) var(--spacing-3xl);
  background: var(--surface-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-float);
  border: 1px solid var(--border-subtle);
}

/* 警告图标容器 */
.error-icon-wrap {
  margin-bottom: var(--spacing-xl);
  display: inline-block;
}

/* 标题 */
.error-title {
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--spacing-sm);
  line-height: var(--leading-tight);
}

/* 描述文字 */
.error-desc {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  margin: 0 0 var(--spacing-2xl);
  line-height: var(--leading-normal);
  word-break: break-word;
}

/* 操作按钮组 */
.error-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

/* 按钮基础样式 */
.error-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: var(--transition-base);
  border: none;
  line-height: var(--leading-normal);
}

/* 主按钮：渐变背景 + 阴影 */
.error-btn-primary {
  background: var(--grad-primary);
  color: var(--text-inverse);
  box-shadow: var(--shadow-sm);
}

.error-btn-primary:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-1px);
}

.error-btn-primary:active {
  transform: translateY(0);
}

/* 幽灵按钮：透明背景 + 边框 */
.error-btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.error-btn-ghost:hover {
  background: var(--surface-hover);
  border-color: var(--border-strong);
}

/* 文字按钮：无背景无边框 */
.error-btn-text {
  background: transparent;
  color: var(--text-muted);
  padding: var(--spacing-xs) var(--spacing-sm);
}

.error-btn-text:hover {
  color: var(--text-secondary);
}

/* 复制成功提示 */
.copied-hint {
  font-size: var(--font-size-sm);
  color: var(--success-text);
}

/* 技术详情容器 */
.error-details {
  margin-top: var(--spacing-xl);
  text-align: left;
}

/* 详情开关 */
.error-details-toggle {
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  transition: color var(--duration-fast);
}

.error-details-toggle:hover {
  color: var(--text-secondary);
}

/* 错误堆栈 */
.error-stack {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-family: var(--font-mono);
  line-height: var(--leading-normal);
  color: var(--text-muted);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
}

/* 滚动条样式 */
.error-stack::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.error-stack::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-full);
}

.error-stack::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* 暗色模式 */
:global(html.dark) .error-boundary { background: var(--surface-bg); }
:global(html.dark) .error-boundary-card { background: var(--surface-card); border-color: var(--border-subtle); }
:global(html.dark) .error-stack { background: var(--surface-nested); border-color: var(--border-subtle); }
</style>