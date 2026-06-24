<template>
  <div class="skeleton-loader">
    <!-- 表格骨架屏 -->
    <template v-if="type === 'table'">
      <div class="skeleton-row header">
        <div
          v-for="i in columns"
          :key="i"
          class="skeleton-cell skeleton-pulse"
          :style="{ width: getColumnWidth(i) }"
        />
      </div>
      <div v-for="i in rows" :key="i" class="skeleton-row">
        <div
          v-for="j in columns"
          :key="j"
          class="skeleton-cell skeleton-pulse"
          :style="{ width: getColumnWidth(j) }"
        />
      </div>
    </template>

    <!-- 卡片骨架屏 -->
    <template v-else-if="type === 'card'">
      <div class="skeleton-card" v-for="i in rows" :key="i">
        <div class="skeleton-card-header skeleton-pulse" />
        <div class="skeleton-card-body">
          <div class="skeleton-text skeleton-pulse long" />
          <div class="skeleton-text skeleton-pulse medium" />
          <div class="skeleton-text skeleton-pulse short" />
        </div>
      </div>
    </template>

    <!-- 列表骨架屏 -->
    <template v-else-if="type === 'list'">
      <div v-for="i in rows" :key="i" class="skeleton-list-item">
        <div class="skeleton-avatar skeleton-pulse skeleton-circle" />
        <div class="skeleton-list-content">
          <div class="skeleton-text skeleton-pulse medium" />
          <div class="skeleton-text skeleton-pulse short" />
        </div>
      </div>
    </template>

    <!-- 表单骨架屏 -->
    <template v-else-if="type === 'form'">
      <div v-for="i in rows" :key="i" class="skeleton-form-item">
        <div
          class="skeleton-label skeleton-pulse"
          style="width: 80px; height: 14px; margin-bottom: 8px"
        />
        <div
          class="skeleton-input skeleton-pulse"
          style="width: 100%; height: 32px; border-radius: var(--radius-sm)"
        />
      </div>
    </template>

    <!-- 自定义骨架屏 -->
    <template v-else>
      <slot>
        <div class="skeleton-text skeleton-pulse long" />
        <div class="skeleton-text skeleton-pulse medium" />
        <div class="skeleton-text skeleton-pulse short" />
      </slot>
    </template>
  </div>
</template>

<script setup lang="ts">
interface Props {
  type?: "table" | "card" | "list" | "form" | "custom"
  rows?: number
  columns?: number
}

withDefaults(defineProps<Props>(), {
  type: "custom",
  rows: 5,
  columns: 4,
})

const getColumnWidth = (index: number) => {
  const widths = ["30%", "25%", "25%", "20%"]
  return widths[(index - 1) % widths.length]
}
</script>

<style scoped>
.skeleton-loader {
  width: 100%;
  animation: skeletonFadeIn 0.3s ease;
}

@keyframes skeletonFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.skeleton-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.skeleton-row.header {
  background: var(--surface-muted);
  margin: 0 calc(-1 * var(--space-4));
  padding: var(--space-3) var(--space-4);
}

.skeleton-cell {
  height: 20px;
  border-radius: var(--radius-sm);
}

.skeleton-card {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-4);
  background: var(--surface-card);
}

.skeleton-card-header {
  height: 120px;
}

.skeleton-card-body {
  padding: var(--space-4);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.skeleton-avatar {
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
}

.skeleton-form-item {
  margin-bottom: var(--space-4);
}

.skeleton-input {
  height: var(--height-input);
}

/* ── 骨架屏动画 — shimmer 微光效果（与 Element Plus 风格统一） ── */
.skeleton-cell,
.skeleton-card-header,
.skeleton-avatar,
.skeleton-input,
.skeleton-label {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-08) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
}

.skeleton-text {
  height: 14px;
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-08) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
}
.skeleton-text.long { width: 80%; }
.skeleton-text.medium { width: 60%; }
.skeleton-text.short { width: 35%; }

.skeleton-circle { border-radius: var(--radius-full); }

@keyframes skeleton-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 降级：reduced-motion 下使用静态 */
@media (prefers-reduced-motion: reduce) {
  .skeleton-loader {
    animation: none;
  }
  .skeleton-cell,
  .skeleton-card-header,
  .skeleton-avatar,
  .skeleton-text,
  .skeleton-input,
  .skeleton-label {
    animation: none;
    opacity: 0.7;
  }
}

/* 暗色模式 — 使用更亮的 shimmer 高光 */
html.dark .skeleton-cell,
html.dark .skeleton-card-header,
html.dark .skeleton-avatar,
html.dark .skeleton-text,
html.dark .skeleton-input,
html.dark .skeleton-label {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-16) 50%,
    var(--surface-hover) 75%
  );
}

html.dark .skeleton-card {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
</style>
