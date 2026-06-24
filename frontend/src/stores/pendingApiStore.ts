// 专门管理"待创建接口"状态
import { defineStore } from 'pinia'
import { reactive, computed } from 'vue'

interface PendingApi {
  tempId: string
  name: string
  method: string
}

export const usePendingApiStore = defineStore('pendingApi', () => {
  // 使用 reactive(Map) 避免全量对象替换的响应式开销
  const apis = reactive(new Map<string, PendingApi>())

  const pendingApisMap = computed(() => {
    const obj: Record<string, PendingApi> = {}
    for (const [k, v] of apis) {
      obj[k] = { ...v }
    }
    return obj
  })

  function addPendingNewApi(categoryId: string | number, name = '新接口', method = 'GET') {
    apis.set(String(categoryId), { tempId: `pending-${Date.now()}`, name, method })
  }

  function updatePendingNewApiName(categoryId: string | number, name: string) {
    const key = String(categoryId)
    const entry = apis.get(key)
    if (entry) {
      entry.name = name
    }
  }

  function removePendingNewApi(categoryId: string | number) {
    apis.delete(String(categoryId))
  }

  function getPendingApi(categoryId: string | number): PendingApi | undefined {
    return apis.get(String(categoryId))
  }

  function resetState() {
    apis.clear()
  }

  return {
    pendingApisMap,
    addPendingNewApi,
    updatePendingNewApiName,
    removePendingNewApi,
    getPendingApi,
    resetState,
  }
})
