<template>
  <section class="split-section left-section">
    <div class="section-head">
      <div class="section-head-left">
        <h2 class="section-title">最近执行</h2>
        <div class="filter-tabs">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            class="filter-tab"
            :class="{ active: modelValue === tab.key }"
            @click="$emit('update:modelValue', tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
      <button class="section-link" @click="$emit('viewAll')">查看全部 →</button>
    </div>
    <div class="report-list" :key="reportsKey + modelValue">
      <div v-for="r in reports" :key="r.id" class="report-item" :class="r.status" @click="$emit('selectReport', r.id)"
        tabindex="0"
        @keydown.enter="$emit('selectReport', r.id)"
      >
        <div class="report-item-body">
          <div class="report-item-top">
            <span class="report-id">#{{ r.id }}</span>
            <span class="report-passrate" :class="r.status === 'success' ? 'passed' : 'failed'">
              {{ r.total_count ? Math.round(r.pass_count / r.total_count * 100) : 0 }}%
            </span>
            <span class="report-duration">{{ r.duration ? Number(r.duration).toFixed(2) + 's' : '-' }}</span>
          </div>
          <div class="report-item-bottom">
            <span class="report-scene-name"><span :class="{ 'unnamed-hint': !r.scene_name }">{{ r.scene_name || '未命名场景' }}</span></span>
            <span class="report-sep">·</span>
            <span class="report-env">{{ r.env_name || '测试环境' }}</span>
            <span class="report-sep">·</span>
            <span class="report-time">{{ formatRelativeTime(r.created_at) }}</span>
          </div>
        </div>
        <button
          class="report-rerun-btn"
          :class="{ loading: rerunLoading === r.id }"
          @click.stop="$emit('rerun', r.id)"
          title="重新执行"
        >
          <Play :size="13" v-if="rerunLoading !== r.id" />
          <span v-else class="rerun-spinner"></span>
          <span>重跑</span>
        </button>
      </div>
      <div v-if="reports.length === 0 && !loading" class="report-empty">
        <div class="report-empty-visual">
          <FileText :size="32" class="report-empty-icon" />
        </div>
        <p class="report-empty-title">
          <template v-if="modelValue === 'all'">还没有执行记录</template>
          <template v-else-if="modelValue === 'success'">暂无通过的记录</template>
          <template v-else>暂无失败的记录</template>
        </p>
        <p v-if="modelValue === 'all'" class="report-empty-desc">运行你的第一个场景，测试结果将在这里展示</p>
        <el-button v-if="modelValue === 'all'" type="primary" size="small" @click="$emit('goToScenes')">
          <Play :size="14" style="margin-right: 4px" />去运行场景
        </el-button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Play, FileText } from 'lucide-vue-next'
import type { TestReport } from '../../types'

const filterTabs = [
  { key: 'all', label: '全部' },
  { key: 'success', label: '通过' },
  { key: 'failed', label: '失败' },
]

defineProps<{
  modelValue: 'all' | 'success' | 'failed'
  reports: TestReport[]
  reportsKey: number
  loading: boolean
  rerunLoading: number | null
}>()

defineEmits<{
  'update:modelValue': [value: 'all' | 'success' | 'failed']
  viewAll: []
  selectReport: [id: number]
  rerun: [id: number]
  goToScenes: []
}>()

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}
</script>
