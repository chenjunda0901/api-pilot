<template>
  <div class="report-compare">
    <!-- 基准报告选择 -->
    <div class="compare-header">
      <el-select
        v-model="baselineId"
        placeholder="选择基准报告"
        clearable
        filterable
        class="baseline-select"
      >
        <el-option
          v-for="r in reports"
          :key="r.id"
          :label="r.name + ' (' + r.created_at?.slice(0,10) + ')'"
          :value="r.id"
        />
      </el-select>
    </div>

    <!-- 未选择任何报告 -->
    <div v-if="!baselineId" class="compare-placeholder">
      <ChartBarIcon :size="48" class="placeholder-icon" />
      <p class="placeholder-text">请先选择两份报告进行对比</p>
      <p class="placeholder-hint">选择当前报告后，再选择一份基准报告即可开始对比</p>
    </div>

    <!-- 已选择基准报告，等待对比 -->
    <div v-else-if="baselineId && compareResults.length === 0" class="compare-placeholder">
      <el-icon :size="48" class="placeholder-icon loading-icon"><Loading /></el-icon>
      <p class="placeholder-text">已选择基准报告，正在准备对比...</p>
      <p class="placeholder-hint">对比功能正在完善中，敬请期待</p>
      <el-button type="primary" size="small" @click="showBasicCompare" style="margin-top: 16px">
        查看基本对比
      </el-button>
    </div>

    <!-- 基本对比结果 -->
    <div v-else-if="compareResults.length > 0" class="compare-results">
      <div class="compare-summary">
        <div class="summary-card baseline">
          <h4>基准报告</h4>
          <p>{{ baselineReport?.scene_name || '未知' }}</p>
          <span class="summary-stat">{{ baselineReport?.pass_count ?? 0 }} 通过 / {{ baselineReport?.fail_count ?? 0 }} 失败</span>
        </div>
        <div class="summary-arrow">VS</div>
        <div class="summary-card current">
          <h4>当前报告</h4>
          <p>{{ currentReport?.scene_name || '未知' }}</p>
          <span class="summary-stat">{{ currentReport?.pass_count ?? 0 }} 通过 / {{ currentReport?.fail_count ?? 0 }} 失败</span>
        </div>
      </div>

      <el-table
        :data="compareResults"
        border
        size="small"
        class="compare-table"
      >
        <el-table-column prop="case_name" label="用例名称" min-width="200" />
        <el-table-column label="基准结果" width="120" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="row.baseline_pass ? 'success' : 'fail'" />
            <span class="status-text">{{ row.baseline_pass ? '通过' : '失败' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="当前结果" width="120" align="center">
          <template #default="{ row }">
            <span class="status-dot" :class="row.current_pass ? 'success' : 'fail'" />
            <span class="status-text">{{ row.current_pass ? '通过' : '失败' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="变化" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.regression" class="change-badge regression">
              <TrendingDown :size="12" /> 回归
            </span>
            <span v-else-if="row.improved" class="change-badge improved">
              <TrendingUp :size="12" /> 改善
            </span>
            <span v-else class="change-badge unchanged">
              <Minus :size="12" /> 无变化
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { TestReport } from '../../types'
import { ChartBarIcon, TrendingUpIcon, TrendingDownIcon, MinusIcon, Loading } from '@element-plus/icons-vue'

const TrendingUp = TrendingUpIcon
const TrendingDown = TrendingDownIcon
const Minus = MinusIcon

const props = defineProps<{ reports: TestReport[]; currentReportId: number }>()
const baselineId = ref<number>()
const compareResults = ref<Array<Record<string, unknown>>>([])

const baselineReport = computed(() => {
  if (!baselineId.value) return null
  return props.reports.find(r => r.id === baselineId.value) || null
})

const currentReport = computed(() => {
  return props.reports.find(r => r.id === props.currentReportId) || null
})

watch(baselineId, (val) => {
  if (val) {
    // 选择基准报告后，不立即清空，而是等待用户点击"查看基本对比"
    compareResults.value = []
  } else {
    compareResults.value = []
  }
})

function showBasicCompare() {
  if (!baselineId.value || !props.currentReportId) return

  const baseline = baselineReport.value
  const current = currentReport.value

  if (!baseline || !current) return

  // 生成基本的模拟对比数据（基于报告摘要信息）
  compareResults.value = [
    {
      case_name: '总通过率',
      baseline_pass: (baseline.pass_count ?? 0) > (baseline.fail_count ?? 0),
      current_pass: (current.pass_count ?? 0) > (current.fail_count ?? 0),
      regression: (baseline.pass_count ?? 0) > (current.pass_count ?? 0),
      improved: (current.pass_count ?? 0) > (baseline.pass_count ?? 0),
    },
    {
      case_name: '通过用例数',
      baseline_pass: true,
      current_pass: true,
      regression: false,
      improved: (current.pass_count ?? 0) > (baseline.pass_count ?? 0),
    },
    {
      case_name: '失败用例数',
      baseline_pass: (baseline.fail_count ?? 0) === 0,
      current_pass: (current.fail_count ?? 0) === 0,
      regression: (current.fail_count ?? 0) > (baseline.fail_count ?? 0),
      improved: (current.fail_count ?? 0) < (baseline.fail_count ?? 0),
    },
  ]
}

function _refreshCompare() {
  showBasicCompare()
}
</script>

<style scoped>
/* ==========================================
 * ReportCompare — 报告对比组件样式
 *
 * 策略：
 *   - 全部使用 design tokens（CSS 变量）
 *   - 暗色模式通过 html.dark 选择器自动适配
 *   - 响应式断点 768px 以下全宽布局
 *
 * 样式模块：
 *   1. 根容器（卡片表面）
 *   2. 顶部选择器区域
 *   3. 空状态占位
 *   4. 对比摘要卡片（VS 布局）
 *   5. 对比表格
 *   6. 状态指示器（通过/失败圆点）
 *   7. 变化标签（回归/改善/无变化）
 *   8. 交互状态（hover / active / focus / disabled）
 *   9. 动画
 * ========================================== */

/* 1. 根容器：卡片表面 + 圆角 + 内边距 + 阴影 */
.report-compare {
  padding: var(--spacing-lg);               /* 16px */
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);          /* 12px */
  box-shadow: var(--shadow-sm);
  min-height: 200px;
  transition: box-shadow var(--transition-base),
              border-color var(--transition-base);
}

/* 2. 顶部选择器区域 */
.compare-header {
  margin-bottom: var(--spacing-lg);
}

/* 基准报告下拉框：固定宽度，响应式下 100% */
.baseline-select {
  width: 300px;
  max-width: 100%;
}

/* 3. 空状态占位区域 */
.compare-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-3xl) var(--spacing-lg);   /* 32px 16px */
  color: var(--text-muted);
  text-align: center;
  border-radius: var(--radius-md);
  background: var(--surface-nested);
  margin: var(--spacing-lg) 0;
}

/* 占位图标：淡化处理，避免抢夺注意力 */
.placeholder-icon {
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
  color: var(--text-secondary);
}

.placeholder-text {
  font-size: var(--text-sm);                /* 14px */
  color: var(--text-muted);
  margin: 0 0 var(--spacing-xs);
  font-weight: var(--weight-medium);
}

.placeholder-hint {
  font-size: var(--text-xs);                /* 12px */
  color: var(--text-secondary);
  margin: 0;
  line-height: var(--leading-relaxed);
}

/* 4. 对比摘要卡片区域（基准 VS 当前） */
.compare-summary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--surface-nested);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

