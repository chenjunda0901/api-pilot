<template>
  <el-tooltip :content="isDark ? 'Switch to Light' : 'Switch to Dark'" placement="bottom">
    <el-button link class="theme-toggle" @click="toggleTheme" :aria-label="isDark ? 'Switch to Light' : 'Switch to Dark'">
      <el-icon :size="18" aria-hidden="true">
        <Moon v-if="!isDark" />
        <Sunny v-else />
      </el-icon>
    </el-button>
  </el-tooltip>
</template>

<script setup lang="ts">
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useTheme } from '@/composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>

<style scoped>
/* ── ThemeToggle v2：主题切换按钮
   设计要点：
   - 圆形按钮，hover 时显示背景色
   - 图标切换动画：旋转 + 缩放
   - 使用 design tokens 确保主题一致性
   - 暗色模式下自动适配
   ─────────────────────────────── */

/* 按钮容器 */
.theme-toggle {
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Hover 状态：显示背景色 */
.theme-toggle:hover {
  background: var(--surface-hover);
}

/* Active 状态：轻微缩放 */
.theme-toggle:active {
  transform: scale(var(--press-scale));
}

/* 图标动画：切换时旋转 + 缩放 */
.theme-toggle :deep(.el-icon) {
  transition: transform var(--duration-base) var(--ease-spring);
}

.theme-toggle:hover :deep(.el-icon) {
  transform: rotate(15deg) scale(1.1);
}
</style>
