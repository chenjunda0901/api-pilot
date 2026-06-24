<template>
  <div class="empty-state" role="status" aria-live="polite">
    <div class="empty-icon-wrapper">
      <slot name="icon">
        <!-- 报告/文档空状态 -->
        <svg v-if="illustration === 'report'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="8" y="12" width="48" height="40" rx="6" stroke="var(--primary-200)" stroke-width="2.5"/>
          <rect x="8" y="12" width="48" height="10" rx="6" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2.5"/>
          <rect x="14" y="28" width="24" height="6" rx="3" fill="var(--primary-100)"/>
          <rect x="14" y="38" width="16" height="6" rx="3" fill="var(--primary-50)"/>
          <rect x="14" y="48" width="20" height="3" rx="1.5" fill="var(--primary-50)"/>
          <circle cx="48" cy="28" r="8" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2"/>
          <path d="M45 28l2 2 4-4" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        
        <!-- 场景测试空状态 -->
        <svg v-else-if="illustration === 'scene'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M20 16c0-3.3 2.7-6 6-6h12c3.3 0 6 2.7 6 6v24c0 3.3-2.7 6-6 6H26c-3.3 0-6-2.7-6-6V16z" stroke="var(--primary-200)" stroke-width="2.5" rx="6"/>
          <path d="M32 24v16M24 32h16" stroke="var(--primary-300)" stroke-width="2.5" stroke-linecap="round"/>
          <circle cx="44" cy="18" r="8" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2"/>
          <path d="M41 18h6M44 15v6" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round"/>
        </svg>
        
        <!-- API接口空状态 -->
        <svg v-else-if="illustration === 'api'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M32 8l24 12v24L32 56 8 44V20L32 8z" stroke="var(--primary-200)" stroke-width="2.5" stroke-linejoin="round"/>
          <circle cx="32" cy="32" r="10" stroke="var(--primary-300)" stroke-width="2.5"/>
          <path d="M26 28l12 8M38 28l-12 8" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round"/>
        </svg>
        
        <!-- 回收站空状态 -->
        <svg v-else-if="illustration === 'recycle'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M32 12c-5 0-9 4-9 9v4H12c-2 0-4 2-4 4s2 4 4 4h4l2 16c0 4 4 8 8 8h12c4 0 8-4 8-8l2-16h4c2 0 4-2 4-4s-2-4-4-4h-11v-4c0-5-4-9-9-9z" stroke="var(--primary-200)" stroke-width="2.5" stroke-linejoin="round"/>
          <path d="M22 18h20M24 28v16M32 28v12" stroke="var(--primary-300)" stroke-width="2" stroke-linecap="round"/>
        </svg>
        
        <!-- 环境配置空状态 -->
        <svg v-else-if="illustration === 'environment'" viewBox="0 0 64 64" width="64" height="64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="8" y="20" width="48" height="32" rx="6" stroke="var(--primary-200)" stroke-width="2.5"/>
          <circle cx="20" cy="36" r="4" fill="var(--primary-300)"/>
          <circle cx="32" cy="36" r="4" fill="var(--primary-200)"/>
          <circle cx="44" cy="36" r="4" fill="var(--primary-100)"/>
          <path d="M14 28h36" stroke="var(--primary-100)" stroke-width="2"/>
          <circle cx="54" cy="14" r="10" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2"/>
          <path d="M50 14h8M54 10v8" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round"/>
        </svg>
        
        <!-- 数据/统计空状态 -->
        <svg v-else-if="illustration === 'data'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="12" y="32" width="8" height="20" rx="2" fill="var(--primary-100)"/>
          <rect x="24" y="24" width="8" height="28" rx="2" fill="var(--primary-200)"/>
          <rect x="36" y="16" width="8" height="36" rx="2" fill="var(--primary-300)"/>
          <rect x="48" y="20" width="4" height="32" rx="2" fill="var(--primary-200)"/>
          <path d="M8 16l8 4-8 4" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        
        <!-- 项目空状态 -->
        <svg v-if="illustration === 'project'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="10" y="14" width="44" height="36" rx="6" stroke="var(--primary-200)" stroke-width="2.5"/>
          <path d="M10 28h44" stroke="var(--primary-100)" stroke-width="2.5"/>
          <rect x="16" y="34" width="14" height="14" rx="3" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="1.5"/>
          <rect x="34" y="34" width="14" height="6" rx="3" fill="var(--primary-50)" stroke="var(--primary-200)" stroke-width="1.5"/>
          <rect x="34" y="43" width="14" height="5" rx="2.5" fill="var(--primary-50)" stroke="var(--primary-200)" stroke-width="1"/>
        </svg>
        
        <!-- 搜索空状态 -->
        <svg v-else-if="illustration === 'search'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="28" cy="28" r="14" stroke="var(--primary-200)" stroke-width="2.5"/>
          <path d="M38 38l12 12" stroke="var(--primary-300)" stroke-width="2.5" stroke-linecap="round"/>
          <circle cx="28" cy="28" r="3" fill="var(--primary-100)"/>
          <path d="M20 44l-6 6M18 18l-4-4" stroke="var(--primary-100)" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        
        <!-- 通用空状态 -->
        <svg v-else-if="illustration === 'empty'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="12" y="16" width="40" height="32" rx="6" stroke="var(--primary-200)" stroke-width="2.5"/>
          <path d="M12 28h40" stroke="var(--primary-100)" stroke-width="2.5"/>
          <circle cx="22" cy="22" r="3" fill="var(--primary-300)"/>
          <rect x="20" y="34" width="24" height="6" rx="3" fill="var(--primary-50)"/>
          <rect x="20" y="44" width="14" height="4" rx="2" fill="var(--primary-50)"/>
        </svg>

        <!-- 文件夹空状态 -->
        <svg v-else-if="illustration === 'folder'" viewBox="0 0 64 64" width="56" height="56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M8 18c0-2.2 1.8-4 4-4h12l4 4h24c2.2 0 4 1.8 4 4v24c0 2.2-1.8 4-4 4H12c-2.2 0-4-1.8-4-4V18z" stroke="var(--primary-200)" stroke-width="2.5"/>
          <path d="M8 26h48" stroke="var(--primary-100)" stroke-width="2.5"/>
          <rect x="20" y="32" width="24" height="6" rx="3" fill="var(--primary-50)"/>
          <rect x="20" y="42" width="14" height="4" rx="2" fill="var(--primary-50)"/>
          <circle cx="48" cy="20" r="8" fill="var(--primary-100)" stroke="var(--primary-200)" stroke-width="2"/>
          <path d="M45 20h6M48 17v6" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round"/>
        </svg>
        
        <!-- 默认空状态（保持兼容） -->
        <svg v-else viewBox="0 0 64 64" width="64" height="64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="12" y="16" width="40" height="32" rx="6" stroke="var(--primary-200)" stroke-width="2.5"/>
          <path d="M12 28h40" stroke="var(--primary-100)" stroke-width="2.5"/>
          <circle cx="22" cy="22" r="3" fill="var(--primary-300)"/>
          <rect x="20" y="34" width="24" height="6" rx="3" fill="var(--primary-50)"/>
          <rect x="20" y="44" width="14" height="4" rx="2" fill="var(--primary-50)"/>
        </svg>
      </slot>
    </div>
    
    <h3 class="empty-title" v-if="title">{{ title }}</h3>
    <p class="empty-desc" v-if="description">{{ description }}</p>
    
    <!-- 快捷操作提示 -->
    <div class="empty-tips" v-if="tips?.length">
      <div v-for="(tip, i) in tips" :key="i" class="empty-tip">
        <kbd class="tip-key">{{ tip.key }}</kbd>
        <span class="tip-text">{{ tip.label }}</span>
      </div>
    </div>
    
    <div class="empty-action-bar" v-if="$slots.action">
      <slot name="action" />
    </div>
    
    <div class="empty-actions" v-if="actions?.length">
      <button
        v-for="(act, i) in actions"
        :key="i"
        :class="['btn', act.type === 'primary' ? 'btn-primary' : 'btn-secondary', { 'is-loading': act.loading }]"
        :disabled="act.loading"
        @click="act.onClick"
        :aria-label="act.ariaLabel || act.text"
      >
        <span v-if="act.loading" class="btn-spinner" aria-hidden="true"></span>
        {{ act.text }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { type Component } from 'vue'

interface Action {
  text: string
  type?: 'primary' | 'secondary' | 'ghost'
  onClick: () => void
  ariaLabel?: string
  loading?: boolean
}

interface Tip {
  key: string
  label: string
}

interface Props {
  icon?: Component
  title: string
  description?: string
  actions?: Action[]
  tips?: Tip[]
  illustration?: 'report' | 'scene' | 'api' | 'recycle' | 'environment' | 'data' | 'project' | 'search' | 'empty' | 'folder' | 'default'
}

defineProps<Props>()
</script>

<style scoped>
/* ── 空状态容器：居中布局 ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16) var(--space-8);
  min-height: 280px;
  text-align: center;
  animation: fadeIn var(--duration-page) var(--ease-out);
}

/* ── 图标容器：64px 圆角软底 + 5s 浮动动画 ── */
.empty-icon-wrapper {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-2xl);
  background: linear-gradient(145deg, var(--color-primary-100), var(--color-primary-200));
  margin-bottom: var(--space-5);
  box-shadow:
    0 8px 32px var(--color-primary-alpha-12),
    inset 0 1px 0 var(--color-white-alpha-50),
    inset 0 -1px 0 var(--color-primary-alpha-10);
  position: relative;
  animation: empty-float 5s ease-in-out infinite;
  transition: transform var(--duration-slow) var(--ease-spring),
              box-shadow var(--duration-base) var(--ease-out);
}

