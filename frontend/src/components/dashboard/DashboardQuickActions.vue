<template>
  <section class="split-section right-section">
    <div class="section-head">
      <h2 class="section-title">快捷操作</h2>
    </div>
    <div class="quick-grid">
      <div class="quick-section-label">常用操作</div>
      <button class="quick-action-item primary" @click="$emit('newApi')">
        <PlusCircle :size="20" />
        <span>新建接口</span>
      </button>
      <button class="quick-action-item" @click="$emit('import')">
        <Download :size="20" />
        <span>导入接口</span>
      </button>
      <button class="quick-action-item" @click="$emit('settings')">
        <Settings :size="20" />
        <span>环境配置</span>
      </button>
      <button class="quick-action-item" @click="$emit('batchRun')">
        <Zap :size="20" />
        <span>批量执行</span>
      </button>
      <button class="quick-action-item" @click="$emit('stressTest')">
        <Activity :size="20" />
        <span>压力测试</span>
      </button>
    </div>

    <!-- 最近访问 -->
    <div class="quick-divider"></div>
    <div class="quick-section-label">最近访问</div>
    <div class="recent-list" v-if="recentItems.length > 0">
      <div v-for="item in recentItems" :key="item.id" class="recent-item" @click="$emit('goToRecent', item)">
        <span class="recent-icon">{{ item.type === 'scene' ? '📄' : '🔗' }}</span>
        <div class="recent-info">
          <span class="recent-name">{{ item.name }}</span>
          <span class="recent-meta">{{ item.typeLabel }} · {{ formatRelativeTime(item.updated_at) }}</span>
        </div>
      </div>
    </div>
    <div v-else class="recent-empty">
      <div class="recent-empty-icon">📋</div>
      <span class="recent-empty-text">暂无操作记录</span>
      <span class="recent-empty-hint">开始测试你的第一个场景</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { PlusCircle, Download, Settings, Zap, Activity } from 'lucide-vue-next'

defineProps<{
  recentItems: Array<{
    id: number
    name: string
    type: string
    typeLabel: string
    updated_at: string
  }>
}>()

defineEmits<{
  newApi: []
  import: []
  settings: []
  batchRun: []
  stressTest: []
  goToRecent: [item: { id: number; name: string; type: string }]
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
