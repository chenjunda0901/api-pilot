<template>
  <div class="category-tree-node">
    <div
      class="category-item"
      :class="{ active: selectedCategoryId === category.id }"
      :style="{ paddingLeft: `calc(var(--space-3) + ${depth * 20}px)` }"
      @click="selectCategory(category.id)"
    >
      <span class="category-expand" @click.stop="toggleCategory(category.id)">
        <span
          v-if="category.children?.length"
          class="expand-icon"
          :class="{ expanded: expandedCategories.has(category.id) }"
        >▶</span>
        <span v-else class="expand-placeholder"></span>
      </span>
      <span class="category-name">{{ category.name }}</span>
      <span class="category-count">{{ category.api_count }}</span>
    </div>
    <div v-if="expandedCategories.has(category.id) && category.children?.length" class="category-children">
      <CategoryTreeNode
        v-for="child in category.children"
        :key="child.id"
        :category="child"
        :depth="depth + 1"
        :selected-category-id="selectedCategoryId"
        :expanded-categories="expandedCategories"
        @select="selectCategory"
        @toggle="toggleCategory"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface CategoryNode {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
  api_count: number
  children: CategoryNode[]
  first_api: {
    id: number
    name: string
    method: string
    category_id: number
    case_count: number
  } | null
}

defineOptions({ name: 'CategoryTreeNode' })

const _props = defineProps<{
  category: CategoryNode
  depth: number
  selectedCategoryId: number | null
  expandedCategories: Set<number>
}>()

const emit = defineEmits<{
  select: [id: number]
  toggle: [id: number]
}>()

function selectCategory(id: number) {
  emit('select', id)
}

function toggleCategory(id: number) {
  emit('toggle', id)
}
</script>

<style scoped>
.category-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px var(--space-3);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  transition: background var(--duration-fast) var(--ease-smooth);
  user-select: none;
}

.category-item:hover {
  background: var(--surface-hover);
}

.category-item.active {
  background: var(--surface-selected);
  color: var(--text-primary);
  font-weight: var(--weight-medium);
}

.category-expand {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.expand-icon {
  font-size: 8px;
  color: var(--text-muted);
  transition: transform 200ms var(--ease-smooth);
  display: inline-block;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.expand-placeholder {
  width: 16px;
  height: 16px;
  display: inline-block;
}

.category-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-count {
  font-size: var(--text-xs);
  color: var(--text-muted);
  background: var(--surface-nested);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  min-width: 20px;
  text-align: center;
}
</style>
