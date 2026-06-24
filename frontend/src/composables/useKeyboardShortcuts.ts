import { onMounted, onUnmounted } from 'vue'
import { useHotkeys, type HotkeyBinding } from './useHotkeys'

/**
 * 全局键盘快捷键注册中心
 *
 * 注册所有应用级快捷键到 useHotkeys 全局注册表，
 * 使其可在 HotkeyHelp 面板中展示。
 *
 * 快捷键列表：
 * - Cmd/Ctrl + Enter   → 发送请求
 * - Cmd/Ctrl + S       → 保存当前项
 * - Cmd/Ctrl + Shift + F → 全局搜索
 * - Cmd/Ctrl + K       → 命令面板
 * - Cmd/Ctrl + Shift + K → 快速搜索
 * - Escape             → 关闭对话框/面板
 * - ?                  → 帮助面板（非输入框时）
 */
export function useKeyboardShortcuts() {
  const bindings: HotkeyBinding[] = [
    {
      key: 'Enter',
      ctrl: true,
      description: '发送请求',
      action: () => window.dispatchEvent(new CustomEvent('app:send-request')),
    },
    {
      key: 'Enter',
      ctrl: true,
      shift: true,
      description: '保存并发送',
      action: () => window.dispatchEvent(new CustomEvent('app:save-and-send')),
    },
    {
      key: 's',
      ctrl: true,
      description: '保存',
      action: () => window.dispatchEvent(new CustomEvent('app:save')),
    },
    {
      key: 'f',
      ctrl: true,
      shift: true,
      description: '全局搜索',
      action: () => window.dispatchEvent(new CustomEvent('app:global-search')),
    },
    {
      key: 'k',
      ctrl: true,
      description: '命令面板',
      action: () => window.dispatchEvent(new CustomEvent('app:quick-jump')),
    },
    {
      key: 'k',
      ctrl: true,
      shift: true,
      description: '快速搜索',
      action: () => window.dispatchEvent(new CustomEvent('app:quick-search')),
    },
    {
      key: 'Escape',
      description: '关闭对话框/面板',
      action: () => window.dispatchEvent(new CustomEvent('app:escape')),
    },
  ]

  // ? 键帮助面板：需要特殊处理，仅在非输入框时触发
  function handleHelpKey(e: KeyboardEvent) {
    if (e.key !== '?') return
    const tag = (e.target as HTMLElement)?.tagName
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable
    if (isInput) return
    e.preventDefault()
    window.dispatchEvent(new CustomEvent('app:shortcut-help'))
  }

  useHotkeys(bindings)

  onMounted(() => {
    document.addEventListener('keydown', handleHelpKey)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleHelpKey)
  })
}

/** 格式化快捷键显示文本 */
export function formatShortcut(binding: { ctrl?: boolean; shift?: boolean; alt?: boolean; key: string }): string {
  const mod = navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'
  const parts: string[] = []
  if (binding.ctrl) parts.push(mod)
  if (binding.shift) parts.push('Shift')
  if (binding.alt) parts.push('Alt')
  parts.push(binding.key.length === 1 ? binding.key.toUpperCase() : binding.key)
  return parts.join('+')
}
