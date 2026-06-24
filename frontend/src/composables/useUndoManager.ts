/**
 * 撤销管理器
 * 用于实现删除、移动等操作的撤销功能
 * 按 editorId 维护独立栈，支持多 Tab 编辑隔离（避免串改）
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface UndoItem {
  id: string
  type: 'delete_api' | 'delete_scene' | 'delete_case' | 'delete_env' | 'move_api' | 'restore_api' | 'restore_scene'
  label: string  // 用于 Toast 显示，如 "删除接口「用户列表」"
  data: Record<string, unknown>
  timestamp: number
  reversible: boolean  // 是否可以重做
}

const MAX_UNDO_SIZE = 50
const UNDO_TIMEOUT_MS = 5 * 60 * 1000  // 5 分钟超时

/** 默认 editorId，向后兼容无 editorId 的调用方 */
const DEFAULT_EDITOR_ID = 'default'

interface EditorStacks {
  undo: UndoItem[]
  redo: UndoItem[]
}

/**
 * 生成唯一 ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

// ============================================================
// Pinia store —— 按 editorId 维护独立撤销/重做栈
// ============================================================

export const useUndoStore = defineStore('undo', () => {
  /** 按 editorId 维护独立栈，避免多 Tab 编辑串改 */
  const stacks = ref<Record<string, EditorStacks>>({})

  /** 变更回调集合（向后兼容 onUndoChange） */
  const _undoChangeCallbacks: Set<() => void> = new Set()

  function notifyChange() {
    _undoChangeCallbacks.forEach(cb => cb())
  }

  /** 获取指定 editorId 的栈（不存在则自动创建） */
  function getStack(editorId: string): EditorStacks {
    if (!stacks.value[editorId]) {
      stacks.value[editorId] = { undo: [], redo: [] }
    }
    return stacks.value[editorId]
  }

  /**
   * 添加到撤销栈
   */
  function pushUndo(
    item: Omit<UndoItem, 'id' | 'timestamp' | 'reversible'>,
    editorId: string = DEFAULT_EDITOR_ID
  ): string {
    const fullItem: UndoItem = {
      ...item,
      id: generateId(),
      timestamp: Date.now(),
      reversible: true,
    }

    const stack = getStack(editorId)
    stack.undo.push(fullItem)

    // 限制栈大小
    if (stack.undo.length > MAX_UNDO_SIZE) {
      stack.undo = stack.undo.slice(-MAX_UNDO_SIZE)
    }

    // 清空重做栈
    stack.redo = []
    notifyChange()

    return fullItem.id
  }

  /**
   * 获取撤销栈
   */
  function getUndoStack(editorId: string = DEFAULT_EDITOR_ID): UndoItem[] {
    return [...(stacks.value[editorId]?.undo || [])]
  }

  /**
   * 获取重做栈
   */
  function getRedoStack(editorId: string = DEFAULT_EDITOR_ID): UndoItem[] {
    return [...(stacks.value[editorId]?.redo || [])]
  }

  /**
   * 是否可以撤销
   */
  function canUndo(editorId: string = DEFAULT_EDITOR_ID): boolean {
    const stack = stacks.value[editorId]
    if (!stack || stack.undo.length === 0) return false
    // 检查超时
    const oldest = stack.undo[0]
    if (Date.now() - oldest.timestamp > UNDO_TIMEOUT_MS) {
      return false
    }
    return stack.undo.length > 0
  }

  /**
   * 是否可以重做
   */
  function canRedo(editorId: string = DEFAULT_EDITOR_ID): boolean {
    const stack = stacks.value[editorId]
    return !!stack && stack.redo.length > 0
  }

  /**
   * 弹出最后一个撤销项（但不执行撤销）
   */
  function peekUndo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
    if (!canUndo(editorId)) return null
    const undoStack = stacks.value[editorId]!.undo
    return undoStack[undoStack.length - 1]
  }

  /**
   * 执行撤销
   */
  function undo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
    if (!canUndo(editorId)) return null

    const stack = stacks.value[editorId]!
    const item = stack.undo.pop()!
    stack.redo.push(item)
    notifyChange()

    return item
  }

  /**
   * 执行重做
   */
  function redo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
    if (!canRedo(editorId)) return null

    const stack = stacks.value[editorId]!
    const item = stack.redo.pop()!
    stack.undo.push(item)
    notifyChange()

    return item
  }

  /**
   * 清空指定 editorId 的历史
   */
  function clearHistory(editorId: string = DEFAULT_EDITOR_ID): void {
    const stack = getStack(editorId)
    stack.undo = []
    stack.redo = []
    notifyChange()
  }

  /**
   * 监听撤销状态变化
   */
  function onUndoChange(callback: () => void): () => void {
    _undoChangeCallbacks.add(callback)
    return () => {
      _undoChangeCallbacks.delete(callback)
    }
  }

  /**
   * 撤销统计
   */
  function getUndoStats(editorId: string = DEFAULT_EDITOR_ID) {
    const stack = stacks.value[editorId]
    return {
      undoCount: stack?.undo.length || 0,
      redoCount: stack?.redo.length || 0,
      oldestTimestamp: stack && stack.undo.length > 0 ? stack.undo[0].timestamp : null,
    }
  }

  return {
    stacks,
    pushUndo,
    getUndoStack,
    getRedoStack,
    canUndo,
    canRedo,
    peekUndo,
    undo,
    redo,
    clearHistory,
    onUndoChange,
    getUndoStats,
  }
})

