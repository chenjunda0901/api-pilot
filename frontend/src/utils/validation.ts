/**
 * 表单验证工具
 * 提供常用的表单验证规则
 */

// 必填验证
export const required = (message = '此项为必填项') => ({
  required: true,
  message,
  trigger: ['blur', 'change']
})

// 最小长度
export const minLength = (min: number, message?: string) => ({
  min,
  message: message || `最少输入 ${min} 个字符`,
  trigger: 'blur'
})

// 最大长度
export const maxLength = (max: number, message?: string) => ({
  max,
  message: message || `最多输入 ${max} 个字符`,
  trigger: 'blur'
})

// URL格式验证
export const isUrl = (message = '请输入有效的URL地址') => ({
  type: 'url',
  message,
  trigger: 'blur'
})

// 邮箱格式验证
export const isEmail = (message = '请输入有效的邮箱地址') => ({
  type: 'email',
  message,
  trigger: 'blur'
})

// 数字验证
export const isNumber = (message = '请输入数字') => ({
  type: 'number',
  message,
  trigger: 'blur'
})

// 正则验证
export const pattern = (regex: RegExp, message: string) => ({
  pattern: regex,
  message,
  trigger: 'blur'
})

// API路径验证
export const isApiPath = () => pattern(
  /^\/[\w\-/{}]*$/,
  '请输入有效的API路径，如 /api/users/{id}'
)

// JSON格式验证
export const isJson = (message = '请输入有效的JSON格式') => ({
  validator: (rule: unknown, value: string, callback: (error?: Error) => void) => {
    if (!value) {
      callback()
      return
    }
    try {
      JSON.parse(value)
      callback()
    } catch {
      callback(new Error(message))
    }
  },
  trigger: 'blur'
})

// 组合验证
export const combine = (...rules: Record<string, unknown>[]) => rules.flat()

// 常用组合
export const nameRules = [required('请输入名称'), minLength(2), maxLength(50)]
export const urlRules = [required('请输入URL'), isUrl()]
export const pathRules = [required('请输入路径'), isApiPath()]

export default {
  required,
  minLength,
  maxLength,
  isUrl,
  isEmail,
  isNumber,
  pattern,
  isApiPath,
  isJson,
  combine,
  nameRules,
  urlRules,
  pathRules
}
