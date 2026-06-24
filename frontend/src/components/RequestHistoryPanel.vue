<template>
  <div class="history-panel">
    <div class="history-header">
      <h3>请求历史</h3>
      <div class="history-actions">
        <el-button size="small" text aria-label="刷新历史" @click="refresh" :disabled="loading">
          <RotateCw :size="14" />
        </el-button>
        <el-button size="small" text type="danger" @click="clearAll">
          清空
        </el-button>
      </div>
    </div>
    <div v-if="loading" class="history-loading">
      <el-skeleton :rows="3" animated />
    </div>
    <div v-else-if="items.length === 0" class="history-empty">
      <History :size="32" />
      <p>暂无请求历史</p>
      <p class="hint">发送请求后将自动记录</p>
    </div>
    <div v-else class="history-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="history-item"
        :class="{ active: selectedId === item.id }"
        @click="selectItem(item)"
      >
        <div class="history-item-row">
          <span class="method-badge" :class="methodClass(item.method)">{{ item.method }}</span>
          <span class="status-badge" :class="statusClass(item.response_status)">{{ item.response_status || '-' }}</span>
          <span class="duration">{{ item.duration_ms }}ms</span>
        </div>
        <div class="history-item-url" :title="item.url">{{ item.url }}</div>
        <div class="history-item-time">{{ formatTime(item.created_at) }}</div>
      </div>
    </div>
    <!-- 选中条目的详情弹窗 -->
    <el-dialog v-model="showDetail" title="请求详情" width="720px" top="5vh">
      <template v-if="selectedItem">
        <div class="detail-section">
          <div class="detail-label">请求 URL</div>
          <el-input :model-value="selectedItem.url" readonly type="textarea" :rows="2" />
        </div>
        <div class="detail-row">
          <div class="detail-section flex-1">
            <div class="detail-label">方法</div>
            <el-tag :type="methodTag(selectedItem.method)" size="small">{{ selectedItem.method }}</el-tag>
          </div>
          <div class="detail-section flex-1">
            <div class="detail-label">状态码</div>
            <el-tag :type="statusTag(selectedItem.response_status)" size="small">{{ selectedItem.response_status || '-' }}</el-tag>
          </div>
          <div class="detail-section flex-1">
            <div class="detail-label">耗时</div>
            <span>{{ selectedItem.duration_ms }}ms</span>
          </div>
        </div>
        <div class="detail-section">
          <div class="detail-label">请求头</div>
          <JsonViewer :data="parseJson(selectedItem.request_headers)" />
        </div>
        <div class="detail-section">
          <div class="detail-label">请求体</div>
          <el-input :model-value="selectedItem.request_body" readonly type="textarea" :rows="4" />
        </div>
        <div class="detail-section">
          <div class="detail-label">响应头</div>
          <JsonViewer :data="parseJson(selectedItem.response_headers)" />
        </div>
        <div class="detail-section">
          <div class="detail-label">响应体</div>
          <el-input :model-value="selectedItem.response_body" readonly type="textarea" :rows="6" />
        </div>
      </template>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
        <el-button type="primary" @click="restoreRequest">恢复请求参数</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import request from '@/api/request'
import { ElMessageBox } from 'element-plus'
import { msgSuccess, msgError } from '@/utils/message'
import { logger, isSilentAuthError } from '@/utils/logger'
import { RotateCw, History } from 'lucide-vue-next'
import JsonViewer from './JsonViewer.vue'
import { useRequireLogin } from '@/composables/useRequireLogin'

const { requireLogin } = useRequireLogin()

interface HistoryItem {
  id: number
  method: string
  response_status: number | null
  duration_ms: number
  url: string
  created_at: string
  request_headers?: string
  request_body?: string
  response_headers?: string
  response_body?: string
}

const props = defineProps<{ apiId: number }>()
const emit = defineEmits<{
  (e: 'restore', data: { url?: string; headers?: string; body?: string }): void
}>()

const items = ref<HistoryItem[]>([])
const loading = ref(false)
const selectedId = ref<number | null>(null)
const selectedItem = ref<HistoryItem | null>(null)
const showDetail = ref(false)

const route = useRoute()
const projectId = computed(() => Number(route.params.id))

function methodClass(m: string) {
  return `method-${(m || '').toLowerCase()}`
}

function statusClass(s: number | null) {
  if (!s) return 'status-unknown'
  if (s < 300) return 'status-success'
  if (s < 400) return 'status-redirect'
  return 'status-error'
}

function methodTag(m: string) {
  const map: Record<string, string> = { get: '', post: 'success', put: 'warning', patch: 'warning', delete: 'danger' }
  return map[(m || '').toLowerCase()] || ''
}

function statusTag(s: number | null) {
  if (!s) return 'info'
  if (s < 300) return 'success'
  if (s < 400) return 'warning'
  return 'danger'
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(11, 19)
}

function parseJson(s: string) {
  if (!s) return []
  try { return JSON.parse(s) } catch { return [] }
}

async function refresh() {
  loading.value = true
  try {
    const res = await request.get(`/projects/${projectId.value}/debug-history`, {
      params: { api_id: props.apiId, limit: 30 },
    })
    items.value = res.data.items || []
  } catch (err) {
    if (!isSilentAuthError(err)) logger.error('[RequestHistoryPanel] refresh history failed:', err)
    items.value = []
  } finally {
    loading.value = false
  }
}

