<template>
  <div>
    <Teleport to="body">
      <div v-if="visible" class="cd-overlay" @click.self="onCancel" role="dialog" aria-modal="true" :aria-label="displayTitle">
        <div ref="dialogRef" class="cd-dialog" :style="{ width }">
          <div class="cd-header" :class="{ 'cd-header--Danger': dangerIcon }">
            <span class="cd-title" :class="{ 'cd-title--danger': dangerIcon }">
              <alert-triangle v-if="dangerIcon" :size="18" class="cd-danger-icon" />
              {{ displayTitle }}
            </span>
            <button class="cd-close" @click="onCancel">&times;</button>
          </div>
          <div class="cd-body">
            <p class="cd-message">{{ displayMessage }}</p>
            <div v-if="confirmInput !== null" class="cd-confirm-input">
              <p class="cd-input-hint">{{ $t('dialog.inputHint', { value: confirmInput }) }}</p>
              <input v-model="inputValue" class="input" :placeholder="$t('dialog.inputPlaceholder', { value: confirmInput })" />
            </div>
          </div>
          <div class="cd-footer">
            <button class="btn btn-ghost" :disabled="loading" @click="onCancel">{{ displayCancelText }}</button>
            <button
              class="btn"
              :class="[type === 'danger' ? 'btn-danger' : 'btn-primary', { 'is-loading': loading }]"
              :disabled="loading || (confirmInput !== null && inputValue !== confirmInput)"
              @click="onConfirm"
            >
              <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
              {{ displayConfirmText }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle } from 'lucide-vue-next'

const { t } = useI18n()

interface Props {
  visible: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  type?: 'info' | 'danger'
  width?: string
  dangerIcon?: boolean
  confirmInput?: string | null
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  message: '',
  confirmText: '',
  cancelText: '',
  type: 'info',
  width: '420px',
  dangerIcon: false,
  confirmInput: null,
  loading: false,
})

const displayTitle = computed(() => props.title ?? t('dialog.defaultTitle'))
const displayMessage = computed(() => props.message ?? t('dialog.defaultMessage'))
const displayConfirmText = computed(() => props.confirmText ?? t('dialog.confirmBtn'))
const displayCancelText = computed(() => props.cancelText ?? t('dialog.cancelBtn'))

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const inputValue = ref('')
const dialogRef = ref<HTMLElement | null>(null)
let previousFocusEl: Element | null = null

// Focus trap: get all focusable elements inside the dialog
function getFocusableElements(): HTMLElement[] {
  if (!dialogRef.value) return []
  const selectors = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  return Array.from(dialogRef.value.querySelectorAll<HTMLElement>(selectors))
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (props.loading) return
    e.preventDefault()
    onCancel()
    return
  }

  if (e.key === 'Enter' && !e.shiftKey) {
    const target = e.target as HTMLElement
    if (target.tagName === 'TEXTAREA') return
    if (props.loading) return
    if (props.confirmInput !== null && inputValue.value !== props.confirmInput) return
    e.preventDefault()
    onConfirm()
    return
  }

  if (e.key !== 'Tab') return
  const focusable = getFocusableElements()
  if (focusable.length === 0) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault()
      last.focus()
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

watch(() => props.visible, (v) => {
  if (v) {
    // Store the previously focused element for focus return
    previousFocusEl = document.activeElement
    inputValue.value = ''
    // Auto-focus: focus the confirm button (or input if confirmInput is set)
    void nextTick(() => {
      if (props.confirmInput !== null) {
        const input = dialogRef.value?.querySelector<HTMLInputElement>('.cd-confirm-input .input')
        input?.focus()
      } else {
        const confirmBtn = dialogRef.value?.querySelector<HTMLButtonElement>('.cd-footer .btn-primary, .cd-footer .btn-danger')
        confirmBtn?.focus()
      }
    })
    document.addEventListener('keydown', onKeyDown)
  } else {
    document.removeEventListener('keydown', onKeyDown)
    // Focus return: restore focus to the element that had focus before the dialog opened
    if (previousFocusEl && 'focus' in previousFocusEl) {
      (previousFocusEl as HTMLElement).focus()
    }
    previousFocusEl = null
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
})

function onConfirm() {
  emit('confirm')
  emit('update:visible', false)
}

function onCancel() {
  emit('cancel')
  emit('update:visible', false)
}
</script>

<style scoped>
/* ===== 遮罩层 — 使用 z-modal 层级 + 品牌化模糊 ===== */
.cd-overlay {
  position: fixed;
  inset: 0;
  /* 遮罩色使用 alpha token 确保暗色模式一致 */
  background: var(--color-black-alpha-45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  animation: cdFadeIn var(--duration-fast) var(--ease-out);
}

@keyframes cdFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ===== 弹窗主体 — 品牌化 + 多层阴影 ===== */
.cd-dialog {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: var(--space-7);
  /* 使用 shadow-float token 替代硬编码阴影 */
  box-shadow: var(--shadow-float);
  animation: cdCardIn var(--duration-slow) var(--ease-out);
  width: 420px;
  max-width: 90vw;
  position: relative;
  overflow: hidden;
}
/* 顶部品牌渐变装饰条 */
.cd-dialog::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--grad-primary);
  opacity: 0.5;
}

