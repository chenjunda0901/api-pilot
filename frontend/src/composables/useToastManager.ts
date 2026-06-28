import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: string
  type: ToastType
  message: string
  duration: number
  action?: { label: string; onClick: () => void }
  createdAt: number
}

const MAX_VISIBLE = 3
const MERGE_WINDOW_MS = 3000

let toastIdCounter = 0
function nextId(): string { return `toast_${++toastIdCounter}_${Date.now()}` }

/**
 * Toast 队列管理器
 *
 * 特性:
 * - 同类错误合并（3s 内相同 message 的 error 合并为 1 条）
 * - 优先级队列：error > warning > success > info
 * - 上限控制：同时最多显示 3 条
 * - 操作反馈风格统一
 *
 * 用法:
 *   const toast = useToastManager()
 *   toast.show({ type: 'success', message: '已保存' })
 *   toast.show({ type: 'error', message: '操作失败' })
 */
export function useToastManager() {
  const queue = ref<ToastItem[]>([])
  const visible = ref<ToastItem[]>([])
  const recentMessages = new Map<string, { count: number; timer: ReturnType<typeof setTimeout> }>()

  function show(options: {
    type: ToastType
    message: string
    action?: { label: string; onClick: () => void }
    duration?: number
  }) {
    const { type, message, action, duration = type === 'error' ? 0 : 3000 } = options

    // 同类合并检查：3s 内相同 type+message 的 toast 合并
    const key = `${type}:${message}`
    const existing = recentMessages.get(key)
    if (existing) {
      existing.count++
      return
    }

    const toast: ToastItem = {
      id: nextId(),
      type,
      message,
      duration,
      action,
      createdAt: Date.now(),
    }

    // 设置合并窗口定时器
    const timer = setTimeout(() => {
      recentMessages.delete(key)
    }, MERGE_WINDOW_MS)
    recentMessages.set(key, { count: 1, timer })

    queue.value.push(toast)
    processQueue()
  }

  function processQueue() {
    // 按优先级排序
    const priority: Record<ToastType, number> = { error: 0, warning: 1, success: 2, info: 3 }
    queue.value.sort((a, b) => priority[a.type] - priority[b.type])

    while (visible.value.length < MAX_VISIBLE && queue.value.length > 0) {
      const toast = queue.value.shift()!
      visible.value.push(toast)
      showToast(toast)
    }
  }

  function showToast(toast: ToastItem) {
    const msg = toast.action
      ? `${toast.message} <span class="toast-action" style="color:var(--el-color-primary);cursor:pointer;margin-left:8px">${toast.action.label}</span>`
      : toast.message

    const instance = ElMessage({
      type: toast.type,
      message: msg,
      duration: toast.duration,
      dangerouslyUseHTMLString: true,
      onClose: () => {
        visible.value = visible.value.filter(v => v.id !== toast.id)
        processQueue()
      },
    })

    // 处理 action 点击
    if (toast.action) {
      // 用 MutationObserver 检测 toast 元素挂载后绑定事件
      const checkInterval = setInterval(() => {
        const toastEl = document.querySelector('.el-message .toast-action') as HTMLElement | null
        if (toastEl) {
          clearInterval(checkInterval)
          toastEl.addEventListener('click', () => {
            toast.action?.onClick()
            instance.close()
          })
        }
      }, 50)
      // 安全清理
      setTimeout(() => clearInterval(checkInterval), 5000)
    }
  }

  function dismiss(id: string) {
    queue.value = queue.value.filter(v => v.id !== id)
    visible.value = visible.value.filter(v => v.id !== id)
  }

  function clear() {
    queue.value = []
    visible.value = []
    recentMessages.forEach(({ timer }) => clearTimeout(timer))
    recentMessages.clear()
    ElMessage.closeAll()
  }

  return { show, dismiss, clear, queue, visible }
}

/** 全局单例 */
export const globalToastManager = useToastManager()