async function clearAll() {
  if (!(await requireLogin('清空请求历史'))) return
  try {
    await ElMessageBox.confirm('确定清空此接口的所有请求历史？', '清空历史', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
    await request.delete(`/projects/${projectId.value}/debug-history`, {
      params: { api_id: props.apiId },
    })
    items.value = []
    msgSuccess('已清空')
  } catch (err) { logger.error('[RequestHistoryPanel] clear all failed:', err); msgError('清空历史记录失败'); /* cancelled */ }
}

function selectItem(item: HistoryItem) {
  selectedId.value = item.id
  selectedItem.value = item
  showDetail.value = true
}

function restoreRequest() {
  if (!selectedItem.value) return
  emit('restore', {
    url: selectedItem.value.url,
    headers: selectedItem.value.request_headers,
    body: selectedItem.value.request_body,
  })
  showDetail.value = false
  msgSuccess('已恢复请求参数')
}

// 当 apiId 变化时重新加载
watch(() => props.apiId, () => { void refresh() }, { immediate: true })
</script>

<style scoped>
/* 请求历史面板 — 使用 design tokens 统一风格
 * 策略：所有颜色/间距/圆角均使用 CSS 变量，确保暗色模式自动适配
 * 交互状态：hover / active / focus-visible 完整覆盖
 */
.history-panel {
  border-left: 1px solid var(--border-subtle);
  background: var(--surface-card);
  width: 280px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部 */
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-subtle);
}

.history-header h3 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
}

.history-actions {
  display: flex;
  gap: var(--spacing-xs);
}

/* 加载状态 */
.history-loading {
  padding: var(--spacing-lg);
}

/* 空状态 */
.history-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  padding: var(--spacing-5xl) var(--spacing-lg);
  text-align: center;
  gap: var(--spacing-sm);
}

.history-empty p {
  margin: 0;
  font-size: var(--font-size-sm);
}

.history-empty .hint {
  font-size: var(--font-size-xs);
  color: var(--text-disabled);
}

/* 历史列表 */
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: var(--radius-2xs);
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* 历史条目 — 交互状态完整覆盖 */
.history-item {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--duration-fast) var(--ease-smooth),
              box-shadow var(--duration-fast) var(--ease-smooth);
  margin-bottom: var(--spacing-xs);
}

.history-item:hover {
  background: var(--surface-hover);
}

.history-item.active {
  background: var(--surface-selected);
  box-shadow: var(--shadow-xs);
}

.history-item:focus-visible {
  outline: none;
  box-shadow: var(--shadow-focus);
}

.history-item:active {
  background: var(--surface-active);
}

.history-item-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

/* HTTP 方法徽章 — 使用语义色变量，暗色模式自动适配 */
.method-badge {
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-bold);
  padding: var(--spacing-0-5) var(--spacing-xs);
  border-radius: var(--radius-sm);
  color: var(--text-inverse);
  min-width: 36px;
  text-align: center;
  line-height: var(--leading-tight);
  transition: opacity var(--duration-fast) var(--ease-smooth);
}

.method-badge:hover {
  opacity: 0.85;
}

.method-get { background: var(--method-get-text); }
.method-post { background: var(--method-post-text); }
.method-put { background: var(--method-put-text); }
.method-patch { background: var(--method-patch-text); }
.method-delete { background: var(--method-delete-text); }
.method-head { background: var(--method-head-text); }
.method-options { background: var(--method-options-text); }

/* 状态码徽章 — 使用语义色变量 */
.status-badge {
  font-size: var(--font-size-2xs);
  font-weight: var(--weight-semibold);
  padding: var(--spacing-0-5) var(--spacing-xs);
  border-radius: var(--radius-sm);
  min-width: 32px;
  text-align: center;
  line-height: var(--leading-tight);
}

.status-success { background: var(--success-bg); color: var(--success-text); }
.status-redirect { background: var(--warning-bg); color: var(--warning-text); }
.status-error { background: var(--error-bg); color: var(--error-text); }
.status-unknown { background: var(--surface-nested); color: var(--text-muted); }

/* 耗时 */
.duration {
  font-size: var(--font-size-2xs);
  color: var(--text-muted);
  margin-left: auto;
  font-family: var(--font-mono);
}

/* URL — 单行截断，使用省略号 */
.history-item-url {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 240px;
  line-height: var(--leading-normal);
}

/* 时间戳 — 使用等宽字体 */
.history-item-time {
  font-size: var(--font-size-2xs);
  color: var(--text-disabled);
  margin-top: var(--spacing-xs);
  font-family: var(--font-mono);
  line-height: var(--leading-tight);
}

/* 详情弹窗 */
.detail-section {
  margin-bottom: var(--spacing-md);
}

.detail-label {
  font-size: var(--font-size-xs);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
}

.detail-row {
  display: flex;
  gap: var(--spacing-lg);
}

.flex-1 {
  flex: 1;
}

/* 暗色模式 */
:global(html.dark) .history-panel { background: var(--surface-card); border-left-color: var(--border-subtle); }
:global(html.dark) .history-header { border-bottom-color: var(--border-subtle); }
:global(html.dark) .history-header h3 { color: var(--text-primary); }
:global(html.dark) .history-item:hover { background: var(--surface-hover); }
:global(html.dark) .history-item.active { background: var(--color-primary-alpha-10); }
</style>
