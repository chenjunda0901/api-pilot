<template>
  <div class="skeleton-table">
    <div class="sk-header">
      <div v-for="(col, i) in columns" :key="i" class="sk-th" :style="{ width: col.width }">
        <div class="sk-block" style="width: 60%; height: 10px" />
      </div>
    </div>
    <div v-for="r in rows" :key="r" class="sk-row">
      <div v-for="(col, ci) in columns" :key="ci" class="sk-cell" :style="{ width: col.width }">
        <div
          class="sk-block"
          :style="{ width: cellWidths[ci % cellWidths.length], height: '12px' }"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Column {
  width: string
}

interface Props {
  rows?: number
  columns?: Column[]
}

const cellWidths = ["80%", "95%", "70%", "90%", "85%"]

withDefaults(defineProps<Props>(), {
  rows: 5,
  columns: () => [{ width: "25%" }, { width: "30%" }, { width: "15%" }, { width: "15%" }],
})
</script>

<style scoped>
/* ── SkeletonTable v2：表格骨架屏
   设计要点：
   - 模拟表格结构：表头 + 多行数据
   - 表头与内容有视觉区分（背景色 + 边框）
   - 使用 shimmer 动画效果
   - 统一使用 design tokens
   - 暗色模式自动适配
   ─────────────────────────────── */

/* 表格容器 */
.skeleton-table {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-card);
}

/* 表头 */
.sk-header {
  display: flex;
  padding: var(--spacing-md) var(--spacing-md);
  background: var(--surface-muted);
  border-bottom: 1px solid var(--border-subtle);
  gap: var(--spacing-md);
}

.sk-th {
  display: flex;
}

/* 表格行 */
.sk-row {
  display: flex;
  padding: var(--spacing-md) var(--spacing-md);
  gap: var(--spacing-md);
  border-bottom: 1px solid var(--border-subtle);
}

.sk-row:last-child {
  border-bottom: none;
}

.sk-cell {
  display: flex;
}

/* 骨架块：shimmer 动画 (与 Element Plus 风格统一) */
.sk-block {
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

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ── 降级：减少动画偏好 ── */
@media (prefers-reduced-motion: reduce) {
  .sk-block {
    animation: none;
    opacity: 0.7;
  }
}

/* ── 暗色模式 ── */
html.dark .sk-block {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-12) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
}
html.dark .skeleton-table {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
html.dark .sk-header {
  background: var(--surface-nested);
  border-bottom-color: var(--border-subtle);
}
html.dark .sk-row {
  border-bottom-color: var(--border-subtle);
}
</style>
