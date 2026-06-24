<template>
  <div class="diff-viewer">
    <!-- 顶部：摘要信息 -->
    <div class="diff-summary" v-if="normalizedDiff">
      <div class="diff-summary-item added">
        <span class="diff-summary-icon">+</span>
        <span class="diff-summary-num">{{ addedCount }}</span>
        <span class="diff-summary-label">新增</span>
      </div>
      <div class="diff-summary-item removed">
        <span class="diff-summary-icon">−</span>
        <span class="diff-summary-num">{{ removedCount }}</span>
        <span class="diff-summary-label">删除</span>
      </div>
      <div class="diff-summary-item modified">
        <span class="diff-summary-icon">~</span>
        <span class="diff-summary-num">{{ modifiedCount }}</span>
        <span class="diff-summary-label">修改</span>
      </div>
      <div class="diff-summary-item breaking" v-if="normalizedDiff.breaking">
        <el-tag type="danger" effect="dark" size="small">Breaking</el-tag>
      </div>
    </div>

    <!-- 主体：行级 diff -->
    <div class="diff-body" v-if="normalizedDiff && normalizedDiff.ops.length">
      <div
        v-for="(op, idx) in normalizedDiff.ops"
        :key="idx"
        class="diff-line"
        :class="['type-' + opType(op.op)]"
      >
        <div class="diff-line-marker">
          <span v-if="op.op === 'add'">+</span>
          <span v-else-if="op.op === 'remove'">−</span>
          <span v-else>~</span>
        </div>
        <div class="diff-line-content">
          <div class="diff-line-path">
            <code>{{ op.path }}</code>
          </div>
          <div class="diff-line-values">
            <div v-if="'old' in op" class="diff-value old">
              <span class="diff-value-label">原值</span>
              <code>{{ stringify(op.old) }}</code>
            </div>
            <div v-if="'new' in op" class="diff-value new">
              <span class="diff-value-label">新值</span>
              <code>{{ stringify(op.new) }}</code>
            </div>
          </div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else-if="normalizedDiff"
      illustration="empty"
      title="无差异"
      description="两个快照完全一致"
    />
    <EmptyState
      v-else
      illustration="empty"
      title="未选择快照"
      description="请在顶部选择 A、B 两个快照"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EmptyState from '@/components/EmptyState.vue'
import type { SnapshotDiff } from '@/api/snapshots'

const props = defineProps<{
  diff: SnapshotDiff | null
}>()

const normalizedDiff = computed(() => props.diff)

const addedCount = computed(() => normalizedDiff.value?.ops.filter(o => o.op === 'add').length ?? 0)
const removedCount = computed(() => normalizedDiff.value?.ops.filter(o => o.op === 'remove').length ?? 0)
const modifiedCount = computed(() => normalizedDiff.value?.ops.filter(o => o.op === 'replace' || o.op === 'type_change').length ?? 0)

function opType(op: string): string {
  if (op === 'add') return 'added'
  if (op === 'remove') return 'removed'
  return 'modified'
}

function stringify(v: unknown): string {
  if (v === null) return 'null'
  if (v === undefined) return 'undefined'
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return '[object]'
  }
}
</script>

<style scoped>
.diff-viewer {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
}

.diff-summary {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.diff-summary-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 4px 10px;
  background: var(--surface-hover);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
}
.diff-summary-icon {
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
}
.diff-summary-num { font-weight: var(--weight-semibold); }
.diff-summary-item.added { color: var(--color-success); background: var(--color-success-alpha-08); }
.diff-summary-item.removed { color: var(--color-error); background: var(--color-error-alpha-08); }
.diff-summary-item.modified { color: var(--color-warning); background: var(--color-warning-alpha-08); }

.diff-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--border-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: auto;
}

.diff-line {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--surface-card);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.diff-line.type-added { background: var(--color-success-alpha-08); }
.diff-line.type-removed { background: var(--color-error-alpha-08); }
.diff-line.type-modified { background: var(--color-warning-alpha-08); }

.diff-line-marker {
  width: 16px;
  text-align: center;
  font-weight: var(--weight-bold);
  color: var(--text-muted);
  flex-shrink: 0;
}
.diff-line.type-added .diff-line-marker { color: var(--color-success); }
.diff-line.type-removed .diff-line-marker { color: var(--color-error); }
.diff-line.type-modified .diff-line-marker { color: var(--color-warning); }

.diff-line-content { flex: 1; min-width: 0; }
.diff-line-path {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 2px;
}
.diff-line-path code {
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  word-break: break-all;
}

.diff-line-values { display: flex; flex-direction: column; gap: 2px; }
.diff-value { display: flex; gap: var(--space-2); align-items: flex-start; }
.diff-value-label { color: var(--text-muted); flex-shrink: 0; min-width: 36px; }
.diff-value code {
  word-break: break-all;
  color: var(--text-secondary);
  background: var(--surface-hover);
  padding: 2px 6px;
  border-radius: 3px;
  flex: 1;
}
.diff-value.old code { color: var(--color-error); }
.diff-value.new code { color: var(--color-success); }
</style>
