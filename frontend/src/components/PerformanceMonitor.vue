<template>
  <div class="performance-monitor" v-if="isVisible">
    <div class="monitor-header">
      <h3>性能监控</h3>
      <button @click="toggleVisibility" class="close-btn">×</button>
    </div>
    
    <div class="monitor-content">
      <!-- 页面加载指标 -->
      <div class="metric-section">
        <h4>页面加载</h4>
        <div class="metric-grid">
          <div class="metric-item">
            <span class="metric-label">页面加载时间</span>
            <span class="metric-value">{{ formatTime(report.summary.averageLoadTime) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">首次绘制</span>
            <span class="metric-value">{{ formatTime(report.summary.averageFirstPaint) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">首次内容绘制</span>
            <span class="metric-value">{{ formatTime(report.summary.averageFirstContentfulPaint) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">最大内容绘制</span>
            <span class="metric-value">{{ formatTime(report.summary.averageLargestContentfulPaint) }}</span>
          </div>
        </div>
      </div>
      
      <!-- 交互性能 -->
      <div class="metric-section">
        <h4>交互性能</h4>
        <div class="metric-grid">
          <div class="metric-item">
            <span class="metric-label">点击响应时间</span>
            <span class="metric-value">{{ formatTime(averageClickResponse) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">输入响应时间</span>
            <span class="metric-value">{{ formatTime(averageInputResponse) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">布局偏移</span>
            <span class="metric-value">{{ report.summary.averageCumulativeLayoutShift.toFixed(3) }}</span>
          </div>
        </div>
      </div>
      
      <!-- 资源加载 -->
      <div class="metric-section">
        <h4>资源加载</h4>
        <div class="metric-grid">
          <div class="metric-item">
            <span class="metric-label">总资源数</span>
            <span class="metric-value">{{ resourceCount }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">总加载时间</span>
            <span class="metric-value">{{ formatTime(totalResourceTime) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">平均加载时间</span>
            <span class="metric-value">{{ formatTime(averageResourceTime) }}</span>
          </div>
        </div>
      </div>
      
      <!-- 最慢资源 -->
      <div class="metric-section">
        <h4>最慢资源 (Top 5)</h4>
        <div class="slow-resources">
          <div v-for="(resource, index) in slowestResources" :key="index" class="resource-item">
            <span class="resource-name">{{ truncateUrl(resource.name || 'Unknown') }}</span>
            <span class="resource-time">{{ formatTime(resource.value) }}</span>
          </div>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="monitor-actions">
        <button @click="refreshMetrics" class="action-btn">刷新</button>
        <button @click="exportMetrics" class="action-btn">导出</button>
        <button @click="clearMetrics" class="action-btn">清除</button>
      </div>
    </div>
  </div>
  
  <!-- 浮动按钮 -->
  <button v-if="!isVisible" @click="toggleVisibility" class="monitor-toggle">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 20V10"></path>
      <path d="M18 20V4"></path>
      <path d="M6 20v-4"></path>
    </svg>
  </button>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { performanceMonitor } from '@/utils/performance'

const isVisible = ref(false)
const report = ref(performanceMonitor.getReport())
let refreshInterval: ReturnType<typeof setInterval> | null = null

// 计算属性
const averageClickResponse = computed(() => {
  const metrics = report.value.metrics.filter(m => m.name === 'click_response_time')
  if (metrics.length === 0) return 0
  return metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length
})

const averageInputResponse = computed(() => {
  const metrics = report.value.metrics.filter(m => m.name === 'input_response_time')
  if (metrics.length === 0) return 0
  return metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length
})

const resourceCount = computed(() => {
  return report.value.metrics.filter(m => m.name === 'resource_load_time').length
})

const totalResourceTime = computed(() => {
  const metrics = report.value.metrics.filter(m => m.name === 'resource_load_time')
  return metrics.reduce((sum, m) => sum + m.value, 0)
})

const averageResourceTime = computed(() => {
  if (resourceCount.value === 0) return 0
  return totalResourceTime.value / resourceCount.value
})

const slowestResources = computed(() => {
  return report.value.metrics
    .filter(m => m.name === 'resource_load_time')
    .sort((a, b) => b.value - a.value)
    .slice(0, 5)
})

// 方法
const toggleVisibility = () => {
  isVisible.value = !isVisible.value
}

const refreshMetrics = () => {
  report.value = performanceMonitor.getReport()
}

const exportMetrics = () => {
  const dataStr = JSON.stringify(report.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `performance-report-${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

const clearMetrics = () => {
  performanceMonitor.clearMetrics()
  report.value = performanceMonitor.getReport()
}

const formatTime = (ms: number) => {
  if (ms < 1) return '< 1ms'
  if (ms < 1000) return `${ms.toFixed(1)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

const truncateUrl = (url: string) => {
  if (url.length > 50) {
    return url.substring(0, 50) + '...'
  }
  return url
}

// 生命周期
onMounted(() => {
  // 每5秒刷新一次指标
  refreshInterval = setInterval(refreshMetrics, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
/* ==========================================
 * PerformanceMonitor 样式
 * 使用 design tokens 确保主题一致性
 * ========================================== */

/* 主面板：固定定位 + 卡片表面 */
.performance-monitor {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 400px;
  max-height: 80vh;
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-drag);
  border: 1px solid var(--border-default);
  z-index: var(--z-max);
  overflow: hidden;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-muted);
}

.monitor-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 关闭按钮 */
.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth);
}

.close-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.monitor-content {
  padding: var(--spacing-lg);
  max-height: calc(80vh - 60px);
  overflow-y: auto;
}

/* ===== 指标区域 ===== */
.metric-section {
  margin-bottom: var(--spacing-2xl);
}

.metric-section h4 {
  margin: 0 0 var(--spacing-md);
  font-size: var(--font-size-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

/* 指标网格：2列布局 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--surface-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
}

.metric-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.metric-value {
  font-size: var(--font-size-lg);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ===== 慢资源列表 ===== */
.slow-resources {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.resource-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--surface-muted);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
}

.resource-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
}

.resource-time {
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  margin-left: var(--spacing-md);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* ===== 操作按钮 ===== */
.monitor-actions {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-lg);
}

.action-btn {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--surface-muted);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--weight-medium);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
              color var(--duration-fast) var(--ease-smooth),
              border-color var(--duration-fast) var(--ease-smooth);
}

.action-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

/* ===== 浮动按钮（折叠状态）===== */
.monitor-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  background: var(--primary-500);
  border: none;
  border-radius: var(--radius-full);
  color: var(--text-inverse);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-float);
  z-index: var(--z-max);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              transform var(--duration-fast) var(--ease-smooth);
}

.monitor-toggle:hover {
  background: var(--primary-600);
  transform: scale(1.05);
}

/* ===== 响应式设计 ===== */
@media (max-width: 640px) {
  .performance-monitor {
    width: calc(100% - 40px);
    left: 20px;
    right: 20px;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }
}

/* ===== 暗色模式适配 ===== */
html.dark .performance-monitor {
  background: var(--surface-card);
  border-color: var(--border-strong);
}

html.dark .monitor-header {
  background: var(--surface-nested);
  border-bottom-color: var(--border-strong);
}

html.dark .metric-item {
  background: var(--surface-nested);
  border-color: var(--border-default);
}

html.dark .resource-item {
  background: var(--surface-nested);
  border-color: var(--border-default);
}

html.dark .action-btn {
  background: var(--surface-nested);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

html.dark .action-btn:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

html.dark .monitor-toggle {
  background: var(--primary-500);
  color: var(--text-inverse);
}

html.dark .monitor-toggle:hover {
  background: var(--primary-400);
}
</style>