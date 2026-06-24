<template>
  <div class="skeleton-row">
    <div class="sk-block sk-block-1" />
    <div class="sk-block sk-block-2" />
    <div class="sk-block sk-block-3" />
  </div>
</template>

<style scoped>
.skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
}

.sk-block {
  height: 12px;
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-08) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

.sk-block-1 { width: 30%; }
.sk-block-2 { width: 50%; }
.sk-block-3 { width: 15%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .sk-block {
    animation: none;
    opacity: 0.7;
  }
}

/* 暗色模式 */
html.dark .sk-block {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-12) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
}
</style>