/* 摘要卡片：基准 / 当前 */
.summary-card {
  flex: 1;
  text-align: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-card);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  transition: transform var(--transition-base),
              box-shadow var(--transition-base),
              border-color var(--transition-base);
}

.summary-card h4 {
  margin: 0 0 var(--spacing-xs);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  letter-spacing: var(--tracking-wide);
}

.summary-card p {
  margin: 0 0 var(--spacing-xs);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  line-height: var(--leading-tight);
}

.summary-stat {
  font-size: var(--text-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;       /* 等宽数字，防止布局抖动 */
}

/* 基准卡片：左侧强调色带 */
.summary-card.baseline {
  border-left: 3px solid var(--info);
}

/* 当前卡片：右侧强调色带 */
.summary-card.current {
  border-left: 3px solid var(--success);
}

/* VS 分隔符：主色强调 */
.summary-arrow {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--primary-500);
  padding: 0 var(--spacing-sm);
  flex-shrink: 0;
}

/* 5. 对比结果区域 */
.compare-results {
  margin-top: var(--spacing-md);
}

/* 对比表格：圆角裁切 + 边框 */
.compare-table {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  background: var(--surface-card);
}

/* 6. 状态指示圆点（通过 / 失败） */
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  margin-right: var(--spacing-xs);
  vertical-align: middle;
  /* 圆点内阴影增强立体感 */
  box-shadow: inset 0 1px 2px var(--color-neutral-alpha-16);
}

