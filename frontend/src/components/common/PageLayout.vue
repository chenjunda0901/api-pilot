<template>
  <div class="page-layout" :class="{ 'page-layout--compact': compact }">
    <!-- 紧凑模式：标题 + 筛选 + 操作合并为一行 -->
    <div v-if="compact && (title || kicker || $slots['hero-extra'] || $slots.filter)" class="page-compact-bar">
      <div v-if="title || kicker" class="page-compact-title">
        <span v-if="kicker" class="page-kicker">{{ kicker }}</span>
        <h1 v-if="title" class="page-title">{{ title }}</h1>
        <slot name="hero-meta" />
      </div>
      <div v-if="$slots.filter" class="page-compact-filter">
        <slot name="filter" />
      </div>
      <div v-if="$slots['hero-extra']" class="page-compact-extra">
        <slot name="hero-extra" />
      </div>
    </div>

    <!-- 标准模式 Hero 区域 -->
    <div v-if="!compact && (title || kicker || $slots['hero-extra'])" class="page-hero">
      <div class="page-hero-text">
        <span v-if="kicker" class="page-kicker">{{ kicker }}</span>
        <h1 v-if="title" class="page-title">{{ title }}</h1>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
        <slot name="hero-meta" />
      </div>
      <div class="page-hero-extra">
        <slot name="hero-extra" />
      </div>
    </div>

    <!-- 标准模式筛选栏 -->
    <div v-if="!compact && $slots.filter" class="page-filter">
      <slot name="filter" />
    </div>

    <!-- 内容区 -->
    <div class="page-content">
      <!-- 加载态 -->
      <slot v-if="loading" name="loading">
        <SkeletonLoader type="table" :rows="4" />
      </slot>

      <!-- 错误态 -->
      <EmptyState
        v-else-if="error"
        illustration="default"
        title="加载失败"
        :description="error"
      >
        <template #action>
          <el-button type="primary" size="small" @click="$emit('retry')">重试</el-button>
        </template>
      </EmptyState>

      <!-- 空状态 -->
      <EmptyState
        v-else-if="empty"
        :icon="emptyIcon"
        :illustration="emptyIllustration"
        :title="emptyTitle || '暂无数据'"
        :description="emptyDescription"
      >
        <template #action>
          <slot name="empty-action" />
        </template>
      </EmptyState>

      <!-- 正常内容 -->
      <slot v-else />

      <!-- 底部 -->
      <div v-if="$slots.footer" class="page-footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type Component } from 'vue'
import EmptyState from '../EmptyState.vue'
import SkeletonLoader from './SkeletonLoader.vue'

interface Props {
  title?: string
  subtitle?: string
  kicker?: string
  compact?: boolean
  loading?: boolean
  empty?: boolean
  emptyTitle?: string
  emptyDescription?: string
  emptyIcon?: Component
  emptyIllustration?: 'report' | 'scene' | 'api' | 'recycle' | 'environment' | 'data' | 'project' | 'search' | 'empty' | 'folder' | 'default'
  error?: string | null
}

defineProps<Props>()

defineEmits<{
  retry: []
}>()
</script>

<style scoped>
.page-layout {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--space-4) var(--space-5);
  gap: var(--space-3);
  min-height: 0;
  overflow: visible;
  transition: padding var(--duration-base) var(--ease-smooth);
}

/* ---- 紧凑模式：消除多余 padding/gap，标题+筛选+操作合并一行 ---- */
.page-layout--compact {
  padding: 0;
  gap: 0;
}

.page-compact-bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  transition: border-color var(--duration-base) var(--ease-smooth);
}

.page-compact-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.page-compact-title .page-title {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin: 0;
  white-space: nowrap;
  transition: color var(--duration-base) var(--ease-smooth);
}

.page-compact-filter {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
}

.page-compact-extra {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* 紧凑模式下 page-content 消除额外 padding 和 max-width */
.page-layout--compact .page-content {
  padding: 0;
  max-width: none;
  gap: var(--space-2);
}

/* ---- Hero 区域：简洁风格，和紧凑模式保持视觉一致 ---- */
.page-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: none;
  border-radius: 0;
  overflow: hidden;
  transition:
    background-color var(--duration-base) var(--ease-smooth),
    border-color var(--duration-base) var(--ease-smooth),
    box-shadow var(--duration-base) var(--ease-smooth),
    padding var(--duration-base) var(--ease-smooth);
}

.page-hero-text {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
  min-width: 0;
}

/* ---- Kicker：uppercase + 主色 ---- */
.page-kicker {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--primary-600);
  transition: color var(--duration-base) var(--ease-smooth);
}

.page-compact-title .page-kicker {
  margin-bottom: 0;
  font-size: var(--text-2xs);
  letter-spacing: 0.08em;
}

/* ---- 标题：xl + bold + tracking-tight + 主文字色 ---- */
.page-title {
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
  line-height: 1.3;
  color: var(--text-primary);
  margin: 0;
  transition:
    color var(--duration-base) var(--ease-smooth),
    font-size var(--duration-base) var(--ease-smooth);
}

/* ---- 副标题：sm + secondary + 1.5 line-height ---- */
.page-subtitle {
  font-size: var(--text-sm);
  line-height: 1.5;
  color: var(--text-secondary);
  margin: var(--space-05) 0 0 0;
  max-width: 640px;
  transition: color var(--duration-base) var(--ease-smooth);
}

/* ---- Hero-extra：flex + wrap ---- */
.page-hero-extra {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.page-filter {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.page-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-height: 0;
  overflow-y: auto;
}

.page-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
  transition: border-color var(--duration-base) var(--ease-smooth);
}

/* ---- 所有可交互子元素 focus-visible 统一支持 ---- */
.page-layout :deep(a:focus-visible),
.page-layout :deep(button:focus-visible),
.page-layout :deep([role="button"]:focus-visible),
.page-layout :deep([tabindex]:not([tabindex="-1"]):focus-visible),
.page-layout :deep(input:focus-visible),
.page-layout :deep(select:focus-visible),
.page-layout :deep(textarea:focus-visible) {
  outline: 2px solid var(--primary-500);
  outline-offset: 2px;
}

/* ================================================================
   暗色模式适配
   ================================================================ */
html.dark .page-kicker {
  color: var(--primary-400);
}

html.dark .page-layout :deep(a:focus-visible),
html.dark .page-layout :deep(button:focus-visible),
html.dark .page-layout :deep([role="button"]:focus-visible),
html.dark .page-layout :deep([tabindex]:not([tabindex="-1"]):focus-visible),
html.dark .page-layout :deep(input:focus-visible),
html.dark .page-layout :deep(select:focus-visible),
html.dark .page-layout :deep(textarea:focus-visible) {
  outline: 2px solid var(--primary-400);
  outline-offset: 2px;
}

/* ================================================================
   响应式：窄屏紧凑化
   ================================================================ */
@media (max-width: 768px) {
  .page-layout {
    padding: var(--space-4);
    gap: var(--space-3);
  }

  .page-hero {
    flex-direction: column;
    padding: var(--space-4);
    gap: var(--space-3);
  }

  .page-hero-text {
    width: 100%;
  }

  .page-title {
    font-size: var(--text-xl);
  }

  .page-subtitle {
    font-size: var(--text-sm);
  }

  .page-hero-extra {
    width: 100%;
    max-width: 100%;
    justify-content: flex-start;
  }

  .page-filter {
    gap: var(--space-2);
  }

  .page-compact-bar {
    flex-wrap: wrap;
    padding: var(--space-2) var(--space-3);
  }

  .page-content {
    gap: var(--space-3);
  }
}
</style>