// ============================================================
// 向后兼容的独立导出 —— 委托给 Pinia store，使用默认 editorId
// 现有调用方（message.ts / useShortcuts.ts）无需改动
// ============================================================

export function pushUndo(
  item: Omit<UndoItem, 'id' | 'timestamp' | 'reversible'>,
  editorId: string = DEFAULT_EDITOR_ID
): string {
  return useUndoStore().pushUndo(item, editorId)
}

export function getUndoStack(editorId: string = DEFAULT_EDITOR_ID): UndoItem[] {
  return useUndoStore().getUndoStack(editorId)
}

export function getRedoStack(editorId: string = DEFAULT_EDITOR_ID): UndoItem[] {
  return useUndoStore().getRedoStack(editorId)
}

export function canUndo(editorId: string = DEFAULT_EDITOR_ID): boolean {
  return useUndoStore().canUndo(editorId)
}

export function canRedo(editorId: string = DEFAULT_EDITOR_ID): boolean {
  return useUndoStore().canRedo(editorId)
}

export function peekUndo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
  return useUndoStore().peekUndo(editorId)
}

export function undo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
  return useUndoStore().undo(editorId)
}

export function redo(editorId: string = DEFAULT_EDITOR_ID): UndoItem | null {
  return useUndoStore().redo(editorId)
}

export function clearHistory(editorId: string = DEFAULT_EDITOR_ID): void {
  useUndoStore().clearHistory(editorId)
}

export function onUndoChange(callback: () => void): () => void {
  return useUndoStore().onUndoChange(callback)
}

export function getUndoStats(editorId: string = DEFAULT_EDITOR_ID) {
  return useUndoStore().getUndoStats(editorId)
}

/**
 * 创建撤销项的便捷函数
 */
export function createDeleteUndo(
  type: UndoItem['type'],
  label: string,
  data: Record<string, unknown>
): Omit<UndoItem, 'id' | 'timestamp'> {
  return { type, label, data, reversible: true }
}

// ============================================================
// composable 封装，方便组件使用
// 接收 editorId 参数，绑定到指定编辑器实例的栈
// ============================================================

export function useUndoManager(editorId: string = DEFAULT_EDITOR_ID) {
  const store = useUndoStore()

  // 使用 computed 自动响应 store 状态变化（无需手动订阅）
  const undoStack = computed(() => store.getUndoStack(editorId))
  const redoStack = computed(() => store.getRedoStack(editorId))

  return {
    undoStack,
    redoStack,
    canUndo: () => store.canUndo(editorId),
    canRedo: () => store.canRedo(editorId),
    pushUndo: (item: Omit<UndoItem, 'id' | 'timestamp' | 'reversible'>) => store.pushUndo(item, editorId),
    undo: () => store.undo(editorId),
    redo: () => store.redo(editorId),
    peekUndo: () => store.peekUndo(editorId),
    clearHistory: () => store.clearHistory(editorId),
  }
}
