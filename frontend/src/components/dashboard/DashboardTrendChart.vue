<template>
  <section class="trend-section" v-if="trendData.length > 0">
    <div class="trend-head">
      <h2 class="section-title">执行趋势</h2>
      <div class="trend-period-selector">
        <button
          v-for="p in periodOptions"
          :key="p.value"
          class="period-btn"
          :class="{ active: selectedPeriod === p.value }"
          @click="onPeriodChange(p.value)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>
    <div class="trend-stats" v-if="trendData.length > 0">
      <div class="trend-stat-item">
        <span class="trend-stat-label">平均通过率</span>
        <span class="trend-stat-value">{{ Math.round(trendData.reduce((a,b) => a+b, 0) / trendData.length) }}%</span>
      </div>
      <div class="trend-stat-divider"></div>
      <div class="trend-stat-item">
        <span class="trend-stat-label">最高</span>
        <span class="trend-stat-value">{{ Math.max(...trendData) }}%</span>
      </div>
      <div class="trend-stat-divider"></div>
      <div class="trend-stat-item">
        <span class="trend-stat-label">最低</span>
        <span class="trend-stat-value">{{ Math.min(...trendData) }}%</span>
      </div>
    </div>
    <div class="trend-chart" ref="chartRef" role="img" aria-label="执行趋势图表"></div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useEchartsTheme } from '@/composables/useEchartsTheme'

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  trendData: number[]
}>()

const emit = defineEmits<{
  'period-change': [days: number]
}>()

const selectedPeriod = ref(7)
const periodOptions = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
]

function onPeriodChange(days: number) {
  selectedPeriod.value = days
  emit('period-change', days)
}

const { themeName, onThemeChange } = useEchartsTheme()
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

watch(chartRef, (el) => {
  if (!el) {
    chartInstance?.dispose()
    chartInstance = null
    return
  }
  chartInstance = echarts.init(el, themeName.value)
  updateChart()
  onThemeChange(() => updateChart())
})

watch(() => props.trendData, () => {
  if (chartInstance) updateChart()
}, { deep: true })

function resolveCyan(alpha: string): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--color-cyan-alpha-${alpha}`).trim()
  return raw || `rgba(43, 160, 175, ${parseFloat(alpha) / 100})`
}

function generateDayLabels(count: number, totalDays: number): string[] {
  const labels: string[] = []
  const now = new Date()
  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - Math.round((i / (count - 1 || 1)) * (totalDays - 1)))
    labels.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return labels
}

function updateChart() {
  if (!chartInstance) return
  const data = props.trendData

  // 根据数据长度生成对应天数的日期标签
  const days = generateDayLabels(data.length, selectedPeriod.value)

  chartInstance.setOption({
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: days,
      axisLine: { lineStyle: { color: 'var(--border-subtle)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 12 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: 'var(--slate-100)' } },
      axisLabel: { color: 'var(--text-muted)', fontSize: 11, formatter: '{value}%' },
    },
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: 'var(--primary-500)', width: 2.5 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: resolveCyan('15') },
          { offset: 1, color: resolveCyan('03') },
        ]),
      },
      itemStyle: { color: 'var(--primary-500)' },
    }],
    tooltip: {
      trigger: 'axis',
      formatter: (params: { value: number }[]) => `${params[0]?.value ?? 0}%`,
    },
  })
}

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.trend-period-selector {
  display: flex;
  gap: 4px;
  background: var(--surface-hover, #f5f5f5);
  border-radius: var(--radius-md, 6px);
  padding: 2px;
}

.period-btn {
  padding: 2px 10px;
  font-size: var(--text-xs, 12px);
  font-weight: var(--weight-medium, 500);
  color: var(--text-secondary, #666);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  transition: all 200ms var(--ease-smooth, ease);
  white-space: nowrap;
  font-family: inherit;
}

.period-btn:hover {
  color: var(--text-primary, #333);
  background: var(--surface-card, #fff);
}

.period-btn.active {
  color: var(--primary-600, #1a73e8);
  background: var(--surface-card, #fff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
</style>
