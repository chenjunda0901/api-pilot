<template>
  <div class="mock-stats">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-statistic title="Total Rules" :value="stats.total_rules" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Enabled" :value="stats.enabled_rules" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Total Hits" :value="stats.total_hits" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Active Rate" :value="activeRate" suffix="%" />
      </el-col>
    </el-row>

    <!-- 匹配率 -->
    <el-divider />
    <h4>Match Rate</h4>
    <el-row :gutter="16">
      <el-col :span="6">
        <el-statistic title="Total Calls" :value="matchRate.total_calls" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Matched" :value="matchRate.matched_calls" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Unmatched (404)" :value="matchRate.unmatched_calls" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="Match Rate" :value="matchRate.match_rate" suffix="%" />
      </el-col>
    </el-row>

    <!-- 调用趋势图 -->
    <el-divider />
    <h4>Call Trend (Last 7 Days)</h4>
    <div v-if="callTrend.length" class="trend-chart">
      <div class="trend-bars">
        <div v-for="item in callTrend" :key="item.date" class="trend-bar-group">
          <div class="trend-bar-wrapper">
            <div
              class="trend-bar"
              :style="{ height: barHeight(item.count) + '%' }"
              :title="`${item.date}: ${item.count} calls`"
            ></div>
          </div>
          <div class="trend-label">{{ item.date.slice(5) }}</div>
          <div class="trend-count">{{ item.count }}</div>
        </div>
      </div>
    </div>
    <div v-else class="trend-empty">暂无调用数据</div>

    <!-- Top Hit Rules -->
    <el-divider />
    <h4>Top Hit Rules</h4>
    <el-table :data="stats.top_rules || []" border size="small" max-height="300">
      <el-table-column prop="name" label="Rule" min-width="180" />
      <el-table-column prop="hit_count" label="Hits" width="100" align="center" />
      <el-table-column prop="priority" label="Priority" width="100" align="center" />
      <el-table-column prop="match_path" label="Path" min-width="200" />
      <el-table-column label="Conditions" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.conditions && row.conditions.length" size="small" type="info">
            {{ row.conditions.length }}
          </el-tag>
          <span v-else style="color: var(--text-muted)">-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MockRule } from '../../types'

interface MockStats {
  total_rules: number
  enabled_rules: number
  total_hits: number
  top_rules: MockRule[]
}

interface CallTrendItem {
  date: string
  count: number
}

interface MatchRateData {
  total_calls: number
  matched_calls: number
  unmatched_calls: number
  match_rate: number
}

const props = withDefaults(defineProps<{
  stats: MockStats
  callTrend?: CallTrendItem[]
  matchRate?: MatchRateData
}>(), {
  callTrend: () => [],
  matchRate: () => ({ total_calls: 0, matched_calls: 0, unmatched_calls: 0, match_rate: 0 }),
})

const activeRate = computed(() => {
  if (!props.stats.total_rules) return 0
  return Math.round((props.stats.enabled_rules / props.stats.total_rules) * 100)
})

const maxCount = computed(() => {
  if (!props.callTrend.length) return 1
  return Math.max(...props.callTrend.map(i => i.count), 1)
})

function barHeight(count: number): number {
  if (maxCount.value === 0) return 0
  return Math.max((count / maxCount.value) * 100, 2)
}
</script>

<style scoped>
/* ==========================================
 * MockStatistics 组件样式
 * ==========================================
 * 使用 design tokens 确保主题一致性
 * 支持亮色/暗色模式自动适配
 * ========================================== */

/* 组件根容器：统计面板 */
.mock-stats {
  padding: var(--spacing-lg); /* 16px */
}

/* 统计卡片标题：带底部分隔线 */
h4 {
  margin: 0 0 var(--spacing-md); /* 12px */
  font-size: var(--font-size-sm); /* 14px */
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
  padding-bottom: var(--spacing-sm); /* 8px */
  border-bottom: 1px solid var(--border-subtle);
}

/* 分隔线 token 化覆盖 */
.mock-stats :deep(.el-divider) {
  border-color: var(--border-subtle);
  margin: var(--spacing-lg) 0; /* 16px */
}

/* 统计卡片容器增强：带背景与边框 */
.mock-stats :deep(.el-statistic) {
  padding: var(--spacing-md); /* 12px */
  background: var(--surface-nested);
  border-radius: var(--radius-md); /* 8px */
  border: 1px solid var(--border-subtle);
  transition: background-color var(--duration-fast) var(--ease-smooth),
              border-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
}

