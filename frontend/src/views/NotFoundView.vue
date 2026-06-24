<template>
  <div class="not-found">
    <div class="not-found-inner">
      <div class="not-found-code">404</div>
      <h1 class="not-found-title">{{ $t('notFound.title') }}</h1>
      <p class="not-found-desc">{{ $t('notFound.description') }}</p>
      <div class="not-found-actions">
        <router-link to="/dashboard" class="btn-primary">{{ $t('notFound.goHome') }}</router-link>
        <button class="btn-ghost" @click="router.back()">{{ $t('notFound.goBack') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router"
const router = useRouter()
</script>

<style scoped>
/* 404 页面 — 居中展示，使用 design tokens 保持主题一致性 */
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  background: var(--surface-page);
}
.not-found-inner {
  text-align: center;
  max-width: 480px;
  padding: var(--space-8);
}

/* 404 错误码 — 纯色文字 */
.not-found-code {
  font-size: clamp(4rem, 12vw, 96px);
  font-weight: var(--weight-bold);
  color: var(--primary-500);
  line-height: 1;
  margin-bottom: var(--space-4);
  user-select: none;
}
.not-found-title {
  font-size: var(--text-2xl);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-3);
}
.not-found-desc {
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-6);
}
.not-found-actions {
  display: flex;
  gap: var(--space-3);
  justify-content: center;
}
.btn-primary {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2-5) var(--space-6);
  background: var(--grad-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  text-decoration: none;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: opacity var(--duration-base) var(--ease-smooth),
              box-shadow var(--duration-base) var(--ease-smooth);
}
.btn-primary:hover {
  opacity: 0.9;
  box-shadow: var(--shadow-md);
}
.btn-ghost {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2-5) var(--space-6);
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background-color var(--duration-base) var(--ease-smooth),
              color var(--duration-base) var(--ease-smooth),
              border-color var(--duration-base) var(--ease-smooth);
}
.btn-ghost:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

/* ===== 暗色模式 ===== */
html.dark .not-found {
  background: var(--surface-page);
}
html.dark .not-found-title { color: var(--text-primary); }
html.dark .not-found-desc { color: var(--text-secondary); }
html.dark .btn-ghost {
  color: var(--text-secondary);
  border-color: var(--border-default);
}
html.dark .btn-ghost:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}
</style>
