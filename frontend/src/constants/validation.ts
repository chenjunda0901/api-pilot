/** 表单校验文案 */

export const VALIDATION_MSG = {
  REQUIRED: (label: string) => `请输入${label}`,
  EMAIL: '请输入有效的邮箱地址',
  PASSWORD_MIN: '密码至少需要 6 位',
  URL_FORMAT: '请输入有效的 URL 地址',
  JSON_FORMAT: '请输入有效的 JSON 格式',
  POSITIVE_INT: '请输入正整数',
  SELECT_REQUIRED: (label: string) => `请选择${label}`,
}
