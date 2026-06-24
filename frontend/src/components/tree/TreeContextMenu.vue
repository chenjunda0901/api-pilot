<template>
  <div>
    <Teleport to="body">
      <div
        v-if="visible"
        class="tree-context-menu"
        :style="{ left: x + 'px', top: y + 'px' }"
        @click.stop
      >
        <template v-for="(item, idx) in items" :key="idx">
          <div v-if="item.divider" class="context-divider" />
          <div
            v-else
            class="context-item"
            :class="{ 'context-item--danger': item.danger }"
            @click="handleItemClick(item)"
            tabindex="0"
            role="menuitem"
            @keydown.enter="handleItemClick(item)"
          >
            <component :is="item.icon" v-if="item.icon" :size="14" class="context-item-icon" />
            <span class="context-item-label">{{ item.label }}</span>
          </div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script lang="ts">
import type { Component } from "vue"

export interface ContextMenuItem {
  label?: string
  icon?: Component
  divider?: boolean
  danger?: boolean
  action?: () => void
}
</script>

<script setup lang="ts">
defineProps<{
  visible: boolean
  x: number
  y: number
  items: ContextMenuItem[]
}>()

const emit = defineEmits<{
  close: []
}>()

function handleItemClick(item: ContextMenuItem) {
  item.action?.()
  emit("close")
}
</script>

<style scoped>
/* ===== 右键菜单容器 - 全局定位 ===== */
:global(.tree-context-menu) {
  position: fixed;
  z-index: var(--z-max);
  min-width: 180px;
  max-width: 280px;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: var(--space-1-5);
  border: 1px solid var(--border-subtle);
  animation: contextMenuIn var(--duration-fast) var(--ease-out);
  overflow: hidden;
}

@keyframes contextMenuIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* ===== 菜单项 - 图标和文字对齐 ===== */
:global(.context-item) {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: var(--transition-fast);
  user-select: none;
  outline: none;
  min-height: var(--height-row-compact);
}

:global(.context-item:hover),
:global(.context-item:focus-visible) {
  background: var(--surface-hover);
  color: var(--primary-600);
  transform: translateX(2px);
}

:global(.context-item:active) {
  background: var(--color-primary-alpha-12);
  transform: translateX(0);
}

/* ===== 危险操作项 ===== */
:global(.context-item--danger) {
  color: var(--error-text);
}

:global(.context-item--danger:hover),
:global(.context-item--danger:focus-visible) {
  background: var(--color-error-alpha-08);
  color: var(--error-dark);
}

:global(.context-item--danger:active) {
  background: var(--color-error-alpha-12);
}

/* ===== 菜单图标 - 大小和对齐 ===== */
:global(.context-item-icon) {
  flex-shrink: 0;
  width: var(--size-icon-sm);
  height: var(--size-icon-sm);
  opacity: 0.75;
  transition: var(--transition-fast);
}

:global(.context-item:hover .context-item-icon),
:global(.context-item:focus-visible .context-item-icon) {
  opacity: 1;
  transform: scale(1.05);
}

:global(.context-item--danger:hover .context-item-icon) {
  color: var(--error-dark);
}

/* ===== 菜单标签文字 ===== */
:global(.context-item-label) {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--weight-medium);
}

/* ===== 分隔线 ===== */
:global(.context-divider) {
  height: 1px;
  background: var(--border-subtle);
  margin: var(--space-1) var(--space-2);
}

/* ===== 暗色模式适配 ===== */
html.dark :global(.tree-context-menu) {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-lg);
}

html.dark :global(.context-item) {
  color: var(--text-primary);
}

html.dark :global(.context-item:hover),
html.dark :global(.context-item:focus-visible) {
  background: var(--surface-hover);
  color: var(--primary-400);
}

html.dark :global(.context-item--danger) {
  color: var(--error-text);
}

html.dark :global(.context-item--danger:hover) {
  background: var(--color-error-alpha-10);
  color: var(--error-dark);
}
</style>
