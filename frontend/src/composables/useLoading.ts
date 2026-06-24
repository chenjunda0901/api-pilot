import { ref, computed, reactive } from 'vue'
import { ElLoading, ElMessageBox } from 'element-plus'
import { msgSuccess, msgError } from '@/utils/message'

/**
 * 加载状态管理 - 用户友好版
 * 支持：全局loading、局部loading、进度消息、操作确认
 */

// 全局loading管理
let globalLoadingCount = 0
let globalLoadingInstance: ReturnType<typeof ElLoading.service> | null = null

// 局部loading状态
const loadingStates = reactive<Map<string, { loading: boolean; message: string }>>(new Map())

/**
 * 获取指定key的loading状态
 */
function getState(key: string) {
  if (!loadingStates.has(key)) {
    loadingStates.set(key, reactive({ loading: false, message: '' }))
  }
  return loadingStates.get(key)!
}

/**
 * 启动局部loading
 */
export function showLoading(key: string, message = '加载中...') {
  const state = getState(key)
  state.loading = true
  state.message = message
  return () => hideLoading(key)
}

/**
 * 停止局部loading
 */
export function hideLoading(key: string) {
  const state = loadingStates.get(key)
  if (state) {
    state.loading = false
    state.message = ''
  }
}

/**
 * 启动全局loading
 */
export function showGlobalLoading(message = '加载中...') {
  globalLoadingCount++
  
  if (globalLoadingInstance) {
    // 更新文本
    // 注意：此处使用 document.querySelector 访问 Element Plus 内部 DOM 元素，
    // 无法通过 Vue ref 替代，因为该元素由 ElLoading.service 动态创建而非模板渲染。
    const textEl = document.querySelector('.el-loading-text')
    if (textEl) textEl.textContent = message
    return () => hideGlobalLoading()
  }
  
  globalLoadingInstance = ElLoading.service({
    fullscreen: true,
    lock: true,
    text: message,
    background: 'rgba(0, 0, 0, 0.6)',
    customClass: 'user-friendly-loading'
  })
  
  return () => hideGlobalLoading()
}

/**
 * 停止全局loading
 */
export function hideGlobalLoading() {
  globalLoadingCount = Math.max(0, globalLoadingCount - 1)
  if (globalLoadingCount === 0 && globalLoadingInstance) {
    globalLoadingInstance.close()
    globalLoadingInstance = null
  }
}

/**
 * 带loading的异步操作 - 核心API
 */
export function useLoading(initialState = false) {
  const isLoading = ref(initialState)
  const loadingText = ref('')
  const error = ref<Error | null>(null)
  
  const startLoading = (text = '加载中...') => {
    isLoading.value = true
    loadingText.value = text
    error.value = null
  }
  
  const stopLoading = () => {
    isLoading.value = false
    loadingText.value = ''
  }
  
  const setLoadingError = (err: Error | string) => {
    isLoading.value = false
    error.value = err instanceof Error ? err : new Error(err)
  }
  
  // 包装异步函数，自动管理loading状态
  const withLoading = async <T>(
    fn: () => Promise<T>,
    options: {
      loadingText?: string
      successText?: string
      errorText?: string
      showLoading?: boolean
      showSuccess?: boolean
      showError?: boolean
    } = {}
  ): Promise<T | undefined> => {
    const {
      loadingText: lt = '加载中...',
      successText = '',
      errorText = '操作失败，请稍后重试',
      showLoading: _showLoading = true,
      showSuccess = true,
      showError = true
    } = options
    
    startLoading(lt)
    
    try {
      const result = await fn()
      stopLoading()
      if (showSuccess && successText) {
        msgSuccess(successText)
      }
      return result
    } catch (err) {
      setLoadingError(err as Error)
      if (showError && errorText) {
        msgError(errorText)
      }
      return undefined
    }
  }
  
  const hasError = computed(() => error.value !== null)
  const errorMessage = computed(() => {
    const msg = error.value?.message || ''
    // 如果是技术性错误，替换为友好消息
    if (msg.includes('Error') || msg.length > 100 || !/[\u4e00-\u9fa5]/.test(msg)) {
      return '操作失败，请稍后重试'
    }
    return msg
  })
  
  return {
    isLoading,
    loadingText,
    error,
    hasError,
    errorMessage,
    startLoading,
    stopLoading,
    setLoadingError,
    withLoading
  }
}

