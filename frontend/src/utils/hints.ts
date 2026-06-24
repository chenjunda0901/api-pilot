/**
 * 工具提示配置 - 用户友好版
 * 提供统一的操作提示和快捷键说明
 */

// 操作提示映射
export const ACTION_HINTS: Record<string, { title: string; hint: string; shortcut?: string }> = {
  // 通用操作
  save: {
    title: '保存',
    hint: '保存当前修改',
    shortcut: 'Ctrl + S'
  },
  delete: {
    title: '删除',
    hint: '确认要删除吗？删除后无法恢复',
    shortcut: 'Delete'
  },
  cancel: {
    title: '取消',
    hint: '放弃当前修改',
    shortcut: 'Esc'
  },
  submit: {
    title: '提交',
    hint: '提交后将无法修改',
  },
  
  // 编辑器操作
  copy: {
    title: '复制',
    hint: '复制到剪贴板',
    shortcut: 'Ctrl + C'
  },
  paste: {
    title: '粘贴',
    hint: '从剪贴板粘贴',
    shortcut: 'Ctrl + V'
  },
  cut: {
    title: '剪切',
    hint: '剪切选中文本',
    shortcut: 'Ctrl + X'
  },
  undo: {
    title: '撤销',
    hint: '撤销上一步操作',
    shortcut: 'Ctrl + Z'
  },
  redo: {
    title: '重做',
    hint: '恢复撤销的操作',
    shortcut: 'Ctrl + Y'
  },
  
  // API相关
  sendRequest: {
    title: '发送请求',
    hint: '发送API请求并查看响应',
    shortcut: 'Ctrl + Enter'
  },
  addParameter: {
    title: '添加参数',
    hint: '添加新的请求参数',
  },
  addHeader: {
    title: '添加头部',
    hint: '添加HTTP请求头',
  },
  addBody: {
    title: '添加请求体',
    hint: '添加JSON或表单数据',
  },
  
  // 场景相关
  runScene: {
    title: '运行场景',
    hint: '执行测试场景中的所有步骤',
    shortcut: 'F5'
  },
  addStep: {
    title: '添加步骤',
    hint: '在场景中添加新的测试步骤',
  },
  reorder: {
    title: '调整顺序',
    hint: '拖拽调整步骤顺序',
  },
}

// 操作友好的中文描述
export const ACTION_LABELS: Record<string, string> = {
  // CRUD 操作
  create: '创建',
  read: '查看',
  update: '更新',
  delete: '删除',
  
  // 状态操作
  enable: '启用',
  disable: '禁用',
  activate: '激活',
  deactivate: '停用',
  
  // 导入导出
  import: '导入',
  export: '导出',
  download: '下载',
  upload: '上传',
  
  // 测试操作
  run: '运行',
  stop: '停止',
  pause: '暂停',
  resume: '继续',
  retry: '重试',
  debug: '调试',
  
  // 数据操作
  save: '保存',
  reset: '重置',
  clear: '清空',
  refresh: '刷新',
  sync: '同步',
  backup: '备份',
  
  // 用户操作
  login: '登录',
  logout: '退出',
  register: '注册',
  edit: '编辑',
  view: '查看',
  share: '分享',
  copy: '复制',
}

// 友好的确认提示
export const CONFIRM_MESSAGES: Record<string, string> = {
  // 危险操作
  'delete': '确定要删除吗？此操作不可撤销。',
  'deleteAll': '确定要删除全部吗？此操作不可撤销。',
  'reset': '确定要重置吗？重置后数据将无法恢复。',
  'clear': '确定要清空吗？此操作不可撤销。',
  'uninstall': '确定要卸载吗？卸载后需要重新安装。',
  
  // 重要操作
  'submit': '确认提交吗？提交后将无法修改。',
  'publish': '确认发布吗？发布后将对外可见。',
  'activate': '确认启用吗？启用后将对用户生效。',
  
  // 常规操作
  'confirm': '确定要继续吗？',
  'cancel': '确定要取消吗？',
}

// 友好的状态描述
export const STATUS_LABELS: Record<string, { label: string; description: string }> = {
  pending: {
    label: '待处理',
    description: '任务正在排队等待执行'
  },
  running: {
    label: '执行中',
    description: '任务正在执行，请稍候'
  },
  success: {
    label: '成功',
    description: '任务已成功完成'
  },
  failed: {
    label: '失败',
    description: '任务执行失败，请检查配置'
  },
  cancelled: {
    label: '已取消',
    description: '任务已被取消'
  },
  timeout: {
    label: '超时',
    description: '任务执行超时，请重试'
  },
  paused: {
    label: '已暂停',
    description: '任务已暂停，可以继续'
  },
}

// 错误提示映射
export const ERROR_HINTS: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络后重试',
  'TIMEOUT': '请求超时，请稍后重试',
  'UNAUTHORIZED': '登录已过期，请重新登录',
  'FORBIDDEN': '权限不足，无法执行此操作',
  'NOT_FOUND': '请求的资源不存在',
  'SERVER_ERROR': '服务器繁忙，请稍后重试',
  'VALIDATION_ERROR': '数据格式不正确，请检查后重试',
  'CONFLICT': '数据冲突，请刷新后重试',
  'RATE_LIMIT': '操作太频繁，请稍后重试',
  'DATABASE_ERROR': '数据库繁忙，请稍后重试',
}

// 表单验证消息
export const VALIDATION_MESSAGES: Record<string, string> = {
  required: '此项为必填项',
  email: '请输入正确的邮箱地址',
  url: '请输入正确的网址',
  phone: '请输入正确的手机号码',
  number: '请输入数字',
  integer: '请输入整数',
  min: '值不能小于 {min}',
  max: '值不能大于 {max}',
  minLength: '至少需要 {minLength} 个字符',
  maxLength: '最多只能输入 {maxLength} 个字符',
  pattern: '格式不正确',
  equalTo: '两次输入不一致',
  date: '请输入正确的日期',
  datetime: '请输入正确的时间',
}

// 格式化验证消息
export function formatValidationMessage(type: string, params?: Record<string, unknown>): string {
  let message = VALIDATION_MESSAGES[type] || '格式不正确'
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      message = message.replace(`{${key}}`, String(value))
    })
  }
  
  return message
}

export default {
  ACTION_HINTS,
  ACTION_LABELS,
  CONFIRM_MESSAGES,
  STATUS_LABELS,
  ERROR_HINTS,
  VALIDATION_MESSAGES,
  formatValidationMessage
}