/**
 * Toast 通知工具 - 用户友好版
 * 提供统一的通知提示，包括成功、警告、错误、信息
 */

import { ElMessage, ElNotification, MessageOptions, NotificationOptions } from 'element-plus'

// 友好的操作结果消息 — 克制版（不带感叹号、避免营销词）
const SUCCESS_MESSAGES: Record<string, string> = {
  // 通用
  save: '已保存',
  delete: '已删除',
  update: '已更新',
  create: '已创建',
  copy: '已复制到剪贴板',
  import: '已导入',
  export: '已导出',
  send: '已发送',
  submit: '已提交',

  // 特定操作
  login: '登录成功',
  logout: '已退出登录',
  register: '注册成功',
  refresh: '已刷新',
  reset: '已重置',
  cancel: '已取消',
  close: '已关闭',
}

// 友好的警告消息
const WARNING_MESSAGES: Record<string, string> = {
  unsaved: '有未保存的修改，是否确定离开？',
  duplicate: '已存在相同名称的数据',
  empty: '数据不能为空',
  invalid: '数据格式不正确',
  timeout: '请求超时，请稍后重试',
  network: '网络连接不稳定',
}

// 错误消息映射（技术性错误 -> 友好消息）
const ERROR_MESSAGES: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络后重试',
  'TIMEOUT': '请求超时，请稍后重试',
  'UNAUTHORIZED': '登录已过期，请重新登录',
  'FORBIDDEN': '权限不足，无法执行此操作',
  'NOT_FOUND': '请求的资源不存在',
  'SERVER_ERROR': '服务器繁忙，请稍后重试',
  'VALIDATION_ERROR': '数据格式不正确，请检查后重试',
  'CONFLICT': '数据冲突，请刷新后重试',
}

/**
 * 成功通知
 */
export function showSuccess(message: string, options?: MessageOptions) {
  return ElMessage.success({
    message,
    duration: 3000,
    showClose: true,
    ...options
  })
}

/**
 * 警告通知
 */
export function showWarning(message: string, options?: MessageOptions) {
  return ElMessage.warning({
    message,
    duration: 3500,
    showClose: true,
    ...options
  })
}

/**
 * 错误通知
 */
export function showError(message: string, options?: MessageOptions) {
  return ElMessage.error({
    message,
    duration: 4000,
    showClose: true,
    ...options
  })
}

/**
 * 信息通知
 */
export function showInfo(message: string, options?: MessageOptions) {
  return ElMessage.info({
    message,
    duration: 3000,
    ...options
  })
}

/**
 * 操作成功提示（根据操作类型自动选择消息）
 */
export function showActionSuccess(action: string, customMessage?: string) {
  const message = customMessage || SUCCESS_MESSAGES[action] || '操作成功'
  return showSuccess(message)
}

/**
 * 通用错误提示
 */
export function showActionError(error?: string | Error, fallback = '操作失败，请稍后重试') {
  if (!error) {
    return showError(fallback)
  }
  
  // 如果已经是友好消息，直接显示
  if (typeof error === 'string') {
    if (error.length < 100 && /[\u4e00-\u9fa5]/.test(error)) {
      return showError(error)
    }
    return showError(fallback)
  }
  
  // 错误对象处理
  const errorObj = error as { message?: string; code?: string; response?: { data?: { message?: string } } }
  
  // 优先使用后端返回的友好消息
  const backendMsg = errorObj.response?.data?.message
  if (backendMsg && backendMsg.length < 100 && /[\u4e00-\u9fa5]/.test(backendMsg)) {
    return showError(backendMsg)
  }
  
  // 使用 code 映射
  if (errorObj.code && ERROR_MESSAGES[errorObj.code]) {
    return showError(ERROR_MESSAGES[errorObj.code])
  }
  
  // 使用默认消息
  return showError(fallback)
}

/**
 * 操作确认提示
 */
export function showActionWarning(action: string) {
  const message = WARNING_MESSAGES[action] || '确定要继续吗？'
  return showWarning(message)
}

// ============================================================
// 桌面通知（Notification）
// ============================================================

/**
 * 成功通知（桌面弹窗）
 */
export function notifySuccess(title: string, message: string, options?: NotificationOptions) {
  return ElNotification({
    title,
    message,
    type: 'success',
    duration: 3000,
    ...options
  })
}

/**
 * 错误通知（桌面弹窗）
 */
export function notifyError(title: string, message: string, options?: NotificationOptions) {
  return ElNotification({
    title,
    message,
    type: 'error',
    duration: 5000,
    ...options
  })
}

/**
 * 警告通知（桌面弹窗）
 */
export function notifyWarning(title: string, message: string, options?: NotificationOptions) {
  return ElNotification({
    title,
    message,
    type: 'warning',
    duration: 4000,
    ...options
  })
}

/**
 * 信息通知（桌面弹窗）
 */
export function notifyInfo(title: string, message: string, options?: NotificationOptions) {
  return ElNotification({
    title,
    message,
    type: 'info',
    duration: 3000,
    ...options
  })
}

// ============================================================
// 操作结果处理
// ============================================================

/**
 * 处理操作结果
 */
export function handleResult<T>(
  result: { success?: boolean; message?: string; data?: T } | null | undefined,
  options: {
    successMessage?: string
    errorMessage?: string
    onSuccess?: (data: T) => void
    onError?: (message: string) => void
  } = {}
) {
  const { successMessage, errorMessage, onSuccess, onError } = options
  
  if (result?.success !== false) {
    const msg = result?.message || successMessage || '操作成功'
    showSuccess(msg)
    if (onSuccess && result?.data !== undefined) {
      onSuccess(result.data)
    }
    return true
  } else {
    const msg = result?.message || errorMessage || '操作失败'
    showError(msg)
    if (onError) {
      onError(msg)
    }
    return false
  }
}

/**
 * 异步操作包装器
 */
export async function withNotify<T>(
  fn: () => Promise<T>,
  options: {
    loadingMessage?: string
    successMessage?: string
    errorMessage?: string
    showLoading?: boolean
    showSuccess?: boolean
    showError?: boolean
  } = {}
): Promise<T | undefined> {
  const {
    loadingMessage = '处理中...',
    successMessage = '操作成功',
    errorMessage = '操作失败，请稍后重试',
    showLoading = true,
    showSuccess = true,
    showError = true
  } = options
  
  // 显示loading
  const loading = showLoading ? ElMessage.loading(loadingMessage, { duration: 0 }) : null
  
  try {
    const result = await fn()
    
    // 关闭loading
    if (loading) loading.close()
    
    // 显示成功消息
    if (showSuccess && successMessage) {
      showSuccess(successMessage)
    }
    
    return result
  } catch (error) {
    // 关闭loading
    if (loading) loading.close()
    
    // 显示错误消息
    if (showError) {
      showActionError(error, errorMessage)
    }
    
    return undefined
  }
}

export default {
  // 基础通知
  showSuccess,
  showWarning,
  showError,
  showInfo,
  // 操作便捷方法
  showActionSuccess,
  showActionError,
  showActionWarning,
  // 桌面通知
  notifySuccess,
  notifyError,
  notifyWarning,
  notifyInfo,
  // 结果处理
  handleResult,
  withNotify,
  // 消息常量
  SUCCESS_MESSAGES,
  WARNING_MESSAGES,
  ERROR_MESSAGES
}