import { ref, watch, onMounted, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * 将筛选条件同步到 URL query 参数，实现状态持久化
 * - 页面加载时从 URL query 恢复筛选状态
 * - 筛选状态变化时同步到 URL query
 */
export function useFilterState<T extends Record<string, unknown>>(defaults: T): Ref<T> {
  const route = useRoute()
  const router = useRouter()

  const state = ref({ ...defaults }) as Ref<T>

  // 从 URL query 中恢复状态
  onMounted(() => {
    const query = route.query
    for (const key of Object.keys(defaults)) {
      if (query[key] !== undefined && query[key] !== null) {
        const defaultVal = defaults[key]
        const queryVal = query[key] as string
        // 根据默认值类型进行类型转换
        if (typeof defaultVal === 'number') {
          const num = Number(queryVal)
          if (!isNaN(num)) {
            state.value[key] = num as T[typeof key]
          }
        } else if (typeof defaultVal === 'boolean') {
          state.value[key] = (queryVal === 'true') as T[typeof key]
        } else {
          state.value[key] = queryVal as T[typeof key]
        }
      }
    }
  })

  // 状态变化时同步到 URL（防抖，避免频繁更新 URL）
  let syncTimer: ReturnType<typeof setTimeout> | null = null
  watch(state, (val) => {
    if (syncTimer) clearTimeout(syncTimer)
    syncTimer = setTimeout(() => {
      // 只同步非默认值的参数，保持 URL 简洁
      const query: Record<string, string> = {}
      for (const key of Object.keys(val)) {
        const v = val[key]
        if (v !== defaults[key] && v !== '' && v !== null && v !== undefined) {
          query[key] = String(v)
        }
      }
      const merged = { ...route.query, ...query }
      for (const key of Object.keys(defaults)) {
        if (!(key in query)) {
          delete merged[key]
        }
      }
      void router.replace({ query: merged })

    }, 300)
  }, { deep: true })

  return state
}
