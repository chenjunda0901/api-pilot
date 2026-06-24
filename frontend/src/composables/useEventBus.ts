import { provide, inject, reactive } from 'vue'

type EventCallback = (...args: unknown[]) => void

interface EventBus {
  on(event: string, cb: EventCallback): void
  off(event: string, cb: EventCallback): void
  emit(event: string, ...args: unknown[]): void
}

const BUS_KEY = Symbol('eventBus')

export function createEventBus(): EventBus {
  // 使用 reactive(Map) 替代 ref(Map)，确保 .set()/.get()/.delete() 是响应式的
  const listeners = reactive(new Map<string, Set<EventCallback>>())

  function on(event: string, cb: EventCallback) {
    if (!listeners.has(event)) {
      listeners.set(event, new Set())
    }
    listeners.get(event)!.add(cb)
  }

  function off(event: string, cb: EventCallback) {
    listeners.get(event)?.delete(cb)
  }

  function emit(event: string, ...args: unknown[]) {
    const cbs = listeners.get(event)
    if (cbs) {
      // 快照拷贝，防止遍历过程中 off() 导致的并发修改
      ;[...cbs].forEach(cb => cb(...args))
    }
  }

  return { on, off, emit }
}

export function provideEventBus() {
  const bus = createEventBus()
  provide(BUS_KEY, bus)
  return bus
}

export function useEventBus() {
  const bus = inject<EventBus>(BUS_KEY)
  if (!bus) throw new Error('useEventBus: no event bus provided')
  return bus
}
