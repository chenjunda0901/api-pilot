<template>
  <div class="status-bar">
    <div class="status-bar-left">
      <span class="status-divider"></span>
      <span class="status-item status-env" v-if="currentEnv">
        <span class="status-dot online"></span>
        {{ currentEnv }}
      </span>
    </div>
    <div class="status-bar-right">
      <span v-if="runningInfo" class="status-item status-running">
        <span class="status-dot running"></span>
        <span class="status-running-label">运行中</span>
        {{ runningInfo }}
      </span>
      <span class="status-divider" v-if="runningInfo"></span>
      <button class="status-btn" @click="$emit('openRecycle')" title="回收站">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        <span>回收站</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  runningInfo?: string
  currentEnv?: string
}>()

defineEmits<{
  openRecycle: []
}>()
</script>

<style scoped>
/* ── 状态栏容器 — 统一高度与间距 ── */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  height: var(--height-statusbar);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  border-top: 1px solid var(--border-subtle);
  background: var(--surface-card);
  flex-shrink: 0;
  user-select: none;
}

.status-bar-left,
.status-bar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* ── 状态项 ── */
.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  font-weight: var(--weight-medium);
}

/* ── 按钮 ── */
.status-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 6px;
  height: 20px;
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: background-color 160ms var(--ease-smooth),
    color 160ms var(--ease-smooth),
    box-shadow 160ms var(--ease-smooth),
    transform 160ms var(--ease-smooth),
    border-color 160ms var(--ease-smooth);
  font-family: inherit;
}
.status-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

/* ── 状态点 — 精致微光 ── */
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
}
.status-dot.online {
  background: var(--success);
  box-shadow: 0 0 0 3px var(--color-success-alpha-10);
  animation: dotOnlinePulse 3s ease-in-out infinite;
}
.status-dot.running {
  background: var(--warning);
  box-shadow: 0 0 0 3px var(--color-warning-alpha-12);
  animation: statusPulse 1.5s ease-in-out infinite;
}
@keyframes dotOnlinePulse {
  0%, 100% { box-shadow: 0 0 0 2px var(--color-success-alpha-08), 0 0 0 0 var(--color-success-alpha-20); }
  50% { box-shadow: 0 0 0 2px var(--color-success-alpha-12), 0 0 0 4px var(--color-success-alpha-04); }
}
.status-running-label {
  font-weight: var(--weight-semibold);
  color: var(--warning);
}
.status-running {
  color: var(--text-secondary);
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.85); }
}

/* ── 分隔线 ── */
.status-divider {
  width: 1px;
  height: 12px;
  background: var(--border-subtle);
  margin: 0 var(--space-0-5);
}

/* ── 环境 ── */
.status-env {
  color: var(--primary-600);
  font-weight: var(--weight-semibold);
}

/* ── Dark Mode — 使用 tokens 变量 ── */
html.dark .status-bar {
  background: var(--surface-card);
  border-top-color: var(--border-subtle);
}
html.dark .status-item { color: var(--text-secondary); }
html.dark .status-btn { color: var(--text-muted); }
html.dark .status-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}
html.dark .status-env { color: var(--primary-400); }
html.dark .status-running-label { color: var(--warning); }
html.dark .status-divider { background: var(--border-subtle); }
</style>