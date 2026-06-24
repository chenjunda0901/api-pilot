<template>
  <div ref="chartRef" class="report-trend" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useEchartsTheme } from '@/composables/useEchartsTheme'

const props = defineProps<{ data: Record<string, unknown>[] }>()
const { themeName, onThemeChange } = useEchartsTheme()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const cssVar = (name: string, fallback: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

function render() {
  if (!chartRef.value || !props.data.length) return
  if (!chart) chart = echarts.init(chartRef.value, themeName.value)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['Pass Rate %', 'Duration (s)'] },
    xAxis: { type: 'category', data: props.data.map(d => d.created_at?.slice(5, 16) || ''), axisLabel: { rotate: 45 } },
    yAxis: [
      { type: 'value', name: 'Pass Rate %', min: 0, max: 100 },
      { type: 'value', name: 'Duration (s)', min: 0 },
    ],
    series: [
      {
        name: 'Pass Rate %',
        type: 'line',
        data: props.data.map(d => d.pass_rate),
        smooth: true,
        symbol: props.data.length === 1 ? 'circle' : undefined,
        symbolSize: props.data.length === 1 ? 10 : undefined,
        itemStyle: { color: cssVar('--primary-500', '#7488c8') }
      },
      { name: 'Duration (s)', type: 'bar', yAxisIndex: 1, data: props.data.map(d => (d.duration || 0).toFixed(1)), itemStyle: { color: cssVar('--color-info', '#5aa0d0'), opacity: 0.6 } },
    ],
    grid: { left: 50, right: 50, bottom: 60 },
  })
}

watch(() => props.data, render, { deep: true })
onMounted(render)
onThemeChange(() => render())
onUnmounted(() => { chart?.dispose() })
</script>

<style scoped>
/* ==========================================
 * ReportTrend — 报告趋势图表组件样式
 *
 * 策略：
 *   - 图表容器使用卡片表面 + 圆角
 *   - 通过 CSS 变量确保暗色模式适配
 *   - ECharts 主题色在 script 中通过 cssVar() 读取
 * ========================================== */

/* 图表根容器：宽度 100% + 固定高度 300px */
.report-trend {
  width: 100%;
  height: 300px;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

/* 暗色模式下图表容器背景自动适配 */
html.dark .report-trend {
  background: var(--surface-card);
}
</style>
