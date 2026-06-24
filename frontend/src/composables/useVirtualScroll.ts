/**
 * 虚拟滚动 Composable
 * 用于优化大量列表项的渲染性能
 */
import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue'

export interface VirtualScrollOptions {
  /** 列表项预估高度 */
  itemHeight?: number
  /** 缓冲区大小（额外渲染的项数） */
  buffer?: number
  /** 容器高度，默认 400 */
  containerHeight?: number
  /** 启用虚拟化的阈值，列表项数量小于该值时不启用虚拟化，默认 50 */
  threshold?: number
}

export interface VirtualScrollReturn<T> {
  /** 可视区域的数据 */
  visibleItems: Ref<T[]>
  /** 总高度占位符样式 */
  totalHeightStyle: ComputedRef<{ height: string; position: 'relative' }>
  /** 偏移量样式（用于 translateY） */
  offsetStyle: ComputedRef<{ transform: string }>
  /** 可视区域索引范围 */
  visibleRange: { start: number; end: number }
  /** 滚动容器 ref */
  scrollContainer: Ref<HTMLElement | null>
  /** 是否启用虚拟化 */
  enabled: ComputedRef<boolean>
  /** 滚动到指定索引 */
  scrollToIndex: (index: number) => void
  /** 滚动到顶部 */
  scrollToTop: () => void
  /** 更新列表数据 */
  updateItems: (items: T[]) => void
  /** 手动触发刷新 */
  refresh: () => void
}

export function useVirtualScroll<T>(
  items: Ref<T[]>,
  options: VirtualScrollOptions = {}
): VirtualScrollReturn<T> {
  const {
    itemHeight = 60,
    buffer = 5,
    containerHeight = 400,
    threshold = 50,
  } = options

  const scrollContainer = ref<HTMLElement | null>(null)
  const scrollTop = ref(0)
  const actualContainerHeight = ref(containerHeight)

  // 是否启用虚拟化
  const enabled = computed(() => items.value.length >= threshold)

  // 计算可视区域能显示的项数
  const visibleCount = computed(() =>
    Math.ceil(actualContainerHeight.value / itemHeight)
  )

  // 计算起始和结束索引
  const startIndex = computed(() =>
    Math.max(0, Math.floor(scrollTop.value / itemHeight) - buffer)
  )

  const endIndex = computed(() =>
    Math.min(items.value.length, startIndex.value + visibleCount.value + buffer * 2)
  )

  // 可视区域数据
  const visibleItems = computed(() => {
    if (!enabled.value) {
      return items.value
    }
    return items.value.slice(startIndex.value, endIndex.value)
  })

  // 总高度
  const totalHeight = computed(() => items.value.length * itemHeight)

  // 偏移量
  const offset = computed(() => startIndex.value * itemHeight)

  // 样式
  const totalHeightStyle = computed(() => {
    if (!enabled.value) {
      return {
        height: 'auto',
        position: 'relative' as const,
      }
    }
    return {
      height: `${totalHeight.value}px`,
      position: 'relative' as const,
    }
  })

  const offsetStyle = computed(() => {
    if (!enabled.value) {
      return { transform: 'none' }
    }
    return { transform: `translateY(${offset.value}px)` }
  })

  const visibleRange = {
    get start() { return startIndex.value },
    get end() { return endIndex.value },
  }

  // 滚动处理
  const handleScroll = (e: Event) => {
    const target = e.target as HTMLElement
    scrollTop.value = target.scrollTop
  }

  // 滚动到指定索引
  const scrollToIndex = (index: number) => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = index * itemHeight
    }
  }

  // 滚动到顶部
  const scrollToTop = () => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = 0
    }
  }

  // 手动刷新
  const refresh = () => {
    if (scrollContainer.value) {
      const { scrollTop: current, clientHeight } = scrollContainer.value
      // 触发响应式更新
      scrollTop.value = current
      void clientHeight
    }
  }

  // 设置容器高度
  onMounted(() => {
    if (scrollContainer.value) {
      actualContainerHeight.value =
        scrollContainer.value.clientHeight || containerHeight
      scrollContainer.value.addEventListener('scroll', handleScroll, {
        passive: true,
      })
    }
  })

  onUnmounted(() => {
    if (scrollContainer.value) {
      scrollContainer.value.removeEventListener('scroll', handleScroll)
    }
  })

  return {
    visibleItems,
    totalHeightStyle,
    offsetStyle,
    visibleRange,
    scrollContainer,
    enabled,
    scrollToIndex,
    scrollToTop,
    updateItems: () => {
      // items 是响应式的，自动更新
    },
    refresh,
  }
}
