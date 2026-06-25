/** 统一 Toast 封装 —— 统一时长、关闭行为、防轰炸 grouping */
import { ElMessage } from 'element-plus'
import { h } from 'vue'
import { logger } from '@/utils/logger'
import { pushUndo, createDeleteUndo, type UndoItem } from '@/composables/useUndoManager'

const baseOpts = { grouping: true, showClose: true }

export function msgSuccess(text: string) {
  ElMessage({ ...baseOpts, message: text, type: 'success', duration: 3000 })
}

export function msgError(text: string, onRetry?: () => void) {
  const message = h('div', { class: 'msg-error-content' }, [
    h('span', { class: 'msg-error-text' }, text),
    onRetry
      ? h('button', {
          class: 'msg-error-retry',
          onClick: (e: MouseEvent) => {
            e.stopPropagation()
            onRetry()
            ElMessage.closeAll()
          },
        }, '重试')
      : null,
  ])
  ElMessage({ ...baseOpts, message, type: 'error', duration: 4000 })
}

export function msgWarning(text: string) {
  ElMessage({ ...baseOpts, message: text, type: 'warning', duration: 3500 })
}

export function msgInfo(text: string) {
  ElMessage({ ...baseOpts, message: text, type: 'info', duration: 3000 })
}

/**
 * 带撤销功能的成功消息
 * @param text 消息文本
 * @param undoType 撤销类型
 * @param undoData 撤销数据
 * @param onUndo 撤销处理函数
 */
export function msgSuccessWithUndo(
  text: string,
  undoType: UndoItem['type'],
  undoData: Record<string, unknown>,
  onUndo: () => Promise<void>
) {
  // 注册撤销
  const item = createDeleteUndo(undoType, text, undoData)
  const undoId = pushUndo(item)


  // 监听撤销事件
  const handler = (e: Event) => {
    const detail = (e as CustomEvent).detail
    if (detail?.id === undoId || detail?.type === undoType) {
      window.removeEventListener('app:undo', handler)
      void (async () => {
        try {
          await onUndo()
          ElMessage.success('已撤销')
        } catch (err) {
          logger.error('[undo] failed:', err)
          ElMessage.error('撤销失败，请手动恢复')
        }
      })()
    }
  }
  window.addEventListener('app:undo', handler)

  // 消息消失后自动清理 handler，防止内存泄漏
  setTimeout(() => {
    window.removeEventListener('app:undo', handler)
  }, 5000)


  // 显示消息
  const message = h('div', { class: 'msg-undo-content' }, [
    h('span', { class: 'msg-undo-text' }, text),
    h('button', {
      class: 'msg-undo-btn',
      onClick: () => {
        window.dispatchEvent(new CustomEvent('app:undo', { detail: { id: undoId, type: undoType } }))
        ElMessage.closeAll()
      },
    }, '撤销'),
  ])
  ElMessage({ ...baseOpts, message, type: 'success', duration: 5000 })
}
