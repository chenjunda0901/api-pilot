<template>
  <div ref="el" class="sortable-list">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Sortable from 'sortablejs'

const props = defineProps<{
  items: Record<string, unknown>[]
  itemKey: string
  handle?: string
}>()

const emit = defineEmits<{
  'update:items': [items: Record<string, unknown>[]]
  end: []
  start: []
}>()

const el = ref<HTMLElement>()

let sortable: Sortable | null = null

onMounted(() => {
  if (!el.value) return
  sortable = new Sortable(el.value, {
    handle: props.handle || undefined,
    animation: 250,
    easing: 'cubic-bezier(0.2, 1, 0.2, 1)',
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    dragClass: 'sortable-drag',
    forceFallback: true,
    fallbackClass: 'sortable-fallback',
    fallbackOnBody: true,
    fallbackTolerance: 4,
    onStart: () => {
      emit('start')
    },
    onEnd: () => {
      const newOrder: Record<string, unknown>[] = []
      const children = el.value!.children
      const items = props.items
      const key = props.itemKey

      const itemMap = new Map<string, Record<string, unknown>>()
      items.forEach((item: Record<string, unknown>) => {
        itemMap.set(item[key] as string, item)
      })

      for (let i = 0; i < children.length; i++) {
        const child = children[i] as HTMLElement
        const sortableKey = child.getAttribute('data-key')
        if (sortableKey && itemMap.has(sortableKey)) {
          newOrder.push(itemMap.get(sortableKey)!)
        }
      }

      emit('update:items', newOrder)
      emit('end')
    },
  })
})

onUnmounted(() => {
  sortable?.destroy()
})
</script>

<style>
.sortable-ghost {
  opacity: 0.4 !important;
  background: var(--color-primary-alpha-08) !important;
  border: 2px dashed var(--primary-400) !important;
  border-radius: var(--radius-md) !important;
}

.sortable-chosen {
  cursor: grabbing !important;
}

.sortable-drag {
  opacity: 0.9 !important;
  box-shadow: var(--shadow-float) !important;
  transform: scale(1.02) !important;
  background: var(--surface-card) !important;
  border: 1px solid var(--primary-300) !important;
  border-radius: var(--radius-md) !important;
  z-index: 9999 !important;
}

.sortable-fallback {
  opacity: 0.9 !important;
  box-shadow: var(--shadow-float) !important;
  transform: scale(1.02) rotate(1.5deg) !important;
  background: var(--surface-card) !important;
  border: 1px solid var(--primary-300) !important;
  border-radius: var(--radius-md) !important;
  z-index: 9999 !important;
  cursor: grabbing !important;
}
</style>
