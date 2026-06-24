<template>
  <el-dropdown trigger="click" @command="handleCommand">
    <!-- 环境切换触发按钮 -->
    <el-button size="small" class="env-switcher-btn">
      <span class="env-switcher-label">{{ currentName }}</span>
      <el-icon class="env-switcher-arrow"><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu class="env-switcher-menu">
        <el-dropdown-item
          v-for="env in environments"
          :key="env.id"
          :command="env.id"
          :class="{ 'is-active': env.id === activeEnvId }"
        >
          <span class="env-color-dot" :style="{ background: env.color || 'var(--primary-500)' }"></span>
          {{ env.name }}
          <span v-if="env.id === activeEnvId" class="env-check-mark">✓</span>
        </el-dropdown-item>
        <el-dropdown-item divided command="manage">
          <el-icon class="env-manage-icon"><Setting /></el-icon> 管理环境
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowDown, Setting } from '@element-plus/icons-vue'
import type { Environment } from '../../types'

const props = defineProps<{
  environments: Environment[]
  activeEnvId?: number
}>()

const emit = defineEmits<{ select: [id: number]; manage: [] }>()

const currentName = computed(() => {
  const env = props.environments.find(e => e.id === props.activeEnvId)
  return env?.name || '选择环境'
})

function handleCommand(cmd: string | number) {
  if (cmd === 'manage') {
    emit('manage')
  } else {
    emit('select', cmd as number)
  }
}
</script>

<style scoped>
/* ===== 环境切换器按钮 ===== */
.env-switcher-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs); /* 4px */
  padding: var(--spacing-xs) var(--spacing-sm); /* 4px 8px */
  font-size: var(--font-size-sm); /* 14px */
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md); /* 8px */
  box-shadow: var(--shadow-xs);
  cursor: pointer;
  transition: var(--transition-fast);
}

/* 按钮悬停状态 */
.env-switcher-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

/* 按钮激活状态 */
.env-switcher-btn:active {
  transform: translateY(0) scale(0.98);
  box-shadow: var(--shadow-xs);
  transition-duration: var(--duration-fast);
}

/* 按钮焦点状态 */
.env-switcher-btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
  box-shadow: var(--shadow-focus);
}

/* 按钮禁用状态 */
.env-switcher-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: var(--shadow-xs);
}

/* 环境名称标签 */
.env-switcher-label {
  color: var(--text-primary);
  white-space: nowrap;
}

/* 下拉箭头图标 */
.env-switcher-arrow {
  margin-left: var(--spacing-xs); /* 4px */
  color: var(--text-secondary);
  transition: transform var(--duration-fast) var(--ease-smooth);
}

/* 下拉菜单悬停时箭头旋转 */
.env-switcher-btn:hover .env-switcher-arrow {
  transform: rotate(180deg);
}

/* 下拉菜单样式 */
.env-switcher-menu {
  background: var(--surface-overlay);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); /* 8px */
  box-shadow: var(--shadow-pop);
  padding: var(--spacing-xs) 0;
}

/* 菜单项样式 */
.env-switcher-menu :deep(.el-dropdown-menu__item) {
  padding: var(--spacing-sm) var(--spacing-md); /* 8px 12px */
  font-size: var(--font-size-sm); /* 14px */
  color: var(--text-primary);
  transition: var(--transition-fast);
}

/* 菜单项悬停状态 */
.env-switcher-menu :deep(.el-dropdown-menu__item:hover) {
  background: var(--surface-hover);
  color: var(--primary-600);
}

/* 菜单项激活状态 */
.env-switcher-menu :deep(.el-dropdown-menu__item.is-active) {
  background: var(--color-primary-alpha-08);
  color: var(--primary-600);
  font-weight: var(--weight-medium);
}

/* 环境颜色圆点 */
.env-color-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
  flex-shrink: 0;
}

/* 选中项勾选标记 */
.env-check-mark {
  margin-left: auto;
  padding-left: var(--spacing-sm);
  color: var(--primary-600);
  font-weight: var(--weight-bold);
  font-size: var(--font-size-sm);
}

/* 管理环境选项（分割线上方） */
.env-manage-icon {
  margin-right: var(--spacing-xs); /* 4px */
  color: var(--text-secondary);
}

/* ===== 暗色模式适配 ===== */
html.dark .env-switcher-btn {
  background: var(--surface-card);
  border-color: var(--border-default);
  color: var(--text-primary);
  box-shadow: var(--shadow-xs);
}

html.dark .env-switcher-btn:hover {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

html.dark .env-switcher-menu {
  background: var(--surface-overlay);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-pop);
}

html.dark .env-switcher-menu :deep(.el-dropdown-menu__item) {
  color: var(--text-primary);
}

html.dark .env-switcher-menu :deep(.el-dropdown-menu__item:hover) {
  background: var(--surface-hover);
  color: var(--primary-400);
}

html.dark .env-switcher-menu :deep(.el-dropdown-menu__item.is-active) {
  background: var(--color-primary-alpha-12);
  color: var(--primary-400);
}
</style>