@keyframes empty-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.empty-icon-wrapper::before {
  display: none;
}

.empty-icon-wrapper:hover {
  animation-play-state: paused;
  transform: scale(1.08) translateY(-4px);
  box-shadow:
    0 16px 48px var(--color-primary-alpha-16),
    inset 0 1px 0 var(--color-white-alpha-50);
}

.empty-icon-wrapper:hover::before {
  display: none;
}

.empty-icon {
  color: var(--primary-600);
}

/* ── 标题排版：使用 tokens 变量 ── */
.empty-title {
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
  letter-spacing: var(--tracking-tight);
  line-height: var(--leading-tight);
}

/* ── 描述文字：使用 tokens 变量 ── */
.empty-desc {
  font-size: var(--text-sm);
  color: var(--text-muted);
  max-width: 360px;
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-6);
}

/* 快捷键提示 */
.empty-tips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: center;
  margin-bottom: var(--space-5);
  max-width: 360px;
}

.empty-tip {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2-5);
  background: var(--surface-hover);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  border: 1px solid var(--border-subtle);
}

.tip-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 var(--space-2);
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xs);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  box-shadow: 0 1px 0 var(--border-subtle);
}

.tip-text {
  color: var(--text-muted);
  white-space: nowrap;
}

.empty-action-bar {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.empty-actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

/* 暗色模式 */
html.dark .empty-icon-wrapper {
  background: linear-gradient(145deg, var(--color-primary-alpha-12), var(--color-primary-alpha-06));
  box-shadow:
    0 8px 32px var(--color-black-alpha-28),
    inset 0 1px 0 var(--color-white-alpha-06);
  color: var(--text-secondary);
}

html.dark .empty-desc {
  color: var(--text-secondary);
}

html.dark .tip-key {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  color: var(--text-muted);
}

html.dark .empty-tip {
  background: var(--color-primary-alpha-06);
}

/* 按钮样式 — 与全局按钮风格统一 */
.empty-actions .btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: 8px 20px;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  font-family: inherit;
  line-height: var(--leading-normal);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    transform var(--duration-fast) var(--ease-spring),
    box-shadow var(--duration-base) var(--ease-out),
    background-color var(--duration-fast) var(--ease-smooth),
    border-color var(--duration-fast) var(--ease-smooth),
    color var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
  min-height: 36px;
}
.empty-actions .btn:hover:not(:disabled) {
  transform: translateY(-1px);
}
.empty-actions .btn:active:not(:disabled) {
  transform: translateY(0) scale(var(--press-scale, 0.97));
}
.empty-actions .btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--border-focus);
  outline-offset: 2px;
}
.empty-actions .btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-secondary {
  background: var(--surface-hover);
  color: var(--text-secondary);
  border-color: var(--border-default);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--surface-nested);
  color: var(--text-primary);
  border-color: var(--color-neutral-alpha-14);
  box-shadow: var(--shadow-xs);
}

.btn-primary {
  background: var(--grad-primary);
  color: var(--text-inverse);
  border: none;
  box-shadow: 0 2px 8px var(--color-primary-alpha-16);
}
.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 16px var(--color-primary-alpha-24), 0 2px 6px var(--color-primary-alpha-12);
}

/* 按钮加载状态 — 与全局风格统一 */
.empty-actions .btn.is-loading {
  opacity: 0.7;
  pointer-events: none;
  cursor: default;
  position: relative;
}

.empty-actions .btn-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  margin-right: var(--space-2);
  animation: btnSpin 0.9s linear infinite;
}

@keyframes btnSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 减少动画偏好 */
@media (prefers-reduced-motion: reduce) {
  .empty-state,
  .empty-icon-wrapper,
  .empty-actions .btn {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* 暗色模式按钮适配 */
html.dark .btn-secondary {
  background: var(--color-white-alpha-06);
  color: var(--text-secondary);
  border-color: var(--border-default);
}
html.dark .btn-secondary:hover:not(:disabled) {
  background: var(--color-white-alpha-10);
  color: var(--text-primary);
}
</style>