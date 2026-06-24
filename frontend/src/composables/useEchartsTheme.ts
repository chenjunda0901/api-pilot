/**
 * ECharts 主题响应式 composable
 *
 * 监听 documentElement 的 'dark' class 变化（与 utils/theme.ts 协作），
 * 为图表组件提供响应式的主题状态以及变更订阅能力。
 *
 * 当用户切换全局主题时，调用方应在 onThemeChange 回调里重新初始化图表
 * 或更新其 option，以应用新主题。
 *
 * @example
 * ```ts
 * import { useEchartsTheme } from '@/composables/useEchartsTheme'
 *
 * const { isDark, themeName, onThemeChange } = useEchartsTheme()
 *
 * let chart: echarts.ECharts | null = null
 *
 * onThemeChange(() => {
 *   if (!chart) return
 *   chart.dispose()
 *   chart = echarts.init(el, themeName.value)
 *   chart.setOption(option)
 * })
 * ```
 */

import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import { ECHARTS_THEMES, type EchartsThemeName } from '../utils/echartsTheme'

/**
 * ECharts 主题 composable
 *
 * @returns isDark        - 当前是否为暗色主题（响应式 ref<boolean>）
 * @returns themeName     - 当前 ECharts 主题名称（响应式 ref<EchartsThemeName>）
 * @returns onThemeChange - 注册主题切换监听器
 */
export function useEchartsTheme(): {
  isDark: Ref<boolean>
  themeName: Ref<EchartsThemeName>
  onThemeChange: (fn: () => void) => void
} {
  const isDark = ref<boolean>(false)
  const themeName = ref<EchartsThemeName>(ECHARTS_THEMES.light)
  const listeners: Array<() => void> = []
  let observer: MutationObserver | null = null

  function syncFromDom(): void {
    if (typeof document === 'undefined') return
    const dark = document.documentElement.classList.contains('dark')
    isDark.value = dark
    themeName.value = dark ? ECHARTS_THEMES.dark : ECHARTS_THEMES.light
  }

  function notifyListeners(): void {
    for (const fn of listeners) {
      try {
        fn()
      } catch (err) {
        // 单个监听器异常不影响其他监听器
        // eslint-disable-next-line no-console
        console.warn('[useEchartsTheme] theme change listener threw', err)
      }
    }
  }

  /**
   * 注册一个主题切换监听器，回调会在 documentElement 的 'dark' class
   * 发生变化时被调用。
   */
  function onThemeChange(fn: () => void): void {
    listeners.push(fn)
  }

  onMounted(() => {
    // 1. 初始同步
    syncFromDom()

    // 2. 监听 documentElement 的 class 变化
    if (typeof document !== 'undefined' && typeof MutationObserver !== 'undefined') {
      observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
          if (m.type === 'attributes' && m.attributeName === 'class') {
            syncFromDom()
            notifyListeners()
            break
          }
        }
      })
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class'],
      })
    }
  })

  onUnmounted(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  })

  return {
    isDark,
    themeName,
    onThemeChange,
  }
}
