/**
 * ECharts 主题注册
 *
 * 为 ECharts 注册亮色/暗色两套主题，配合 composables/useEchartsTheme.ts
 * 在用户切换全局主题时自动适配图表样式。
 *
 * 主题与 utils/theme.ts 的 'light' | 'dark' 主题一一对应：
 *   - 'light' -> 'ap-light'
 *   - 'dark'  -> 'ap-dark'
 *
 * @example
 * ```ts
 * import * as echarts from 'echarts'
 * import { ECHARTS_THEMES } from '@/utils/echartsTheme'
 *
 * const isDark = document.documentElement.classList.contains('dark')
 * const chart = echarts.init(el, isDark ? ECHARTS_THEMES.dark : ECHARTS_THEMES.light)
 * ```
 */

import * as echarts from 'echarts'

/**
 * ECharts 主题对象类型，结构上与 EChartsCoreOption 兼容
 */
type EchartsTheme = Record<string, unknown>

/**
 * 亮色主题
 */
const light: EchartsTheme = {
  color: ['#5A86F0', '#3dcb85', '#e8b236', '#d96b6b', '#9b7ce8', '#5ac8c8'],
  textStyle: {
    color: '#2d2c3b',
  },
  tooltip: {
    backgroundColor: '#ffffff',
    borderColor: '#e4e6ef',
    textStyle: {
      color: '#2d2c3b',
    },
  },
  xAxis: {
    axisLine: { lineStyle: { color: '#d8dae5' } },
    axisLabel: { color: '#6b7283' },
    splitLine: { lineStyle: { color: '#eef0f6' } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: '#d8dae5' } },
    axisLabel: { color: '#6b7283' },
    splitLine: { lineStyle: { color: '#eef0f6' } },
  },
}

/**
 * 暗色主题
 */
const dark: EchartsTheme = {
  color: ['#8aa8fa', '#6dcf9e', '#fcd34d', '#f8a5a5', '#b89ce8', '#5ac8c8'],
  textStyle: {
    color: '#dde4f0',
  },
  tooltip: {
    backgroundColor: '#252938',
    borderColor: '#3a4054',
    textStyle: {
      color: '#dde4f0',
    },
  },
  xAxis: {
    axisLine: { lineStyle: { color: '#3a4054' } },
    axisLabel: { color: '#9ba3b8' },
    splitLine: { lineStyle: { color: '#2f3447' } },
  },
  yAxis: {
    axisLine: { lineStyle: { color: '#3a4054' } },
    axisLabel: { color: '#9ba3b8' },
    splitLine: { lineStyle: { color: '#2f3447' } },
  },
}

echarts.registerTheme('ap-light', light)
echarts.registerTheme('ap-dark', dark)

/**
 * ECharts 主题名称映射常量
 *
 * 用作 echarts.init(el, themeName) 的第二参数。
 */
export const ECHARTS_THEMES = {
  light: 'ap-light',
  dark: 'ap-dark',
} as const

/**
 * ECHARTS_THEMES 值的字面量类型
 */
export type EchartsThemeName = (typeof ECHARTS_THEMES)[keyof typeof ECHARTS_THEMES]
