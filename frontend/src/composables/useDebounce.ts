import { ref, watch, onUnmounted, type Ref } from 'vue'

/**
 * 防抖 composable：对响应式源值进行延迟追踪
 * @param source 返回源值的 getter 函数
 * @param delay 延迟毫秒数，默认 300
 * @returns 防抖后的 Ref
 */
export function useDebounce<T>(source: () => T, delay = 300): Ref<T> {
  const debounced = ref<T>(source()) as Ref<T>

  let timer: ReturnType<typeof setTimeout>
  watch(
    source,
    (val) => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        debounced.value = val
      }, delay)
    }
  )

  onUnmounted(() => clearTimeout(timer))

  return debounced
}
