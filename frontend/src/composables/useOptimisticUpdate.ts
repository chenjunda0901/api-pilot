import { ref } from 'vue'

export interface OptimisticUpdateOptions<T> {
  /** 乐观更新函数，接收当前数据返回新数据 */
  update: (current: T) => T
  /** 实际提交的 API 请求 */
  commit: () => Promise<T>
  /** 回滚函数，接收旧数据恢复状态 */
  rollback: (previous: T) => void
  /** 获取当前数据的函数 */
  getCurrent: () => T
  /**
   * 冲突检测（可选）
   * 返回 true 表示检测到冲突（服务端版本更新）
   */
  versionCheck?: (serverData: T, localData: T) => boolean
}

/**
 * 乐观更新 composable
 *
 * 写操作先乐观更新 UI（即时响应），后台发送请求确认，
 * 失败时自动回滚并提示错误。
 *
 * 用法:
 *   const optimistic = useOptimisticUpdate<ApiItem[]>()
 *   await optimistic.execute({
 *     update: (list) => [...list, newItem],
 *     commit: () => api.createApi(data),
 *     rollback: (prev) => { apiList.value = prev },
 *     getCurrent: () => apiList.value,
 *   })
 */
export function useOptimisticUpdate<T>() {
  const isPending = ref(false)
  const error = ref<Error | null>(null)

  async function execute(options: OptimisticUpdateOptions<T>): Promise<void> {
    const { update, commit, rollback, getCurrent, versionCheck } = options
    const previous = getCurrent()
    error.value = null

    // Step 1: 乐观更新 UI
    isPending.value = true
    try {
      update(previous)

      // Step 2: 后台提交
      const serverData = await commit()

      // Step 3: 冲突检测
      if (versionCheck && versionCheck(serverData, getCurrent())) {
        rollback(previous)
        throw new Error('数据已被他人修改，请刷新后重试')
      }
    } catch (err) {
      // Step 4: 失败回滚
      rollback(previous)
      error.value = err instanceof Error ? err : new Error(String(err))
      throw error.value
    } finally {
      isPending.value = false
    }
  }

  function reset() {
    error.value = null
    isPending.value = false
  }

  return {
    /** 执行乐观更新 */
    execute,
    /** 是否正在提交 */
    isPending,
    /** 最后一次错误 */
    error,
    /** 重置状态 */
    reset,
  }
}