<template>
  <div class="history-tab">
    <div class="history-tab-head">
      <span>变更历史</span>
    </div>
    <SkeletonTable v-if="loading" :rows="4" />
    <div v-else class="history-list">
      <div
        v-for="s in snapshots"
        :key="s.id"
        class="history-item"
        :class="{ active: selectedId === s.id }"
        @click="$emit('select', s)"
      >
        <div class="history-item-head">
          <span class="history-change-type" :class="s.change_type">{{ changeTypeLabel(s.change_type) }}</span>
          <span class="muted">{{ formatTime(s.created_at) }}</span>
        </div>
        <p class="history-msg">{{ s.change_summary || '无说明' }}</p>
      </div>
      <EmptyState
        v-if="!loading && !snapshots.length"
        illustration="data"
        title="暂无历史版本"
        description="保存接口后系统会自动创建快照"
      />
    </div>
    <!-- diff 视图 -->
    <div v-if="selectedId && diff" class="history-diff-section">
      <div class="history-diff-head">
        <span>与当前版本的差异</span>
        <el-button size="small" type="danger" @click="$emit('restore')">回滚到此版本</el-button>
      </div>
      <DiffViewer :diff="diff" />
    </div>
  </div>
</template>

<script setup lang="ts">
import SkeletonTable from '@/components/SkeletonTable.vue'
import EmptyState from '@/components/EmptyState.vue'
import DiffViewer from '@/components/common/DiffViewer.vue'

export interface Snapshot {
  id: number
  change_type: string
  change_summary?: string
  created_at: string
}

export interface SnapshotDiff {
  [key: string]: unknown
}

defineProps<{
  snapshots: Snapshot[]
  loading: boolean
  selectedId: number | null
  diff: SnapshotDiff | null
}>()

defineEmits<{
  select: [snapshot: Snapshot]
  restore: []
}>()

function changeTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    create: '创建', update: '更新', delete: '删除'
  }
  return labels[type] || type
}

function formatTime(val: string | undefined | null): string {
  if (!val) return '--'
  try {
    const d = new Date(val)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${y}-${m}-${day} ${h}:${min}`
  } catch {
    return '--'
  }
}
</script>

<style scoped>
.history-tab {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.history-tab-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 400px;
  overflow-y: auto;
}
.history-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-soft),
              border-color var(--duration-fast) var(--ease-soft);
}
.history-item:hover {
  background: var(--surface-hover);
  border-color: var(--primary-300);
}
.history-item.active {
  background: var(--primary-50);
  border-color: var(--primary-400);
}
.history-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.history-change-type {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  padding: 1px 8px;
  border-radius: var(--radius-full);
}
.history-change-type.create {
  background: var(--success-bg);
  color: var(--success-text);
}
.history-change-type.update {
  background: rgba(90, 152, 199, 0.1);
  color: #3a78a5;
}
.history-change-type.delete {
  background: var(--error-bg);
  color: var(--error-text);
}
.history-msg {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin: 0;
}
.history-diff-section {
  border-top: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.history-diff-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}
.muted {
  color: var(--text-muted);
  font-size: var(--text-xs);
}
</style>
