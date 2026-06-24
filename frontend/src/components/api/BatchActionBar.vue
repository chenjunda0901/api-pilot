<template>
  <transition name="slide-up">
    <div v-if="selectedIds.length > 0" class="batch-action-bar">
      <span class="selected-count">已选择 {{ selectedIds.length }} 项</span>
      <div class="action-buttons">
        <el-button size="small" @click="$emit('move')">
          <el-icon><Rank /></el-icon> 移动
        </el-button>
        <el-button size="small" @click="$emit('copy')">
          <el-icon><CopyDocument /></el-icon> 复制
        </el-button>
        <el-button size="small" type="danger" @click="$emit('delete')">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
        <el-button size="small" @click="$emit('clear')">
          <el-icon><Close /></el-icon> 取消
        </el-button>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { Delete, Close, CopyDocument, Rank } from '@element-plus/icons-vue'

defineProps<{ selectedIds: number[] }>()
defineEmits<{ move: []; copy: []; delete: []; clear: [] }>()
</script>

<style scoped>
.batch-action-bar {
  position: fixed; bottom: var(--space-6); left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-2-5) var(--space-5); background: var(--surface-card); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl); box-shadow: var(--shadow-float); z-index: 100;
}
.selected-count { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--text-primary); }
.action-buttons { display: flex; gap: var(--space-2); }
.slide-up-enter-active, .slide-up-leave-active { transition: all var(--duration-slow) var(--ease-smooth); }
.slide-up-enter-from, .slide-up-leave-to { transform: translateX(-50%) translateY(100%); opacity: 0; }

/* Dark mode */
html.dark .batch-action-bar {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: 0 10px 25px var(--color-black-alpha-30);
}
html.dark .selected-count {
  color: var(--text-primary);
}
</style>
