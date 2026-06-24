<template>
  <nav class="breadcrumb-nav" aria-label="面包屑导航" role="navigation">
    <ol class="breadcrumb-list">
      <li
        v-for="(item, index) in items"
        :key="index"
        class="breadcrumb-item"
        :aria-current="index === items.length - 1 ? 'page' : undefined"
      >
        <span v-if="index > 0" class="breadcrumb-sep" aria-hidden="true">/</span>
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
  color: var(--text-disabled);
  margin: 0 var(--space-2);
  user-select: none;
  font-weight: var(--weight-regular);
  font-size: var(--text-xs);
  opacity: 0.6;
}

.breadcrumb-link {
  color: var(--text-muted);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-smooth);
  font-weight: var(--weight-medium);
  position: relative;
}

.breadcrumb-link:hover {
  color: var(--primary-600);
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
</style>
