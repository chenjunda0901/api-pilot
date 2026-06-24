<template>
  <div class="skeleton-card" :class="[`skeleton-${type}`]">
    <template v-if="type === 'env'">
      <div class="sk-header">
        <div class="sk-line sk-w-120" />
        <div class="sk-actions">
          <div class="sk-btn" />
          <div class="sk-btn" />
        </div>
      </div>
      <div class="sk-body">
        <div class="sk-section">
          <div class="sk-label" />
          <div class="sk-line sk-w-full" />
          <div class="sk-line sk-w-80" />
        </div>
        <div class="sk-section">
          <div class="sk-label" />
          <div class="sk-line sk-w-full" />
          <div class="sk-line sk-w-60" />
        </div>
      </div>
    </template>

    <template v-else-if="type === 'report'">
      <div class="sk-report" v-for="i in count" :key="i">
        <div class="sk-report-left">
          <div class="sk-circle" />
          <div class="sk-report-info">
            <div class="sk-line sk-w-140" />
            <div class="sk-line sk-w-80 sk-sm" />
          </div>
        </div>
        <div class="sk-report-right">
          <div class="sk-line sk-w-60" />
          <div class="sk-line sk-w-40 sk-sm" />
        </div>
      </div>
    </template>

    <template v-else-if="type === 'mock'">
      <div class="sk-mock" v-for="i in count" :key="i">
        <div class="sk-mock-left">
          <div class="sk-badge" />
          <div class="sk-line sk-w-100" />
          <div class="sk-line sk-w-200 sk-sm" />
        </div>
        <div class="sk-mock-actions">
          <div class="sk-btn-sm" />
          <div class="sk-btn-sm" />
          <div class="sk-btn-sm" />
        </div>
      </div>
    </template>

    <template v-else-if="type === 'recycle'">
      <div class="sk-recycle" v-for="i in count" :key="i">
        <div class="sk-recycle-icon" />
        <div class="sk-recycle-info">
          <div class="sk-line sk-w-160" />
          <div class="sk-line sk-w-80 sk-sm" />
        </div>
        <div class="sk-recycle-meta">
          <div class="sk-line sk-w-60 sk-sm" />
        </div>
        <div class="sk-mock-actions">
          <div class="sk-btn-sm" />
          <div class="sk-btn-sm" />
        </div>
      </div>
    </template>

    <template v-else>
      <div class="sk-default" v-for="i in count" :key="i">
        <div class="sk-line sk-w-full" />
        <div class="sk-line sk-w-60 sk-sm" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'env' | 'report' | 'mock' | 'recycle' | 'default'
  count?: number
}>(), {
  type: 'default',
  count: 4,
})
</script>

<style scoped>
/* ── SkeletonCard v2：卡片骨架屏
   设计要点：
   - 支持多种场景：env、report、mock、recycle、default
   - 使用 shimmer 动画效果（替代 pulse）
   - 统一使用 design tokens
   - 暗色模式自动适配
   ─────────────────────────────── */

/* 容器淡入动画 */
.skeleton-card {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ── 基础骨架块：shimmer 微光效果 (与 Element Plus 风格统一) ── */
.sk-line,
.sk-label,
.sk-circle,
.sk-badge,
.sk-btn,
.sk-btn-sm,
.sk-recycle-icon {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-08) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

/* 文字行 */
.sk-line {
  height: 16px;
}

.sk-line.sk-sm {
  height: 12px;
  margin-top: var(--spacing-sm);
}

.sk-line.sk-w-40 { width: 40%; }
.sk-line.sk-w-60 { width: 60%; }
.sk-line.sk-w-80 { width: 80%; }
.sk-line.sk-w-100 { width: 100px; }
.sk-line.sk-w-120 { width: 120px; }
.sk-line.sk-w-140 { width: 140px; }
.sk-line.sk-w-160 { width: 160px; }
.sk-line.sk-w-200 { width: 200px; }
.sk-line.sk-w-full { width: 100%; }

/* 标签 */
.sk-label {
  width: 60px;
  height: 12px;
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;
}

/* 圆形 */
.sk-circle {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

/* 徽章 */
.sk-badge {
  width: 48px;
  height: 20px;
  flex-shrink: 0;
}

/* 按钮 */
.sk-btn,
.sk-btn-sm {
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.sk-btn {
  width: 32px;
  height: 32px;
}

.sk-btn-sm {
  width: 28px;
  height: 28px;
}

.sk-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* ── Shimmer 动画 ── */
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ── 场景：env ── */
.skeleton-env {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  padding: var(--spacing-xl);
}

.skeleton-env .sk-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.skeleton-env .sk-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.skeleton-env .sk-section {
  display: flex;
  flex-direction: column;
}

/* ── 场景：report ── */
.skeleton-report {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sk-report {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
}

.sk-report-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.sk-report-info {
  display: flex;
  flex-direction: column;
}

.sk-report-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* ── 场景：mock ── */
.skeleton-mock {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sk-mock {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
}

.sk-mock-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.sk-mock-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* ── 场景：recycle ── */
.skeleton-recycle {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sk-recycle {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
}

.sk-recycle-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.sk-recycle-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.sk-recycle-meta {
  display: flex;
  flex-direction: column;
  margin-right: var(--spacing-sm);
}

/* ── 场景：default ── */
.skeleton-default {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  padding: var(--spacing-xl);
}

.sk-default > div {
  padding: var(--spacing-lg);
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
}

/* ── 降级：减少动画偏好 ── */
@media (prefers-reduced-motion: reduce) {
  .sk-line,
  .sk-label,
  .sk-circle,
  .sk-badge,
  .sk-btn,
  .sk-btn-sm,
  .sk-recycle-icon {
    animation: none;
    opacity: 0.7;
  }
}

/* ── 暗色模式 ── */
html.dark .sk-line,
html.dark .sk-label,
html.dark .sk-circle,
html.dark .sk-badge,
html.dark .sk-btn,
html.dark .sk-btn-sm,
html.dark .sk-recycle-icon {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-12) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
}
html.dark .skeleton-env,
html.dark .sk-report,
html.dark .sk-mock,
html.dark .sk-recycle,
html.dark .sk-default > div {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
</style>
