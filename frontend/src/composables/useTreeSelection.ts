import { ref } from 'vue'

export function useTreeSelection() {
  const selectedIds = ref<number[]>([])
  const multiSelectMode = ref(false)

  function toggleSelect(id: number, event: MouseEvent) {
    if (event.ctrlKey || event.metaKey || multiSelectMode.value) {
      const idx = selectedIds.value.indexOf(id)
      if (idx >= 0) selectedIds.value.splice(idx, 1)
      else selectedIds.value.push(id)
    }
  }

  function clearSelection() {
    selectedIds.value = []
    multiSelectMode.value = false
  }

  function isSelected(id: number) {
    return selectedIds.value.includes(id)
  }

  return { selectedIds, multiSelectMode, toggleSelect, clearSelection, isSelected }
}
