import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { undo, redo, canUndo, canRedo } from './useUndoManager'

/**
 * 全局键盘快捷键
 * Ctrl+S  保存当前编辑
 * Ctrl+K  搜索/快速跳转
 * Ctrl+/  显示快捷键帮助
 * Ctrl+Z  撤销
 * Ctrl+Shift+Z / Ctrl+Y  重做
 * Escape  关闭弹窗/退出编辑
 */
export function useGlobalShortcuts() {
  const _router = useRouter()

  function handleKeydown(e: KeyboardEvent) {
    const mod = e.ctrlKey || e.metaKey

    // Ctrl+S: 阻止浏览器默认保存，触发自定义保存事件
    if (mod && e.key === 's') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('app:save'))
      return
    }

    // Ctrl+K: 快速跳转
    if (mod && e.key === 'k') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('app:quick-jump'))
      return
    }

    // Ctrl+/: 快捷键帮助
    if (mod && e.key === '/') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('app:shortcut-help'))
      return
    }

    // Ctrl+Z: 撤销
    if (mod && e.key === 'z' && !e.shiftKey) {
      e.preventDefault()
      if (canUndo()) {
        const item = undo()
        if (item) {
          window.dispatchEvent(new CustomEvent('app:undo', { detail: item }))
        }
      }
      return
    }

    // Ctrl+Shift+Z 或 Ctrl+Y: 重做
    if ((mod && e.key === 'z' && e.shiftKey) || (mod && e.key === 'y')) {
      e.preventDefault()
      if (canRedo()) {
        const item = redo()
        if (item) {
          window.dispatchEvent(new CustomEvent('app:redo', { detail: item }))
        }
      }
      return
    }

    // Escape: 关闭最上层弹窗
    if (e.key === 'Escape') {
      window.dispatchEvent(new CustomEvent('app:escape'))
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown)
  })
}
