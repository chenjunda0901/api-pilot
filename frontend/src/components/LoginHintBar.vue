<template>
  <Transition name="slide-down">
    <div v-if="hintBar.visible" class="login-hint-bar" role="banner">
      <div class="hint-content">
        <span class="hint-icon" aria-hidden="true">!</span>
        <span class="hint-text">
          {{ $t('hintBar.loginToContinue') }} <strong>{{ hintBar.actionName }}</strong>{{ $t('hintBar.actionHint') }}
        </span>
      </div>
      <div class="hint-actions">
        <button class="hint-login-btn" @click="hintBar.goLogin()" :aria-label="$t('hintBar.goLogin')">{{ $t('hintBar.goLogin') }}</button>
        <button class="hint-dismiss-btn" @click="hintBar.dismiss()" :aria-label="$t('hintBar.dismiss')">{{ $t('hintBar.dismiss') }}</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { useHintBarStore } from '../stores/hintBarStore'
const hintBar = useHintBarStore()
</script>

<style scoped>
/* ── 登录提示栏：琥珀色渐变背景 ── */
.login-hint-bar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2-5) var(--space-4);
  background: linear-gradient(135deg, var(--color-warning-50), var(--color-warning-100));
  border-bottom: 1px solid var(--color-warning-alpha-12);
  box-shadow: var(--shadow-sm);
}

/* ── 内容区域：图标 + 文字 ── */
.hint-content {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.hint-text strong {
  font-weight: var(--weight-bold);
  color: var(--warning-dark);
}

/* ── 警告图标：圆形徽章 ── */
.hint-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: linear-gradient(135deg, var(--warning), var(--warning-light));
  color: var(--text-inverse);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  flex-shrink: 0;
  line-height: 1;
  box-shadow: var(--shadow-sm);
}

/* ── 操作按钮组 ── */
.hint-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* ── 主按钮：渐变背景 + 悬停提升 ── */
.hint-login-btn {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 var(--space-4);
  background: linear-gradient(135deg, var(--warning), var(--warning-light));
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-smooth);
  box-shadow: var(--shadow-md);
  white-space: nowrap;
}

.hint-login-btn:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}

.hint-login-btn:active {
  transform: translateY(0) scale(var(--press-scale));
}

/* ── 次要按钮：幽灵风格 ── */
.hint-dismiss-btn {
  display: inline-flex;
  align-items: center;
  height: 32px;
  padding: 0 var(--space-3);
  background: var(--color-white-alpha-60);
  border: 1px solid var(--color-warning-alpha-10);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);
  white-space: nowrap;
}

.hint-dismiss-btn:hover {
  color: var(--text-primary);
  background: var(--color-white-alpha-90);
}

/* ── 过渡动画：上下滑动 ── */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--duration-slow) var(--ease-smooth);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-100%);
}

/* ── 暗色模式适配 ── */
html.dark .login-hint-bar {
  background: linear-gradient(180deg, var(--color-warning-alpha-92), var(--color-warning-alpha-88));
  border-bottom-color: var(--color-warning-alpha-16);
}

html.dark .hint-dismiss-btn {
  background: var(--color-white-alpha-06);
  color: var(--text-secondary);
  border-color: var(--color-white-alpha-08);
}

html.dark .hint-dismiss-btn:hover {
  background: var(--color-white-alpha-10);
}
</style>