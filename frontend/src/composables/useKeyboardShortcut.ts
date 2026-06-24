import { onMounted, onUnmounted } from 'vue'

type KeyHandler = (event: KeyboardEvent) => void

interface ShortcutConfig {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: KeyHandler
  preventDefault?: boolean
}

export function useKeyboardShortcut(shortcuts: ShortcutConfig[]) {
  const handleKeydown = (event: KeyboardEvent) => {
    for (const shortcut of shortcuts) {
      const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
      const ctrlMatch = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : !(event.ctrlKey || event.metaKey)
      const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
      const altMatch = shortcut.alt ? event.altKey : !event.altKey
      
      if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault()
        }
        shortcut.handler(event)
        return
      }
    }
  }
  
  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })
  
  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })
  
  return { handleKeydown }
}

// 使用示例:
// useKeyboardShortcut([
//   { key: 's', ctrl: true, handler: () => save() },
//   { key: 'Escape', handler: () => close() },
// ])