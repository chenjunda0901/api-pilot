<template>
  <nav class="breadcrumb-nav" aria-label="面包屑导航" role="navigation">
    <ol class="breadcrumb-list">
      <li
        v-for="(item, index) in items"
        :key="index"
        class="breadcrumb-item"
        :aria-current="index === items.length - 1 ? 'page' : undefined"
      >
        <span v-if="index > 0" class="breadcrumb-sep" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </span>
        <router-link
          v-if="item.to && index < items.length - 1"
          :to="item.to"
          class="breadcrumb-link"
        >{{ item.label }}</router-link>
        <span v-else class="breadcrumb-current">{{ item.label }}</span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
defineOptions({ name: 'BreadcrumbNav' })

export interface BreadcrumbItem {
  label: string
  to?: string
}

defineProps<{
  items: BreadcrumbItem[]
}>()
</script>

<style scoped>
.breadcrumb-nav {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
  font-size: var(--text-sm);
  line-height: 1.5;
  margin-bottom: var(--space-3);
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
}

.breadcrumb-sep {
  display: inline-flex;
  align-items: center;
  color: var(--text-disabled);
  margin: 0 var(--space-1-5);
  user-select: none;
  opacity: 0.5;
  flex-shrink: 0;
}
.breadcrumb-sep svg {
  width: 12px;
  height: 12px;
}

.breadcrumb-link {
  color: var(--text-muted);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-smooth);
  font-weight: var(--weight-medium);
  position: relative;
  padding-bottom: 1px;
}

.breadcrumb-link:hover {
  color: var(--primary-600);
}

.breadcrumb-link::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 1px;
  background: currentColor;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform var(--duration-fast) var(--ease-smooth);
}
.breadcrumb-link:hover::after {
  transform: scaleX(1);
}

.breadcrumb-link:active {
  color: var(--primary-700);
}

.breadcrumb-link:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 3px;
  border-radius: var(--radius-sm);
}

.breadcrumb-current {
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
}

/* 暗色模式 */
:global(html.dark) .breadcrumb-nav {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

:global(html.dark) .breadcrumb-link:hover {
  color: var(--primary-400);
}

:global(html.dark) .breadcrumb-link:active {
  color: var(--primary-300);
}

:global(html.dark) .breadcrumb-current {
  color: var(--text-primary);
}
:global(html.dark) .breadcrumb-sep {
  color: var(--text-disabled);
  opacity: 0.35;
}
</style>
