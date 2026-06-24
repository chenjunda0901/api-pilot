import { ref, type Ref } from "vue"

export interface AsyncState<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<string | null>
  execute: (...args: unknown[]) => Promise<T | null>
}

/**
 * Creates a standardized async operation with loading/error state.
 * Usage: const { data, loading, error, execute } = useAsync(fetchFn)
 */
export function useAsync<T>(
  fn: (...args: unknown[]) => Promise<T>,
  initialData: T | null = null
) {
  const data = ref<T | null>(initialData) as Ref<T | null>
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute(...args: unknown[]): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      const result = await fn(...args)
      data.value = result
      return result
    } catch (e: unknown) {
      // Try to extract backend structured error message first
      const axiosErr = e as { response?: { data?: { message?: string; detail?: string } } }
      const msg =
        axiosErr?.response?.data?.message ||
        axiosErr?.response?.data?.detail ||
        (e instanceof Error ? e.message : '未知错误')
      error.value = msg
      return null
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, execute }
}

/**
 * Creates a debounced function.
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}
