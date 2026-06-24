import { ElMessage, ElNotification, ElMessageBox } from 'element-plus'

/**
 * 增强的消息提示工具
 * 提供更友好的用户体验反馈
 */

// 成功消息
export function showSuccess(message: string, duration = 3000) {
  return ElMessage({
    message,
    type: 'success',
    duration,
    showClose: true,
    grouping: true
  })
}

// 错误消息
export function showError(message: string, duration = 4000) {
  return ElMessage({
    message,
    type: 'error',
    duration,
    showClose: true,
    grouping: true
  })
}

// 警告消息
export function showWarning(message: string, duration = 3500) {
  return ElMessage({
    message,
    type: 'warning',
    duration,
    showClose: true,
    grouping: true
  })
}

// 信息消息
export function showInfo(message: string, duration = 3000) {
  return ElMessage({
    message,
    type: 'info',
    duration,
    showClose: true,
    grouping: true
  })
}

// 成功通知
export function notifySuccess(title: string, message: string) {
  return ElNotification({
    title,
    message,
    type: 'success',
    duration: 3000,
    position: 'bottom-right'
  })
}

// 错误通知
export function notifyError(title: string, message: string) {
  return ElNotification({
    title,
    message,
    type: 'error',
    duration: 5000,
    position: 'bottom-right'
  })
}

// 确认对话框
export async function confirm(
  message: string,
  title = '提示',
  options: {
    confirmButtonText?: string
    cancelButtonText?: string
    type?: 'warning' | 'info' | 'success' | 'error'
  } = {}
) {
  const {
    confirmButtonText = '确定',
    cancelButtonText = '取消',
    type = 'warning'
  } = options
  
  try {
    await ElMessageBox.confirm(message, title, {
      confirmButtonText,
      cancelButtonText,
      type,
      draggable: true,
      closeOnClickModal: false
    })
    return true
  } catch {
    return false
  }
}

// 删除确认
export async function confirmDelete(itemName: string, itemType = '项目') {
  return confirm(
    `确定要删除${itemType}「${itemName}」吗？此操作不可恢复。`,
    '删除确认',
    { confirmButtonText: '确认删除', type: 'error' }
  )
}

// 批量删除确认
export async function confirmBatchDelete(count: number, itemType = '项目') {
  return confirm(
    `确定要删除选中的 ${count} 个${itemType}吗？此操作不可恢复。`,
    '批量删除确认',
    { confirmButtonText: '确认删除', type: 'error' }
  )
}

// 加载中提示
export function showLoading(text = '加载中...') {
  return ElMessage({
    message: text,
    type: 'info',
    duration: 0,
    showClose: false,
    icon: undefined,
    customClass: 'loading-message'
  })
}

// 操作成功（带详情）
export function showOperationSuccess(operation: string, details?: string) {
  const message = details ? `${operation}成功：${details}` : `${operation}成功`
  return showSuccess(message)
}

// 操作失败（带原因）
export function showOperationFailed(operation: string, reason?: string) {
  const message = reason ? `${operation}失败：${reason}` : `${operation}失败，请重试`
  return showError(message)
}

// 网络错误提示
export function showNetworkError() {
  return showError('网络连接失败，请检查网络后重试')
}

// 权限错误提示
export function showPermissionError() {
  return showError('没有操作权限，请联系管理员')
}

// 导出所有方法
export default {
  success: showSuccess,
  error: showError,
  warning: showWarning,
  info: showInfo,
  notifySuccess,
  notifyError,
  confirm,
  confirmDelete,
  confirmBatchDelete,
  showLoading,
  showOperationSuccess,
  showOperationFailed,
  showNetworkError,
  showPermissionError
}
