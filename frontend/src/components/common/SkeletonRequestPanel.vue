<template>
  <div class="skeleton-panel-root">
    <div class="skeleton-request-line">
      <div class="skeleton-block skeleton-method" />
      <div class="skeleton-block skeleton-path" />
      <div class="skeleton-block skeleton-send" />
    </div>
    <div class="skeleton-toolbar">
      <div class="skeleton-block skeleton-env" />
    </div>
    <div class="skeleton-tabs">
      <div v-for="i in 6" :key="i" class="skeleton-block skeleton-tab" />
    </div>
    <div class="skeleton-body">
      <div class="skeleton-panel">
        <div v-for="i in 4" :key="i" class="skeleton-block skeleton-param-row" />
      </div>
      <div class="skeleton-divider" />
      <div class="skeleton-panel">
        <div class="skeleton-block skeleton-response-header" />
        <div class="skeleton-block skeleton-response-body" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-panel-root {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--space-4);
  gap: var(--space-3);
  animation: skeletonFadeIn 0.3s ease;
}
@keyframes skeletonFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.skeleton-block {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-08) 50%,
    var(--surface-hover) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.4s ease-in-out infinite;
  border-radius: var(--radius-sm);
  height: 20px;
}
@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.skeleton-request-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
}
.skeleton-method {
  width: var(--width-sidebar-collapsed);
  height: 32px;
  border-radius: var(--radius-xs);
}
.skeleton-path {
  flex: 1;
  height: 32px;
}
.skeleton-send {
  width: 80px;
  height: 32px;
  border-radius: var(--radius-xs);
}
.skeleton-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-1) 0;
}
.skeleton-env {
  width: 120px;
  height: 32px;
}
.skeleton-tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) 0;
}
.skeleton-tab {
  width: 60px;
  height: 32px;
}
.skeleton-body {
  flex: 1;
  display: flex;
  gap: var(--space-3);
  min-height: 300px;
}
.skeleton-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--surface-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}
.skeleton-divider {
  width: var(--space-1);
  background: var(--border-subtle);
  border-radius: var(--radius-2xs);
}
.skeleton-param-row {
  height: var(--height-row-compact);
}
.skeleton-response-header {
  width: 60%;
  height: 32px;
  margin-bottom: var(--space-2);
}
.skeleton-response-body {
  flex: 1;
  height: 200px;
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-panel-root {
    animation: none;
  }
  .skeleton-block {
    animation: none;
    opacity: 0.7;
  }
}

html.dark .skeleton-block {
  background: linear-gradient(
    90deg,
    var(--surface-hover) 25%,
    var(--color-primary-alpha-12) 50%,
    var(--surface-hover) 75%
  );
}

html.dark .skeleton-panel {
  background: var(--surface-card);
  border-color: var(--border-subtle);
}
</style>