// 多个加载状态管理
export function useMultipleLoading() {
  const loadingStates = ref<Map<string, boolean>>(new Map())
  
  const setLoading = (key: string, loading: boolean) => {
    loadingStates.value.set(key, loading)
  }
  
  const isLoading = (key: string) => {
    return loadingStates.value.get(key) || false
  }
  
  const isAnyLoading = computed(() => {
    return Array.from(loadingStates.value.values()).some(v => v)
  })
  
  const withLoading = async <T>(key: string, fn: () => Promise<T>): Promise<T> => {
    setLoading(key, true)
    try {
      return await fn()
    } finally {
      setLoading(key, false)
    }
  }
  
  return {
    setLoading,
    isLoading,
    isAnyLoading,
    withLoading
  }
}

// ============================================================
// 便捷操作函数
// ============================================================

/**
 * 操作确认对话框 - 用户友好
 */
export async function confirmAction(
  title: string,
  message: string,
  options: {
    confirmText?: string
    cancelText?: string
    type?: 'warning' | 'danger' | 'info' | 'success'
  } = {}
): Promise<boolean> {
  const {
    confirmText = '确定',
    cancelText = '取消',
    type = 'warning'
  } = options
  
  // 确认消息优化
  const friendlyMessages: Record<string, string> = {
    delete: '删除后数据将无法恢复，请确认是否继续',
    reset: '此操作将重置所有数据，是否继续？',
    clear: '确定要清空吗？此操作不可撤销',
    submit: '确认提交吗？提交后将无法修改',
  }
  
  // 如果消息是已知操作，替换为友好提示
  const friendlyMsg = friendlyMessages[message] || message
  
  return new Promise((resolve) => {
    ElMessageBox.confirm(friendlyMsg, title, {
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      type,
      roundButton: true,
      closeOnClickModal: false,
      closeOnPressEscape: false,
    }).then(() => resolve(true)).catch(() => resolve(false))
  })
}

/**
 * 危险操作确认（红色警告样式）
 */
export async function confirmDanger(
  title: string,
  message: string,
  confirmText = '确认删除'
): Promise<boolean> {
  return confirmAction(title, message, {
    confirmText,
    cancelText: '取消',
    type: 'danger'
  })
}

/**
 * 操作成功后显示消息并跳转
 */
export function successGoTo(message: string, path: string, delay = 1500) {
  msgSuccess(message)
  setTimeout(() => {
    window.location.href = path
  }, delay)
}

/**
 * 操作成功后显示消息并返回
 */
export function successGoBack(message: string, delay = 1500) {
  msgSuccess(message)
  setTimeout(() => {
    if (window.history.length > 1) {
      window.history.back()
    } else {
      window.location.href = '/'
    }
  }, delay)
}

/**
 * 操作成功后显示消息并刷新
 */
export function successReload(message: string, delay = 1500) {
  msgSuccess(message)
  setTimeout(() => {
    window.location.reload()
  }, delay)
}

/**
 * 进度指示器消息
 */
const progressMsgs = [
  '正在加载，请稍候...',
  '正在处理数据...',
  '马上就好...',
  '请稍候...',
  '正在准备中...'
]

export function getProgressMessage(): string {
  return progressMsgs[Math.floor(Math.random() * progressMsgs.length)]
}

export default {
  // Loading管理
  showLoading,
  hideLoading,
  showGlobalLoading,
  hideGlobalLoading,
  useLoading,
  useMultipleLoading,
  // 便捷操作
  confirmAction,
  confirmDanger,
  successGoTo,
  successGoBack,
  successReload,
  getProgressMessage
}