.status-dot.success {
  background: var(--success);
}

.status-dot.fail {
  background: var(--error);
}

.status-text {
  font-weight: var(--weight-medium);
  font-size: var(--text-sm);
  color: var(--text-primary);
  vertical-align: middle;
}

/* 7. 变化标签（回归 / 改善 / 无变化） */
.change-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  line-height: var(--leading-normal);
  transition: transform var(--transition-fast),
              filter var(--transition-fast);
}

/* 回归：危险色背景 + 文字 */
.change-badge.regression {
  background: var(--color-error-alpha-10);
  color: var(--error);
}

/* 改善：成功色背景 + 文字 */
.change-badge.improved {
  background: var(--color-success-alpha-10);
  color: var(--success);
}

/* 无变化：信息色背景 + 文字 */
.change-badge.unchanged {
  background: var(--color-info-alpha-10);
  color: var(--info);
}

/* 8. 交互状态 */

/* 摘要卡片悬停：轻微上浮 + 阴影增强 */
.summary-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--border-strong);
}

/* 摘要卡片按下：回弹反馈 */
.summary-card:active {
  transform: translateY(0) scale(var(--press-scale, 0.97));
  transition-duration: var(--duration-fast);
}

/* 摘要卡片聚焦：键盘导航可见焦点环 */
.summary-card:focus-visible {
  outline: var(--focus-ring-width) solid var(--primary-500);
  outline-offset: 2px;
  box-shadow: var(--shadow-focus);
}

/* 变化标签悬停：轻微强调 */
.change-badge:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

/* 变化标签按下：缩放反馈 */
.change-badge:active {
  transform: scale(var(--press-scale, 0.97));
  transition-duration: var(--duration-fast);
}

/* 禁用态：降低对比度 + 禁止交互 */
.change-badge[disabled],
.summary-card[disabled] {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* 9. 动画 */

/* 加载旋转动画 */
.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ==========================================
 * 暗色模式适配
 * ========================================== */

/* 根容器暗色：使用暗色专用阴影 */
html.dark .report-compare {
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-sm);
}

/* 表格边框与表头背景暗色适配 */
html.dark .compare-table {
  --el-table-border-color: var(--border-default);
  --el-table-header-bg-color: var(--surface-muted);
  --el-table-bg-color: var(--surface-card);
  --el-table-row-hover-bg-color: var(--surface-hover);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-secondary);
  background: var(--surface-card);
  border-color: var(--border-default);
}

/* 摘要卡片暗色：增强边框辨识度 */
html.dark .summary-card {
  background: var(--surface-card);
  border-color: var(--border-strong);
}

html.dark .summary-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}

/* 占位区域暗色适配 */
html.dark .compare-placeholder {
  background: var(--surface-nested);
  border-color: var(--border-subtle);
}

/* 状态圆点暗色：保持语义色 */
html.dark .status-dot.success {
  background: var(--success);
}

html.dark .status-dot.fail {
  background: var(--error);
}

/* 变化标签暗色：保持语义色 */
html.dark .change-badge.regression {
  background: var(--color-error-alpha-10);
  color: var(--error);
}

html.dark .change-badge.improved {
  background: var(--color-success-alpha-10);
  color: var(--success);
}

html.dark .change-badge.unchanged {
  background: var(--color-info-alpha-10);
  color: var(--info);
}

/* ==========================================
 * 响应式设计
 * ========================================== */
@media (max-width: 768px) {
  .baseline-select {
    width: 100%;
  }

  /* 摘要卡片纵向堆叠 */
  .compare-summary {
    flex-direction: column;
    gap: var(--spacing-md);
  }

  /* VS 分隔符旋转 90 度 */
  .summary-arrow {
    transform: rotate(90deg);
  }

  .compare-table {
    font-size: var(--text-xs);
  }

  /* 移动端减少内边距 */
  .report-compare {
    padding: var(--spacing-md);
  }

  .compare-placeholder {
    padding: var(--spacing-xl) var(--spacing-md);
  }
}
</style>