/* 统计卡片 hover：增强视觉反馈 */
.mock-stats :deep(.el-statistic:hover) {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

/* 统计数值样式：等宽字体突出显示 */
.mock-stats :deep(.el-statistic__number) {
  font-size: var(--font-size-2xl); /* 24px */
  font-weight: var(--weight-bold);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

/* 统计标题样式：大写辅助文字 */
.mock-stats :deep(.el-statistic__head) {
  font-size: var(--font-size-xs); /* 12px */
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: var(--weight-medium);
  margin-bottom: var(--spacing-xs); /* 4px */
}

/* 调用趋势图 */
.trend-chart {
  padding: var(--spacing-md);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-sm);
  height: 160px;
  padding-bottom: 0;
}

.trend-bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.trend-bar-wrapper {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.trend-bar {
  width: 70%;
  max-width: 48px;
  min-height: 2px;
  background: var(--color-primary, #409eff);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: height 0.3s ease;
  cursor: pointer;
}

.trend-bar:hover {
  opacity: 0.8;
}

.trend-label {
  font-size: var(--font-size-2xs);
  color: var(--text-secondary);
  margin-top: var(--spacing-xs);
  white-space: nowrap;
}

.trend-count {
  font-size: var(--font-size-2xs);
  font-family: var(--font-mono);
  color: var(--text-primary);
  font-weight: var(--weight-semibold);
  margin-top: 2px;
}

.trend-empty {
  text-align: center;
  padding: var(--spacing-lg);
  color: var(--text-muted);
  font-size: var(--font-size-sm);
}

/* 表格 token 化覆盖 */
.mock-stats :deep(.el-table) {
  --el-table-border-color: var(--border-default);
  --el-table-header-bg-color: var(--surface-muted);
  --el-table-header-text-color: var(--text-primary);
  --el-table-row-hover-bg-color: var(--surface-hover);
  --el-table-bg-color: var(--surface-card);
  --el-table-text-color: var(--text-primary);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.mock-stats :deep(.el-table th.el-table__cell) {
  font-weight: var(--weight-semibold);
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.mock-stats :deep(.el-table tr) {
  transition: background-color var(--duration-fast) var(--ease-smooth);
}

.mock-stats :deep(.el-table td.el-table__cell) {
  border-bottom-color: var(--border-default);
}

.mock-stats :deep(.el-tag--info) {
  background: var(--color-info-alpha-10);
  border-color: var(--info-border);
  color: var(--info-text);
  font-weight: var(--weight-medium);
}

.mock-stats :deep(.text-muted) {
  color: var(--text-muted);
  font-style: italic;
}

.mock-stats :deep(.el-table__empty-block) {
  min-height: 120px;
}

.mock-stats :deep(.el-table__empty-text) {
  color: var(--text-muted);
  font-size: var(--font-size-sm);
}

/* ==========================================
 * 暗色模式适配
 * ========================================== */
html.dark .mock-stats :deep(.el-statistic) {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .mock-stats :deep(.el-statistic:hover) {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-sm);
}

html.dark .mock-stats :deep(.el-table) {
  --el-table-border-color: var(--border-default);
  --el-table-header-bg-color: var(--surface-muted);
  --el-table-row-hover-bg-color: var(--surface-hover);
  --el-table-bg-color: var(--surface-card);
  --el-table-text-color: var(--text-primary);
}

html.dark .mock-stats :deep(.el-table th.el-table__cell) {
  color: var(--text-secondary);
}

html.dark .mock-stats :deep(.el-table td.el-table__cell) {
  border-bottom-color: var(--border-default);
}

html.dark .mock-stats :deep(.el-tag--info) {
  background: var(--color-info-alpha-10);
  border-color: var(--info-border);
  color: var(--info-text);
}

html.dark .mock-stats :deep(.el-table__empty-text) {
  color: var(--text-muted);
}

html.dark .mock-stats :deep(.el-divider) {
  border-color: var(--border-subtle);
}

html.dark .trend-chart {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

html.dark .trend-bar {
  background: var(--primary-400, #66b1ff);
}

html.dark .trend-label {
  color: var(--text-secondary);
}

html.dark .trend-count {
  color: var(--text-primary);
}

html.dark .trend-empty {
  color: var(--text-muted);
}
</style>
