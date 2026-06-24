<template>
  <Transition name="save-indicator">
    <div v-if="status !== 'idle'" class="auto-save-indicator" :class="`save-${status}`">
      <span class="save-dot" />
      <span class="save-text">{{ text }}</span>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

const props = defineProps<{ status: SaveStatus }>()

const textMap: Record<SaveStatus, string> = {
  idle: '',
  saving: '保存中...',
  saved: '已保存',
  error: '保存失败',
}

const text = computed(() => textMap[props.status])
</script>

<style scoped>
/* ── 自动保存指示器：胶囊状标签 ── */
.auto-save-indicator {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-1) var(--space-2-5);
  border-radius: var(--radius-full);
  background: var(--color-neutral-alpha-06);
  transition: all var(--duration-fast) var(--ease-smooth);
}

/* ── 状态指示点 ── */
.save-dot {
  width: var(--space-1-5);
  height: var(--space-1-5);
  border-radius: var(--radius-full);
  background: var(--text-disabled);
  transition: background var(--duration-fast) var(--ease-smooth);
}

/* ── 保存中：主色脉冲动画 ── */
.save-saving .save-dot {
  background: var(--primary-500);
  animation: pulse-dot 1s var(--ease-smooth) infinite;
}

/* ── 已保存：成功色 ── */
.save-saved .save-dot {
  background: var(--success);
}

/* ── 保存失败：危险色 ── */
.save-error .save-dot {
  background: var(--error);
}

.save-error {
  color: var(--error);
  background: var(--color-error-alpha-06);
}

/* ── 暗色模式适配 ── */
html.dark .auto-save-indicator {
  background: var(--color-white-alpha-06);
  color: var(--text-secondary);
}
html.dark .save-error {
  background: var(--color-error-alpha-08);
}

/* ── 脉冲动画 ── */
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

/* ── 过渡动画 ── */
.save-indicator-enter-active {
  transition: all var(--duration-fast) var(--ease-out);
}
.save-indicator-leave-active {
  transition: all var(--duration-fast) var(--ease-in);
}
.save-indicator-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.save-indicator-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
