<template>
  <div class="loading-bar-container" :class="{ active }">
    <!-- 顶部进度条 -->
    <div class="loading-bar" aria-hidden="true">
      <div class="loading-bar-progress" />
    </div>
    <!-- 旋转加载指示器（可选） -->
    <div v-if="showSpinner" class="loading-spinner">
      <svg class="spinner-icon" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" opacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="3" stroke-linecap="round" />
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  showSpinner?: boolean
}

withDefaults(defineProps<Props>(), {
  showSpinner: false,
})

const active = ref(false)

function show() {
  active.value = true
}

function hide() {
  active.value = false
}

defineExpose({ show, hide, active })
</script>

<style scoped>
.loading-bar-container {
  position: relative;
}

/* ── 顶部加载进度条 ── */
.loading-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: var(--z-max);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--duration-fast) var(--ease-smooth);
}

.loading-bar-container.active .loading-bar {
  opacity: 1;
}

/* ── 进度条主体：渐变 + 主色光晕 ── */
.loading-bar-progress {
  height: 100%;
  background: var(--grad-primary);
  transition: width var(--duration-base) var(--ease-smooth);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  box-shadow: 0 0 8px var(--color-primary-alpha-30);
}

/* ── 错误状态：使用危险色 ── */
.loading-bar.error .loading-bar-progress {
  background: var(--error);
  box-shadow: 0 0 8px var(--color-error-alpha-12);
}

/* ── 暗色模式：增强光晕可见度 ── */
html.dark .loading-bar-progress {
  box-shadow: 0 0 12px var(--color-primary-alpha-45);
}
html.dark .loading-bar.error .loading-bar-progress {
  box-shadow: 0 0 12px var(--color-error-alpha-20);
}

/* ── 旋转加载指示器 ── */
.loading-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: var(--z-max);
  opacity: 0;
  transition: opacity var(--duration-base) var(--ease-smooth);
  pointer-events: none;
}

.loading-bar-container.active .loading-spinner {
  opacity: 1;
}

.spinner-icon {
  width: 48px;
  height: 48px;
  color: var(--primary-500);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── 降级：减少动画偏好 ── */
@media (prefers-reduced-motion: reduce) {
  .spinner-icon {
    animation: none;
  }
}
</style>
