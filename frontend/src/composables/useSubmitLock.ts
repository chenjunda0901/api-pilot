import { ref, computed, type Ref, type ComputedRef } from 'vue'

export interface UseSubmitLockReturn {
  /** 是否正在加载 */
  loading: Ref<boolean>
  /** 按钮是否禁用（loading 时为 true） */
  disabled: ComputedRef<boolean>
  /** 执行异步操作，自动管理 loading/disabled */
  run: <T>(fn: () => Promise<T>) => Promise<T | undefined>
  /** 手动锁定 */
  lock: () => void
  /** 手动解锁 */
  unlock: () => void
  /** 最近一次错误（run 失败时自动设置） */
  error: Ref<Error | null>
}

/**
 * 提交锁 composable：loading 时禁用按钮，防止重复提交
 * @returns loading 状态、disabled 计算属性、run 包装函数及手动 lock/unlock
 */
export function useSubmitLock(): UseSubmitLockReturn {
  const loading = ref(false)
  const error = ref<Error | null>(null)

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    // 防止重复调用
    if (loading.value) {
      return undefined
    }
    loading.value = true
    error.value = null
    try {
      const result = await fn()
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e : new Error(String(e))
      return undefined
    } finally {
      loading.value = false
    }
  }

  function lock() {
    loading.value = true
  }

  function unlock() {
    loading.value = false
  }

  return { loading, disabled: computed(() => loading.value), run, lock, unlock, error }
}
