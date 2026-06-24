import { ref, watch, onUnmounted, type Ref } from "vue"
import type { ComputedRef } from "vue"

type KeyHandler = (e: KeyboardEvent) => void

interface Shortcut {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  handler: KeyHandler
  description?: string
}

const registeredShortcuts: Shortcut[] = []
let globalHandler: ((e: KeyboardEvent) => void) | null = null

function ensureGlobalHandler() {
  if (globalHandler) return
  globalHandler = (e: KeyboardEvent) => {
    for (const sc of registeredShortcuts) {
      const modKey = sc.ctrl || sc.meta
      const shiftKey = sc.shift
      if (
        e.key.toLowerCase() === sc.key.toLowerCase() &&
        (!modKey || e.ctrlKey || e.metaKey) &&
        (!shiftKey || e.shiftKey)
      ) {
        const tag = (e.target as HTMLElement)?.tagName
        const isEditable = (e.target as HTMLElement)?.isContentEditable
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || isEditable) continue
        e.preventDefault()
        sc.handler(e)
      }
    }
  }
  window.addEventListener("keydown", globalHandler)
}

export function useShortcut(sc: Shortcut) {
  ensureGlobalHandler()
  registeredShortcuts.push(sc)
  onUnmounted(() => {
    const idx = registeredShortcuts.indexOf(sc)
    if (idx >= 0) registeredShortcuts.splice(idx, 1)
  })
}

export function useListNavigation(
  items: Ref<unknown[]> | ComputedRef<unknown[]>,
  onEnter: (index: number) => void
) {
  const activeIndex = ref(0)
  watch(items, (val) => {
    if (activeIndex.value >= val.length) activeIndex.value = Math.max(0, val.length - 1)
  })
  function onKeydown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      activeIndex.value = Math.min(activeIndex.value + 1, items.value.length - 1)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      activeIndex.value = Math.max(activeIndex.value - 1, 0)
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (items.value[activeIndex.value]) onEnter(activeIndex.value)
    }
  }
  return { activeIndex, onKeydown }
}
