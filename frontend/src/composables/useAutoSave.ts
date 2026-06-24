import { ref, watch, onUnmounted } from 'vue'
import type { Ref } from 'vue'
import { logger } from '@/utils/logger'

/** 自动保存选项 */
interface AutoSaveOptions {
  /** 防抖延迟，默认1000ms */
  delay?: number
  /** 保存回调函数 */
  onSave: () => Promise<void> | void
  /** 是否启用自动保存，默认 true */
  enabled?: Ref<boolean>
}

/**
 * 自动保存 composable
 *
 * 监听响应式数据变化，防抖后自动调用保存回调。
 *
 * @param data - 要监听的响应式数据
 * @param options - 自动保存配置
 * @returns 保存状态（isSaving, lastSaved, saveNow）
 *
 * @example
 * ```ts
 * const form = ref({ name: '' })
 * const { isSaving, lastSaved, saveNow } = useAutoSave(form, {
 *   delay: 800,
 *   onSave: () => api.saveProject(form.value),
 * })
 * ```
 */
export function useAutoSave<T>(data: Ref<T>, options: AutoSaveOptions) {
  const { delay = 1000, onSave, enabled = ref(true) } = options
  
  const isSaving = ref(false)
  const lastSaved = ref<Date | null>(null)
  const error = ref<Error | null>(null)
  let timer: ReturnType<typeof setTimeout> | null = null

  const save = async () => {
    if (!enabled.value || isSaving.value) return

    isSaving.value = true
    error.value = null
    try {
      await onSave()
      lastSaved.value = new Date()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e : new Error(String(e))
      logger.warn('[useAutoSave] save failed:', e)
    } finally {
      isSaving.value = false
    }
  }
  
  const debouncedSave = () => {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(save, delay)
  }
  
  // 监听数据变化
  const stopWatch = watch(data, debouncedSave, { deep: true })
  
  // 清理
  onUnmounted(() => {
    if (timer) {
      clearTimeout(timer)
    }
    stopWatch()
  })
  
  // 立即保存
  const saveNow = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    return save()
  }
  
  return {
    isSaving,
    lastSaved,
    saveNow,
    error,
  }
}

// 使用示例:
// const formData = ref({ name: '', description: '' })
// const { isSaving, lastSaved, saveNow } = useAutoSave(formData, {
//   delay: 2000,
//   onSave: async () => {
//     await api.update(formData.value)
//   }
// })