@keyframes cdCardIn {
  from { opacity: 0; transform: scale(0.95) translateY(6px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* ===== 头部 ===== */
.cd-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}
/* 危险类型头部底部分隔线 */
.cd-header--danger {
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-error-alpha-08);
}

.cd-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  letter-spacing: var(--tracking-tight);
}
.cd-title--danger {
  color: var(--error);
}

/* 危险图标容器 — 带背景色 */
.cd-danger-icon {
  color: var(--error);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--color-error-alpha-08);
  flex-shrink: 0;
}

/* 关闭按钮 — 旋转 hover 效果 */
.cd-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-lg);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth),
    transform var(--duration-fast) var(--ease-spring);
  line-height: 1;
}
.cd-close:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  transform: scale(1.08) rotate(90deg);
}
.cd-close:active {
  transform: scale(0.92) rotate(90deg);
}
/* 键盘焦点可见环 */
.cd-close:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}

/* ===== 内容区 ===== */
.cd-body {
  margin-bottom: var(--space-6);
}

.cd-message {
  font-size: var(--text-base);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
}

/* 确认输入区域 — 嵌套表面 */
.cd-confirm-input {
  margin-top: var(--space-4);
  padding: var(--space-3);
  background: var(--surface-nested);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  transition: border-color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth);
}
.cd-confirm-input:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-08);
}

.cd-input-hint {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-2);
  font-weight: var(--weight-medium);
}
.cd-input-hint strong {
  color: var(--primary-600);
  font-weight: var(--weight-bold);
  padding: 0 2px;
}

/* 输入框 — 与全局 el-input 风格统一 */
.cd-confirm-input .input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-family: inherit;
  color: var(--text-primary);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  outline: none;
  transition:
    border-color var(--duration-fast) var(--ease-smooth),
    box-shadow var(--duration-fast) var(--ease-smooth);
  box-sizing: border-box;
  line-height: var(--leading-normal);
}
.cd-confirm-input .input::placeholder {
  color: var(--text-muted);
}
.cd-confirm-input .input:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-alpha-10);
}

/* ===== 底部按钮区 ===== */
.cd-footer {
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}

/* 统一按钮基础样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: 8px 20px;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  font-family: inherit;
  line-height: var(--leading-normal);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-base) var(--ease-out),
    background-color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
  min-height: 36px;
}
.btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.btn:active:not(:disabled) {
  transform: translateY(0) scale(var(--press-scale, 0.97));
}
/* 键盘焦点可见环 */
.btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}

/* Ghost / Cancel 按钮 */
.btn-ghost {
  background: var(--surface-hover);
  color: var(--text-secondary);
  border-color: var(--border-default);
}
.btn-ghost:hover {
  background: var(--surface-nested);
  color: var(--text-primary);
  border-color: var(--color-neutral-alpha-14, var(--border-strong));
  box-shadow: var(--shadow-xs);
}

/* Primary 按钮 — 渐变背景 + 主色阴影 */
.btn-primary {
  background: var(--grad-primary);
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-primary-alpha-16);
}
.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 16px var(--color-primary-alpha-24), 0 2px 6px var(--color-primary-alpha-12);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Danger 按钮 — 渐变红色背景 */
.btn-danger {
  background: linear-gradient(135deg, var(--error), var(--error-dark));
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-error-alpha-15);
}
.btn-danger:hover:not(:disabled) {
  box-shadow: 0 4px 16px var(--color-error-alpha-20), 0 2px 6px var(--color-error-alpha-10);
}
.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 按钮加载状态 */
.btn.is-loading {
  opacity: 0.7;
  pointer-events: none;
  cursor: default;
  position: relative;
}

.btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  margin-right: var(--space-2);
  animation: btnSpin 0.9s linear infinite;
}

@keyframes btnSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Ghost 按钮的禁用状态 */
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ===== 暗色模式适配 ===== */
html.dark .cd-overlay {
  background: var(--color-black-alpha-60);
}
html.dark .cd-dialog {
  /* 暗色模式使用 shadow-float token（已含微发光） */
  box-shadow: var(--shadow-float);
}
html.dark .cd-dialog::before {
  opacity: 0.3;
}
html.dark .cd-header--danger {
  border-bottom-color: var(--color-error-alpha-10);
}
html.dark .cd-danger-icon {
  background: var(--color-error-alpha-10);
}
html.dark .cd-close:hover {
  background: var(--color-white-alpha-06);
}
html.dark .cd-confirm-input {
  background: var(--color-white-alpha-05);
  border-color: var(--border-default);
}
html.dark .cd-confirm-input:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 3px var(--color-primary-alpha-10);
}
html.dark .cd-confirm-input .input {
  background: var(--color-white-alpha-06);
  border-color: var(--border-default);
  color: var(--text-primary);
}
html.dark .cd-confirm-input .input:focus {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 2px var(--color-primary-alpha-12);
}
html.dark .btn-ghost {
  background: var(--color-white-alpha-06);
  color: var(--text-secondary);
  border-color: var(--border-default);
}
html.dark .btn-ghost:hover {
  background: var(--color-white-alpha-10);
  color: var(--text-primary);
}

/* ===== 无障碍：减少动画偏好 ===== */
@media (prefers-reduced-motion: reduce) {
  .cd-overlay,
  .cd-dialog,
  .cd-close,
  .btn {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>