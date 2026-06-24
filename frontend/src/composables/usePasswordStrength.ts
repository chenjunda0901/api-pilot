import { computed, type Ref } from 'vue'

export interface PasswordStrength {
  level: number       // 0-4
  label: string       // '' | '弱' | '一般' | '强' | '非常强'
  class: string       // '' | 'weak' | 'medium' | 'strong' | 'super'
}

export function usePasswordStrength(password: Ref<string>) {
  const strength = computed<PasswordStrength>(() => {
    const pw = password.value
    if (!pw) return { level: 0, label: '', class: '' }

    let score = 0
    if (pw.length >= 6) score++
    if (pw.length >= 10) score++
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++
    if (/\d/.test(pw)) score++
    if (/[^a-zA-Z0-9]/.test(pw)) score++

    const map: Record<number, PasswordStrength> = {
      1: { level: 1, label: '弱', class: 'weak' },
      2: { level: 2, label: '一般', class: 'medium' },
      3: { level: 3, label: '强', class: 'strong' },
      4: { level: 3, label: '强', class: 'strong' },
      5: { level: 4, label: '非常强', class: 'super' },
    }

    return map[score] || { level: 1, label: '弱', class: 'weak' }
  })

  return { strength }
}
