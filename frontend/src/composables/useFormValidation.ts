import { computed, reactive, ref, type ComputedRef } from 'vue'

export interface ValidationRule {
  required?: boolean | string
  minLength?: number | { value: number; message: string }
  maxLength?: number | { value: number; message: string }
  pattern?: RegExp | { value: RegExp; message: string }
  url?: boolean | string
  custom?: (value: string) => boolean | string
}

export type Rules<T> = Partial<Record<keyof T, ValidationRule>>

/**
 * 表单验证 composable
 * @param formData 返回当前表单数据的 getter 函数
 * @param rules 各字段的验证规则
 */
export function useFormValidation<T extends Record<string, unknown>>(
  formData: () => T,
  rules: Rules<T>
): {
  errors: ComputedRef<Partial<Record<keyof T, string>>>
  validate: () => boolean
  isValid: ComputedRef<boolean>
  clearError: (field?: keyof T) => void
  touched: Record<keyof T, boolean>
  markTouched: (fieldName: keyof T) => void
  markAllTouched: () => void
} {
  // 已被 clearError 清除的字段集合，这些字段在自动验证时跳过错误展示
  const clearedFields = ref(new Set<keyof T>())

  // touched: tracks which fields have been interacted with
  const touched: Record<keyof T, boolean> = reactive(
    Object.fromEntries((Object.keys(rules) as (keyof T)[]).map((key) => [key, false])) as Record<keyof T, boolean>
  )

  function markTouched(fieldName: keyof T) {
    touched[fieldName] = true
  }

  function markAllTouched() {
    ;(Object.keys(rules) as (keyof T)[]).forEach((key) => {
      touched[key] = true
    })
  }

  /**
   * 验证单个字段，返回错误消息（空字符串表示通过）
   */
  const validateField = (value: unknown, rule: ValidationRule): string => {
    const isEmpty = value === null || value === undefined || value === ''

    // required
    if (rule.required) {
      if (isEmpty) {
        return typeof rule.required === 'string' ? rule.required : '该字段不能为空'
      }
    } else if (isEmpty) {
      // 非必填且为空，跳过其余校验
      return ''
    }

    const strValue = typeof value === 'string' ? value : typeof value === 'number' || typeof value === 'boolean' ? String(value) : ''

    // minLength
    if (rule.minLength !== undefined) {
      const min = typeof rule.minLength === 'number' ? rule.minLength : rule.minLength.value
      if (strValue.length < min) {
        return typeof rule.minLength === 'number'
          ? `长度不能少于 ${min} 个字符`
          : rule.minLength.message
      }
    }

    // maxLength
    if (rule.maxLength !== undefined) {
      const max = typeof rule.maxLength === 'number' ? rule.maxLength : rule.maxLength.value
      if (strValue.length > max) {
        return typeof rule.maxLength === 'number'
          ? `长度不能超过 ${max} 个字符`
          : rule.maxLength.message
      }
    }

    // pattern
    if (rule.pattern !== undefined) {
      const regex = rule.pattern instanceof RegExp ? rule.pattern : rule.pattern.value
      if (!regex.test(strValue)) {
        return rule.pattern instanceof RegExp ? '格式不正确' : rule.pattern.message
      }
    }

    // url
    if (rule.url) {
      const message = typeof rule.url === 'string' ? rule.url : 'URL 格式不正确'
      try {
        new URL(strValue)
      } catch {
        return message
      }
    }

    // custom
    if (rule.custom !== undefined) {
      const result = rule.custom(strValue)
      if (typeof result === 'string') {
        return result
      }
    }

    return ''
  }

  // errors：基于 formData 自动重新验证（ComputedRef）— 仅显示已 touched 的字段错误
  const errors = computed<Partial<Record<keyof T, string>>>(() => {
    const data = formData()
    const result: Partial<Record<keyof T, string>> = {}
    const cleared = clearedFields.value
    ;(Object.keys(rules) as (keyof T)[]).forEach((key) => {
      if (cleared.has(key)) return
      if (!touched[key]) return
      const rule = rules[key]
      if (!rule) return
      const error = validateField(data[key], rule)
      if (error) result[key] = error
    })
    return result
  })

  // isValid：errors 中无非空值即为通过
  const isValid = computed<boolean>(() => {
    return Object.values(errors.value).every((v) => !v)
  })

  // validate：手动触发验证，显示全部错误并返回是否通过
  const validate = (): boolean => {
    clearedFields.value = new Set()
    markAllTouched()
    return isValid.value
  }

  // clearError：清除指定字段或全部错误
  const clearError = (field?: keyof T): void => {
    if (field === undefined) {
      clearedFields.value = new Set(Object.keys(rules) as (keyof T)[])
    } else {
      const next = new Set(clearedFields.value)
      next.add(field)
      clearedFields.value = next
    }
  }

  return { errors, validate, isValid, clearError, touched, markTouched, markAllTouched }
}
