import { onMounted, onUnmounted, ref, readonly } from 'vue'

export type HotkeyAction = () => void

export interface HotkeyBinding {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  description: string
  action: HotkeyAction
  scopes?: string[]
}

// 全局已注册的快捷键列表（用于帮助面板展示）
const registeredHotkeys = ref<HotkeyBinding[]>([])

export function useRegisteredHotkeys() {
  return readonly(registeredHotkeys)
}

function formatKeys(binding: HotkeyBinding): string[] {
  const keys: string[] = []
  if (binding.ctrl) keys.push('Ctrl')
  if (binding.shift) keys.push('Shift')
  if (binding.alt) keys.push('Alt')
  keys.push(binding.key.length === 1 ? binding.key.toUpperCase() : binding.key)
  return keys
}

export function useHotkeys(bindings: HotkeyBinding[]) {
  function handleKeydown(e: KeyboardEvent) {
    // 跳过输入框中的快捷键（除 Escape）
    const tag = (e.target as HTMLElement)?.tagName
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable
    if (isInput && e.key !== 'Escape') return

    for (const binding of bindings) {
      const ctrlMatch = binding.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey)
      const shiftMatch = binding.shift ? e.shiftKey : !e.shiftKey
      const altMatch = binding.alt ? e.altKey : !e.altKey
      const keyMatch = e.key.toLowerCase() === binding.key.toLowerCase()

      if (ctrlMatch && shiftMatch && altMatch && keyMatch) {
        e.preventDefault()
        e.stopPropagation()
        binding.action()
        return
      }
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
    // 注册到全局列表
    for (const b of bindings) {
      if (!registeredHotkeys.value.find(h => h.description === b.description)) {
        registeredHotkeys.value.push(b)
      }
    }
  })
  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
    for (const b of bindings) {
      const idx = registeredHotkeys.value.findIndex(h => h.description === b.description)
      if (idx >= 0) registeredHotkeys.value.splice(idx, 1)
    }
  })
}

export { formatKeys }
