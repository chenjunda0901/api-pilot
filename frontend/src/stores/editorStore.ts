// frontend/src/stores/editorStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ApiDefinition, TestCase } from '../types'

export const useEditorStore = defineStore('editor', () => {
  const currentApi = ref<ApiDefinition | null>(null)
  const currentCase = ref<TestCase | null>(null)
  const originalSnapshot = ref<string>('')
  const pendingChanges = ref<boolean>(false)

  const _dirtyFlag = ref(false)
  function markDirty() { _dirtyFlag.value = true }
  function markClean() { _dirtyFlag.value = false }
  const dirty = computed(() => _dirtyFlag.value)

  function openApi(api: ApiDefinition) {
    currentApi.value = JSON.parse(JSON.stringify(api))
    originalSnapshot.value = JSON.stringify(api)
    pendingChanges.value = false
    markClean()
  }

  function openCase(c: TestCase) {
    currentCase.value = JSON.parse(JSON.stringify(c))
    originalSnapshot.value = JSON.stringify(c)
    pendingChanges.value = false
    markClean()
  }

  function markSaved() {
    const current = JSON.stringify(currentApi.value || currentCase.value)
    originalSnapshot.value = current
    pendingChanges.value = false
    markClean()
  }

  function close() {
    currentApi.value = null
    currentCase.value = null
    originalSnapshot.value = ''
    pendingChanges.value = false
    markClean()
  }

  function resetState() {
    currentApi.value = null
    currentCase.value = null
    originalSnapshot.value = ''
    pendingChanges.value = false
    markClean()
  }

  return { currentApi, currentCase, dirty, pendingChanges, openApi, openCase, markSaved, markDirty, markClean, close, resetState }
})
